# -*- coding: utf-8 -*-
"""生成戏曲/演唱会类方言片排除候选清单（2026-08-18 审计，只读分析）。

背景：v4.1 定义 E4 条款排除戏曲声腔，但 OPERA_MARKERS 从未在判定逻辑中
使用，导致约 10 部戏曲片 + 20 余部演唱会/音乐纪录片被判为方言片。
本脚本生成候选清单供人工复核，不修改任何数据。

候选信号（仅针对 Is_Dialect=1 的影片）：
  R1 类型字段含"戏曲"            → 候选原因=戏曲片
  R2 片名含"演唱会/音乐会"       → 候选原因=演唱会
  R3 类型含"音乐"且不含叙事类型（剧情/喜剧/爱情等）→ 候选原因=音乐纪录片/演唱会
  R3b 类型含"音乐"+叙事类型      → 默认保留（音乐题材叙事片，供复核）
  R4 片名含"颁奖"                → 候选原因=颁奖礼
  R5 已知戏曲片人工补充（豆瓣类型未标"戏曲"的粤剧经典等）

默认建议规则：
  - 命中候选信号 → 排除
  - 特例保留：《川剧往事》（片名含剧种但类型为剧情的叙事电影）
"""
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DERIVED_MOVIES_INFO  # noqa: E402

OUT_CSV = ROOT / "data" / "archive" / "analysis" / "opera_concert_exclude_candidates_20260818.csv"
REPORT_TXT = ROOT / "_opera_concert_candidates_report.txt"

# 已知戏曲片人工补充：豆瓣"类型"未标戏曲、但实为戏曲影片（粤剧经典等）
KNOWN_OPERA_IDS = {
    "4047730": "粤剧经典《蝶影红梨记》(1959)，豆瓣类型误标为歌舞/爱情",
}

# 片名含剧种关键词但实为剧情叙事片的特例（建议保留）
KEEP_SPECIAL = {
    "25922880": "《川剧往事》(2014)：片名含剧种但类型为剧情，对白为四川话的叙事电影",
}

# 弱信号：片名含剧种名但类型未标戏曲（默认保留，供人工复核）
TITLE_OPERA_KW = ["京剧", "越剧", "黄梅戏", "豫剧", "昆曲", "川剧", "粤剧",
                  "秦腔", "评剧", "沪剧", "歌仔戏", "曲剧", "花鼓戏"]

# 类型无"音乐"标签但实为音乐纪录片/演唱会的补充
KNOWN_CONCERT_IDS = {
    "3642305": "《歌舞升平》(2008)：类型仅标纪录片，实为音乐纪录片",
}

# 叙事类型：类型含"音乐"但同时含以下任一类型时视为音乐题材叙事片（默认保留）
NARRATIVE_GENRES = ["剧情", "喜", "爱情", "家庭", "奇幻", "悬疑", "犯罪",
                    "动作", "科幻", "恐怖", "短片", "儿童", "冒险"]


def main():
    # 控制台中文输出重定向到文件，避免终端编码乱码
    report = io.StringIO()

    with open(DERIVED_MOVIES_INFO, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    dialect = [r for r in rows if r.get("Is_Dialect") == "1"]
    report.write(f"derived_movies.csv 总行数: {len(rows)}\n")
    report.write(f"Is_Dialect=1 总数: {len(dialect)}\n\n")

    candidates = {}  # movie_id -> dict

    def add(row, reason):
        mid = row["movie_id"]
        if mid in candidates:
            candidates[mid]["候选原因"] += "；" + reason
        else:
            candidates[mid] = {
                "movie_id": mid,
                "片名": row.get("片名", ""),
                "年份": row.get("年份", ""),
                "豆瓣评分": row.get("豆瓣评分", ""),
                "语言": row.get("语言", ""),
                "类型": row.get("类型", ""),
                "Region": row.get("Region", ""),
                "候选原因": reason,
                "默认建议": "排除",
                "备注": "",
            }

    for r in dialect:
        genre = r.get("类型", "") or ""
        name = r.get("片名", "") or ""
        mid = r["movie_id"]
        if "戏曲" in genre:
            add(r, "戏曲片（类型含戏曲）")
        if "演唱会" in name or "音乐会" in name:
            add(r, "演唱会（片名）")
        if "音乐" in genre:
            if any(ng in genre for ng in NARRATIVE_GENRES):
                # 音乐题材叙事片：默认保留待复核
                if mid not in candidates:
                    add(r, "音乐题材叙事片（类型含音乐+叙事类型）")
                    candidates[mid]["默认建议"] = "保留"
                    candidates[mid]["备注"] = "含叙事类型，对白为方言的剧情片，建议保留"
            else:
                add(r, "音乐类型（纪录片/演唱会）")
        if "颁奖" in name:
            add(r, "颁奖礼（片名）")
        if mid in KNOWN_OPERA_IDS:
            add(r, "已知戏曲片：" + KNOWN_OPERA_IDS[mid])
        if mid in KNOWN_CONCERT_IDS:
            add(r, "已知音乐纪录片：" + KNOWN_CONCERT_IDS[mid])
        # 弱信号：片名含剧种名但未被强信号命中（类型未标戏曲）→ 默认保留待复核
        if mid not in candidates and any(k in name for k in TITLE_OPERA_KW):
            add(r, "片名含剧种名（弱信号，类型未标戏曲）")
            candidates[mid]["默认建议"] = "保留"
            candidates[mid]["备注"] = "片名含剧种名但类型为" + (genre or "无") + "，需人工判断是否叙事片"

    # 特例覆盖为保留
    for mid, note in KEEP_SPECIAL.items():
        if mid in candidates:
            candidates[mid]["默认建议"] = "保留"
            candidates[mid]["备注"] = note

    items = sorted(
        candidates.values(),
        key=lambda x: (x["默认建议"], x["候选原因"], x["年份"], x["片名"]),
    )

    exclude_n = sum(1 for x in items if x["默认建议"] == "排除")
    keep_n = sum(1 for x in items if x["默认建议"] == "保留")
    report.write(f"候选总数: {len(items)} 部（默认排除 {exclude_n}，建议保留 {keep_n}）\n\n")

    report.write("=== 默认建议：排除 ===\n")
    for x in items:
        if x["默认建议"] != "排除":
            continue
        report.write(
            f'  id={x["movie_id"]:>10s} {x["片名"][:30]:32s} ({x["年份"]}) '
            f'分{x["豆瓣评分"]:>4s} 类型={x["类型"]} 原因={x["候选原因"]}\n'
            f'             语言="{x["语言"]}" Region={x["Region"]}\n'
        )

    report.write("\n=== 默认建议：保留（片名含戏曲/音乐信号但为叙事片） ===\n")
    for x in items:
        if x["默认建议"] != "保留":
            continue
        report.write(
            f'  id={x["movie_id"]:>10s} {x["片名"][:30]:32s} ({x["年份"]}) '
            f'类型={x["类型"]} 备注={x["备注"]}\n'
        )

    # 输出 CSV（utf-8-sig 便于 Excel 打开）
    fieldnames = ["movie_id", "片名", "年份", "豆瓣评分", "语言", "类型",
                  "Region", "候选原因", "默认建议", "备注"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(items)

    report.write(f"\n候选清单已写入: {OUT_CSV}\n")

    text = report.getvalue()
    REPORT_TXT.write_text(text, encoding="utf-8")
    print(f"OK: {len(items)} candidates, exclude={exclude_n}, keep={keep_n}")
    print(f"CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
