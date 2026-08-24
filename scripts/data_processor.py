"""Build the reproducible publication sample for the taste-analysis story.

The source table is much larger than the browser payload and continues to gain
metadata.  This script selects only records that support defensible rating
comparisons: a title, a plausible release year, a valid Douban rating, and at
least ``MIN_VOTE_COUNT`` recorded ratings.  It also normalizes bilingual country,
language, and genre values used by the front-end story.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST, SOURCE_MOVIES_INFO, SOURCE_MOVIES_MERGED

# 方言定义单一事实来源（v2.1 严格中国语言标准）。
# 修改方言判定请只改 dialect_defs.py，data_processor 与 gen_report_strict 共用。
from dialect_defs import MANDARIN_MARKERS, has_strict_dialect_tag, first_tag_is_foreign


MIN_VOTE_COUNT = 100
MIN_YEAR = 1888
MAX_YEAR = 2026
CHUNK_SIZE = 5_000

COLUMNS = {
    "id": "movie_id",
    "title": "片名",
    "year": "年份",
    "director": "导演",
    "genre": "类型",
    "region_raw": "制片国家/地区",
    "language_raw": "语言",
    "rating": "豆瓣评分",
    "synopsis": "剧情简介",
    "gemini_review": "Gemini评价",
    "votes": "评价人数",
    "source": "数据来源",
    "source_url": "来源URL",
}

OUTPUT_COLUMNS = [
    COLUMNS["id"],
    COLUMNS["title"],
    COLUMNS["year"],
    COLUMNS["director"],
    COLUMNS["genre"],
    COLUMNS["region_raw"],
    COLUMNS["language_raw"],
    COLUMNS["rating"],
    COLUMNS["synopsis"],
    COLUMNS["gemini_review"],
    COLUMNS["votes"],
    COLUMNS["source"],
    COLUMNS["source_url"],
    "Decade",
    "Region",
    "Language_Category",
    "Region_Code",
    "Genre_Code",
    "Language_Code",
    "Is_Dialect",
    # 新增字段（delivery_20260817 合并后）
    "card_subtitle",
    "rating_star",
    "featured_comment",
    "comment_user",
    "honors",
]

# 合并数据新增的列（不在 COLUMNS 中，但需从源数据传递到输出）
DELIVERY_PASSTHROUGH_COLUMNS = [
    "card_subtitle",
    "rating_star",
    "featured_comment",
    "comment_user",
    "honors",
]

REGION_CODES = {
    "North_America": 0,
    "Europe": 1,
    "East_Asia": 2,
    "China": 3,
    "Other": 4,
}

CHINA_MARKERS = (
    "中国", "china", "hong kong", "香港", "taiwan", "台湾", "臺灣",
    "macau", "macao", "澳门", "澳門",
)
NORTH_AMERICA_MARKERS = (
    "united states", "u.s.a", "usa", "美国", "美國", "canada", "加拿大",
    "mexico", "墨西哥",
)
EAST_ASIA_MARKERS = (
    "japan", "日本", "south korea", "republic of korea", "korea", "韩国",
    "韓國", "north korea", "朝鲜", "朝鮮", "mongolia", "蒙古",
)
EUROPE_MARKERS = (
    "europe", "欧洲", "歐洲", "united kingdom", "uk", "england", "britain",
    "英国", "英國", "france", "法国", "法國", "germany", "德国", "德國",
    "西德", "东德", "東德", "west germany", "east germany",
    "italy", "意大利", "義大利", "spain", "西班牙", "portugal", "葡萄牙",
    "ireland", "爱尔兰", "愛爾蘭", "netherlands", "holland", "荷兰", "荷蘭",
    "belgium", "比利时", "比利時", "switzerland", "瑞士", "austria", "奥地利",
    "奧地利", "sweden", "瑞典", "norway", "挪威", "denmark", "丹麦", "丹麥",
    "finland", "芬兰", "芬蘭", "iceland", "冰岛", "冰島", "poland", "波兰",
    "波蘭", "czech", "捷克", "slovakia", "斯洛伐克", "hungary", "匈牙利",
    "romania", "罗马尼亚", "羅馬尼亞", "bulgaria", "保加利亚", "保加利亞",
    "greece", "希腊", "希臘", "croatia", "克罗地亚", "克羅地亞", "serbia",
    "塞尔维亚", "塞爾維亞", "slovenia", "斯洛文尼亚", "斯洛文尼亞",
    "ukraine", "乌克兰", "烏克蘭", "russia", "俄罗斯", "俄羅斯", "ussr",
    "soviet union", "苏联", "蘇聯", "estonia", "爱沙尼亚", "愛沙尼亞",
    "latvia", "拉脱维亚", "拉脫維亞", "lithuania", "立陶宛", "luxembourg",
    "卢森堡", "盧森堡",
)

CHINESE_LANGUAGE_MARKERS = (
    "汉语", "漢語", "中文", "普通话", "普通話", "国语", "國語",  # 2026-08-15 审计补“国语”异形
    "mandarin", "cantonese",
    "粤语", "粵語", "hokkien", "闽南", "閩南", "shanghainese", "沪语", "滬語",
    "sichuanese", "四川话", "四川話", "hakka", "客家话", "客家話", "taiwanese",
)
# DIALECT_MARKERS / MANDARIN_MARKERS 定义已迁移至 dialect_defs.py（v2.1 完整白名单），
# 此处不再重复定义；Is_Dialect 判定统一走 has_strict_dialect_tag。
ENGLISH_MARKERS = ("english", "英语", "英語")
JAPANESE_MARKERS = ("japanese", "日语", "日語", "日本語", "日文")
KOREAN_MARKERS = (
    "korean", "韩语", "韓語", "한국어", "조선어", "조선말",
    "朝鲜语", "朝鮮語", "韩文", "韓文",
)
JAPANESE_KOREAN_MARKERS = JAPANESE_MARKERS + KOREAN_MARKERS
EUROPEAN_LANGUAGE_MARKERS = (
    "french", "法语", "法語", "german", "德语", "德語", "italian", "意大利语",
    "義大利語", "spanish", "西班牙语", "西班牙語", "portuguese", "葡萄牙语",
    "葡萄牙語", "russian", "俄语", "俄語", "dutch", "荷兰语", "荷蘭語",
    "swedish", "瑞典语", "瑞典語", "danish", "丹麦语", "丹麥語", "norwegian",
    "挪威语", "挪威語", "polish", "波兰语", "波蘭語", "greek", "希腊语",
    "希臘語", "czech", "捷克语", "捷克語", "hungarian", "匈牙利语", "匈牙利語",
)


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def normalize_identity_title(value: object) -> str:
    """Normalize a title for identity checks without changing display text."""
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", "", text).casefold()


def douban_subject_id(value: object) -> str:
    """Extract a canonical Douban subject id from a source URL when present."""
    if pd.isna(value):
        return ""
    match = re.search(r"/subject/(\d+)(?:/|$)", str(value))
    return match.group(1) if match else ""


def normalize_movie_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:-2] if re.fullmatch(r"\d+\.0", text) else text


def deduplicate_publication_records(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Prefer canonical source identities, then deduplicate normalized title/year.

    The upstream table mixes canonical Douban ids with a small set of internal
    project ids. Two records can therefore point to the same Douban subject
    while differing only in title capitalization. URL identity is checked
    first; normalized title/year remains the fallback used by the publication.
    """
    sample = frame.copy()
    sample["_subject_id"] = sample[COLUMNS["source_url"]].map(douban_subject_id)
    normalized_ids = sample[COLUMNS["id"]].map(normalize_movie_id)
    sample["_canonical_id_match"] = sample["_subject_id"].ne("") & sample["_subject_id"].eq(normalized_ids)
    sample["_source_priority"] = sample[COLUMNS["source"]].fillna("").eq("douban_all_data")
    sample["_normalized_title"] = sample[COLUMNS["title"]].map(normalize_identity_title)

    sample = sample.sort_values(
        [COLUMNS["votes"], "_canonical_id_match", "_source_priority", COLUMNS["title"], COLUMNS["year"]],
        ascending=[False, False, False, True, True],
        kind="stable",
    )
    duplicate_url = sample["_subject_id"].ne("") & sample["_subject_id"].duplicated(keep="first")
    removed_by_url = int(duplicate_url.sum())
    sample = sample.loc[~duplicate_url].copy()

    duplicate_title_year = sample.duplicated(["_normalized_title", COLUMNS["year"]], keep="first")
    removed_by_title_year = int(duplicate_title_year.sum())
    sample = sample.loc[~duplicate_title_year].copy()
    sample = sample.drop(columns=["_subject_id", "_canonical_id_match", "_source_priority", "_normalized_title"])
    return sample, {
        "duplicates_removed_by_source_url": removed_by_url,
        "duplicates_removed_by_normalized_title_year": removed_by_title_year,
        "duplicates_removed": removed_by_url + removed_by_title_year,
    }


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def first_listed_value(value: object) -> str:
    """Return the first listed production country/region.

    Douban's native format uses slash (or pipe/semicolon) separators.
    delivery_20260817 uses spaces between CJK country names
    (e.g. ``日本 中国香港 韩国``). English multi-word names such as
    ``united states`` are kept intact because they contain no CJK.
    """
    text = normalize_text(value)
    if not text:
        return ""
    parts = re.split(r"\s*(?:/|\||;|；)\s*", text)
    if len(parts) > 1:
        return parts[0]
    if " " in text and _CJK_RE.search(text):
        return text.split(" ", 1)[0]
    return text


def contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def categorize_decade(year: int) -> str:
    if year < 1990:
        return "Pre-1990s"
    if year < 2000:
        return "1990s"
    if year < 2010:
        return "2000s"
    if year < 2020:
        return "2010s"
    return "2020s"


def categorize_region(value: object) -> str:
    """Classify by the first listed production country/region."""
    primary = first_listed_value(value)
    if contains_any(primary, CHINA_MARKERS):
        return "China"
    if contains_any(primary, NORTH_AMERICA_MARKERS):
        return "North_America"
    if contains_any(primary, EAST_ASIA_MARKERS):
        return "East_Asia"
    if contains_any(primary, EUROPE_MARKERS):
        return "Europe"
    return "Other"


def language_parts(value: object) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"\s*(?:/|\||;|；|,)\s*", text) if part.strip()]


def primary_language_tag(value: object) -> str:
    """First listed language tag; used as the main-language key for mixed films."""
    parts = language_parts(value)
    return parts[0] if parts else ""


def categorize_language(value: object) -> str:
    text = normalize_text(value)
    if contains_any(text, CHINESE_LANGUAGE_MARKERS):
        return "Chinese"
    if contains_any(text, ENGLISH_MARKERS):
        return "English"
    primary = primary_language_tag(value) or text
    if contains_any(primary, JAPANESE_MARKERS):
        return "Japanese"
    if contains_any(primary, KOREAN_MARKERS):
        return "Korean"
    if contains_any(text, JAPANESE_MARKERS):
        return "Japanese"
    if contains_any(text, KOREAN_MARKERS):
        return "Korean"
    if contains_any(text, EUROPEAN_LANGUAGE_MARKERS):
        return "European_Languages"
    return "Other"


