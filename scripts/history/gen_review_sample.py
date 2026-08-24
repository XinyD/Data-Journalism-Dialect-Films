# -*- coding: utf-8 -*-
"""
人工核验准备（2026-08-15，计划 G）：

1. data/codebook_review.csv —— 按《方言电影轻量版_Codebook_v2.0.md》§5 30 秒
   记录卡字段建同构表头（幂等：已存在则不覆盖）。
2. data/review_queue.csv —— 追加方案 A 标注清单中"少数民族语言+外语同现"
   影片为首批种子（入队原因"方案A标注-待核验"，幂等去重）。
3. data/codebook_review_sample.csv —— 分层抽样清单：
   Tier 1 抽 30 + Tier 2a 抽 20 + Tier 2b 抽 50 + 方案 A 排除边界全量（54 部），
   固定 seed=42（项目铁律），预填影片信息、判定列留空。
   人工看片由用户执行，本脚本只交付清单。
"""
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dialect_defs import (  # noqa: E402
    has_minority_tag, has_foreign_tag,
)
from gen_report_strict import classify_strict  # noqa: E402
from apply_plan_a import first_tag_is_foreign  # noqa: E402

SEED = 42
SRC = ROOT / "data" / "derived_movies.csv"
TEMPLATE = ROOT / "data" / "codebook_review.csv"
QUEUE = ROOT / "data" / "review_queue.csv"
ANNOTATED = ROOT / "data" / "plan_a_foreign_annotated.csv"
EXCLUDED = ROOT / "data" / "plan_a_excluded.csv"
SAMPLE_OUT = ROOT / "data" / "codebook_review_sample.csv"

# Codebook v2.0.1 §5 记录卡同构表头（+ movie_id 便于合并核验）
CARD_COLUMNS = [
    "movie_id", "片名", "年份", "所看版本", "方言名称", "少数民族语言",
    "步骤1_有方言吗", "步骤2_方言重要吗", "步骤3_方言有作用吗",
    "主导对白语言", "结论", "Tier初判", "证据",
]
JUDGE_COLUMNS = CARD_COLUMNS[3:]  # 人工填写列，清单中留空


def ensure_template() -> None:
    if TEMPLATE.exists():
        print(f"模板已存在，跳过: {TEMPLATE.name}")
        return
    pd.DataFrame(columns=CARD_COLUMNS).to_csv(TEMPLATE, index=False, encoding="utf-8-sig")
    print(f"记录卡模板已创建: {TEMPLATE.name}（{len(CARD_COLUMNS)} 列）")


def append_queue_seeds(df: pd.DataFrame) -> None:
    anno = pd.read_csv(ANNOTATED, dtype={"movie_id": "string"}, encoding="utf-8-sig")
    seed_ids = [
        mid for mid, lang in zip(anno["movie_id"], anno["语言"])
        if has_minority_tag(lang) and has_foreign_tag(lang)
    ]
    queue = pd.read_csv(QUEUE, dtype={"movie_id": "string"}, encoding="utf-8-sig")
    existing = set(queue["movie_id"])
    new_rows = []
    info = df.set_index(df["movie_id"].astype(str))
    for mid in seed_ids:
        if mid in existing:
            continue
        r = info.loc[mid]
        new_rows.append({
            "movie_id": mid, "片名": r["片名"], "年份": r["年份"],
            "Region": r["Region"], "语言": r["语言"], "状态": "待核验",
            "原因": "方案A标注-待核验（方言组保留片，少数民族语言+外语标签同现）",
            "处理日期": "", "来源": "scripts/gen_review_sample.py（计划G）",
        })
    if new_rows:
        # 整体重写避免 utf-8-sig 追加模式在文件中部引入 BOM
        merged = pd.concat([queue, pd.DataFrame(new_rows)], ignore_index=True)
        merged.to_csv(QUEUE, index=False, encoding="utf-8-sig")
    print(f"复核队列种子: 少数民族+外语同现 {len(seed_ids)} 部，新入队 {len(new_rows)} 部")


def main() -> None:
    df = pd.read_csv(SRC, dtype={"movie_id": "string"}, low_memory=False)
    china = df[df["Region"] == "China"]

    ensure_template()
    append_queue_seeds(df)

    # ---- 分层抽样（China 方言组，按重算 Tier）----
    records = {}
    for _, row in china.iterrows():
        info = classify_strict(row)
        if info["is_dialect"] == 1:
            records[str(row["movie_id"])] = (row, info["tier"])

    by_tier = {"Tier 1": [], "Tier 2a": [], "Tier 2b": []}
    for mid, (row, tier) in records.items():
        if tier in by_tier:
            by_tier[tier].append(mid)
    for tier in by_tier:
        by_tier[tier].sort()  # 固定排序保证跨平台可复现

    rng = random.Random(SEED)
    quotas = {"Tier 1": 30, "Tier 2a": 20, "Tier 2b": 50}
    picked = []
    for tier, quota in quotas.items():
        pool = by_tier[tier][:]
        rng.shuffle(pool)
        picked.extend([(mid, tier, "分层抽样") for mid in pool[:quota]])
        print(f"{tier}: 总体 {len(by_tier[tier])} 部，抽取 {min(quota, len(pool))} 部")

    # ---- 方案 A 排除边界全量 ----
    excluded = pd.read_csv(EXCLUDED, dtype={"movie_id": "string"}, encoding="utf-8-sig")
    picked.extend(
        (str(mid), "方案A排除", "方案A排除边界全查") for mid in excluded["movie_id"]
    )
    print(f"方案 A 排除边界: 全量 {len(excluded)} 部")

    # ---- 输出清单（判定列留空）----
    rows = []
    info_by_id = {mid: (row, tier) for mid, (row, tier) in records.items()}
    for mid, tier, source in picked:
        if mid in info_by_id:
            r, _ = info_by_id[mid]
            lang, title, year = r["语言"], r["片名"], r["年份"]
        else:  # 方案 A 排除片：从主表取
            r = china[china["movie_id"].astype(str) == mid].iloc[0]
            lang, title, year = r["语言"], r["片名"], r["年份"]
        row_out = {
            "movie_id": mid, "片名": title, "年份": year,
            "语言字段原文": lang, "Tier初判_自动": tier, "抽样来源": source,
            "外语排首": "是" if first_tag_is_foreign(lang) else "否",
        }
        for c in JUDGE_COLUMNS:
            if c not in row_out:
                row_out[c] = ""
        rows.append(row_out)

    out = pd.DataFrame(rows)
    cols = ["movie_id", "片名", "年份", "语言字段原文", "Tier初判_自动",
            "抽样来源", "外语排首"] + [c for c in JUDGE_COLUMNS if c not in
                                       ("movie_id", "片名", "年份")]
    out[cols].to_csv(SAMPLE_OUT, index=False, encoding="utf-8-sig")
    print(f"抽样清单已写出: {SAMPLE_OUT.name}（{len(out)} 行，seed={SEED}）")


if __name__ == "__main__":
    main()
