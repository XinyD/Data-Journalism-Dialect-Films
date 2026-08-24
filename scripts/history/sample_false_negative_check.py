# -*- coding: utf-8 -*-
"""假阴性探查：从非方言组（Region=China, Is_Dialect=0）随机抽样，
人工核对豆瓣页面是否漏标方言标签。

用法：py scripts/sample_false_negative_check.py
输出：data/false_negative_sample30.csv（30 部，seed=42）
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

df = pd.read_csv(
    ROOT / "data" / "cleaned" / "derived_movies.csv",
    dtype={"movie_id": "string"},
    low_memory=False,
)

china_nondialect = df[(df["Region"] == "China") & (df["Is_Dialect"] == 0)]

sample = china_nondialect.sample(n=30, random_state=42)
output = sample[["movie_id", "片名", "年份", "语言", "来源URL"]].copy()
output["豆瓣链接"] = output["来源URL"]
output = output.drop(columns=["来源URL"])

out_path = ROOT / "data" / "archive" / "analysis" / "false_negative_sample30.csv"
output.to_csv(out_path, index=False, encoding="utf-8-sig")
print(f"已输出 30 部假阴性探查样本 -> {out_path}")
print(f"非方言池: {len(china_nondialect)} 部，抽样: 30 部，seed=42")
