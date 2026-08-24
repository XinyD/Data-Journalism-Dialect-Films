"""
2026-08-15 Tier 2b 口径重构落地（v4.1）：默认排除 + 证据漏斗补回。

背景：Tier 2b（普通话排首位、语言字段含方言白名单标签）共 702 部，
v4.0 口径全部计为方言片。v4.1 改为默认排除，仅经证据漏斗
（scripts/score_tier2b.py：E1/E2/E3/E4 正向证据 + N1/N2 负向画像）
auto_recover 的 62 部，以及灰区逐部补判（scripts/llm_judge_tier2b.py，
离线路径回填后 --apply）verdict=yes 的 287 部进入白名单，共 349 部保留；
其余 353 部（exclude 215 + 补判 no 109 + uncertain 29）默认排除。

本脚本：
1. 幂等备份 data/derived_movies.csv -> data/derived_movies_v21_tier2b_backup_20260815.csv
2. 对 702 部 Tier 2b：白名单保留 Is_Dialect=1，排除者 Is_Dialect→0、Language_Code 3→2
3. 新增 Dialect_Evidence 列：补回影片记录证据编号（E1/E2/…/BENCHMARK/LLM_JUDGE），
   被排除的 Tier 2b 记录 TIER2B_EXCLUDED，其余行留空（Tier 1/2a 由语言标签直接判定）
4. 不变量断言：code2 == Chinese&Is_Dialect=0、code3 == Is_Dialect=1
5. 重算 publication_fingerprint，更新 sample_manifest.json（追加 tier2b_20260815 块）
   与 README.md 中的指纹

注意：重跑 scripts/data_processor.py 会撤销本次重分类（main 已加守卫，见 v4.1 文档）。
用法：py scripts/apply_tier2b_reclassify_20260815.py
"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import publication_fingerprint  # noqa: E402
from freeze_constants import TIER2B_EXCLUDED, TIER2B_MANDARIN_FIRST  # noqa: E402

EXPECTED_TOTAL = 63_025
EXPECTED_TIER2B = 702
BACKUP_PATH = ROOT / "data" / "derived_movies_v41_tier2b_backup_20260818.csv"
EVIDENCE_CSV = ROOT / "data" / "tier2b_evidence.csv"
RECOVERED_CSV = ROOT / "data" / "tier2b_recovered.csv"
OLD_FP = "352711f639d8ac2aa35f0320c117efe86d01465d5e2ed67fa3d0a8ee6541f709"

# 用户指定标杆片（学术界/公众广泛认定的方言片），必须落在保留白名单内。
# 用 (片名, 年份) 消歧：数据集存在同名《亲爱的》（3166599，粤语标签、证据不足被排除）。
BENCHMARK_TITLES = (("疯狂的石头", 2006), ("疯狂的赛车", 2009), ("西藏往事", 2011),
                    ("秘密基地", 2020), ("亲爱的", 2014), ("心花路放", 2014))


def main() -> None:
    df = pd.read_csv(DERIVED_MOVIES_INFO, dtype={"movie_id": "string"}, low_memory=False)
    assert len(df) == EXPECTED_TOTAL, f"总行数 {len(df)} != {EXPECTED_TOTAL}"

    if "Dialect_Evidence" in df.columns:
        evidence = df["Dialect_Evidence"].fillna("")
        excluded_n = int(evidence.eq("TIER2B_EXCLUDED").sum())
        recovered_n = int(evidence.str.startswith(("E:", "BENCHMARK", "LLM_JUDGE", "人工复核")).sum())
        if excluded_n == TIER2B_EXCLUDED and recovered_n == TIER2B_MANDARIN_FIRST:
            print(
                f"Tier 2b 已落地（排除 {excluded_n} / 补回 {recovered_n}），跳过（幂等）"
            )
            return

    # ---- 0. 幂等备份 ----
    if not BACKUP_PATH.exists():
        shutil.copy2(DERIVED_MOVIES_INFO, BACKUP_PATH)
        print(f"已备份 -> {BACKUP_PATH.name}")
    else:
        print(f"备份已存在，跳过: {BACKUP_PATH.name}")

    # ---- 1. 构建 movie_id -> 保留证据 映射 ----
    evidence = pd.read_csv(EVIDENCE_CSV, dtype={"movie_id": "string"})
    recovered = pd.read_csv(RECOVERED_CSV, dtype={"movie_id": "string"})
    assert len(evidence) == EXPECTED_TIER2B, f"证据表 {len(evidence)} 行 != {EXPECTED_TIER2B}"

    keep: dict[str, str] = {}  # movie_id -> Dialect_Evidence
    # auto_recover：记录规则引擎命中的证据编号（E1/E2/E3/E4 组合）
    for _, row in evidence[evidence["verdict"] == "auto_recover"].iterrows():
        keep[str(row["movie_id"])] = f"E:{row['hits']}"
    # 灰区补判 yes：记录 LLM_JUDGE（标杆片记 BENCHMARK）
    for _, row in recovered.iterrows():
        keep[str(row["movie_id"])] = str(row["evidence"])

    overlap = set(keep) & set(evidence[evidence["verdict"] == "exclude"]["movie_id"])
    assert not overlap, f"白名单与 exclude 判定重叠: {overlap}"
    print(f"保留白名单: {len(keep)} 部（auto_recover {int((evidence['verdict']=='auto_recover').sum())}"
          f" + 补判 yes {len(recovered)}）")

    # ---- 2. 定位 702 部 Tier 2b（当前 Is_Dialect=1、China、普通话排首+含方言标签）----
    sys.path.insert(0, str(ROOT / "scripts"))
    from dialect_defs import has_strict_dialect_tag, has_mandarin_tag, lang_parts, normalize_language_tags, first_tag_is_foreign, DIALECT_MARKERS_STRICT, normalize_text  # noqa: E402

    china_mask = df["Region"].eq("China")

    def is_tier2b(row) -> bool:
        lang = str(row.get("语言", "") or "")
        if not (has_strict_dialect_tag(lang) and has_mandarin_tag(lang)):
            return False
        if first_tag_is_foreign(lang):
            return False  # 方案 A 已排除，不属于 Tier 2b
        langs = normalize_language_tags(lang)
        for i, l in enumerate(langs):
            lnorm = normalize_text(l)
            for marker in DIALECT_MARKERS_STRICT:
                if normalize_text(marker) in lnorm:
                    return i != 0  # 方言非首位（普通话排首）才是 Tier 2b
        return False

    t2b_idx = df.index[china_mask & df["Is_Dialect"].astype(int).eq(1)]
    t2b_mask = pd.Series([is_tier2b(df.loc[i]) for i in t2b_idx], index=t2b_idx)
    t2b_idx = t2b_idx[t2b_mask.values]
    assert len(t2b_idx) == EXPECTED_TIER2B, f"Tier 2b 检出 {len(t2b_idx)} != {EXPECTED_TIER2B}"

    # 标杆片断言：必须在保留白名单内（按 片名+年份 消歧）
    t2b_keys = dict(zip(df.loc[t2b_idx, "movie_id"],
                        zip(df.loc[t2b_idx, "片名"].astype(str), df.loc[t2b_idx, "年份"].astype(int))))
    missing = [t for t in BENCHMARK_TITLES if t not in set(t2b_keys.values())]
    assert not missing, f"标杆片未出现在 Tier 2b 集合: {missing}"
    benchmark_ids = {mid for mid, key in t2b_keys.items() if key in BENCHMARK_TITLES}
    assert benchmark_ids <= set(keep), f"标杆片未进入白名单: {benchmark_ids}"

    # ---- 3. 写回：保留者记证据；排除者 Is_Dialect→0、Language_Code→2 ----
    if "Dialect_Evidence" not in df.columns:
        df["Dialect_Evidence"] = ""
    df["Dialect_Evidence"] = df["Dialect_Evidence"].fillna("").astype(str)

    keep_idx = [i for i in t2b_idx if str(df.at[i, "movie_id"]) in keep]
    drop_idx = [i for i in t2b_idx if str(df.at[i, "movie_id"]) not in keep]
    assert len(keep_idx) == len(keep), f"保留 {len(keep_idx)} != 白名单 {len(keep)}"
    assert len(keep_idx) + len(drop_idx) == EXPECTED_TIER2B

    for i in keep_idx:
        df.at[i, "Dialect_Evidence"] = keep[str(df.at[i, "movie_id"])]
    for i in drop_idx:
        df.at[i, "Is_Dialect"] = 0
        df.at[i, "Language_Code"] = 2
        df.at[i, "Dialect_Evidence"] = "TIER2B_EXCLUDED"

    print(f"保留 {len(keep_idx)} 部（Is_Dialect=1 + 证据编号）；排除 {len(drop_idx)} 部（→普通话组）")

    # ---- 4. 不变量复核 ----
    df["Is_Dialect"] = df["Is_Dialect"].astype(int)
    df["Language_Code"] = df["Language_Code"].astype(int)
    code2 = int((df["Language_Code"] == 2).sum())
    ch_d0 = int(((df["Language_Category"] == "Chinese") & (df["Is_Dialect"] == 0)).sum())
    code3 = int((df["Language_Code"] == 3).sum())
    d1 = int((df["Is_Dialect"] == 1).sum())
    print(f"复核: code2={code2} Chinese&D0={ch_d0} code3={code3} D1={d1}")
    assert code2 == ch_d0 and code3 == d1, "Language_Code / Is_Dialect 不变量被破坏"

    china_dialect = int((china_mask & (df["Is_Dialect"] == 1)).sum())
    print(f"China 方言片: 3436 -> {china_dialect}（预期 ~3083，排除 {len(drop_idx)} 部）")
    assert china_dialect == 3436 - len(drop_idx)

    # ---- 5. 写回 CSV ----
    df.to_csv(DERIVED_MOVIES_INFO, index=False, encoding="utf-8-sig")
    print(f"已写回 {DERIVED_MOVIES_INFO}")

    # ---- 6. manifest / README 指纹同步 ----
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["publication_records"] == EXPECTED_TOTAL
    manifest["sample_fingerprint_sha256"] = fp
    manifest["tier2b_20260818"] = {
        "applied_by": "scripts/apply_tier2b_reclassify_20260815.py",
        "rule": "v4.1 Tier 2b 证据审查：普通话排首+方言标签默认排除，经证据漏斗/补判白名单补回",
        "pipeline": [
            "scripts/score_tier2b.py -> data/tier2b_evidence.csv (702 = 63 auto_recover + 424 gray_zone + 215 exclude)",
            "scripts/llm_judge_tier2b.py --apply data/tier2b_gray_zone_review.csv -> data/tier2b_recovered.csv (286 yes)",
        ],
        "tier2b_total": EXPECTED_TIER2B,
        "recovered_kept": len(keep_idx),
        "excluded_default": len(drop_idx),
        "china_dialect_movies_before": 3436,
        "china_dialect_movies_after": china_dialect,
        "new_column": "Dialect_Evidence（E:E1/E2/…=规则引擎证据, BENCHMARK/LLM_JUDGE=补判, TIER2B_EXCLUDED=默认排除）",
        "trace_files": [
            "data/tier2b_evidence.csv", "data/tier2b_gray_zone_review.csv",
            "data/tier2b_recovered.csv", "data/cleaned/review_queue.csv",
            "data/derived_movies_v41_tier2b_backup_20260818.csv",
        ],
        "note": f"行集与行数不变（{EXPECTED_TOTAL:,}）；指纹变化因 {len(drop_idx)} 行 Is_Dialect 1→0、Language_Code 3→2。",
    }
    SAMPLE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest 指纹已更新: {fp}")

    readme_path = ROOT / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    if OLD_FP in text:
        text = text.replace(OLD_FP, fp)
        readme_path.write_text(text, encoding="utf-8")
        print("README.md 指纹已同步")
    else:
        print("README.md 未找到旧指纹（可能已同步），跳过")


if __name__ == "__main__":
    main()
