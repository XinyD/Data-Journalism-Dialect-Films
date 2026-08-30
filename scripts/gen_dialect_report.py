# -*- coding: utf-8 -*-
"""
方言片逐部明细报告生成器（定义口径 v3 / 判定规则 v2.1）。

输入  : data/cleaned/derived_movies.csv
输出  : data/dialect_films/方言片明细报告.csv   —— 全量方言片 + 普通话对照组分层抽样（年代分层, n≈500）
        方言片详细报告.html        —— 总览统计 + 代表性影片 + 对照组统计 + 字段解读

占比口径（推断值, 非实测）:
    Tier 1  纯方言标签           ≈100%（推断）
    Tier 2a 方言标签排首位        >50%（推断）
    Tier 2b 普通话标签排首位      <50%（推断）
    对照组  无方言标签            普通话主导
"""
import csv
import html
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    DERIVED_MOVIES_INFO,
    DIALECT_DETAIL_CSV,
    DIALECT_DETAIL_HTML,
    atomic_write_text,
)

# dialect_defs.py 是方言定义的单一事实来源（v2.1）。
from dialect_defs import (
    DIALECT_GROUPS, DIALECT_MARKERS_STRICT, MANDARIN_MARKERS,
    OPERA_CONCERT_EXCLUDE_MOVIE_IDS,
    normalize_text, lang_parts, first_tag_is_foreign,
    is_tier2b_default_excluded,
)
from freeze_constants import TIER_BASELINE

SRC = DERIVED_MOVIES_INFO
OUT_CSV = DIALECT_DETAIL_CSV
OUT_HTML = DIALECT_DETAIL_HTML

RATIO_BY_TIER = {
    "Tier 1": ("≈100%（推断）", "纯方言/少数民族语言标签，无普通话标签（对应'全部对白为方言'的狭义纯方言片）"),
    "Tier 2a": (">50%（推断）", "方言标签排首位、普通话居后（方言为主导对白）"),
    "Tier 2b": ("<50%（推断）", "普通话标签排首位、方言为次要但对白中显著存在"),
}

BOUNDARY_TITLES = ["小武", "秋菊打官司", "路边野餐", "少年的你", "让子弹飞",
                   "火锅英雄", "无名之辈", "爱情神话", "三峡好人", "疯狂的石头"]


MANDARIN_NORM = {"汉语普通话", "漢語普通話", "普通话", "普通話", "mandarin", "国语", "國語"}


def tag_is_dialect(t):
    tnorm = normalize_text(t)
    return any(normalize_text(m) in tnorm for m in DIALECT_MARKERS_STRICT)


def tag_is_mandarin(t):
    tnorm = normalize_text(t)
    return any(m in tnorm for m in MANDARIN_MARKERS)


def dialect_groups_of(t):
    tnorm = normalize_text(t)
    hits = [g for g, markers in DIALECT_GROUPS.items() if any(normalize_text(m) in tnorm for m in markers)]
    return hits


def classify_v21(lang, evidence="", movie_id=""):
    """v2.1 严格判定（与 gen_report_strict.classify_strict 完全一致）:
    返回 (is_dialect, tier, found_tags, groups)

    含方案 A（2026-08-15）：命中方言标签但首个语言标签为外语 → 非方言。
    含 v4.1（2026-08-15）Tier 2b 证据审查：普通话排首+方言标签默认排除，
    仅 evidence（Dialect_Evidence 列）非空且非 TIER2B_EXCLUDED 才计方言。
    含 2026-08-18 戏曲/演唱会审计：名单内影片不计入方言口径。
    调用方仅限 China 行（build_records 已过滤 Region=="China"）。"""
    langs = lang_parts(lang)
    has_d = any(tag_is_dialect(l) for l in langs)
    # 2026-08-18 戏曲/演唱会审计排除（E4/E8）
    if has_d and str(movie_id) in OPERA_CONCERT_EXCLUDE_MOVIE_IDS:
        has_d = False
    # 方言优先（与 dialect_defs.has_mandarin_tag 一致）：含方言标记的 part 不贡献普通话信号
    has_m = any(tag_is_mandarin(l) and not tag_is_dialect(l) for l in langs)
    found_tags, groups = [], []
    for i, l in enumerate(langs):
        if tag_is_dialect(l):
            if l not in found_tags:
                found_tags.append(l)
            for g in dialect_groups_of(l):
                if g not in groups:
                    groups.append(g)
    # 方案 A：外语排首位 → 排除出方言口径
    if has_d and first_tag_is_foreign(lang):
        has_d = False
    if not has_d:
        return 0, "非方言", found_tags, groups
    if not has_m:
        tier = "Tier 1"
    else:
        tier = "Tier 2a" if langs and tag_is_dialect(langs[0]) else "Tier 2b"
    # v4.1：Tier 2b 未通过证据审查（无补回证据）→ 默认排除
    if tier == "Tier 2b" and is_tier2b_default_excluded(evidence):
        return 0, "非方言", found_tags, groups
    return 1, tier, found_tags, groups


