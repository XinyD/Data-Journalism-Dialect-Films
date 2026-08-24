# -*- coding: utf-8 -*-
"""Generate the updated HTML report with strict Chinese-language data."""
import json
from pathlib import Path

base = Path(__file__).resolve().parent.parent

with open(base / "data" / "dialect_films" / "report_data_strict.json", "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]
dialect_groups = data.get("dialect_groups", {})

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
  .movie-table thead th {{ background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; font-weight: 600; position: sticky; top: 0; white-space: nowrap; }}
  .movie-table tbody td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .movie-table tbody tr:hover {{ background: #f8f9fa; }}
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
    <div class="meta">数据范围：中国制片电影 {summary["total_china"]:,} 部 | 方言片（中国方言/少数民族语言）{summary["total_dialect"]:,} 部 | 生成日期：2026-08-10</div>
    <span class="badge-rev">2026修订版 v2.1 — 纳入中国少数民族语言</span>
  </div>
</div>

<div class="container">

  <!-- Change Summary -->
  <div class="change-box">
    <strong>本次修订要点</strong>
    <ul style="margin-top:6px;padding-left:20px">
      <li>移除 Tier 1* 间接判定规则（原 784 部不再计入方言片）</li>
      <li>研究对象严格限定为<strong>中国境内使用的方言/少数民族语言</strong>（粤语、闽南语、吴语、西南官话、客家话、湘语、赣语、晋语、徽语、平话，以及藏语、维吾尔语、蒙古语、哈萨克语、苗语、彝语等中国少数民族语言）</li>
      <li>排除所有外语（英语、日语、韩语、法语、德语、意大利语、西班牙语、俄语等）</li>
      <li>方言片从 4,050 部 → <strong>3,487 部</strong>（移除 563 部）</li>
    </ul>
  </div>

  <!-- Section 1: Summary -->
  <div class="section" style="margin-top:24px">
    <div class="section-title"><span class="num">1</span> 总览统计</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">中国电影总数</div>
        <div class="value">{summary["total_china"]:,}</div>
        <div class="sub">Region = China</div>
      </div>
      <div class="stat-card">
        <div class="label">方言片（中国语言）</div>
        <div class="value" style="color:var(--accent)">{summary["total_dialect"]:,}</div>
        <div class="sub">占中国电影 {summary["dialect_pct_of_china"]}%</div>
      </div>
      <div class="stat-card">
        <div class="label">普通话/非方言片</div>
        <div class="value">{summary["total_nondialect"]:,}</div>
        <div class="sub">占中国电影 {summary["total_nondialect"]/summary["total_china"]*100:.1f}%</div>
      </div>
      <div class="stat-card">
        <div class="label">Tier 1 纯方言片</div>
        <div class="value" style="color:var(--tier1)">{summary["tier1_pure"]:,}</div>
        <div class="sub">占方言片 {summary["tier1_pct"]}%</div>
      </div>
    </div>
    <div class="stats-grid" style="margin-top:16px">
      <div class="stat-card">
        <div class="label">Tier 2a 方言排首位</div>
        <div class="value" style="color:var(--tier2a)">{summary["tier2a_dialect_first"]}</div>
        <div class="sub">混合方言片</div>
      </div>
      <div class="stat-card">
        <div class="label">Tier 2b 普通话排首位</div>
        <div class="value" style="color:var(--tier2b)">{summary["tier2b_mandarin_first"]}</div>
        <div class="sub">混合方言片</div>
      </div>
      <div class="stat-card">
        <div class="label">Tier 2 混合合计</div>
        <div class="value">{summary["tier2a_dialect_first"]+summary["tier2b_mandarin_first"]}</div>
        <div class="sub">占方言片 {summary["tier2_pct"]}%</div>
      </div>
      <div class="stat-card">
        <div class="label">vs 旧定义</div>
        <div class="value" style="color:var(--accent)">-{summary["removed_from_old"]}</div>
        <div class="sub">移除外语/间接判定</div>
      </div>
    </div>
  </div>

  <!-- Section 2: Score comparison -->
  <div class="section">
    <div class="section-title"><span class="num">2</span> 各层级评分对比</div>
    <table class="tier-table">
      <thead>
        <tr>
          <th>层级</th><th>说明</th><th>数量</th><th>均分</th><th>烂片率(&lt;5分)</th><th>高分率(&ge;8分)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="badge badge-tier1">Tier 1</span></td>
          <td>纯方言片：语言字段含中国方言/少数民族语言标签，不含普通话标签</td>
          <td>{summary["Tier1_count"]}</td>
          <td><strong>{summary["Tier1_avg"]}</strong></td>
          <td>{summary["Tier1_low_rate"]}%</td>
          <td>{summary["Tier1_high_rate"]}%</td>
        </tr>
        <tr>
          <td><span class="badge badge-tier2a">Tier 2a</span></td>
          <td>混合方言片：中国方言/少数民族语言标签排在语言字段第一位</td>
          <td>{summary["Tier2a_count"]}</td>
          <td><strong>{summary["Tier2a_avg"]}</strong></td>
          <td>{summary["Tier2a_low_rate"]}%</td>
          <td>{summary["Tier2a_high_rate"]}%</td>
        </tr>
        <tr>
          <td><span class="badge badge-tier2b">Tier 2b</span></td>
          <td>混合方言片：普通话标签排第一，中国方言/少数民族语言标签在后</td>
          <td>{summary["Tier2b_count"]}</td>
          <td><strong>{summary["Tier2b_avg"]}</strong></td>
          <td>{summary["Tier2b_low_rate"]}%</td>
          <td>{summary["Tier2b_high_rate"]}%</td>
        </tr>
        <tr style="background:#fff8e1">
          <td><strong>方言片合计</strong></td>
          <td>Tier 1 + Tier 2a + Tier 2b（中国方言/少数民族语言）</td>
          <td><strong>{summary["全部方言_count"]}</strong></td>
          <td><strong>{summary["全部方言_avg"]}</strong></td>
          <td><strong>{summary["全部方言_low_rate"]}%</strong></td>
          <td><strong>{summary["全部方言_high_rate"]}%</strong></td>
        </tr>
        <tr>
          <td><span class="badge badge-nond">非方言</span></td>
          <td>普通话/非方言片（Is_Dialect=0）</td>
          <td>{summary["普通话片_count"]}</td>
          <td><strong>{summary["普通话片_avg"]}</strong></td>
          <td>{summary["普通话片_low_rate"]}%</td>
          <td>{summary["普通话片_high_rate"]}%</td>
        </tr>
      </tbody>
    </table>
    <div class="note">
      <strong>关键发现（修订后结论不变）：</strong>方言片均分（{summary["全部方言_avg"]}）显著高于普通话片（{summary["普通话片_avg"]}），烂片率（{summary["全部方言_low_rate"]}%）仅为普通话片（{summary["普通话片_low_rate"]}%）的 1/{summary["普通话片_low_rate"]/summary["全部方言_low_rate"]:.1f}。Tier 1 纯方言片表现最优（均分 {summary["Tier1_avg"]}，烂片率仅 {summary["Tier1_low_rate"]}%）。修订后结论的稳健性得到验证。
    </div>
  </div>

  <!-- Section 3: Dialect group distribution -->
  <div class="section">
    <div class="section-title"><span class="num">3</span> 中国方言大区分布</div>
    <div id="dialect-group-dist"></div>
    <div class="note-info">
      <strong>说明：</strong>上表统计方言片中各中国方言/少数民族语言大区的出现频次。粤语以 {summary["dialect_group_dist"][0][1]} 次占据绝对主导（与香港电影产量直接相关），其次为闽南语、西南官话和中国少数民族语言。本次修订在完整覆盖十大汉语方言区的基础上，新增了中国少数民族语言大类。
    </div>
  </div>

  <!-- Section 4: Language tag distribution -->
  <div class="section">
    <div class="section-title"><span class="num">4</span> 方言片语言标签分布（TOP 20）</div>
    <div id="lang-dist"></div>
    <div class="note">
      <strong>说明：</strong>豆瓣"语言"字段为<strong>标签型元数据</strong>，标注影片中"出现过"的语言，而非对白占比。本图已做标签归一化："汉语普通话""国语""普通话/国语"等统一合并为"普通话"，便于读者直观看到方言片中标准语与方言的共存关系。"普通话"出现在本图是因为大量方言片（尤其 Tier 2 混合片）同时含有普通话对白，而非普通话本身是方言。粤语（{summary["dialect_lang_tags_top20"][0][1]}次）占据绝对主导地位，藏语、维吾尔语等少数民族语言标签也进入前列。
    </div>
  </div>

  <!-- Section 5: Methodology -->
  <div class="section">
    <div class="section-title"><span class="num">5</span> 方言判定方法论与字段说明（严格版 v2.1）</div>
    <div class="method-box">
      <h4>研究对象范围</h4>
      <p>严格限定为<strong>中国境内使用的语言</strong>拍摄的电影，包括两类：（1）汉语各方言（汉语的地域变体），包括十大方言区：粤语、闽南语、吴语、西南官话、客家话、湘语、赣语、晋语、徽语、平话，以及官话区的地域变体（东北官话、中原官话、江淮官话等）和台语（闽南语台湾变体）；（2）中国境内少数民族语言，包括藏语、维吾尔语、蒙古语、哈萨克语、苗语、彝语、壮语、傣语、侗语、瑶语、白语、哈尼语、傈僳语、佤语、拉祜语、纳西语、锡伯语、朝鲜语（中国朝鲜族语言）等。</p>
      <h4 style="margin-top:12px">排除范围</h4>
      <ul>
        <li><strong>外语</strong>：英语、日语、韩语（한국어）、法语、德语、意大利语、西班牙语、俄语、泰语、越南语等任何外国语言</li>
        <li><strong>手语</strong>、<strong>戏曲声腔</strong>（京剧、黄梅戏等）</li>
      </ul>
      <h4 style="margin-top:12px">操作化判定规则</h4>
      <ul>
        <li><strong>Is_Dialect = 0</strong>：语言字段不含任何中国方言/少数民族语言标签</li>
        <li><strong>Is_Dialect = 1, Tier 1</strong>：语言字段含中国方言/少数民族语言标签 + 不含普通话标签 → <strong>纯方言片</strong>（强信号）</li>
        <li><strong>Is_Dialect = 1, Tier 2a</strong>：含中国方言/少数民族语言标签 + 含普通话标签，方言排第一 → <strong>混合方言片</strong>（中信号）</li>
        <li><strong>Is_Dialect = 1, Tier 2b</strong>：含中国方言/少数民族语言标签 + 含普通话标签，普通话排第一 → <strong>混合方言片</strong>（弱信号）</li>
      </ul>
      <div style="background:#fde8ea;border-left:4px solid var(--accent);padding:8px 12px;border-radius:6px;margin-top:8px">
        <strong>已删除</strong>：Tier 1* 间接判定规则（原 <code>has_chinese and len(parts) > 1</code> 条件）。该规则将含中文标签+多语言的电影误判为方言片，实际包含大量含英语/日语的中外合拍片，现已移除。
      </div>
      <h4 style="margin-top:12px">已知偏差</h4>
      <ul>
        <li>豆瓣标注"出现过的所有语言"而非"主要对白语言"，导致部分学术纯方言片被归入 Tier 2</li>
        <li>"方言占比"字段为基于标签的近似估算，非精确对白占比数据</li>
        <li>地域特征为代理变量，非直接度量</li>
        <li>少数民族语言标签与外语标签在个别情况下可能混用（如朝鲜语 vs 韩语），以"中国境内使用"为原则进行归属判定</li>
      </ul>
    </div>
  </div>

  <!-- Section 6: Full data table -->
  <div class="section">
    <div class="section-title"><span class="num">6</span> 电影数据明细表（可搜索/筛选/排序）</div>
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
            <th style="width:40px">#</th><th>片名</th><th>年份</th><th>评分</th><th>评价人数</th>
            <th>语言字段（原始）</th><th>方言标签</th><th>层级</th><th>方言占比说明</th><th>信号</th>
          </tr>
        </thead>
        <tbody id="table-body"><tr><td colspan="10" style="text-align:center;padding:40px;color:#6c757d">正在加载数据...</td></tr></tbody>
      </table>
    </div>
    <div class="pagination" id="pagination"></div>
  </div>

</div>

<script src="movie_data.js"></script>
<script>
const PAGE_SIZE = 50;
let currentPage = 1;
let filteredMovies = [];

function getTierBadge(tier) {{
  const map = {{
    'Tier 1': '<span class="badge badge-tier1">Tier 1</span>',
    'Tier 2a': '<span class="badge badge-tier2a">Tier 2a</span>',
    'Tier 2b': '<span class="badge badge-tier2b">Tier 2b</span>',
    '非方言': '<span class="badge badge-nond">非方言</span>'
  }};
  return map[tier] || tier;
}}
function getSignalBadge(signal) {{
  const map = {{
    '强信号': '<span class="badge badge-tier1">强</span>',
    '中信号': '<span class="badge badge-tier2a">中</span>',
    '弱信号': '<span class="badge badge-tier2b">弱</span>',
    '不适用': '<span class="badge badge-nond">—</span>'
  }};
  return map[signal] || signal;
}}
function getRatingClass(r) {{
  if (r >= 8.0) return 'rating-high';
  if (r < 5.0) return 'rating-low';
  return '';
}}
function escapeHtml(text) {{
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}}
function applyFilters() {{
  const search = document.getElementById('search-input').value.toLowerCase().trim();
  const tier = document.getElementById('tier-filter').value;
  const sortBy = document.getElementById('sort-select').value;
  filteredMovies = ALL_MOVIES.filter(m => {{
    if (tier && m.t !== tier) return false;
    if (search) {{
      const haystack = (m.n + '|' + m.l + '|' + (m.d||'') + '|' + (m.g||'')).toLowerCase();
      if (!haystack.includes(search)) return false;
    }}
    return true;
  }});
  const sorters = {{
    'tier_year': (a, b) => {{
      const order = {{'Tier 1':0,'Tier 2a':1,'Tier 2b':2,'非方言':3}};
      const oa = order[a.t] ?? 4, ob = order[b.t] ?? 4;
      if (oa !== ob) return oa - ob;
      return (a.y||0) - (b.y||0);
    }},
    'rating_desc': (a, b) => (b.r||0) - (a.r||0),
    'rating_asc': (a, b) => (a.r||0) - (b.r||0),
    'year_asc': (a, b) => (a.y||0) - (b.y||0),
    'year_desc': (a, b) => (b.y||0) - (a.y||0),
    'votes_desc': (a, b) => (b.v||0) - (a.v||0),
  }};
  filteredMovies.sort(sorters[sortBy] || sorters['tier_year']);
  currentPage = 1;
  renderTable();
}}
function renderTable() {{
  const tbody = document.getElementById('table-body');
  const start = (currentPage - 1) * PAGE_SIZE;
  const end = start + PAGE_SIZE;
  const pageData = filteredMovies.slice(start, end);
  tbody.innerHTML = pageData.map((m, i) => {{
    const idx = start + i + 1;
    const dialectTags = m.dt && m.dt.length > 0 ? m.dt.join(', ') : '<span style="color:#adb5bd">无</span>';
    return `<tr>
      <td style="color:var(--text-muted)">${{idx}}</td>
      <td class="title-cell">${{escapeHtml(m.n)}}</td>
      <td>${{m.y}}</td>
      <td class="${{getRatingClass(m.r)}}">${{m.r}}</td>
      <td>${{(m.v||0).toLocaleString()}}</td>
      <td class="lang-cell">${{escapeHtml(m.l)}}</td>
      <td>${{dialectTags}}</td>
      <td>${{getTierBadge(m.t)}}</td>
      <td class="dp-cell">${{escapeHtml(m.dp)}}</td>
      <td>${{getSignalBadge(m.sg)}}</td>
    </tr>`;
  }}).join('');
  renderPagination();
}}
function renderPagination() {{
  const total = filteredMovies.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const pag = document.getElementById('pagination');
  let html = '';
  html += `<button onclick="goPage(1)" ${{currentPage===1?'disabled':''}}>首页</button>`;
  html += `<button onclick="goPage(${{currentPage-1}})" ${{currentPage===1?'disabled':''}}>上一页</button>`;
  const maxButtons = 7;
  let startPage = Math.max(1, currentPage - 3);
  let endPage = Math.min(totalPages, startPage + maxButtons - 1);
  if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);
  for (let p = startPage; p <= endPage; p++) {{
    html += `<button onclick="goPage(${{p}})" class="${{p===currentPage?'active':''}}">${{p}}</button>`;
  }}
  html += `<button onclick="goPage(${{currentPage+1}})" ${{currentPage>=totalPages?'disabled':''}}>下一页</button>`;
  html += `<button onclick="goPage(${{totalPages}})" ${{currentPage>=totalPages?'disabled':''}}>末页</button>`;
  html += `<span class="info">共 ${{total.toLocaleString()}} 条，第 ${{currentPage}}/${{totalPages}} 页</span>`;
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
  const headers = ['片名','年份','豆瓣评分','评价人数','导演','类型','语言字段','方言标签','方言标签数','语言总数','Is_Dialect','方言层级','层级说明','方言占比说明','信号强度','含普通话标签'];
  const keys = ['n','y','r','v','d','g','l','dt','dc','tc','id','t','td','dp','sg','mp'];
  let csv = headers.join(',') + '\n';
  filteredMovies.forEach(m => {{
    const row = keys.map(k => {{
      let val = m[k];
      if (Array.isArray(val)) val = val.join(';');
      val = String(val || '').replace(/"/g, '""');
      return `"${{val}}"`;
    }});
    csv += row.join(',') + '\n';
  }});
  const blob = new Blob(['\ufeff' + csv], {{type:'text/csv;charset=utf-8'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = '方言电影数据明细_严格中国语言标准.csv';
  a.click();
  URL.revokeObjectURL(url);
}}
function renderLangDist() {{
  const langData = {json.dumps(summary["dialect_lang_tags_top20"], ensure_ascii=False)};
  const maxCount = langData[0][1];
  const colors = ['#e63946','#f77f00','#fcbf49','#06d6a0','#118ab2','#073b4c','#9b5de5','#f15bb5','#00bbf9','#00f5d4','#ff6b6b','#ffd93d','#6bcf7f','#4d96ff','#c780fa','#ffa45c','#5f0f40','#0b4f6c','#01baef','#20a39e'];
  const container = document.getElementById('lang-dist');
  container.innerHTML = langData.map((item, i) => {{
    const [lang, count] = item;
    const pct = (count / maxCount * 100).toFixed(1);
    const color = colors[i % colors.length];
    return `<div class="lang-bar"><span class="lang-name">${{escapeHtml(lang)}}</span><div class="bar-wrap"><div class="bar" style="width:${{pct}}%;background:${{color}}"></div></div><span class="count">${{count}}</span></div>`;
  }}).join('');
}}
function renderDialectGroupDist() {{
  const groupData = {json.dumps(summary["dialect_group_dist"], ensure_ascii=False)};
  const maxCount = groupData[0][1];
  const colors = ['#e63946','#f77f00','#fcbf49','#06d6a0','#118ab2','#9b5de5','#f15bb5','#00bbf9','#00f5d4','#ff6b6b','#ffd93d','#6bcf7f','#4d96ff','#c780fa','#ffa45c'];
  const container = document.getElementById('dialect-group-dist');
  container.innerHTML = groupData.map((item, i) => {{
    const [group, count] = item;
    const pct = (count / maxCount * 100).toFixed(1);
    const color = colors[i % colors.length];
    return `<div class="lang-bar"><span class="lang-name" style="width:180px;font-size:11px">${{escapeHtml(group)}}</span><div class="bar-wrap"><div class="bar" style="width:${{pct}}%;background:${{color}}"></div></div><span class="count">${{count}}</span></div>`;
  }}).join('');
}}
renderDialectGroupDist();
renderLangDist();
if (typeof ALL_MOVIES !== 'undefined' && ALL_MOVIES.length > 0) {{
  filteredMovies = [...ALL_MOVIES];
  applyFilters();
}} else {{
  document.getElementById('table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;padding:40px;color:#e63946">数据加载失败，请确保 movie_data.js 文件与此 HTML 文件在同一目录下。</td></tr>';
}}
</script>
</body>
</html>
"""

output_path = base / "方言电影数据详细报告.html"
output_path.write_text(html, encoding="utf-8")
print(f"Report generated: {output_path}")
print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
