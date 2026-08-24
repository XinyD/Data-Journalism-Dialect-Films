# -*- coding: utf-8 -*-
"""Generate detailed dialect movie report data."""
import pandas as pd
import re, json
from collections import Counter

df = pd.read_csv("data/cleaned/derived_movies.csv", low_memory=False)
china = df[df["Region"] == "China"].copy()

DIALECT_MARKERS = (
    "cantonese", "粤语", "粵語", "hokkien", "闽南", "閩南",
    "shanghainese", "沪语", "滬語", "sichuanese", "四川话", "四川話",
    "hakka", "客家话", "客家話", "taiwanese", "台语", "臺語", "方言",
)
MANDARIN_MARKERS = ("汉语普通话", "漢語普通話", "普通话", "普通話", "mandarin", "国语", "國語")

DIALECT_DETAIL_MAP = {
    "粤语": "粤语（广府片/白话）",
    "粵語": "粤语（广府片/白话）",
    "cantonese": "粤语（广府片/白话）",
    "hokkien": "闽南语（闽台片）",
    "闽南": "闽南语（闽台片）",
    "閩南": "闽南语（闽台片）",
    "shanghainese": "吴语（上海话）",
    "沪语": "吴语（上海话）",
    "滬語": "吴语（上海话）",
    "sichuanese": "西南官话（四川话）",
    "四川话": "西南官话（四川话）",
    "四川話": "西南官话（四川话）",
    "hakka": "客家话",
    "客家话": "客家话",
    "客家話": "客家话",
    "taiwanese": "闽南语（台湾腔/台语）",
    "台语": "闽南语（台语）",
    "臺語": "闽南语（台语）",
    "方言": "方言（未具体标注）",
}


def normalize_text(v):
    if pd.isna(v):
        return ""
    return re.sub(r"\s+", " ", str(v).strip()).casefold()


def lang_parts(v):
    text = normalize_text(v)
    if not text:
        return []
    return [p.strip() for p in re.split(r"\s*(?:/|\||;|；|,)\s*", text) if p.strip()]


def has_dialect_tag(lang):
    text = normalize_text(lang)
    return any(m in text for m in DIALECT_MARKERS)


def has_mandarin_tag(lang):
    text = normalize_text(lang)
    return any(m in text for m in MANDARIN_MARKERS)


def get_dialect_tags(lang):
    """Return list of dialect tags found in language field."""
    tags = []
    parts = lang_parts(lang)
    for p in parts:
        pnorm = normalize_text(p)
        for marker, detail in DIALECT_DETAIL_MAP.items():
            if marker in pnorm:
                tags.append(p.strip())
                break
    return tags


def classify_dialect_movie(row):
    """Return tier and dialect proportion description for a single movie."""
    lang = str(row.get("语言", "") or "")
    langs = lang_parts(lang)
    n_langs = len(langs)
    has_d = has_dialect_tag(lang)
    has_m = has_mandarin_tag(lang)

    if not has_d and not has_m:
        # Is_Dialect=1 but no explicit dialect/mandarin tag
        # This happens because of the "has_chinese and len(parts)>1" rule
        return {
            "tier": "Tier 1*",
            "tier_desc": "多语言中文片（间接判定）",
            "dialect_tags": [],
            "all_langs": [str(l) for l in langs],
            "dialect_count": 0,
            "total_count": n_langs,
            "proportion": "未知（豆瓣仅标注语言标签，无对白占比数据）",
            "signal": "弱信号",
            "mandarin_present": False,
        }

    d_tags = get_dialect_tags(lang)
    dialect_count = len(d_tags)

    if has_d and not has_m:
        # Tier 1: pure dialect
        if n_langs == 1:
            prop = "100%（唯一语言标签为方言）"
            signal = "强信号"
        else:
            other = [l for l in langs if l not in d_tags]
            prop = f"方言标签 {dialect_count}/{n_langs}，其余为 {', '.join(other[:3])}"
            signal = "强信号"
        return {
            "tier": "Tier 1",
            "tier_desc": "纯方言片",
            "dialect_tags": d_tags,
            "all_langs": [str(l) for l in langs],
            "dialect_count": dialect_count,
            "total_count": n_langs,
            "proportion": prop,
            "signal": signal,
            "mandarin_present": False,
        }
    elif has_d and has_m:
        # Tier 2: mixed
        d_first = False
        for i, l in enumerate(langs):
            lnorm = normalize_text(l)
            if any(m in lnorm for m in DIALECT_MARKERS):
                d_first = (i == 0)
                break

        if d_first:
            tier_label = "Tier 2a"
            tier_desc = "混合方言片（方言排首位）"
            signal = "中信号"
            prop = f"方言排第1，共{n_langs}种语言，方言标签 {dialect_count}个"
        else:
            tier_label = "Tier 2b"
            tier_desc = "混合方言片（普通话排首位）"
            signal = "弱信号"
            prop = f"普通话排第1，共{n_langs}种语言，方言标签 {dialect_count}个"
        return {
            "tier": tier_label,
            "tier_desc": tier_desc,
            "dialect_tags": d_tags,
            "all_langs": [str(l) for l in langs],
            "dialect_count": dialect_count,
            "total_count": n_langs,
            "proportion": prop,
            "signal": signal,
            "mandarin_present": True,
        }
    else:
        # has_m only, no dialect tag but Is_Dialect=1
        return {
            "tier": "Tier 1*",
            "tier_desc": "普通话+其他语言（间接判定）",
            "dialect_tags": [],
            "all_langs": [str(l) for l in langs],
            "dialect_count": 0,
            "total_count": n_langs,
            "proportion": "无显式方言标签（多语言中文片）",
            "signal": "弱信号",
            "mandarin_present": True,
        }


