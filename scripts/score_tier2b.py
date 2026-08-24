# -*- coding: utf-8 -*-
"""
Tier 2b 证据漏斗规则引擎（v4.1，2026-08-15）。

背景：
- Tier 2b = Region=China 且命中方言白名单、但归一化后普通话标签排首位的影片（701 部）。
- 实测该层噪声大：217 部「汉语普通话/粤语」双标签港片含大量邵氏国语配音片；
  而《疯狂的石头》等真方言片也在该层。语言字段首位排序不可靠，
  故 v4.1 口径将 Tier 2b 默认移出口径，仅凭证据漏斗补回。

规则（只读打分，不改主表）：
    E1  方言标签 >= 2 个（去重后）                +3  强信号
    E2  单方言标签且紧随普通话居第 2 位            +1  结构信号
    E3  剧情简介命中方言关键词                     +2  文本证据
    E4  Gemini评价提及方言                        +2  文本证据
    N1  制片含香港 且 标签恰为{普通话,粤语}两个     -3  邵氏/老港片假阳性画像
    N2  方言标签首现位置 >= 4                     -1  弱结构信号

判定：score >= 3 → auto_recover；score <= -2 → exclude；其余 → gray_zone。
标杆影片（TIER2B_BENCHMARK_TITLES，学术/公众公认方言片）强制进入 gray_zone
（走 LLM/人工复核通道，不被规则直接排除）。

产出：data/tier2b_evidence.csv（逐部得分/命中证据/判定/是否标杆）+ 控制台统计。
用法：py scripts/score_tier2b.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "data" / "cleaned" / "derived_movies.csv"
OUT = BASE / "data" / "tier2b_evidence.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dialect_defs import (  # noqa: E402
    lang_parts,
    get_dialect_tags_found,
    normalize_text,
)

# 与 classify_strict/classify_v21 一致的普通话标记（判定用，非展示）
from dialect_defs import MANDARIN_MARKERS, DIALECT_MARKERS_STRICT  # noqa: E402

# 标杆影片：学术界/公众广泛认定的方言片（v4.1 强制人工复核通道）。
# (片名, 年份或 None)；年份用于消歧（如《亲爱的》2008/2014 同名）。
# 与数据集求交集后生效；不在 Tier 2b 层（或不在数据集）的自动跳过。
TIER2B_BENCHMARK_TITLES = [
    ("疯狂的石头", 2006), ("疯狂的赛车", 2009), ("西藏往事", 2011),
    ("秘密基地", 2020), ("亲爱的", 2014), ("心花路放", 2014),
    ("让子弹飞", 2010), ("三峡好人", 2006), ("站台", 2000), ("任逍遥", 2002),
    ("世界", 2004), ("天注定", 2013), ("山河故人", 2015), ("江湖儿女", 2018),
    ("路边野餐", 2015), ("南方车站的聚会", 2019), ("追凶者也", 2016),
    ("一个勺子", 2014), ("鸡犬不宁", 2006), ("光荣的愤怒", 2006),
    ("姨妈的后现代生活", 2007),
]


def is_benchmark(title, year):
    for t, y in TIER2B_BENCHMARK_TITLES:
        if title == t and (y is None or str(year) == str(y)):
            return True
    return False

# 剧情简介/Gemini评价 的方言关键词（文本证据 E3/E4）
TEXT_KEYWORDS = [
    "方言", "川话", "四川话", "重庆话", "成都话", "粤语", "广东话", "上海话",
    "沪语", "苏州话", "杭州话", "温州话", "东北话", "陕西话", "陕西方言",
    "陕北话", "河南话", "山西话", "晋语", "闽南", "客家", "潮汕", "潮州话",
    "藏语", "维吾尔", "蒙古语", "朝鲜语", "壮语", "彝语", "苗语", "侗语",
    "哈萨克", "武汉话", "长沙话", "湖南话", "南京话", "徐州", "青岛话",
    "山东话", "唐山话", "云南话", "云南方言", "贵州话", "贵阳", "台语",
    "吴语", "徽语", "赣语", "湘语", "乡音",
]

PLACEHOLDER = {"经典电影暂无简介", "暂无简介", "经典电影暂无评价", "暂无评价"}


def tag_is_dialect(t):
    tnorm = normalize_text(t)
    return any(normalize_text(m) in tnorm for m in DIALECT_MARKERS_STRICT)


def tag_is_mandarin(t):
    tnorm = normalize_text(t)
    return any(m in tnorm for m in MANDARIN_MARKERS) and not tag_is_dialect(t)


def is_tier2b(lang):
    """与 gen_report_strict.classify_strict 的 Tier 2b 判定一致（方案 A 已先行生效，
    主表 Is_Dialect=1 已排除外语排首影片，此处仅判结构）。"""
    parts = lang_parts(lang)
    if not parts:
        return False
    has_d = any(tag_is_dialect(p) for p in parts)
    has_m = any(tag_is_mandarin(p) for p in parts)
    return has_d and has_m and not tag_is_dialect(parts[0])


def clean_text(v):
    t = str(v or "").strip()
    return "" if t in PLACEHOLDER else t


def score_movie(r):
    """返回 (score, hits[list[str]])。"""
    lang = str(r.get("语言") or "")
    parts = lang_parts(lang)
    d_tags = get_dialect_tags_found(lang)
    d_uniq = []
    for t in d_tags:
        if normalize_text(t) not in {normalize_text(x) for x in d_uniq}:
            d_uniq.append(t)
    # 方言首现位置（1-based）
    d_pos = next((i + 1 for i, p in enumerate(parts) if tag_is_dialect(p)), None)

    hits, score = [], 0
    if len(d_uniq) >= 2:
        hits.append("E1")
        score += 3
    if len(d_uniq) == 1 and d_pos == 2:
        hits.append("E2")
        score += 1
    if any(k in clean_text(r.get("剧情简介")) for k in TEXT_KEYWORDS):
        hits.append("E3")
        score += 2
    if any(k in clean_text(r.get("Gemini评价")) for k in TEXT_KEYWORDS):
        hits.append("E4")
        score += 2

    norm_set = set()
    for p in parts:
        norm_set.add("普通话" if tag_is_mandarin(p) else normalize_text(p))
    is_hk = "香港" in str(r.get("制片国家/地区") or "")
    if is_hk and len(parts) == 2 and norm_set == {"普通话", normalize_text("粤语")}:
        hits.append("N1")
        score -= 3
    if d_pos is not None and d_pos >= 4:
        hits.append("N2")
        score -= 1
    return score, hits


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    t2b = [r for r in rows
           if r["Region"] == "China" and r["Is_Dialect"] == "1" and is_tier2b(r["语言"])]
    print(f"Tier 2b 影片: {len(t2b)} 部")

    fieldnames = ["movie_id", "片名", "年份", "导演", "制片国家/地区", "语言",
                  "豆瓣评分", "评价人数", "score", "hits", "verdict", "benchmark", "来源URL"]
    verdict_cnt = Counter()
    out_rows = []
    for r in t2b:
        score, hits = score_movie(r)
        bench = is_benchmark(r["片名"].strip(), r["年份"])
        if bench:
            verdict = "gray_zone"  # 标杆片强制走人工/LLM 复核通道
        elif score >= 3:
            verdict = "auto_recover"
        elif score <= -2:
            verdict = "exclude"
        else:
            verdict = "gray_zone"
        verdict_cnt[verdict] += 1
        out_rows.append({
            "movie_id": r["movie_id"], "片名": r["片名"], "年份": r["年份"],
            "导演": r["导演"], "制片国家/地区": r["制片国家/地区"], "语言": r["语言"],
            "豆瓣评分": r["豆瓣评分"], "评价人数": r["评价人数"],
            "score": score, "hits": "+".join(hits), "verdict": verdict,
            "benchmark": "1" if bench else "0", "来源URL": r["来源URL"],
        })

    out_rows.sort(key=lambda x: (-x["score"], int(x["年份"] or 0)))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f"已写出: {OUT}")
    for k in ["auto_recover", "gray_zone", "exclude"]:
        print(f"  {k}: {verdict_cnt[k]}")

    bench_in = [x for x in out_rows if x["benchmark"] == "1"]
    print(f"\n标杆片命中 Tier 2b: {len(bench_in)} 部")
    for x in bench_in:
        print(f"  {x['片名']} ({x['年份']}) score={x['score']} hits={x['hits']} → {x['verdict']}")

    print("\nauto_recover 样例（前 15）:")
    for x in [x for x in out_rows if x["verdict"] == "auto_recover"][:15]:
        print(f"  {x['片名']} ({x['年份']}) {x['语言']}")
    print("\nexclude 样例（前 15）:")
    for x in [x for x in out_rows if x["verdict"] == "exclude"][:15]:
        print(f"  {x['片名']} ({x['年份']}) {x['语言']}")


if __name__ == "__main__":
    main()