def norm_lang_display(lang):
    """语言字段展示归一化: 普通话/汉语普通话/国语/Mandarin → 普通话; 保序去重; 台湾国语保留"""
    out = []
    for p in lang_parts(lang):
        if normalize_text(p) in {normalize_text(x) for x in MANDARIN_NORM}:
            key = "普通话"
        else:
            key = p
        if key not in out:
            out.append(key)
    return " / ".join(out)


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_records():
    df = pd.read_csv(SRC, low_memory=False)
    china = df[df["Region"] == "China"].copy()
    rows_d, rows_ctrl = [], []
    for _, r in china.iterrows():
        lang = r.get("语言") if isinstance(r.get("语言"), str) else str(r.get("语言") or "")
        evidence = r.get("Dialect_Evidence", "") if "Dialect_Evidence" in china.columns else ""
        is_d, tier, tags, groups = classify_v21(lang, evidence, r.get("movie_id", ""))
        score = to_float(r.get("豆瓣评分"))
        base = {
            "movie_id": r.get("movie_id"),
            "片名": str(r.get("片名") or ""),
            "年份": r.get("年份"),
            "豆瓣评分": r.get("豆瓣评分"),
            "_score": score,
            "评价人数": r.get("评价人数"),
            "类型": r.get("类型"),
            "Decade": r.get("Decade"),
            "语言字段原文": lang,
            "归一化语言": norm_lang_display(lang),
            "来源URL": r.get("来源URL"),
        }
        if is_d == 1:
            ratio, basis = RATIO_BY_TIER[tier]
            rows_d.append({**base, "组别": "方言片", "命中方言标签": " / ".join(tags),
                           "方言大区": " / ".join(groups), "Tier层级": tier,
                           "方言占比（推断）": ratio, "占比推断依据": basis})
        else:
            rows_ctrl.append({**base, "组别": "对照组", "命中方言标签": "", "方言大区": "",
                              "Tier层级": "非方言", "方言占比（推断）": "普通话主导（0%）",
                              "占比推断依据": "语言字段无中国方言/少数民族语言标签"})
    return china, rows_d, rows_ctrl


def sample_control(rows_ctrl, n=500, seed=42):
    """按年代分层抽样（比例分配），仅抽有评分影片便于对照统计"""
    rng = random.Random(seed)
    rated = [r for r in rows_ctrl if r["_score"] is not None]
    by_decade = defaultdict(list)
    for r in rated:
        by_decade[str(r["Decade"])].append(r)
    total = len(rated)
    picked = []
    for dec, pool in by_decade.items():
        k = max(1, round(n * len(pool) / total)) if total else 0
        rng.shuffle(pool)
        picked.extend(pool[:k])
    return picked


def stats(rows):
    scores = [r["_score"] for r in rows if r["_score"] is not None]
    if not scores:
        return {"n": len(rows), "rated": 0, "mean": None, "bad": None}
    bad = sum(1 for s in scores if s < 5.0)
    return {"n": len(rows), "rated": len(scores),
            "mean": sum(scores) / len(scores), "bad": bad / len(scores) * 100}


def fmt(v, nd=2, suffix=""):
    return f"{v:.{nd}f}{suffix}" if v is not None else "—"