def non_dialect_language_code(value: object) -> int:
    """Map a non-dialect film to the six analysis language groups.

    0 English, 1 Japanese, 2 Mandarin, 4 Korean, 5 Other.
    Mandarin/English keep the previous any-marker membership so the Chinese
    dialect-vs-Mandarin comparison uses the same films. Japanese/Korean/Other
    split the former Europe/other bucket by the first listed language.
    """
    text = normalize_text(value)
    if contains_any(text, MANDARIN_MARKERS) or contains_any(text, CHINESE_LANGUAGE_MARKERS):
        return 2
    if contains_any(text, ENGLISH_MARKERS):
        return 0
    primary = primary_language_tag(value) or text
    if contains_any(primary, JAPANESE_MARKERS):
        return 1
    if contains_any(primary, KOREAN_MARKERS):
        return 4
    if contains_any(text, JAPANESE_MARKERS):
        return 1
    if contains_any(text, KOREAN_MARKERS):
        return 4
    return 5


def language_code(value: object, region: object = None) -> tuple[int, int]:
    """Return front-end language code and dialect flag.

    0 English, 1 Japanese, 2 Mandarin, 3 Chinese dialect, 4 Korean, 5 Other.

    方言组沿用中国方言清单（Is_Dialect）。方案 A（2026-08-15）：region == "China"
    且命中方言标签但首个语言标签为外语时不计入方言口径，改走非方言主语言归组。
    规则定义见 dialect_defs.first_tag_is_foreign；非 China 行不受影响。
    """
    # v2.1 严格判定：仅当语言字段含中国方言/少数民族语言标签才算方言片。
    is_dialect = has_strict_dialect_tag(value)
    if is_dialect and region == "China" and first_tag_is_foreign(value):
        is_dialect = False  # 方案 A：外语排首位的中国制片方言片排除出口径
    if is_dialect:
        return 3, 1
    return non_dialect_language_code(value), 0


