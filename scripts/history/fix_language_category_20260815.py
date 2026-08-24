# -*- coding: utf-8 -*-
"""
2026-08-15 审计补丁二：修复 Language_Category 漏收"国语/國語"异形。

CHINESE_LANGUAGE_MARKERS 原缺"国语/國語"，导致 23 部仅标"国语"的影片
Language_Category 落到 Other/English，与 Language_Code==2（普通话）不一致，
也使 narrative_facts.languages["普通话"]（Chinese类且非方言）与 CSV 对不齐。
本脚本用修正后的 categorize_language 全量重算 Language_Category 并落盘。

用法：python scripts/fix_language_category_20260815.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from data_processor import atomic_write_csv, categorize_language  # noqa: E402

CSV = ROOT / "data" / "derived_movies.csv"
EXPECTED_TOTAL = 53_467
EXPECTED_CHANGED = 23


def main() -> None:
    df = pd.read_csv(CSV, low_memory=False)
    assert len(df) == EXPECTED_TOTAL, f"总行数 {len(df)} != {EXPECTED_TOTAL}"

    new_cat = df["语言"].map(categorize_language)
    changed = df[new_cat != df["Language_Category"]]
    print(f"Language_Category 变化影片: {len(changed)} 部")
    assert len(changed) == EXPECTED_CHANGED, f"变化数 {len(changed)} != {EXPECTED_CHANGED}"
    for _, r in changed.iterrows():
        line = f"  {r['片名']} ({r['年份']}) Region={r['Region']} {r['Language_Category']}->{new_cat.loc[r.name]} lang={r['语言']}"
        print(line)
    assert (new_cat[changed.index] == "Chinese").all(), "变化目标类别应为 Chinese"

    df["Language_Category"] = new_cat
    atomic_write_csv(df, CSV)
    print(f"\n已写回 {CSV}")
    print("language counts:", df["Language_Category"].value_counts().sort_index().to_dict())

    # 一致性复核：code2 == Chinese类&D0，code3 == D1
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    print(f"复核: code2={code2} Chinese&D0={ch_d0} code3={code3} D1={d1}")
    assert code2 == ch_d0 and code3 == d1


if __name__ == "__main__":
    main()
