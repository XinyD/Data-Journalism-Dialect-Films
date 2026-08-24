"""DEPRECATED — stale WeChat absolute paths. Do not run.

Split 206 foreign-primary dialect films into two groups:
- Group A (98): present in the dialect-only report (3,487 films)
- Group B (108): NOT in the dialect-only report (were classified as 非方言)

Generates CSV + searchable HTML for each group with complete fields.
"""
import csv, re, html as H
from collections import Counter

# Paths
CSV_PATH = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/derived_movies.csv"
FOREIGN_CSV = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/外语为主方言片_含豆瓣链接.csv"
FULL_HTML = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/方言电影数据报告_仅方言片_含豆瓣链接.html"

OUT_DIR = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main"

# ============================================================
# Step 1: Build key set from full dialect report HTML
# ============================================================
print("Step 1: Reading dialect report HTML keys...")
report_keys = set()
with open(FULL_HTML, "r", encoding="utf-8") as f:
    for line in f:
        if "data-tier=" in line and "<tr" in line:
            sm = re.search(r'data-search="([^"]*)"', line)
            ym = re.search(r'data-year="([^"]*)"', line)
            if sm and ym:
                search = H.unescape(sm.group(1))
                title = search.split("|")[0].casefold().strip() if "|" in search else search.casefold().strip()
                year = ym.group(1).strip()
                report_keys.add((title, year))
print(f"  Dialect report keys: {len(report_keys)}")

# ============================================================
# Step 2: Read foreign-primary CSV and split into two groups
# ============================================================
print("Step 2: Reading foreign-primary CSV and splitting...")
group_a = []  # in report (98)
group_b = []  # not in report (108)

