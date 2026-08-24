"""Backfill empty-language China films for the 63,025-row dataset.

Re-applies the v4.1.1 dialect backfills (8 dialect + 1 revert + 4 nondialect fixes)
that were lost during the 2026-08-18 data rebuild, then defaults remaining
empty-language China films to "汉语普通话" (Is_Dialect=0).
"""
import json, shutil, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST
from data_processor import categorize_language, language_code, publication_fingerprint
from dialect_defs import has_strict_dialect_tag, first_tag_is_foreign, has_mandarin_tag

CSV = DERIVED_MOVIES_INFO
BACKUP = ROOT / "data" / "derived_movies_empty_lang_backup_20260818.csv"

# ── 8 dialect films: restore language + Is_Dialect=1 ──
DIALECT_TAGS = {
    "4133310":  {"片名": "惊梦魂",         "lang": "粤语",                   "tier": "Tier 1"},
    "2129914":  {"片名": "八廓南街16号",    "lang": "藏语",                   "tier": "Tier 1"},
    "1308060":  {"片名": "龙的深处―失落的拼图", "lang": "粤语/安徽方言/国语",  "tier": "Tier 2a"},
    "10518931": {"片名": "猎人与骷髅怪",    "lang": "藏语",                   "tier": "Tier 1"},
    "19899635": {"片名": "穷人·榴莲·麻药·偷渡客", "lang": "云南方言/普通话/缅语", "tier": "Tier 2a"},
    "30441138": {"片名": "监狱建筑师",      "lang": "粤语",                   "tier": "Tier 1"},
    "34436895": {"片名": "出花园",          "lang": "潮汕方言",               "tier": "Tier 1"},
    "34847185": {"片名": "阿紫",            "lang": "闽南语/普通话",          "tier": "Tier 2a"},
}

# ── 1 revert: was dialect, should be Mandarin ──
REVERT = {
    "34953763": {"片名": "巴依尔的春节", "lang": "普通话"},
}

# ── 4 nondialect fixes ──
NONDIALECT_FIX = {
    "33425521": {"片名": "张学友1/2世纪世界巡回演唱会", "fix": "普通话"},
    "35376928": {"片名": "张敬轩x香港中乐团《盛乐》演唱会", "fix": "普通话"},
    "30253124": {"片名": "腐草为萤", "fix": "汉语普通话"},
    "30396250": {"片名": "公交车", "fix": "汉语普通话"},
}