def genre_code(value: object) -> int:
    """Map the first listed genre to the seven story groups."""
    primary = first_listed_value(value)
    if contains_any(primary, ("剧情", "劇情", "drama")):
        return 0
    if contains_any(primary, ("喜剧", "喜劇", "comedy")):
        return 1
    if contains_any(primary, ("动作", "動作", "action", "冒险", "冒險", "adventure")):
        return 2
    if contains_any(primary, ("爱情", "愛情", "romance")):
        return 3
    if contains_any(primary, (
        "悬疑", "懸疑", "犯罪", "惊悚", "驚悚", "恐怖", "mystery", "crime",
        "thriller", "horror",
    )):
        return 4
    if contains_any(primary, ("科幻", "奇幻", "sci-fi", "science fiction", "fantasy")):
        return 5
    return 6


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig")
    try:
        temporary.replace(path)
    except PermissionError:
        import os
        import stat as stat_mod
        if path.exists():
            os.chmod(path, stat_mod.S_IWRITE | stat_mod.S_IREAD)
            temporary.replace(path)
        else:
            raise


def atomic_write_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temporary.replace(path)
    except PermissionError:
        import os
        import stat as stat_mod
        if path.exists():
            os.chmod(path, stat_mod.S_IWRITE | stat_mod.S_IREAD)
            temporary.replace(path)
        else:
            raise


def manifest_source_display(source_path: Path, repo_root: Path) -> str:
    """Store a portable source locator: repo-relative POSIX path, or filename only."""
    resolved = source_path.expanduser().resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return f"source_external:{resolved.name}"


def publication_fingerprint(sample: pd.DataFrame) -> str:
    fingerprint_columns = [
        COLUMNS["id"], COLUMNS["title"], COLUMNS["year"], COLUMNS["rating"],
        COLUMNS["votes"], "Region", "Language_Code", "Genre_Code",
    ]
    hashed = pd.util.hash_pandas_object(sample[fingerprint_columns], index=False)
    return hashlib.sha256(hashed.values.tobytes()).hexdigest()


