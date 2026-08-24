#!/usr/bin/env python3
"""Remove non-dialect films from both reports and add Douban link column.

Report 1: 方言电影数据详细报告_完整版.html (11,121 films)
  → Remove data-tier="非方言" rows (7,634)
  → Keep 3,487 dialect films
  → Add 豆瓣链接 column

Report 2: foreign_primary_china_region_clean.csv (350 films)
  → Remove films classified as 非方言 in Report 1 (~150)
  → Keep ~200 films
  → Add 豆瓣链接 column (来源URL already in CSV)
"""

import csv
import re
import html as html_module

BASE = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main"
CSV_PATH = f"{BASE}/data/derived_movies.csv"
HTML_PATH = f"{BASE}/方言电影数据详细报告_完整版.html"
CLEAN_CSV_PATH = f"{BASE}/data/foreign_primary_china_region_clean.csv"

OUT_HTML = f"{BASE}/方言电影数据报告_仅方言片_含豆瓣链接.html"
OUT_CLEAN_HTML = f"{BASE}/外语为主方言片_含豆瓣链接.html"
OUT_CLEAN_CSV = f"{BASE}/外语为主方言片_含豆瓣链接.csv"


def extract_title_year(line):
    """Extract title and year from a <tr> line's data-search and data-year attributes."""
    search_match = re.search(r'data-search="([^"]*)"', line)
    year_match = re.search(r'data-year="([^"]*)"', line)
    if search_match and year_match:
        title = html_module.unescape(search_match.group(1).split('|')[0])
        year = year_match.group(1)
        return title, year
    return None, None


# ============================================================
# Step 1: Build URL lookup from derived_movies.csv (case-insensitive)
# ============================================================
print("Step 1: Building URL lookup from CSV...")
url_lookup = {}
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        title_cf = row.get('片名', '').casefold()
        year = row.get('年份', '')
        key = (title_cf, year)
        if key not in url_lookup:
            url_lookup[key] = row.get('来源URL', '')
print(f"  URL lookup: {len(url_lookup)} entries")


# ============================================================
# Step 2: Build non-dialect set + count dialect rows from HTML
# ============================================================
print("Step 2: Scanning HTML for non-dialect films...")
nondialect_set = set()
dialect_count = 0
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        if 'data-tier=' in line and '<tr' in line:
            title, year = extract_title_year(line)
            if title and year:
                if 'data-tier="非方言"' in line:
                    nondialect_set.add((title.casefold(), year))
                else:
                    dialect_count += 1
print(f"  Dialect films: {dialect_count}")
print(f"  Non-dialect films: {len(nondialect_set)}")


# ============================================================
# Step 3: Process 完整版 HTML — remove non-dialect, add links
# ============================================================
print("Step 3: Processing 完整版 HTML...")
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
url_found = 0
url_missing = 0

for line in lines:
    # --- Skip non-dialect rows ---
    if 'data-tier=' in line and '<tr' in line and 'data-tier="非方言"' in line:
        continue

    # --- Add Douban link cell to dialect rows ---
    if 'data-tier=' in line and '<tr' in line:
        title, year = extract_title_year(line)
        if title and year:
            url = url_lookup.get((title.casefold(), year), '')
            if url:
                url_found += 1
                link_cell = f'<td><a href="{url}" target="_blank" style="color:var(--accent);text-decoration:none">豆瓣\u2197</a></td>'
            else:
                url_missing += 1
                link_cell = '<td style="color:var(--text-muted)">\u2014</td>'
            line = line.replace('</tr>', link_cell + '</tr>')

    # --- Update <title> tag ---
    if '<title>' in line and '</title>' in line:
        line = line.replace(
            '方言电影数据详细报告',
            '方言电影数据报告（仅方言片·含豆瓣链接）'
        )

    # --- Update <h1> heading ---
    if '<h1>' in line and '方言电影数据详细报告' in line:
        line = line.replace('方言电影数据详细报告', '方言电影数据报告（仅方言片）')

    # --- Update header meta text ---
    if '数据范围：' in line and '11,121' in line:
        line = line.replace(
            '数据范围：中国制片电影 11,121 部 | 方言片（中国方言/少数民族语言）3,487 部 | 明细表含全部电影 | 生成日期：2026-08-10',
            f'数据范围：方言片（中国方言/少数民族语言）{dialect_count} 部 | 已移除非方言片 | 含豆瓣链接方便人工核查 | 生成日期：2026-08-14'
        )

    # --- Update section 6 title ---
    if '共 11,121 部' in line:
        line = line.replace('共 11,121 部', f'共 {dialect_count} 部（仅方言片）')

    # --- Remove "非方言" option from tier filter dropdown ---
    if 'value="非方言"' in line:
        continue

    # --- Add 豆瓣链接 to table header ---
    if '<th>信号</th>' in line and '<th>豆瓣链接</th>' not in line:
        line = line.replace('<th>信号</th>', '<th>信号</th><th>豆瓣链接</th>')

    # --- Update exportCSV: add '豆瓣链接' to headers ---
    if "var headers = ['#','片名'" in line and "'信号强度']" in line:
        line = line.replace("'信号强度'];", "'信号强度','豆瓣链接'];")

    # --- Update exportCSV: add link URL extraction to rowData ---
    if 'var rowData = [text(0)' in line and 'text(9)]' in line:
        line = line.replace(
            'var rowData = [text(0), text(1), text(2), text(3), text(4), text(5), text(6), text(7), text(8), text(9)];',
            "var linkUrl = ''; if (cells[10]) { var la = cells[10].querySelector('a'); if (la) linkUrl = la.getAttribute('href') || ''; }\n    var rowData = [text(0), text(1), text(2), text(3), text(4), text(5), text(6), text(7), text(8), text(9), linkUrl];"
        )

    new_lines.append(line)

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"  Dialect films kept: {dialect_count}")
print(f"  URLs found: {url_found}, missing: {url_missing}")
print(f"  Saved: {OUT_HTML}")


