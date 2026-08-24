"""Extract films where a foreign language is the first/primary language."""
import csv
import re
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DERIVED_MOVIES_INFO
from dialect_defs import (
    DIALECT_MARKERS_STRICT, MANDARIN_MARKERS, MINORITY_MARKERS,
    SIGN_MARKERS, FOREIGN_MARKERS,
)

CSV_PATH = str(DERIVED_MOVIES_INFO)
BASE = Path(__file__).resolve().parents[1]

# “中国语言” = 方言 + 普通话 + 少数民族 + 手语
_CHINESE_MARKERS = DIALECT_MARKERS_STRICT + list(MANDARIN_MARKERS) + list(MINORITY_MARKERS) + list(SIGN_MARKERS)


def normalize_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def contains_any(text, markers):
    return any(marker in text for marker in markers)


def language_parts(value):
    text = normalize_text(value)
    if not text:
        return []
    return [p.strip() for p in re.split(r"\s*(?:/|\||;|;|,)\s*", text) if p.strip()]


def is_chinese_lang(lang_text):
    return contains_any(lang_text, _CHINESE_MARKERS)


def is_foreign_lang(lang_text):
    return contains_any(lang_text, FOREIGN_MARKERS)


def main():
    results = []
    total_rows = 0
    foreign_by_category = {}

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            lang_raw = row.get("\u8bed\u8a00", "") or row.get("语言", "")
            parts = language_parts(lang_raw)
            if not parts:
                continue

            first_lang = parts[0]

            # Skip silent/no-dialogue films
            if first_lang in ("无声", "无对白", "silence", "silent", "无", ""):
                continue

            first_is_chinese = is_chinese_lang(first_lang)
            first_is_foreign = is_foreign_lang(first_lang)

            # We want: first language is foreign AND not Chinese
            if first_is_foreign and not first_is_chinese:
                region = row.get("Region", "")
                results.append({
                    "片名": row.get("片名", ""),
                    "年份": row.get("年份", ""),
                    "语言": lang_raw,
                    "第一语言": first_lang,
                    "导演": row.get("导演", ""),
                    "类型": row.get("类型", ""),
                    "制片国家/地区": row.get("制片国家/地区", ""),
                    "豆瓣评分": row.get("豆瓣评分", ""),
                    "评价人数": row.get("评价人数", ""),
                    "剧情简介": row.get("剧情简介", ""),
                    "Gemini评价": row.get("Gemini评价", ""),
                    "Region": region,
                    "Language_Category": row.get("Language_Category", ""),
                    "Decade": row.get("Decade", ""),
                    "Is_Dialect": row.get("Is_Dialect", ""),
                    "来源URL": row.get("来源URL", ""),
                })
                foreign_by_category[region] = foreign_by_category.get(region, 0) + 1

    print(f"Total rows in CSV: {total_rows}")
    print(f"Foreign-first-language films found: {len(results)}")
    print(f"By region: {foreign_by_category}")
    print()

    # Print summary stats
    from collections import Counter
    lang_counter = Counter(r["第一语言"] for r in results)
    print("Top 30 first languages:")
    for lang, count in lang_counter.most_common(30):
        print(f"  {lang}: {count}")
    print()

    # Print first 30 films as preview
    for i, r in enumerate(results[:30]):
        print(f"--- {i+1} ---")
        print(f"  片名: {r['片名']}")
        print(f"  年份: {r['年份']}")
        print(f"  语言: {r['语言']}  (第一语言: {r['第一语言']})")
        print(f"  导演: {r['导演']}")
        print(f"  类型: {r['类型']}")
        print(f"  制片: {r['制片国家/地区']}")
        print(f"  评分: {r['豆瓣评分']} (评价人数: {r['评价人数']})")
        print(f"  Region: {r['Region']} | Decade: {r['Decade']}")
        brief = r['剧情简介'][:100] if r['剧情简介'] else ""
        print(f"  简介: {brief}{'...' if len(r['剧情简介']) > 100 else ''}")
        print()

    # Save to JSON
    out_path = BASE / "data" / "foreign_first_language_films.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nFull list saved to: {out_path}")
    print(f"Total records: {len(results)}")


if __name__ == "__main__":
    main()
