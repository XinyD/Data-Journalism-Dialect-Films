"""Replay the v4.4 idempotent patch chain after a from-source rebuild.

`data_processor.py` drops `Dialect_Evidence` (it is not in OUTPUT_COLUMNS) and
recomputes Is_Dialect from language tags, which undoes every manual correction.
This script reapplies the published patches in documented order
(v4.4 six-step chain plus v4.5 first-listed region plus v4.6/v4.7 language
backfill plus the 2026-08-30 隐入尘烟 and 椒麻堂会 language fixes) and asserts
the frozen end state.

Dialect_Evidence is maintained by this chain, not by data_processor.

Usage:
  python scripts/replay_v44_baseline.py
  python scripts/replay_v44_baseline.py --full-rebuild --source path/to/movies_info.csv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from config import DERIVED_MOVIES_INFO, SOURCE_MOVIES_MERGED, SOURCE_MOVIES_INFO  # noqa: E402
from dialect_defs import DIALECT_AUDIT_EXCLUDE_MOVIE_IDS, first_tag_is_foreign, has_strict_dialect_tag  # noqa: E402
from freeze_constants import (  # noqa: E402
    AUDIT_EXCLUDED,
    CHINA_DIALECT,
    CHINA_TOTAL,
    OPERA_CONCERT_EXCLUDED,
    PLAN_A_EXCLUDED,
    PUBLICATION_RECORDS,
    TIER2B_EXCLUDED,
    TIER_BASELINE,
)

PATCH_SCRIPTS = (
    ("apply_tier2b_reclassify_20260815.py", []),
    ("apply_empty_lang_backfill_20260818.py", []),
    ("apply_language_backfill_20260830.py", []),
    ("apply_audit_exclude_20260818.py", []),
    ("apply_f7_region_fix_20260818.py", ["--apply"]),
    ("apply_opera_concert_exclude_20260818.py", []),
    ("apply_ama_lang_fix_20260819.py", []),
    ("apply_yinruchenyan_lang_fix_20260830.py", []),
    ("apply_jiaoma_leshan_lang_fix_20260830.py", []),
    ("apply_first_listed_region_20260824.py", []),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Run data_processor.py --overwrite-tier2b from --source before replaying patches.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Upstream movies_info.csv for --full-rebuild. Defaults to merged then original source.",
    )
    parser.add_argument(
        "--skip-publication-rebuild",
        action="store_true",
        help="After --full-rebuild + patches, do not run rebuild.py.",
    )
    return parser.parse_args()


def run(script: str, *arguments: str) -> None:
    command = [sys.executable, str(SCRIPTS / script), *arguments]
    print(f"\n> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def assert_end_state() -> None:
    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
    assert len(df) == PUBLICATION_RECORDS, f"rows {len(df)} != {PUBLICATION_RECORDS}"

    china = df[df["Region"] == "China"]
    assert len(china) == CHINA_TOTAL, f"China rows {len(china)} != {CHINA_TOTAL}"
    lang = china["语言"].fillna("").astype(str)
    empty = china[lang.str.strip() == ""]
    assert len(empty) == 0, f"empty-language China films: {len(empty)}"

    from gen_report_strict import classify_strict

    summary = {"tier1_pure": 0, "tier2a_dialect_first": 0, "tier2b_mandarin_first": 0, "total_dialect": 0}
    for rec in china.to_dict("records"):
        info = classify_strict(rec)
        if not info["is_dialect"]:
            continue
        summary["total_dialect"] += 1
        if info["tier"] == "Tier 1":
            summary["tier1_pure"] += 1
        elif info["tier"] == "Tier 2a":
            summary["tier2a_dialect_first"] += 1
        elif info["tier"] == "Tier 2b":
            summary["tier2b_mandarin_first"] += 1

    csv_d1 = int(china["Is_Dialect"].sum())
    actual = (
        csv_d1,
        summary["tier1_pure"],
        summary["tier2a_dialect_first"],
        summary["tier2b_mandarin_first"],
    )
    assert csv_d1 == summary["total_dialect"], (
        f"CSV Is_Dialect ({csv_d1}) != classify_strict ({summary['total_dialect']})"
    )
    assert actual == TIER_BASELINE, f"Tier baseline {actual} != {TIER_BASELINE}"

    excluded = df[df["Dialect_Evidence"].fillna("") == "TIER2B_EXCLUDED"]
    assert len(excluded) == TIER2B_EXCLUDED, f"TIER2B_EXCLUDED {len(excluded)} != {TIER2B_EXCLUDED}"
    assert int(excluded["Is_Dialect"].sum()) == 0

    plan_a = china[lang.map(has_strict_dialect_tag) & lang.map(first_tag_is_foreign)]
    assert len(plan_a) == PLAN_A_EXCLUDED, f"plan A {len(plan_a)} != {PLAN_A_EXCLUDED}"

    audit_hits = df[df["movie_id"].isin(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS) & (df["Is_Dialect"] == 1)]
    assert len(audit_hits) == 0, f"audit exclude still dialect: {len(audit_hits)}"

    from dialect_defs import OPERA_CONCERT_EXCLUDE_MOVIE_IDS

    opera_hits = df[df["movie_id"].isin(OPERA_CONCERT_EXCLUDE_MOVIE_IDS) & (df["Is_Dialect"] == 1)]
    assert len(opera_hits) == 0, f"opera exclude still dialect: {len(opera_hits)}"
    assert len(OPERA_CONCERT_EXCLUDE_MOVIE_IDS) == OPERA_CONCERT_EXCLUDED
    assert len(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS) == AUDIT_EXCLUDED

    print(
        f"[OK] v4.7 baseline: China n={len(china)} D1={actual[0]} "
        f"tiers={actual[1:]}, TIER2B_EXCLUDED={TIER2B_EXCLUDED}, "
        f"opera={OPERA_CONCERT_EXCLUDED}, audit={AUDIT_EXCLUDED}, plan_a={PLAN_A_EXCLUDED}"
    )


def main() -> None:
    args = parse_args()
    if args.full_rebuild:
        source = (args.source or (SOURCE_MOVIES_MERGED if SOURCE_MOVIES_MERGED.exists() else SOURCE_MOVIES_INFO))
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Upstream source not found: {source}")
        run("data_processor.py", "--source", str(source), "--overwrite-tier2b")

    for script, extra in PATCH_SCRIPTS:
        run(script, *extra)

    assert_end_state()

    if args.full_rebuild and not args.skip_publication_rebuild:
        command = [sys.executable, str(ROOT / "rebuild.py")]
        print(f"\n> {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