# ============================================================
# Step 4: Process cleaned data — remove non-dialect, add links
# ============================================================
print("\nStep 4: Processing cleaned data...")
cleaned_films = []
nondialect_removed = 0

with open(CLEAN_CSV_PATH, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        title = row.get('片名', '')
        year = row.get('年份', '')
        if (title.casefold(), year) in nondialect_set:
            nondialect_removed += 1
            continue
        cleaned_films.append(row)

print(f"  Original: 350 films")
print(f"  Removed (non-dialect in 完整版): {nondialect_removed}")
print(f"  Remaining: {len(cleaned_films)} films")

# Save filtered CSV
with open(OUT_CLEAN_CSV, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(cleaned_films)
print(f"  CSV saved: {OUT_CLEAN_CSV}")

# Generate HTML report for cleaned data
html_parts = []
html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>外语为主方言片 — 含豆瓣链接</title>
<style>
  :root {
    --bg: #f8f9fa; --card-bg: #fff; --text: #1a1a2e; --text-muted: #6c757d;
    --border: #dee2e6; --accent: #e63946; --accent-light: #fde8ea;
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-lg: 0 4px 12px rgba(0,0,0,0.1);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; font-size: 14px; }
  .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
  .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 36px 24px; border-radius: 0 0 24px 24px; box-shadow: var(--shadow-lg); margin-bottom: 24px; }
  .header h1 { font-size: 22px; margin-bottom: 6px; }
  .header .subtitle { font-size: 13px; opacity: 0.85; }
  .header .meta { font-size: 12px; opacity: 0.6; margin-top: 8px; }
  .section { background: var(--card-bg); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: var(--shadow); }
  .section-title { font-size: 16px; font-weight: 700; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 2px solid var(--border); }
  .note { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 14px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }
  .note strong { color: #856404; }
  .filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }
  .filter-bar input, .filter-bar select { padding: 7px 11px; border: 1px solid var(--border); border-radius: 7px; font-size: 13px; background: white; }
  .filter-bar input { flex: 1; min-width: 200px; }
  .table-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); max-height: 700px; overflow-y: auto; }
  .movie-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .movie-table thead th { background: #1a1a2e; color: white; padding: 8px 10px; text-align: left; font-weight: 600; position: sticky; top: 0; white-space: nowrap; z-index: 10; }
  .movie-table tbody td { padding: 6px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .movie-table tbody tr:hover { background: #f8f9fa; }
  .title-cell { font-weight: 600; max-width: 180px; }
  .lang-cell { max-width: 180px; word-break: break-all; }
  .dp-cell { max-width: 250px; font-size: 11px; }
  .badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; }
  .badge-first { background: #fde8ea; color: var(--accent); }
  .badge-dominant { background: #fce8e0; color: #b08968; }
  a.douban-link { color: var(--accent); text-decoration: none; font-weight: 600; }
  a.douban-link:hover { text-decoration: underline; }
  .pagination { display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
  .pagination button { padding: 5px 10px; border: 1px solid var(--border); border-radius: 5px; background: white; cursor: pointer; font-size: 12px; }
  .pagination button.active { background: var(--accent); color: white; border-color: var(--accent); }
  .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
  .pagination .info { font-size: 11px; color: var(--text-muted); margin-left: 8px; }
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>外语为主方言片 — 人工核查表</h1>
    <div class="subtitle">从方言标记影片中提取的外语为第一语言/外语为主的影片（仅中国制片地区·仅方言片·含豆瓣链接）</div>
    <div class="meta">原始350部 → 秠除非方言片"""+str(nondialect_removed)+f"""部 → 剩余{len(cleaned_films)}部 | 生成日期：2026-08-14</div>
  </div>
</div>
<div class="container">
  <div class="note">
    <strong>使用说明：</strong>此表为需要人工核查的影片清单。每部影片均附有豆瓣链接，点击"豆瓣↗"可在新标签页打开豆瓣页面，核查其语言使用情况。
    <br><strong>筛选规则：</strong>第一语言为外语，或外语标签数量多于中文标签。
    <br><strong>已移除：</strong>在完整版报告中已被分类为"非方言"的{nondialect_removed}部影片。
  </div>
  <div class="section">
    <div class="section-title">影片明细（可搜索·可排序）— 共 {len(cleaned_films)} 部</div>
    <div class="filter-bar">
      <input type="text" id="search-input" placeholder="搜索片名、导演、语言..." oninput="applyFilters()">
      <select id="reason-filter" onchange="applyFilters()">
        <option value="">全部原因</option>
        <option value="外语第一">外语为第一语言</option>
        <option value="外语为主">外语为主</option>
      </select>
      <select id="sort-select" onchange="applyFilters()">
        <option value="reason_year">按原因+年份</option>
        <option value="rating_desc">评分降序</option>
        <option value="rating_asc">评分升序</option>
        <option value="year_asc">年份升序</option>
        <option value="year_desc">年份降序</option>
        <option value="votes_desc">评价人数降序</option>
      </select>
    </div>
    <div class="table-wrap">
      <table class="movie-table" id="movie-table">
        <thead>
          <tr>
            <th style="width:36px">#</th><th>片名</th><th>年份</th><th>评分</th><th>评价人数</th>
            <th>语言字段</th><th>第一语言</th><th>筛选原因</th><th>导演</th><th>类型</th>
            <th>制片地区</th><th>剧情简介</th><th>豆瓣链接</th>
          </tr>
        </thead>
        <tbody id="table-body">
""")

for i, row in enumerate(cleaned_films):
    title = html_module.escape(row.get('片名', ''))
    year = row.get('年份', '')
    rating = row.get('豆瓣评分', '')
    votes = row.get('评价人数', '')
    lang = html_module.escape(row.get('语言', ''))
    first_lang = html_module.escape(row.get('第一语言', ''))
    reason = row.get('筛选原因', '')
    director = html_module.escape(row.get('导演', ''))
    genre = html_module.escape(row.get('类型', ''))
    region = html_module.escape(row.get('制片国家/地区', ''))
    synopsis = html_module.escape(row.get('剧情简介', ''))
    url = row.get('来源URL', '')

    if len(synopsis) > 100:
        synopsis = synopsis[:100] + '...'

    reason_badge = 'badge-first' if '第一' in reason else 'badge-dominant'
    reason_text = '外语第一' if '第一' in reason else '外语为主'

    votes_display = f"{int(votes):,}" if votes.isdigit() else votes

    link_html = f'<a href="{url}" target="_blank" class="douban-link">豆瓣\u2197</a>' if url else '<span style="color:var(--text-muted)">\u2014</span>'

    search_text = f"{title}|{lang}|{director}|{genre}|{first_lang}|{region}"

    html_parts.append(
        f'<tr data-idx="{i+1}" data-reason="{reason_text}" data-year="{year}" '
        f'data-rating="{rating}" data-votes="{votes}" data-search="{search_text}">'
        f'<td style="color:var(--text-muted)">{i+1}</td>'
        f'<td class="title-cell">{title}</td>'
        f'<td>{year}</td>'
        f'<td>{rating}</td>'
        f'<td>{votes_display}</td>'
        f'<td class="lang-cell">{lang}</td>'
        f'<td>{first_lang}</td>'
        f'<td><span class="badge {reason_badge}">{reason_text}</span></td>'
        f'<td>{director}</td>'
        f'<td>{genre}</td>'
        f'<td>{region}</td>'
        f'<td class="dp-cell">{synopsis}</td>'
        f'<td>{link_html}</td>'
        f'</tr>\n'
    )

html_parts.append("""        </tbody>
      </table>
    </div>
    <div class="pagination" id="pagination"></div>
  </div>
</div>
<script>
var STATIC_ROWS = document.querySelectorAll('#table-body tr');
var MOVIE_DATA = [];
for (var i = 0; i < STATIC_ROWS.length; i++) {
  var r = STATIC_ROWS[i];
  MOVIE_DATA.push({
    html: r.innerHTML,
    reason: r.dataset.reason || '',
    year: parseFloat(r.dataset.year) || 0,
    rating: parseFloat(r.dataset.rating) || 0,
    votes: parseFloat(r.dataset.votes) || 0,
    search: r.dataset.search || ''
  });
}
document.getElementById('table-body').innerHTML = '';

var filteredData = MOVIE_DATA.slice();
var currentPage = 1;
var PAGE_SIZE = 50;

function getReasonOrder(reason) {
  return reason === '外语第一' ? 0 : 1;
}

function applyFilters() {
  var search = document.getElementById('search-input').value.toLowerCase().trim();
  var reason = document.getElementById('reason-filter').value;
  var sortByVal = document.getElementById('sort-select').value;

  filteredData = MOVIE_DATA.filter(function(m) {
    if (reason && m.reason !== reason) return false;
    if (search && m.search.toLowerCase().indexOf(search) === -1) return false;
    return true;
  });

  var sorters = {
    'reason_year': function(a, b) {
      var oa = getReasonOrder(a.reason), ob = getReasonOrder(b.reason);
      if (oa !== ob) return oa - ob;
      return a.year - b.year;
    },
    'rating_desc': function(a, b) { return b.rating - a.rating; },
    'rating_asc': function(a, b) { return a.rating - b.rating; },
    'year_asc': function(a, b) { return a.year - b.year; },
    'year_desc': function(a, b) { return b.year - a.year; },
    'votes_desc': function(a, b) { return b.votes - a.votes; }
  };
  filteredData.sort(sorters[sortByVal] || sorters['reason_year']);
  currentPage = 1;
  renderTable();
}

function renderTable() {
  var total = filteredData.length;
  var totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;
  var start = (currentPage - 1) * PAGE_SIZE;
  var end = Math.min(start + PAGE_SIZE, total);
  var parts = [];
  for (var i = start; i < end; i++) {
    parts.push('<tr>' + filteredData[i].html + '</tr>');
  }
  document.getElementById('table-body').innerHTML = parts.join('');
  renderPagination(total, totalPages);
}

function renderPagination(total, totalPages) {
  var pag = document.getElementById('pagination');
  var html = '';
  html += '<button onclick="goPage(1)"' + (currentPage===1?' disabled':'') + '>首页</button>';
  html += '<button onclick="goPage(' + (currentPage-1) + ')"' + (currentPage===1?' disabled':'') + '>上一页</button>';
  var maxButtons = 7;
  var startPage = Math.max(1, currentPage - 3);
  var endPage = Math.min(totalPages, startPage + maxButtons - 1);
  if (endPage - startPage < maxButtons - 1) startPage = Math.max(1, endPage - maxButtons + 1);
  for (var p = startPage; p <= endPage; p++) {
    html += '<button onclick="goPage(' + p + ')"' + (p===currentPage?' class="active"':'') + '>' + p + '</button>';
  }
  html += '<button onclick="goPage(' + (currentPage+1) + ')"' + (currentPage>=totalPages?' disabled':'') + '>下一页</button>';
  html += '<button onclick="goPage(' + totalPages + ')"' + (currentPage>=totalPages?' disabled':'') + '>末页</button>';
  html += '<span class="info">共 ' + total + ' 条，第 ' + currentPage + '/' + totalPages + ' 页</span>';
  pag.innerHTML = html;
}

function goPage(p) {
  currentPage = p;
  renderTable();
  document.getElementById('movie-table').scrollIntoView({behavior:'smooth',block:'nearest'});
}

applyFilters();
</script>
</body>
</html>
""")

with open(OUT_CLEAN_HTML, 'w', encoding='utf-8') as f:
    f.write(''.join(html_parts))
print(f"  HTML saved: {OUT_CLEAN_HTML}")

print(f"\n{'='*60}")
print(f"DONE!")
print(f"  Report 1 (完整版): {dialect_count} dialect films → {OUT_HTML}")
print(f"  Report 2 (外语为主): {len(cleaned_films)} films → {OUT_CLEAN_HTML}")
print(f"  Report 2 CSV: {OUT_CLEAN_CSV}")
print(f"  URLs found in Report 1: {url_found}/{dialect_count}")
