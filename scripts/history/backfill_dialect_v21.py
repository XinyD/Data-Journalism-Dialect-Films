# -*- coding: utf-8 -*-
"""DEPRECATED — historical one-shot. Paths in this docstring may be stale.

将 data/derived_movies.csv 的 Is_Dialect / Language_Code 两列统一到 v2.1 口径。

背景（2026-08-14）：
- CSV 中 Is_Dialect 是旧 v1 口径（含 has_chinese and len(parts)>1 间接判定，共 4,667 部）
- v2.1 严格判定（dialect_defs.py / gen_report_strict.py）：仅语言字段含中国方言/少数民族
  语言标签才算方言片，无间接规则（Region=China 子集应为 3,487 部）
- data_processor.py 已修复并接入 dialect_defs，此处复用其 language_code() 保证
  与将来有源数据时重建的输出完全一致。

运行前已备份：data/derived_movies_v1_backup_20260814.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
from data_processor import language_code  # noqa: E402  已接入 v2.1 判定

CSV_PATH = "data/cleaned/derived_movies.csv"


def main() -> None:
    df = pd.read_csv(CSV_PATH, low_memory=False)
    total = len(df)
    before_dialect = int(df["Is_Dialect"].sum())

    pairs = df["语言"].map(language_code)
    df["Language_Code"] = pairs.map(lambda p: p[0]).astype(int)
    df["Is_Dialect"] = pairs.map(lambda p: p[1]).astype(int)

    after_dialect = int(df["Is_Dialect"].sum())
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    china = df[df["Region"] == "China"]
    china_dialect = int((china["Is_Dialect"] == 1).sum())
    dialect = df[df["Is_Dialect"] == 1]
    scored = dialect[dialect["豆瓣评分"] > 0]

    print(f"总行数: {total}")
    print(f"Is_Dialect=1: {before_dialect} → {after_dialect}（全量，含非中国地区）")
    print(f"Region=China 方言片: {china_dialect}  ← 应与 gen_report_strict 的 3,487 一致")
    print(f"全量方言片均分: {scored['豆瓣评分'].mean():.2f}，烂片率: {(scored['豆瓣评分'] < 5).mean() * 100:.1f}%")
    print("CSV 已写回:", CSV_PATH)


if __name__ == "__main__":
    main()
