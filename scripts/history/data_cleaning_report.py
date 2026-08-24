# -*- coding: utf-8 -*-
"""
方言电影数据清理与核查脚本
第一步：从742部外语为主影片中筛选制片地区含"中国"/"中国香港"/"中国台湾"的影片
第二步：与"完整版"HTML报告交叉对比
第三步：生成修改报告
"""
import csv
import re
import json
import html as html_lib
from collections import Counter, defaultdict

BASE = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main"

# ============================
# 输入文件路径
# ============================
FOREIGN_CSV = f"{BASE}/data/dialect_films_with_foreign_primary.csv"
REPORT_HTML = f"{BASE}/方言电影数据详细报告_完整版.html"
SOURCE_CSV  = f"{BASE}/data/derived_movies.csv"

# ============================
# 输出文件路径
# ============================
OUT_CLEAN_CSV  = f"{BASE}/data/foreign_primary_china_region_clean.csv"
OUT_CLEAN_HTML = f"{BASE}/data/foreign_primary_china_region_clean.html"
OUT_REPORT_HTML = f"{BASE}/方言电影数据清理与修改报告.html"

# 中国地区标记
CHINA_MARKERS = ("中国", "中国香港", "中国台湾")

# ============================
# 第一步：筛选中国制片地区影片
# ============================
print("=" * 60)
print("第一步：筛选制片地区包含中国标记的影片")
print("=" * 60)

china_films = []
removed_films = []

