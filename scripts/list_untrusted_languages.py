# -*- coding: utf-8 -*-
"""List publication rows whose Douban language field is missing or untrusted.

delivery_20260817 had no language column; China empties were defaulted to
汉语普通话 and non-China empties stayed blank. This script writes the
candidate table for fetch_douban_languages.py (no network).

Usage:
  python scripts/list_untrusted_languages.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, LANGUAGE_BACKFILL_CANDIDATES  # noqa: E402
from language_backfill_lib import candidate_reason, subject_url  # noqa: E402

OUTPUT_COLUMNS = (
    "movie_id",
    "片名",
    "年份",
    "Region",
    "语言",
    "数据来源",
    "来源URL",
    "reason",
)


def build_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rec in frame.to_dict("records"):
        series = pd.Series(rec)
        reason = candidate_reason(series)
        if not reason:
            continue
        rows.append({
            "movie_id": str(rec.get("movie_id", "") or ""),
            "片名": rec.get("片名", ""),
            "年份": rec.get("年份", ""),
            "Region": rec.get("Region", ""),
            "语言": "" if pd.isna(rec.get("语言")) else rec.get("语言"),
            "数据来源": rec.get("数据来源", ""),
            "来源URL": subject_url(series),
            "reason": reason,
        })
    out = pd.DataFrame(rows, columns=list(OUTPUT_COLUMNS))
    if len(out):
        out = out.sort_values(["reason", "Region", "年份", "movie_id"], kind="stable")
    return out.reset_index(drop=True)


def main() -> None:
    df = pd.read_csv(
        DERIVED_MOVIES_INFO,
        encoding="utf-8-sig",
        low_memory=False,
        dtype={"movie_id": "str"},
    )
    candidates = build_candidates(df)
    LANGUAGE_BACKFILL_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(LANGUAGE_BACKFILL_CANDIDATES, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(candidates):,} candidates -> {LANGUAGE_BACKFILL_CANDIDATES}")
    if len(candidates):
        print(candidates["reason"].value_counts().to_string())
        print("Region x reason:")
        print(pd.crosstab(candidates["Region"], candidates["reason"]).to_string())


if __name__ == "__main__":
    main()
