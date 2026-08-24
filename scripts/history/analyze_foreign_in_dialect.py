"""DEPRECATED — stale path data/derived_movies.csv. Do not run.

分析方言片中含外语标签的情况，验证"外语为主+方言点缀"风险。

纯标准库实现，不依赖 pandas。
"""
import csv
import re
from collections import Counter, defaultdict

CSV_PATH = r"data\derived_movies.csv"

# --- 语言标签分类（与 v2.1 方言定义对齐） ---

# 中国汉语方言标签（v2.1）
DIALECT_TAGS = {
    # 粤语
    "粤语", "粵語", "cantonese",
    # 闽南语
    "闽南语", "閩南語", "hokkien", "闽南", "閩南", "台语", "臺語", "taiwanese",
    # 吴语
    "上海话", "上海話", "shanghainese", "沪语", "滬語", "苏州话", "蘇州話",
    "宁波话", "寧波話", "温州话", "溫州話", "杭州话", "杭州話",
    # 西南官话
    "四川话", "四川話", "sichuanese", "四川方言", "重庆话", "重慶話",
    "成都话", "貴陽話", "贵阳话", "昆明话", "武漢話", "武汉话", "桂林话",
    # 客家话
    "客家话", "客家話", "hakka",
    # 湘语
    "长沙话", "長沙話", "湘语", "湘語", "湖南话", "湖南話",
    # 赣语
    "南昌话", "南昌話", "赣语", "贛語",
    # 晋语
    "晋语", "晉語", "山西话", "山西話", "太原话",
    # 徽语
    "徽语", "徽語",
    # 平话
    "平话", "平話",
    # 其他官话变体
    "河南话", "河南方言", "陕西话", "陝西話", "西安话", "东北话", "東北話",
    "大连话", "青岛话", "青島話", "唐山话", "山东话", "山東話",
    "北京话", "北京方言",
    # 通用方言标签
    "方言",
}

# 中国少数民族语言标签
MINORITY_TAGS = {
    "藏语", "藏語", "tibetan",
    "维吾尔语", "維吾爾語", "uyghur", "uighur",
    "蒙古语", "蒙古語", "mongolian",
    "哈萨克语", "哈薩克語", "kazakh",
    "苗语", "苗語", "hmong",
    "彝语", "彝語", "yi language",
    "壮语", "壯語", "zhuang",
    "傣语", "傣語", "dai",
    "侗语", "侗語", "dong",
    "瑶语", "瑤語", "yao",
    "白语", "白語",
    "哈尼语", "哈尼語",
    "傈僳语", "傈僳語",
    "佤语", "佤語",
    "拉祜语", "拉祜語",
    "纳西语", "納西語",
    "锡伯语", "錫伯語",
    "朝鲜语", "朝鮮語",  # 中国朝鲜族
}

# 普通话标签（3种变体）
MANDARIN_TAGS = {
    "汉语普通话", "漢語普通話", "普通话", "普通話", "mandarin", "国语", "國語",
}

# 外语标签
FOREIGN_TAGS = {
    "英语", "英語", "english",
    "日语", "日語", "日本語", "japanese",
    "韩语", "韓語", "한국어", "korean",
    "法语", "法語", "french",
    "德语", "德語", "german",
    "意大利语", "義大利語", "italian",
    "西班牙语", "西班牙語", "spanish",
    "葡萄牙语", "葡萄牙語", "portuguese",
    "俄语", "俄語", "russian",
    "泰语", "泰語", "thai",
    "荷兰语", "荷蘭語", "dutch",
    "瑞典语", "瑞典語", "swedish",
    "丹麦语", "丹麥語", "danish",
    "挪威语", "挪威語", "norwegian",
    "波兰语", "波蘭語", "polish",
    "希腊语", "希臘語", "greek",
    "捷克语", "捷克語", "czech",
    "匈牙利语", "匈牙利語", "hungarian",
    "手语", "手語", "sign language",
}

