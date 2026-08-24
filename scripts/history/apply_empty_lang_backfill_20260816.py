# -*- coding: utf-8 -*-
"""一次性脚本：空语言84部电影人工复核后全量回填（2026-08-16 v2）

步骤：
1. 修复补全结果CSV：不曾消失的台湾省 "删除" → "台湾国语"
2. 重新生成补全结果HTML
3. 回填 derived_movies.csv：
   - 8部方言电影（含3部新+2部已有+3部已有不动）
   - 1部撤销方言（巴依尔的春节）
   - 5部新增方言（龙的深处/穷人·榴莲/监狱建筑师/出花园/阿紫）
   - 70部非方言（补全语言字段）
4. 更新 codebook_review / review_queue / manifest
"""
import json, os, shutil, stat, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST  # noqa: E402
from data_processor import categorize_language, language_code, publication_fingerprint  # noqa: E402
from dialect_defs import has_strict_dialect_tag, first_tag_is_foreign, has_mandarin_tag  # noqa: E402

TODAY = "2026-08-16"
CSV_RESULT = ROOT / "data" / "archive" / "analysis" / "空语言补全结果_84部.csv"
HTML_RESULT = ROOT / "data" / "archive" / "analysis" / "空语言补全结果_84部.html"
BACKUP = ROOT / "data" / "archive" / "backups" / "derived_movies_empty_lang_backup2_20260816.csv"
CODEBOOK = ROOT / "data" / "archive" / "analysis" / "codebook_review.csv"
REVIEW_QUEUE = ROOT / "data" / "cleaned" / "review_queue.csv"

EXPECTED_TOTAL = 53_467

# ── 8部方言电影 → derived_movies.csv 语言字段 ──
DIALECT_TAGS = {
    "4133310":  {"片名": "惊梦魂",         "lang": "粤语",                   "tier": "Tier 1", "note": "粤语为主要对白语言"},
    "2129914":  {"片名": "八廓南街16号",    "lang": "藏语",                   "tier": "Tier 1", "note": "藏语承担核心叙事功能"},
    "1308060":  {"片名": "龙的深处―失落的拼图", "lang": "粤语/安徽方言/国语",  "tier": "Tier 2a", "note": "纪录片多语言交织，国语旁白为框架但粤语和安徽方言占比显著"},
    "10518931": {"片名": "猎人与骷髅怪",    "lang": "藏语",                   "tier": "Tier 1", "note": "全程藏语（甘孜方言），少数民族语言片"},
    "19899635": {"片名": "穷人·榴莲·麻药·偷渡客", "lang": "云南方言/普通话/缅语", "tier": "Tier 2a", "note": "云南方言属西南官话，缅语为外语不影响方言定性"},
    "30441138": {"片名": "监狱建筑师",      "lang": "粤语",                   "tier": "Tier 1", "note": "香港取景，粤语对白承担叙事"},
    "34436895": {"片名": "出花园",          "lang": "潮汕方言",               "tier": "Tier 1", "note": "潮汕方言电影"},
    "34847185": {"片名": "阿紫",            "lang": "闽南语/普通话",          "tier": "Tier 2a", "note": "台语=闽南语属闽语分支；国台语混合"},
}

# ── 撤销方言 ──
REVERT = {
    "34953763": {"片名": "巴依尔的春节", "lang": "普通话", "note": "撤销方言判定，搜狗百科标注对白语言=普通话"},
}

# ── 非方言但补全语言需要修正（会导致误判Is_Dialect=1的） ──
NONDIALECT_FIX = {
    "33425521": {"片名": "张学友1/2世纪世界巡回演唱会", "orig": "普通话/粤语", "fix": "普通话", "note": "演唱会，简化避免误判方言"},
    "35376928": {"片名": "张敬轩x香港中乐团《盛乐》演唱会", "orig": "普通话/粤语", "fix": "普通话", "note": "演唱会，简化避免误判方言"},
    "30253124": {"片名": "腐草为萤", "orig": "无语言", "fix": "汉语普通话", "note": "无语言信息，默认汉语普通话"},
    "30396250": {"片名": "公交车", "orig": "无语言", "fix": "汉语普通话", "note": "无语言信息，默认汉语普通话"},
}

