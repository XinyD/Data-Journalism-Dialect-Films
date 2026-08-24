# -*- coding: utf-8 -*-
"""DEPRECATED — historical one-shot. Output paths in this docstring may be stale.

一次性审计修正脚本（2026-08-15 阶段一 → 阶段二，用户审核确认后执行）。

依据《待审错误清单_20260815.md》审核结论：
  1. 白名单补收 昆明话/独山话/井陉话（已改 dialect_defs.py）
     → 《碎片》《四个春天》《村戏》 Is_Dialect 0→1；
  2. 删除境外"XX方言"兜底误命中 4 部（全量口径假阳性）；
  3. 删除"朝鲜语"国别歧义 17 部（Region≠China 全量口径假阳性）；
  4. 删除《The Court-Martial of Jackie Robinson》(1990)：豆瓣无此片评分，数据源错误。

运行前已备份：data/derived_movies_v21_backup_20260815.csv
运行产物：
  - data/derived_movies.csv（修正后）
  - data/review_queue.csv（22 部删除影片溯源记录）
  - stdout 打印被删 movie_id 列表（回填 dialect_defs.py 排除名单用）
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/
from data_processor import language_code  # noqa: E402  已接入 dialect_defs v2.1
from dialect_defs import has_strict_dialect_tag  # noqa: E402

CSV_PATH = "data/cleaned/derived_movies.csv"
QUEUE_PATH = "data/cleaned/review_queue.csv"


def main() -> None:
    df = pd.read_csv(CSV_PATH, low_memory=False)
    total0 = len(df)
    china0 = df[df["Region"] == "China"]
    china_d0 = int((china0["Is_Dialect"] == 1).sum())
    all_d0 = int(df["Is_Dialect"].sum())
    print(f"[修正前] 总行数 {total0:,} | 全量方言 {all_d0:,} | China 方言 {china_d0:,}")
    assert total0 == 53489, "总行数与预期不符，数据可能已被修改，中止"
    assert china_d0 == 3487, "China 方言基线不符，中止"

    lang = df["语言"].fillna("")

    # --- 2. 境外"方言"兜底误命中（4 部）---
    mask_overseas = (
        (df["Is_Dialect"] == 1)
        & lang.str.contains("南部瑞典方言|印度方言|剛果方言|坦纳岛西南部方言", regex=True)
    )
    # --- 3. 朝鲜语国别歧义（17 部，Region≠China）---
    mask_korean = (
        (df["Is_Dialect"] == 1)
        & (df["Region"] != "China")
        & lang.str.contains("朝鲜语|朝鮮語", regex=True)
    )
    # --- 4. 豆瓣无评分的错误行 ---
    mask_badrating = df["片名"].str.strip() == "The Court-Martial of Jackie Robinson"

    def reason_of(row):
        if mask_badrating.loc[row.name]:
            return "豆瓣无此片评分（数据源错误），整行删除"
        if mask_overseas.loc[row.name]:
            return "境外方言标签被'方言'兜底误命中，全量口径假阳性，整行删除"
        return "'朝鲜语'国别歧义（朝鲜半岛影片），全量口径假阳性，整行删除"

    drop_mask = mask_overseas | mask_korean | mask_badrating
    dropped = df[drop_mask].copy()
    print(f"\n[删除] 共 {len(dropped)} 行：境外方言 {int(mask_overseas.sum())} + "
          f"朝鲜语歧义 {int(mask_korean.sum())} + 无评分错误行 {int(mask_badrating.sum())}")
    assert len(dropped) == 22, f"预期删除 22 行，实际 {len(dropped)}，中止"

    queue_rows = []
    for _, row in dropped.iterrows():
        queue_rows.append({
            "movie_id": row["movie_id"], "片名": row["片名"], "年份": row["年份"],
            "Region": row["Region"], "语言": row["语言"],
            "处置": "整行删除", "原因": reason_of(row),
            "审计日期": "2026-08-15",
            "依据": "待审错误清单_20260815.md 第二/三/八类（用户审核确认）",
        })
        print(f"  - [{row['movie_id']}] {row['片名']} ({row['年份']}) R={row['Region']} lang={row['语言']}")
    pd.DataFrame(queue_rows).to_csv(QUEUE_PATH, index=False, encoding="utf-8-sig")
    print(f"溯源记录已写入 {QUEUE_PATH}")

    df = df[~drop_mask].copy()

    # --- 1. 按新白名单全量重算 Is_Dialect / Language_Code ---
    pairs = df["语言"].map(language_code)
    new_code = pairs.map(lambda p: p[0]).astype(int)
    new_d = pairs.map(lambda p: p[1]).astype(int)
    changed = df[(df["Is_Dialect"] != new_d)]
    print(f"\n[重算] Is_Dialect 变化 {len(changed)} 行：")
    for _, row in changed.iterrows():
        print(f"  - {row['片名']} ({row['年份']}) R={row['Region']} "
              f"D: {row['Is_Dialect']}→{int(new_d.loc[row.name])} lang={row['语言']}")
    df["Language_Code"] = new_code
    df["Is_Dialect"] = new_d

    # --- 写回并核验 ---
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    total1 = len(df)
    all_d1 = int(df["Is_Dialect"].sum())
    china1 = df[df["Region"] == "China"]
    china_d1 = int((china1["Is_Dialect"] == 1).sum())
    print(f"\n[修正后] 总行数 {total1:,} | 全量方言 {all_d1:,} | China 方言 {china_d1:,}")
    assert total1 == 53489 - 22
    assert china_d1 == 3490, f"China 方言预期 3,490，实际 {china_d1}"
    print("\n被删 movie_id 列表（回填 dialect_defs.py 排除名单用）：")
    print(sorted(str(x) for x in dropped["movie_id"].tolist()))
    print("\n完成。请运行 gen_report_strict.py 与 gen_html_report_static.py 重生成报告。")


if __name__ == "__main__":
    main()
