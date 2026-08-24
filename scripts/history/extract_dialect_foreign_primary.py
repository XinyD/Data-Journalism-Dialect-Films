"""Find films flagged as Chinese dialect (Is_Dialect=1) where the FIRST listed
language is actually a foreign language — i.e. dialect-flagged films whose
primary language is foreign rather than Chinese.

Also captures films where foreign languages outnumber Chinese ones.
"""
import csv, re, json, html
from collections import Counter

CSV_PATH = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/derived_movies.csv"
OUT_CSV = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/dialect_films_with_foreign_primary.csv"
OUT_JSON = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/dialect_films_with_foreign_primary.json"
OUT_HTML = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/dialect_films_with_foreign_primary.html"

# ─── Chinese language markers ───
CHINESE_MARKERS = (
    "汉语", "漢語", "中文", "普通话", "普通話", "mandarin", "国语", "國語",
    "cantonese", "粤语", "粵語", "广东话", "廣東話",
    "hokkien", "闽南", "閩南", "闽南话", "閩南話", "潮州话", "潮州話",
    "shanghainese", "沪语", "滬語", "上海话", "上海話", "吴语", "吳語",
    "sichuanese", "四川话", "四川話", "四川方言", "西南官话", "西南官話",
    "武汉话", "武漢話", "贵州话", "貴州話", "贵州方言", "云南话", "雲南話", "云南方言",
    "桂林话", "柳州话", "昆明话",
    "hakka", "客家话", "客家話", "客语", "客語",
    "湘语", "湘語", "长沙话", "長沙話", "湖南方言", "湖南当地方言",
    "赣语", "贛語", "南昌话", "南昌話",
    "晋语", "晉語", "太原话",
    "徽语", "徽語",
    "平话", "平話",
    "taiwanese", "台语", "臺語", "台語",
    "北京话", "南京话", "南京話", "东北话", "東北話", "东北方言",
    "河南话", "河南話", "河南方言", "陕西话", "陝西話", "陕西方言",
    "山东话", "山東話", "天津话", "天津話",
    "重庆话", "重慶話", "重庆方言", "大连话", "大連話",
    "方言",
    "藏语", "藏語", "tibetan",
    "维吾尔语", "維吾爾語", "uyghur", "uighur",
    "蒙古语", "蒙古語", "mongolian", "蒙语",
    "哈萨克语", "哈薩克語", "哈薩克斯坦語", "kazakh",
    "苗语", "苗語", "hmong", "miao",
    "彝语", "彝語", "壮语", "壯語", "zhuang",
    "傣语", "傣語", "dai", "侗语", "侗語", "dong",
    "瑶语", "瑤語", "yao", "白语", "白語",
    "哈尼语", "哈尼語", "傈僳语", "傈僳語", "lisu",
    "佤语", "佤語", "拉祜语", "拉祜語", "lahu",
    "纳西语", "納西語", "naxi", "锡伯语", "錫伯語", "xibe",
    "朝鲜语", "朝鮮語",
    "手语", "手語", "sign language",
    "越剧", "京剧", "昆曲", "黄梅戏",
)