def main():
    df = pd.read_csv(CSV, encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
    total = len(df)
    print(f"Total rows: {total}")

    # Backup
    if not BACKUP.exists():
        shutil.copy2(CSV, BACKUP)
        print(f"Backup -> {BACKUP.name}")

    changes = []
    china_mask = df["Region"] == "China"

    # 1. Dialect films
    print("\n--- Dialect films ---")
    for mid, info in DIALECT_TAGS.items():
        idx = df.index[df["movie_id"] == mid]
        if len(idx) != 1:
            print(f"  SKIP {info['片名']} ({mid}): found {len(idx)} rows")
            continue
        i = idx[0]
        old_lang = str(df.at[i, "语言"]) if pd.notna(df.at[i, "语言"]) else "(empty)"
        old_isd = int(df.at[i, "Is_Dialect"])

        df.at[i, "语言"] = info["lang"]
        df.at[i, "Language_Category"] = categorize_language(info["lang"])
        lc, is_dia = language_code(info["lang"], region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        # Clear Dialect_Evidence for newly added dialect films (they're Tier 1/2a, not Tier 2b)
        if df.at[i, "Dialect_Evidence"] == "TIER2B_EXCLUDED":
            df.at[i, "Dialect_Evidence"] = ""
        print(f"  {info['片名']:30s} | {old_lang:10s} -> {info['lang']:30s} | D {old_isd}->{is_dia}")
        changes.append(f"dialect:{mid}:{info['片名']}")

    # 2. Revert
    print("\n--- Revert dialect ---")
    for mid, info in REVERT.items():
        idx = df.index[df["movie_id"] == mid]
        if len(idx) != 1:
            print(f"  SKIP {info['片名']} ({mid}): found {len(idx)} rows")
            continue
        i = idx[0]
        old_lang = str(df.at[i, "语言"]) if pd.notna(df.at[i, "语言"]) else "(empty)"
        df.at[i, "语言"] = info["lang"]
        df.at[i, "Language_Category"] = categorize_language(info["lang"])
        lc, is_dia = language_code(info["lang"], region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = ""
        print(f"  {info['片名']:30s} | {old_lang:10s} -> {info['lang']:10s} | D {int(df.at[i, 'Is_Dialect'])}->{is_dia}")
        changes.append(f"revert:{mid}:{info['片名']}")

    # 3. Nondialect fixes
    print("\n--- Nondialect fixes ---")
    for mid, info in NONDIALECT_FIX.items():
        idx = df.index[df["movie_id"] == mid]
        if len(idx) != 1:
            print(f"  SKIP ({mid}): found {len(idx)} rows")
            continue
        i = idx[0]
        df.at[i, "语言"] = info["fix"]
        df.at[i, "Language_Category"] = categorize_language(info["fix"])
        lc, is_dia = language_code(info["fix"], region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        print(f"  {info['片名']:35s} -> {info['fix']:12s} | D=0")
        changes.append(f"nondialect_fix:{mid}:{info['片名']}")

    # 4. Default remaining empty-language China films to "汉语普通话"
    print("\n--- Default remaining empty-lang China to Mandarin ---")
    handled_ids = set(DIALECT_TAGS) | set(REVERT) | set(NONDIALECT_FIX)
    empty_mask = china_mask & (df["语言"].isna() | (df["语言"].astype(str).str.strip() == "") | (df["语言"].astype(str) == "nan"))
    remaining = df.index[empty_mask & ~df["movie_id"].isin(handled_ids)]
    default_count = 0
    for i in remaining:
        df.at[i, "语言"] = "汉语普通话"
        df.at[i, "Language_Category"] = categorize_language("汉语普通话")
        lc, is_dia = language_code("汉语普通话", region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        default_count += 1
    print(f"  Defaulted {default_count} films to 汉语普通话")

    # 5. Verify invariants
    print("\n--- Invariants ---")
    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    print(f"  code2={code2} Chinese&D0={ch_d0} code3={code3} D1={d1}")
    assert code2 == ch_d0 and code3 == d1, "Language_Code / Is_Dialect invariant broken!"

    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    empty_china = int((china["语言"].isna() | (china["语言"].astype(str).str.strip() == "") | (china["语言"].astype(str) == "nan")).sum())
    print(f"  China dialect: {china_dialect}")
    print(f"  China empty language: {empty_china}")
    assert empty_china == 0, f"Still {empty_china} empty-language China films!"

    # 6. Write back
    df.to_csv(CSV, index=False, encoding="utf-8-sig")
    print(f"\n  CSV written: {CSV}")

    # 7. Update manifest fingerprint
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["empty_lang_backfill_20260818"] = {
        "applied_by": "scripts/apply_empty_lang_backfill_20260818.py",
        "rule": "Re-apply v4.1.1 backfills + default remaining to 汉语普通话",
        "dialect_films": len(DIALECT_TAGS),
        "revert_films": len(REVERT),
        "nondialect_fix": len(NONDIALECT_FIX),
        "defaulted_to_mandarin": default_count,
        "china_dialect_after": china_dialect,
        "china_empty_after": 0,
        "backup": BACKUP.name,
    }
    SAMPLE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  Manifest fingerprint: {fp[:16]}...")
    print(f"\nDone! China dialect={china_dialect}, empty=0")


if __name__ == "__main__":
    main()
