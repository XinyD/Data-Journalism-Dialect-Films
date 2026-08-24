"""Recompute Region from the first listed production country (v4.5).

Fixes space-separated delivery_20260817 country lists that previously failed
`first_listed_value` slash splitting, and adds 西德/东德 to Europe. Re-applies
the F7 平壤之约 override afterwards.

Does not touch Is_Dialect / Dialect_Evidence. Idempotent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import (  # noqa: E402
    REGION_CODES,
    atomic_write_csv,
    atomic_write_json,
    categorize_region,
    publication_fingerprint,
)
from freeze_constants import F7_PYONGYANG_MOVIE_ID, PUBLICATION_RECORDS  # noqa: E402


def main() -> None:
    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
    assert len(df) == PUBLICATION_RECORDS, f"rows {len(df)} != {PUBLICATION_RECORDS}"

    previous = df["Region"].astype(str)
    df["Region"] = df["制片国家/地区"].map(categorize_region)
    f7 = df["movie_id"] == F7_PYONGYANG_MOVIE_ID
    if int(f7.sum()) != 1:
        raise SystemExit(f"F7 movie {F7_PYONGYANG_MOVIE_ID} found {int(f7.sum())} times")
    df.loc[f7, "Region"] = "East_Asia"
    assert int(df.loc[f7, "Is_Dialect"].iloc[0]) == 0, "平壤之约应为非方言片"
    df["Region_Code"] = df["Region"].map(REGION_CODES)

    changed = int((previous != df["Region"].astype(str)).sum())
    print(f"Region recategorized: {changed} rows changed")
    print("Region counts:")
    print(df["Region"].value_counts().sort_index().to_string())

    china = df[df["Region"] == "China"]
    print(f"China D1={int(china['Is_Dialect'].sum())} D0={int((china['Is_Dialect']==0).sum())} n={len(china)}")

    atomic_write_csv(df, DERIVED_MOVIES_INFO)
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["counts"]["region"] = df["Region"].value_counts().sort_index().to_dict()
    manifest["first_listed_region_20260824"] = {
        "applied_by": "scripts/apply_first_listed_region_20260824.py",
        "rows_changed": changed,
        "rule": "first listed country; CJK space-separated lists split; 西德/东德 → Europe; F7 平壤之约 stays East_Asia",
    }
    atomic_write_json(manifest, SAMPLE_MANIFEST)
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    import re
    match = re.search(r"当前发布指纹：\s+```text\s+([0-9a-f]{64})", text)
    if match and match.group(1) != fp:
        text = text.replace(match.group(1), fp)
        readme.write_text(text, encoding="utf-8")
        print("README fingerprint updated")
    print(f"Wrote fingerprint {fp}")


if __name__ == "__main__":
    main()
