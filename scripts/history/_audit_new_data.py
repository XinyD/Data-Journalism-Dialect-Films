"""Audit the delivery_20260817 new data (9,541 records) in the merged dataset.

Checks:
1. Region coding: all values in valid set
2. Language_Category: all values in valid set
3. Audit exclude list: 22 known movie_ids not present as D1
4. 朝鲜语 ambiguity: no North Korean films misclassified as China dialect
5. Foreign-first tags (方案A): no foreign-first language films counted as dialect
6. Source distribution: verify delivery_20260817 records count
7. Language tag scan: look for unusual/suspicious tags in new data
"""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO
from dialect_defs import (
    has_strict_dialect_tag, first_tag_is_foreign, has_mandarin_tag,
    DIALECT_AUDIT_EXCLUDE_MOVIE_IDS,
)

CSV = DERIVED_MOVIES_INFO

def main():
    df = pd.read_csv(CSV, encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
    print(f"Total rows: {len(df)}")

    # Source distribution
    print("\n=== Source Distribution ===")
    src_counts = df["数据来源"].fillna("Unknown").value_counts()
    for src, ct in src_counts.items():
        print(f"  {src}: {ct}")

    delivery_mask = df["数据来源"].str.contains("delivery", na=False)
    delivery = df[delivery_mask]
    print(f"\nDelivery records: {len(delivery)}")

    # 1. Region coding
    print("\n=== Region Coding ===")
    valid_regions = {"China", "North_America", "Europe", "East_Asia", "Other"}
    actual_regions = set(df["Region"].unique())
    invalid_regions = actual_regions - valid_regions
    print(f"  Actual regions: {actual_regions}")
    print(f"  Invalid regions: {invalid_regions if invalid_regions else 'NONE (OK)'}")
    for r in sorted(actual_regions):
        ct = int((df["Region"] == r).sum())
        print(f"  {r}: {ct}")

    # 2. Language_Category
    print("\n=== Language_Category ===")
    valid_lang_cats = {"Chinese", "English", "European_Languages", "Japanese_Korean", "Other"}
    actual_cats = set(df["Language_Category"].unique())
    invalid_cats = actual_cats - valid_lang_cats
    print(f"  Actual: {actual_cats}")
    print(f"  Invalid: {invalid_cats if invalid_cats else 'NONE (OK)'}")

    # 3. Audit exclude list
    print("\n=== Audit Exclude List ===")
    exclude_ids = DIALECT_AUDIT_EXCLUDE_MOVIE_IDS
    print(f"  Exclude list size: {len(exclude_ids)}")
    in_df = [mid for mid in exclude_ids if mid in df["movie_id"].values]
    in_d1 = [mid for mid in in_df if df.loc[df["movie_id"] == mid, "Is_Dialect"].iloc[0] == 1]
    print(f"  In dataset: {len(in_df)}")
    print(f"  In D1 (should be 0): {len(in_d1)}")
    if in_d1:
        for mid in in_d1:
            row = df[df["movie_id"] == mid].iloc[0]
            print(f"    VIOLATION: {mid} {row['片名']} Is_Dialect=1")

    # 4. 朝鲜语 check
    print("\n=== 朝鲜语 Ambiguity Check ===")
    lang_col = df["语言"].fillna("").astype(str)
    korean_mask = lang_col.str.contains("朝鲜语|조선어", na=False)
    korean_films = df[korean_mask]
    print(f"  Films with 朝鲜语/조선어: {len(korean_films)}")
    for _, r in korean_films.iterrows():
        region = r["Region"]
        is_d = int(r["Is_Dialect"])
        print(f"    {r['movie_id']} {r['片名']} Region={region} Is_Dialect={is_d} Lang={r['语言']}")
        if region == "China" and is_d == 1:
            print(f"    ⚠️ POTENTIAL ISSUE: 朝鲜语 + China + D1")

    # 5. 方案A: foreign-first tags
    print("\n=== 方案A Foreign-First Check ===")
    china = df[df["Region"] == "China"]
    china_d1 = china[china["Is_Dialect"] == 1]
    foreign_first_d1 = []
    for _, r in china_d1.iterrows():
        lang = str(r["语言"]) if pd.notna(r["语言"]) else ""
        if first_tag_is_foreign(lang):
            foreign_first_d1.append(r)
    print(f"  China D1 with foreign-first language: {len(foreign_first_d1)}")
    if foreign_first_d1:
        for r in foreign_first_d1[:5]:
            print(f"    VIOLATION: {r['movie_id']} {r['片名']} Lang={r['语言']}")

    # 6. Dialect_Evidence column check
    print("\n=== Dialect_Evidence Column ===")
    if "Dialect_Evidence" in df.columns:
        ev_counts = df["Dialect_Evidence"].fillna("").value_counts()
        print(f"  Column exists: YES")
        non_empty = int((df["Dialect_Evidence"].fillna("").astype(str).str.strip() != "").sum())
        excluded = int((df["Dialect_Evidence"] == "TIER2B_EXCLUDED").sum())
        evidence = non_empty - excluded
        print(f"  Non-empty: {non_empty} (evidence: {evidence}, excluded: {excluded})")
    else:
        print(f"  Column exists: NO (PROBLEM!)")

    # 7. Unusual language tags scan (China films)
    print("\n=== Unusual Language Tags (China D1) ===")
    china_d1_langs = china_d1["语言"].fillna("").astype(str).unique()
    # Look for tags that might be problematic
    suspicious_markers = ["韩语", "韓語", "korean", "日语", "日語", "japanese",
                          "英语", "英語", "english", "法语", "德"]
    for marker in suspicious_markers:
        matches = [l for l in china_d1_langs if marker in l.lower() or marker in l]
        if matches:
            print(f"  '{marker}' found in {len(matches)} unique lang tags:")
            for l in matches[:3]:
                ct = int((china_d1["语言"].fillna("").astype(str) == l).sum())
                print(f"    '{l}' ({ct} films)")

    # 8. Summary
    print("\n=== AUDIT SUMMARY ===")
    china_total = len(china)
    china_d0 = int((china["Is_Dialect"] == 0).sum())
    china_d1 = len(china_d1)
    print(f"  Total: {len(df)}")
    print(f"  China: {china_total} (D1={china_d1}, D0={china_d0})")
    print(f"  Region valid: {'OK' if not invalid_regions else 'FAIL'}")
    print(f"  Language_Category valid: {'OK' if not invalid_cats else 'FAIL'}")
    print(f"  Audit exclude: {'OK' if not in_d1 else 'FAIL'}")
    print(f"  Foreign-first in D1: {'OK' if not foreign_first_d1 else 'FAIL'}")
    print(f"  Dialect_Evidence: {'OK' if 'Dialect_Evidence' in df.columns else 'MISSING'}")

    issues = []
    if invalid_regions: issues.append("invalid regions")
    if invalid_cats: issues.append("invalid language categories")
    if in_d1: issues.append("audit exclude in D1")
    if foreign_first_d1: issues.append("foreign-first in D1")
    if "Dialect_Evidence" not in df.columns: issues.append("Dialect_Evidence missing")
    if issues:
        print(f"\n  ISSUES: {', '.join(issues)}")
    else:
        print(f"\n  ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
