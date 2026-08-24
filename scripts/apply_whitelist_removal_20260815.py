# -*- coding: utf-8 -*-
"""一次性脚本：用户人工复核决定——《芒种》(1986783) 移出 Tier 2b 白名单（2026-08-15）

背景：v4.1 Tier 2b 证据审查中《芒种》经 LLM_JUDGE（conf=0.85）补回白名单。
用户复核全部 3 部现存含「朝鲜」标签影片后决定：三部均不算方言片。
《惊变28周》(1306421) 与《平壤之约》(10478122) 本已排除，无需改动；
实际变更为将《芒种》移出白名单。

本脚本：
1. 幂等备份 derived_movies.csv -> derived_movies_v41_removal_backup_20260815.csv
2. codebook_review.csv 回填 3 部影片的人工复核记录卡（结论均为非方言）
3. review_queue.csv 追加《芒种》移出白名单溯源行
4. derived_movies.csv：1986783 置 Is_Dialect=0、Language_Code=2、
   Dialect_Evidence=TIER2B_EXCLUDED；tier2b_recovered.csv 删除该行
5. 不变量断言 + 基线断言 (3082, 2309, 425, 348)
6. 重算 publication_fingerprint，更新 sample_manifest.json 与 README.md

用法：py scripts/apply_whitelist_removal_20260815.py
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
from data_processor import publication_fingerprint  # noqa: E402

MOVIE_ID = "1986783"
EXPECTED_TOTAL = 53_467
BACKUP_PATH = ROOT / "data" / "derived_movies_v41_removal_backup_20260815.csv"
RECOVERED_CSV = ROOT / "data" / "tier2b_recovered.csv"
REVIEW_QUEUE = ROOT / "data" / "review_queue.csv"
CODEBOOK = ROOT / "data" / "codebook_review.csv"
OLD_FP = "f6114f938b0a1215dbad35aee6738709ff886d729a5c37bab460d11d504c7ceb"
TODAY = "2026-08-15"


def main() -> None:
    skip_codebook = "--skip-codebook" in sys.argv
    # ---- 1. 备份 ----
    if not BACKUP_PATH.exists():
        shutil.copy2(DERIVED_MOVIES_INFO, BACKUP_PATH)
        print(f"已备份 -> {BACKUP_PATH.name}")
    else:
        print(f"备份已存在，跳过：{BACKUP_PATH.name}")

    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig")
    df["movie_id"] = df["movie_id"].astype(str)
    assert len(df) == EXPECTED_TOTAL

    # ---- 2. codebook_review.csv 人工复核记录卡 ----
    cb = pd.read_csv(CODEBOOK, encoding="utf-8-sig")
    cards = [
        {"movie_id": "1986783", "片名": "芒种", "年份": 2006,
         "方言名称": "", "少数民族语言": "",
         "结论": "非方言", "证据": "用户人工复核（2026-08-15）：朝鲜语题材片，不算方言片，移出 Tier 2b 白名单"},
        {"movie_id": "10478122", "片名": "平壤之约", "年份": 2012,
         "方言名称": "", "少数民族语言": "",
         "结论": "非方言", "证据": "用户人工复核（2026-08-15）确认维持排除（中朝合拍，普通话主导）"},
        {"movie_id": "1306421", "片名": "惊变28周", "年份": 2002,
         "方言名称": "", "少数民族语言": "",
         "结论": "非方言", "证据": "用户人工复核（2026-08-15）确认维持排除（外语片，朝鲜手语）"},
    ]
    for card in cards:
        if card["movie_id"] not in cb["movie_id"].astype(str).values:
            cb = pd.concat([cb, pd.DataFrame([card])], ignore_index=True)
    if skip_codebook:
        pending = ROOT / "data" / "codebook_review_pending_append.csv"
        safe_write_csv(cb, pending)
        print(f"⚠ codebook_review.csv 被占用，记录卡已暂存 -> {pending.name}，释放后带 --apply-codebook 重跑")
    else:
        try:
            safe_write_csv(cb, CODEBOOK)
            print(f"codebook_review.csv 回填 {len(cards)} 张记录卡")
        except PermissionError:
            pending = ROOT / "data" / "codebook_review_pending_append.csv"
            safe_write_csv(cb, pending)
            print(f"⚠ codebook_review.csv 被其他程序占用，记录卡已暂存 -> {pending.name}，释放后带 --apply-codebook 重跑")

    # ---- 3. review_queue.csv 溯源 ----
    rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
    rq["movie_id"] = rq["movie_id"].astype(str)
    row = df.loc[df["movie_id"] == MOVIE_ID].iloc[0]
    if not ((rq["movie_id"] == MOVIE_ID) & (rq["处置"] == "移出tier2b白名单")).any():
        rq = pd.concat([rq, pd.DataFrame([{
            "movie_id": MOVIE_ID, "片名": row["片名"], "年份": row["年份"],
            "Region": row["Region"], "语言": row["语言"],
            "处置": "移出tier2b白名单",
            "原因": "用户人工复核（2026-08-15）：《芒种》不算方言片，推翻 LLM_JUDGE(conf=0.85) 补判",
            "审计日期": TODAY,
            "依据": "v4.1 白名单增删流程（Codebook §8）：人工听辨结论与白名单冲突走记录卡回填",
            "状态": "已处理", "处理日期": TODAY,
            "来源": "scripts/apply_whitelist_removal_20260815.py",
        }])], ignore_index=True)
        safe_write_csv(rq, REVIEW_QUEUE)
        print("review_queue.csv 已追加移出记录")

    # ---- 4. 主表 + 白名单修改 ----
    idx = df.index[df["movie_id"] == MOVIE_ID]
    assert len(idx) == 1, f"movie_id {MOVIE_ID} 未找到或重复"
    i = idx[0]
    assert df.at[i, "Is_Dialect"] == 1 and df.at[i, "Dialect_Evidence"] == "LLM_JUDGE", \
        f"《芒种》当前状态异常：{df.at[i, 'Is_Dialect']} / {df.at[i, 'Dialect_Evidence']}"
    df.at[i, "Is_Dialect"] = 0
    df.at[i, "Language_Code"] = 2
    df.at[i, "Dialect_Evidence"] = "TIER2B_EXCLUDED"

    rec = pd.read_csv(RECOVERED_CSV, encoding="utf-8-sig")
    rec["movie_id"] = rec["movie_id"].astype(str)
    before = len(rec)
    rec = rec[rec["movie_id"] != MOVIE_ID]
    assert len(rec) == before - 1, "白名单中未找到《芒种》"
    safe_write_csv(rec, RECOVERED_CSV)
    print(f"tier2b_recovered.csv：{before} -> {len(rec)}")

    # ---- 5. 断言 ----
    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    assert china_dialect == 3082, f"China 方言片应为 3082，实测 {china_dialect}"
    t2b_kept = int(((china["Is_Dialect"] == 1)
                    & china["Dialect_Evidence"].fillna("").str.contains(
                        "E:|BENCHMARK|LLM_JUDGE", regex=True)).sum())
    assert t2b_kept == 348, f"Tier 2b 保留应为 348，实测 {t2b_kept}"
    code2 = df[df["Language_Code"] == 2]
    code3 = df[df["Language_Code"] == 3]
    assert int(code3["Is_Dialect"].sum()) == len(code3) == int(df["Is_Dialect"].sum())
    assert (code2["Is_Dialect"] == 0).all()
    safe_write_csv(df, DERIVED_MOVIES_INFO)
    print(f"已写回主表：China 方言片 {china_dialect}，Tier 2b 保留 {t2b_kept}")

    # ---- 6. manifest / README 指纹同步 ----
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["whitelist_removal_20260815"] = {
        "applied_by": "scripts/apply_whitelist_removal_20260815.py",
        "rule": "用户人工复核：《芒种》(1986783) 不算方言片，移出 Tier 2b 白名单",
        "baseline": "(3082, 2309, 425, 348)",
        "backup": BACKUP_PATH.name,
        "date": TODAY,
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 指纹已更新: {fp}")

    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    if OLD_FP in text:
        readme_path.write_text(text.replace(OLD_FP, fp), encoding="utf-8")
        print("README.md 指纹已同步")
    else:
        print("README.md 未找到旧指纹（可能已同步），跳过")


if __name__ == "__main__":
    if "--apply-codebook" in sys.argv:
        # 仅把暂存的记录卡合并回 codebook_review.csv（文件释放后使用）
        ROOT2 = Path(__file__).resolve().parent.parent
        pending = ROOT2 / "data" / "codebook_review_pending_append.csv"
        if pending.exists():
            cb = pd.read_csv(pending, encoding="utf-8-sig")
            safe_write_csv(cb, ROOT2 / "data" / "codebook_review.csv")
            pending.unlink()
            print("记录卡已合并回 codebook_review.csv，暂存文件已删除")
        else:
            print("无暂存记录卡，无需操作")
    else:
        main()