# ─── Foreign language markers ───
FOREIGN_MARKERS = (
    "english", "英语", "英語", "英文",
    "japanese", "日语", "日語", "日本語",
    "korean", "韩语", "韓語", "한국어",
    "french", "法语", "法語",
    "german", "德语", "德語",
    "italian", "意大利语", "義大利語",
    "spanish", "西班牙语", "西班牙語",
    "portuguese", "葡萄牙语", "葡萄牙語",
    "russian", "俄语", "俄語", "俄罗斯语", "俄羅斯語",
    "dutch", "荷兰语", "荷蘭語", "菏兰语", "弗拉芒语", "弗拉芒語",
    "swedish", "瑞典语", "瑞典語",
    "danish", "丹麦语", "丹麥語",
    "norwegian", "挪威语", "挪威語",
    "icelandic", "冰岛语", "冰島語",
    "finnish", "芬兰语", "芬蘭語",
    "sami", "萨米语", "薩米語",
    "polish", "波兰语", "波蘭語",
    "czech", "捷克语", "捷克語",
    "hungarian", "匈牙利语", "匈牙利語",
    "romanian", "罗马尼亚语", "羅馬尼亞語",
    "bulgarian", "保加利亚语", "保加利亞語",
    "croatian", "克罗地亚语", "克羅地亞語",
    "serbian", "塞尔维亚语", "塞爾維亞語",
    "slovenian", "斯洛文尼亚语", "斯洛文尼亞語",
    "slovak", "斯洛伐克语", "斯洛伐克語",
    "latvian", "拉脱维亚语", "拉脫維亞語",
    "lithuanian", "立陶宛语", "立陶宛語",
    "estonian", "爱沙尼亚语", "愛沙尼亞語",
    "ukrainian", "乌克兰语", "烏克蘭語",
    "belarusian", "白俄罗斯语", "白俄羅斯語",
    "macedonian", "马其顿语", "馬其頓語",
    "bosnian", "波斯尼亚语", "波斯尼亞語",
    "greek", "希腊语", "希臘語",
    "arabic", "阿拉伯语", "阿拉伯語",
    "hebrew", "希伯来语", "希伯來語",
    "persian", "波斯语", "波斯語", "farsi",
    "turkish", "土耳其语", "土耳其語",
    "urdu", "乌尔都语", "烏爾都語",
    "pashto", "普什图语", "普什圖語",
    "dari", "达里语", "達里語", "达利语", "達利語",
    "kurdish", "库尔德语", "庫爾德語",
    "hindi", "印地语", "印地語", "北印度语", "北印度語",
    "印度语", "印度語",
    "bengali", "孟加拉语", "孟加拉語",
    "tamil", "泰米尔语", "泰米爾語",
    "telugu", "泰卢固语", "泰盧固語",
    "malayalam", "马拉雅拉姆语", "馬拉雅拉姆語",
    "kannada", "卡纳达语", "卡納達語",
    "punjabi", "旁遮普语", "旁遮普語",
    "sinhala", "sinhalese", "僧伽罗语", "僧伽羅語",
    "nepali", "尼泊尔语", "尼泊爾語",
    "thai", "泰语", "泰語",
    "vietnamese", "越南语", "越南語",
    "indonesian", "印尼语", "印度尼西亞語", "印度尼西亚语",
    "malay", "马来语", "馬來語",
    "tagalog", "filipino", "菲律宾语", "菲律賓語", "他加禄语", "他加祿語", "塔加路语", "塔加路語",
    "khmer", "高棉语", "高棉語", "柬埔寨语",
    "lao", "老挝语", "老撾語",
    "burmese", "缅甸语", "緬甸語",
    "swahili", "斯瓦希里语", "斯瓦希里語",
    "amharic", "阿姆哈拉语", "阿姆哈拉語",
    "zulu", "祖鲁语", "祖魯語",
    "xhosa", "科萨语", "科薩語",
    "somali", "索马里语", "索馬里語",
    "hausa", "yoruba", "约鲁巴语", "約魯巴語",
    "igbo", "wolof", "沃洛夫语", "沃洛夫語",
    "afrikaans", "南非语", "南非荷蘭語", "南非荷兰语",
    "catalan", "加泰罗尼亚语", "加泰羅尼亞語",
    "galician", "加利西亚语", "加利西亞語",
    "basque", "巴斯克语", "巴斯克語",
    "welsh", "威尔士语", "威爾士語",
    "irish", "爱尔兰语", "愛爾蘭語",
    "albanian", "阿尔巴尼亚语", "阿爾巴尼亞語",
    "armenian", "亚美尼亚语", "亞美尼亞語",
    "georgian", "格鲁吉亚语", "格魯吉亞語",
    "latin", "拉丁语", "拉丁語",
    "esperanto",
    "maori", "毛利语", "毛利語",
    "hawaiian", "夏威夷语", "夏威夷語",
    "samoan", "萨摩亚语", "薩摩亞語",
    "yiddish", "意第绪语", "意第緒語",
    "quechua", "盖丘亚语", "蓋丘亞語", "克丘亚语", "克丘亞語",
    "navajo", "纳瓦霍语", "納瓦霍語",
    "inuktitut", "因纽特语", "因紐特語",
    "hopi",
    "sicilian", "西西里语", "西西里語",
    "sardinian", "撒丁语", "撒丁語",
    "neapolitan", "那不勒斯语", "那不勒斯語",
    "琉球语", "琉球語",
    "sanskrit", "梵语", "梵語",
    "uzbek", "乌兹别克语", "烏茲別克語",
    "azerbaijani", "阿塞拜疆语", "阿塞拜疆語",
    "格陵兰语", "格陵蘭語",
    "宗卡语", "宗卡語",
    "比利时语",
    "撒丁语",
)

