# -*- coding: utf-8 -*-
"""一次性脚本：《给阿嬷的情书》(37116446) 语言字段修正补收，升版 v4.4（2026-08-19）

背景：D1 排查时按主表"语言=汉语普通话"拍板"不补收"。用户出示豆瓣现页证据
（语言: 潮汕话 / 汉语普通话 / 泰语 / 英语，潮汕话排首）后溯源发现：
delivery_20260817 的 9,541 条新数据不含语言列（merge_delivery_data.py 的
NEW_DATA_MISSING_COLUMNS 明文置空），该片语言字段在 apply_empty_lang_backfill_20260818.py
第 4 步被默认回填为"汉语普通话"——属管线假阴性，非豆瓣标注事实。
dialect_defs.py 白名单闽南语组已收录"潮汕话"，按 v2.1 口径应判方言片。

用户拍板（2026-08-19）：补收，基线升版 v4.4。

本脚本：
1. 幂等备份 derived_movies.csv -> derived_movies_ama_lang_fix_backup_20260819.csv
2. 主表：语言字段按豆瓣现页修正为"潮汕话 / 汉语普通话 / 泰语 / 英语"，
   重算 Language_Category / Language_Code / Is_Dialect；Dialect_Evidence=LANG_FIX_20260819
3. review_queue.csv 追加补收溯源行
4. 不变量断言 + 新基线断言 China 方言 3,045 / 普通话·非方言 9,813
5. 重算 publication_fingerprint，更新 sample_manifest.json（新增溯源块）
6. 统计 delivery_20260817 来源中被默认回填的 China 片数量（诚实边界披露用）

用法：py scripts/apply_ama_lang_fix_20260819.py
"""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import publication_fingerprint, categorize_language, language_code  # noqa: E402
from freeze_constants import CHINA_DIALECT, CHINA_MANDARIN, PUBLICATION_RECORDS, TIER_BASELINE  # noqa: E402

MOVIE_ID = "37116446"
NEW_LANG = "潮汕话 / 汉语普通话 / 泰语 / 英语"
EXPECTED_TOTAL = PUBLICATION_RECORDS
BACKUP_PATH = ROOT / "data" / "derived_movies_ama_lang_fix_backup_20260819.csv"
REVIEW_QUEUE = ROOT / "data" / "cleaned" / "review_queue.csv"
OLD_FP = "3049f41485d4922965f7acb596fbdb3c8908fefc71540c47b6d51607d1b50da9"
TODAY = "2026-08-19"


