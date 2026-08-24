# -*- coding: utf-8 -*-
"""
方案 A 落地（2026-08-15）：排除"外语标签排首位"的中国制片方言片。

背景与依据：
- analyze_v21_foreign_risk.py 四方案模拟后推荐方案 A（最保守精准）：
  仅排除语言字段首个标签为外语的影片（外语对白为主、方言点缀），
  其余含外语标签但方言/普通话排首的影片保留并做标注清单。
- 该决策避免误杀《我不是药神》《重庆森林》等外语标签非首位的经典片。

规则（与 analyze_v21_foreign_risk.py 方案 A 一致）：
    Region == "China"
    AND Is_Dialect == 1
    AND lang_parts(语言)[0]（归一化后）命中 FOREIGN_MARKERS
    → Is_Dialect=0，Language_Code 复用 data_processor.language_code 重算。

产出：
- data/derived_movies.csv 写回（执行前自动备份为 *_planA_backup_*.csv）
- data/plan_a_excluded.csv        排除明细（含豆瓣字段，可溯源）
- data/plan_a_foreign_annotated.csv  保留但含外语标签的标注清单（约 355 部）

与 DIALECT_AUDIT_EXCLUDE_MOVIE_IDS（审计删除的 22 部）无交集：
那些行已不在主表中，脚本启动时做交集校验并打印留痕。
"""
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
from dialect_defs import (  # noqa: E402
    DIALECT_AUDIT_EXCLUDE_MOVIE_IDS,
    first_tag_is_foreign,
    has_foreign_tag,
)
from data_processor import language_code  # noqa: E402

CSV_PATH = "data/cleaned/derived_movies.csv"
BACKUP_PATH = "data/archive/backups/derived_movies_v21_planA_backup_20260815.csv"
EXCLUDED_PATH = "data/archive/analysis/plan_a_excluded.csv"
ANNOTATED_PATH = "data/archive/analysis/plan_a_foreign_annotated.csv"

KEEP_COLS = ["movie_id", "片名", "年份", "豆瓣评分", "评价人数", "导演", "类型", "语言", "Region"]


def main() -> None:
    df = pd.read_csv(CSV_PATH, low_memory=False)

    # 备份（幂等：已存在则不覆盖，保留最早快照）
    if not Path(BACKUP_PATH).exists():
        shutil.copy2(CSV_PATH, BACKUP_PATH)
        print(f"已备份: {BACKUP_PATH}")
    else:
        print(f"备份已存在（保留最早快照）: {BACKUP_PATH}")

    before_dialect = int(df["Is_Dialect"].sum())
    china_mask = df["Region"] == "China"
    china_dialect_mask = china_mask & (df["Is_Dialect"] == 1)
    china_dialect_before = int(china_dialect_mask.sum())

    # 方案 A 排除目标
    exclude_mask = china_dialect_mask & df["语言"].map(first_tag_is_foreign)
    excluded = df.loc[exclude_mask].copy()

    # 与审计删除名单交集校验（预期 0）
    overlap = set(str(x) for x in excluded["movie_id"]) & set(
        str(x) for x in DIALECT_AUDIT_EXCLUDE_MOVIE_IDS
    )
    print(f"与 DIALECT_AUDIT_EXCLUDE_MOVIE_IDS 交集: {len(overlap)} 部（预期 0）")
    if overlap:
        raise SystemExit(f"交集非空: {sorted(overlap)}，请人工确认后再执行")

    # 应用排除：Is_Dialect=0，Language_Code 重算（传入 region 使方案 A 生效）
    df.loc[exclude_mask, "Is_Dialect"] = 0
    df.loc[exclude_mask, "Language_Code"] = df.loc[exclude_mask, "语言"].map(
        lambda v: language_code(v, "China")[0]
    )

    # 保留但含外语标签的标注清单（方言组内）
    still_dialect_mask = china_mask & (df["Is_Dialect"] == 1)
    annotated_mask = still_dialect_mask & df["语言"].map(has_foreign_tag)

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    cols = [c for c in KEEP_COLS if c in excluded.columns]
    excluded[cols].sort_values("年份").to_csv(EXCLUDED_PATH, index=False, encoding="utf-8-sig")
    df.loc[annotated_mask, cols].sort_values("年份").to_csv(
        ANNOTATED_PATH, index=False, encoding="utf-8-sig"
    )

    china_dialect_after = int((df[china_mask]["Is_Dialect"] == 1).sum())
    after_dialect = int(df["Is_Dialect"].sum())

    print(f"全量方言: {before_dialect} → {after_dialect}")
    print(f"China 方言: {china_dialect_before} → {china_dialect_after}")
    print(f"方案 A 排除: {len(excluded)} 部 → {EXCLUDED_PATH}")
    print(f"含外语标签保留标注: {int(annotated_mask.sum())} 部 → {ANNOTATED_PATH}")
    print("\n下一步: 运行 gen_report_strict.py / gen_dialect_report.py / update_narrative_facts_v21.py")


if __name__ == "__main__":
    main()