def render_html(china_n, d_rows, ctrl_rows, ctrl_sample):
    ds, cs, ss = stats(d_rows), stats(ctrl_rows), stats(ctrl_sample)
    tier_order = ["Tier 1", "Tier 2a", "Tier 2b"]
    tier_rows_html = []
    for t in tier_order:
        sub = [r for r in d_rows if r["Tier层级"] == t]
        st = stats(sub)
        ratio, _ = RATIO_BY_TIER[t]
        tier_rows_html.append(
            f"<tr><td><strong>{t}</strong></td><td>{st['n']:,}</td>"
            f"<td>{st['n']/ds['n']*100:.1f}%</td><td>{fmt(st['mean'])}</td>"
            f"<td>{fmt(st['bad'],1,'%')}</td><td>{ratio}</td></tr>")

    group_cnt = Counter()
    group_score = defaultdict(list)
    for r in d_rows:
        for g in r["方言大区"].split(" / "):
            if g:
                group_cnt[g] += 1
                if r["_score"] is not None:
                    group_score[g].append(r["_score"])
    group_rows_html = []
    for g, c in group_cnt.most_common():
        sc = group_score[g]
        m = sum(sc) / len(sc) if sc else None
        group_rows_html.append(f"<tr><td>{html.escape(g)}</td><td>{c:,}</td><td>{fmt(m)}</td></tr>")

    def film_table(rows, caption, limit=None):
        rows = rows[:limit] if limit else rows
        body = "".join(
            f"<tr><td>{html.escape(r['片名'])}</td><td>{r['年份']}</td><td>{r['豆瓣评分']}</td>"
            f"<td>{html.escape(r['归一化语言'][:40])}</td><td>{html.escape(r['Tier层级'])}</td>"
            f"<td>{html.escape(r['方言占比（推断）'].split('（')[0])}</td></tr>"
            for r in rows)
        return f"<h4>{caption}</h4><table><thead><tr><th>片名</th><th>年份</th><th>评分</th><th>归一化语言</th><th>Tier</th><th>占比(推断)</th></tr></thead><tbody>{body}</tbody></table>"

    tier1_top = sorted([r for r in d_rows if r["Tier层级"] == "Tier 1" and r["_score"] is not None],
                       key=lambda r: (-r["_score"], -(float(r["评价人数"] or 0))))
    tier2a_top = sorted([r for r in d_rows if r["Tier层级"] == "Tier 2a" and r["_score"] is not None],
                        key=lambda r: (-r["_score"], -(float(r["评价人数"] or 0))))
    tier2b_top = sorted([r for r in d_rows if r["Tier层级"] == "Tier 2b" and r["_score"] is not None],
                        key=lambda r: (-r["_score"], -(float(r["评价人数"] or 0))))

    boundary_html = []
    for t in BOUNDARY_TITLES:
        hit = [r for r in d_rows if r["片名"] == t] or [r for r in ctrl_rows if r["片名"] == t]
        if not hit:
            boundary_html.append(f"<tr><td>{html.escape(t)}</td><td colspan=5>未在中国区数据中匹配到同名影片</td></tr>")
            continue
        r = hit[0]
        boundary_html.append(
            f"<tr><td>{html.escape(r['片名'])}</td><td>{r['年份']}</td><td>{r['豆瓣评分']}</td>"
            f"<td>{html.escape(r['归一化语言'][:40])}</td><td>{r['Tier层级']}</td>"
            f"<td>{html.escape(r['方言占比（推断）'].split('（')[0])}</td></tr>")

    decade_cnt = Counter(str(r["Decade"]) for r in ctrl_sample)
    decade_html = "".join(f"<tr><td>{html.escape(d)}</td><td>{c}</td></tr>"
                          for d, c in sorted(decade_cnt.items()))

    css = """
    :root{--bg:#f8f9fa;--card:#fff;--text:#1a1a2e;--muted:#6c757d;--border:#dee2e6;--accent:#e63946;
    --tier1:#2a9d8f;--tier1-bg:#e0f5f2;--info:#118ab2;--info-bg:#e3f2fd;--warn:#f77f00;--warn-bg:#fff3cd;
    --shadow:0 1px 3px rgba(0,0,0,.08)}
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;background:var(--bg);
    color:var(--text);line-height:1.7;font-size:14px}
    .container{max-width:940px;margin:0 auto;padding:24px}
    .header{background:linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%);color:#fff;padding:36px 24px;
    border-radius:0 0 20px 20px;margin-bottom:28px}
    .header h1{font-size:23px;margin-bottom:6px}.header .sub{font-size:13px;opacity:.85}
    .header .badge{display:inline-block;background:var(--accent);padding:3px 10px;border-radius:12px;
    font-size:11px;font-weight:600;margin-top:8px}
    .section{background:var(--card);border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:var(--shadow)}
    .section h2{font-size:17px;font-weight:700;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid var(--border)}
    .section h3{font-size:15px;font-weight:600;margin:14px 0 8px;color:var(--info)}
    .section h4{font-size:13.5px;font-weight:600;margin:12px 0 6px}
    table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0}
    th{background:#f1f3f5;padding:7px 10px;text-align:left;border-bottom:2px solid var(--border)}
    td{padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
    .cards{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}
    .card{flex:1 1 160px;background:#f8f9fa;border:1px solid var(--border);border-radius:10px;padding:14px}
    .card .v{font-size:22px;font-weight:700;color:var(--tier1)}
    .card .k{font-size:12px;color:var(--muted)}
    .callout{border-radius:8px;padding:12px 16px;margin:12px 0;font-size:13px}
    .callout-warn{background:var(--warn-bg);border-left:4px solid var(--warn)}
    .callout-info{background:var(--info-bg);border-left:4px solid var(--info)}
    ul{padding-left:20px}li{margin-bottom:4px}
    code{background:#f1f3f5;padding:1px 4px;border-radius:3px;font-size:12px}
    """

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>方言片详细报告 — 逐部明细与分层统计</title><style>{css}</style></head><body>
<div class="header"><div class="container">
<h1>方言片详细报告 — 逐部明细与分层统计</h1>
<div class="sub">定义口径 v3（文献综述版） · 判定规则 v2.1（Tier 分层 + 严格中国语言白名单） · 生成日期 2026-08-14</div>
<span class="badge">逐部明细见 data/方言片明细报告.csv（{ds['n']+len(ctrl_sample):,} 行）</span>
</div></div>
<div class="container">

