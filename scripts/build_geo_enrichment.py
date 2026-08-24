"""Build geographic enrichment for the frontend particle engine.

Reads derived_movies.csv, extracts the first listed production country,
maps it to (latitude, longitude) centroid and a fine-grained geo_region,
then writes data/frontend/geo_enrichment.json.

The enrichment payload is a compact columnar array so the frontend can
merge it with the existing frontend_dataset.json records by index.

geo_region codes (extends the existing 0-4 Region_Code):
  0  North_America   (same as Region_Code 0)
  1  Europe          (same as Region_Code 1)
  2  East_Asia       (same as Region_Code 2)
  3  China           (same as Region_Code 3)
  5  South_America
  6  Africa
  7  Oceania
  8  South_Asia      (India, Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan)
  9  Southeast_Asia  (Thailand, Vietnam, Indonesia, Philippines, etc.)
  10 West_Asia       (Iran, Israel, Turkey, Lebanon, Saudi Arabia, etc.)
  11 Central_Asia     (Kazakhstan, Uzbekistan, etc.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DERIVED_MOVIES_INFO, GEO_ENRICHMENT, SAMPLE_MANIFEST, atomic_write_text  # noqa: E402
from data_processor import first_listed_value  # noqa: E402

# ---------------------------------------------------------------------------
# Country → (lat, lng, geo_region) mapping
# ---------------------------------------------------------------------------
# geo_region: 0=NA, 1=Europe, 2=EastAsia, 3=China, 5=S.America, 6=Africa,
#             7=Oceania, 8=S.Asia, 9=SE.Asia, 10=W.Asia, 11=C.Asia

# Format: "normalized_country": (lat, lng, geo_region, display_name)
COUNTRY_DB: dict[str, tuple[float, float, int, str]] = {
    # ---- China (3) ----
    "中国": (35.0, 105.0, 3, "中国"),
    "china": (35.0, 105.0, 3, "中国"),
    "中国香港": (22.3, 114.2, 3, "中国香港"),
    "hong kong": (22.3, 114.2, 3, "中国香港"),
    "香港": (22.3, 114.2, 3, "中国香港"),
    "中国台湾": (23.5, 121.0, 3, "中国台湾"),
    "中国台湾": (23.5, 121.0, 3, "中国台湾"),
    "台湾": (23.5, 121.0, 3, "中国台湾"),
    "臺灣": (23.5, 121.0, 3, "中国台湾"),
    "taiwan": (23.5, 121.0, 3, "中国台湾"),
    "中国澳门": (22.2, 113.5, 3, "中国澳门"),
    "macau": (22.2, 113.5, 3, "中国澳门"),
    "macao": (22.2, 113.5, 3, "中国澳门"),
    "澳门": (22.2, 113.5, 3, "中国澳门"),
    "澳門": (22.2, 113.5, 3, "中国澳门"),

    # ---- North America (0) ----
    "美国": (39.0, -98.0, 0, "美国"),
    "united states": (39.0, -98.0, 0, "美国"),
    "u.s.a": (39.0, -98.0, 0, "美国"),
    "usa": (39.0, -98.0, 0, "美国"),
    "加拿大": (56.0, -106.0, 0, "加拿大"),
    "canada": (56.0, -106.0, 0, "加拿大"),
    "墨西哥": (23.0, -102.0, 0, "墨西哥"),
    "mexico": (23.0, -102.0, 0, "墨西哥"),

    # ---- East Asia (2) ----
    "日本": (36.0, 138.0, 2, "日本"),
    "japan": (36.0, 138.0, 2, "日本"),
    "韩国": (36.0, 128.0, 2, "韩国"),
    "韓國": (36.0, 128.0, 2, "韩国"),
    "south korea": (36.0, 128.0, 2, "韩国"),
    "republic of korea": (36.0, 128.0, 2, "韩国"),
    "korea": (36.0, 128.0, 2, "韩国"),
    "朝鲜": (39.0, 126.0, 2, "朝鲜"),
    "朝鮮": (39.0, 126.0, 2, "朝鲜"),
    "north korea": (39.0, 126.0, 2, "朝鲜"),
    "蒙古": (47.0, 104.0, 2, "蒙古"),
    "mongolia": (47.0, 104.0, 2, "蒙古"),

    # ---- Europe (1) ----
    "欧洲": (50.0, 10.0, 1, "欧洲"),
    "europe": (50.0, 10.0, 1, "欧洲"),
    "英国": (54.0, -2.0, 1, "英国"),
    "英國": (54.0, -2.0, 1, "英国"),
    "united kingdom": (54.0, -2.0, 1, "英国"),
    "uk": (54.0, -2.0, 1, "英国"),
    "england": (54.0, -2.0, 1, "英国"),
    "britain": (54.0, -2.0, 1, "英国"),
    "法国": (46.0, 2.0, 1, "法国"),
    "france": (46.0, 2.0, 1, "法国"),
    "德国": (51.0, 10.0, 1, "德国"),
    "germany": (51.0, 10.0, 1, "德国"),
    "西德": (51.0, 10.0, 1, "西德"),
    "west germany": (51.0, 10.0, 1, "西德"),
    "东德": (52.0, 13.0, 1, "东德"),
    "東德": (52.0, 13.0, 1, "东德"),
    "east germany": (52.0, 13.0, 1, "东德"),
    "意大利": (42.0, 12.0, 1, "意大利"),
    "意大利": (42.0, 12.0, 1, "意大利"),
    "spain": (40.0, -4.0, 1, "西班牙"),
    "西班牙": (40.0, -4.0, 1, "西班牙"),
    "葡萄牙": (39.5, -8.0, 1, "葡萄牙"),
    "portugal": (39.5, -8.0, 1, "葡萄牙"),
    "爱尔兰": (53.0, -8.0, 1, "爱尔兰"),
    "愛爾蘭": (53.0, -8.0, 1, "爱尔兰"),
    "ireland": (53.0, -8.0, 1, "爱尔兰"),
    "荷兰": (52.0, 5.0, 1, "荷兰"),
    "holland": (52.0, 5.0, 1, "荷兰"),
    "荷兰": (52.0, 5.0, 1, "荷兰"),
    "belgium": (50.8, 4.5, 1, "比利时"),
    "比利时": (50.8, 4.5, 1, "比利时"),
    "比利時": (50.8, 4.5, 1, "比利时"),
    "switzerland": (47.0, 8.0, 1, "瑞士"),
    "瑞士": (47.0, 8.0, 1, "瑞士"),
    "austria": (47.5, 14.5, 1, "奥地利"),
    "奥地利": (47.5, 14.5, 1, "奥地利"),
    "奧地利": (47.5, 14.5, 1, "奥地利"),
    "sweden": (62.0, 15.0, 1, "瑞典"),
    "瑞典": (62.0, 15.0, 1, "瑞典"),
    "norway": (62.0, 10.0, 1, "挪威"),
    "挪威": (62.0, 10.0, 1, "挪威"),
    "denmark": (56.0, 10.0, 1, "丹麦"),
    "丹麦": (56.0, 10.0, 1, "丹麦"),
    "丹麥": (56.0, 10.0, 1, "丹麦"),
    "finland": (64.0, 26.0, 1, "芬兰"),
    "芬兰": (64.0, 26.0, 1, "芬兰"),
    "芬蘭": (64.0, 26.0, 1, "芬兰"),
    "iceland": (65.0, -18.0, 1, "冰岛"),
    "冰岛": (65.0, -18.0, 1, "冰岛"),
    "冰島": (65.0, -18.0, 1, "冰岛"),
    "poland": (52.0, 20.0, 1, "波兰"),
    "波兰": (52.0, 20.0, 1, "波兰"),
    "波蘭": (52.0, 20.0, 1, "波兰"),
    "czech": (50.0, 15.0, 1, "捷克"),
    "捷克": (50.0, 15.0, 1, "捷克"),
    "slovakia": (48.7, 19.7, 1, "斯洛伐克"),
    "斯洛伐克": (48.7, 19.7, 1, "斯洛伐克"),
    "hungary": (47.0, 20.0, 1, "匈牙利"),
    "匈牙利": (47.0, 20.0, 1, "匈牙利"),
    "romania": (46.0, 25.0, 1, "罗马尼亚"),
    "罗马尼亚": (46.0, 25.0, 1, "罗马尼亚"),
    "羅馬尼亞": (46.0, 25.0, 1, "罗马尼亚"),
    "bulgaria": (43.0, 25.0, 1, "保加利亚"),
    "保加利亚": (43.0, 25.0, 1, "保加利亚"),
    "保加利亞": (43.0, 25.0, 1, "保加利亚"),
    "greece": (39.0, 22.0, 1, "希腊"),
    "希腊": (39.0, 22.0, 1, "希腊"),
    "希臘": (39.0, 22.0, 1, "希腊"),
    "croatia": (45.0, 16.0, 1, "克罗地亚"),
    "克罗地亚": (45.0, 16.0, 1, "克罗地亚"),
    "克羅地亞": (45.0, 16.0, 1, "克罗地亚"),
    "serbia": (44.0, 21.0, 1, "塞尔维亚"),
    "塞尔维亚": (44.0, 21.0, 1, "塞尔维亚"),
    "塞爾維亞": (44.0, 21.0, 1, "塞尔维亚"),
    "slovenia": (46.0, 15.0, 1, "斯洛文尼亚"),
    "斯洛文尼亚": (46.0, 15.0, 1, "斯洛文尼亚"),
    "斯洛文尼亞": (46.0, 15.0, 1, "斯洛文尼亚"),
    "ukraine": (49.0, 32.0, 1, "乌克兰"),
    "乌克兰": (49.0, 32.0, 1, "乌克兰"),
    "烏克蘭": (49.0, 32.0, 1, "乌克兰"),
    "russia": (60.0, 100.0, 1, "俄罗斯"),
    "俄罗斯": (60.0, 100.0, 1, "俄罗斯"),
    "俄羅斯": (60.0, 100.0, 1, "俄罗斯"),
    "ussr": (56.0, 37.0, 1, "苏联"),
    "soviet union": (56.0, 37.0, 1, "苏联"),
    "苏联": (56.0, 37.0, 1, "苏联"),
    "蘇聯": (56.0, 37.0, 1, "苏联"),
    "estonia": (59.0, 25.0, 1, "爱沙尼亚"),
    "爱沙尼亚": (59.0, 25.0, 1, "爱沙尼亚"),
    "愛沙尼亞": (59.0, 25.0, 1, "爱沙尼亚"),
    "latvia": (57.0, 25.0, 1, "拉脱维亚"),
    "拉脱维亚": (57.0, 25.0, 1, "拉脱维亚"),
    "拉脫維亞": (57.0, 25.0, 1, "拉脱维亚"),
    "lithuania": (55.0, 24.0, 1, "立陶宛"),
    "立陶宛": (55.0, 24.0, 1, "立陶宛"),
    "luxembourg": (49.8, 6.1, 1, "卢森堡"),
    "卢森堡": (49.8, 6.1, 1, "卢森堡"),
    "盧森堡": (49.8, 6.1, 1, "卢森堡"),
    # Additional European
    "南斯拉夫": (44.0, 21.0, 1, "南斯拉夫"),
    "波黑": (43.9, 17.7, 1, "波黑"),
    "马其顿": (41.5, 21.7, 1, "马其顿"),
    "阿尔巴尼亚": (41.0, 20.0, 1, "阿尔巴尼亚"),
    "格鲁吉亚": (42.0, 43.4, 1, "格鲁吉亚"),
    "哈萨克斯坦": (48.0, 68.0, 11, "哈萨克斯坦"),
    "吉尔吉斯斯坦": (41.0, 75.0, 11, "吉尔吉斯斯坦"),

    # ---- South America (5) ----
    "巴西": (-10.0, -55.0, 5, "巴西"),
    "brazil": (-10.0, -55.0, 5, "巴西"),
    "阿根廷": (-34.0, -64.0, 5, "阿根廷"),
    "argentina": (-34.0, -64.0, 5, "阿根廷"),
    "智利": (-33.0, -71.0, 5, "智利"),
    "chile": (-33.0, -71.0, 5, "智利"),
    "哥伦比亚": (4.0, -72.0, 5, "哥伦比亚"),
    "colombia": (4.0, -72.0, 5, "哥伦比亚"),
    "委内瑞拉": (8.0, -66.0, 5, "委内瑞拉"),
    "venezuela": (8.0, -66.0, 5, "委内瑞拉"),
    "乌拉圭": (-33.0, -56.0, 5, "乌拉圭"),
    "uruguay": (-33.0, -56.0, 5, "乌拉圭"),
    "古巴": (22.0, -80.0, 5, "古巴"),
    "cuba": (22.0, -80.0, 5, "古巴"),
    "秘鲁": (-10.0, -76.0, 5, "秘鲁"),
    "peru": (-10.0, -76.0, 5, "秘鲁"),
    "巴拉圭": (-23.0, -58.0, 5, "巴拉圭"),
    "paraguay": (-23.0, -58.0, 5, "巴拉圭"),
    "厄瓜多尔": (-1.0, -78.0, 5, "厄瓜多尔"),
    "ecuador": (-1.0, -78.0, 5, "厄瓜多尔"),
    "玻利维亚": (-17.0, -65.0, 5, "玻利维亚"),
    "bolivia": (-17.0, -65.0, 5, "玻利维亚"),
    "多米尼加": (19.0, -70.0, 5, "多米尼加"),
    "dominican republic": (19.0, -70.0, 5, "多米尼加"),
    "波多黎各": (18.2, -66.5, 5, "波多黎各"),
    "puerto rico": (18.2, -66.5, 5, "波多黎各"),
    "巴拿马": (9.0, -80.0, 5, "巴拿马"),
    "panama": (9.0, -80.0, 5, "巴拿马"),
    "阿鲁巴": (12.5, -70.0, 5, "阿鲁巴"),
    "aruba": (12.5, -70.0, 5, "阿鲁巴"),
    "危地马拉": (15.5, -90.0, 5, "危地马拉"),
    "guatemala": (15.5, -90.0, 5, "危地马拉"),
    "哥斯达黎加": (10.0, -84.0, 5, "哥斯达黎加"),
    "costa rica": (10.0, -84.0, 5, "哥斯达黎加"),
    "洪都拉斯": (15.0, -87.0, 5, "洪都拉斯"),
    "honduras": (15.0, -87.0, 5, "洪都拉斯"),
    "牙买加": (18.1, -77.3, 5, "牙买加"),
    "jamaica": (18.1, -77.3, 5, "牙买加"),

    # ---- Africa (6) ----
    "南非": (-30.0, 25.0, 6, "南非"),
    "south africa": (-30.0, 25.0, 6, "南非"),
    "埃及": (27.0, 30.0, 6, "埃及"),
    "egypt": (27.0, 30.0, 6, "埃及"),
    "突尼斯": (34.0, 9.0, 6, "突尼斯"),
    "tunisia": (34.0, 9.0, 6, "突尼斯"),
    "塞内加尔": (14.5, -14.5, 6, "塞内加尔"),
    "senegal": (14.5, -14.5, 6, "塞内加尔"),
    "阿尔及利亚": (28.0, 3.0, 6, "阿尔及利亚"),
    "algeria": (28.0, 3.0, 6, "阿尔及利亚"),
    "摩洛哥": (32.0, -5.0, 6, "摩洛哥"),
    "morocco": (32.0, -5.0, 6, "摩洛哥"),
    "尼日利亚": (10.0, 8.0, 6, "尼日利亚"),
    "nigeria": (10.0, 8.0, 6, "尼日利亚"),
    "肯尼亚": (-1.0, 38.0, 6, "肯尼亚"),
    "kenya": (-1.0, 38.0, 6, "肯尼亚"),
    "埃塞俄比亚": (9.0, 38.5, 6, "埃塞俄比亚"),
    "ethiopia": (9.0, 38.5, 6, "埃塞俄比亚"),
    "加纳": (8.0, -1.0, 6, "加纳"),
    "ghana": (8.0, -1.0, 6, "加纳"),
    "喀麦隆": (6.0, 12.0, 6, "喀麦隆"),
    "cameroon": (6.0, 12.0, 6, "喀麦隆"),
    "刚果": (-4.0, 15.0, 6, "刚果"),
    "congo": (-4.0, 15.0, 6, "刚果"),
    "坦桑尼亚": (-6.0, 35.0, 6, "坦桑尼亚"),
    "tanzania": (-6.0, 35.0, 6, "坦桑尼亚"),
    "乌干达": (1.0, 32.0, 6, "乌干达"),
    "uganda": (1.0, 32.0, 6, "乌干达"),
    "津巴布韦": (-20.0, 30.0, 6, "津巴布韦"),
    "zimbabwe": (-20.0, 30.0, 6, "津巴布韦"),
    "莫桑比克": (-18.0, 35.0, 6, "莫桑比克"),
    "mozambique": (-18.0, 35.0, 6, "莫桑比克"),
    "卢旺达": (-2.0, 30.0, 6, "卢旺达"),
    "rwanda": (-2.0, 30.0, 6, "卢旺达"),
    "苏丹": (16.0, 30.0, 6, "苏丹"),
    "sudan": (16.0, 30.0, 6, "苏丹"),
    "毛里塔尼亚": (20.0, -12.0, 6, "毛里塔尼亚"),
    "mauritania": (20.0, -12.0, 6, "毛里塔尼亚"),
    "马里": (17.0, -2.0, 6, "马里"),
    "mali": (17.0, -2.0, 6, "马里"),
    "乍得": (15.0, 19.0, 6, "乍得"),
    "chad": (15.0, 19.0, 6, "乍得"),
    "贝宁": (9.5, 2.0, 6, "贝宁"),
    "benin": (9.5, 2.0, 6, "贝宁"),
    "布基纳法索": (12.0, -1.5, 6, "布基纳法索"),
    "burkina faso": (12.0, -1.5, 6, "布基纳法索"),
    "几内亚": (11.0, -10.0, 6, "几内亚"),
    "guinea": (11.0, -10.0, 6, "几内亚"),
    "科特迪瓦": (7.0, -5.5, 6, "科特迪瓦"),
    "ivory coast": (7.0, -5.5, 6, "科特迪瓦"),
    "马达加斯加": (-19.0, 47.0, 6, "马达加斯加"),
    "madagascar": (-19.0, 47.0, 6, "马达加斯加"),
    "毛里求斯": (-20.3, 57.5, 6, "毛里求斯"),
    "mauritius": (-20.3, 57.5, 6, "毛里求斯"),
    "纳米比亚": (-22.0, 17.0, 6, "纳米比亚"),
    "namibia": (-22.0, 17.0, 6, "纳米比亚"),
    "博茨瓦纳": (-22.0, 24.0, 6, "博茨瓦纳"),
    "botswana": (-22.0, 24.0, 6, "博茨瓦纳"),
    "塞拉利昂": (8.5, -11.5, 6, "塞拉利昂"),
    "sierra leone": (8.5, -11.5, 6, "塞拉利昂"),
    "利比里亚": (6.5, -9.5, 6, "利比里亚"),
    "liberia": (6.5, -9.5, 6, "利比里亚"),
    "尼日尔": (17.5, 8.0, 6, "尼日尔"),
    "niger": (17.5, 8.0, 6, "尼日尔"),
    "刚果（金）": (-4.0, 22.0, 6, "刚果(金)"),
    "dr congo": (-4.0, 22.0, 6, "刚果(金)"),

    # ---- Oceania (7) ----
    "澳大利亚": (-25.0, 133.0, 7, "澳大利亚"),
    "australia": (-25.0, 133.0, 7, "澳大利亚"),
    "新西兰": (-41.0, 174.0, 7, "新西兰"),
    "new zealand": (-41.0, 174.0, 7, "新西兰"),
    "巴布亚新几内亚": (-6.0, 147.0, 7, "巴布亚新几内亚"),
    "papua new guinea": (-6.0, 147.0, 7, "巴布亚新几内亚"),
    "斐济": (-18.0, 178.0, 7, "斐济"),
    "fiji": (-18.0, 178.0, 7, "斐济"),

    # ---- South Asia (8) ----
    "印度": (22.0, 78.0, 8, "印度"),
    "india": (22.0, 78.0, 8, "印度"),
    "巴基斯坦": (30.0, 70.0, 8, "巴基斯坦"),
    "pakistan": (30.0, 70.0, 8, "巴基斯坦"),
    "孟加拉国": (24.0, 90.0, 8, "孟加拉国"),
    "bangladesh": (24.0, 90.0, 8, "孟加拉国"),
    "斯里兰卡": (7.5, 80.5, 8, "斯里兰卡"),
    "sri lanka": (7.5, 80.5, 8, "斯里兰卡"),
    "尼泊尔": (28.0, 84.0, 8, "尼泊尔"),
    "nepal": (28.0, 84.0, 8, "尼泊尔"),
    "不丹": (27.5, 90.5, 8, "不丹"),
    "bhutan": (27.5, 90.5, 8, "不丹"),

    # ---- Southeast Asia (9) ----
    "泰国": (15.0, 100.0, 9, "泰国"),
    "thailand": (15.0, 100.0, 9, "泰国"),
    "菲律宾": (12.0, 122.0, 9, "菲律宾"),
    "philippines": (12.0, 122.0, 9, "菲律宾"),
    "新加坡": (1.3, 103.8, 9, "新加坡"),
    "singapore": (1.3, 103.8, 9, "新加坡"),
    "马来西亚": (4.0, 102.0, 9, "马来西亚"),
    "malaysia": (4.0, 102.0, 9, "马来西亚"),
    "印度尼西亚": (-5.0, 120.0, 9, "印度尼西亚"),
    "indonesia": (-5.0, 120.0, 9, "印度尼西亚"),
    "印尼": (-5.0, 120.0, 9, "印度尼西亚"),
    "越南": (16.0, 108.0, 9, "越南"),
    "vietnam": (16.0, 108.0, 9, "越南"),
    "柬埔寨": (12.5, 105.0, 9, "柬埔寨"),
    "cambodia": (12.5, 105.0, 9, "柬埔寨"),
    "缅甸": (20.0, 96.0, 9, "缅甸"),
    "myanmar": (20.0, 96.0, 9, "缅甸"),
    "burma": (20.0, 96.0, 9, "缅甸"),
    "老挝": (18.0, 103.0, 9, "老挝"),
    "laos": (18.0, 103.0, 9, "老挝"),
    "文莱": (4.5, 114.5, 9, "文莱"),
    "brunei": (4.5, 114.5, 9, "文莱"),

    # ---- West Asia / Middle East (10) ----
    "伊朗": (33.0, 53.0, 10, "伊朗"),
    "iran": (33.0, 53.0, 10, "伊朗"),
    "以色列": (31.5, 35.0, 10, "以色列"),
    "israel": (31.5, 35.0, 10, "以色列"),
    "土耳其": (39.0, 35.0, 10, "土耳其"),
    "turkey": (39.0, 35.0, 10, "土耳其"),
    "黎巴嫩": (33.9, 35.9, 10, "黎巴嫩"),
    "lebanon": (33.9, 35.9, 10, "黎巴嫩"),
    "沙特阿拉伯": (24.0, 45.0, 10, "沙特阿拉伯"),
    "saudi arabia": (24.0, 45.0, 10, "沙特阿拉伯"),
    "巴勒斯坦": (31.9, 35.2, 10, "巴勒斯坦"),
    "palestine": (31.9, 35.2, 10, "巴勒斯坦"),
    "约旦": (31.0, 36.0, 10, "约旦"),
    "jordan": (31.0, 36.0, 10, "约旦"),
    "阿联酋": (24.0, 54.0, 10, "阿联酋"),
    "united arab emirates": (24.0, 54.0, 10, "阿联酋"),
    "伊拉克": (33.0, 44.0, 10, "伊拉克"),
    "iraq": (33.0, 44.0, 10, "伊拉克"),
    "叙利亚": (35.0, 38.0, 10, "叙利亚"),
    "syria": (35.0, 38.0, 10, "叙利亚"),
    "阿富汗": (34.0, 66.0, 10, "阿富汗"),
    "afghanistan": (34.0, 66.0, 10, "阿富汗"),
    "也门": (15.5, 48.0, 10, "也门"),
    "yemen": (15.5, 48.0, 10, "也门"),
    "阿曼": (21.0, 57.0, 10, "阿曼"),
    "oman": (21.0, 57.0, 10, "阿曼"),
    "卡塔尔": (25.3, 51.2, 10, "卡塔尔"),
    "qatar": (25.3, 51.2, 10, "卡塔尔"),
    "科威特": (29.5, 47.5, 10, "科威特"),
    "kuwait": (29.5, 47.5, 10, "科威特"),
    "格鲁吉亚": (42.0, 43.4, 10, "格鲁吉亚"),
    "georgia": (42.0, 43.4, 10, "格鲁吉亚"),
    "亚美尼亚": (40.0, 45.0, 10, "亚美尼亚"),
    "armenia": (40.0, 45.0, 10, "亚美尼亚"),
    "阿塞拜疆": (40.0, 50.0, 10, "阿塞拜疆"),
    "azerbaijan": (40.0, 50.0, 10, "阿塞拜疆"),
    # Additional missing entries (patched 2026-08-19)
    "italy": (42.0, 12.0, 1, "意大利"),
    "摩尔多瓦": (47.0, 29.0, 1, "摩尔多瓦"),
    "moldova": (47.0, 29.0, 1, "摩尔多瓦"),
    "塞浦路斯": (35.0, 33.0, 1, "塞浦路斯"),
    "cyprus": (35.0, 33.0, 1, "塞浦路斯"),
    "科索沃": (42.6, 21.0, 1, "科索沃"),
    "kosovo": (42.6, 21.0, 1, "科索沃"),
    "台灣": (23.5, 121.0, 3, "中国台湾"),
    "泰國": (15.0, 100.0, 9, "泰国"),
    "巴哈马": (24.0, -76.0, 5, "巴哈马"),
    "bahamas": (24.0, -76.0, 5, "巴哈马"),
    "格陵兰": (72.0, -40.0, 1, "格陵兰"),
    "greenland": (72.0, -40.0, 1, "格陵兰"),
    "马耳他": (35.9, 14.4, 1, "马耳他"),
    "malta": (35.9, 14.4, 1, "马耳他"),
    "黑山": (42.7, 19.4, 1, "黑山"),
    "montenegro": (42.7, 19.4, 1, "黑山"),
    "北爱尔兰": (54.6, -7.0, 1, "北爱尔兰"),
    "northern ireland": (54.6, -7.0, 1, "北爱尔兰"),
    "法罗群岛": (62.0, -7.0, 1, "法罗群岛"),
    "faroe islands": (62.0, -7.0, 1, "法罗群岛"),
    "直布罗陀": (36.1, -5.4, 1, "直布罗陀"),
    "gibraltar": (36.1, -5.4, 1, "直布罗陀"),
    "北马其顿": (41.5, 21.7, 1, "北马其顿"),
    "north macedonia": (41.5, 21.7, 1, "北马其顿"),
    "乌兹别克斯坦": (41.0, 64.0, 11, "乌兹别克斯坦"),
    "uzbekistan": (41.0, 64.0, 11, "乌兹别克斯坦"),
    "塔吉克斯坦": (39.0, 71.0, 11, "塔吉克斯坦"),
    "tajikistan": (39.0, 71.0, 11, "塔吉克斯坦"),
    "土库曼斯坦": (40.0, 59.0, 11, "土库曼斯坦"),
    "turkmenistan": (40.0, 59.0, 11, "土库曼斯坦"),
}

# Remove duplicate key for 格鲁吉亚 (it's in both Europe and West Asia sections)
# Keep the West Asia mapping as it's more geographically accurate
del COUNTRY_DB["格鲁吉亚"]
COUNTRY_DB["格鲁吉亚"] = (42.0, 43.4, 10, "格鲁吉亚")

GEO_REGION_LABELS = {
    0: "North_America",
    1: "Europe",
    2: "East_Asia",
    3: "China",
    5: "South_America",
    6: "Africa",
    7: "Oceania",
    8: "South_Asia",
    9: "Southeast_Asia",
    10: "West_Asia",
    11: "Central_Asia",
}

# ---------------------------------------------------------------------------
# Country → (dlng, dlat) geographic spread for particle distribution
# ---------------------------------------------------------------------------
# Controls how far movies can spread from the centroid within each country.
# Larger countries get bigger spreads to fill continental shapes.
# Key = display name (4th element of COUNTRY_DB tuples)

COUNTRY_SPREADS: dict[str, tuple[float, float]] = {
    # Large countries
    "美国": (13.0, 5.0),
    "加拿大": (15.0, 6.0),
    "中国": (12.0, 7.0),
    "俄罗斯": (15.0, 5.0),
    "巴西": (12.0, 10.0),
    "澳大利亚": (12.0, 8.0),
    "印度": (10.0, 9.0),
    "阿根廷": (7.0, 10.0),
    "墨西哥": (8.0, 5.0),
    # Medium countries
    "法国": (2.5, 2.5),
    "德国": (3.0, 3.0),
    "意大利": (3.5, 3.0),
    "西班牙": (3.5, 3.0),
    "英国": (3.0, 4.0),
    "日本": (5.0, 6.0),
    "韩国": (2.5, 3.0),
    "印度尼西亚": (12.0, 4.0),
    "南非": (6.0, 6.0),
    "埃及": (5.0, 4.0),
    "土耳其": (6.0, 3.0),
    "伊朗": (6.0, 4.0),
    "波兰": (3.0, 2.5),
    "瑞典": (3.5, 5.0),
    "挪威": (4.0, 7.0),
    "芬兰": (3.5, 4.5),
    "丹麦": (2.0, 2.5),
    "荷兰": (1.5, 1.5),
    "比利时": (1.2, 1.2),
    "瑞士": (1.5, 1.2),
    "奥地利": (2.0, 1.5),
    "葡萄牙": (1.8, 2.5),
    "希腊": (2.5, 2.5),
    "捷克": (1.8, 1.5),
    "匈牙利": (2.0, 1.8),
    "罗马尼亚": (2.5, 2.0),
    "泰国": (4.0, 5.0),
    "菲律宾": (5.0, 5.0),
    "马来西亚": (4.0, 5.0),
    "越南": (3.5, 5.0),
    "巴基斯坦": (5.0, 5.0),
    "孟加拉国": (3.0, 3.5),
    "智利": (3.5, 12.0),
    "哥伦比亚": (4.5, 6.0),
    "秘鲁": (4.5, 6.0),
    "委内瑞拉": (4.5, 5.0),
    "新西兰": (4.0, 6.0),
    "以色列": (1.5, 3.0),
    "黎巴嫩": (1.2, 1.5),
    "沙特阿拉伯": (6.0, 6.0),
    # Small countries/territories
    "中国香港": (0.3, 0.3),
    "中国台湾": (0.8, 0.8),
    "中国澳门": (0.1, 0.1),
    "新加坡": (0.3, 0.3),
    "冰岛": (2.5, 1.5),
    "爱尔兰": (2.0, 2.0),
}


def normalize_country(value: str) -> str:
    """Extract and normalize the first listed production country."""
    return first_listed_value(value)


def lookup_country(normalized: str) -> tuple[float, float, int, str] | None:
    """Look up a country in the database. Try exact match first, then substring."""
    if not normalized:
        return None
    # Exact match
    if normalized in COUNTRY_DB:
        return COUNTRY_DB[normalized]
    # Try with english suffix pattern: "印度 india" -> "india"
    parts = normalized.split()
    if len(parts) >= 2:
        # Try last word (often English name)
        last = parts[-1]
        if last in COUNTRY_DB:
            return COUNTRY_DB[last]
        # Try first word
        first = parts[0]
        if first in COUNTRY_DB:
            return COUNTRY_DB[first]
    # Substring match: check if any key is contained in the text
    for key, value in COUNTRY_DB.items():
        if key in normalized:
            return value
    return None


def build_enrichment() -> None:
    frame = pd.read_csv(
        DERIVED_MOVIES_INFO,
        usecols=["movie_id", "制片国家/地区", "Region_Code"],
        dtype={"movie_id": "string"},
    )
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    if len(frame) != manifest["publication_records"]:
        raise ValueError(
            f"Derived dataset ({len(frame)}) and manifest "
            f"({manifest['publication_records']}) disagree"
        )

    lats: list[float] = []
    lngs: list[float] = []
    geo_regions: list[int] = []
    countries: list[str] = []
    dlngs: list[float] = []
    dlats: list[float] = []
    unmapped: dict[str, int] = {}
    unmapped_total = 0

    for _, row in frame.iterrows():
        raw = row["制片国家/地区"]
        region_code = int(row["Region_Code"])
        normalized = normalize_country(raw)
        result = lookup_country(normalized)

        if result is not None:
            lat, lng, geo_region, display = result
            lats.append(round(lat, 1))
            lngs.append(round(lng, 1))
            geo_regions.append(geo_region)
            countries.append(display)
            # Look up geographic spread for this country
            spread = COUNTRY_SPREADS.get(display, (1.5, 1.5))
            dlngs.append(spread[0])
            dlats.append(spread[1])
        else:
            # Fallback: use existing Region_Code centroid
            fallback = {
                0: (39.0, -98.0, 0, "North_America"),
                1: (50.0, 10.0, 1, "Europe"),
                2: (36.0, 130.0, 2, "East_Asia"),
                3: (35.0, 105.0, 3, "China"),
            }
            fb = fallback.get(region_code, (0.0, 0.0, region_code, "Unknown"))
            lats.append(fb[0])
            lngs.append(fb[1])
            geo_regions.append(fb[2])
            countries.append(fb[3])
            dlngs.append(1.5)
            dlats.append(1.5)
            key = normalized or f"(empty/region={region_code})"
            unmapped[key] = unmapped.get(key, 0) + 1
            unmapped_total += 1

    # Build compact columnar payload
    payload = {
        "meta": {
            "schemaVersion": 1,
            "recordCount": len(frame),
            "sampleFingerprint": manifest["sample_fingerprint_sha256"],
            "unmappedCount": unmapped_total,
            "unmappedTop": dict(
                sorted(unmapped.items(), key=lambda x: -x[1])[:20]
            ),
            "geoRegionLabels": GEO_REGION_LABELS,
        },
        "columns": ["lat", "lng", "geoRegion", "country", "dlng", "dlat"],
        "records": [
            [lats[i], lngs[i], geo_regions[i], countries[i], dlngs[i], dlats[i]]
            for i in range(len(frame))
        ],
    }

    output_path = GEO_ENRICHMENT
    atomic_write_text(
        output_path,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )

    coverage = (len(frame) - unmapped_total) / len(frame) * 100
    print(f"Geo enrichment: {len(frame):,} records")
    print(f"  Mapped: {len(frame) - unmapped_total:,} ({coverage:.1f}%)")
    print(f"  Unmapped: {unmapped_total:,}")
    print(f"  Output: {output_path}")
    if unmapped:
        print(f"  Top unmapped:")
        for key, count in sorted(unmapped.items(), key=lambda x: -x[1])[:10]:
            print(f"    {key:35s} {count:>5}")

    # Also print geo_region distribution
    from collections import Counter
    dist = Counter(geo_regions)
    print(f"  Geo region distribution:")
    for code in sorted(dist):
        label = GEO_REGION_LABELS.get(code, f"code_{code}")
        print(f"    {code:2d} {label:20s} {dist[code]:>6}")


if __name__ == "__main__":
    build_enrichment()
