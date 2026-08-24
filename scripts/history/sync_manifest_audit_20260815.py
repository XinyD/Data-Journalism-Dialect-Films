# -*- coding: utf-8 -*-
"""
2026-08-15 审计修正后：同步 data/sample_manifest.json 与 README.md。

背景：apply_audit_fix_20260815.py 删除 22 行（境外方言 4 + 朝鲜语歧义 17 +
豆瓣无评分 1）并将 3 部中国方言片 Is_Dialect 0→1，总行数 53,489 → 53,467。
本脚本按 data_processor.publication_fingerprint 的原始算法重算样本指纹，
更新 manifest 的发布记录数与各维度计数，并同步 README 中的记录数/指纹/Tier 数字。

用法：python scripts/sync_manifest_audit_20260815.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import publication_fingerprint  # noqa: E402

EXPECTED_TOTAL = 53_467
OLD_FP = "6b24e5d931db798e93de9eb30e9c123e35c36ccaa4ae35f089ac7b0600fe1057"


def main() -> None:
    frame = pd.read_csv(DERIVED_MOVIES_INFO, low_memory=False)
    assert len(frame) == EXPECTED_TOTAL, f"总行数 {len(frame)} != {EXPECTED_TOTAL}"

    fp = publication_fingerprint(frame)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["publication_records"] == EXPECTED_TOTAL

    manifest["publication_records"] = EXPECTED_TOTAL
    manifest["sample_fingerprint_sha256"] = fp
    manifest["counts"] = {
        "decade": frame["Decade"].value_counts().sort_index().to_dict(),
        "region": frame["Region"].value_counts().sort_index().to_dict(),
        "language": frame["Language_Category"].value_counts().sort_index().to_dict(),
        "source": frame["数据来源"].fillna("Unknown").value_counts().sort_index().to_dict(),
    }
    manifest["audit_20260815"] = {
        "applied_by": "scripts/apply_audit_fix_20260815.py",
        "records_removed": 22,
        "removal_reasons": {
            "foreign_dialect_false_positive": 4,
            "korean_language_ambiguity_non_china": 17,
            "no_douban_rating_entry": 1,
        },
        "dialect_flag_flipped_0_to_1": ["碎片", "四个春天", "村戏"],
        "trace_file": "data/cleaned/review_queue.csv",
        "note": "stages 各数字为上游清洗管线原始输出，保持不变；发布记录数与指纹为审计后口径。",
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 已更新: publication_records={EXPECTED_TOTAL}")
    print(f"新指纹: {fp}")
    print("counts:", json.dumps(manifest["counts"], ensure_ascii=False))

    # ---- README 同步（幂等：仅在存在旧值时替换）----
    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    if "53,489" in text:
        text = text.replace("53,489", "53,467")
    if OLD_FP in text:
        text = text.replace(OLD_FP, fp)
    readme_path.write_text(text, encoding="utf-8")
    print("README.md 已同步记录数与指纹（Tier/方言数字待重跑报告后另行更新）")

    # ---- 供 README Tier/叙事数字更新参考：China 口径与分年代差值 ----
    china = frame[frame["Region"] == "China"]
    dialect = china[china["Is_Dialect"] == 1]
    mandarin = china[china["Is_Dialect"] == 0]
    print(f"\nChina 口径: 方言 {len(dialect)} / 普通话(非方言) {len(mandarin)}")
    for dec in ["1990s", "2010s"]:
        d = dialect[dialect["Decade"] == dec]["豆瓣评分"].mean()
        m = mandarin[mandarin["Decade"] == dec]["豆瓣评分"].mean()
        print(f"  {dec}: 方言均分 {d:.4f} vs 普通话均分 {m:.4f}, 差值 {d - m:+.2f}")


if __name__ == "__main__":
    main()
