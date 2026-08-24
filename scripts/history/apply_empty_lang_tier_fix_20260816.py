# -*- coding: utf-8 -*-
"""
Tier 修正脚本（2026-08-16 下午·续）
================================
用户复核指出：《惊梦魂》《出花园》不应在 Tier 1，应在 Tier 2。

依据与处置：
1. 惊梦魂 (4133310, 1995)
   - 百度百科"普通话/粤语"、抖音百科"粤语/汉语"，粤语现场收音、粤语为主要对白
   - 语言: "粤语" → "粤语/普通话"  → Tier 2a（方言排首）
2. 出花园 (34436895, 2019)
   - 中国网"青春光影"标注 语言"中文/潮汕方言"（中文排首）
   - 语言: "潮汕方言" → "普通话/潮汕方言" → Tier 2b（普通话排首，须证据补回）
   - Dialect_Evidence 写入补回证据（v4.1 §5 Tier 2b 机制）

同步更新：empty_lang_backfill_summary / codebook_review / review_queue /
         空语言补全结果_84部（CSV+HTML）
不动：narrative_facts / frontend / 报告 / 测试 —— 等用户通知统一重跑。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "cleaned", "derived_movies.csv")

from dialect_defs import has_strict_dialect_tag, has_mandarin_tag
from gen_dialect_report import classify_v21

# ---- 变更定义 ----
CHANGES = [
    {
        "movie_id": 4133310, "片名": "惊梦魂",
        "新语言": "粤语/普通话",
        "evidence": "",
        "期望tier": "Tier 2a",
        "理由": ("用户复核20260816：百度百科'普通话/粤语'、抖音百科'粤语/汉语'，"
                 "粤语现场收音香港片、粤语为主要对白语言 → Tier 2a"),
    },
    {
        "movie_id": 34436895, "片名": "出花园",
        "新语言": "普通话/潮汕方言",
        "evidence": ("人工复核20260816 Tier2b补回：中国网'青春光影'标注语言'中文/潮汕方言'；"
                     "主演郑鹏生（汕头潮阳人，素人演员）主要参演潮汕方言电影"
                     "（《爸，我一定行的》《出花园》）"),
        "期望tier": "Tier 2b",
        "理由": ("用户复核20260816：中国网标注语言'中文/潮汕方言'（中文排首）→ Tier 2b，"
                 "经人工复核证据补回计方言"),
    },
]

df = pd.read_csv(SRC, encoding="utf-8-sig", low_memory=False)

# ---- Step 1: 修正 derived_movies.csv ----
for ch in CHANGES:
    idx = df.index[df["movie_id"] == ch["movie_id"]]
    assert len(idx) == 1, f"{ch['片名']} 定位失败"
    i = idx[0]
    old_lang = df.at[i, "语言"]
    df.at[i, "语言"] = ch["新语言"]
    if ch["evidence"]:
        df.at[i, "Dialect_Evidence"] = ch["evidence"]
    # 断言新值判定结果
    ev = df.at[i, "Dialect_Evidence"] if pd.notna(df.at[i, "Dialect_Evidence"]) else ""
    is_d, tier, tags, groups = classify_v21(ch["新语言"], ev)
    assert is_d == 1 and tier == ch["期望tier"], \
        f"{ch['片名']} 判定异常: {is_d},{tier}（期望 1,{ch['期望tier']}）"
    print(f"[OK] {ch['片名']}: 语言 '{old_lang}' → '{ch['新语言']}' → {tier}")

df.to_csv(SRC, index=False, encoding="utf-8-sig")
print("derived_movies.csv 已保存")

# ---- Step 2: 校验 8 部方言片全部 Tier ----
print("\n=== 8 部空语言方言片 Tier 复核 ===")
dialect_ids = [4133310, 2129914, 1308060, 10518931, 19899635,
               30441138, 34436895, 34847185]
tiers = {}
for mid in dialect_ids:
    r = df[df["movie_id"] == mid].iloc[0]
    ev = r["Dialect_Evidence"] if pd.notna(r["Dialect_Evidence"]) else ""
    is_d, tier, tags, groups = classify_v21(r["语言"], ev)
    tiers[mid] = tier
    assert is_d == 1, f"{r['片名']} 判定丢失方言!"
    print(f"  {r['片名']:20s} 语言={r['语言']:20s} → {tier}")

china = df[df["Region"] == "China"]
expect_total, expect_t1 = 3090, None  # 总数不变；Tier1 应 -2
# 复算全库 Tier 分布
t1 = t2a = t2b = 0
for _, r in china.iterrows():
    lang = r["语言"] if isinstance(r["语言"], str) else ""
    ev = r["Dialect_Evidence"] if isinstance(r.get("Dialect_Evidence"), str) else ""
    is_d, tier, _, _ = classify_v21(lang, ev)
    if is_d != 1:
        continue
    if tier == "Tier 1":
        t1 += 1
    elif tier == "Tier 2a":
        t2a += 1
    else:
        t2b += 1
total = t1 + t2a + t2b
print(f"\n全库复算: 方言 {total:,} = T1 {t1:,} + T2a {t2a:,} + T2b {t2b:,}")
assert total == 3090, f"方言总数异常: {total}"
assert (t1, t2a, t2b) == (2312, 429, 349), f"Tier 分布异常: {(t1,t2a,t2b)}"
print("断言通过: (2312, 429, 349)")

# ---- Step 3: empty_lang_backfill_summary 更新 Tier ----
SUM = os.path.join(BASE, "data", "archive", "analysis", "empty_lang_backfill_summary_20260816.csv")
s = pd.read_csv(SUM, encoding="utf-8-sig", dtype=str).fillna("")
for ch in CHANGES:
    m = s["movie_id"] == str(ch["movie_id"])
    s.loc[m, "Tier"] = ch["期望tier"]
    s.loc[m, "补全语言"] = ch["新语言"]
    s.loc[m, "变更"] = s.loc[m, "变更"] + "；Tier修正(Tier1→" + ch["期望tier"] + ")"
s.to_csv(SUM, index=False, encoding="utf-8-sig")
print("\nempty_lang_backfill_summary_20260816.csv 已更新")

# ---- Step 4: codebook_review 更新 Tier初判 ----
CB = os.path.join(BASE, "data", "archive", "analysis", "codebook_review.csv")
cb = pd.read_csv(CB, encoding="utf-8-sig", dtype=str).fillna("")
for ch in CHANGES:
    m = cb["movie_id"] == str(ch["movie_id"])
    cb.loc[m, "Tier初判"] = ch["期望tier"]
    cb.loc[m, "主导对白语言"] = "粤语" if ch["movie_id"] == 4133310 else "潮汕方言（普通话并存）"
cb.to_csv(CB, index=False, encoding="utf-8-sig")
print("codebook_review.csv 已更新")

# ---- Step 5: review_queue 追加审计行 ----
RQ = os.path.join(BASE, "data", "cleaned", "review_queue.csv")
rq = pd.read_csv(RQ, encoding="utf-8-sig", dtype=str).fillna("")
new_rows = []
for ch in CHANGES:
    new_rows.append({
        "movie_id": str(ch["movie_id"]), "片名": ch["片名"], "年份": "1995" if ch["movie_id"] == 4133310 else "2019",
        "Region": "China", "语言": ch["新语言"],
        "处置": "空语言补回方言口径v3-Tier修正",
        "原因": ch["理由"],
        "审计日期": "2026-08-16", "依据": "v4.1 方言定义 Tier 分层",
        "状态": "已处理", "处理日期": "2026-08-16",
        "来源": "scripts/apply_empty_lang_tier_fix_20260816.py",
    })
rq = pd.concat([rq, pd.DataFrame(new_rows)], ignore_index=True)
rq.to_csv(RQ, index=False, encoding="utf-8-sig")
print(f"review_queue.csv 已追加 {len(new_rows)} 行")

# ---- Step 6: 空语言补全结果_84部.csv 同步 ----
RES = os.path.join(BASE, "data", "archive", "analysis", "空语言补全结果_84部.csv")
res = pd.read_csv(RES, encoding="utf-8-sig", dtype=str).fillna("")
for ch in CHANGES:
    m = res["movie_id"] == str(ch["movie_id"])
    res.loc[m, "补全语言"] = ch["新语言"]
    res.loc[m, "备注"] = res.loc[m, "备注"] + f"；{ch['期望tier']}（20260816修正）"
res.to_csv(RES, index=False, encoding="utf-8-sig")
print("空语言补全结果_84部.csv 已更新")

print("\n=== 全部完成 ===")