<div class="section"><h2>一、总览</h2>
<div class="cards">
<div class="card"><div class="v">{china_n:,}</div><div class="k">中国电影总数（Region=China）</div></div>
<div class="card"><div class="v">{ds['n']:,}</div><div class="k">方言片（Is_Dialect=1，占 {ds['n']/china_n*100:.1f}%）</div></div>
<div class="card"><div class="v">{fmt(ds['mean'])}</div><div class="k">方言片均分（有评分 {ds['rated']:,} 部）</div></div>
<div class="card"><div class="v">{fmt(cs['mean'])}</div><div class="k">非方言片均分（有评分 {cs['rated']:,} 部）</div></div>
<div class="card"><div class="v">{fmt(ds['bad'],1,'%')} / {fmt(cs['bad'],1,'%')}</div><div class="k">烂片率(&lt;5分) 方言 / 非方言</div></div>
</div>
<div class="callout callout-warn"><strong>占比口径声明</strong>：豆瓣"语言"字段只有标签、无对白时长占比。本报告中所有"方言占比"均为
<strong>基于标签结构与排序的推断值</strong>（非实测）：Tier 1 ≈100%、Tier 2a &gt;50%、Tier 2b &lt;50%，
详见《方言电影定义_文献综述与操作标准_v3.html》第五节。</div>
</div>

<div class="section"><h2>二、Tier 分层分布（对应方言占比推断）</h2>
<table><thead><tr><th>层级</th><th>数量</th><th>占方言片</th><th>均分</th><th>烂片率</th><th>方言占比（推断）</th></tr></thead>
<tbody>{''.join(tier_rows_html)}</tbody></table>
<ul>
<li><strong>Tier 1 纯方言片</strong>：语言字段只含方言/少数民族语言标签，无普通话标签 → 最接近学术定义中"全部对白为方言"的纯方言片（李恒 2009 狭义口径），信号最强。</li>
<li><strong>Tier 2a 方言排首位</strong>：方言+普通话并存、方言居首 → 方言为主导对白（含《秋菊打官司》《小武》等因豆瓣双标注被降级的学术纯方言片）。</li>
<li><strong>Tier 2b 普通话排首位</strong>：普通话居首、方言显著存在 → 方言为次要成分，解读需最谨慎。</li>
</ul></div>

