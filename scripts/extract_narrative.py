"""Recompute every quantitative fact used by the scrollytelling article."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST, NARRATIVE_FACTS, atomic_write_text


TITLE = "片名"
YEAR = "年份"
RATING = "豆瓣评分"
VOTES = "评价人数"
OUTPUT = NARRATIVE_FACTS
GENRE_LABELS = ["剧情", "喜剧", "动作/冒险", "爱情", "悬疑/惊悚", "科幻/奇幻", "其他"]
REGION_LABELS = ["北美", "欧洲", "东亚", "中国大陆", "其他"]
LANGUAGE_LABELS = ["英语", "日语", "普通话", "方言", "韩语", "其他"]


def summary(frame: pd.DataFrame) -> dict:
    ratings = frame[RATING].dropna()
    return {
        "n": int(len(frame)),
        "mean": round(float(ratings.mean()), 4) if len(ratings) else None,
        "median": round(float(ratings.median()), 4) if len(ratings) else None,
        "sd": round(float(ratings.std(ddof=0)), 4) if len(ratings) else None,
        "q1": round(float(ratings.quantile(0.25)), 4) if len(ratings) else None,
        "high_share": round(float((ratings >= 8.5).mean() * 100), 4) if len(ratings) else None,
        "below_five_share": round(float((ratings < 5).mean() * 100), 4) if len(ratings) else None,
        "mean_votes": round(float(frame[VOTES].mean()), 2) if len(frame) else None,
    }


def top_movies(frame: pd.DataFrame, count: int = 5) -> list[dict]:
    return (
        frame.sort_values([RATING, VOTES], ascending=False)[[TITLE, YEAR, RATING, VOTES]]
        .head(count)
        .rename(columns={TITLE: "title", YEAR: "year", RATING: "rating", VOTES: "votes"})
        .to_dict("records")
    )


def standardized_mean(
    frame: pd.DataFrame,
    reference: pd.DataFrame,
    dimensions: list[str],
) -> dict:
    """Directly standardize a group mean to the reference cell distribution."""
    reference_weights = reference.groupby(dimensions).size() / len(reference)
    cell_means = frame.groupby(dimensions)[RATING].mean()
    common = cell_means.index.intersection(reference_weights.index)
    covered_weights = reference_weights.loc[common]
    coverage = float(covered_weights.sum())
    if not len(common) or coverage <= 0:
        return {"mean": None, "reference_weight_coverage": 0.0, "cells": 0}
    normalized_weights = covered_weights / coverage
    value = float((cell_means.loc[common] * normalized_weights).sum())
    return {
        "mean": round(value, 4),
        "reference_weight_coverage": round(coverage, 6),
        "cells": int(len(common)),
    }


def main() -> None:
    frame = pd.read_csv(DERIVED_MOVIES_INFO)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    facts: dict[str, object] = {
        "meta": {
            "record_count": len(frame),
            "minimum_vote_count": manifest["inclusion_criteria"]["minimum_vote_count"],
            "sample_fingerprint": manifest["sample_fingerprint_sha256"],
        },
        "sample": {
            **summary(frame),
            "year_min": int(frame[YEAR].min()),
            "year_max": int(frame[YEAR].max()),
        },
    }

    facts["decades"] = {
        str(value): summary(group)
        for value, group in frame.groupby("Decade", sort=True)
    }
    facts["regions"] = {
        REGION_LABELS[int(code)]: summary(group)
        for code, group in frame.groupby("Region_Code", sort=True)
    }
    facts["languages"] = {
        LANGUAGE_LABELS[int(code)]: summary(group)
        for code, group in frame.groupby("Language_Code", sort=True)
    }

    genre_comparison = {}
    for code, label in enumerate(GENRE_LABELS):
        genre = frame[frame["Genre_Code"] == code]
        genre_comparison[label] = {
            "all": summary(genre),
            "north_america": summary(genre[genre["Region_Code"] == 0]),
            "other_regions": summary(genre[genre["Region_Code"] != 0]),
        }
    facts["genre_comparison"] = genre_comparison

    year_1994 = frame[frame[YEAR] == 1994]
    facts["year_1994"] = {
        **summary(year_1994),
        "top_movies": top_movies(year_1994),
    }
    other_1990s = frame[frame[YEAR].between(1990, 1999) & frame[YEAR].ne(1994)]
    facts["other_1990s_excluding_1994"] = summary(other_1990s)

    yearly_region = {}
    for year, group in frame[frame[YEAR].between(1990, 2026)].groupby(YEAR):
        north_america = group[group["Region_Code"] == 0]
        east_asia_china = group[group["Region_Code"].isin([2, 3])]
        north_summary = summary(north_america)
        east_summary = summary(east_asia_china)
        delta = None
        if north_summary["n"] and east_summary["n"]:
            delta = round(
                float(east_asia_china[RATING].mean() - north_america[RATING].mean()),
                4,
            )
        yearly_region[str(int(year))] = {
            "north_america": north_summary,
            "east_asia_china": east_summary,
            "delta": delta,
        }
    facts["yearly_region_comparison"] = yearly_region
    facts["year_2011"] = yearly_region.get("2011", {})

    comparable_years = [
        {"year": int(year), **values}
        for year, values in yearly_region.items()
        if values["north_america"]["n"] >= 30 and values["east_asia_china"]["n"] >= 30
    ]
    comparable_years.sort(key=lambda item: item["year"])
    sign_changes = []
    for previous, current in zip(comparable_years, comparable_years[1:]):
        if (previous["delta"] < 0) != (current["delta"] < 0):
            sign_changes.append({
                "from_year": previous["year"],
                "to_year": current["year"],
                "from_delta": previous["delta"],
                "to_delta": current["delta"],
            })
    facts["yearly_region_sign_changes_min_n_30"] = sign_changes

    cutoff = 2010
    facts["cutoff_2010"] = {
        "before": summary(frame[frame[YEAR] < cutoff]),
        "after": summary(frame[frame[YEAR] >= cutoff]),
    }
    cutoff_values = []
    for candidate in range(1990, 2021):
        before = summary(frame[frame[YEAR] < candidate])
        after = summary(frame[frame[YEAR] >= candidate])
        if before["mean"] is None or after["mean"] is None:
            continue
        cutoff_values.append({
            "cutoff": candidate,
            "before": before,
            "after": after,
            "mean_gap": round(before["mean"] - after["mean"], 4),
        })
    facts["cutoff_sensitivity"] = {
        "values": cutoff_values,
        "minimum": min(cutoff_values, key=lambda item: item["mean_gap"]),
        "maximum": max(cutoff_values, key=lambda item: item["mean_gap"]),
    }

    europe = frame[frame["Region_Code"] == 1]
    facts["europe"] = {**summary(europe), "top_movies": top_movies(europe)}
    non_europe = frame[frame["Region_Code"] != 1]
    standardization_dimensions = ["Decade", "Genre_Code"]
    europe_standardized = standardized_mean(europe, frame, standardization_dimensions)
    non_europe_standardized = standardized_mean(non_europe, frame, standardization_dimensions)
    raw_gap = float(europe[RATING].mean() - non_europe[RATING].mean())
    standardized_gap = europe_standardized["mean"] - non_europe_standardized["mean"]
    facts["europe_standardization"] = {
        "dimensions": standardization_dimensions,
        "reference": "all publication records",
        "europe": {
            "raw_mean": round(float(europe[RATING].mean()), 4),
            "distribution": summary(europe),
            "standardized": europe_standardized,
        },
        "non_europe": {
            "raw_mean": round(float(non_europe[RATING].mean()), 4),
            "distribution": summary(non_europe),
            "standardized": non_europe_standardized,
        },
        "raw_gap": round(raw_gap, 4),
        "standardized_gap": round(standardized_gap, 4),
        "gap_reduction": round(raw_gap - standardized_gap, 4),
    }

    # F12: mandarin_dialect 必须是 Region=China 口径（Is_Dialect 与报告一致）
    china_frame = frame[frame["Region"] == "China"]
    mandarin = china_frame[china_frame["Is_Dialect"] == 0]
    dialect = china_frame[china_frame["Is_Dialect"] == 1]
    mandarin_summary = summary(mandarin)
    dialect_summary = summary(dialect)
    facts["mandarin_dialect"] = {
        "mandarin": mandarin_summary,
        "dialect_mixed": dialect_summary,
        "mean_delta": round(dialect_summary["mean"] - mandarin_summary["mean"], 4),
        "by_decade": {
            decade: {
                "mandarin": summary(group[group["Is_Dialect"] == 0]),
                "dialect_mixed": summary(group[group["Is_Dialect"] == 1]),
                "mean_delta": round(
                    float(group[group["Is_Dialect"] == 1][RATING].mean())
                    - float(group[group["Is_Dialect"] == 0][RATING].mean()),
                    4,
                ),
            }
            for decade, group in china_frame.groupby("Decade", sort=True)
        },
    }
    # F11 防回归：口径说明随重生成写入 meta（原由 update_narrative_facts_v21.py 补写）
    facts["meta"]["口径说明_20260814"] = (
        "方言定义 v4.1.1 新基线（dialect_defs.py）：方案 A + Tier 2b 证据审查 + 审计排除名单"
        " + 空语言回填（delivery_20260817 合并数据重应用，2026-08-18）"
        " + v4.6 豆瓣语言回填（2026-08-30；Wikidata 只补 Language_Code 空缺）："
        f"mandarin_dialect 块为 Region=China 口径（方言{len(dialect):,} / 普通话{len(mandarin):,}，"
        "与 gen_report_strict 报告一致）；languages 块为全量口径（按 Language_Code 分组）。"
    )

    facts["largest_year_delta_min_n_30"] = max(
        comparable_years,
        key=lambda item: abs(item["delta"]),
        default=None,
    )

    atomic_write_text(OUTPUT, json.dumps(facts, ensure_ascii=False, indent=2))
    print(f"Recomputed narrative facts for {len(frame):,} records: {OUTPUT}")


if __name__ == "__main__":
    main()
