# -*- coding: utf-8 -*-
"""一次性脚本：《隐入尘烟》(35131346) 语言字段修正补收（2026-08-30）

背景：delivery_20260817 不含语言列，该片被默认成「汉语普通话」，随后 Wikidata
P364 回填为「汉语普通话 / Mandarin」。Wikidata 不得铸造 China 方言，故主表
Is_Dialect=0。用户出示豆瓣现页证据（语言: 甘肃方言 / 汉语普通话，甘肃方言排首）
后按 v4.1 口径补收为 Tier 2a 方言片。dialect_defs.py 中原/兰银官话组已收录
「甘肃方言」。

本脚本：
1. 主表：语言字段按豆瓣现页修正为「甘肃方言 / 汉语普通话」，
   重算 Language_Category / Language_Code / Is_Dialect；
   Dialect_Evidence=LANG_FIX_20260830；Language_Provenance=douban_backfill
2. review_queue.csv 追加补收溯源行
3. language_backfill_overrides.csv 该 ID 改为豆瓣现页（source=douban_page）
4. 断言发布终态 China 方言 / Tier 与 freeze_constants 一致
5. 重算 publication_fingerprint，更新 sample_manifest.json 溯源块

用法：
  python scripts/apply_yinruchenyan_lang_fix_20260830.py
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
from freeze_constants import (  # noqa: E402
    CHINA_DIALECT,
    CHINA_MANDARIN,
    PUBLICATION_RECORDS,
    TIER_BASELINE,
)
from language_backfill_lib import YINRUCHENYAN_MOVIE_ID  # noqa: E402

MOVIE_ID = YINRUCHENYAN_MOVIE_ID
TITLE = "隐入尘烟"
NEW_LANG = "甘肃方言 / 汉语普通话"
PRE_LANGS = frozenset({"汉语普通话", "汉语普通话 / Mandarin"})
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

    already = (
        int(df.at[i, "Is_Dialect"]) == 1
        and _text(df.at[i, "语言"]) == NEW_LANG
        and EVIDENCE in _text(df.at[i, "Dialect_Evidence"])
    )
    if already:
        print("该行已修正过（幂等），跳过主表修改")
    else:
        current_lang = _text(df.at[i, "语言"])
        assert int(df.at[i, "Is_Dialect"]) == 0 and current_lang in PRE_LANGS, (
            f"当前状态异常：{current_lang} / Is_Dialect={df.at[i, 'Is_Dialect']}"
        )
        assert _text(df.at[i, "数据来源"]) == "douban_delivery_20260817"
        df.at[i, "语言"] = NEW_LANG
        df.at[i, "Language_Category"] = categorize_language(NEW_LANG)
        lc, is_dia = language_code(NEW_LANG, region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = EVIDENCE
        df.at[i, "Language_Provenance"] = "douban_backfill"
        assert lc == 3 and is_dia == 1, f"重算结果异常：Language_Code={lc}, Is_Dialect={is_dia}"
        print(f"主表已修正：语言={NEW_LANG} -> Language_Code={lc}, Is_Dialect={is_dia}")

    rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
    rq["movie_id"] = rq["movie_id"].astype(str)
    traced = (rq["movie_id"] == MOVIE_ID) & (rq["处置"] == "语言字段修正补收")
    if not traced.any():
        rq = pd.concat([rq, pd.DataFrame([{
            "movie_id": MOVIE_ID,
            "片名": TITLE,
            "年份": 2022,
            "Region": "China",
            "语言": NEW_LANG,
            "处置": "语言字段修正补收",
            "原因": "delivery_20260817 不含语言列，空语言回填默认普通话后 Wikidata P364 "
                    "写成汉语普通话/Mandarin；豆瓣现页为 甘肃方言/汉语普通话（甘肃方言排首），"
                    "按现页修正补收为 Tier 2a 方言片",
            "审计日期": TODAY,
            "依据": "v4.1 白名单增删流程：数据源事实修正须留痕；甘肃方言在 dialect_defs.py "
                    "中原/兰银官话组白名单内",
            "状态": "已处理",
            "处理日期": TODAY,
            "来源": "scripts/apply_yinruchenyan_lang_fix_20260830.py",
        }])], ignore_index=True)
        atomic_write_csv(rq, REVIEW_QUEUE)
        print("review_queue.csv 已追加补收溯源行")
    else:
        print("review_queue.csv 已有溯源行，跳过")

    update_overrides(NEW_LANG)
    print(f"overrides 已更新：{MOVIE_ID} -> {NEW_LANG} (douban_page)")

    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    china_mandarin = int((china["Is_Dialect"] == 0).sum())
    assert china_dialect == CHINA_DIALECT, f"China 方言片应为 {CHINA_DIALECT}，实测 {china_dialect}"
    assert china_mandarin == CHINA_MANDARIN, f"普通话·非方言应为 {CHINA_MANDARIN}，实测 {china_mandarin}"
    code2 = df[df["Language_Code"] == 2]
    code3 = df[df["Language_Code"] == 3]
    assert int(code3["Is_Dialect"].sum()) == len(code3) == int(df["Is_Dialect"].sum())
    assert (code2["Is_Dialect"] == 0).all()
    if already:
        print(f"主表未改写：China 方言片 {china_dialect}，普通话·非方言 {china_mandarin}")
        return

    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    atomic_write_csv(df, DERIVED_MOVIES_INFO)
    print(f"已写回主表：China 方言片 {china_dialect}，普通话·非方言 {china_mandarin}")

    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    previous = manifest.get("sample_fingerprint_sha256", "")
    if not already:
        assert fp != previous, "指纹未变化，异常"
    manifest["sample_fingerprint_sha256"] = fp
    manifest["yinruchenyan_lang_fix_20260830"] = {
        "applied_by": "scripts/apply_yinruchenyan_lang_fix_20260830.py",
        "rule": "《隐入尘烟》(35131346)：delivery_20260817 无语言列，空语言回填默认普通话，"
                "Wikidata P364 写成汉语普通话/Mandarin；按豆瓣现页修正为 甘肃方言/汉语普通话"
                "（甘肃方言排首），补收为 Tier 2a 方言片",
        "baseline": str(TIER_BASELINE),
        "previous_fingerprint": previous,
        "date": TODAY,
    }
    atomic_write_json(manifest, SAMPLE_MANIFEST)
    print(f"manifest 指纹已更新: {fp}")


if __name__ == "__main__":
    main()
