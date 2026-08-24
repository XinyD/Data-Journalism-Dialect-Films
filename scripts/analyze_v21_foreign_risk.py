# -*- coding: utf-8 -*-
"""
v2.1 严格标准下方言片含外语标签分析 + 解决方案模拟。

使用 gen_report_strict.py 的完整标签白名单，只处理 Region=="China" 的电影。
模拟 4 种解决方案对"外语为主+方言点缀"问题的修正效果。
"""
import pandas as pd
import sys
import re
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# dialect_defs.py 是方言定义的单一事实来源（v2.1）。
from dialect_defs import (
    DIALECT_GROUPS, DIALECT_MARKERS_STRICT, MANDARIN_MARKERS,
    FOREIGN_MARKERS, SIGN_MARKERS, OPERA_MARKERS,
    normalize_text, lang_parts, has_strict_dialect_tag,
    has_mandarin_tag, has_foreign_tag, get_dialect_tags_found,
)


def classify_v21(lang):
    """v2.1 严格判定，返回 (is_dialect, tier, has_foreign, first_tag_type, dialect_count, foreign_count)"""
    langs = lang_parts(lang)
    n_langs = len(langs)
    has_d = has_strict_dialect_tag(lang)
    has_m = has_mandarin_tag(lang)
    has_f = has_foreign_tag(lang)
    d_tags = get_dialect_tags_found(lang)

    if not has_d:
        return (0, "非方言", has_f, None, 0, 0)

    # 计算各方言/外语标签的位置
    first_dialect_idx = None
    first_mandarin_idx = None
    first_foreign_idx = None
    dialect_count = 0
    foreign_count = 0

    for i, l in enumerate(langs):
        lnorm = normalize_text(l)
        is_dialect = any(normalize_text(m) in lnorm for m in DIALECT_MARKERS_STRICT)
        is_mandarin = any(m in lnorm for m in MANDARIN_MARKERS)
        is_foreign = any(m in lnorm for m in FOREIGN_MARKERS)

        if is_dialect:
            dialect_count += 1
            if first_dialect_idx is None:
                first_dialect_idx = i
        if is_mandarin and first_mandarin_idx is None:
            first_mandarin_idx = i
        if is_foreign:
            foreign_count += 1
            if first_foreign_idx is None:
                first_foreign_idx = i

    first_tag_type = None
    if langs:
        first_norm = normalize_text(langs[0])
        if any(normalize_text(m) in first_norm for m in DIALECT_MARKERS_STRICT):
            first_tag_type = "dialect"
        elif any(m in first_norm for m in MANDARIN_MARKERS):
            first_tag_type = "mandarin"
        elif any(m in first_norm for m in FOREIGN_MARKERS):
            first_tag_type = "foreign"
        else:
            first_tag_type = "other"

    if not has_m:
        tier = "Tier 1"
    else:
        if first_dialect_idx is not None and first_mandarin_idx is not None:
            if first_dialect_idx < first_mandarin_idx:
                tier = "Tier 2a"
            else:
                tier = "Tier 2b"
        else:
            tier = "Tier 2a"  # fallback

    return (1, tier, has_f, first_tag_type, dialect_count, foreign_count)