# 港澳台地区标记
HK_MACAU_MARKERS = ("香港", "hong kong", "澳門", "macau", "macao")
TAIWAN_MARKERS = ("台湾", "臺灣", "taiwan")


def split_language_tags(lang_str):
    """将语言字段拆分为标签列表（保留原始顺序）。"""
    if not lang_str:
        return []
    parts = re.split(r"\s*(?:/|\||;|；|,|，)\s*", lang_str.strip())
    return [p.strip() for p in parts if p.strip()]


def classify_tag(tag):
    """将单个标签分类。"""
    tag_lower = tag.lower().strip()
    # 精确匹配优先
    if tag in DIALECT_TAGS or tag_lower in {t.lower() for t in DIALECT_TAGS}:
        return "dialect"
    if tag in MINORITY_TAGS or tag_lower in {t.lower() for t in MINORITY_TAGS}:
        return "minority"
    if tag in MANDARIN_TAGS or tag_lower in {t.lower() for t in MANDARIN_TAGS}:
        return "mandarin"
    if tag in FOREIGN_TAGS or tag_lower in {t.lower() for t in FOREIGN_TAGS}:
        return "foreign"
    return "other"


def is_china_region(region_str):
    """判断是否中国制片地区。"""
    if not region_str:
        return False
    r = region_str.lower()
    markers = ("中国", "china", "hong kong", "香港", "taiwan", "台湾",
               "臺灣", "macau", "macao", "澳门", "澳門")
    return any(m in r for m in markers)


def is_hk(region_str):
    if not region_str:
        return False
    r = region_str.lower()
    return any(m in r for m in HK_MACAU_MARKERS)


def is_taiwan(region_str):
    if not region_str:
        return False
    r = region_str.lower()
    return any(m in r for m in TAIWAN_MARKERS)


