# -*- coding: utf-8 -*-
"""Apply Douban language overrides for delivery_20260817 missing-language rows.

Reads data/cleaned/language_backfill_overrides.csv, writes 语言 back onto
derived_movies.csv, recomputes Language_Category / Language_Code / Is_Dialect,
and stamps Language_Provenance.

v4.1 alignment:
  Tier 1 / 2a → Is_Dialect=1, Dialect_Evidence=LANG_BACKFILL_20260830
  Tier 2b → default exclude (LANG_BACKFILL_TIER2B_EXCLUDED), not the 702 pool
  opera/audit exclude lists stay non-dialect
  protected LANG_FIX rows (阿嬷 / 隐入尘烟) are skipped
  remaining empty China language → 汉语普通话 + EMPTY_LANG_DEFAULTED

Usage:
  python scripts/apply_language_backfill_20260830.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    DERIVED_MOVIES_INFO,
    LANGUAGE_BACKFILL_OVERRIDES,
    SAMPLE_MANIFEST,
)
from data_processor import (  # noqa: E402
    categorize_language,
    language_code,
    non_dialect_language_code,
    publication_fingerprint,
    atomic_write_csv,
    atomic_write_json,
)
from dialect_defs import (  # noqa: E402
    DIALECT_AUDIT_EXCLUDE_MOVIE_IDS,
    OPERA_CONCERT_EXCLUDE_MOVIE_IDS,
    first_tag_is_foreign,
    has_mandarin_tag,
    has_strict_dialect_tag,
)
from freeze_constants import PUBLICATION_RECORDS  # noqa: E402
from gen_report_strict import classify_strict  # noqa: E402
from language_backfill_lib import (  # noqa: E402
    DELIVERY_SOURCE,
    is_empty_language,
    is_protected_language_row,
)

TODAY = "2026-08-30"
EVIDENCE_DIALECT = "LANG_BACKFILL_20260830"
EVIDENCE_TIER2B = "LANG_BACKFILL_TIER2B_EXCLUDED"
EVIDENCE_DEFAULTED = "EMPTY_LANG_DEFAULTED"
EXCLUDE_IDS = DIALECT_AUDIT_EXCLUDE_MOVIE_IDS | OPERA_CONCERT_EXCLUDE_MOVIE_IDS


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def assign_baseline_provenance(frame: pd.DataFrame) -> pd.Series:
    langs = frame["语言"].map(_text).str.strip()
    empty = langs.map(is_empty_language)
    source = frame["数据来源"].fillna("").astype(str)
    protected = frame.apply(is_protected_language_row, axis=1)
    provenance = pd.Series("douban_observed", index=frame.index)
    provenance[empty] = "empty"
    delivery = source.eq(DELIVERY_SOURCE)
    provenance[delivery & langs.eq("汉语普通话") & ~protected] = "empty_default_mandarin"
    provenance[delivery & empty] = "empty"
    return provenance


def apply_language_row(frame: pd.DataFrame, index: int, lang: str, provenance: str) -> str:
    """Write language + derived fields. Returns a change tag."""
    mid = str(frame.at[index, "movie_id"])
    region = frame.at[index, "Region"]
    frame.at[index, "语言"] = lang
    frame.at[index, "Language_Category"] = categorize_language(lang)
    frame.at[index, "Language_Provenance"] = provenance

    if mid in EXCLUDE_IDS:
        lc, _ = language_code(lang, region=region)
        if has_strict_dialect_tag(lang):
            lc = non_dialect_language_code(lang)
        frame.at[index, "Language_Code"] = lc
        frame.at[index, "Is_Dialect"] = 0
        return "excluded_list"

    # Wikidata P364 is a language-gap filler, not Douban 语言. Never mint dialect.
    if provenance == "wikidata":
        lc, is_dia = language_code(lang, region=region)
        if is_dia:
            lc = non_dialect_language_code(lang)
        frame.at[index, "Language_Code"] = lc
        frame.at[index, "Is_Dialect"] = 0
        return "language_only"

    info = classify_strict({
        "语言": lang,
        "movie_id": mid,
        "Dialect_Evidence": "",
        "Region": region,
    })
    if info["is_dialect"] == 1:
        frame.at[index, "Language_Code"] = 3
        frame.at[index, "Is_Dialect"] = 1
        frame.at[index, "Dialect_Evidence"] = EVIDENCE_DIALECT
        return f"dialect:{info['tier']}"

    dialect_tagged = has_strict_dialect_tag(lang)
    mandarin_first_mix = (
        dialect_tagged
        and has_mandarin_tag(lang)
        and not first_tag_is_foreign(lang)
        and region == "China"
    )
    if mandarin_first_mix:
        frame.at[index, "Language_Code"] = non_dialect_language_code(lang)
        frame.at[index, "Is_Dialect"] = 0
        frame.at[index, "Dialect_Evidence"] = EVIDENCE_TIER2B
        return "tier2b_excluded"

    lc, is_dia = language_code(lang, region=region)
    frame.at[index, "Language_Code"] = lc
    frame.at[index, "Is_Dialect"] = is_dia
    return "language_only"


def main() -> None:
    if not LANGUAGE_BACKFILL_OVERRIDES.is_file():
        raise SystemExit(
            f"Missing {LANGUAGE_BACKFILL_OVERRIDES}. "
            "Run list_untrusted_languages.py then fetch_douban_languages.py."
        )
    overrides = pd.read_csv(
        LANGUAGE_BACKFILL_OVERRIDES,
        encoding="utf-8-sig",
        dtype={"movie_id": "str"},
    )
    overrides["movie_id"] = overrides["movie_id"].astype(str)
    overrides["语言"] = overrides["语言"].fillna("").astype(str).str.strip()
    overrides = overrides[overrides["语言"] != ""].drop_duplicates("movie_id", keep="last")

    df = pd.read_csv(
        DERIVED_MOVIES_INFO,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={"movie_id": "str"},
    )
    assert len(df) == PUBLICATION_RECORDS, f"rows {len(df)} != {PUBLICATION_RECORDS}"
    if "Dialect_Evidence" not in df.columns:
        df["Dialect_Evidence"] = ""
    df["Dialect_Evidence"] = df["Dialect_Evidence"].fillna("").astype(str)
    if "Language_Provenance" not in df.columns:
        df["Language_Provenance"] = assign_baseline_provenance(df)
    else:
        missing = df["Language_Provenance"].isna() | (df["Language_Provenance"].astype(str).str.strip() == "")
        if missing.any():
            baseline = assign_baseline_provenance(df)
            df.loc[missing, "Language_Provenance"] = baseline.loc[missing]

    id_to_index = {str(mid): idx for idx, mid in zip(df.index, df["movie_id"].astype(str))}
    stats = {
        "overrides_in_file": int(len(overrides)),
        "applied": 0,
        "skipped_missing_id": 0,
        "skipped_protected": 0,
        "dialect_tier1_2a": 0,
        "tier2b_excluded": 0,
        "excluded_list": 0,
        "language_only": 0,
        "unchanged": 0,
        "skipped_wikidata_china_dialect": 0,
    }
    for rec in overrides.to_dict("records"):
        mid = str(rec["movie_id"])
        lang = rec["语言"]
        idx = id_to_index.get(mid)
        if idx is None:
            stats["skipped_missing_id"] += 1
            continue
        if is_protected_language_row(df.loc[idx]):
            stats["skipped_protected"] += 1
            continue
        old_lang = _text(df.at[idx, "语言"]).strip()
        source = str(rec.get("source", "") or "").strip()
        if source == "wikidata_p364":
            provenance = "wikidata"
            # SSOT: dialect membership is Douban 语言 only. Wikidata P364 may
            # fill Language_Code=5 gaps, but must not mint China dialect rows.
            if df.at[idx, "Region"] == "China" and has_strict_dialect_tag(lang):
                stats["skipped_wikidata_china_dialect"] += 1
                continue
        elif source:
            provenance = "douban_backfill"
        else:
            provenance = "douban_backfill"
        tag = apply_language_row(df, idx, lang, provenance)
        stats["applied"] += 1
        if old_lang == lang and tag == "language_only":
            stats["unchanged"] += 1
        elif tag.startswith("dialect:"):
            stats["dialect_tier1_2a"] += 1
        elif tag == "tier2b_excluded":
            stats["tier2b_excluded"] += 1
        elif tag == "excluded_list":
            stats["excluded_list"] += 1
        else:
            stats["language_only"] += 1

    # Remaining empty China language: keep the v4.1.1 default, but stamp it.
    langs = df["语言"].map(_text)
    empty_china = (df["Region"] == "China") & langs.map(is_empty_language)
    defaulted = 0
    for idx in df.index[empty_china]:
        if is_protected_language_row(df.loc[idx]):
            continue
        df.at[idx, "语言"] = "汉语普通话"
        df.at[idx, "Language_Category"] = categorize_language("汉语普通话")
        lc, is_dia = language_code("汉语普通话", region="China")
        df.at[idx, "Language_Code"] = lc
        df.at[idx, "Is_Dialect"] = is_dia
        df.at[idx, "Language_Provenance"] = "empty_default_mandarin"
        evidence = _text(df.at[idx, "Dialect_Evidence"]).strip()
        if evidence == "":
            df.at[idx, "Dialect_Evidence"] = EVIDENCE_DEFAULTED
        defaulted += 1
    stats["china_empty_defaulted"] = defaulted

    # Delivery China still on the synthetic default (fetch failed / not in overrides).
    delivery_china_default = (
        (df["数据来源"] == DELIVERY_SOURCE)
        & (df["Region"] == "China")
        & (df["语言"].map(_text).str.strip() == "汉语普通话")
        & (df["Language_Provenance"].astype(str) == "empty_default_mandarin")
    )
    stamped = 0
    for idx in df.index[delivery_china_default]:
        if is_protected_language_row(df.loc[idx]):
            continue
        evidence = _text(df.at[idx, "Dialect_Evidence"]).strip()
        if evidence == "":
            df.at[idx, "Dialect_Evidence"] = EVIDENCE_DEFAULTED
            stamped += 1
    stats["delivery_china_default_stamped"] = stamped

    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    assert code2 == ch_d0 and code3 == d1, (
        f"Language_Code / Is_Dialect invariant broken: code2={code2} ch_d0={ch_d0} code3={code3} d1={d1}"
    )

    china = df[df["Region"] == "China"]
    empty_after = int(china["语言"].map(_text).map(is_empty_language).sum())
    assert empty_after == 0, f"Still {empty_after} empty-language China films"
    stats["china_dialect_after"] = int(china["Is_Dialect"].sum())
    stats["china_mandarin_after"] = int((china["Is_Dialect"] == 0).sum())
    stats["china_total_after"] = int(len(china))

    atomic_write_csv(df, DERIVED_MOVIES_INFO)
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["counts"]["language"] = df["Language_Category"].value_counts().sort_index().to_dict()
    manifest["language_backfill_20260830"] = {
        "applied_by": "scripts/apply_language_backfill_20260830.py",
        "rule": "Douban subject-page 语言 backfill for delivery_20260817 missing column; "
                "Tier 2b new hits default-excluded; remaining empty China stamped "
                "EMPTY_LANG_DEFAULTED rather than treated as observed Mandarin",
        "date": TODAY,
        "overrides_file": LANGUAGE_BACKFILL_OVERRIDES.name,
        **stats,
    }
    atomic_write_json(manifest, SAMPLE_MANIFEST)
    print("Applied language backfill:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"China D1={stats['china_dialect_after']} D0={stats['china_mandarin_after']}")
    print(f"Fingerprint: {fp}")


if __name__ == "__main__":
    main()
