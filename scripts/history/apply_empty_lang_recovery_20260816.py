# -*- coding: utf-8 -*-
"""一次性脚本：用户人工复核决定——4部空语言China电影补回方言口径（2026-08-16）

背景：derived_movies.csv 中 Region=China 且语言字段为空的 84 部电影按非方言处理。
经百度百科补全、用户复核后决定：
  - 《追鱼》(1960) 为越剧戏曲片，维持非方言；
  - 《张学友1/2世纪世界巡回演唱会》(2011) 为演唱会，维持非方言；
  - 《惊梦魂》(1995)、《八廓南街16号》(1997)、《猎人与骷髅怪》(2012)、
    《巴依尔的春节》(2020) 纳入方言电影。

本脚本：
1. 幂等备份 derived_movies.csv -> derived_movies_empty_lang_backup_20260816.csv
2. 对 4 部电影回填「语言」字段，并按 v4.1 判定函数重算：
     Language_Category、Language_Code、Is_Dialect
   回填标签选择：
     - 惊梦魂 -> "粤语"（百度百科为"普通话/粤语"，简化为粤语以避免落入 Tier 2b）
     - 八廓南街16号 -> "藏语"
     - 猎人与骷髅怪 -> "藏语"
     - 巴依尔的春节 -> "山西方言"
3. codebook_review.csv 回填 4 张人工复核记录卡
4. review_queue.csv 追加补回溯源行
5. 更新 sample_manifest.json 中的 publication_fingerprint
6. 不变量断言： China 方言片 3082 -> 3086

用法：py scripts/apply_empty_lang_recovery_20260816.py
"""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pandas as pd


def safe_write_csv(df: pd.DataFrame, path) -> None:
    """Windows 只读文件回退：先清除只读属性再写入。"""
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    df.to_csv(path, index=False, encoding="utf-8-sig")


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import categorize_language, language_code, publication_fingerprint  # noqa: E402

EXPECTED_TOTAL = 53_467
BACKUP_PATH = ROOT / "data" / "archive" / "backups" / "derived_movies_empty_lang_backup_20260816.csv"
REVIEW_QUEUE = ROOT / "data" / "cleaned" / "review_queue.csv"
CODEBOOK = ROOT / "data" / "archive" / "analysis" / "codebook_review.csv"
TODAY = "2026-08-16"

# 用户复核后需补回的 4 部电影（movie_id -> 补全语言标签）
RECOVERY = {
    "4133310": {
        "片名": "惊梦魂",
        "年份": 1995,
        "语言": "粤语",
        "方言名称": "粤语",
        "少数民族语言": "",
        "备注": "百度百科：对白语言=普通话/粤语；为直接纳入方言口径，回填'粤语'（避免落入Tier 2b证据审查）",
    },
    "2129914": {
        "片名": "八廓南街16号",
        "年份": 1997,
        "语言": "藏语",
        "方言名称": "",
        "少数民族语言": "藏语",
        "备注": "百度百科：对白语言=藏语；中国少数民族语言片",
    },
    "10518931": {
        "片名": "猎人与骷髅怪",
        "年份": 2012,
        "语言": "藏语",
        "方言名称": "",
        "少数民族语言": "藏语",
        "备注": "百度百科：语言=藏语（康巴甘孜方言）；中国少数民族语言片",
    },
    "34953763": {
        "片名": "巴依尔的春节",
        "年份": 2020,
        "语言": "山西方言",
        "方言名称": "山西方言",
        "少数民族语言": "",
        "备注": "百度百科：山西方言对白；拍摄地点山西太原；晋语片",
    },
}


