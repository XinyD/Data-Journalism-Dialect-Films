# -*- coding: utf-8 -*-
"""
Updated dialect movie analysis with STRICT Chinese-language definition.

Key changes from previous version:
1. Expanded DIALECT_MARKERS to cover ALL Chinese dialects AND minority languages
2. REMOVED the indirect rule (has_chinese and len(parts) > 1) — Tier 1* eliminated
3. INCLUDE minority languages spoken in China (藏语, 维吾尔语, 蒙古语, etc.) as Chinese dialects
4. Explicitly EXCLUDE foreign languages (English, Japanese, Korean peninsula, etc.)
5. Only movies with explicit Chinese dialect/minority tags are Is_Dialect=1
"""
import pandas as pd
import json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DERIVED_MOVIES_INFO, REPORT_DATA_STRICT, atomic_write_text

# dialect_defs.py 是方言定义的单一事实来源（v2.1）。
from dialect_defs import (
    DIALECT_GROUPS, DIALECT_MARKERS_STRICT,
    OPERA_CONCERT_EXCLUDE_MOVIE_IDS,
    has_strict_dialect_tag, has_mandarin_tag, has_foreign_tag,
    has_minority_tag, normalize_text, lang_parts, normalize_language_tags,
    get_dialect_tags_found, first_tag_is_foreign,
    is_tier2b_default_excluded,
)

import argparse
import os


# ============================================================
# New strict classification
# ============================================================
def classify_strict(row):
    """
    STRICT classification: only movies with explicit Chinese dialect or Chinese minority-language tags.
    No indirect judgment. Foreign languages excluded from dialect definition.

    方案 A（2026-08-15）：命中方言标签但首个语言标签为外语的影片
    （外语对白为主、方言点缀）不计入方言口径 → is_dialect=0。
    v4.1（2026-08-15）Tier 2b 证据审查：普通话排首+方言标签默认排除，
    仅 Dialect_Evidence 列记录了补回证据的影片才计入方言。
    本函数仅处理 China 行（main 中已过滤 Region=="China"），无需再判 Region。
    """
    lang = str(row.get("语言", "") or "")
    raw_langs = lang_parts(lang)
    langs = normalize_language_tags(lang)
    n_langs = len(langs)
    has_d = has_strict_dialect_tag(lang)
    has_m = has_mandarin_tag(lang)
    d_tags = get_dialect_tags_found(lang)

    # 2026-08-18 戏曲/演唱会审计：名单内影片（戏曲声腔 E4 / 非叙事影片 E8）
    # 不计入方言口径，与 derived_movies.csv 的 Is_Dialect=0 补丁保持一致。
    if str(row.get("movie_id", "")) in OPERA_CONCERT_EXCLUDE_MOVIE_IDS:
        has_d = False

    # 方案 A：外语排首位 → 排除出方言口径（保留外语标记信息供标注清单使用）
    if has_d and first_tag_is_foreign(lang):
        has_d = False

    if not has_d:
        return {
            "is_dialect": 0,
            "tier": "非方言",
            "tier_desc": "普通话/非方言片",
            "dialect_tags": [],
            "all_langs": [str(l) for l in langs],
            "dialect_count": 0,
            "total_count": n_langs,
            "proportion": "不适用（非方言片）",
            "signal": "不适用",
            "mandarin_present": has_m,
            "has_foreign": has_foreign_tag(lang),
            "has_minority": has_minority_tag(lang),
        }

    # Has dialect tag
    if not has_m:
        # Tier 1: pure dialect (no mandarin tag)
        if n_langs == 1:
            prop = "100%（唯一语言标签为中国方言/少数民族语言）"
            signal = "强信号"
        else:
            other = [l for l in langs if l not in d_tags]
            prop = f"中国方言/少数民族语言标签 {len(d_tags)}/{n_langs}，其余为 {', '.join([str(x) for x in other[:3]])}"
            signal = "强信号"
        return {
            "is_dialect": 1,
            "tier": "Tier 1",
            "tier_desc": "纯方言片",
            "dialect_tags": d_tags,
            "all_langs": [str(l) for l in langs],
            "dialect_count": len(d_tags),
            "total_count": n_langs,
            "proportion": prop,
            "signal": signal,
            "mandarin_present": False,
            "has_foreign": has_foreign_tag(lang),
            "has_minority": has_minority_tag(lang),
        }
    else:
        # Tier 2: mixed (has both dialect and mandarin)
        d_first = False
        for i, l in enumerate(langs):
            lnorm = normalize_text(l)
            for marker in DIALECT_MARKERS_STRICT:
                if normalize_text(marker) in lnorm:
                    d_first = (i == 0)
                    break
            if d_first:
                break

        if d_first:
            tier_label = "Tier 2a"
            tier_desc = "混合方言片（方言排首位）"
            signal = "中信号"
            prop = f"方言排第1，共{n_langs}种语言，中国方言/少数民族语言标签 {len(d_tags)}个"
        else:
            # v4.1（2026-08-15）Tier 2b 证据审查：普通话排首+方言标签默认排除，
            # 仅经证据漏斗/补判白名单补回（Dialect_Evidence 非空且非 TIER2B_EXCLUDED）才计方言。
            evidence = str(row.get("Dialect_Evidence", "") or "").strip()
            if is_tier2b_default_excluded(evidence):
                return {
                    "is_dialect": 0,
                    "tier": "非方言",
                    "tier_desc": "普通话/非方言片（Tier 2b 默认排除，见 v4.1 证据审查）",
                    "dialect_tags": [],
                    "all_langs": [str(l) for l in langs],
                    "dialect_count": 0,
                    "total_count": n_langs,
                    "proportion": "不适用（Tier 2b 未通过证据审查）",
                    "signal": "不适用",
                    "mandarin_present": has_m,
                    "has_foreign": has_foreign_tag(lang),
                    "has_minority": has_minority_tag(lang),
                }
            tier_label = "Tier 2b"
            tier_desc = "混合方言片（普通话排首位，证据补回）"
            signal = "弱信号"
            prop = f"普通话排第1，共{n_langs}种语言，中国方言/少数民族语言标签 {len(d_tags)}个；补回证据：{evidence}"
        return {
            "is_dialect": 1,
            "tier": tier_label,
            "tier_desc": tier_desc,
            "dialect_tags": d_tags,
            "all_langs": [str(l) for l in langs],
            "dialect_count": len(d_tags),
            "total_count": n_langs,
            "proportion": prop,
            "signal": signal,
            "mandarin_present": True,
            "has_foreign": has_foreign_tag(lang),
            "has_minority": has_minority_tag(lang),
        }