def build_publication_sample(
    source_path: Path,
    min_votes: int = MIN_VOTE_COUNT,
    min_year: int = MIN_YEAR,
    max_year: int = MAX_YEAR,
) -> tuple[pd.DataFrame, dict]:
    headers = pd.read_csv(source_path, nrows=0).columns.tolist()
    required = [
        COLUMNS["id"], COLUMNS["title"], COLUMNS["year"], COLUMNS["genre"],
        COLUMNS["region_raw"], COLUMNS["language_raw"], COLUMNS["rating"],
        COLUMNS["votes"],
    ]
    missing = [column for column in required if column not in headers]
    if missing:
        raise ValueError(f"Source dataset is missing required columns: {missing}")

    selected_columns = [column for column in COLUMNS.values() if column in headers]
    # 新增：传递 delivery 合并数据的额外列（如果源文件有这些列）
    for col in DELIVERY_PASSTHROUGH_COLUMNS:
        if col in headers and col not in selected_columns:
            selected_columns.append(col)
    chunks: list[pd.DataFrame] = []
    stages = {
        "source_rows": 0,
        "valid_title_year_rating": 0,
        "minimum_vote_count": 0,
    }

    for chunk in pd.read_csv(
        source_path,
        usecols=selected_columns,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        dtype={COLUMNS["id"]: "string"},
    ):
        stages["source_rows"] += len(chunk)
        title = chunk[COLUMNS["title"]].fillna("").astype(str).str.strip()
        year = pd.to_numeric(
            chunk[COLUMNS["year"]].astype(str).str.extract(r"(\d{4})", expand=False),
            errors="coerce",
        )
        rating = pd.to_numeric(chunk[COLUMNS["rating"]], errors="coerce")
        votes = pd.to_numeric(chunk[COLUMNS["votes"]], errors="coerce")

        valid = (
            title.ne("")
            & year.between(min_year, max_year)
            & rating.gt(0)
            & rating.le(10)
        )
        stages["valid_title_year_rating"] += int(valid.sum())
        eligible = valid & votes.ge(min_votes)
        stages["minimum_vote_count"] += int(eligible.sum())
        if not eligible.any():
            continue

        selected = chunk.loc[eligible].copy()
        selected[COLUMNS["title"]] = title.loc[eligible]
        selected[COLUMNS["year"]] = year.loc[eligible].astype(int)
        selected[COLUMNS["rating"]] = rating.loc[eligible].astype(float)
        selected[COLUMNS["votes"]] = votes.loc[eligible].astype(int)
        for column in COLUMNS.values():
            if column not in selected:
                selected[column] = ""
        # 新增：确保 delivery 传递列存在（即使为空）
        for col in DELIVERY_PASSTHROUGH_COLUMNS:
            if col not in selected:
                selected[col] = ""
        chunks.append(selected)

    if not chunks:
        raise ValueError("No records satisfy the publication criteria")

    sample = pd.concat(chunks, ignore_index=True)
    before_deduplication = len(sample)
    sample, deduplication = deduplicate_publication_records(sample)
    stages["deduplicated_records"] = len(sample)
    stages.update(deduplication)
    if stages["duplicates_removed"] != before_deduplication - len(sample):
        raise AssertionError("Deduplication stage counts do not reconcile")

    sample["Decade"] = sample[COLUMNS["year"]].map(categorize_decade)
    sample["Region"] = sample[COLUMNS["region_raw"]].map(categorize_region)
    sample["Language_Category"] = sample[COLUMNS["language_raw"]].map(categorize_language)
    sample["Region_Code"] = sample["Region"].map(REGION_CODES).astype(int)
    sample["Genre_Code"] = sample[COLUMNS["genre"]].map(genre_code).astype(int)
    language_pairs = [
        language_code(lang, region)
        for lang, region in zip(sample[COLUMNS["language_raw"]], sample["Region"])
    ]
    sample["Language_Code"] = [pair[0] for pair in language_pairs]
    sample["Is_Dialect"] = [pair[1] for pair in language_pairs]

    sample = sample.sort_values(
        [COLUMNS["year"], COLUMNS["title"], COLUMNS["id"]],
        kind="stable",
    ).reset_index(drop=True)
    sample = sample[OUTPUT_COLUMNS]

    fingerprint = publication_fingerprint(sample)
    generated_at = datetime.now(timezone.utc).isoformat()
    if SAMPLE_MANIFEST.is_file():
        try:
            previous = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
            if previous.get("sample_fingerprint_sha256") == fingerprint:
                generated_at = previous.get("generated_at", generated_at)
        except (OSError, json.JSONDecodeError, TypeError, AttributeError):
            pass
    repo_root = Path(__file__).resolve().parent.parent
    source_display = manifest_source_display(source_path, repo_root)
    manifest = {
        "schema_version": 2,
        "generated_at": generated_at,
        "source": source_display,
        "source_bytes": source_path.stat().st_size,
        "inclusion_criteria": {
            "minimum_vote_count": min_votes,
            "year_range": [min_year, max_year],
            "rating_range": {"minimum_exclusive": 0, "maximum_inclusive": 10},
            "requires_title": True,
            "deduplication_key": ["canonical Douban subject URL", "normalized title", COLUMNS["year"]],
            "region_rule": "first listed production country/region",
        },
        "stages": stages,
        "publication_records": len(sample),
        "sample_fingerprint_sha256": fingerprint,
        "counts": {
            "decade": sample["Decade"].value_counts().sort_index().to_dict(),
            "region": sample["Region"].value_counts().sort_index().to_dict(),
            "language": sample["Language_Category"].value_counts().sort_index().to_dict(),
            "source": sample[COLUMNS["source"]].fillna("Unknown").value_counts().sort_index().to_dict(),
        },
    }
    return sample, manifest


