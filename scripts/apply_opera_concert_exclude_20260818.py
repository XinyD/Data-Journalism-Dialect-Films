"""Apply the OPERA_CONCERT_EXCLUDE_MOVIE_IDS to the current dataset.

2026-08-18 审计：49 部戏曲片（定义 E4）与演唱会/音乐纪录片/颁奖典礼
（E8，非叙事影片）因语言字段含粤语/方言标签被误判为方言片。
本脚本将其 Is_Dialect 置 0 并重算 Language_Code（影片保留在数据集中，
仍为有效的普通话组样本），Dialect_Evidence 标记 AUDIT_EXCLUDED_OPERA_CONCERT。

幂等性：重复运行不改变数据；manifest 中 fixed_count 为本次改动数，
first_run_fixed_count 仅首次运行写入（避免覆盖溯源信息）。
"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import (  # noqa: E402
    CHINESE_LANGUAGE_MARKERS,
    ENGLISH_MARKERS,
    MANDARIN_MARKERS,
    contains_any,
    normalize_text,
    publication_fingerprint,
)
from dialect_defs import OPERA_CONCERT_EXCLUDE_MOVIE_IDS  # noqa: E402

CSV = DERIVED_MOVIES_INFO
BACKUP = ROOT / "data" / "derived_movies_opera_concert_backup_20260818.csv"
MANIFEST_KEY = "opera_concert_exclude_20260818"


def main():
    df = pd.read_csv(CSV, encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
    print(f"Total rows: {len(df)}")

    # 首次运行才备份（幂等：重跑不覆盖已有备份）
    if not BACKUP.exists():
        shutil.copy2(CSV, BACKUP)
        print(f"Backup written: {BACKUP}")
    else:
        print(f"Backup exists, skipped: {BACKUP}")

    fixed = 0
    healed_code = 0
    already_d0 = []
    missing = []
    for mid in sorted(OPERA_CONCERT_EXCLUDE_MOVIE_IDS):
        idx = df.index[df["movie_id"] == mid]
        if len(idx) != 1:
            missing.append(mid)
            continue
        i = idx[0]
        if int(df.at[i, "Is_Dialect"]) != 1:
            # 幂等自愈：修正首轮误将纯方言语言（Language_Category=Other）归入
            # Language_Code=2 的 5 部影片（应对齐 data_processor.language_code → 1）。
            if int(df.at[i, "Language_Code"]) == 2 and df.at[i, "Language_Category"] != "Chinese":
                df.at[i, "Language_Code"] = 1
                healed_code += 1
            already_d0.append(mid)
            continue
        df.at[i, "Is_Dialect"] = 0
        # 重算 Language_Code（不再计方言），与 data_processor.language_code 语义一致：
        # 中文类（普通话/Chinese 标签）→2，英语→0，其余（含纯方言语言、
        # Language_Category=Other）→1；保持不变量 code2 == Chinese 类且 Is_Dialect=0。
        lang = str(df.at[i, "语言"]) if pd.notna(df.at[i, "语言"]) else ""
        text = normalize_text(lang)
        has_chinese = contains_any(text, CHINESE_LANGUAGE_MARKERS)
        if contains_any(text, MANDARIN_MARKERS) or has_chinese:
            df.at[i, "Language_Code"] = 2
        elif contains_any(text, ENGLISH_MARKERS):
            df.at[i, "Language_Code"] = 0
        else:
            df.at[i, "Language_Code"] = 1
        if "Dialect_Evidence" in df.columns:
            df.at[i, "Dialect_Evidence"] = "AUDIT_EXCLUDED_OPERA_CONCERT"
        fixed += 1

    print(f"Fixed {fixed} films (Is_Dialect 1->0)")
    print(f"Healed Language_Code 2->1 (pure-dialect-language rows): {healed_code}")
    print(f"Already Is_Dialect=0 (idempotent skip): {len(already_d0)}")
    if missing:
        print(f"WARNING: {len(missing)} ids not found in dataset: {missing}")

    # Invariants
    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    assert code3 == d1, f"Invariant broken: Language_Code==3 ({code3}) != Is_Dialect==1 ({d1})"
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    assert code2 == ch_d0, f"Invariant broken: Language_Code==2 ({code2}) != Chinese&D0 ({ch_d0})"
    print(f"Invariant OK: Language_Code==3 == Is_Dialect==1 == {d1}; code2 == Chinese&D0 == {code2}")

    df.to_csv(CSV, index=False, encoding="utf-8-sig")
    print(f"CSV written: {CSV}")

    # Manifest
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    entry = manifest.get(MANIFEST_KEY, {})
    first_run = "first_run_fixed_count" not in entry
    entry.update({
        "applied_by": "scripts/apply_opera_concert_exclude_20260818.py",
        "rule": "OPERA_CONCERT_EXCLUDE_MOVIE_IDS: 戏曲片(E4)与演唱会/音乐纪录片/颁奖典礼(E8)排除方言口径",
        "exclude_list_size": len(OPERA_CONCERT_EXCLUDE_MOVIE_IDS),
        "fixed_count": fixed,
        "language_code_healed": healed_code,
        "already_d0": already_d0,
        "candidate_list": "data/archive/analysis/opera_concert_exclude_candidates_20260818.csv",
        "backup": BACKUP.name,
        "note": "fixed_count 为本次运行改动数，非累计值；影片保留在数据集中（普通话组）；language_code_healed 为纯方言语言行 Language_Code 2→1 自愈数（对齐 data_processor.language_code 语义）",
    })
    if first_run:
        entry["first_run_fixed_count"] = fixed
    manifest[MANIFEST_KEY] = entry
    SAMPLE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest updated, fingerprint: {fp[:16]}...")

    # Final counts
    china = df[df["Region"] == "China"]
    china_d1 = int(china["Is_Dialect"].sum())
    total_d1 = int(df["Is_Dialect"].sum())
    print(f"\nFinal: total D1={total_d1}, China D1={china_d1}")


if __name__ == "__main__":
    main()
