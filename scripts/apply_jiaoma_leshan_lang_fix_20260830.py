# -*- coding: utf-8 -*-
"""一次性脚本：《椒麻堂会》(27305997) 乐山话白名单补收（2026-08-30）

背景：豆瓣语言字段为「四川乐山话」，但 dialect_defs 西南官话组只有「四川话」
等上位标签，子串匹配不到「四川乐山话」（中间多了「乐山」）。回填后
classify 不识别 → Is_Dialect=0、Language_Code=5、误戳 EMPTY_LANG_DEFAULTED。
本片为 2021 年四川乐山话代表作（8.5 分 / 8 万+ 评价），应计 Tier 1 方言片。

前置：dialect_defs.py 西南官话组已增补「乐山话」「四川乐山话」。

本脚本：
1. 主表：语言保持「四川乐山话」，重算 Language_Category / Language_Code /
   Is_Dialect；Dialect_Evidence=LANG_FIX_20260830；清掉 EMPTY_LANG_DEFAULTED；
   Language_Provenance=douban_backfill
2. review_queue.csv 追加补收溯源行
3. language_backfill_overrides.csv 该 ID 保持/写为豆瓣现页
4. 重算 publication_fingerprint，更新 sample_manifest.json 溯源块

不在此断言 China 方言总数：本脚本若先于 opera 排除运行，中间态会是 3077。

用法：
  python scripts/apply_jiaoma_leshan_lang_fix_20260830.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    DERIVED_MOVIES_INFO,
    LANGUAGE_BACKFILL_OVERRIDES,
    SAMPLE_MANIFEST,
)
from data_processor import (  # noqa: E402
    atomic_write_csv,
    atomic_write_json,
    categorize_language,
    language_code,
    publication_fingerprint,
)
from freeze_constants import PUBLICATION_RECORDS, TIER_BASELINE  # noqa: E402

MOVIE_ID = "27305997"
TITLE = "椒麻堂会"
EXPECTED_LANG = "四川乐山话"
EVIDENCE = "LANG_FIX_20260830"
TODAY = "2026-08-30"
REVIEW_QUEUE = ROOT / "data" / "cleaned" / "review_queue.csv"


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def update_overrides(lang: str) -> None:
    path = LANGUAGE_BACKFILL_OVERRIDES
    if path.is_file():
        frame = pd.read_csv(path, encoding="utf-8-sig", dtype={"movie_id": "str"})
        frame["movie_id"] = frame["movie_id"].astype(str)
    else:
        frame = pd.DataFrame(columns=["movie_id", "语言", "fetched_at", "http_status", "source"])
    fetched_at = datetime.now(timezone.utc).isoformat()
    mask = frame["movie_id"] == MOVIE_ID
    row = {
        "movie_id": MOVIE_ID,
        "语言": lang,
        "fetched_at": fetched_at,
        "http_status": 200,
        "source": "douban_page",
    }
    if mask.any():
        for key, value in row.items():
            frame.loc[mask, key] = value
    else:
        frame = pd.concat([frame, pd.DataFrame([row])], ignore_index=True)
    atomic_write_csv(frame, path)


def main() -> None:
    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False)
    df["movie_id"] = df["movie_id"].astype(str)
    assert len(df) == PUBLICATION_RECORDS, f"总行数应为 {PUBLICATION_RECORDS}，实测 {len(df)}"

    idx = df.index[df["movie_id"] == MOVIE_ID]
    assert len(idx) == 1, f"movie_id {MOVIE_ID} 未找到或重复"
    i = idx[0]
    assert df.at[i, "片名"] == TITLE, f"片名不符：{df.at[i, '片名']}"
    current_lang = _text(df.at[i, "语言"])
    assert current_lang == EXPECTED_LANG, f"语言字段应为 {EXPECTED_LANG}，实测 {current_lang}"

    already = (
        int(df.at[i, "Is_Dialect"]) == 1
        and int(df.at[i, "Language_Code"]) == 3
        and EVIDENCE in _text(df.at[i, "Dialect_Evidence"])
    )
    if already:
        print("该行已修正过（幂等），跳过主表修改")
    else:
        df.at[i, "Language_Category"] = categorize_language(EXPECTED_LANG)
        lc, is_dia = language_code(EXPECTED_LANG, region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = EVIDENCE
        df.at[i, "Language_Provenance"] = "douban_backfill"
        assert lc == 3 and is_dia == 1, f"重算结果异常：Language_Code={lc}, Is_Dialect={is_dia}"
        print(f"主表已修正：语言={EXPECTED_LANG} -> Language_Code={lc}, Is_Dialect={is_dia}")

    if REVIEW_QUEUE.is_file():
        rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
        rq["movie_id"] = rq["movie_id"].astype(str)
        traced = (rq["movie_id"] == MOVIE_ID) & (rq["处置"] == "语言字段修正补收")
        if not traced.any():
            rq = pd.concat([rq, pd.DataFrame([{
                "movie_id": MOVIE_ID,
                "片名": TITLE,
                "年份": 2021,
                "Region": "China",
                "语言": EXPECTED_LANG,
                "处置": "语言字段修正补收",
                "原因": "豆瓣语言为四川乐山话，白名单仅有四川话导致子串无法命中，"
                        "被误判 Language_Code=5 并戳 EMPTY_LANG_DEFAULTED；"
                        "增补乐山话/四川乐山话后按现页补收为 Tier 1 方言片",
                "审计日期": TODAY,
                "依据": "v4.1 白名单增删流程：下位方言变体须显式列入；全表仅 1 行命中",
                "状态": "已处理",
                "处理日期": TODAY,
                "来源": "scripts/apply_jiaoma_leshan_lang_fix_20260830.py",
            }])], ignore_index=True)
            atomic_write_csv(rq, REVIEW_QUEUE)
            print("review_queue.csv 已追加补收溯源行")
        else:
            print("review_queue.csv 已有溯源行，跳过")

    update_overrides(EXPECTED_LANG)
    print(f"overrides 已更新：{MOVIE_ID} -> {EXPECTED_LANG} (douban_page)")

    row = df.loc[i]
    assert int(row["Is_Dialect"]) == 1 and int(row["Language_Code"]) == 3
    if already:
        return

    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    atomic_write_csv(df, DERIVED_MOVIES_INFO)
    print("已写回主表")

    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    previous = manifest.get("sample_fingerprint_sha256", "")
    manifest["sample_fingerprint_sha256"] = fp
    manifest["jiaoma_leshan_lang_fix_20260830"] = {
        "applied_by": "scripts/apply_jiaoma_leshan_lang_fix_20260830.py",
        "rule": "《椒麻堂会》(27305997)：语言四川乐山话因白名单缺口被漏判；"
                "增补乐山话/四川乐山话后补收为 Tier 1 方言片（LANG_FIX_20260830）",
        "baseline": str(TIER_BASELINE),
        "previous_fingerprint": previous,
        "date": TODAY,
    }
    atomic_write_json(manifest, SAMPLE_MANIFEST)
    print(f"manifest 指纹已更新: {fp}")


if __name__ == "__main__":
    main()
