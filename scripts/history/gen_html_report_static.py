# -*- coding: utf-8 -*-
"""Generate a fully self-contained HTML report with static table rows.

This version embeds all movie rows directly as HTML <tr> elements so that the
file works offline, inside WeChat's built-in browser, and inside the preview
panel without relying on external JS files or large inline JSON parsing.
"""
import json
from html import escape
from pathlib import Path

base = Path(__file__).resolve().parent.parent

# 数据源：data/dialect_films/report_data_strict.json（由 gen_report_strict.py 基于最新
# cleaned/derived_movies.csv 生成，与 CSV Is_Dialect 列交叉校验一致）。
with open(base / "data" / "dialect_films" / "report_data_strict.json", "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]

# 上一版报告（方案 A 落地后）的方言片基数，用于展示本轮口径变更净变化。
# v4.1（2026-08-15）Tier 2b 证据审查 + 2026-08-18 戏曲/演唱会审计排除 49 部。
PREV_DIALECT_TOTAL = 3436
TIER2B_EXCLUDED = PREV_DIALECT_TOTAL - summary["total_dialect"]  # 累计净减数（Tier 2b 审查 + 戏曲/演唱会审计）

def generate_report(movies, output_filename, showing_all):

    def rating_class(r):
        if r >= 8.0:
            return "rating-high"
        if r < 5.0:
            return "rating-low"
        return ""


    def tier_badge(tier):
        cls = {
            "Tier 1": "badge-tier1",
            "Tier 2a": "badge-tier2a",
            "Tier 2b": "badge-tier2b",
            "非方言": "badge-nond",
        }.get(tier, "badge-nond")
        return f'<span class="badge {cls}">{escape(str(tier))}</span>'


    def signal_badge(signal):
        label_map = {"强信号": "强", "中信号": "中", "弱信号": "弱", "不适用": "—"}
        cls_map = {
            "强信号": "badge-tier1",
            "中信号": "badge-tier2a",
            "弱信号": "badge-tier2b",
            "不适用": "badge-nond",
        }
        return f'<span class="badge {cls_map.get(signal, "badge-nond")}">{escape(label_map.get(signal, str(signal)))}</span>'


    rows_html_parts = []
    for idx, m in enumerate(movies, start=1):
        rc = rating_class(m["r"])
        rc_attr = f' class="{rc}"' if rc else ""
        tags = ", ".join(m["dt"]) if m.get("dt") else '<span style="color:#adb5bd">无</span>'
        rows_html_parts.append(
            f'<tr data-idx="{idx}" data-tier="{escape(m["t"])}" data-year="{m["y"]}" '
            f'data-rating="{m["r"]}" data-votes="{m.get("v", 0)}" '
            f'data-search="{escape((m["n"] + "|" + str(m["l"]) + "|" + str(m.get("d", "")) + "|" + str(m.get("g", ""))).lower())}">'
            f'<td style="color:var(--text-muted)">{idx}</td>'
            f'<td class="title-cell">{escape(str(m["n"]))}</td>'
            f'<td>{m["y"]}</td>'
            f'<td{rc_attr}>{m["r"]}</td>'
            f'<td>{m.get("v", 0):,}</td>'
            f'<td class="lang-cell">{escape(str(m["l"]))}</td>'
            f'<td>{tags}</td>'
            f'<td>{tier_badge(m["t"])}</td>'
            f'<td class="dp-cell">{escape(str(m["dp"]))}</td>'
            f'<td>{signal_badge(m["sg"])}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(rows_html_parts)

    # Estimate row count for JS
    num_movies = len(movies)

    html = f"""<!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>方言电影数据详细报告 — 严格中国语言标准（2026修订版 v2.1）</title>
    <style>
      :root {{
        --bg: #f8f9fa; --card-bg: #fff; --text: #1a1a2e; --text-muted: #6c757d;
        --border: #dee2e6; --accent: #e63946; --accent-light: #fde8ea;
        --tier1: #2a9d8f; --tier1-bg: #e0f5f2;
        --tier2a: #e29578; --tier2a-bg: #fce8e0;
        --tier2b: #b08968; --tier2b-bg: #f5ebe0;
        --nond: #adb5bd; --nond-bg: #f1f3f5;
        --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
        --shadow-lg: 0 4px 12px rgba(0,0,0,0.1);
      }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; font-size: 14px; }}
      .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
      .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 48px 24px; border-radius: 0 0 24px 24px; box-shadow: var(--shadow-lg); margin-bottom: 32px; }}
      .header h1 {{ font-size: 26px; margin-bottom: 8px; font-weight: 700; }}
      .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
      .header .meta {{ font-size: 12px; opacity: 0.6; margin-top: 12px; }}
      .header .badge-rev {{ display: inline-block; background: var(--accent); padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-top: 8px; }}
      .section {{ background: var(--card-bg); border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow); }}
      .section-title {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--border); display: flex; align-items: center; gap: 8px; }}
      .section-title .num {{ background: var(--accent); color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }}
      .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 8px; }}
      .stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; text-align: center; }}
      .stat-card .label {{ font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }}
      .stat-card .value {{ font-size: 28px; font-weight: 700; }}
      .stat-card .sub {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}
      .tier-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      .tier-table th {{ background: #f1f3f5; padding: 10px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); }}
      .tier-table td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
      .tier-table tr:hover {{ background: #f8f9fa; }}
      .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
      .badge-tier1 {{ background: var(--tier1-bg); color: var(--tier1); }}
      .badge-tier2a {{ background: var(--tier2a-bg); color: var(--tier2a); }}
      .badge-tier2b {{ background: var(--tier2b-bg); color: var(--tier2b); }}
      .badge-nond {{ background: var(--nond-bg); color: var(--nond); }}
      .lang-bar {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
      .lang-bar .lang-name {{ width: 100px; text-align: right; font-size: 12px; }}
      .lang-bar .bar-wrap {{ flex: 1; height: 18px; background: #f1f3f5; border-radius: 4px; overflow: hidden; }}
      .lang-bar .bar {{ height: 100%; border-radius: 4px; }}
      .lang-bar .count {{ width: 60px; font-size: 12px; color: var(--text-muted); }}
      .filter-bar {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }}
      .filter-bar input, .filter-bar select {{ padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: white; }}
      .filter-bar input {{ flex: 1; min-width: 200px; }}
      .filter-bar select {{ min-width: 140px; }}
      .filter-bar .btn {{ padding: 8px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }}
      .filter-bar .btn-primary {{ background: var(--accent); color: white; }}
      .filter-bar .btn-outline {{ background: white; border: 1px solid var(--border); color: var(--text); }}
      .table-wrap {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); }}
      .movie-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      .movie-table thead th {{ background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; font-weight: 600; position: sticky; top: 0; white-space: nowrap; cursor: pointer; }}
      .movie-table thead th:hover {{ background: #2a2a4e; }}
      .movie-table tbody td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
      .movie-table tbody tr:hover {{ background: #f8f9fa; }}
      .movie-table tbody tr.hidden {{ display: none; }}
      .movie-table .title-cell {{ font-weight: 600; max-width: 200px; }}
      .movie-table .lang-cell {{ max-width: 200px; word-break: break-all; }}
      .movie-table .dp-cell {{ max-width: 280px; font-size: 12px; }}
      .rating-high {{ color: var(--tier1); font-weight: 700; }}
      .rating-low {{ color: var(--accent); font-weight: 700; }}
      .pagination {{ display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; flex-wrap: wrap; }}
      .pagination button {{ padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px; background: white; cursor: pointer; font-size: 13px; }}
      .pagination button.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
      .pagination button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
      .pagination .info {{ font-size: 12px; color: var(--text-muted); margin-left: 12px; }}
      .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
      .note strong {{ color: #856404; }}
      .note-info {{ background: #e3f2fd; border-left: 4px solid #118ab2; padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
      .note-info strong {{ color: #0d47a1; }}
      .method-box {{ background: #f1f3f5; border-radius: 8px; padding: 16px; font-size: 13px; }}
      .method-box h4 {{ margin-bottom: 8px; font-size: 14px; }}
      .method-box ul {{ padding-left: 20px; }}
      .method-box li {{ margin-bottom: 4px; }}
      .change-box {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; margin-top: 12px; font-size: 13px; }}
      .change-box strong {{ color: #15803d; }}
      @media (max-width: 768px) {{ .container {{ padding: 12px; }} .header {{ padding: 24px 16px; }} .header h1 {{ font-size: 20px; }} .stats-grid {{ grid-template-columns: 1fr 1fr; }} }}
    </style>
    </head>
    <body>

    <div class="header">
      <div class="container">
        <h1>方言电影数据详细报告</h1>
        <div class="subtitle">中国电影语言字段与方言占比分析 — 严格中国语言标准</div>
        <div class="meta">数据范围：中国制片电影 {summary["total_china"]:,} 部 | 方言片（中国方言/少数民族语言）{summary["total_dialect"]:,} 部 | 明细表{'含全部中国制片电影（含非方言对照）' if showing_all else '仅含方言/少数民族语言电影'} | 生成日期：2026-08-18</div>
        <span class="badge-rev">2026修订版 v2.1 — 纳入中国少数民族语言 — 第一语言检查（方案 A）— 自包含文件（无需外部依赖）</span>
      </div>
    </div>

    <div class="container">

      <div class="change-box">
        <strong>本次修订要点（v2.1 严格口径 + 2026-08-15 数据清洗终态）</strong>
        <ul style="margin-top:6px;padding-left:20px">
          <li>移除 Tier 1* 间接判定规则（原 784 部不再计入方言片）</li>
          <li>研究对象严格限定为<strong>中国境内使用的方言/少数民族语言</strong>（粤语、闽南语、吴语、西南官话、客家话、湘语、赣语、晋语、徽语、平话，以及藏语、维吾尔语、蒙古语、哈萨克语、苗语、彝语等中国少数民族语言）；排除所有外语（英语、日语、韩语、法语、德语、意大利语、西班牙语、俄语等）及手语、戏曲声腔</li>
          <li><strong>应用“第一语言检查”规则（方案 A）</strong>：语言字段首位标签（归一化后）为外语的影片判为外语为主，移出口径——实测移除 54 部（Tier 1 −21 / Tier 2b −33）；另有 355 部含外语标签但非排首的影片保留并标注</li>
          <li><strong>Tier 2b 证据审查（v4.1）</strong>：普通话排首+方言标签的 702 部默认排除，经证据漏斗（方言标签数/位置/简介/Gemini评价）自动补回 63 部 + 逐部补判确认 286 部，后经用户人工复核移出《芒种》1 部，共保留 348 部（2026-08-18 戏曲/演唱会审计另移出《卷席筒》《五女拜寿》2 部 → 现行基线 346）；净移除 {TIER2B_EXCLUDED} 部（含邵氏国语配音片等假阳性群），补回依据逐部见 Dialect_Evidence 列与 data/tier2b_evidence.csv / tier2b_recovered.csv</li>
          <li>审计修正已落地：白名单补收《碎片》《四个春天》《村戏》3 部；删除境外方言假阳性 4 部、“朝鲜语”国别歧义 17 部、豆瓣无评分 1 部</li>
          <li>方言片从上一版报告的 {PREV_DIALECT_TOTAL:,} 部 → <strong>{summary["total_dialect"]:,} 部</strong>（净减 {TIER2B_EXCLUDED} 部：v4.1 Tier 2b 证据审查 + 2026-08-18 戏曲/演唱会审计排除 49 部）；最终层级 Tier 1 = {summary["tier1_pure"]:,} / Tier 2a = {summary["tier2a_dialect_first"]:,} / Tier 2b = {summary["tier2b_mandarin_first"]:,}（证据补回白名单）</li>
        </ul>
      </div>

      <div class="section" style="margin-top:24px">
        <div class="section-title"><span class="num">1</span> 总览统计</div>
        <div class="stats-grid">
          <div class="stat-card"><div class="label">中国电影总数</div><div class="value">{summary["total_china"]:,}</div><div class="sub">Region = China</div></div>
          <div class="stat-card"><div class="label">方言片（中国语言）</div><div class="value" style="color:var(--accent)">{summary["total_dialect"]:,}</div><div class="sub">占中国电影 {summary["dialect_pct_of_china"]}%</div></div>
          <div class="stat-card"><div class="label">普通话/非方言片</div><div class="value">{summary["total_nondialect"]:,}</div><div class="sub">占中国电影 {summary["total_nondialect"]/summary["total_china"]*100:.1f}%</div></div>
          <div class="stat-card"><div class="label">Tier 1 纯方言片</div><div class="value" style="color:var(--tier1)">{summary["tier1_pure"]:,}</div><div class="sub">占方言片 {summary["tier1_pct"]}%</div></div>
        </div>
        <div class="stats-grid" style="margin-top:16px">
          <div class="stat-card"><div class="label">Tier 2a 方言排首位</div><div class="value" style="color:var(--tier2a)">{summary["tier2a_dialect_first"]}</div><div class="sub">混合方言片</div></div>
          <div class="stat-card"><div class="label">Tier 2b 普通话排首位</div><div class="value" style="color:var(--tier2b)">{summary["tier2b_mandarin_first"]}</div><div class="sub">混合方言片</div></div>
          <div class="stat-card"><div class="label">Tier 2 混合合计</div><div class="value">{summary["tier2a_dialect_first"]+summary["tier2b_mandarin_first"]}</div><div class="sub">占方言片 {summary["tier2_pct"]}%</div></div>
          <div class="stat-card"><div class="label">vs 上一版报告（{PREV_DIALECT_TOTAL:,} 部）</div><div class="value" style="color:var(--accent)">-{TIER2B_EXCLUDED}</div><div class="sub">Tier 2b 证据审查 + 戏曲/演唱会审计</div></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title"><span class="num">2</span> 各层级评分对比</div>
        <table class="tier-table">
          <thead><tr><th>层级</th><th>说明</th><th>信号强度</th><th>数量</th><th>均分</th><th>烂片率(&lt;5分)</th><th>高分率(&ge;8分)</th></tr></thead>
          <tbody>
            <tr><td><span class="badge badge-tier1">Tier 1</span></td><td>纯方言片：语言字段含中国方言/少数民族语言标签，不含普通话标签</td><td><span class="badge badge-tier1">强信号</span></td><td>{summary["Tier1_count"]}</td><td><strong>{summary["Tier1_avg"]}</strong></td><td>{summary["Tier1_low_rate"]}%</td><td>{summary["Tier1_high_rate"]}%</td></tr>
            <tr><td><span class="badge badge-tier2a">Tier 2a</span></td><td>混合方言片：中国方言/少数民族语言标签排在语言字段第一位</td><td><span class="badge badge-tier2a">中信号</span></td><td>{summary["Tier2a_count"]}</td><td><strong>{summary["Tier2a_avg"]}</strong></td><td>{summary["Tier2a_low_rate"]}%</td><td>{summary["Tier2a_high_rate"]}%</td></tr>
            <tr><td><span class="badge badge-tier2b">Tier 2b</span></td><td>混合方言片：普通话标签排第一，中国方言/少数民族语言标签在后</td><td><span class="badge badge-tier2b">弱信号</span></td><td>{summary["Tier2b_count"]}</td><td><strong>{summary["Tier2b_avg"]}</strong></td><td>{summary["Tier2b_low_rate"]}%</td><td>{summary["Tier2b_high_rate"]}%</td></tr>
            <tr style="background:#fff8e1"><td><strong>方言片合计</strong></td><td>Tier 1 + Tier 2a + Tier 2b（中国方言/少数民族语言）</td><td>—</td><td><strong>{summary["全部方言_count"]}</strong></td><td><strong>{summary["全部方言_avg"]}</strong></td><td><strong>{summary["全部方言_low_rate"]}%</strong></td><td><strong>{summary["全部方言_high_rate"]}%</strong></td></tr>
            <tr><td><span class="badge badge-nond">非方言</span></td><td>普通话/非方言片（Is_Dialect=0）</td><td>—</td><td>{summary["普通话片_count"]}</td><td><strong>{summary["普通话片_avg"]}</strong></td><td>{summary["普通话片_low_rate"]}%</td><td>{summary["普通话片_high_rate"]}%</td></tr>
          </tbody>
        </table>
        <div class="note"><strong>关键发现（修订后结论不变）：</strong>方言片均分（{summary["全部方言_avg"]}）显著高于普通话片（{summary["普通话片_avg"]}），烂片率（{summary["全部方言_low_rate"]}%）仅为普通话片（{summary["普通话片_low_rate"]}%）的 1/{summary["普通话片_low_rate"]/summary["全部方言_low_rate"]:.1f}。</div>
        <div class="note" style="margin-top:6px"><strong>Tier 口径说明（F8，2026-08-15）：</strong>Tier 表示方言标签的<strong>信号强度</strong>（强/中/弱），而非对白占比实测值。占比均为基于标签结构与排序的推断值（非实测），报告中一律标注"推断"。口径出处：v3 文档第五节，已固化于 <code>dialect_defs.py</code> 模块注释。</div>
      </div>

      <div class="section">
        <div class="section-title"><span class="num">3</span> 中国方言大区分布</div>
        <div id="dialect-group-dist"></div>
        <div class="note-info"><strong>说明：</strong>上表统计方言片中各中国方言/少数民族语言大区的出现频次。粤语以 {summary["dialect_group_dist"][0][1]} 次占据绝对主导。</div>
      </div>

      <div class="section">
        <div class="section-title"><span class="num">4</span> 方言片语言标签分布（TOP 20）</div>
        <div id="lang-dist"></div>
        <div class="note"><strong>说明：</strong>豆瓣"语言"字段为标签型元数据，标注影片中"出现过"的语言，而非对白占比。本图已做标签归一化："汉语普通话""国语""普通话/国语"等统一合并为"普通话"，便于读者直观看到方言片中标准语与方言的共存关系。"普通话"出现在本图是因为大量方言片（尤其 Tier 2 混合片）同时含有普通话对白，而非普通话本身是方言。</div>
      </div>

      <div class="section">
        <div class="section-title"><span class="num">5</span> 方言判定方法论与字段说明（严格版 v2.1）</div>
        <div class="method-box">
          <h4>研究对象范围</h4>
          <p>严格限定为<strong>中国境内使用的语言</strong>拍摄的电影，包括两类：（1）汉语各方言（十大方言区：粤语、闽南语、吴语、西南官话、客家话、湘语、赣语、晋语、徽语、平话）；（2）中国境内少数民族语言（藏语、维吾尔语、蒙古语、哈萨克语、苗语、彝语、壮语、傣语、侗语、瑶语、白语、哈尼语、傈僳语、佤语、拉祜语、纳西语、锡伯语、朝鲜语等）。</p>
          <h4 style="margin-top:12px">排除范围</h4>
          <ul><li><strong>外语</strong>：英语、日语、韩语（한국어）、法语、德语、意大利语、西班牙语、俄语等</li><li><strong>手语</strong>、<strong>戏曲声腔</strong></li></ul>
          <h4 style="margin-top:12px">操作化判定规则</h4>
          <ul>
            <li><strong>Is_Dialect = 0</strong>：语言字段不含任何中国方言/少数民族语言标签</li>
            <li><strong>Is_Dialect = 1, Tier 1</strong>：含中国方言/少数民族语言标签 + 不含普通话标签 → 纯方言片（强信号）</li>
            <li><strong>Is_Dialect = 1, Tier 2a</strong>：含中国方言/少数民族语言标签 + 含普通话标签，方言排第一 → 混合方言片（中信号）</li>
            <li><strong>Is_Dialect = 1, Tier 2b</strong>：含中国方言/少数民族语言标签 + 含普通话标签，普通话排第一，且通过 v4.1 证据审查（Dialect_Evidence 补回证据非空）→ 混合方言片（弱信号，白名单保留）</li>
            <li><strong>第一语言检查（方案 A，2026-08-15）</strong>：命中方言白名单标签、但语言字段首位标签（归一化后）为外语 → 判为外语为主，Is_Dialect = 0（实测移除 54 部：Tier 1 −21 / Tier 2b −33）</li>
            <li><strong>Tier 2b 证据审查（v4.1，2026-08-15）</strong>：普通话排首+方言标签的影片默认 Is_Dialect = 0，仅经证据漏斗（E1 方言标签≥2个 / E2 方言居第2位 / E3 简介命中 / E4 Gemini评价提及）或逐部补判（BENCHMARK/LLM_JUDGE）进入白名单才保留（实测 702 部中保留 348 部、移除 {TIER2B_EXCLUDED} 部）</li>
          </ul>
          <h4 style="margin-top:12px">已知偏差</h4>
          <ul><li>豆瓣标注"出现过的所有语言"而非"主要对白语言"</li><li>"方言占比"字段为基于标签的近似估算</li><li>外语为主但含方言标签的影片：已通过"第一语言检查"移除外语排首的 54 部；另有 355 部含外语标签但非排首者经标注后保留（见 data/plan_a_foreign_annotated.csv），仍可能存在边缘案例偏差</li><li>Tier 2b 证据审查中被默认排除的 {TIER2B_EXCLUDED} 部（含 29 部补判 uncertain）可能存在个别漏网方言片；标杆影片与低置信案例已标记强制人工复核（见 data/review_queue.csv）</li><li>少数民族语言标签与外语标签个别情况下可能混用（审计已移除"朝鲜语"国别歧义 17 部、境外方言假阳性 4 部；F7 交叉验证脚本见 scripts/verify_f7_cross_border.py，发现蒙古语/哈萨克语等跨境标签存在同类歧义，待后续处理）</li><li>豆瓣语言字段含国家名/错拼等噪声标签（如意大利、瑞士语、菏兰语，审计实测 19+7 部），判定以白名单命中为准，噪声标签自动落为非方言，不影响 China 口径</li><li>对照组（普通话/非方言）含 84 部语言字段缺失影片（占 1.1%），无法判断是否含未标注方言，按非方言处理；已抽样核对 10 部（seed=42，见 data/empty_language_china_sample10.csv），未发现漏标方言片</li></ul>
        </div>
      </div>

      <div class="section">
        <div class="section-title"><span class="num">6</span> 电影数据明细表（可搜索/筛选/排序）— 共 {num_movies:,} 部{f'（仅方言/少数民族语言电影）' if not showing_all else ''}</div>
        <div class="filter-bar">
          <input type="text" id="search-input" placeholder="搜索片名、导演、语言..." oninput="applyFilters()">
          <select id="tier-filter" onchange="applyFilters()">
            <option value="">全部层级</option>
            <option value="Tier 1">Tier 1 纯方言片</option>
            <option value="Tier 2a">Tier 2a 方言排首位</option>
            <option value="Tier 2b">Tier 2b 普通话排首位</option>
            <option value="非方言">非方言片</option>
          </select>
          <select id="sort-select" onchange="applyFilters()">
            <option value="tier_year">按层级+年份</option>
            <option value="rating_desc">评分降序</option>
            <option value="rating_asc">评分升序</option>
            <option value="year_asc">年份升序</option>
            <option value="year_desc">年份降序</option>
            <option value="votes_desc">评价人数降序</option>
          </select>
          <button class="btn btn-outline" onclick="resetFilters()">重置</button>
          <button class="btn btn-primary" onclick="exportCSV()">导出CSV</button>
        </div>
        <div class="table-wrap" style="max-height:600px;overflow-y:auto">
          <table class="movie-table" id="movie-table">
            <thead>
              <tr>
                <th style="width:40px">#</th><th>片名</th><th onclick="sortBy('year')">年份 ↕</th><th onclick="sortBy('rating')">评分 ↕</th><th onclick="sortBy('votes')">评价人数 ↕</th>
                <th>语言字段（原始）</th><th>方言标签</th><th>层级</th><th>方言占比说明</th><th>信号</th>
              </tr>
            </thead>
            <tbody id="table-body">
    {rows_html}
            </tbody>
          </table>
        </div>
        <div class="pagination" id="pagination">
          <span class="info" id="init-msg" style="color:var(--text-muted)">正在初始化表格…</span>
        </div>
      </div>

    </div>

    <script>
    // === Data extraction from static rows (fast, no DOM reflow) ===
    const PAGE_SIZE = 50;
    const STATIC_ROWS = document.querySelectorAll('#table-body tr');
    const MOVIE_DATA = [];
    for (var i = 0; i < STATIC_ROWS.length; i++) {{
      var r = STATIC_ROWS[i];
      MOVIE_DATA.push({{
        html: r.innerHTML,
        tier: r.dataset.tier || '',
        year: parseFloat(r.dataset.year) || 0,
        rating: parseFloat(r.dataset.rating) || 0,
        votes: parseFloat(r.dataset.votes) || 0,
        search: r.dataset.search || ''
      }});
    }}
    // Clear static rows; we'll render from MOVIE_DATA
    document.getElementById('table-body').innerHTML = '';

    var filteredData = MOVIE_DATA.slice();
    var currentPage = 1;

    function getTierOrder(tier) {{
      var order = {{'Tier 1':0,'Tier 2a':1,'Tier 2b':2,'非方言':3}};
      return order[tier] !== undefined ? order[tier] : 4;
    }}

    function applyFilters() {{
      var search = document.getElementById('search-input').value.toLowerCase().trim();
      var tier = document.getElementById('tier-filter').value;
      var sortByVal = document.getElementById('sort-select').value;

      filteredData = MOVIE_DATA.filter(function(m) {{
        if (tier && m.tier !== tier) return false;
        if (search && m.search.indexOf(search) === -1) return false;
        return true;
      }});

      // Sort (on plain JS objects — no DOM manipulation)
      var sorters = {{
        'tier_year': function(a, b) {{
          var oa = getTierOrder(a.tier), ob = getTierOrder(b.tier);
          if (oa !== ob) return oa - ob;
          return a.year - b.year;
        }},
        'rating_desc': function(a, b) {{ return b.rating - a.rating; }},
        'rating_asc': function(a, b) {{ return a.rating - b.rating; }},
        'year_asc': function(a, b) {{ return a.year - b.year; }},
        'year_desc': function(a, b) {{ return b.year - a.year; }},
        'votes_desc': function(a, b) {{ return b.votes - a.votes; }}
      }};
      filteredData.sort(sorters[sortByVal] || sorters['tier_year']);

      currentPage = 1;
      renderTable();
    }}

    function sortBy(field) {{
      var select = document.getElementById('sort-select');
      var map = {{ year: 'year_asc', rating: 'rating_desc', votes: 'votes_desc' }};
      select.value = map[field] || 'tier_year';
      applyFilters();
    }}

    function renderTable() {{
      var total = filteredData.length;
      var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      if (currentPage > totalPages) currentPage = totalPages;
      var start = (currentPage - 1) * PAGE_SIZE;
      var end = Math.min(start + PAGE_SIZE, total);

      // Build HTML string for current page only — single innerHTML set
      var parts = [];
      for (var i = start; i < end; i++) {{
        parts.push('<tr>' + filteredData[i].html + '</tr>');
      }}
      document.getElementById('table-body').innerHTML = parts.join('');

      renderPagination(total, totalPages);
    }}

    function renderPagination(total, totalPages) {{
      var pag = document.getElementById('pagination');
      var html = '';
      html += '<button onclick="goPage(1)"' + (currentPage===1?' disabled':'') + '>首页</button>';
      html += '<button onclick="goPage(' + (currentPage-1) + ')"' + (currentPage===1?' disabled':'') + '>上一页</button>';
      var maxButtons = 7;
      var startPage = Math.max(1, currentPage - 3);
      var endPage = Math.min(totalPages, startPage + maxButtons - 1);
      if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);
      for (var p = startPage; p <= endPage; p++) {{
        html += '<button onclick="goPage(' + p + ')"' + (p===currentPage?' class="active"':'') + '>' + p + '</button>';
      }}
      html += '<button onclick="goPage(' + (currentPage+1) + ')"' + (currentPage>=totalPages?' disabled':'') + '>下一页</button>';
      html += '<button onclick="goPage(' + totalPages + ')"' + (currentPage>=totalPages?' disabled':'') + '>末页</button>';
      html += '<span class="info">共 ' + total.toLocaleString() + ' 条，第 ' + currentPage + '/' + totalPages + ' 页</span>';
      pag.innerHTML = html;
    }}

    function goPage(p) {{
      currentPage = p;
      renderTable();
      document.getElementById('movie-table').scrollIntoView({{behavior:'smooth',block:'nearest'}});
    }}

    function resetFilters() {{
      document.getElementById('search-input').value = '';
      document.getElementById('tier-filter').value = '';
      document.getElementById('sort-select').value = 'tier_year';
      applyFilters();
    }}

    function exportCSV() {{
      var headers = ['#','片名','年份','豆瓣评分','评价人数','语言字段','方言标签','方言层级','方言占比说明','信号强度'];
      var csv = headers.join(',') + '\\n';
      filteredData.forEach(function(row) {{
        // Parse the stored row HTML to extract text content
        var tmp = document.createElement('tr');
        tmp.innerHTML = row.html;
        var cells = tmp.querySelectorAll('td');
        var text = function(i) {{
          return cells[i] ? cells[i].textContent.replace(/"/g, '""').replace(/\\n/g, ' ') : '';
        }};
        var rowData = [text(0), text(1), text(2), text(3), text(4), text(5), text(6), text(7), text(8), text(9)];
        csv += rowData.map(function(v) {{ return '"' + v + '"'; }}).join(',') + '\\n';
      }});
      var blob = new Blob(['\ufeff' + csv], {{type:'text/csv;charset=utf-8'}});
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = '方言电影数据明细_严格中国语言标准.csv';
      a.click();
      URL.revokeObjectURL(url);
    }}

    function renderLangDist() {{
      var langData = {json.dumps(summary["dialect_lang_tags_top20"], ensure_ascii=False)};
      var maxCount = langData[0][1];
      var colors = ['#e63946','#f77f00','#fcbf49','#06d6a0','#118ab2','#073b4c','#9b5de5','#f15bb5','#00bbf9','#00f5d4','#ff6b6b','#ffd93d','#6bcf7f','#4d96ff','#c780fa','#ffa45c','#5f0f40','#0b4f6c','#01baef','#20a39e'];
      var container = document.getElementById('lang-dist');
      container.innerHTML = langData.map(function(item, i) {{
        var lang = item[0], count = item[1];
        var pct = (count / maxCount * 100).toFixed(1);
        var color = colors[i % colors.length];
        return '<div class="lang-bar"><span class="lang-name">' + escapeHtml(lang) + '</span><div class="bar-wrap"><div class="bar" style="width:' + pct + '%;background:' + color + '"></div></div><span class="count">' + count + '</span></div>';
      }}).join('');
    }}

    function renderDialectGroupDist() {{
      var groupData = {json.dumps(summary["dialect_group_dist"], ensure_ascii=False)};
      var maxCount = groupData[0][1];
      var colors = ['#e63946','#f77f00','#fcbf49','#06d6a0','#118ab2','#9b5de5','#f15bb5','#00bbf9','#00f5d4','#ff6b6b','#ffd93d','#6bcf7f','#4d96ff','#c780fa','#ffa45c'];
      var container = document.getElementById('dialect-group-dist');
      container.innerHTML = groupData.map(function(item, i) {{
        var group = item[0], count = item[1];
        var pct = (count / maxCount * 100).toFixed(1);
        var color = colors[i % colors.length];
        return '<div class="lang-bar"><span class="lang-name" style="width:180px;font-size:11px">' + escapeHtml(group) + '</span><div class="bar-wrap"><div class="bar" style="width:' + pct + '%;background:' + color + '"></div></div><span class="count">' + count + '</span></div>';
      }}).join('');
    }}

    function escapeHtml(text) {{
      if (!text) return '';
      var div = document.createElement('div');
      div.textContent = String(text);
      return div.innerHTML;
    }}

    renderDialectGroupDist();
    renderLangDist();
    applyFilters();
    </script>
    </body>
    </html>
    """

    output_path = base / output_filename
    output_path.write_text(html, encoding="utf-8")
    print(f"Report generated: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Total rows embedded: {num_movies:,}")


# 生成分言片版（默认）
dialect_movies = [m for m in data["movies"] if m["id"] == 1]
generate_report(dialect_movies, "方言电影数据详细报告.html", False)

# 生成完整版（全部中国电影）
generate_report(data["movies"], "方言电影数据详细报告_完整版.html", True)