def main():
    df = pd.read_csv("data/cleaned/derived_movies.csv", low_memory=False)
    china = df[df["Region"] == "China"].copy()

    print(f"中国电影总数: {len(china)}")

    # v2.1 判定
    results = []
    for _, row in china.iterrows():
        lang = str(row.get("语言", "") or "")
        is_d, tier, has_f, first_type, d_count, f_count = classify_v21(lang)
        results.append({
            "片名": str(row.get("片名", "")),
            "年份": row.get("年份", ""),
            "豆瓣评分": row.get("豆瓣评分", 0),
            "评价人数": row.get("评价人数", 0),
            "语言": lang,
            "制片地区": str(row.get("制片国家/地区", "")),
            "Is_Dialect": is_d,
            "Tier": tier,
            "has_foreign": has_f,
            "first_tag_type": first_type,
            "dialect_count": d_count,
            "foreign_count": f_count,
        })

    rdf = pd.DataFrame(results)
    dialect_df = rdf[rdf["Is_Dialect"] == 1].copy()
    nondialect_df = rdf[rdf["Is_Dialect"] == 0].copy()

    print(f"\n{'='*70}")
    print(f"v2.1 方言片总数: {len(dialect_df)}")
    print(f"  Tier 1: {len(dialect_df[dialect_df['Tier']=='Tier 1'])}")
    print(f"  Tier 2a: {len(dialect_df[dialect_df['Tier']=='Tier 2a'])}")
    print(f"  Tier 2b: {len(dialect_df[dialect_df['Tier']=='Tier 2b'])}")
    print(f"非方言片: {len(nondialect_df)}")

    # === 含外语标签的方言片 ===
    foreign_dialect = dialect_df[dialect_df["has_foreign"] == True]
    print(f"\n{'='*70}")
    print(f"含外语标签的方言片: {len(foreign_dialect)} / {len(dialect_df)} ({len(foreign_dialect)/len(dialect_df)*100:.1f}%)")

    # 外语标签频次
    lang_counter = Counter()
    for langs_str in dialect_df["语言"]:
        for l in lang_parts(langs_str):
            lang_counter[l] += 1

    print(f"\n--- v2.1 方言片语言标签 TOP 20 ---")
    for tag, count in lang_counter.most_common(20):
        # 分类
        tnorm = normalize_text(tag)
        if any(normalize_text(m) in tnorm for m in DIALECT_MARKERS_STRICT):
            cls = "[方言]"
        elif any(m in tnorm for m in MANDARIN_MARKERS):
            cls = "[普通话]"
        elif any(m in tnorm for m in FOREIGN_MARKERS):
            cls = "[外语]"
        else:
            cls = "[其他]"
        print(f"  {tag:25s} {count:5d}  {cls}")

    # === "外语为主+方言点缀"风险 ===
    print(f"\n{'='*70}")
    print(f"【风险分析】外语排在方言前面的方言片")
    risk1 = dialect_df[dialect_df["first_tag_type"] == "foreign"]
    print(f"  外语排第一位的方言片: {len(risk1)} ({len(risk1)/len(dialect_df)*100:.1f}%)")

    risk2 = dialect_df[dialect_df["foreign_count"] >= dialect_df["dialect_count"]]
    print(f"  外语标签数 >= 方言标签数: {len(risk2)} ({len(risk2)/len(dialect_df)*100:.1f}%)")

    # 高风险案例
    print(f"\n--- 高风险案例（外语排第一）TOP 20 ---")
    risk_sorted = risk1.sort_values("评价人数", ascending=False)
    for _, r in risk_sorted.head(20).iterrows():
        print(f"  《{r['片名']}》({r['年份']}) 评分:{r['豆瓣评分']} 评价:{r['评价人数']}")
        print(f"    地区: {r['制片地区']}")
        print(f"    语言: {r['语言']}")

    # === 解决方案模拟 ===
    print(f"\n{'='*70}")
    print(f"【解决方案模拟】")
    print(f"{'='*70}")

    # 当前 v2.1 基线
    d_scores = dialect_df["豆瓣评分"].astype(float)
    nd_scores = nondialect_df["豆瓣评分"].astype(float)
    print(f"\n基线（当前 v2.1）:")
    print(f"  方言片: {len(dialect_df)}部, 均分:{d_scores.mean():.2f}, 烂片率:{(d_scores<5).sum()/len(dialect_df)*100:.1f}%")
    print(f"  普通话片: {len(nondialect_df)}部, 均分:{nd_scores.mean():.2f}, 烂片率:{(nd_scores<5).sum()/len(nondialect_df)*100:.1f}%")

    # 方案 A: 排除"外语排第一"的电影
    keep_a = dialect_df[dialect_df["first_tag_type"] != "foreign"]
    moved_a = dialect_df[dialect_df["first_tag_type"] == "foreign"]
    nd_a = pd.concat([nondialect_df, moved_a])
    d_scores_a = keep_a["豆瓣评分"].astype(float)
    nd_scores_a = nd_a["豆瓣评分"].astype(float)
    print(f"\n方案A: 排除'外语排第一'的电影 → 移至非方言")
    print(f"  方言片: {len(keep_a)}部 (移除{len(moved_a)}部), 均分:{d_scores_a.mean():.2f}, 烂片率:{(d_scores_a<5).sum()/len(keep_a)*100:.1f}%")
    print(f"  普通话片: {len(nd_a)}部, 均分:{nd_scores_a.mean():.2f}, 烂片率:{(nd_scores_a<5).sum()/len(nd_a)*100:.1f}%")

    # 方案 B: 排除"外语标签数 >= 方言标签数"的电影
    keep_b = dialect_df[dialect_df["foreign_count"] < dialect_df["dialect_count"]]
    moved_b = dialect_df[dialect_df["foreign_count"] >= dialect_df["dialect_count"]]
    nd_b = pd.concat([nondialect_df, moved_b])
    d_scores_b = keep_b["豆瓣评分"].astype(float)
    nd_scores_b = nd_b["豆瓣评分"].astype(float)
    print(f"\n方案B: 排除'外语标签数 >= 方言标签数'的电影 → 移至非方言")
    print(f"  方言片: {len(keep_b)}部 (移除{len(moved_b)}部), 均分:{d_scores_b.mean():.2f}, 烂片率:{(d_scores_b<5).sum()/len(keep_b)*100:.1f}%")
    print(f"  普通话片: {len(nd_b)}部, 均分:{nd_scores_b.mean():.2f}, 烂片率:{(nd_scores_b<5).sum()/len(nd_b)*100:.1f}%")

    # 方案 C: 排除含外语标签的方言片（最激进）
    keep_c = dialect_df[dialect_df["has_foreign"] == False]
    moved_c = dialect_df[dialect_df["has_foreign"] == True]
    nd_c = pd.concat([nondialect_df, moved_c])
    d_scores_c = keep_c["豆瓣评分"].astype(float)
    nd_scores_c = nd_c["豆瓣评分"].astype(float)
    print(f"\n方案C: 排除所有含外语标签的方言片（最激进）→ 移至非方言")
    print(f"  方言片: {len(keep_c)}部 (移除{len(moved_c)}部), 均分:{d_scores_c.mean():.2f}, 烂片率:{(d_scores_c<5).sum()/len(keep_c)*100:.1f}%")
    print(f"  普通话片: {len(nd_c)}部, 均分:{nd_scores_c.mean():.2f}, 烂片率:{(nd_scores_c<5).sum()/len(nd_c)*100:.1f}%")

    # 方案 D: 排除"外语排第一" + 排除"外语标签数 > 方言标签数"（组合）
    keep_d = dialect_df[(dialect_df["first_tag_type"] != "foreign") &
                        (dialect_df["foreign_count"] <= dialect_df["dialect_count"])]
    moved_d = dialect_df[~((dialect_df["first_tag_type"] != "foreign") &
                           (dialect_df["foreign_count"] <= dialect_df["dialect_count"]))]
    nd_d = pd.concat([nondialect_df, moved_d])
    d_scores_d = keep_d["豆瓣评分"].astype(float)
    nd_scores_d = nd_d["豆瓣评分"].astype(float)
    print(f"\n方案D: 排除'外语排第一' + '外语标签数 > 方言标签数'（组合推荐）")
    print(f"  方言片: {len(keep_d)}部 (移除{len(moved_d)}部), 均分:{d_scores_d.mean():.2f}, 烂片率:{(d_scores_d<5).sum()/len(keep_d)*100:.1f}%")
    print(f"  普通话片: {len(nd_d)}部, 均分:{nd_scores_d.mean():.2f}, 烂片率:{(nd_scores_d<5).sum()/len(nd_d)*100:.1f}%")

    # === 方案 D 的 Tier 分布 ===
    print(f"\n--- 方案D 移除影片的 Tier 分布 ---")
    print(moved_d["Tier"].value_counts().to_string())

    # === 方案 D 移除的影片样例 ===
    print(f"\n--- 方案D 移除的影片 TOP 15（按评价人数） ---")
    moved_sorted = moved_d.sort_values("评价人数", ascending=False)
    for _, r in moved_sorted.head(15).iterrows():
        print(f"  《{r['片名']}》({r['年份']}) 评分:{r['豆瓣评分']} | 语言: {r['语言'][:60]}")

    # === 被保留的高分方言片样例（验证不会误杀） ===
    print(f"\n--- 方案D 保留的高分方言片 TOP 10（验证不误杀） ---")
    keep_high = keep_d.sort_values("豆瓣评分", ascending=False)
    for _, r in keep_high.head(10).iterrows():
        print(f"  《{r['片名']}》({r['年份']}) 评分:{r['豆瓣评分']} | 语言: {r['语言'][:60]}")


if __name__ == "__main__":
    main()
