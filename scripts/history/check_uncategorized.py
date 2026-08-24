"""DEPRECATED — stale WeChat absolute paths. Do not run.

Check for uncategorized first languages."""
import csv, re
from collections import Counter

CSV_PATH = "D:/WeChat/Doocuments/xwechat_files/wxid_peaubjuu1zuj22_3738/msg/file/2026-07/movie-rating-data-story-main/movie-rating-data-story-main/data/derived_movies.csv"

CHINESE_MARKERS = (
    "汉语", "漢語", "中文", "普通话", "普通話", "mandarin", "国语", "國語",
    "cantonese", "粤语", "粵語", "广东话", "廣東話",
    "hokkien", "闽南", "閩南", "hakka", "客家", "shanghainese", "沪语", "滬語",
    "sichuanese", "四川话", "taiwanese", "台语", "臺語",
    "藏语", "藏語", "tibetan", "维吾尔", "uyghur", "uighur",
    "蒙古语", "蒙古語", "mongolian", "哈萨克", "kazakh",
    "苗语", "彝语", "壮语", "傣语", "侗语", "瑶语", "白语",
    "哈尼语", "傈僳", "佤语", "拉祜", "纳西", "锡伯", "朝鲜语", "朝鮮語",
    "手语", "手語", "sign language",
    "湘语", "赣语", "晋语", "徽语", "平话",
    "北京话", "南京话", "东北话", "河南话", "陕西话", "山东话", "天津话",
    "武汉话", "贵州话", "云南话", "长沙话", "南昌话",
)

KNOWN_FOREIGN = (
    "english", "英语", "英語", "japanese", "日语", "日語", "日本語",
    "korean", "韩语", "韓語", "한국어", "french", "法语", "法語",
    "german", "德语", "德語", "italian", "意大利", "義大利",
    "spanish", "西班牙", "portuguese", "葡萄牙",
    "russian", "俄语", "俄語", "dutch", "荷兰", "荷蘭",
    "swedish", "瑞典", "danish", "丹麦", "丹麥",
    "norwegian", "挪威", "polish", "波兰", "波蘭",
    "greek", "希腊", "希臘", "czech", "捷克",
    "hungarian", "匈牙利", "finnish", "芬兰", "芬蘭",
    "romanian", "罗马尼亚", "羅馬尼亞", "bulgarian", "保加利亚",
    "croatian", "克罗地亚", "serbian", "塞尔维亚",
    "slovenian", "斯洛文尼亚", "slovak", "斯洛伐克",
    "icelandic", "冰岛", "冰島", "latvian", "拉脱维亚",
    "lithuanian", "立陶宛", "estonian", "爱沙尼亚", "愛沙尼亞",
    "arabic", "阿拉伯", "hebrew", "希伯来", "希伯來",
    "hindi", "印地语", "thai", "泰语", "泰語",
    "vietnamese", "越南", "indonesian", "印尼",
    "malay", "马来", "馬來", "tagalog", "filipino", "菲律宾", "菲律賓",
    "turkish", "土耳其", "persian", "波斯", "farsi",
    "urdu", "乌尔都", "bengali", "孟加拉",
    "tamil", "泰米尔", "telugu", "泰卢固",
    "malayalam", "马拉雅拉姆", "kannada", "卡纳达",
    "punjabi", "旁遮普", "swahili", "斯瓦希里",
    "amharic", "阿姆哈拉", "catalan", "加泰罗尼亚",
    "basque", "巴斯克", "welsh", "威尔士", "威爾士",
    "irish", "爱尔兰", "愛爾蘭", "albanian", "阿尔巴尼亚",
    "armenian", "亚美尼亚", "georgian", "格鲁吉亚",
    "macedonian", "马其顿", "bosnian", "波斯尼亚",
    "ukrainian", "乌克兰", "烏克蘭", "belarusian", "白俄罗斯",
    "latin", "拉丁", "esperanto", "nepali", "尼泊尔",
    "sinhala", "僧伽罗", "khmer", "高棉", "柬埔寨",
    "lao", "老挝", "老撾", "burmese", "缅甸", "緬甸",
    "maori", "毛利", "hawaiian", "夏威夷",
    "samoan", "萨摩亚", "zulu", "祖鲁", "祖魯",
    "afrikaans", "yiddish", "意第绪", "quechua",
    "navajo", "inuktitut", "pashto", "普什图",
    "dari", "kurdish", "库尔德", "somali", "索马里",
    "sanskrit", "梵语", "梵語", "wolof", "hausa", "yoruba",
    "igbo", "malagasy", "fijian",
)

def normalize_text(value):
    if value is None: return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()

def contains_any(text, markers):
    return any(m in text for m in markers)

def language_parts(value):
    text = normalize_text(value)
    if not text: return []
    return [p.strip() for p in re.split(r"\s*(?:/|\||;|;|,)\s*", text) if p.strip()]

uncategorized = Counter()
with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        lang_raw = row.get("语言", "")
        parts = language_parts(lang_raw)
        if not parts: continue
        first = parts[0]
        if first in ("无声", "无对白", "silence", "silent", "无", ""): continue
        if not contains_any(first, CHINESE_MARKERS) and not contains_any(first, KNOWN_FOREIGN):
            uncategorized[first] += 1

print("Uncategorized first languages (neither Chinese nor known foreign):")
for lang, count in uncategorized.most_common(50):
    print(f"  '{lang}': {count}")
print(f"\nTotal uncategorized types: {len(uncategorized)}")
print(f"Total uncategorized films: {sum(uncategorized.values())}")
