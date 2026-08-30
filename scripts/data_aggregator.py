"""Aggregate the publication sample and export a compact browser payload."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    AGGREGATED_STATS,
    DERIVED_MOVIES_INFO,
    DIALECT_AGGREGATES,
    FRONTEND_DATASET,
    MOVIE_DETAILS_DIR,
    SAMPLE_MANIFEST,
)
from dialect_defs import lang_parts  # noqa: E402


TITLE = "片名"
YEAR = "年份"
RATING = "豆瓣评分"
VOTES = "评价人数"
GENRE = "类型"
MOVIE_ID = "movie_id"
DIRECTOR = "导演"
PRODUCTION_COUNTRIES = "制片国家/地区"
ORIGINAL_LANGUAGES = "语言"
DATA_SOURCE = "数据来源"
SOURCE_URL = "来源URL"
SYNOPSIS = "剧情简介"
GEMINI_REVIEW = "Gemini评价"

FRONTEND_COLUMNS = [
    "movieId",
    "title",
    "year",
    "rating",
    "votes",
    "decade",
    "region",
    "language",
    "genres",
    "regionCode",
    "genreCode",
    "langCode",
    "isDialect",
]

DETAIL_COLUMNS = [
    "movieId",
    "director",
    "productionCountries",
    "originalLanguages",
    "source",
    "sourceUrl",
    "summaryKind",
    "summary",
]
DETAIL_SHARD_COUNT = 64
DETAIL_SUMMARY_LIMIT = 500
MISSING_DETAIL_VALUES = {
    "", "nan", "null", "none", "unknown", "<na>", "未知", "暂无数据",
    "暂无简介", r"\N", "\n",
    # 注：前端 app.js / core.js 的 missing 集合使用 '\n'（换行符），
    # 后端同时包含 r"\N"（字面反斜杠 N）和 "\n"（换行符），确保两种无意义值均被过滤。
}
NORMALIZED_MISSING_DETAIL_VALUES = {item.casefold() for item in MISSING_DETAIL_VALUES}


def atomic_write_json(payload: object, path: Path, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    kwargs = {"ensure_ascii": False, "allow_nan": False}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    temporary.write_text(json.dumps(payload, **kwargs), encoding="utf-8")
    # Windows: Path.replace() fails if target is read-only; clear the flag first.
    try:
        temporary.replace(path)
    except PermissionError:
        if path.exists():
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            temporary.replace(path)
        else:
            raise


def top_movies(frame: pd.DataFrame, count: int = 5) -> list[dict]:
    columns = [TITLE, YEAR, RATING, VOTES, GENRE]
    return (
        frame.sort_values([RATING, VOTES], ascending=False)[columns]
        .head(count)
        .rename(columns={TITLE: "title", YEAR: "year", RATING: "rating", VOTES: "votes", GENRE: "genres"})
        .to_dict("records")
    )


def grouped_stats(frame: pd.DataFrame, column: str) -> dict:
    result = {}
    for value, group in frame.groupby(column, dropna=False):
        ratings = group[RATING]
        result[str(value)] = {
            "count": int(len(group)),
            "avg_rating": round(float(ratings.mean()), 4),
            "median_rating": round(float(ratings.median()), 4),
            "avg_votes": round(float(group[VOTES].mean()), 2),
            "top_movies": top_movies(group),
        }
    return result


def build_frontend_payload(frame: pd.DataFrame, manifest: dict) -> dict:
    records = []
    source_columns = [
        MOVIE_ID, TITLE, YEAR, RATING, VOTES, "Decade", "Region",
        "Language_Category", GENRE, "Region_Code", "Genre_Code",
        "Language_Code", "Is_Dialect",
    ]
    for values in frame[source_columns].itertuples(index=False, name=None):
        (
            movie_id, title, year, rating, votes, decade, region, language,
            genres, region_code, genre_code, language_code, is_dialect,
        ) = values
        records.append([
            str(movie_id),
            title,
            int(year),
            float(rating),
            int(votes),
            decade,
            region,
            language,
            genres if pd.notna(genres) else "Unknown",
            int(region_code),
            int(genre_code),
            int(language_code),
            int(is_dialect),
        ])

    return {
        "meta": {
            "schemaVersion": 2,
            "recordCount": len(records),
            "sourceRecordCount": manifest["stages"]["source_rows"],
            "minimumVoteCount": manifest["inclusion_criteria"]["minimum_vote_count"],
            "yearRange": [int(frame[YEAR].min()), int(frame[YEAR].max())],
            "eligibleYearRange": manifest["inclusion_criteria"]["year_range"],
            "sampleFingerprint": manifest["sample_fingerprint_sha256"],
        },
        "columns": FRONTEND_COLUMNS,
        "records": records,
    }


def detail_shard(movie_id: object) -> int:
    value = str(movie_id)
    result = 0
    for character in value:
        result = (result * 31 + ord(character)) & 0xFFFFFFFF
    return result % DETAIL_SHARD_COUNT


def usable_detail_text(value: object, *, gemini: bool = False) -> str:
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value).strip())
    if text.casefold() in NORMALIZED_MISSING_DETAIL_VALUES:
        return ""
    if gemini and text in {"经典电影暂无评价", "暂无评价"}:
        return ""
    return text


def build_movie_detail_shards(frame: pd.DataFrame, manifest: dict) -> list[dict]:
    records_by_shard: list[list[list]] = [[] for _ in range(DETAIL_SHARD_COUNT)]
    source_columns = [
        MOVIE_ID, DIRECTOR, PRODUCTION_COUNTRIES, ORIGINAL_LANGUAGES,
        DATA_SOURCE, SOURCE_URL, SYNOPSIS, GEMINI_REVIEW,
    ]
    for values in frame[source_columns].itertuples(index=False, name=None):
        movie_id = str(values[0])
        synopsis = usable_detail_text(values[6])
        gemini_review = usable_detail_text(values[7], gemini=True)
        summary_kind = 0 if synopsis else 1 if gemini_review else 2
        summary = synopsis or gemini_review
        if len(summary) > DETAIL_SUMMARY_LIMIT:
            summary = summary[:DETAIL_SUMMARY_LIMIT].rstrip() + "…"
        records_by_shard[detail_shard(movie_id)].append([
            movie_id,
            values[1] if pd.notna(values[1]) else "",
            values[2] if pd.notna(values[2]) else "",
            values[3] if pd.notna(values[3]) else "",
            values[4] if pd.notna(values[4]) else "",
            values[5] if pd.notna(values[5]) else "",
            summary_kind,
            summary,
        ])
    return [
        {
            "meta": {
                "schemaVersion": 1,
                "recordCount": len(records),
                "shard": shard,
                "shardCount": DETAIL_SHARD_COUNT,
                "sampleFingerprint": manifest["sample_fingerprint_sha256"],
            },
            "columns": DETAIL_COLUMNS,
            "records": records,
        }
        for shard, records in enumerate(records_by_shard)
    ]


# --- 方言叙事聚合（口径固化自 scripts/sync_preview_dialect_v43_20260819.py 文档头，v4.4 基线） ---

DECADE_ORDER = ["Pre-1990s", "1990s", "2000s", "2010s", "2020s"]
FLOP_DECADES = ["1990s", "2000s", "2010s", "2020s"]
YEARLY_START, YEARLY_END = 1990, 2020
YEARLY_MIN_PER_SIDE = 5
DIVERSITY_MIN_COUNT = 10
DIVERSITY_TOP = 10
GENRE_AVG_MIN_COUNT = 30
GENRE_AVG_TOP = 8
GENRE_AVG_TOP_FILMS = 3
TYPE_EXCLUDE_GENRES = ("纪录片", "音乐", "歌舞", "舞台")
TYPE_DRAMA_TAG = "剧情"
# 与 sync 脚本一致的“中国方言语言”标签集合（diversity 仅统计这些标签）
CHINESE_DIALECT_TAGS = {'粤语', '闽南语', '台语', '上海话', '四川话', '重庆话', '客家话', '晋语',
                        '维吾尔语', '藏语', '东北话', '河南话', '陕西话', '湖南话', '山东话',
                        '吴语', '赣语', '湘语', '蒙语', '哈萨克语', '彝语', '壮语', '潮汕话',
                        '南京话', '武汉话', '广州话', '方言', '唐山话', '天津话', '贵州话',
                        '云南话', '山西话', '河北话', '江淮官话', '手语'}
# 三波浪潮人工策展片单（movie_id 选取为人工核验结果，属性从冻结主表动态取值）
WAVE_CASE_IDS = {
    "hk": ["1307914", "1303913", "900054", "1305690", "900089"],
    "sw": ["900072", "27110296", "26337866", "26657126", "27668250"],
    "mn": ["1292434", "27059130", "3993559", "30292777", "34805873"],
}


def below5_share(frame: pd.DataFrame) -> float | None:
    if frame.empty:
        return None
    return round(float((frame[RATING] < 5).mean() * 100), 1)


def group_block(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"n": 0, "mean": None, "below5": None}
    return {
        "n": int(len(frame)),
        "mean": round(float(frame[RATING].mean()), 2),
        "below5": below5_share(frame),
    }


def genre_mask(frame: pd.DataFrame, tags: tuple) -> pd.Series:
    text = frame[GENRE].fillna("").astype(str)
    return text.map(lambda value: any(tag in value for tag in tags))


def build_dialect_aggregates(frame: pd.DataFrame, manifest: dict) -> dict:
    """从冻结主表重算方言叙事预计算聚合（全部 Region=China，除非另注）。

    口径继承 sync_preview_dialect_v43_20260819.py 文档头：
    dialect = Is_Dialect==1；mandarin = Is_Dialect==0；below5 = 豆瓣评分<5 占比；
    yearly = 逐年均分差（方言-普通话），双方 n>=5，范围 1990-2020；
    canto = 方言片中语言字段含/不含“粤语”；diversity = lang_parts 拆标签，min n>=10；
    global = 六层烂片率（全 Region 子层 + China 层，欧洲子层用 Language_Category）；
    dual_director = 双栖导演（方言/普通话片各>=1 部）分差直方图；
    genre_avg = 方言片类型展开，min n>=30，按均分 top8，各配 top3 片单。
    """
    china = frame[frame["Region"] == "China"]
    dialect = china[china["Is_Dialect"] == 1]
    mandarin = china[china["Is_Dialect"] == 0]

    # by_decade / flop_decade
    by_decade = {}
    for decade in DECADE_ORDER:
        d_part = dialect[dialect["Decade"].astype(str) == decade]
        m_part = mandarin[mandarin["Decade"].astype(str) == decade]
        if d_part.empty or m_part.empty:
            delta = None
        else:
            delta = round(float(d_part[RATING].mean() - m_part[RATING].mean()), 2)
        by_decade[decade] = {
            "d": group_block(d_part),
            "m": group_block(m_part),
            "delta": delta,
        }
    flop_decade = {
        decade: {
            "d": below5_share(dialect[dialect["Decade"].astype(str) == decade]),
            "m": below5_share(mandarin[mandarin["Decade"].astype(str) == decade]),
        }
        for decade in FLOP_DECADES
    }
    flop_overall = {"d": below5_share(dialect), "m": below5_share(mandarin)}

    # yearly（双方 n>=5）
    yearly = {}
    for year in range(YEARLY_START, YEARLY_END + 1):
        d_year = dialect[dialect[YEAR] == year]
        m_year = mandarin[mandarin[YEAR] == year]
        if len(d_year) >= YEARLY_MIN_PER_SIDE and len(m_year) >= YEARLY_MIN_PER_SIDE:
            yearly[str(year)] = round(float(d_year[RATING].mean() - m_year[RATING].mean()), 2)

    # type_controlled 三口径
    def controlled_pair(sub: pd.DataFrame) -> dict:
        return {
            "d": group_block(sub[sub["Is_Dialect"] == 1]),
            "m": group_block(sub[sub["Is_Dialect"] == 0]),
        }

    exclude_mask = genre_mask(china, TYPE_EXCLUDE_GENRES)
    type_controlled = {
        "raw": controlled_pair(china),
        "exclude": controlled_pair(china[~exclude_mask]),
        "drama": controlled_pair(china[genre_mask(china, (TYPE_DRAMA_TAG,))]),
    }

    # canto（方言片内部：含/不含粤语）
    lang_text = dialect[ORIGINAL_LANGUAGES].fillna("").astype(str)
    canto_part = dialect[lang_text.str.contains("粤语")]
    non_canto = dialect[~lang_text.str.contains("粤语")]
    cantonese_vs_non = [
        {"name": "非粤语方言", "mean": round(float(non_canto[RATING].mean()), 2),
         "below5": below5_share(non_canto), "n": int(len(non_canto))},
        {"name": "粤语", "mean": round(float(canto_part[RATING].mean()), 2),
         "below5": below5_share(canto_part), "n": int(len(canto_part))},
    ]

    # lang_diversity（lang_parts 拆标签，仅中国方言语言标签，min n>=10，top10 by mean）
    tag_ratings: dict[str, list[float]] = defaultdict(list)
    for language, rating in zip(
        dialect[ORIGINAL_LANGUAGES].fillna("").astype(str), dialect[RATING]
    ):
        for part in lang_parts(language):
            if part in CHINESE_DIALECT_TAGS:
                tag_ratings[part].append(float(rating))
    diversity_rows = [
        (tag, sum(values) / len(values), len(values))
        for tag, values in tag_ratings.items()
        if len(values) >= DIVERSITY_MIN_COUNT
    ]
    diversity_rows.sort(key=lambda item: (-item[1], item[0]))
    lang_diversity = [
        {"name": tag, "mean": round(mean, 2), "n": count}
        for tag, mean, count in diversity_rows[:DIVERSITY_TOP]
    ]

    # global_layers 六层烂片率（全 Region 子层 + China 层）
    europe = frame[frame["Region"] == "Europe"]
    north_america = frame[frame["Region"] == "North_America"]
    east_asia = frame[frame["Region"] == "East_Asia"]
    layers = [
        ("欧洲 · 非主导语言", europe[europe["Language_Category"] == "European_Languages"], {}),
        ("欧洲 · 英语", europe[europe["Language_Category"] == "English"], {}),
        ("日韩", east_asia, {}),
        ("华语 · 方言", dialect, {}),
        ("北美 · 英语", north_america[north_america["Language_Category"] == "English"], {}),
        ("华语 · 普通话", mandarin, {"outlier": True}),
    ]
    global_layers = [
        {"name": name, "below5": below5_share(sub), "n": int(len(sub)), **extra}
        for name, sub, extra in layers
    ]

    # dual_director（双栖导演分差直方图 + 群体指标）
    d_stats = dialect.groupby(DIRECTOR)[RATING].agg(["mean", "count"])
    m_stats = mandarin.groupby(DIRECTOR)[RATING].agg(["mean", "count"])
    common = d_stats.index.intersection(m_stats.index)
    diff = d_stats.loc[common, "mean"] - m_stats.loc[common, "mean"]
    rounded = diff.round(0)
    dual_director = {
        "hist": {
            "≤−2": int((rounded <= -2).sum()),
            "−1": int((rounded == -1).sum()),
            "0": int((rounded == 0).sum()),
            "+1": int((rounded == 1).sum()),
            "+2": int((rounded == 2).sum()),
            "+3": int((rounded == 3).sum()),
            "≥+4": int((rounded >= 4).sum()),
        },
        "total": int(len(common)),
        "share_positive": int(round(float((diff > 0).mean() * 100))),
        "mean_diff": round(float(diff.mean()), 2),
    }

    # genre_avg（方言片类型展开，n>=30，top8 by mean，含 top3 片单）
    genre_films: dict[str, list[dict]] = defaultdict(list)
    for genres, title, year, rating, movie_id in dialect[
        [GENRE, TITLE, YEAR, RATING, MOVIE_ID]
    ].itertuples(index=False, name=None):
        if pd.isna(genres):
            continue
        for tag in re.split(r"[/,，]", str(genres)):
            tag = tag.strip()
            if tag and tag.casefold() != "nan":
                genre_films[tag].append({
                    "id": str(movie_id),
                    "title": title,
                    "year": int(year),
                    "rating": float(rating),
                })
    candidates = [
        (tag, films, sum(film["rating"] for film in films) / len(films))
        for tag, films in genre_films.items()
        if len(films) >= GENRE_AVG_MIN_COUNT
    ]
    candidates.sort(key=lambda item: (-item[2], item[0]))
    genre_avg = [
        {
            "name": tag,
            "mean": round(mean, 2),
            "n": len(films),
            "top": sorted(films, key=lambda film: (-film["rating"], film["title"]))[:GENRE_AVG_TOP_FILMS],
        }
        for tag, films, mean in candidates[:GENRE_AVG_TOP]
    ]

    # wave_cases（人工策展片单，属性从冻结主表取值）
    def wave_entry(movie_id: str) -> dict:
        rows = frame[frame[MOVIE_ID] == movie_id]
        if len(rows) != 1:
            raise ValueError(f"wave case movie {movie_id} missing from publication sample")
        row = rows.iloc[0]
        return {
            "id": movie_id,
            "title": row[TITLE],
            "year": int(row[YEAR]),
            "rating": float(row[RATING]),
        }

    wave_cases = {wave: [wave_entry(mid) for mid in ids] for wave, ids in WAVE_CASE_IDS.items()}

    return {
        "meta": {
            "schemaVersion": 1,
            "sampleFingerprint": manifest["sample_fingerprint_sha256"],
            "baseline": {
                "china_dialect": int(len(dialect)),
                "china_mandarin": int(len(mandarin)),
                "china_total": int(len(china)),
                "dialect_all_regions": int((frame["Is_Dialect"] == 1).sum()),
                "publication_records": int(len(frame)),
            },
            "methodology": (
                "Region=China；dialect=Is_Dialect==1；below5=豆瓣评分<5占比；"
                "yearly 双方n>=5（1990-2020）；lang_diversity min n>=10 top10；"
                "genre_avg min n>=30 top8；口径固化自 sync_preview_dialect_v43_20260819.py"
            ),
        },
        "by_decade": by_decade,
        "flop_decade": flop_decade,
        "flop_overall": flop_overall,
        "yearly": yearly,
        "type_controlled": type_controlled,
        "cantonese_vs_non": cantonese_vs_non,
        "lang_diversity": lang_diversity,
        "global_layers": global_layers,
        "dual_director": dual_director,
        "genre_avg": genre_avg,
        "wave_cases": wave_cases,
    }


def main() -> None:
    frame = pd.read_csv(DERIVED_MOVIES_INFO, dtype={MOVIE_ID: "string"})
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    if len(frame) != manifest["publication_records"]:
        raise ValueError("Derived dataset and sample manifest have different record counts")

    stats = {
        "meta": {
            "record_count": len(frame),
            "minimum_vote_count": manifest["inclusion_criteria"]["minimum_vote_count"],
            "sample_fingerprint": manifest["sample_fingerprint_sha256"],
        },
        "decades": grouped_stats(frame, "Decade"),
        "regions": grouped_stats(frame, "Region"),
        "languages": grouped_stats(frame, "Language_Category"),
    }
    payload = build_frontend_payload(frame, manifest)
    detail_shards = build_movie_detail_shards(frame, manifest)
    dialect_aggregates = build_dialect_aggregates(frame, manifest)
    atomic_write_json(stats, AGGREGATED_STATS, pretty=True)
    atomic_write_json(payload, FRONTEND_DATASET)
    for shard, detail_payload in enumerate(detail_shards):
        atomic_write_json(detail_payload, MOVIE_DETAILS_DIR / f"{shard:02x}.json")
    atomic_write_json(dialect_aggregates, DIALECT_AGGREGATES, pretty=True)
    print(f"Aggregated {len(frame):,} publication records.")
    print(f"Statistics: {AGGREGATED_STATS}")
    print(f"Frontend payload: {FRONTEND_DATASET}")
    print(f"Movie details: {len(detail_shards)} shards in {MOVIE_DETAILS_DIR}")
    print(f"Dialect aggregates: {DIALECT_AGGREGATES}")


if __name__ == "__main__":
    main()