<div class="section"><h2>三、方言大区分布</h2>
<table><thead><tr><th>方言大区</th><th>命中影片数*</th><th>均分</th></tr></thead>
<tbody>{''.join(group_rows_html)}</tbody></table>
<p style="font-size:12px;color:var(--muted)">*一部影片可含多个方言标签，故按大区计数之和大于方言片总数。</p></div>

<div class="section"><h2>四、代表性影片</h2>
{film_table(tier1_top, "Tier 1 纯方言片 · 评分 TOP 10", 10)}
{film_table(tier2a_top, "Tier 2a 方言排首位 · 评分 TOP 5", 5)}
{film_table(tier2b_top, "Tier 2b 普通话排首位 · 评分 TOP 5", 5)}
<h4>边界案例抽查（知名影片分类核验）</h4>
<table><thead><tr><th>片名</th><th>年份</th><th>评分</th><th>归一化语言</th><th>Tier</th><th>占比(推断)</th></tr></thead>
<tbody>{''.join(boundary_html)}</tbody></table>
</div>

<div class="section"><h2>五、普通话对照组（分层抽样 n={ss['n']}）</h2>
<div class="cards">
<div class="card"><div class="v">{ss['n']}</div><div class="k">抽样部数（按年代分层比例分配）</div></div>
<div class="card"><div class="v">{fmt(ss['mean'])}</div><div class="k">抽样均分</div></div>
<div class="card"><div class="v">{fmt(ss['bad'],1,'%')}</div><div class="k">抽样烂片率(&lt;5分)</div></div>
</div>
<h4>抽样年代分布</h4>
<table><thead><tr><th>Decade</th><th>部数</th></tr></thead><tbody>{decade_html}</tbody></table>
<p style="font-size:12.5px">对照组全量（非方言中国电影）均分 {fmt(cs['mean'])}、烂片率 {fmt(cs['bad'],1,'%')}，
抽样与其一致即说明分层有效。对照组明细已并入 CSV（组别列 = "对照组"）。</p></div>

<div class="section"><h2>六、语言字段解读说明（重点）</h2>
<div class="callout callout-info">
<strong>豆瓣"语言"字段 ≠ 对白占比</strong>。该字段标注影片中<strong>出现过</strong>的语言标签集合：
(1) 不含时长占比，无法直接度量方言对白的百分比；(2) 标签顺序在多数情况下反映主次，但不作保证；
(3) 存在双标注（如学术纯方言片《小武》同时标"山西方言/普通话"）与漏标注（少量对白未被标注）两类噪声。
因此本报告以 <strong>Tier 分层 + 标签排序</strong> 作三档占比推断，并在 CSV 中逐部给出"占比推断依据"。
</div>
<ul>
<li><strong>归一化规则</strong>：汉语普通话/普通话/国语/汉语/中文/Mandarin 统一归并为"普通话"（对照组标准语）；"台湾国语"保留独立标签（官话变体）。</li>
<li><strong>命中方言标签</strong>：白名单（90+ 标签，17 组）匹配到的原始标签，是 Is_Dialect 判定的直接证据。</li>
<li><strong>方言大区</strong>：命中标签映射到的方言区（粤语/闽南语/吴语/西南官话/客家话/湘语/赣语/晋语/徽语/平话/官话变体/台语/少数民族语言）。</li>
<li><strong>对照组污染声明</strong>：对照组影片可能存在未被豆瓣标注的少量方言对白，属平台标注盲区，方向性影响已在定义文档第六节声明。</li>
</ul></div>

<div class="section"><h2>七、数据文件</h2>
<ul>
<li><code>data/方言片明细报告.csv</code> — 逐部明细（方言片全量 + 对照组抽样），字段：组别、movie_id、片名、年份、豆瓣评分、评价人数、类型、Decade、语言字段原文、归一化语言、命中方言标签、方言大区、Tier层级、方言占比（推断）、占比推断依据、来源URL。</li>
<li><code>方言电影定义_文献综述与操作标准_v3.html</code> — 定义、文献引用与操作化标准（本报告口径依据）。</li>
</ul></div>