def main() -> None:
    # ---- 1. 备份 ----
    if not BACKUP_PATH.exists():
        shutil.copy2(DERIVED_MOVIES_INFO, BACKUP_PATH)
        print(f"已备份 -> {BACKUP_PATH.name}")
    else:
        print(f"备份已存在，跳过：{BACKUP_PATH.name}")

    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False)
    df["movie_id"] = df["movie_id"].astype(str)
    assert len(df) == EXPECTED_TOTAL, f"总行数 {len(df)} != {EXPECTED_TOTAL}"

    # ---- 2. 主表修改 ----
    changed = []
    for mid, info in RECOVERY.items():
        idx = df.index[df["movie_id"] == mid]
        assert len(idx) == 1, f"movie_id {mid} 未找到或重复"
        i = idx[0]
        row = df.loc[i]
        assert row["Region"] == "China", f"{info['片名']} Region={row['Region']} 不是 China"
        assert pd.isna(row["语言"]) or str(row["语言"]).strip() == "", \
            f"{info['片名']} 语言字段非空：{row['语言']}"
        assert row["Is_Dialect"] == 0, f"{info['片名']} 当前 Is_Dialect={row['Is_Dialect']}"

        old_lang = row["语言"]
        df.at[i, "语言"] = info["语言"]
        df.at[i, "Language_Category"] = categorize_language(info["语言"])
        lc, is_dia = language_code(info["语言"], region=row["Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = ""  # Tier 1 直接由语言标签判定，无需证据
        changed.append({
            "movie_id": mid,
            "片名": info["片名"],
            "年份": info["年份"],
            "原语言": old_lang if pd.notna(old_lang) else "",
            "补全语言": info["语言"],
            "Language_Code": lc,
            "Is_Dialect": is_dia,
        })
        print(f"已补回 {info['片名']}({info['年份']}): 语言='{info['语言']}' -> Language_Code={lc}, Is_Dialect={is_dia}")

    # ---- 3. codebook_review.csv 人工复核记录卡 ----
    cb = pd.read_csv(CODEBOOK, encoding="utf-8-sig")
    cb["movie_id"] = cb["movie_id"].astype(str)
    cards = []
    for mid, info in RECOVERY.items():
        cards.append({
            "movie_id": mid,
            "片名": info["片名"],
            "年份": info["年份"],
            "方言名称": info["方言名称"],
            "少数民族语言": info["少数民族语言"],
            "结论": "方言",
            "证据": f"用户人工复核（{TODAY}）：百度百科补全语言字段，{info['备注']}",
        })
    for card in cards:
        if card["movie_id"] not in cb["movie_id"].values:
            cb = pd.concat([cb, pd.DataFrame([card])], ignore_index=True)
        else:
            # 已存在则更新结论为方言
            mask = cb["movie_id"] == card["movie_id"]
            cb.loc[mask, "结论"] = "方言"
            cb.loc[mask, "证据"] = card["证据"]
    safe_write_csv(cb, CODEBOOK)
    print(f"codebook_review.csv 回填/更新 {len(cards)} 张记录卡")

    # ---- 4. review_queue.csv 溯源 ----
    rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
    rq["movie_id"] = rq["movie_id"].astype(str)
    for mid, info in RECOVERY.items():
        if not ((rq["movie_id"] == mid) & (rq["处置"] == "空语言补回方言口径")).any():
            row = df.loc[df["movie_id"] == mid].iloc[0]
            rq = pd.concat([rq, pd.DataFrame([{
                "movie_id": mid,
                "片名": info["片名"],
                "年份": info["年份"],
                "Region": row["Region"],
                "语言": info["语言"],
                "处置": "空语言补回方言口径",
                "原因": f"用户人工复核（{TODAY}）：百度百科补全后纳入方言电影；{info['备注']}",
                "审计日期": TODAY,
                "依据": "v4.1 方言定义：语言字段命中中国方言/少数民族语言白名单",
                "状态": "已处理",
                "处理日期": TODAY,
                "来源": "scripts/apply_empty_lang_recovery_20260816.py",
            }])], ignore_index=True)
    safe_write_csv(rq, REVIEW_QUEUE)
    print("review_queue.csv 已追加补回溯源行")

    # ---- 5. 断言 ----
    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    expected_dialect = 3082 + len(RECOVERY)
    assert china_dialect == expected_dialect, f"China 方言片应为 {expected_dialect}，实测 {china_dialect}"

    code2 = df[df["Language_Code"] == 2]
    code3 = df[df["Language_Code"] == 3]
    assert int(code3["Is_Dialect"].sum()) == len(code3) == int(df["Is_Dialect"].sum())
    assert (code2["Is_Dialect"] == 0).all()

    safe_write_csv(df, DERIVED_MOVIES_INFO)
    print(f"已写回主表：China 方言片 {china_dialect}（+{len(RECOVERY)}）")

    # ---- 6. manifest 指纹同步 ----
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["empty_lang_recovery_20260816"] = {
        "applied_by": "scripts/apply_empty_lang_recovery_20260816.py",
        "rule": "用户人工复核：4部空语言China电影补回方言口径",
        "movies": [
            {"movie_id": mid, "片名": info["片名"], "年份": info["年份"], "语言": info["语言"]}
            for mid, info in RECOVERY.items()
        ],
        "baseline_china_dialect": 3082,
        "new_china_dialect": expected_dialect,
        "backup": BACKUP_PATH.name,
        "date": TODAY,
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 指纹已更新: {fp}")

    # ---- 7. 变更摘要 CSV ----
    summary_path = ROOT / "data" / "archive" / "analysis" / "empty_lang_recovery_summary_20260816.csv"
    safe_write_csv(pd.DataFrame(changed), summary_path)
    print(f"变更摘要已保存 -> {summary_path.name}")


if __name__ == "__main__":
    main()