def parse_args() -> argparse.Namespace:
    # 默认使用合并后的数据（如果存在），否则使用原始数据
    default_source = SOURCE_MOVIES_MERGED if SOURCE_MOVIES_MERGED.exists() else SOURCE_MOVIES_INFO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=default_source)
    parser.add_argument("--output", type=Path, default=DERIVED_MOVIES_INFO)
    parser.add_argument("--manifest", type=Path, default=SAMPLE_MANIFEST)
    parser.add_argument("--min-votes", type=int, default=MIN_VOTE_COUNT)
    parser.add_argument("--min-year", type=int, default=MIN_YEAR)
    parser.add_argument("--max-year", type=int, default=MAX_YEAR)
    parser.add_argument(
        "--overwrite-tier2b",
        action="store_true",
        help="允许覆盖 v4.1 Tier 2b 重分类（默认拒绝；重跑后需再跑 apply_tier2b_reclassify_20260815.py 补回）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # v4.1 守卫（2026-08-15）：既有输出若已含 Dialect_Evidence 列，说明 Tier 2b
    # 证据审查重分类已落地；build_publication_sample 会用 language_code() 重算
    # Is_Dialect/Language_Code 而撤销该重分类，默认拒绝重跑。
    if args.output.exists() and not args.overwrite_tier2b:
        try:
            existing_header = pd.read_csv(args.output, nrows=0, encoding="utf-8-sig")
            if "Dialect_Evidence" in existing_header.columns:
                raise SystemExit(
                    f"{args.output} 已含 Dialect_Evidence 列（v4.1 Tier 2b 重分类已落地）。\n"
                    "重跑本脚本会撤销该重分类；如确需重建，请加 --overwrite-tier2b，\n"
                    "并在重建后运行 python scripts/replay_v44_baseline.py 重放全部手工补丁。"
                )
        except FileNotFoundError:
            pass
    sample, manifest = build_publication_sample(
        args.source,
        min_votes=args.min_votes,
        min_year=args.min_year,
        max_year=args.max_year,
    )
    atomic_write_csv(sample, args.output)
    atomic_write_json(manifest, args.manifest)
    print(
        f"Published {len(sample):,} records from {manifest['stages']['source_rows']:,} "
        f"source rows (minimum votes: {args.min_votes:,})."
    )
    print(f"Derived dataset: {args.output}")
    print(f"Sample manifest: {args.manifest}")


if __name__ == "__main__":
    main()