</div></body></html>"""
    return html_doc


def main():
    china, d_rows, ctrl_rows = build_records()
    ctrl_sample = sample_control(ctrl_rows)

    # ---- 与 v2.1 文档核验 ----
    t1 = sum(1 for r in d_rows if r["Tier层级"] == "Tier 1")
    t2a = sum(1 for r in d_rows if r["Tier层级"] == "Tier 2a")
    t2b = sum(1 for r in d_rows if r["Tier层级"] == "Tier 2b")
    print(f"中国区影片: {len(china):,}")
    print(f"方言片(复算): {len(d_rows):,}  [SSOT 基线 {TIER_BASELINE[0]:,}]")
    print(f"  Tier 1 : {t1:,}  [基线 {TIER_BASELINE[1]:,}]")
    print(f"  Tier 2a: {t2a:,}  [基线 {TIER_BASELINE[2]:,}]")
    print(f"  Tier 2b: {t2b:,}  [基线 {TIER_BASELINE[3]:,}]")
    # 基线历史：v2.1 初版 (3487, 2321, 431, 735)；2026-08-15 阶段一审计后
    # 白名单补收 昆明话/独山话/井陉话（《碎片》《四个春天》《村戏》，均 Tier 1）
    # → (3490, 2324, 431, 735)；同日方案 A 落地（排除外语排首 54 部）
    # → (3436, 2303, 431, 702)；同日 F1 收尾（has_mandarin_tag 方言优先，
    # 6 部仅标通用方言标签的影片从 Tier 2a 升回 Tier 1）
    # → (3436, 2309, 425, 702)；同日 v4.1 Tier 2b 证据审查（默认排除 +
    # 证据漏斗/补判白名单补回 349 部，排除 353 部）→ (3083, 2309, 425, 349)；
    # 2026-08-15 用户人工复核移出《芒种》(1986783) → (3082, 2309, 425, 348)；
    # 2026-08-16 用户人工复核补回 4 部空语言 China 电影 → (3086, 2313, 425, 348)。
    # 现行数字以 freeze_constants.TIER_BASELINE 为准（v4.6 发布快照）。
    ok = (len(d_rows), t1, t2a, t2b) == TIER_BASELINE
    print("数字一致性: " + ("PASS" if ok else "WARNING — 与 freeze_constants.TIER_BASELINE 不一致，请检查语言字段或白名单"))

    ds, cs, ss = stats(d_rows), stats(ctrl_rows), stats(ctrl_sample)
    print(f"方言片均分 {fmt(ds['mean'])} / 烂片率 {fmt(ds['bad'],1,'%')}")
    print(f"非方言片均分 {fmt(cs['mean'])} / 烂片率 {fmt(cs['bad'],1,'%')}")
    print(f"对照组抽样 {ss['n']} 部, 均分 {fmt(ss['mean'])}")

    # ---- 输出 CSV ----
    fieldnames = ["组别", "movie_id", "片名", "年份", "豆瓣评分", "评价人数", "类型", "Decade",
                  "语言字段原文", "归一化语言", "命中方言标签", "方言大区", "Tier层级",
                  "方言占比（推断）", "占比推断依据", "来源URL"]
    all_rows = sorted(d_rows, key=lambda r: (r["Tier层级"], str(r["年份"]))) + \
        sorted(ctrl_sample, key=lambda r: str(r["Decade"]))
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"CSV 已写出: {OUT_CSV} ({len(all_rows):,} 行)")

    # ---- 输出 HTML ----
    atomic_write_text(OUT_HTML, render_html(len(china), d_rows, ctrl_rows, ctrl_sample))
    print(f"HTML 已写出: {OUT_HTML}")

    # ---- 边界案例控制台抽查 ----
    print("\n边界案例抽查:")
    for t in BOUNDARY_TITLES:
        hit = [r for r in d_rows if r["片名"] == t] or [r for r in ctrl_rows if r["片名"] == t]
        if hit:
            r = hit[0]
            print(f"  {t}: Tier={r['Tier层级']} 占比={r['方言占比（推断）']} 语言={r['归一化语言'][:50]}")
        else:
            print(f"  {t}: 未匹配")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
