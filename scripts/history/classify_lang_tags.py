# -*- coding: utf-8 -*-
"""Analyze all language tags in China dialect movies to classify Chinese dialects vs foreign/minority languages.

⚠️ 已废弃（2026-08-15，F4 处置）：本脚本为 v2 前旧口径的一次性分析脚本，
其中"朝鲜语"归入外语的分类与 v2.1 标准矛盾（v2.1 将朝鲜语视为中国朝鲜族
语言纳入方言口径，朝鲜半岛外语才是外语），且本地重复定义了 normalize/lang_parts。
仅作历史存档，勿再运行或复用其结论；现行口径唯一来源为 dialect_defs.py。
"""
import pandas as pd
import re
from collections import Counter

df = pd.read_csv("data/cleaned/derived_movies.csv", low_memory=False)
china = df[df["Region"] == "China"].copy()
dialect_all = china[china["Is_Dialect"] == 1].copy()

def normalize_text(v):
    if pd.isna(v):
        return ""
    return re.sub(r"\s+", " ", str(v).strip()).casefold()

def lang_parts(v):
    text = normalize_text(v)
    if not text:
        return []
    return [p.strip() for p in re.split(r"\s*(?:/|\||;|；|,)\s*", text) if p.strip()]

# Collect all unique language tags from dialect movies
all_tags = Counter()
for _, row in dialect_all.iterrows():
    parts = lang_parts(row.get("语言", ""))
    for p in parts:
        all_tags[p] += 1

print("=" * 80)
print("All language tags in current Is_Dialect=1 movies (sorted by frequency):")
print("=" * 80)
for tag, cnt in all_tags.most_common():
    print(f"  {tag}: {cnt}")

# Now classify: Chinese dialects vs foreign vs minority
CHINESE_DIALECT_TAGS = {
    # 粤语系统
    "粤语", "粵語", "cantonese", "广东话", "廣東話", "广州话", "廣州話",
    # 闽南语系统
    "闽南语", "閩南語", "hokkien", "闽南话", "閩南話", "台语", "臺語", "taiwanese",
    "福建话", "福建話", "潮州话", "潮州話", "潮汕话", "潮汕話", "汕头话",
    # 吴语系统
    "上海话", "shanghainese", "沪语", "滬語", "吴语", "吳語", "吴越方言", "吳越方言",
    "苏州话", "蘇州話", "杭州话", "寧波話", "宁波话", "温州话", "溫州話",
    # 西南官话系统
    "四川话", "四川話", "sichuanese", "四川方言", "重庆话", "重慶話", "贵州话", "雲南話", "云南话",
    # 客家话
    "客家话", "客家話", "hakka", "客家语", "客家語",
    # 湘语
    "湘语", "湘方言", "湖南话", "湖南話", "长沙话", "長沙話",
    # 赣语
    "赣语", "贛語", "赣方言", "江西话", "江西話",
    # 晋语
    "晋语", "晉語", "晋方言", "山西方言", "太原话",
    # 徽语
    "徽语", "徽州话", "徽州方言",
    # 平话
    "平话", "平話", "桂柳话",
    # 其他汉语方言
    "方言", "东北方言", "东北话", "東北話", "西北方言", "西北话",
    "河南话", "陕西话", "陝西話", "唐山话", "天津话", "广西话",
    "湖北话", "湖北方言",
}

# Foreign languages (NOT Chinese dialects)
FOREIGN_TAGS = {
    "english", "英语", "英語",
    "japanese", "日语", "日語", "日本語",
    "korean", "韩语", "韓語", "한국어", "朝鲜语", "朝鮮語",
    "french", "法语", "法語",
    "german", "德语", "德語",
    "italian", "意大利语", "義大利語",
    "spanish", "西班牙语", "西班牙語",
    "russian", "俄语", "俄語",
    "dutch", "荷兰语", "荷蘭語",
    "swedish", "瑞典语", "瑞典語",
    "danish", "丹麦语", "丹麥語",
    "norwegian", "挪威语", "挪威語",
    "polish", "波兰语", "波蘭語",
    "greek", "希腊语", "希臘語",
    "czech", "捷克语", "捷克語",
    "hungarian", "匈牙利语", "匈牙利語",
    "thai", "泰语", "泰語",
    "vietnamese", "越南语", "越南語",
    "hindi", "印地语", "印地語",
    "arabic", "阿拉伯语", "阿拉伯語",
    "portuguese", "葡萄牙语", "葡萄牙語",
    "latin", "拉丁语", "拉丁語",
    "finnish", "芬兰语", "芬蘭語",
    "tagalog", "他加禄语",
    "persian", "波斯语",
    "turkish", "土耳其语",
    "hebrew", "希伯来语",
    "romanian", "罗马尼亚语",
    "catalan", "加泰罗尼亚语",
    "galician", "加利西亚语",
    "basque", "巴斯克语",
    "esperanto",
    "world",
    "aboriginal",
    "mayan",
    "quechua",
}

# Minority languages (NOT Chinese dialects - they are separate languages)
MINORITY_TAGS = {
    "藏语", "藏語", "tibetan",
    "维吾尔语", "維吾爾語", "uyghur", "uighur",
    "蒙古语", "蒙古語", "mongolian",
    "满语", "滿語", "manchu",
    "哈萨克语", "哈薩克語", "kazakh",
    "朝鲜语"  # This is tricky - 朝鲜语 in China context could be Korean minority language
              # But we already have it in FOREIGN_TAGS, so it's covered
    ,
    "苗语", "苗語", "hmong",
    "彝语", "彝語", "yi language",
    "壮语", "壯語", "zhuang",
    "傣语", "傣語", "dai",
    "侗语", "侗語", "dong",
    "瑶语", "瑤語",
    "白语", "白語",
    "哈尼语", "哈尼語",
    "傈僳语", "傈僳語",
    "佤语", "佤語",
    "拉祜语", "拉祜語",
    "纳西语", "納西語",
    "锡伯语", "錫伯語",
}

# Mandarin tags (NOT dialect)
MANDARIN_TAGS = {
    "汉语普通话", "漢語普通話", "普通话", "普通話", "mandarin",
    "国语", "國語", "汉语", "漢語", "中文",
}

print("\n" + "=" * 80)
print("Classification of all tags:")
print("=" * 80)

uncategorized = []
for tag, cnt in all_tags.most_common():
    tnorm = normalize_text(tag)
    if any(normalize_text(t) in tnorm or tnorm in normalize_text(t) for t in CHINESE_DIALECT_TAGS):
        cat = "Chinese_Dialect"
    elif any(normalize_text(t) in tnorm for t in FOREIGN_TAGS):
        cat = "Foreign"
    elif any(normalize_text(t) in tnorm for t in MINORITY_TAGS):
        cat = "Minority"
    elif any(normalize_text(t) in tnorm for t in MANDARIN_TAGS):
        cat = "Mandarin"
    else:
        cat = "UNCATEGORIZED"
        uncategorized.append((tag, cnt))
    print(f"  [{cat:15s}] {tag}: {cnt}")

if uncategorized:
    print(f"\n!!! {len(uncategorized)} UNCATEGORIZED tags !!!")
    for tag, cnt in uncategorized:
        print(f"  {tag}: {cnt}")