SILENT_MARKERS = ("无声", "无对白", "silence", "silent", "默片", "无语", "silent film")


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def contains_any(text, markers):
    return any(m in text for m in markers)


def language_parts(value):
    text = normalize_text(value)
    if not text:
        return []
    return [p.strip() for p in re.split(r"\s*(?:/|\||;|;|,)\s*", text) if p.strip()]


def is_chinese_lang(lang_text):
    return contains_any(lang_text, CHINESE_MARKERS)


def is_foreign_lang(lang_text):
    return contains_any(lang_text, FOREIGN_MARKERS)


def is_silent(lang_text):
    return contains_any(lang_text, SILENT_MARKERS)


def main():
    results = []
    total_dialect = 0
    total_rows = 0

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            is_dialect = row.get("Is_Dialect", "0")
            if is_dialect != "1":
                continue
            total_dialect += 1

            lang_raw = row.get("语言", "")
            parts = language_parts(lang_raw)
            if not parts:
                continue

            first_lang = parts[0]

            # Skip silent films
            if is_silent(first_lang):
                continue

            first_is_chinese = is_chinese_lang(first_lang)
            first_is_foreign = is_foreign_lang(first_lang)

            # --- Criteria: foreign language is first OR foreign dominates ---
            foreign_dominant = False

            # Criterion 1: first language is foreign (not Chinese)
            if first_is_foreign and not first_is_chinese:
                foreign_dominant = True
                reason = "外语为第一语言"
            # Criterion 2: not first, but check if foreign languages dominate
            elif not first_is_chinese and not first_is_foreign:
                # Unknown first language — skip unless majority foreign
                pass
            else:
                # Count Chinese vs foreign among ALL listed languages
                chinese_count = sum(1 for p in parts if is_chinese_lang(p))
                foreign_count = sum(1 for p in parts if is_foreign_lang(p) and not is_chinese_lang(p))
                if foreign_count > chinese_count and foreign_count > 0:
                    foreign_dominant = True
                    reason = f"外语为主(外语{foreign_count}/中文{chinese_count})"

            if foreign_dominant:
                results.append({
                    "片名": row.get("片名", ""),
                    "年份": row.get("年份", ""),
                    "语言": lang_raw,
                    "第一语言": first_lang,
                    "筛选原因": reason if foreign_dominant else "",
                    "导演": row.get("导演", ""),
                    "类型": row.get("类型", ""),
                    "制片国家/地区": row.get("制片国家/地区", ""),
                    "豆瓣评分": row.get("豆瓣评分", ""),
                    "评价人数": row.get("评价人数", ""),
                    "剧情简介": row.get("剧情简介", ""),
                    "Gemini评价": row.get("Gemini评价", ""),
                    "Region": row.get("Region", ""),
                    "Language_Category": row.get("Language_Category", ""),
                    "Decade": row.get("Decade", ""),
                    "Is_Dialect": is_dialect,
                    "来源URL": row.get("来源URL", ""),
                })

    print(f"Total rows in CSV: {total_rows}")
    print(f"Total dialect-flagged films (Is_Dialect=1): {total_dialect}")
    print(f"Foreign-primary dialect films found: {len(results)}")
    print()

    # Stats
    lang_counter = Counter(r["第一语言"] for r in results)
    reason_counter = Counter(r["筛选原因"].split("(")[0] for r in results)
    region_counter = Counter(r["Region"] for r in results)

    print("By筛选原因:")
    for k, v in reason_counter.most_common():
        print(f"  {k}: {v}")
    print()
    print("By第一语言:")
    for lang, count in lang_counter.most_common(20):
        print(f"  {lang}: {count}")
    print()
    print("By Region:")
    for k, v in region_counter.most_common():
        print(f"  {k}: {v}")
    print()

    # Print all films
    for i, r in enumerate(results):
        print(f"--- {i+1} ---")
        print(f"  片名: {r['片名']}")
        print(f"  年份: {r['年份']}")
        print(f"  语言: {r['语言']}  (第一语言: {r['第一语言']})")
        print(f"  筛选原因: {r['筛选原因']}")
        print(f"  导演: {r['导演']}")
        print(f"  类型: {r['类型']}")
        print(f"  制片: {r['制片国家/地区']}")
        print(f"  评分: {r['豆瓣评分']} (评价人数: {r['评价人数']})")
        print(f"  Region: {r['Region']} | Decade: {r['Decade']}")
        brief = r['剧情简介'][:120] if r['剧情简介'] else ""
        if brief:
            print(f"  简介: {brief}{'...' if len(r['剧情简介']) > 120 else ''}")
        print()

    # Save CSV
    fieldnames = ["片名", "年份", "语言", "第一语言", "筛选原因", "导演", "类型",
                  "制片国家/地区", "豆瓣评分", "评价人数", "剧情简介", "Gemini评价",
                  "Region", "Language_Category", "Decade", "Is_Dialect", "来源URL"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Save JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Generate HTML
    generate_html(results, total_dialect, total_rows)

    print(f"\nCSV saved: {OUT_CSV}")
    print(f"JSON saved: {OUT_JSON}")
    print(f"HTML saved: {OUT_HTML}")


def generate_html(results, total_dialect, total_rows):
    rows_html = []
    for i, r in enumerate(results):
        cells = [
            str(i + 1),
            html.escape(str(r["片名"])),
            html.escape(str(r["年份"])),
            html.escape(str(r["语言"])),
            html.escape(str(r["第一语言"])),
            html.escape(str(r["筛选原因"])),
            html.escape(str(r["导演"])),
            html.escape(str(r["类型"])),
            html.escape(str(r["制片国家/地区"])),
            html.escape(str(r["豆瓣评分"])),
            html.escape(str(r["评价人数"])),
            html.escape(str(r["Region"])),
            html.escape(str(r["Decade"])),
        ]
        summary = html.escape(str(r["剧情简介"])[:200])
        cells.append(summary)
        gemini = html.escape(str(r.get("Gemini评价", ""))[:200])
        cells.append(gemini)
        url = html.escape(str(r["来源URL"]))
        cells.append(f'<a href="{url}" target="_blank">豆瓣链接</a>' if url else "")

        row = "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
        rows_html.append(row)

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>方言片中外语为主影片清单</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
  h1 {{ font-size: 22px; margin-bottom: 8px; color: #1a1a2e; }}
  .summary {{ background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .summary p {{ margin: 4px 0; font-size: 14px; }}
  .summary .num {{ color: #c0392b; font-weight: bold; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 13px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #2c3e50; color: #fff; position: sticky; top: 0; z-index: 10; white-space: nowrap; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  tr:hover {{ background: #fff3cd; }}
  td {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; }}
  .lang-cell {{ white-space: pre-wrap; max-width: 200px; }}
  a {{ color: #2980b9; }}
</style>
</head>
<body>
<h1>方言片中外语为第一语言/外语为主的影片清单</h1>
<div class="summary">
  <p>数据总行数: <span class="num">{total_rows:,}</span> 部</p>
  <p>方言标记影片 (Is_Dialect=1): <span class="num">{total_dialect:,}</span> 部</p>
  <p>其中外语为第一语言/外语为主: <span class="num">{len(results)}</span> 部</p>
  <p style="margin-top:8px;color:#666;">说明: 这些影片虽然被 Is_Dialect 标记为方言片（因语言字段含方言标签或多语言混列），但第一语言实为外语，说明豆瓣语言字段记录的是"出现过的所有语言"而非"主要对白语言"，存在已知偏差。</p>
  <p style="color:#999;font-size:12px;">字段说明: 原始数据无"主演"字段，已包含全部可用字段。简介/Gemini评价截断显示前200字。</p>
</div>
<div class="table-wrap">
<table>
<thead>
<tr>
  <th>#</th>
  <th>片名</th>
  <th>年份</th>
  <th>语言</th>
  <th>第一语言</th>
  <th>筛选原因</th>
  <th>导演</th>
  <th>类型</th>
  <th>制片国家/地区</th>
  <th>豆瓣评分</th>
  <th>评价人数</th>
  <th>Region</th>
  <th>Decade</th>
  <th>剧情简介</th>
  <th>Gemini评价</th>
  <th>链接</th>
</tr>
</thead>
<tbody>
{"".join(rows_html)}
</tbody>
</table>
</div>
</body>
</html>"""

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)


if __name__ == "__main__":
    main()