def safe_write_csv(df: pd.DataFrame, path) -> None:
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    # ---- 1. 备份 ----
    if not BACKUP_PATH.exists():
        shutil.copy2(DERIVED_MOVIES_INFO, BACKUP_PATH)
        print(f"已备份 -> {BACKUP_PATH.name}")
    else:
        print(f"备份已存在，跳过：{BACKUP_PATH.name}")

    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False)
    df["movie_id"] = df["movie_id"].astype(str)
    assert len(df) == EXPECTED_TOTAL, f"总行数应为 {EXPECTED_TOTAL}，实测 {len(df)}"

    # ---- 2. 主表修正 ----
    idx = df.index[df["movie_id"] == MOVIE_ID]
    assert len(idx) == 1, f"movie_id {MOVIE_ID} 未找到或重复"
    i = idx[0]
    assert df.at[i, "片名"] == "给阿嬷的情书", f"片名不符：{df.at[i, '片名']}"
    if df.at[i, "Is_Dialect"] == 1 and df.at[i, "语言"] == NEW_LANG:
        print("该行已修正过（幂等），跳过主表修改")
    else:
        assert df.at[i, "Is_Dialect"] == 0 and df.at[i, "语言"] == "汉语普通话", \
            f"当前状态异常：{df.at[i, '语言']} / Is_Dialect={df.at[i, 'Is_Dialect']}"
        assert df.at[i, "数据来源"] == "douban_delivery_20260817"
        df.at[i, "语言"] = NEW_LANG
        df.at[i, "Language_Category"] = categorize_language(NEW_LANG)
        lc, is_dia = language_code(NEW_LANG, region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = "LANG_FIX_20260819"
        assert lc == 3 and is_dia == 1, f"重算结果异常：Language_Code={lc}, Is_Dialect={is_dia}"
        print(f"主表已修正：语言={NEW_LANG} -> Language_Code={lc}, Is_Dialect={is_dia}")

    # ---- 3. review_queue.csv 溯源 ----
    rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
    rq["movie_id"] = rq["movie_id"].astype(str)
    if not ((rq["movie_id"] == MOVIE_ID) & (rq["处置"] == "语言字段修正补收")).any():
        rq = pd.concat([rq, pd.DataFrame([{
            "movie_id": MOVIE_ID, "片名": "给阿嬷的情书", "年份": 2026,
            "Region": "China", "语言": NEW_LANG,
            "处置": "语言字段修正补收",
            "原因": "delivery_20260817 不含语言列，空语言回填默认普通话致假阴性；"
                    "豆瓣现页语言字段为 潮汕话/汉语普通话/泰语/英语（潮汕话排首），按现页修正补收",
            "审计日期": TODAY,
            "依据": "v4.1 白名单增删流程：数据源事实修正须留痕；潮汕话在 dialect_defs.py 闽南语组白名单内",
            "状态": "已处理", "处理日期": TODAY,
            "来源": "scripts/apply_ama_lang_fix_20260819.py",
        }])], ignore_index=True)
        safe_write_csv(rq, REVIEW_QUEUE)
        print("review_queue.csv 已追加补收溯源行")

    # ---- 4. 断言 ----
    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    china_mandarin = int((china["Is_Dialect"] == 0).sum())
    assert china_dialect == CHINA_DIALECT, f"China 方言片应为 {CHINA_DIALECT}，实测 {china_dialect}"
    assert china_mandarin == CHINA_MANDARIN, f"普通话·非方言应为 {CHINA_MANDARIN}，实测 {china_mandarin}"
    code2 = df[df["Language_Code"] == 2]
    code3 = df[df["Language_Code"] == 3]
    assert int(code3["Is_Dialect"].sum()) == len(code3) == int(df["Is_Dialect"].sum())
    assert (code2["Is_Dialect"] == 0).all()
    safe_write_csv(df, DERIVED_MOVIES_INFO)
    print(f"已写回主表：China 方言片 {china_dialect}，普通话·非方言 {china_mandarin}")

    # ---- 5. manifest 指纹与溯源 ----
    fp = publication_fingerprint(df)
    assert fp != OLD_FP, "指纹未变化，异常"
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["ama_lang_fix_20260819"] = {
        "applied_by": "scripts/apply_ama_lang_fix_20260819.py",
        "rule": "《给阿嬷的情书》(37116446)：delivery_20260817 无语言列，空语言回填默认"
                "普通话致假阴性；按豆瓣现页修正语言字段为 潮汕话/汉语普通话/泰语/英语，补收为方言片",
        "baseline": str(TIER_BASELINE),
        "previous_fingerprint": OLD_FP,
        "backup": BACKUP_PATH.name,
        "date": TODAY,
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 指纹已更新: {fp}")

    # ---- 6. 诚实边界披露统计 ----
    delivery = df[df["数据来源"] == "douban_delivery_20260817"]
    d_china = delivery[delivery["Region"] == "China"]
    defaulted = d_china[d_china["语言"] == "汉语普通话"]
    print(f"\ndelivery_20260817：共 {len(delivery)} 部，其中 China {len(d_china)} 部，"
          f"语言被默认回填为汉语普通话的 {len(defaulted)} 部"
          f"（含本片修正前状态；该批数据语言列整体缺失，为已知局限）")


if __name__ == "__main__":
    main()