with open(FOREIGN_CSV, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        region = row.get("制片国家/地区", "")
        if any(marker in region for marker in CHINA_MARKERS):
            china_films.append(row)
        else:
            removed_films.append(row)

print(f"原始外语为主影片总数: {len(china_films) + len(removed_films)}")
print(f"保留（含中国地区标记）: {len(china_films)}")
print(f"删除（不含中国地区标记）: {len(removed_films)}")

# 保存清理后的CSV
with open(OUT_CLEAN_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(china_films)
print(f"清理后CSV已保存: {OUT_CLEAN_CSV}")

# 统计保留影片的分布
print("\n--- 保留影片统计 ---")
reason_dist = Counter(r["筛选原因"] for r in china_films)
for reason, count in reason_dist.most_common():
    print(f"  {reason}: {count}")

first_lang_dist = Counter(r["第一语言"] for r in china_films)
print("\n第一语言分布TOP10:")
for lang, count in first_lang_dist.most_common(10):
    print(f"  {lang}: {count}")

region_dist = Counter(r["制片国家/地区"] for r in china_films)
print("\n制片地区分布TOP15:")
for region, count in region_dist.most_common(15):
    print(f"  [{count:3d}] {region}")

# ============================
# 第二步：与完整版报告交叉对比
# ============================
print("\n" + "=" * 60)
print("第二步：与完整版报告交叉对比")
print("=" * 60)

# 解析HTML报告中的电影数据
with open(REPORT_HTML, "r", encoding="utf-8") as f:
    html_content = f.read()

# 提取表格行
row_pattern = re.compile(
    r'<tr\s+data-idx="(\d+)"\s+data-tier="([^"]*)"\s+data-year="([^"]*)"\s+'
    r'data-rating="([^"]*)"\s+data-votes="([^"]*)"\s+data-search="([^"]*)"'
    r'>(.*?)</tr>',
    re.DOTALL
)

# 提取每行中的单元格内容
cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)

report_movies = []
for match in row_pattern.finditer(html_content):
    idx = match.group(1)
    tier = match.group(2)
    year = match.group(3)
    rating = match.group(4)
    votes = match.group(5)
    search_str = match.group(6)
    row_html = match.group(7)
    
    cells = cell_pattern.findall(row_html)
    # 清理HTML标签
    cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
    
    if len(cells) >= 10:
        # cells: [#, 片名, 年份, 评分, 评价人数, 语言字段, 方言标签, 层级, 方言占比说明, 信号]
        title = cells[1]
        lang_field = cells[5]
        dialect_tag = cells[6]
        tier_label = cells[7]
        proportion = cells[8]
        signal = cells[9]
        
        report_movies.append({
            "idx": idx,
            "title": title,
            "tier": tier,
            "year": year,
            "rating": rating,
            "votes": votes,
            "lang_field": lang_field,
            "dialect_tag": dialect_tag,
            "tier_label": tier_label,
            "proportion": proportion,
            "signal": signal,
            "search_str": search_str,
        })

print(f"完整版报告中的电影总数: {len(report_movies)}")

# 建立片名索引（用于交叉对比）
report_title_map = {}
for m in report_movies:
    key = m["title"].strip().lower()
    report_title_map[key] = m

# 在完整版报告中查找清理后影片
matched_in_report = []
not_in_report = []

for film in china_films:
    title = film["片名"].strip().lower()
    if title in report_title_map:
        report_entry = report_title_map[title]
        matched_in_report.append({
            "film": film,
            "report_entry": report_entry,
        })
    else:
        not_in_report.append(film)

print(f"清理后影片在完整版报告中找到: {len(matched_in_report)}")
print(f"清理后影片未在完整版报告中找到: {len(not_in_report)}")

# 分析匹配到的影片在报告中的层级
tier_dist_matched = Counter(m["report_entry"]["tier"] for m in matched_in_report)
print("\n匹配影片在完整版报告中的层级分布:")
for tier, count in tier_dist_matched.most_common():
    print(f"  {tier}: {count}")

# 分析语言字段
print("\n匹配影片的语言字段样例（前20部）:")
for i, m in enumerate(matched_in_report[:20]):
    film = m["film"]
    report = m["report_entry"]
    print(f"  [{i+1}] {film['片名']} ({film['年份']})")
    print(f"      CSV语言: {film['语言']}")
    print(f"      CSV第一语言: {film['第一语言']} | 筛选原因: {film['筛选原因']}")
    print(f"      报告层级: {report['tier']} | 报告语言字段: {report['lang_field']}")
    print(f"      报告方言占比: {report['proportion']}")

# ============================
# 第三步：生成修改报告
# ============================
print("\n" + "=" * 60)
print("第三步：生成修改报告")
print("=" * 60)

# 读取derived_movies.csv以获取更完整的字段
source_fields = {}
with open(SOURCE_CSV, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        title = row.get("片名", "").strip()
        year = row.get("年份", "").strip()
        key = f"{title}|{year}"
        source_fields[key] = row

# 为清理后影片补充完整字段
for film in china_films:
    key = f"{film['片名'].strip()}|{film['年份'].strip()}"
    if key in source_fields:
        src = source_fields[key]
        film["导演"] = src.get("导演", film.get("导演", ""))
        film["剧情简介"] = src.get("剧情简介", film.get("剧情简介", ""))
        film["Gemini评价"] = src.get("Gemini评价", film.get("Gemini评价", ""))
        film["类型"] = src.get("类型", film.get("类型", ""))
        film["来源URL"] = src.get("来源URL", film.get("来源URL", ""))

# 分类错误类型
error_categories = {
    "foreign_first": [],       # 外语排第一，中国方言在后
    "foreign_dominant": [],    # 普通话排第一但外语数量>中文
}

for m in matched_in_report:
    film = m["film"]
    report = m["report_entry"]
    reason = film["筛选原因"]
    
    if reason == "外语为第一语言":
        error_categories["foreign_first"].append(m)
    elif "外语为主" in reason:
        error_categories["foreign_dominant"].append(m)
    else:
        # 未知类型，归入foreign_first
        error_categories["foreign_first"].append(m)

print(f"错误分类统计:")
print(f"  外语为第一语言: {len(error_categories['foreign_first'])}")
print(f"  外语为主（外语数量>中文）: {len(error_categories['foreign_dominant'])}")

# 按Tier分组
tier_groups = defaultdict(list)
for m in matched_in_report:
    tier_groups[m["report_entry"]["tier"]].append(m)

print(f"\n按报告层级分组:")
for tier in ["Tier 1", "Tier 2a", "Tier 2b", "非方言"]:
    films = tier_groups.get(tier, [])
    print(f"  {tier}: {len(films)} 部")

# ============================
# 生成HTML报告
# ============================

def esc(s):
    """HTML转义"""
    if s is None:
        return ""
    return html_lib.escape(str(s))

# 生成清理后数据HTML
clean_html_parts = []
clean_html_parts.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>清理后数据 — 中国制片地区外语为主影片</title>
<style>
  :root {{
    --bg: #f8f9fa; --card-bg: #fff; --text: #1a1a2e; --text-muted: #6c757d;
    --border: #dee2e6; --accent: #e63946; --accent-light: #fde8ea;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; font-size: 14px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 36px 24px; border-radius: 0 0 24px 24px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 22px; margin-bottom: 8px; }}
  .header .meta {{ font-size: 13px; opacity: 0.8; margin-top: 8px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .stat {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; text-align: center; }}
  .stat .label {{ font-size: 12px; color: var(--text-muted); }}
  .stat .value {{ font-size: 24px; font-weight: 700; color: var(--accent); }}
  .filter-bar {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }}
  .filter-bar input, .filter-bar select {{ padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; }}
  .filter-bar input {{ flex: 1; min-width: 200px; }}
  .table-wrap {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); max-height: 700px; overflow-y: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{ background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; font-weight: 600; position: sticky; top: 0; white-space: nowrap; }}
  tbody td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tbody tr:hover {{ background: #f8f9fa; }}
  .title-cell {{ font-weight: 600; max-width: 180px; }}
  .lang-cell {{ max-width: 200px; word-break: break-all; }}
  .dp-cell {{ max-width: 300px; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .badge-first {{ background: #fde8ea; color: #e63946; }}
  .badge-dom {{ background: #fff3cd; color: #856404; }}
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>清理后数据 — 中国制片地区·外语为主影片</h1>
    <div class="meta">筛选规则：制片地区含"中国"/"中国香港"/"中国台湾" | 共 {len(china_films)} 部 | 生成日期：2026-08-14</div>
  </div>
</div>
<div class="container">
  <div class="stats">
    <div class="stat"><div class="label">原始外语为主影片</div><div class="value">{len(china_films) + len(removed_films)}</div></div>
    <div class="stat"><div class="label">保留（中国制片）</div><div class="value">{len(china_films)}</div></div>
    <div class="stat"><div class="label">删除（非中国制片）</div><div class="value">{len(removed_films)}</div></div>
    <div class="stat"><div class="label">在完整版报告中匹配</div><div class="value">{len(matched_in_report)}</div></div>
  </div>
  <div class="filter-bar">
    <input type="text" id="search" placeholder="搜索片名、导演、语言..." oninput="filterTable()">
    <select id="reason-filter" onchange="filterTable()">
      <option value="">全部筛选原因</option>
      <option value="外语为第一语言">外语为第一语言</option>
      <option value="外语为主">外语为主</option>
    </select>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th style="width:36px">#</th>
          <th>片名</th>
          <th>年份</th>
          <th>评分</th>
          <th>评价人数</th>
          <th>语言字段（原始）</th>
          <th>第一语言</th>
          <th>筛选原因</th>
          <th>导演</th>
          <th>类型</th>
          <th>制片地区</th>
          <th>剧情简介</th>
          <th>报告层级</th>
        </tr>
      </thead>
      <tbody id="tbody">
""")

for i, film in enumerate(china_films):
    title = film["片名"]
    # 查找报告层级
    report_tier = ""
    key = title.strip().lower()
    if key in report_title_map:
        report_tier = report_title_map[key]["tier"]
    
    reason_class = "badge-first" if film["筛选原因"] == "外语为第一语言" else "badge-dom"
    clean_html_parts.append(f"""<tr data-search="{esc(title.lower())}|{esc(film.get('导演','').lower())}|{esc(film.get('语言','').lower())}" data-reason="{esc(film['筛选原因'])}">
<td style="color:var(--text-muted)">{i+1}</td>
<td class="title-cell">{esc(title)}</td>
<td>{esc(film['年份'])}</td>
<td>{esc(film['豆瓣评分'])}</td>
<td>{esc(film['评价人数'])}</td>
<td class="lang-cell">{esc(film['语言'])}</td>
<td>{esc(film['第一语言'])}</td>
<td><span class="badge {reason_class}">{esc(film['筛选原因'])}</span></td>
<td>{esc(film.get('导演',''))}</td>
<td>{esc(film.get('类型',''))}</td>
<td>{esc(film['制片国家/地区'])}</td>
<td class="dp-cell">{esc(film.get('剧情简介','')[:120])}{'...' if len(film.get('剧情简介',''))>120 else ''}</td>
<td>{esc(report_tier)}</td>
</tr>
""")

clean_html_parts.append("""      </tbody>
    </table>
  </div>
</div>
<script>
function filterTable() {{
  var search = document.getElementById('search').value.toLowerCase();
  var reason = document.getElementById('reason-filter').value;
  var rows = document.querySelectorAll('#tbody tr');
  rows.forEach(function(row) {{
    var dataSearch = row.getAttribute('data-search');
    var dataReason = row.getAttribute('data-reason');
    var matchSearch = !search || dataSearch.indexOf(search) >= 0;
    var matchReason = !reason || dataReason === reason;
    row.style.display = (matchSearch && matchReason) ? '' : 'none';
  }});
}}
</script>
</body>
</html>""")

with open(OUT_CLEAN_HTML, "w", encoding="utf-8") as f:
    f.write("\n".join(clean_html_parts))
print(f"\n清理后数据HTML已保存: {OUT_CLEAN_HTML}")

# ============================
# 生成修改报告HTML
# ============================

# 按Tier分组详细列表
def generate_film_list(films, max_display=None):
    """生成影片列表HTML"""
    items = []
    display = films[:max_display] if max_display else films
    for m in display:
        film = m["film"]
        report = m["report_entry"]
        items.append(f"""
        <tr>
          <td style="color:var(--text-muted)">{esc(report['idx'])}</td>
          <td class="title-cell"><strong>{esc(film['片名'])}</strong></td>
          <td>{esc(film['年份'])}</td>
          <td>{esc(film['豆瓣评分'])}</td>
          <td class="lang-cell">{esc(film['语言'])}</td>
          <td><span class="tag-foreign">{esc(film['第一语言'])}</span></td>
          <td>{esc(film.get('导演',''))}</td>
          <td>{esc(film['制片国家/地区'])}</td>
          <td><span class="tier-badge tier-{esc(report['tier'].lower().replace(' ',''))}">{esc(report['tier'])}</span></td>
          <td class="dp-cell">{esc(report['proportion'])}</td>
          <td class="dp-cell">{esc(film.get('剧情简介','')[:100])}{'...' if len(film.get('剧情简介',''))>100 else ''}</td>
        </tr>""")
    if max_display and len(films) > max_display:
        items.append(f'<tr><td colspan="11" style="text-align:center;color:#6c757d;padding:12px">... 还有 {len(films)-max_display} 部，详见CSV文件</td></tr>')
    return "\n".join(items)

# 统计数据
total_matched = len(matched_in_report)
tier1_count = len(tier_groups.get("Tier 1", []))
tier2a_count = len(tier_groups.get("Tier 2a", []))
tier2b_count = len(tier_groups.get("Tier 2b", []))
nond_count = len(tier_groups.get("非方言", []))

# 按第一语言分组
first_lang_groups = defaultdict(list)
for m in matched_in_report:
    first_lang_groups[m["film"]["第一语言"]].append(m)

# 评分影响分析
ratings = []
for m in matched_in_report:
    try:
        r = float(m["film"]["豆瓣评分"])
        ratings.append(r)
    except:
        pass
avg_rating = sum(ratings)/len(ratings) if ratings else 0
bad_films = sum(1 for r in ratings if r < 5)
high_films = sum(1 for r in ratings if r >= 8)

report_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>方言电影数据清理与修改报告</title>
<style>
  :root {{
    --bg: #f8f9fa; --card-bg: #fff; --text: #1a1a2e; --text-muted: #6c757d;
    --border: #dee2e6; --accent: #e63946; --accent-light: #fde8ea;
    --green: #2a9d8f; --orange: #e29578; --blue: #118ab2;
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-lg: 0 4px 12px rgba(0,0,0,0.1);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; font-size: 14px; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 48px 24px; border-radius: 0 0 24px 24px; box-shadow: var(--shadow-lg); margin-bottom: 32px; }}
  .header h1 {{ font-size: 26px; margin-bottom: 8px; font-weight: 700; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
  .header .meta {{ font-size: 12px; opacity: 0.6; margin-top: 12px; }}
  .section {{ background: var(--card-bg); border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow); }}
  .section-title {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--border); display: flex; align-items: center; gap: 8px; }}
  .section-title .num {{ background: var(--accent); color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }}
  .stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; text-align: center; }}
  .stat-card .label {{ font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }}
  .stat-card .value {{ font-size: 26px; font-weight: 700; }}
  .stat-card .sub {{ font-size: 11px; color: var(--text-muted); margin-top: 4px; }}
  .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
  .note strong {{ color: #856404; }}
  .note-info {{ background: #e3f2fd; border-left: 4px solid #118ab2; padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
  .note-info strong {{ color: #0d47a1; }}
  .note-warn {{ background: #fde8ea; border-left: 4px solid var(--accent); padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
  .note-warn strong {{ color: var(--accent); }}
  .note-ok {{ background: #e0f5f2; border-left: 4px solid var(--green); padding: 12px 16px; border-radius: 6px; font-size: 13px; margin-top: 12px; }}
  .note-ok strong {{ color: var(--green); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }}
  th {{ background: #f1f3f5; padding: 10px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); white-space: nowrap; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tr:hover td {{ background: #f8f9fa; }}
  .title-cell {{ font-weight: 600; max-width: 180px; }}
  .lang-cell {{ max-width: 200px; word-break: break-all; }}
  .dp-cell {{ max-width: 280px; font-size: 12px; }}
  .table-wrap {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); max-height: 600px; overflow-y: auto; }}
  .tag-foreign {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #fde8ea; color: var(--accent); }}
  .tier-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .tier-tier1 {{ background: #e0f5f2; color: var(--green); }}
  .tier-tier2a {{ background: #fce8e0; color: var(--orange); }}
  .tier-tier2b {{ background: #f5ebe0; color: #b08968; }}
  .tier-非方言 {{ background: #f1f3f5; color: #adb5bd; }}
  .filter-bar {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }}
  .filter-bar input {{ padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; flex: 1; min-width: 200px; }}
  .change-box {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; margin-top: 12px; font-size: 13px; }}
  .change-box strong {{ color: #15803d; }}
  .toc {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; margin-bottom: 24px; }}
  .toc-title {{ font-size: 15px; font-weight: 700; margin-bottom: 10px; }}
  .toc ul {{ list-style: none; padding-left: 0; }}
  .toc li {{ padding: 4px 0; }}
  .toc a {{ color: var(--blue); text-decoration: none; }}
  .toc a:hover {{ text-decoration: underline; }}
  .sub-title {{ font-size: 16px; font-weight: 600; margin: 20px 0 10px; padding-left: 12px; border-left: 3px solid var(--accent); }}
</style>
</head>
<body>

<div class="header">
  <div class="container">
    <h1>方言电影数据清理与修改报告</h1>
    <div class="subtitle">基于"外语为主影片"与"方言电影数据详细报告_完整版"交叉对比</div>
    <div class="meta">清理规则：制片地区含"中国"/"中国香港"/"中国台湾" | 生成日期：2026-08-14</div>
  </div>
</div>

<div class="container">

  <!-- 目录 -->
  <div class="toc">
    <div class="toc-title">报告目录</div>
    <ul>
      <li><a href="#step1">第一步：清理后数据文件说明</a></li>
      <li><a href="#step2">第二步：交叉对比结果</a></li>
      <li><a href="#step3">第三步：完整版报告修改建议</a></li>
      <li><a href="#appendix">附录：需修改影片完整清单</a></li>
    </ul>
  </div>

  <!-- 第一步 -->
  <div class="section" id="step1">
    <div class="section-title"><span class="num">1</span>清理后数据文件说明</div>
    
    <div class="stats-grid">
      <div class="stat-card"><div class="label">原始外语为主影片</div><div class="value">{len(china_films) + len(removed_films)}</div><div class="sub">Is_Dialect=1 中外语排第一/外语为主</div></div>
      <div class="stat-card"><div class="label">删除（非中国制片）</div><div class="value" style="color:var(--accent)">{len(removed_films)}</div><div class="sub">制片地区不含中国标记</div></div>
      <div class="stat-card"><div class="label">保留（中国制片）</div><div class="value" style="color:var(--green)">{len(china_films)}</div><div class="sub">含中国/中国香港/中国台湾</div></div>
      <div class="stat-card"><div class="label">在完整版报告中匹配</div><div class="value" style="color:var(--blue)">{total_matched}</div><div class="sub">需修改的记录</div></div>
    </div>

    <div class="sub-title">筛选规则</div>
    <div class="note-info">
      <strong>操作：</strong>从 742 部"外语为第一语言或外语为主"的影片中，删除制片地区不含"中国"、"中国香港"或"中国台湾"的记录。
      <br><strong>保留条件：</strong>制片国家/地区字段中至少包含上述任一中国地区标记。
      <br><strong>输出文件：</strong>
      <ul style="margin-top:6px;padding-left:20px">
        <li><code>data/foreign_primary_china_region_clean.csv</code> — 清理后CSV（含完整字段）</li>
        <li><code>data/foreign_primary_china_region_clean.html</code> — 清理后可浏览HTML表格</li>
      </ul>
    </div>

    <div class="sub-title">删除的影片地区分布（TOP10）</div>
    <table>
      <tr><th>制片地区</th><th>删除数量</th></tr>
"""

# 删除影片地区分布
removed_region_dist = Counter(r["制片国家/地区"] for r in removed_films)
for region, count in removed_region_dist.most_common(10):
    report_html += f'      <tr><td>{esc(region)}</td><td>{count}</td></tr>\n'

report_html += f"""    </table>

    <div class="sub-title">保留影片的第一语言分布</div>
    <table>
      <tr><th>第一语言</th><th>数量</th><th>占比</th></tr>
"""

for lang, count in first_lang_dist.most_common(15):
    pct = count / len(china_films) * 100 if china_films else 0
    report_html += f'      <tr><td>{esc(lang)}</td><td>{count}</td><td>{pct:.1f}%</td></tr>\n'

report_html += f"""    </table>

    <div class="sub-title">保留影片的筛选原因分布</div>
    <table>
      <tr><th>筛选原因</th><th>数量</th><th>说明</th></tr>
      <tr><td>外语为第一语言</td><td>{reason_dist.get("外语为第一语言", 0)}</td><td>语言字段第一位是外语（如英语/日语/法语）</td></tr>
      <tr><td>外语为主（外语数量&gt;中文）</td><td>{reason_dist.get("外语为主（外语数量>中文）", 0)}</td><td>普通话排第一，但外语标签数量超过中文标签</td></tr>
    </table>
  </div>

  <!-- 第二步 -->
  <div class="section" id="step2">
    <div class="section-title"><span class="num">2</span>交叉对比结果</div>

    <div class="stats-grid">
      <div class="stat-card"><div class="label">完整版报告总影片数</div><div class="value">{len(report_movies):,}</div></div>
      <div class="stat-card"><div class="label">清理后影片在报告中匹配</div><div class="value" style="color:var(--accent)">{total_matched}</div></div>
      <div class="stat-card"><div class="label">未在报告中匹配</div><div class="value" style="color:var(--text-muted)">{len(not_in_report)}</div></div>
    </div>

    <div class="note">
      <strong>匹配方法：</strong>以片名精确匹配（不区分大小写），在完整版报告 11,121 部影片的明细表中查找清理后的 {len(china_films)} 部影片。
      匹配到 {total_matched} 部，这批影片在完整版报告中<strong>被错误归类为方言片</strong>（或非方言片中含外语问题），需要修正。
    </div>

    <div class="sub-title">匹配影片在完整版报告中的层级分布</div>
    <table>
      <tr><th>报告层级</th><th>数量</th><th>说明</th><th>修改建议</th></tr>
      <tr>
        <td><span class="tier-badge tier-tier1">Tier 1 纯方言片</span></td>
        <td style="font-weight:700;color:var(--green)">{tier1_count}</td>
        <td>不含普通话标签，含中国方言标签</td>
        <td><strong>需删除或降级</strong>：外语排第一，不符合纯方言片定义</td>
      </tr>
      <tr>
        <td><span class="tier-badge tier-tier2a">Tier 2a 方言排首位</span></td>
        <td style="font-weight:700;color:var(--orange)">{tier2a_count}</td>
        <td>含普通话+方言，方言排第一</td>
        <td><strong>需删除或降级</strong>：实际第一语言是外语</td>
      </tr>
      <tr>
        <td><span class="tier-badge tier-tier2b">Tier 2b 普通话排首位</span></td>
        <td style="font-weight:700;color:#b08968">{tier2b_count}</td>
        <td>普通话排第一，方言在后</td>
        <td><strong>需删除</strong>：外语数量超过中文，不应归入方言片</td>
      </tr>
      <tr>
        <td><span class="tier-badge tier-非方言">非方言片</span></td>
        <td style="font-weight:700;color:#adb5bd">{nond_count}</td>
        <td>Is_Dialect=0</td>
        <td>已正确排除，无需修改</td>
      </tr>
    </table>

    <div class="sub-title">匹配影片的评分统计</div>
    <table>
      <tr><th>指标</th><th>数值</th></tr>
      <tr><td>影片数</td><td>{len(ratings)}</td></tr>
      <tr><td>平均评分</td><td>{avg_rating:.2f}</td></tr>
      <tr><td>烂片数（&lt;5分）</td><td style="color:var(--accent);font-weight:700">{bad_films}</td></tr>
      <tr><td>高分片数（&ge;8分）</td><td style="color:var(--green);font-weight:700">{high_films}</td></tr>
    </table>

    <div class="note-warn">
      <strong>关键发现：</strong>这 {total_matched} 部影片中，有 <strong>{tier1_count + tier2a_count + tier2b_count}</strong> 部被完整版报告归类为方言片（Tier 1/2a/2b），
      但实际对白以外语为主。它们的平均评分 {avg_rating:.2f}，烂片率 {bad_films/len(ratings)*100:.1f}%，
      如果不从方言片中移除，会<strong>拉高</strong>方言片的均分、<strong>降低</strong>方言片的烂片率——使结论看起来"更好"但不真实。
    </div>
  </div>

  <!-- 第三步 -->
  <div class="section" id="step3">
    <div class="section-title"><span class="num">3</span>完整版报告修改建议</div>

    <div class="note-warn">
      <strong>核心修改原则：</strong>完整版报告（v2.1）已排除外语作为研究对象，但其操作化判定规则仍存在漏洞——
      豆瓣"语言"字段是标签型（记录"出现过的所有语言"），当影片的语言字段同时含外语和中国方言标签时，
      当前规则仅检查"是否含中国方言标签"，未检查"第一语言是否为外语"。
      这导致如《上海快车》（英语/法语/粤语/德语）被归入 Tier 1 纯方言片——实际对白以英语为主。
    </div>

    <div class="sub-title">修改建议一：从方言片中移除外语为主的影片</div>
    <div class="note">
      <strong>操作：</strong>从完整版报告的 3,487 部方言片中，移除 {tier1_count + tier2a_count + tier2b_count} 部外语为主的影片。
      <br><strong>影响：</strong>
      <ul style="margin-top:6px;padding-left:20px">
        <li>方言片总数：3,487 → <strong>{3487 - tier1_count - tier2a_count - tier2b_count}</strong></li>
        <li>Tier 1 纯方言片：2,321 → <strong>{2321 - tier1_count}</strong></li>
        <li>Tier 2a：431 → <strong>{431 - tier2a_count}</strong>（如有）</li>
        <li>Tier 2b：735 → <strong>{735 - tier2b_count}</strong>（如有）</li>
      </ul>
      <strong>注意：</strong>这些数字可能因匹配方式不同而略有偏差，建议在 derived_movies.csv 层面直接修正 Is_Dialect 字段。
    </div>

    <div class="sub-title">修改建议二：增加"第一语言检查"规则</div>
    <div class="note-info">
      <strong>当前规则漏洞：</strong>v2.1 的操作定义只检查"语言字段是否含中国方言标签"，未检查"第一语言（即语言字段中排在第一位的语言）是否为外语"。
      <br><strong>建议新增规则：</strong>
      <ul style="margin-top:6px;padding-left:20px">
        <li><strong>新增排除条件：</strong>若语言字段的第一位是外语（英语/日语/法语/韩语等），则即使后续含有中国方言标签，也不计入方言片。</li>
        <li><strong>新增排除条件：</strong>若语言字段中外语标签数量 > 中文标签数量（含普通话+方言），则不计入方言片。</li>
      </ul>
    </div>

    <div class="sub-title">修改建议三：更新报告统计数据</div>
    <div class="note">
      <strong>需更新的统计数字：</strong>
      <ul style="margin-top:6px;padding-left:20px">
        <li>第1节"总览统计"中的方言片数量、占比</li>
        <li>第2节"各层级评分对比"中的数量、均分、烂片率、高分率</li>
        <li>第6节电影数据明细表中的层级标签</li>
      </ul>
    </div>

    <div class="sub-title">修改建议四：添加已知偏差说明</div>
    <div class="note-info">
      <strong>建议在第5节"已知偏差"中新增：</strong>
      <br>"豆瓣语言字段为标签型元数据，标注影片中出现过的所有语言，而非对白占比。当影片以外语为主要对白语言、但语言字段中包含中国方言标签时，
      可能被错误归类为方言片。本报告已通过'第一语言检查'排除此类影片，但仍有少量边缘案例可能存在偏差。"
    </div>
  </div>

  <!-- 附录 -->
  <div class="section" id="appendix">
    <div class="section-title"><span class="num">附</span>需修改影片完整清单</div>
    
    <div class="filter-bar">
      <input type="text" id="appendix-search" placeholder="搜索片名、导演、语言..." oninput="filterAppendix()">
    </div>

    <div class="sub-title">A. Tier 1 纯方言片中的错误归类（{tier1_count} 部）</div>
    <div class="note-warn">
      <strong>问题最严重：</strong>这 {tier1_count} 部影片被标记为 Tier 1（纯方言片，强信号），但实际对白以外语为主。
      按 v2.1 定义，Tier 1 要求"语言字段含中国方言标签且不含普通话标签"——但这些影片的第一语言是外语，不应归入任何方言片层级。
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:36px">#</th>
            <th>片名</th>
            <th>年份</th>
            <th>评分</th>
            <th>语言字段</th>
            <th>第一语言</th>
            <th>导演</th>
            <th>制片地区</th>
            <th>报告层级</th>
            <th>方言占比</th>
            <th>简介</th>
          </tr>
        </thead>
        <tbody id="tier1-tbody">
          {generate_film_list(tier_groups.get("Tier 1", []), max_display=100)}
        </tbody>
      </table>
    </div>

    <div class="sub-title">B. Tier 2a 方言排首位中的错误归类（{tier2a_count} 部）</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:36px">#</th>
            <th>片名</th>
            <th>年份</th>
            <th>评分</th>
            <th>语言字段</th>
            <th>第一语言</th>
            <th>导演</th>
            <th>制片地区</th>
            <th>报告层级</th>
            <th>方言占比</th>
            <th>简介</th>
          </tr>
        </thead>
        <tbody>
          {generate_film_list(tier_groups.get("Tier 2a", []), max_display=100)}
        </tbody>
      </table>
    </div>

    <div class="sub-title">C. Tier 2b 普通话排首位中的错误归类（{tier2b_count} 部）</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th style="width:36px">#</th>
            <th>片名</th>
            <th>年份</th>
            <th>评分</th>
            <th>语言字段</th>
            <th>第一语言</th>
            <th>导演</th>
            <th>制片地区</th>
            <th>报告层级</th>
            <th>方言占比</th>
            <th>简介</th>
          </tr>
        </thead>
        <tbody>
          {generate_film_list(tier_groups.get("Tier 2b", []), max_display=100)}
        </tbody>
      </table>
    </div>

    <div class="sub-title">D. 非方言片中匹配到的影片（{nond_count} 部，仅供参考）</div>
    <div class="note-info">
      <strong>说明：</strong>这些影片在完整版报告中已被正确标记为"非方言"（Is_Dialect=0），无需修改。列出仅供交叉参考。
    </div>
    {f'<div class="table-wrap"><table><thead><tr><th>#</th><th>片名</th><th>年份</th><th>评分</th><th>语言字段</th><th>第一语言</th><th>导演</th><th>制片地区</th><th>报告层级</th><th>方言占比</th><th>简介</th></tr></thead><tbody>{generate_film_list(tier_groups.get("非方言", []), max_display=50)}</tbody></table></div>' if nond_count > 0 else ''}

  </div>

</div>

<script>
function filterAppendix() {{
  var search = document.getElementById('appendix-search').value.toLowerCase();
  document.querySelectorAll('#tier1-tbody tr').forEach(function(row) {{
    var text = row.textContent.toLowerCase();
    row.style.display = (!search || text.indexOf(search) >= 0) ? '' : 'none';
  }});
}}
</script>

</body>
</html>
"""

with open(OUT_REPORT_HTML, "w", encoding="utf-8") as f:
    f.write(report_html)
print(f"修改报告HTML已保存: {OUT_REPORT_HTML}")

# ============================
# 输出总结
# ============================
print("\n" + "=" * 60)
print("任务完成总结")
print("=" * 60)
print(f"第一步：清理后CSV ({len(china_films)}部) -> {OUT_CLEAN_CSV}")
print(f"        清理后HTML -> {OUT_CLEAN_HTML}")
print(f"第二步：交叉对比完成，{total_matched}部在完整版报告中匹配")
print(f"        Tier 1: {tier1_count} | Tier 2a: {tier2a_count} | Tier 2b: {tier2b_count} | 非方言: {nond_count}")
print(f"第三步：修改报告 -> {OUT_REPORT_HTML}")
print(f"        需修改影片总计: {tier1_count + tier2a_count + tier2b_count}部")