def safe_write_csv(df, path):
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    df.to_csv(path, index=False, encoding="utf-8-sig")

def main():
    # ════════════════ STEP 1: 修复补全结果CSV ════════════════
    print("=" * 60)
    print("STEP 1: 修复补全结果CSV")
    print("=" * 60)
    result_df = pd.read_csv(CSV_RESULT, encoding="utf-8-sig", dtype=str).fillna("")
    idx = result_df.index[result_df["movie_id"] == "30215020"]
    assert len(idx) == 1, "不曾消失的台湾省 未找到"
    i = idx[0]
    result_df.at[i, "补全语言"] = "台湾国语"
    result_df.at[i, "置信度"] = "人工复核"
    result_df.at[i, "提取依据"] = "用户复核确认"
    result_df.at[i, "备注"] = "台湾国语纪录片，非方言"
    safe_write_csv(result_df, CSV_RESULT)
    print(f"  已修复: 不曾消失的台湾省 → 台湾国语")

    # ════════════════ STEP 2: 重新生成HTML ════════════════
    print("\n" + "=" * 60)
    print("STEP 2: 重新生成补全结果HTML")
    print("=" * 60)
    html = gen_html(result_df)
    HTML_RESULT.write_text(html, encoding="utf-8")
    print(f"  HTML已重新生成: {HTML_RESULT.name}")

    # ════════════════ STEP 3: 回填 derived_movies.csv ════════════════
    print("\n" + "=" * 60)
    print("STEP 3: 回填 derived_movies.csv")
    print("=" * 60)

    # 备份
    if not BACKUP.exists():
        shutil.copy2(DERIVED_MOVIES_INFO, BACKUP)
        print(f"  已备份 → {BACKUP.name}")
    else:
        print(f"  备份已存在，跳过")

    df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False)
    df["movie_id"] = df["movie_id"].astype(str)
    assert len(df) == EXPECTED_TOTAL, f"总行数 {len(df)} != {EXPECTED_TOTAL}"

    changes = []

    # 3a. 方言电影（含已有的3部确认+新增5部）
    print("\n  --- 方言电影 ---")
    for mid, info in DIALECT_TAGS.items():
        idx = df.index[df["movie_id"] == mid]
        assert len(idx) == 1, f"{info['片名']} movie_id={mid} 未找到或重复"
        i = idx[0]
        row = df.loc[i]
        assert row["Region"] == "China", f"{info['片名']} Region={row['Region']}"
        old_lang = row["语言"] if pd.notna(row["语言"]) else ""
        old_isd = int(row["Is_Dialect"])

        df.at[i, "语言"] = info["lang"]
        df.at[i, "Language_Category"] = categorize_language(info["lang"])
        lc, is_dia = language_code(info["lang"], region=row["Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = ""

        # 验证
        assert is_dia == 1, f"{info['片名']} Is_Dialect={is_dia}, 预期1"
        assert not first_tag_is_foreign(info["lang"]), f"{info['片名']} 首标签为外语!"
        has_mand = has_mandarin_tag(info["lang"])
        tier = "Tier 1" if not has_mand else ("Tier 2a" if not _first_is_mandarin(info["lang"]) else "Tier 2b")
        print(f"  {info['片名']:25s} | {old_lang!s:10s}→{info['lang']:25s} | Is_Dialect {old_isd}→{is_dia} | {tier}")

        changes.append({
            "movie_id": mid, "片名": info["片名"], "原语言": old_lang,
            "补全语言": info["lang"], "Is_Dialect": is_dia, "Tier": tier,
            "变更": "方言(已有)" if old_isd == 1 else "方言(新增)",
        })

    # 3b. 撤销方言
    print("\n  --- 撤销方言 ---")
    for mid, info in REVERT.items():
        idx = df.index[df["movie_id"] == mid]
        assert len(idx) == 1
        i = idx[0]
        row = df.loc[i]
        old_lang = row["语言"] if pd.notna(row["语言"]) else ""
        old_isd = int(row["Is_Dialect"])
        assert old_isd == 1, f"{info['片名']} 当前Is_Dialect={old_isd}, 预期1(需撤销)"

        df.at[i, "语言"] = info["lang"]
        df.at[i, "Language_Category"] = categorize_language(info["lang"])
        lc, is_dia = language_code(info["lang"], region=row["Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        df.at[i, "Dialect_Evidence"] = ""

        assert is_dia == 0, f"{info['片名']} Is_Dialect={is_dia}, 预期0"
        print(f"  {info['片名']:25s} | {old_lang!s:10s}→{info['lang']:10s} | Is_Dialect {old_isd}→{is_dia} | 撤销方言")
        changes.append({
            "movie_id": mid, "片名": info["片名"], "原语言": old_lang,
            "补全语言": info["lang"], "Is_Dialect": is_dia, "Tier": "N/A",
            "变更": "撤销方言",
        })

    # 3c. 非方言电影（需要修正补全语言的）
    print("\n  --- 非方言(修正语言) ---")
    for mid, info in NONDIALECT_FIX.items():
        idx = df.index[df["movie_id"] == mid]
        assert len(idx) == 1
        i = idx[0]
        df.at[i, "语言"] = info["fix"]
        df.at[i, "Language_Category"] = categorize_language(info["fix"])
        lc, is_dia = language_code(info["fix"], region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        assert is_dia == 0
        print(f"  {info['片名']:35s} | {info['orig']:12s}→{info['fix']:12s} | Is_Dialect=0")
        changes.append({
            "movie_id": mid, "片名": info["片名"], "原语言": "",
            "补全语言": info["fix"], "Is_Dialect": 0, "Tier": "N/A",
            "变更": f"非方言(修正:{info['note']})",
        })

    # 3d. 其余非方言电影（直接用补全结果中的语言）
    print("\n  --- 其余非方言(补全语言) ---")
    dialect_ids = set(DIALECT_TAGS.keys()) | set(REVERT.keys()) | set(NONDIALECT_FIX.keys())
    # 4部已变更的也排除（惊梦魂、八廓南街16号、猎人与骷髅怪在DIALECT_TAGS中）
    # 巴依尔在REVERT中
    count = 0
    for _, r in result_df.iterrows():
        mid = str(r["movie_id"])
        if mid in dialect_ids:
            continue
        idx = df.index[df["movie_id"] == mid]
        assert len(idx) == 1, f"movie_id={mid} 未找到"
        i = idx[0]
        lang_val = str(r["补全语言"]).strip()
        if not lang_val or lang_val == "nan":
            lang_val = "汉语普通话"
        # 安全检查：如果补全语言会导致Is_Dialect=1，降级为"普通话"
        if has_strict_dialect_tag(lang_val) and not first_tag_is_foreign(lang_val):
            print(f"  ⚠️ {r['片名']} 补全语言'{lang_val}'会触发方言判定，降级为'普通话'")
            lang_val = "普通话"
        df.at[i, "语言"] = lang_val
        df.at[i, "Language_Category"] = categorize_language(lang_val)
        lc, is_dia = language_code(lang_val, region=df.at[i, "Region"])
        df.at[i, "Language_Code"] = lc
        df.at[i, "Is_Dialect"] = is_dia
        count += 1
    print(f"  共补全 {count} 部非方言电影的语言字段")

    # 3e. 断言
    print("\n  --- 断言验证 ---")
    china = df[df["Region"] == "China"]
    china_dialect = int(china["Is_Dialect"].sum())
    empty_lang_china = int(((china["语言"].isna() | (china["语言"].astype(str).str.strip() == "")) & (china["Is_Dialect"] == 0)).sum())
    print(f"  China 方言片: {china_dialect}")
    print(f"  空语言且非方言(China): {empty_lang_china}")

    # 预期: 原3086 - 1(巴依尔撤销) + 5(新增) = 3090
    expected_dialect = 3086 - 1 + 5
    assert china_dialect == expected_dialect, f"China 方言片应为 {expected_dialect}，实测 {china_dialect}"
    print(f"  ✓ China 方言片 = {china_dialect} (预期 {expected_dialect})")

    # 空语言China应该为0（全部84部已补全）
    # 但4部在之前已补全（惊梦魂/八廓/猎人/巴依尔），其中巴依尔现在是"普通话"不再空
    assert empty_lang_china == 0, f"空语言China仍有 {empty_lang_china} 部"
    print(f"  ✓ 空语言China = 0（全部已补全）")

    # 写回主表
    safe_write_csv(df, DERIVED_MOVIES_INFO)
    print(f"\n  主表已写回: {DERIVED_MOVIES_INFO.name}")

    # ════════════════ STEP 4: 更新辅助文件 ════════════════
    print("\n" + "=" * 60)
    print("STEP 4: 更新辅助文件")
    print("=" * 60)

    # codebook_review
    cb = pd.read_csv(CODEBOOK, encoding="utf-8-sig")
    cb["movie_id"] = cb["movie_id"].astype(str)
    for mid, info in {**DIALECT_TAGS, **REVERT}.items():
        card = {
            "movie_id": mid, "片名": info["片名"],
            "年份": int(df.loc[df["movie_id"] == mid, "年份"].iloc[0]) if pd.notna(df.loc[df["movie_id"] == mid, "年份"].iloc[0]) else "",
            "方言名称": info.get("lang", "") if mid in DIALECT_TAGS else "",
            "少数民族语言": "藏语" if mid in ("2129914", "10518931") else "",
            "结论": "方言" if mid in DIALECT_TAGS else "非方言",
            "证据": f"用户人工复核（{TODAY}）：{info['note']}",
        }
        if card["movie_id"] not in cb["movie_id"].values:
            cb = pd.concat([cb, pd.DataFrame([card])], ignore_index=True)
        else:
            mask = cb["movie_id"] == card["movie_id"]
            for k in ("结论", "证据", "方言名称", "少数民族语言"):
                if k in cb.columns:
                    cb.loc[mask, k] = card[k]
    safe_write_csv(cb, CODEBOOK)
    print(f"  codebook_review.csv 已更新")

    # review_queue
    rq = pd.read_csv(REVIEW_QUEUE, encoding="utf-8-sig")
    rq["movie_id"] = rq["movie_id"].astype(str)
    for mid, info in {**DIALECT_TAGS, **REVERT}.items():
        action = "空语言补回方言口径v2" if mid in DIALECT_TAGS else "空语言撤销方言判定"
        if not ((rq["movie_id"] == mid) & (rq["处置"] == action)).any():
            rq = pd.concat([rq, pd.DataFrame([{
                "movie_id": mid, "片名": info["片名"],
                "年份": int(df.loc[df["movie_id"] == mid, "年份"].iloc[0]) if pd.notna(df.loc[df["movie_id"] == mid, "年份"].iloc[0]) else "",
                "Region": "China", "语言": info["lang"],
                "处置": action,
                "原因": f"用户人工复核（{TODAY}）：{info['note']}",
                "审计日期": TODAY,
                "依据": "v4.1 方言定义",
                "状态": "已处理", "处理日期": TODAY,
                "来源": "scripts/apply_empty_lang_backfill_20260816.py",
            }])], ignore_index=True)
    safe_write_csv(rq, REVIEW_QUEUE)
    print(f"  review_queue.csv 已更新")

    # manifest
    fp = publication_fingerprint(df)
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    manifest["sample_fingerprint_sha256"] = fp
    manifest["empty_lang_backfill_20260816"] = {
        "applied_by": "scripts/apply_empty_lang_backfill_20260816.py",
        "rule": "用户人工复核：84部空语言China电影全量回填",
        "dialect_new": [{"movie_id": mid, "片名": info["片名"], "语言": info["lang"], "tier": info["tier"]}
                        for mid, info in DIALECT_TAGS.items() if mid not in ("4133310","2129914","10518931")],
        "dialect_revert": [{"movie_id": mid, "片名": info["片名"], "语言": info["lang"]}
                           for mid, info in REVERT.items()],
        "baseline_china_dialect": 3086,
        "new_china_dialect": expected_dialect,
        "backup": BACKUP.name,
        "date": TODAY,
    }
    SAMPLE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  manifest 指纹已更新: {fp[:16]}...")

    # 变更摘要
    summary_path = ROOT / "data" / "archive" / "analysis" / "empty_lang_backfill_summary_20260816.csv"
    safe_write_csv(pd.DataFrame(changes), summary_path)
    print(f"  变更摘要: {summary_path.name}")

    print(f"\n{'=' * 60}")
    print(f"全部完成！China 方言片 {3086} → {expected_dialect}（净 +{expected_dialect - 3086}）")
    print(f"  新增方言: 5部（龙的深处/穷人·榴莲/监狱建筑师/出花园/阿紫）")
    print(f"  撤销方言: 1部（巴依尔的春节）")
    print(f"  补全语言: 84部（含上述6部+78部非方言）")
    print(f"{'=' * 60}")


def _first_is_mandarin(lang):
    """检查语言字段首标签是否为普通话标签"""
    from dialect_defs import lang_parts, normalize_text, MANDARIN_MARKERS, DIALECT_MARKERS_STRICT, marker_matches_part
    parts = lang_parts(lang)
    if not parts:
        return False
    p0 = normalize_text(parts[0])
    # 如果首标签本身是方言标签，不算普通话
    for marker in DIALECT_MARKERS_STRICT:
        if marker_matches_part(marker, p0):
            return False
    for m in MANDARIN_MARKERS:
        if m in p0:
            return True
    return False


def gen_html(df):
    """生成补全结果HTML"""
    dialect_ids = ['4133310','2129914','1308060','10518931','19899635','30441138','34436895','34847185']
    nondialect_review_ids = ['34953763','33425521','35376928','30253124','30396250','1937852',
        '27059170','27174453','30397897','30215020','30300095','34436898','30396250',
        '26309329','27062853','34436898','35376928','34953763']

    html_parts = [f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>空语言补全结果_84部_人工复核版</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Microsoft YaHei","Segoe UI",sans-serif; background:#f5f5f5; color:#333; line-height:1.6; }}
.container {{ max-width:1400px; margin:0 auto; padding:20px; }}
h1 {{ text-align:center; margin:20px 0 10px; font-size:24px; color:#1a1a2e; }}
.subtitle {{ text-align:center; color:#888; font-size:13px; margin-bottom:20px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:24px; }}
.stat-card {{ background:#fff; border-radius:8px; padding:16px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
.stat-card .num {{ font-size:28px; font-weight:700; }}
.stat-card .label {{ font-size:12px; color:#888; margin-top:4px; }}
.stat-dialect .num {{ color:#e74c3c; }}
.stat-nondialect .num {{ color:#2ecc71; }}
.stat-total .num {{ color:#9b59b6; }}
.section-title {{ font-size:18px; font-weight:600; margin:24px 0 12px; padding-left:12px; border-left:4px solid #4a90d9; }}
.dialect-list {{ background:#fff; border-radius:8px; padding:16px; margin-bottom:16px; box-shadow:0 2px 4px rgba(0,0,0,0.06); overflow-x:auto; }}
.dialect-list table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.dialect-list th {{ background:#4a90d9; color:#fff; padding:8px 10px; text-align:left; white-space:nowrap; }}
.dialect-list td {{ padding:6px 10px; border-bottom:1px solid #eee; vertical-align:top; }}
.dialect-list tr:hover {{ background:#f0f7ff; }}
.lang-dialect {{ color:#e74c3c; font-weight:600; }}
.lang-nondialect {{ color:#2ecc71; }}
.controls {{ display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }}
.controls input, .controls select {{ padding:6px 12px; border:1px solid #ddd; border-radius:6px; font-size:13px; }}
.controls input {{ flex:1; min-width:200px; }}
.detail-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
.detail-table th {{ background:#34495e; color:#fff; padding:8px; text-align:left; position:sticky; top:0; z-index:10; white-space:nowrap; }}
.detail-table td {{ padding:6px 8px; border-bottom:1px solid #eee; vertical-align:top; }}
.detail-table tr:hover {{ background:#f0f7ff; }}
.table-wrap {{ max-height:600px; overflow:auto; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.06); background:#fff; }}
a {{ color:#4a90d9; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.note-box {{ background:#fff3cd; border:1px solid #ffe08a; border-radius:8px; padding:12px 16px; margin:16px 0; font-size:13px; }}
</style>
</head>
<body>
<div class="container">
<h1>空语言补全结果 — 84部人工复核版</h1>
<p class="subtitle">derived_movies.csv 中语言字段为空 且 Region=China 的84部电影 | 人工复核日期：2026-08-16 | 已回填</p>

<div class="note-box">
<strong>说明：</strong>本文件为用户人工复核后的补全结果，已回填 derived_movies.csv。<br>
1. <strong>方言电影</strong>（8部）：惊梦魂、八廓南街16号、龙的深处、猎人与骷髅怪、穷人·榴莲·麻药·偷渡客、监狱建筑师、出花园、阿紫<br>
2. <strong>巴依尔的春节</strong>：撤销方言判定，改为普通话（非方言）<br>
3. <strong>不曾消失的台湾省</strong>：语言=台湾国语，非方言（不删除）<br>
4. <strong>其他</strong>：补全语言按"汉语普通话"或保留原值，均为非方言
</div>

<div class="stats-grid">
<div class="stat-card stat-dialect"><div class="num">8</div><div class="label">方言电影</div></div>
<div class="stat-card stat-nondialect"><div class="num">76</div><div class="label">非方言</div></div>
<div class="stat-card stat-total"><div class="num">84</div><div class="label">总计</div></div>
</div>

<div class="section-title">方言电影清单（8部）</div>
<div class="dialect-list">
<table>
<thead><tr><th>片名</th><th>年份</th><th>补全语言</th><th>地区</th><th>提取依据</th><th>备注</th></tr></thead>
<tbody>''']

    for mid in dialect_ids:
        row = df[df['movie_id'] == mid].iloc[0]
        html_parts.append(f'''<tr>
<td><a href="{row['豆瓣链接']}" target="_blank">{row['片名']}</a></td>
<td>{row['年份']}</td>
<td class="lang-dialect">{row['补全语言']}</td>
<td>{row['地区']}</td>
<td>{row['提取依据']}</td>
<td>{row['备注']}</td>
</tr>''')

    html_parts.append('''</tbody></table>
</div>

<div class="section-title">全量明细表（84部，可搜索/筛选）</div>
<div class="controls">
<input type="text" id="search" placeholder="搜索片名/导演/语言..." oninput="filterTable()">
<select id="filterLang" onchange="filterTable()">
<option value="">全部语言</option>''')

    for lang in sorted(df['补全语言'].unique()):
        html_parts.append(f'<option value="{lang}">{lang}</option>')

    html_parts.append('''</select>
</div>
<div class="table-wrap">
<table class="detail-table" id="mainTable">
<thead><tr>
<th>片名</th><th>年份</th><th>导演</th><th>类型</th><th>地区</th>
<th>补全语言</th><th>置信度</th><th>提取依据</th><th>备注</th><th>豆瓣</th>
</tr></thead>
<tbody>''')

    for _, row in df.iterrows():
        lang = str(row['补全语言'])
        dialect_langs = {'粤语', '藏语', '粤语/安徽方言/国语', '云南方言/普通话/缅语', '潮汕方言', '闽南语/普通话'}
        lang_cls = 'lang-dialect' if lang in dialect_langs else 'lang-nondialect'
        html_parts.append(f'''<tr>
<td>{row['片名']}</td>
<td>{row['年份']}</td>
<td>{row['导演']}</td>
<td>{row['类型']}</td>
<td>{row['地区']}</td>
<td class="{lang_cls}">{lang}</td>
<td>{row['置信度']}</td>
<td>{row['提取依据']}</td>
<td>{row['备注']}</td>
<td><a href="{row['豆瓣链接']}" target="_blank">链接</a></td>
</tr>''')

    html_parts.append('''</tbody></table>
</div>

<script>
function filterTable() {
    const search = document.getElementById('search').value.toLowerCase();
    const lang = document.getElementById('filterLang').value;
    const rows = document.querySelectorAll('#mainTable tbody tr');
    rows.forEach(r => {
        const text = r.innerText.toLowerCase();
        const langCell = r.cells[5]?.textContent || '';
        const matchSearch = !search || text.includes(search);
        const matchLang = !lang || langCell === lang;
        r.style.display = (matchSearch && matchLang) ? '' : 'none';
    });
}
</script>
</div>
</body></html>''')

    return ''.join(html_parts)


if __name__ == "__main__":
    main()
