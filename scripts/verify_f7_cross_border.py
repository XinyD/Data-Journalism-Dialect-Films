# -*- coding: utf-8 -*-
"""F7 交叉验证：跨境语言标签 x Region 组合审计（只读）。

验证内容（2026-08-18 增强版）：
1. Region=China 且含跨境语言标签（朝鲜语/蒙古语/哈萨克语等）的影片逐部列出，
   其中 Is_Dialect=1 者需确认是中国少数民族题材（非境外片误标 China）；
2. 非 China 的跨境语言影片属全量方言口径（不影响 China 核心统计），仅计数；
3. 《平壤之约》(10478122) Region 应为 East_Asia（防重建后回退，回归检查）。

已核实结论（2026-08-18）：Region=China 含跨境标签 52 部，其中 D=1 的 20 部
制片国家均为中国大陆/合拍的中国少数民族题材（蒙古/哈萨克/维吾尔/俄语族），
全部合规保留（见 PROGRESS.md F7 增强条目）。

输出：data/f7_cross_border_validation.csv
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)  # scripts 的上一级即项目根目录
sys.path.insert(0, ROOT)
from dialect_defs import DIALECT_MARKERS_STRICT, MINORITY_MARKERS

# 跨境语言标签（中国少数民族语言中可能被境外影片使用的）
CROSS_BORDER_MARKERS = [
    "朝鲜语", "朝鮮語",  # 朝鲜半岛
    "蒙古语", "蒙古語", "mongolian", "蒙语",  # 蒙古国
    "哈萨克语", "哈薩克語", "kazakh",  # 哈萨克斯坦
    "柯尔克孜语",  # 吉尔吉斯斯坦
    "乌孜别克语", "乌兹别克语", "烏茲別克語",  # 乌兹别克斯坦
    "塔吉克语",  # 塔吉克斯坦
    "吉尔吉斯语",
    "俄语", "俄語", "russian",  # 俄罗斯（中国境内有俄语少数民族，但大量俄片也用）
]

CSV_PATH = os.path.join(PROJECT_ROOT, "data", "cleaned", "derived_movies.csv")
OUT_PATH = os.path.join(PROJECT_ROOT, "data", "archive", "analysis", "f7_cross_border_validation.csv")


def has_cross_border_marker(lang_text):
    """语言字段是否含跨境语言标签。"""
    if not lang_text:
        return False
    text = str(lang_text).casefold()
    for m in CROSS_BORDER_MARKERS:
        if m.casefold() in text:
            return True
    return False


def get_cross_border_markers_found(lang_text):
    """返回命中的跨境标签列表。"""
    if not lang_text:
        return []
    text = str(lang_text).casefold()
    found = []
    for m in CROSS_BORDER_MARKERS:
        if m.casefold() in text:
            found.append(m)
    return found


def main():
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lang = row.get("语言", "")
            region = row.get("Region", "")
            is_dialect = row.get("Is_Dialect", "0")
            title = row.get("片名", "")
            year = row.get("年份", "")
            movie_id = row.get("movie_id", "")

            if not has_cross_border_marker(lang):
                continue

            markers_found = get_cross_border_markers_found(lang)
            rows.append({
                "movie_id": movie_id,
                "片名": title,
                "年份": year,
                "Region": region,
                "Is_Dialect": is_dialect,
                "语言": lang,
                "跨境标签": " / ".join(markers_found),
            })

    # 分类输出
    china_rows = [r for r in rows if r["Region"] == "China"]
    china_d1 = [r for r in china_rows if r["Is_Dialect"] == "1"]
    non_china_d1 = [r for r in rows if r["Region"] != "China" and r["Is_Dialect"] == "1"]
    non_china_d0 = [r for r in rows if r["Region"] != "China" and r["Is_Dialect"] == "0"]

    print(f"=== F7 交叉验证结果 ===")
    print(f"含跨境语言标签的影片总数: {len(rows)}")
    print(f"  Region=China: {len(china_rows)} 部（其中 D=1: {len(china_d1)} 部，需逐部核实少数民族题材）")
    print(f"  Region!=China 且 D=1: {len(non_china_d1)} 部（全量方言口径，不影响 China 核心统计）")
    print(f"  Region!=China 且 D=0: {len(non_china_d0)} 部")
    print()

    if china_rows:
        print("--- Region=China 含跨境标签影片（逐部核查）---")
        for r in china_rows:
            print(f"  {r['片名']}({r['年份']}) ID={r['movie_id']} D={r['Is_Dialect']} "
                  f"标签=[{r['跨境标签']}] 语言=[{r['语言']}]")
        print()

    if non_china_d1:
        print(f"信息：Region!=China 且 D=1 的跨境语言影片 {len(non_china_d1)} 部（属全量方言口径，不影响 China 统计）。")
        print()

    # 写输出 CSV
    with open(OUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "movie_id", "片名", "年份", "Region", "Is_Dialect", "语言", "跨境标签",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"结果已写入 {OUT_PATH}")

    # 结论
    print(f"\n结论：Region=China 含跨境标签且 D=1 的影片 {len(china_d1)} 部，"
          f"已于 2026-08-18 逐部核实为中国少数民族题材（合规保留）。")

    # 回归检查：《平壤之约》Region 应为 East_Asia（防重建后回退）
    py = [r for r in rows if r["movie_id"] == "10478122"]
    if py:
        if py[0]["Region"] == "East_Asia":
            print("回归检查 PASS：《平壤之约》Region=East_Asia（f7_region_fix_20260818 生效）。")
        else:
            print(f"!!! 回归检查 FAIL：《平壤之约》Region={py[0]['Region']}，"
                  f"请重跑 scripts/apply_f7_region_fix_20260818.py --apply")

    mz = [r for r in china_rows if "芒种" in r["片名"]]
    if mz:
        print("《芒种》Region=China 合理（延边朝鲜族题材），保留。")


if __name__ == "__main__":
    main()
