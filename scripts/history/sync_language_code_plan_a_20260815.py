# -*- coding: utf-8 -*-
"""
2026-08-15 方案 A 补丁：全量重算 Language_Code / Is_Dialect 并同步 manifest。

背景：apply_plan_a.py 首次执行时 data_processor.language_code() 尚未纳入方案 A，
导致 54 部被排除影片的 Language_Code 仍为 3（方言/混合语种），与 Is_Dialect=0
脱节，破坏不变量 code3 == D1 与 narrative_facts.languages 计数一致性。
本脚本在 language_code() 纳入方案 A（region 参数）后全量重算两列并落盘，
随后按 publication_fingerprint 原算法重算指纹，更新 sample_manifest.json
与 README.md 中的指纹（行数与行集不变，仅 Language_Code 54 行 3→2）。

用法：python scripts/sync_language_code_plan_a_20260815.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import language_code, publication_fingerprint  # noqa: E402

EXPECTED_TOTAL = 53_467
OLD_FP = "dd38c08df41870d47261ea45d2516d9c37a6c541678035bdd6f42c8d19dfca16"


def main() -> None:
    df = pd.read_csv(DERIVED_MOVIES_INFO, dtype={"movie_id": "string"}, low_memory=False)
    assert len(df) == EXPECTED_TOTAL, f"总行数 {len(df)} != {EXPECTED_TOTAL}"

    old_lc = df["Language_Code"].astype(int).copy()
    old_d = df["Is_Dialect"].astype(int).copy()

    pairs = [language_code(lang, region) for lang, region in zip(df["语言"], df["Region"])]
    df["Language_Code"] = [p[0] for p in pairs]
    df["Is_Dialect"] = [p[1] for p in pairs]

    changed_lc = df[old_lc != df["Language_Code"]]
    changed_d = df[old_d != df["Is_Dialect"]]
    print(f"Language_Code 变化 {len(changed_lc)} 行（预期 54，全部 China 且 3→2）")
    assert len(changed_lc) == 54 and set(changed_lc["Region"]) == {"China"}
    assert ((old_lc[changed_lc.index] == 3) & (df.loc[changed_lc.index, "Language_Code"] == 2)).all()
    print(f"Is_Dialect 变化 {len(changed_d)} 行（预期 0，方案 A 已先行写回）")
    assert len(changed_d) == 0

    # 不变量复核（与 fix_language_category_20260815.py 同口径）
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    print(f"复核: code2={code2} Chinese&D0={ch_d0} code3={code3} D1={d1}")
    assert code2 == ch_d0 and code3 == d1

    df.to_csv(DERIVED_MOVIES_INFO, index=False, encoding="utf-8-sig")
    print(f"已写回 {DERIVED_MOVIES_INFO}")

    # ---- manifest / README 指纹同步 ----
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["publication_records"] == EXPECTED_TOTAL
    manifest["sample_fingerprint_sha256"] = fp
    manifest.setdefault("plan_a_20260815", {})
    manifest["plan_a_20260815"] = {
        "applied_by": "scripts/apply_plan_a.py + scripts/sync_language_code_plan_a_20260815.py",
        "rule": "Region=China 且命中方言标签但首个语言标签为外语 → 不计入方言口径",
        "movies_excluded_from_dialect": 54,
        "language_code_flipped_3_to_2": 54,
        "trace_files": ["data/plan_a_excluded.csv", "data/plan_a_foreign_annotated.csv"],
        "note": "行集与行数不变（53,467）；指纹变化仅因 Language_Code 54 行 3→2。",
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 指纹已更新: {fp}")

    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    if OLD_FP in text:
        text = text.replace(OLD_FP, fp)
        readme_path.write_text(text, encoding="utf-8")
        print("README.md 指纹已同步")
    else:
        print("README.md 未找到旧指纹（可能已同步），跳过")


if __name__ == "__main__":
    main()