with open(FOREIGN_CSV, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        title_cf = row.get("片名", "").casefold().strip()
        year = row.get("年份", "").strip()
        key = (title_cf, year)
        if key in report_keys:
            group_a.append(row)
        else:
            group_b.append(row)

print(f"  Group A (in report): {len(group_a)}")
print(f"  Group B (not in report): {len(group_b)}")
print(f"  Total: {len(group_a) + len(group_b)}")

# ============================================================
# Step 3: Generate CSV files
# ============================================================
FIELDNAMES = [
    "片名", "年份", "语言", "第一语言", "筛选原因",
    "导演", "类型", "制片国家/地区", "豆瓣评分", "评价人数",
    "剧情简介", "Gemini评价", "Region", "Language_Category", "Decade",
    "Is_Dialect", "来源URL", "豆瓣链接"
]

def write_csv(rows, path, label):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Ensure 来源URL is also duplicated as 豆瓣链接 for clarity
            url = row.get("来源URL", "")
            row["豆瓣链接"] = url
            writer.writerow(row)
    print(f"  {label} CSV: {path} ({len(rows)} rows)")

print("Step 3: Writing CSV files...")
write_csv(group_a, f"{OUT_DIR}/外语为主_在方言报告中_98部.csv", "Group A")
write_csv(group_b, f"{OUT_DIR}/外语为主_不在方言报告中_108部.csv", "Group B")

# ============================================================
# Step 4: Generate HTML files
# ============================================================
def esc(text):
    if not text:
        return ""
    return H.escape(str(text), quote=True)

def truncate(text, n=200):
    if not text:
        return ""
    s = str(text)
    return s if len(s) <= n else s[:n] + "..."

def build_html(rows, title, subtitle, filename):
    # Stats
    reason_counts = Counter(r.get("筛选原因", "") for r in rows)
    lang_counts = Counter(r.get("第一语言", "") for r in rows)
    
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 24px; margin-bottom: 8px; color: #1a1a1a; }}
.subtitle {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
.stats {{ display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
.stat-card {{ background: #fff; border-radius: 8px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); min-width: 120px; }}
.stat-card .num {{ font-size: 28px; font-weight: 700; color: #2563eb; }}
.stat-card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
.filters {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
.filters input, .filters select {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }}
.filters input {{ flex: 1; min-width: 200px; }}
.table-wrap {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
thead {{ background: #f8f9fa; position: sticky; top: 0; z-index: 10; }}
th {{ padding: 12px 10px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #e0e0e0; white-space: nowrap; cursor: pointer; user-select: none; }}
th:hover {{ background: #eef0f3; }}
td {{ padding: 10px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
tr:hover {{ background: #fafbfc; }}
.title-cell {{ font-weight: 600; color: #1a1a1a; max-width: 200px; word-break: break-all; }}
.lang-cell {{ max-width: 180px; word-break: break-all; color: #555; }}
.region-cell {{ max-width: 120px; word-break: break-all; color: #555; }}
.link-cell a {{ color: #2563eb; text-decoration: none; font-size: 12px; }}
.link-cell a:hover {{ text-decoration: underline; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
.badge-first {{ background: #fee2e2; color: #b91c1c; }}
.badge-dominant {{ background: #fef3c7; color: #92400e; }}
.rating-cell {{ font-weight: 600; color: #2563eb; }}
.expand-btn {{ cursor: pointer; color: #2563eb; font-size: 12px; user-select: none; }}
.expand-btn:hover {{ text-decoration: underline; }}
.summary-cell {{ display: none; }}
.summary-cell.show {{ display: table-cell; }}
.detail-row {{ display: none; }}
.detail-row.show {{ display: table-row; background: #fafbfc; }}
.detail-row td {{ padding: 12px 16px; }}
</style>
</head>
<body>
<div class="container">
<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>

<div class="stats">
  <div class="stat-card"><div class="num">{len(rows)}</div><div class="label">影片总数</div></div>
  <div class="stat-card"><div class="num">{reason_counts.get('外语为第一语言', 0)}</div><div class="label">外语为第一语言</div></div>
  <div class="stat-card"><div class="num">{reason_counts.get('外语为主(外语2/中文1)', 0) + reason_counts.get('外语为主(外语3/中文2)', 0)}</div><div class="label">外语为主</div></div>
</div>

<div class="filters">
  <input type="text" id="search" placeholder="搜索片名/导演/语言/地区..." oninput="filterTable()">
  <select id="reason-filter" onchange="filterTable()">
    <option value="">全部原因</option>
    <option value="外语为第一语言">外语为第一语言</option>
    <option value="外语为主(外语2/中文1)">外语为主(外语2/中文1)</option>
    <option value="外语为主(外语3/中文2)">外语为主(外语3/中文2)</option>
  </select>
  <button onclick="exportCSV()" style="padding:8px 16px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">导出CSV</button>
</div>

<div class="table-wrap" style="max-height:70vh;overflow:auto;">
<table>
<thead>
<tr>
  <th>#</th>
  <th>片名</th>
  <th>年份</th>
  <th>评分</th>
  <th>评价人数</th>
  <th>语言</th>
  <th>第一语言</th>
  <th>筛选原因</th>
  <th>导演</th>
  <th>类型</th>
  <th>制片地区</th>
  <th>豆瓣链接</th>
  <th>详情</th>
</tr>
</thead>
<tbody id="tbody">
""")

    for i, r in enumerate(rows):
        idx = i + 1
        title_esc = esc(r.get("片名", ""))
        year_esc = esc(r.get("年份", ""))
        rating_esc = esc(r.get("豆瓣评分", ""))
        votes_esc = esc(r.get("评价人数", ""))
        lang_esc = esc(r.get("语言", ""))
        first_lang_esc = esc(r.get("第一语言", ""))
        reason_raw = r.get("筛选原因", "")
        reason_esc = esc(reason_raw)
        badge_class = "badge-first" if "第一" in reason_raw else "badge-dominant"
        director_esc = esc(r.get("导演", ""))
        genre_esc = esc(r.get("类型", ""))
        region_esc = esc(r.get("制片国家/地区", ""))
        url = r.get("来源URL", "")
        url_esc = esc(url)
        link_html = f'<a href="{url_esc}" target="_blank">豆瓣↗</a>' if url else '<span style="color:#999">—</span>'
        synopsis_esc = esc(truncate(r.get("剧情简介", ""), 300))
        gemini_esc = esc(truncate(r.get("Gemini评价", ""), 200))
        
        search_text = esc(r.get("片名", "") + "|" + r.get("导演", "") + "|" + r.get("语言", "") + "|" + r.get("制片国家/地区", ""))
        
        html_parts.append(f"""<tr data-idx="{idx}" data-reason="{reason_esc}" data-year="{year_esc}" data-search="{search_text}">
<td style="color:#999">{idx}</td>
<td class="title-cell">{title_esc}</td>
<td>{year_esc}</td>
<td class="rating-cell">{rating_esc}</td>
<td>{votes_esc}</td>
<td class="lang-cell">{lang_esc}</td>
<td>{first_lang_esc}</td>
<td><span class="badge {badge_class}">{reason_esc}</span></td>
<td>{director_esc}</td>
<td style="max-width:120px;word-break:break-all">{genre_esc}</td>
<td class="region-cell">{region_esc}</td>
<td class="link-cell">{link_html}</td>
<td><span class="expand-btn" onclick="toggleDetail({idx})">展开</span></td>
</tr>
<tr class="detail-row" id="detail-{idx}">
<td colspan="13">
  <div style="display:flex;gap:24px;flex-wrap:wrap;">
    <div style="flex:1;min-width:300px;">
      <strong>剧情简介：</strong><br>{synopsis_esc}
    </div>
    <div style="flex:1;min-width:200px;">
      <strong>Gemini评价：</strong><br>{gemini_esc}
    </div>
    <div style="min-width:150px;">
      <strong>补充信息</strong><br>
      Region: {esc(r.get("Region", ""))}<br>
      Language_Category: {esc(r.get("Language_Category", ""))}<br>
      Decade: {esc(r.get("Decade", ""))}<br>
      Is_Dialect: {esc(r.get("Is_Dialect", ""))}<br>
      豆瓣链接: <a href="{url_esc}" target="_blank">{url_esc}</a>
    </div>
  </div>
</td>
</tr>
""")

    html_parts.append(f"""</tbody>
</table>
</div>

<script>
function filterTable() {{
  var search = document.getElementById('search').value.toLowerCase();
  var reason = document.getElementById('reason-filter').value;
  var rows = document.querySelectorAll('#tbody tr[data-idx]');
  rows.forEach(function(row) {{
    var dataSearch = row.getAttribute('data-search').toLowerCase();
    var dataReason = row.getAttribute('data-reason');
    var matchSearch = !search || dataSearch.indexOf(search) >= 0;
    var matchReason = !reason || dataReason === reason;
    var display = (matchSearch && matchReason) ? '' : 'none';
    row.style.display = display;
    // Also hide corresponding detail row
    var idx = row.getAttribute('data-idx');
    var detail = document.getElementById('detail-' + idx);
    if (detail) {{
      detail.style.display = (display === 'none' || !detail.classList.contains('show')) ? 'none' : '';
    }}
  }});
}}

function toggleDetail(idx) {{
  var row = document.getElementById('detail-' + idx);
  if (row) {{
    var isVisible = row.classList.contains('show');
    if (isVisible) {{
      row.classList.remove('show');
      row.style.display = 'none';
    }} else {{
      row.classList.add('show');
      row.style.display = '';
    }}
  }}
}}

function exportCSV() {{
  var headers = ['片名','年份','语言','第一语言','筛选原因','导演','类型','制片国家/地区','豆瓣评分','评价人数','Region','Language_Category','Decade','Is_Dialect','豆瓣链接'];
  var rows = [];
  document.querySelectorAll('#tbody tr[data-idx]').forEach(function(tr) {{
    if (tr.style.display === 'none') return;
    var tds = tr.querySelectorAll('td');
    var url = '';
    var link = tr.querySelector('.link-cell a');
    if (link) url = link.getAttribute('href');
    rows.push([
      tds[1].textContent, tds[2].textContent, tds[5].textContent, tds[6].textContent,
      tr.getAttribute('data-reason'), tds[8].textContent, tds[9].textContent, tds[10].textContent,
      tds[3].textContent, tds[4].textContent,
      '', '', '', '', url
    ]);
  }});
  var csv = '\\uFEFF' + headers.join(',') + '\\n';
  rows.forEach(function(r) {{
    csv += r.map(function(c) {{
      var s = String(c || '');
      if (s.indexOf(',') >= 0 || s.indexOf('"') >= 0 || s.indexOf('\\n') >= 0) {{
        s = '"' + s.replace(/"/g, '""') + '"';
      }}
      return s;
    }}).join(',') + '\\n';
  }});
  var blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = '{filename}';
  a.click();
}}
</script>
</div>
</body>
</html>""")

    return "".join(html_parts)

print("Step 4: Writing HTML files...")

html_a = build_html(
    group_a,
    "外语为主方言片 · 在方言报告中（98部）",
    "这98部影片同时存在于「方言电影数据报告_仅方言片_含豆瓣链接.html」(3,487部)和「外语为主方言片」(206部)中——即被归为方言片，但第一语言为外语或外语为主。",
    "外语为主_在方言报告中_98部.csv"
)
html_b = build_html(
    group_b,
    "外语为主方言片 · 不在方言报告中（108部）",
    "这108部影片在CSV中Is_Dialect=1（被标记为方言片），但在「方言电影数据详细报告_完整版」中被归类为「非方言」并已被删除。两套分类标准存在不一致。",
    "外语为主_不在方言报告中_108部.csv"
)

with open(f"{OUT_DIR}/外语为主_在方言报告中_98部.html", "w", encoding="utf-8") as f:
    f.write(html_a)
print(f"  Group A HTML: 外语为主_在方言报告中_98部.html")

with open(f"{OUT_DIR}/外语为主_不在方言报告中_108部.html", "w", encoding="utf-8") as f:
    f.write(html_b)
print(f"  Group B HTML: 外语为主_不在方言报告中_108部.html")

# ============================================================
# Step 5: Print summary stats
# ============================================================
print("\n=== Summary ===")
print(f"Group A (in report): {len(group_a)} films")
print(f"  Reasons: {dict(Counter(r.get('筛选原因','') for r in group_a))}")
print(f"  Top languages: {dict(Counter(r.get('第一语言','') for r in group_a).most_common(5))}")
print(f"  Top regions: {dict(Counter(r.get('制片国家/地区','') for r in group_a).most_common(5))}")
print()
print(f"Group B (not in report): {len(group_b)} films")
print(f"  Reasons: {dict(Counter(r.get('筛选原因','') for r in group_b))}")
print(f"  Top languages: {dict(Counter(r.get('第一语言','') for r in group_b).most_common(5))}")
print(f"  Top regions: {dict(Counter(r.get('制片国家/地区','') for r in group_b).most_common(5))}")

# Verify all have Douban links
for label, group in [("A", group_a), ("B", group_b)]:
    missing_url = sum(1 for r in group if not r.get("来源URL", ""))
    print(f"\nGroup {label}: {len(group) - missing_url}/{len(group)} have Douban links")