def main():
    dialect_films = []
    total_rows = 0

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            try:
                is_dialect = int(row.get("Is_Dialect", 0))
            except (ValueError, TypeError):
                is_dialect = 0
            if is_dialect != 1:
                continue

            lang_str = row.get("语言", "")
            tags = split_language_tags(lang_str)
            tag_classes = [classify_tag(t) for t in tags]

            film = {
                "title": row.get("片名", ""),
                "year": row.get("年份", ""),
                "director": row.get("导演", ""),
                "region": row.get("制片国家/地区", ""),
                "language": lang_str,
                "tags": tags,
                "tag_classes": tag_classes,
                "rating": row.get("豆瓣评分", ""),
                "votes": row.get("评价人数", ""),
            }
            dialect_films.append(film)

    print(f"=" * 70)
    print(f"方言片总数: {len(dialect_films)} / 总记录: {total_rows}")
    print(f"=" * 70)

    # === 1. 统计方言片中各语言标签频次（验证 TOP 20） ===
    tag_counter = Counter()
    for film in dialect_films:
        for tag in film["tags"]:
            tag_counter[tag] += 1

    print(f"\n--- 方言片语言标签频次 TOP 25 ---")
    for tag, count in tag_counter.most_common(25):
        cls = classify_tag(tag)
        print(f"  {tag:20s} {count:5d}  [{cls}]")

    # === 2. 含外语标签的方言片 ===
    foreign_films = [f for f in dialect_films if "foreign" in f["tag_classes"]]
    print(f"\n{'=' * 70}")
    print(f"含外语标签的方言片: {len(foreign_films)} 部 / {len(dialect_films)} 部方言片")
    print(f"占比: {len(foreign_films)/len(dialect_films)*100:.1f}%")
    print(f"{'=' * 70}")

    # === 3. 按外语类型拆分 ===
    foreign_type_counter = Counter()
    for f in foreign_films:
        for tag, cls in zip(f["tags"], f["tag_classes"]):
            if cls == "foreign":
                foreign_type_counter[tag] += 1

    print(f"\n--- 外语标签频次（仅在方言片中） ---")
    for tag, count in foreign_type_counter.most_common():
        print(f"  {tag:15s} {count:5d}")

    # === 4. 按制片地区分析含外语的方言片 ===
    print(f"\n--- 含外语标签的方言片 — 制片地区分布 ---")
    region_counter = Counter()
    hk_count = 0
    tw_count = 0
    mainland_count = 0
    other_china = 0
    non_china = 0
    for f in foreign_films:
        region = f["region"]
        if is_hk(region):
            hk_count += 1
        elif is_taiwan(region):
            tw_count += 1
        elif is_china_region(region):
            mainland_count += 1
        else:
            non_china += 1
        # 取第一地区
        first_region = re.split(r"\s*(?:/|\||;|；)\s*", region.strip())[0] if region else "未知"
        region_counter[first_region] += 1

    print(f"  香港:     {hk_count:4d} ({hk_count/len(foreign_films)*100:.1f}%)")
    print(f"  台湾:     {tw_count:4d} ({tw_count/len(foreign_films)*100:.1f}%)")
    print(f"  中国内地: {mainland_count:4d} ({mainland_count/len(foreign_films)*100:.1f}%)")
    print(f"  非中国:   {non_china:4d} ({non_china/len(foreign_films)*100:.1f}%)")
    print(f"\n  TOP 10 制片地区:")
    for region, count in region_counter.most_common(10):
        print(f"    {region:30s} {count:4d}")

    # === 5. 按具体外语拆分地区（验证英语310是否主要来自港片） ===
    print(f"\n--- 英语标签方言片的制片地区分布 ---")
    english_films = []
    for f in foreign_films:
        for tag, cls in zip(f["tags"], f["tag_classes"]):
            if cls == "foreign" and tag.lower() in ("英语", "英語", "english"):
                english_films.append(f)
                break

    eng_region = Counter()
    eng_hk = 0
    eng_tw = 0
    eng_mainland = 0
    eng_other = 0
    for f in english_films:
        region = f["region"]
        if is_hk(region):
            eng_hk += 1
        elif is_taiwan(region):
            eng_tw += 1
        elif is_china_region(region):
            eng_mainland += 1
        else:
            eng_other += 1

    print(f"  含英语标签的方言片共: {len(english_films)} 部")
    print(f"  香港:     {eng_hk:4d} ({eng_hk/max(len(english_films),1)*100:.1f}%)")
    print(f"  台湾:     {eng_tw:4d} ({eng_tw/max(len(english_films),1)*100:.1f}%)")
    print(f"  中国内地: {eng_mainland:4d} ({eng_mainland/max(len(english_films),1)*100:.1f}%)")
    print(f"  非中国:   {eng_other:4d} ({eng_other/max(len(english_films),1)*100:.1f}%)")

    # === 6. "外语为主+方言点缀"风险分析 ===
    print(f"\n{'=' * 70}")
    print(f"【风险分析】外语排在方言前面的方言片")
    print(f"{'=' * 70}")

    risk_films = []
    for f in dialect_films:
        tags = f["tags"]
        classes = f["tag_classes"]
        if not tags:
            continue
        # 找第一个外语标签和第一个方言/少数民族标签的位置
        first_foreign_idx = None
        first_dialect_idx = None
        for i, cls in enumerate(classes):
            if cls == "foreign" and first_foreign_idx is None:
                first_foreign_idx = i
            if cls in ("dialect", "minority") and first_dialect_idx is None:
                first_dialect_idx = i
        # 外语排在方言前面 = 风险
        if first_foreign_idx is not None and first_dialect_idx is not None:
            if first_foreign_idx < first_dialect_idx:
                risk_films.append(f)

    print(f"外语排在方言前面的方言片: {len(risk_films)} 部")
    print(f"占方言片比例: {len(risk_films)/len(dialect_films)*100:.1f}%")
    print(f"占含外语方言片比例: {len(risk_films)/max(len(foreign_films),1)*100:.1f}%")

    # === 7. 列出高风险案例 ===
    print(f"\n--- 高风险案例（外语排第一，方言排后面）TOP 30 ---")
    # 按评价人数排序，取前30
    risk_sorted = sorted(risk_films, key=lambda x: -int(x["votes"]) if x["votes"].isdigit() else 0)
    for i, f in enumerate(risk_sorted[:30], 1):
        print(f"  {i:2d}. 《{f['title']}》({f['year']}) 评分:{f['rating']} 评价:{f['votes']}")
        print(f"      地区: {f['region']}")
        print(f"      语言: {f['language']}")

    # === 8. 更宽泛的风险：外语标签数量 >= 方言标签数量 ===
    print(f"\n{'=' * 70}")
    print(f"【风险分析2】外语标签数 >= 方言标签数 的方言片")
    print(f"{'=' * 70}")
    risk2_films = []
    for f in dialect_films:
        classes = f["tag_classes"]
        foreign_count = classes.count("foreign")
        dialect_count = classes.count("dialect") + classes.count("minority")
        if foreign_count > 0 and foreign_count >= dialect_count:
            risk2_films.append(f)

    print(f"外语标签数 >= 方言标签数的方言片: {len(risk2_films)} 部")
    print(f"占方言片比例: {len(risk2_films)/len(dialect_films)*100:.1f}%")

    # === 9. 各类标签在方言片中的总频次汇总 ===
    print(f"\n{'=' * 70}")
    print(f"【汇总】方言片中各类标签频次")
    print(f"{'=' * 70}")
    total_dialect = sum(1 for f in dialect_films for c in f["tag_classes"] if c == "dialect")
    total_minority = sum(1 for f in dialect_films for c in f["tag_classes"] if c == "minority")
    total_mandarin = sum(1 for f in dialect_films for c in f["tag_classes"] if c == "mandarin")
    total_foreign = sum(1 for f in dialect_films for c in f["tag_classes"] if c == "foreign")
    total_other = sum(1 for f in dialect_films for c in f["tag_classes"] if c == "other")

    print(f"  中国汉语方言标签:  {total_dialect:5d} 次")
    print(f"  中国少数民族语言:  {total_minority:5d} 次")
    print(f"  普通话类标签:      {total_mandarin:5d} 次 (汉语普通话+普通话+国语)")
    print(f"  外语标签:          {total_foreign:5d} 次 (英语+日语+泰语+法语+韩语等)")
    print(f"  其他/未分类:       {total_other:5d} 次")

    # === 10. Tier 分布（重新推算） ===
    print(f"\n--- 方言片 Tier 分布推算 ---")
    tier1 = 0  # 含方言/少数民族 + 不含普通话
    tier2a = 0  # 含方言/少数民族 + 含普通话 + 方言排第一
    tier2b = 0  # 含方言/少数民族 + 含普通话 + 普通话排第一
    for f in dialect_films:
        classes = f["tag_classes"]
        has_mandarin = "mandarin" in classes
        has_dialect = "dialect" in classes or "minority" in classes
        if not has_dialect:
            continue
        if not has_mandarin:
            tier1 += 1
        else:
            # 找第一个方言/少数民族标签和第一个普通话标签的位置
            first_dialect_idx = None
            first_mandarin_idx = None
            for i, cls in enumerate(classes):
                if cls in ("dialect", "minority") and first_dialect_idx is None:
                    first_dialect_idx = i
                if cls == "mandarin" and first_mandarin_idx is None:
                    first_mandarin_idx = i
            if first_dialect_idx is not None and first_mandarin_idx is not None:
                if first_dialect_idx < first_mandarin_idx:
                    tier2a += 1
                else:
                    tier2b += 1

    print(f"  Tier 1 (纯方言，不含普通话):  {tier1}")
    print(f"  Tier 2a (方言排第一):        {tier2a}")
    print(f"  Tier 2b (普通话排第一):      {tier2b}")
    print(f"  合计:                         {tier1+tier2a+tier2b}")


if __name__ == "__main__":
    main()