def main():
    parser = argparse.ArgumentParser(description="v2.1 方言电影严格分析报告")
    parser.add_argument("--output", default=str(REPORT_DATA_STRICT),
                        help="输出 JSON 路径（默认 data/dialect_films/report_data_strict.json）")
    args = parser.parse_args()

    df = pd.read_csv(DERIVED_MOVIES_INFO, low_memory=False)
    china = df[df["Region"] == "China"].copy()

    # Process all China movies
    records = []
    for _, row in china.iterrows():
        info = classify_strict(row)
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
            "Is_Dialect": info["is_dialect"],
            "方言层级": info["tier"],
            "层级说明": info["tier_desc"],
            "方言占比说明": info["proportion"],
            "信号强度": info["signal"],
            "含普通话标签": "是" if info["mandarin_present"] else "否",
            "Decade": str(row.get("Decade", "")),
        })

    result_df = pd.DataFrame(records)

    # 交叉校验：重算结果必须与 derived_movies.csv 的 Is_Dialect 列一致。
    csv_flags = dict(zip(china["movie_id"].astype(str), china["Is_Dialect"].astype(int)))
    mismatch = sum(
        1 for rec in records
        if csv_flags.get(rec["movie_id"], -1) != rec["Is_Dialect"]
    )
    if mismatch > 0:
        raise AssertionError(
            f"重算 Is_Dialect 与 CSV 列不一致 {mismatch} 行（SSOT 脱节；先跑 scripts/replay_v44_baseline.py）"
        )

    # Summary stats
    total_china = len(result_df)
    dialect_df = result_df[result_df["Is_Dialect"] == 1]
    nondialect_df = result_df[result_df["Is_Dialect"] == 0]

    tier1 = dialect_df[dialect_df["方言层级"] == "Tier 1"]
    tier2a = dialect_df[dialect_df["方言层级"] == "Tier 2a"]
    tier2b = dialect_df[dialect_df["方言层级"] == "Tier 2b"]

    summary = {
        "total_china": total_china,
        "total_dialect": len(dialect_df),
        "total_nondialect": len(nondialect_df),
        "tier1_pure": len(tier1),
        "tier2a_dialect_first": len(tier2a),
        "tier2b_mandarin_first": len(tier2b),
        "tier1_pct": round(len(tier1) / len(dialect_df) * 100, 1) if len(dialect_df) > 0 else 0,
        "tier2_pct": round((len(tier2a) + len(tier2b)) / len(dialect_df) * 100, 1) if len(dialect_df) > 0 else 0,
        "dialect_pct_of_china": round(len(dialect_df) / total_china * 100, 1),
        # 注：旧 v1 宽口径全量为 4,667 部，2026-08-14 起已统一至 v2.1，
        # 不再维护 removed_from_old 字段（硬编码 4050 已过时并删除）。
        "dialect_groups": {group: len(markers) for group, markers in DIALECT_GROUPS.items()},
    }

    for label, subset in [("Tier1", tier1), ("Tier2a", tier2a), ("Tier2b", tier2b), ("全部方言", dialect_df), ("普通话片", nondialect_df)]:
        if len(subset) == 0:
            continue
        # F2 防御（2026-08-15）：缺失评分被置 0 的影片若进入分母会同时计入
        # 烂片率分子与分母（且普通话组冷门片占比高时会系统性高估其烂片率）。
        # 当前管线前置过滤保证无评分影片为 0，此处过滤 + 断言防止未来静默引入偏差。
        unrated = int((subset["豆瓣评分"] <= 0).sum())
        assert unrated == 0, f"{label} 出现 {unrated} 部无评分影片，烂片率口径不安全，请检查数据源"
        scores = subset["豆瓣评分"].astype(float)
        summary[f"{label}_count"] = len(subset)
        summary[f"{label}_avg"] = round(scores.mean(), 2)
        summary[f"{label.lower()}_low_rate"] = round((scores < 5.0).sum() / len(subset) * 100, 1)
        summary[f"{label}_high_rate"] = round((scores >= 8.0).sum() / len(subset) * 100, 1)

    # Fix key naming
    for label in ["Tier1", "Tier2a", "Tier2b", "全部方言", "普通话片"]:
        key_low = f"{label.lower()}_low_rate"
        if key_low in summary:
            summary[f"{label}_low_rate"] = summary.pop(key_low)

    # Language tag distribution for dialect movies
    lang_counter = Counter()
    for langs in dialect_df["语言_列表"]:
        seen_tags = set()
        for l in langs:
            lkey = normalize_text(l)
            if lkey not in seen_tags:
                seen_tags.add(lkey)
                lang_counter[l] += 1
    summary["dialect_lang_tags_top20"] = lang_counter.most_common(20)

    # Dialect group distribution
    dialect_group_counter = Counter()
    for _, row in dialect_df.iterrows():
        for tag in row["方言标签"]:
            tnorm = normalize_text(tag)
            for group, markers in DIALECT_GROUPS.items():
                for marker in markers:
                    if normalize_text(marker) in tnorm:
                        dialect_group_counter[group] += 1
                        break
                else:
                    continue
                break
    summary["dialect_group_dist"] = dialect_group_counter.most_common()

    # Sort movies
    tier_order = {"Tier 1": 0, "Tier 2a": 1, "Tier 2b": 2, "非方言": 3}
    result_df["_sort"] = result_df["方言层级"].map(tier_order).fillna(4).astype(int)
    result_df = result_df.sort_values(["_sort", "年份", "豆瓣评分"], ascending=[True, True, False]).drop(columns=["_sort"])

    movies_sorted = result_df.to_dict(orient="records")

    # Slim down for JSON
    slim_movies = []
    for m in movies_sorted:
        slim_movies.append({
            "n": m["片名"], "y": m["年份"], "r": m["豆瓣评分"],
            "l": m["语言_原始"], "dt": m["方言标签"], "dc": m["方言标签数"],
            "tc": m["语言总数"], "id": m["Is_Dialect"], "t": m["方言层级"],
            "td": m["层级说明"], "dp": m["方言占比说明"], "sg": m["信号强度"],
            "mp": m["含普通话标签"], "v": m["评价人数"], "d": m["导演"],
            "g": m["类型"],
        })

    slim_data = {
        "summary": summary,
        "movies": slim_movies,
        "dialect_groups": DIALECT_GROUPS,
    }

    atomic_write_text(
        Path(args.output),
        json.dumps(slim_data, ensure_ascii=False, separators=(",", ":")),
    )

    sz = os.path.getsize(args.output)
    print(f"Strict JSON size: {sz/1024/1024:.1f} MB, {len(slim_movies)} movies")
    print()
    print("=== STRICT DEFINITION SUMMARY ===")
    print(f"中国电影总数: {summary['total_china']}")
    print(f"方言片(严格): {summary['total_dialect']} (占{summary['dialect_pct_of_china']}%)")
    print(f"Tier 1 纯方言: {summary['tier1_pure']}")
    print(f"Tier 2a 方言排首: {summary['tier2a_dialect_first']}")
    print(f"Tier 2b 普通话排首: {summary['tier2b_mandarin_first']}")
    print(f"普通话/非方言: {summary['total_nondialect']}")
    print()
    for label in ["Tier1", "Tier2a", "Tier2b", "全部方言", "普通话片"]:
        k = f"{label}_count"
        if k in summary:
            print(f"{label} ({summary[k]}部): 均分{summary[f'{label}_avg']}, 烂片率{summary[f'{label}_low_rate']}%, 高分率{summary[f'{label}_high_rate']}%")
    print()
    print("=== 方言片语言标签 TOP 20（含普通话，已归一化）===")
    for tag, cnt in summary["dialect_lang_tags_top20"]:
        print(f"  {tag}: {cnt}")
    print()
    print("=== 方言大区分布 ===")
    for group, cnt in summary["dialect_group_dist"]:
        print(f"  {group}: {cnt}")


if __name__ == "__main__":
    main()
