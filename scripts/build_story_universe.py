"""Build story_universe.json for ch13/ch14 finale previews."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST, STORY_UNIVERSE, atomic_write_text  # noqa: E402
from dialect_defs import lang_parts  # noqa: E402
from data_aggregator import (  # noqa: E402
    CHINESE_DIALECT_TAGS,
    DIRECTOR,
    MOVIE_ID,
    ORIGINAL_LANGUAGES,
    RATING,
    TITLE,
    VOTES,
    YEAR,
)
from province_story_curator import (  # noqa: E402
    LANG_TO_PROVINCES,
    PENDING_STORY_LANGS,
    canonical_lang,
    get_provinces,
    language_meta,
)

MIN_LANG_COUNT = 1
TOP_FILMS_PER_LANG = 6
TOP_FILMS_PER_PROVINCE = 5
EXCLUDED_LANG_TAGS = {"方言"}
OUTPUT = STORY_UNIVERSE


def slugify(name: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name.strip().lower())
    return slug or "lang"


def film_record(row: pd.Series, lang: str) -> dict:
    return {
        "id": str(row[MOVIE_ID]),
        "title": str(row[TITLE]),
        "year": int(row[YEAR]) if pd.notna(row[YEAR]) else None,
        "rating": round(float(row[RATING]), 1) if pd.notna(row[RATING]) else None,
        "director": str(row[DIRECTOR]) if pd.notna(row[DIRECTOR]) else "未知",
        "lang": lang,
    }


def _language_record(tag: str, frame: pd.DataFrame, films: list[dict], status: str) -> dict:
    meta = language_meta(tag)
    mean = None
    if len(frame) and RATING in frame.columns:
        ratings = frame[RATING].astype(float)
        if len(ratings):
            mean = round(float(ratings.mean()), 2)
    return {
        "id": slugify(tag),
        "name": tag,
        "n": int(len(frame)),
        "mean": mean,
        "themes": meta["themes"],
        "language": meta["language"],
        "folk": meta["folk"],
        "history": meta["history"],
        "stories": meta["stories"],
        "academicName": meta.get("academicName", tag),
        "family": meta.get("family", ""),
        "aliases": meta.get("aliases") or [],
        "films": films,
        "status": status,
    }


def build_languages(dialect: pd.DataFrame) -> list[dict]:
    tag_rows: dict[str, list[pd.Series]] = defaultdict(list)
    for _, row in dialect.iterrows():
        lang_text = "" if pd.isna(row[ORIGINAL_LANGUAGES]) else str(row[ORIGINAL_LANGUAGES] or "")
        seen_canon: set[str] = set()
        for part in lang_parts(lang_text):
            if part in EXCLUDED_LANG_TAGS:
                continue
            if part not in CHINESE_DIALECT_TAGS:
                continue
            canon = canonical_lang(part)
            if canon in seen_canon:
                continue
            seen_canon.add(canon)
            tag_rows[canon].append(row)

    languages: list[dict] = []
    for tag, rows in sorted(tag_rows.items(), key=lambda item: (-len(item[1]), item[0])):
        if tag in EXCLUDED_LANG_TAGS:
            continue
        if len(rows) < MIN_LANG_COUNT:
            continue
        frame = pd.DataFrame(rows).drop_duplicates(subset=[MOVIE_ID])
        films_df = (
            frame.sort_values([RATING, VOTES], ascending=[False, False])
            .head(TOP_FILMS_PER_LANG)
        ) if len(frame) >= 2 else pd.DataFrame()
        films = [film_record(r, tag) for _, r in films_df.iterrows()]
        status = "developed" if len(films) >= 1 and len(frame) >= 2 else "pending"
        languages.append(_language_record(tag, frame, films, status))

    have = {item["name"] for item in languages}
    for name in PENDING_STORY_LANGS:
        if name in have:
            continue
        empty = pd.DataFrame(columns=[MOVIE_ID, RATING, VOTES, TITLE, YEAR, DIRECTOR])
        languages.append(_language_record(name, empty, [], "pending"))
    languages.sort(key=lambda item: (-(item["n"] or 0), item["name"]))
    return languages


def build_provinces(languages: list[dict]) -> list[dict]:
    province_films: dict[str, list[dict]] = defaultdict(list)
    province_langs: dict[str, set[str]] = defaultdict(set)

    for lang in languages:
        targets = LANG_TO_PROVINCES.get(lang["name"], [])
        for pid in targets:
            province_langs[pid].add(lang["name"])
            for film in lang["films"]:
                province_films[pid].append(film)

    result: list[dict] = []
    for base in get_provinces():
        pid = base["id"]
        merged_langs = sorted({
            canonical_lang(name)
            for name in (list(base.get("languages", [])) + list(province_langs.get(pid, set())))
        })
        films_map: dict[str, dict] = {}
        for film in province_films.get(pid, []):
            fid = film["id"]
            if fid not in films_map or (film.get("rating") or 0) > (films_map[fid].get("rating") or 0):
                films_map[fid] = film
        films = sorted(films_map.values(), key=lambda f: (-(f.get("rating") or 0), f.get("title", "")))[:TOP_FILMS_PER_PROVINCE]
        pending = list(base.get("pending", []))
        if not films:
            pending = pending or ["更多地方故事待开发"]
        result.append({
            **base,
            "languages": merged_langs,
            "films": films,
            "pending": pending,
            "filmCount": len(films_map),
        })
    return result


def main() -> None:
    frame = pd.read_csv(DERIVED_MOVIES_INFO, dtype={MOVIE_ID: "string"}, low_memory=False)
    dialect = frame[frame["Is_Dialect"] == 1].copy()
    languages = build_languages(dialect)
    provinces = build_provinces(languages)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    payload = {
        "meta": {
            "languageCount": len(languages),
            "provinceCount": len(provinces),
            "minLangCount": MIN_LANG_COUNT,
            "source": str(DERIVED_MOVIES_INFO.name),
            "sampleFingerprint": manifest["sample_fingerprint_sha256"],
        },
        "languages": languages,
        "provinces": provinces,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    atomic_write_text(OUTPUT, text)
    print(f"Wrote {len(languages)} languages and {len(provinces)} provinces to {OUTPUT}")


if __name__ == "__main__":
    main()
