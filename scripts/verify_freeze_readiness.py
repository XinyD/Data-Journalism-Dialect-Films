"""阶段 B：数据冻结前验证（规则口径 v4.1 / 数据基线 v4.5）。

计数与指纹以 freeze_constants.py 为准，不读定义文档手填数字。
B1 三方计数一致 / B2 Tier 基线断言 / B3 方案A+审计名单不变量 /
B4 样本指纹同步 / B5 核心结论方向。全部 PASS 才可冻结。
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    DERIVED_MOVIES_INFO,
    DIALECT_AGGREGATES,
    FRONTEND_DATASET,
    GEO_ENRICHMENT,
    NARRATIVE_FACTS,
    REPORT_DATA_STRICT,
    SAMPLE_MANIFEST,
    STORY_UNIVERSE,
)
from dialect_defs import DIALECT_AUDIT_EXCLUDE_MOVIE_IDS, has_strict_dialect_tag, first_tag_is_foreign  # noqa: E402
from freeze_constants import (  # noqa: E402
    PLAN_A_EXCLUDED,
    TIER2B_EXCLUDED,
    TIER_BASELINE,
)

FAILURES = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


df = pd.read_csv(DERIVED_MOVIES_INFO,
                 encoding="utf-8-sig", low_memory=False, dtype={"movie_id": "str"})
manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
strict = json.loads(REPORT_DATA_STRICT.read_text(encoding="utf-8"))
facts = json.loads(NARRATIVE_FACTS.read_text(encoding="utf-8"))

china = df[df["Region"] == "China"]
csv_d1 = int(china["Is_Dialect"].sum())
csv_d0 = int((china["Is_Dialect"] == 0).sum())

# ── B1 三方计数一致 ──
s = strict["summary"]
check("B1.1 CSV China D1 == strict summary", csv_d1 == s["total_dialect"], f"{csv_d1} vs {s['total_dialect']}")
check("B1.2 CSV China D0 == strict summary", csv_d0 == s["total_nondialect"], f"{csv_d0} vs {s['total_nondialect']}")
md = facts["mandarin_dialect"]
check("B1.3 narrative dialect n == CSV", md["dialect_mixed"]["n"] == csv_d1, f"{md['dialect_mixed']['n']} vs {csv_d1}")
check("B1.4 narrative mandarin n == CSV", md["mandarin"]["n"] == csv_d0, f"{md['mandarin']['n']} vs {csv_d0}")
check("B1.5 narrative 口径说明存在", "口径说明_20260814" in facts["meta"])
check("B1.6 narrative 指纹 == manifest", facts["meta"]["sample_fingerprint"] == manifest["sample_fingerprint_sha256"])

# ── B2 Tier 基线断言 ──
expected = TIER_BASELINE
actual = (s["total_dialect"], s["tier1_pure"], s["tier2a_dialect_first"], s["tier2b_mandarin_first"])
check("B2.1 Tier 基线 (china_d1, t1, t2a, t2b)", actual == expected, f"actual={actual} expected={expected}")
t2b_kept = df[(df["Dialect_Evidence"].fillna("") != "") & (df["Dialect_Evidence"].fillna("") != "TIER2B_EXCLUDED") & (df["Is_Dialect"] == 1)]
excluded_rows = df[df["Dialect_Evidence"].fillna("") == "TIER2B_EXCLUDED"]
check("B2.2 TIER2B_EXCLUDED 恰 N 且全 D0",
      len(excluded_rows) == TIER2B_EXCLUDED and int(excluded_rows["Is_Dialect"].sum()) == 0,
      f"n={len(excluded_rows)}, D1={int(excluded_rows['Is_Dialect'].sum())}")

# ── B3 方案 A + 审计名单不变量 ──
lang = china["语言"].fillna("").astype(str)
plan_a = china[lang.map(has_strict_dialect_tag) & lang.map(first_tag_is_foreign)]
check("B3.1 方案 A 排除恰 N 部", len(plan_a) == PLAN_A_EXCLUDED, f"n={len(plan_a)}")
audit_hits = df[df["movie_id"].isin(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS) & (df["Is_Dialect"] == 1)]
check("B3.2 审计排除名单无 D1 残留", len(audit_hits) == 0, f"hits={len(audit_hits)}")
code2_bad = df[(df["Language_Code"] == 3) & (df["Is_Dialect"] == 0)]
code3_bad = df[(df["Is_Dialect"] == 1) & (df["Language_Code"] != 3)]
check("B3.3 Language_Code 不变量 (code3 == D1)", len(code2_bad) == 0 and len(code3_bad) == 0,
      f"code3&D0={len(code2_bad)}, D1&!code3={len(code3_bad)}")

# ── B4 样本指纹同步 ──
fp = manifest["sample_fingerprint_sha256"]
check("B4.1 manifest 记录数 == CSV", manifest["publication_records"] == len(df),
      f"{manifest['publication_records']} vs {len(df)}")
fe = FRONTEND_DATASET
if fe.exists():
    fe_fp = json.loads(fe.read_text(encoding="utf-8")).get("meta", {}).get("sampleFingerprint", "")
    check("B4.2 frontend_dataset 指纹同步", fe_fp == fp, fe_fp[:12])
else:
    check("B4.2 frontend_dataset 存在", False)
da = DIALECT_AGGREGATES
if da.exists():
    da_fp = json.loads(da.read_text(encoding="utf-8")).get("meta", {}).get("sampleFingerprint", "")
    check("B4.3 dialect_aggregates 指纹同步", da_fp == fp, da_fp[:12])
else:
    check("B4.3 dialect_aggregates 存在", False)
geo = GEO_ENRICHMENT
if geo.exists():
    geo_fp = json.loads(geo.read_text(encoding="utf-8")).get("meta", {}).get("sampleFingerprint", "")
    check("B4.4 geo_enrichment 指纹同步", geo_fp == fp, geo_fp[:12])
else:
    check("B4.4 geo_enrichment 存在", False)
story = STORY_UNIVERSE
if story.exists():
    story_fp = json.loads(story.read_text(encoding="utf-8")).get("meta", {}).get("sampleFingerprint", "")
    check("B4.5 story_universe 指纹同步", story_fp == fp, story_fp[:12] if story_fp else "missing")
else:
    check("B4.5 story_universe 存在", False)

# ── B5 核心结论方向 ──
d = china[china["Is_Dialect"] == 1]
nd = china[china["Is_Dialect"] == 0]
d_mean, nd_mean = d["豆瓣评分"].mean(), nd["豆瓣评分"].mean()
d_low = (d["豆瓣评分"] < 5).mean()
nd_low = (nd["豆瓣评分"] < 5).mean()
check("B5.1 方言均分 > 普通话均分", d_mean > nd_mean, f"{d_mean:.2f} vs {nd_mean:.2f}")
check("B5.2 烂片率差距 >= 3x", nd_low / d_low >= 3.0, f"{nd_low*100:.1f}% vs {d_low*100:.1f}% ({nd_low/d_low:.1f}x)")
check("B5.3 by_decade 方向（1990s<0, 2010s>0）",
      md["by_decade"]["1990s"]["mean_delta"] < 0 < md["by_decade"]["2010s"]["mean_delta"],
      f"1990s={md['by_decade']['1990s']['mean_delta']}, 2010s={md['by_decade']['2010s']['mean_delta']}")
empty = china[china["语言"].isna() | (china["语言"].astype(str).str.strip() == "")]
check("B5.4 空语言 China == 0", len(empty) == 0, f"n={len(empty)}")

print()
if FAILURES:
    print(f"[FAIL] {len(FAILURES)} 项未通过：{FAILURES}")
    sys.exit(1)
print("[OK] 阶段 B 全部验证通过 — 数据可进入冻结流程")
