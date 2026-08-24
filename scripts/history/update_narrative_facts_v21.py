# -*- coding: utf-8 -*-
"""
将 data/narrative_facts.json 的方言相关统计统一到 v2.1 口径（2026-08-14）。

统一原则：
1. mandarin_dialect 块 → Region=China 口径（方言 = Is_Dialect==1，普通话/非方言 = Is_Dialect==0），
   与 gen_report_strict.py 报告完全一致（方案 A 已应用，排除外语排首 54 部，
   2026-08-15），供 Part3 叙事引用。
2. languages 块（世界语言分类对比）→ 保持全量口径（英语/欧洲/其他不变），
   "方言/混合语种" = 全量 Is_Dialect==1，"普通话" = 全量 Chinese 类非方言，
   供 Part1 世界总览 / 语言维度对比引用。

统计量格式与原文件一致：n/mean/median/sd/q1/high_share(>=8)/below_five_share(<5)/mean_votes。
"""
import json

import pandas as pd

CSV_PATH = "data/cleaned/derived_movies.csv"
FACTS_PATH = "data/narrative_facts.json"


def stats(sub: pd.DataFrame) -> dict:
    s = sub["豆瓣评分"].astype(float)
    return {
        "n": int(len(sub)),
        "mean": round(float(s.mean()), 4),
        "median": round(float(s.median()), 4),
        "sd": round(float(s.std()), 4),
        "q1": round(float(s.quantile(0.25)), 4),
        "high_share": round(float((s >= 8).mean() * 100), 4),
        "below_five_share": round(float((s < 5).mean() * 100), 4),
        "mean_votes": round(float(sub["评价人数"].astype(float).mean()), 2),
    }


def main() -> None:
    df = pd.read_csv(CSV_PATH, low_memory=False)
    with open(FACTS_PATH, encoding="utf-8") as f:
        nf = json.load(f)

    # ---- 1. mandarin_dialect：Region=China 口径 ----
    china = df[df["Region"] == "China"]
    dialect = china[china["Is_Dialect"] == 1]
    mandarin = china[china["Is_Dialect"] == 0]

    md = {
        "mandarin": stats(mandarin),
        "dialect_mixed": stats(dialect),
        "mean_delta": round(
            float(dialect["豆瓣评分"].astype(float).mean())
            - float(mandarin["豆瓣评分"].astype(float).mean()),
            4,
        ),
        "by_decade": {},
    }
    for dec in ["Pre-1990s", "1990s", "2000s", "2010s", "2020s"]:
        d_dialect = dialect[dialect["Decade"] == dec]
        d_mandarin = mandarin[mandarin["Decade"] == dec]
        mean_delta = None
        if len(d_dialect) and len(d_mandarin):
            mean_delta = round(
                float(d_dialect["豆瓣评分"].astype(float).mean())
                - float(d_mandarin["豆瓣评分"].astype(float).mean()),
                4,
            )
        md["by_decade"][dec] = {
            "mandarin": stats(d_mandarin) if len(d_mandarin) else None,
            "dialect_mixed": stats(d_dialect) if len(d_dialect) else None,
            "mean_delta": mean_delta,
        }
    nf["mandarin_dialect"] = md

    # ---- 2. languages 块：全量语言分类 ----
    lang_chinese = df[df["Language_Category"] == "Chinese"]
    dialect_all = df[df["Is_Dialect"] == 1]
    mandarin_all = lang_chinese[lang_chinese["Is_Dialect"] == 0]
    nf["languages"]["方言/混合语种"] = stats(dialect_all)
    nf["languages"]["普通话"] = stats(mandarin_all)

    # 元信息标注口径（数字动态计算，避免硬编码脱节）
    nf.setdefault("meta", {})
    nf["meta"]["口径说明_20260814"] = (
        "方言定义 v4.1（dialect_defs.py）：方案 A（排除外语标签排首位 54 部）+ Tier 2b 证据审查"
        "（默认排除+证据漏斗/逐部补判白名单补回，2026-08-15）：mandarin_dialect 块为 Region=China 口径 "
        f"（方言{len(dialect):,} / 普通话{len(mandarin):,}，与 gen_report_strict 报告一致）；"
        "languages 块为全量口径 "
        "（方言=全量Is_Dialect==1 / 普通话=全量Chinese类非方言）。"
    )

    with open(FACTS_PATH, "w", encoding="utf-8") as f:
        json.dump(nf, f, ensure_ascii=False, indent=2)

    print("=== 更新后 mandarin_dialect（Region=China 口径）===")
    m = md["dialect_mixed"]
    print(f"方言: n={m['n']} 均分{m['mean']} 烂片率{m['below_five_share']}%")
    m2 = md["mandarin"]
    print(f"普通话/非方言: n={m2['n']} 均分{m2['mean']} 烂片率{m2['below_five_share']}%")
    print("=== 更新后 languages（全量口径）===")
    l1 = nf["languages"]["方言/混合语种"]
    print(f"方言/混合语种: n={l1['n']} 均分{l1['mean']} 烂片率{l1['below_five_share']}%")
    l2 = nf["languages"]["普通话"]
    print(f"普通话: n={l2['n']} 均分{l2['mean']} 烂片率{l2['below_five_share']}%")


if __name__ == "__main__":
    main()
