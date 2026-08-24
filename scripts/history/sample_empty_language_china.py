# -*- coding: utf-8 -*-
"""84 部 China 空语言影片抽样复核（10 部，seed=42）。

从 derived_movies.csv 提取 Region=China 且语言字段为空的 84 部影片，
按 seed=42 随机抽 10 部，输出复核清单 CSV。

输出：data/empty_language_china_sample10.csv
"""

import csv
import os
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "cleaned", "derived_movies.csv")
OUT_PATH = os.path.join(PROJECT_ROOT, "data", "empty_language_china_sample10.csv")


def main():
    empty_lang_rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row.get("语言", "").strip()
            region = row.get("Region", "").strip()
            if region == "China" and not lang:
                empty_lang_rows.append(row)

    print(f"China 空语言影片总数: {len(empty_lang_rows)}")

    # 按 seed=42 随机抽 10 部
    rng = random.Random(42)
    sample = rng.sample(empty_lang_rows, min(10, len(empty_lang_rows)))

    # 输出复核清单
    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "movie_id", "片名", "年份", "Region", "豆瓣评分", "评价人数",
            "导演", "类型", "语言", "豆瓣页面",
            "复核结果", "复核备注",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(sample, 1):
            writer.writerow({
                "movie_id": row.get("movie_id", ""),
                "片名": row.get("片名", ""),
                "年份": row.get("年份", ""),
                "Region": row.get("Region", ""),
                "豆瓣评分": row.get("豆瓣评分", ""),
                "评价人数": row.get("评价人数", ""),
                "导演": row.get("导演", ""),
                "类型": row.get("类型", ""),
                "语言": row.get("语言", ""),
                "豆瓣页面": f"https://movie.douban.com/subject/{row.get('movie_id', '')}/",
                "复核结果": "",  # 待人工填写
                "复核备注": "",  # 待人工填写
            })

    print(f"抽样清单已写入 {OUT_PATH}")
    print(f"\n抽样 10 部明细：")
    for i, row in enumerate(sample, 1):
        print(f"  {i}. {row.get('片名', '')}({row.get('年份', '')}) "
              f"ID={row.get('movie_id', '')} 评分={row.get('豆瓣评分', '')} "
              f"导演={row.get('导演', '')}")


if __name__ == "__main__":
    main()