# Process all China movies
records = []
for _, row in china.iterrows():
    info = classify_dialect_movie(row)
    records.append({
        "movie_id": str(row.get("movie_id", "")),
        "片名": str(row.get("片名", "")),
        "年份": int(row.get("年份", 0)) if pd.notna(row.get("年份")) else "",
        "豆瓣评分": float(row.get("豆瓣评分", 0)) if pd.notna(row.get("豆瓣评分")) else 0,
        "评价人数": int(row.get("评价人数", 0)) if pd.notna(row.get("评价人数")) else 0,
        "导演": str(row.get("导演", "") or ""),
        "类型": str(row.get("类型", "") or ""),
        "语言_原始": str(row.get("语言", "") or ""),
        "语言_列表": info["all_langs"],
        "方言标签": info["dialect_tags"],
        "方言标签数": info["dialect_count"],
        "语言总数": info["total_count"],
        "Is_Dialect": int(row.get("Is_Dialect", 0)),
        "方言层级": info["tier"] if int(row.get("Is_Dialect", 0)) == 1 else "非方言",
        "层级说明": info["tier_desc"] if int(row.get("Is_Dialect", 0)) == 1 else "普通话/非方言片",
        "方言占比说明": info["proportion"] if int(row.get("Is_Dialect", 0)) == 1 else "不适用（非方言片）",
        "信号强度": info["signal"] if int(row.get("Is_Dialect", 0)) == 1 else "不适用",
        "含普通话标签": "是" if info["mandarin_present"] else "否",
        "Decade": str(row.get("Decade", "")),
    })

result_df = pd.DataFrame(records)

# Summary stats
total_china = len(result_df)
dialect_df = result_df[result_df["Is_Dialect"] == 1]
nondialect_df = result_df[result_df["Is_Dialect"] == 0]

tier1 = dialect_df[dialect_df["方言层级"] == "Tier 1"]
tier1_star = dialect_df[dialect_df["方言层级"] == "Tier 1*"]
tier2a = dialect_df[dialect_df["方言层级"] == "Tier 2a"]
tier2b = dialect_df[dialect_df["方言层级"] == "Tier 2b"]

summary = {
    "total_china": total_china,
    "total_dialect": len(dialect_df),
    "total_nondialect": len(nondialect_df),
    "tier1_pure": len(tier1),
    "tier1_star_indirect": len(tier1_star),
    "tier2a_dialect_first": len(tier2a),
    "tier2b_mandarin_first": len(tier2b),
    "tier1_pct": round(len(tier1) / len(dialect_df) * 100, 1) if len(dialect_df) > 0 else 0,
    "tier2_pct": round((len(tier2a) + len(tier2b)) / len(dialect_df) * 100, 1) if len(dialect_df) > 0 else 0,
}

# Score stats
for label, subset in [("Tier1", tier1), ("Tier1*", tier1_star), ("Tier2a", tier2a), ("Tier2b", tier2b), ("全部方言", dialect_df), ("普通话片", nondialect_df)]:
    if len(subset) == 0:
        continue
    scores = subset["豆瓣评分"].astype(float)
    summary[f"{label}_count"] = len(subset)
    summary[f"{label}_avg"] = round(scores.mean(), 2)
    summary[f"{label}_low_rate"] = round((scores < 5.0).sum() / len(subset) * 100, 1)
    summary[f"{label}_high_rate"] = round((scores >= 8.0).sum() / len(subset) * 100, 1)

# Language tag distribution for dialect movies
lang_counter = Counter()
for langs in dialect_df["语言_列表"]:
    for l in langs:
        lang_counter[l] += 1
summary["dialect_lang_tags_top20"] = lang_counter.most_common(20)

# Save full data as JSON for the report
output = {
    "summary": summary,
    "movies": records,
}

# Sort movies: dialect first (by tier, then by year), then non-dialect
tier_order = {"Tier 1": 0, "Tier 1*": 1, "Tier 2a": 2, "Tier 2b": 3, "非方言": 4}
result_df["_sort"] = result_df["方言层级"].map(tier_order).fillna(5).astype(int)
result_df = result_df.sort_values(["_sort", "年份", "豆瓣评分"], ascending=[True, True, False]).drop(columns=["_sort"])

# Save to JSON
movies_sorted = result_df.to_dict(orient="records")
output["movies"] = movies_sorted
output["summary"] = summary

with open("scripts/report_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print("=== SUMMARY ===")
for k, v in summary.items():
    if k == "dialect_lang_tags_top20":
        print(f"\n方言片语言标签 TOP 20:")
        for tag, cnt in v:
            print(f"  {tag}: {cnt}")
    else:
        print(f"  {k}: {v}")

print(f"\nTotal movies in report: {len(movies_sorted)}")
print("Data saved to scripts/report_data.json")
