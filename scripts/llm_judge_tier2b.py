# -*- coding: utf-8 -*-
"""
Tier 2b 灰区 LLM 补判管线（v4.1，2026-08-15）。

对 score_tier2b.py 产出的 gray_zone 影片（含强制复核的标杆片）逐部补判：
- --export（默认/无 API key）：导出 data/tier2b_gray_zone_review.csv
  （含 movie_id/片名/年份/导演/语言/简介/Gemini评价/来源URL 及待填列
  final_decision/confidence/reason），供 LLM 批量判定或人工逐部回填。
- --api：若设置 GEMINI_API_KEY，则逐部调用 Gemini API 生成
  yes/no/uncertain + 置信度 + 理由，直接写入判定文件。
- --apply <csv>：读取已回填的判定 CSV，生成最终白名单
  data/tier2b_recovered.csv（verdict=yes 的影片），并把全部补判结论
  （含 no/uncertain）追加进 data/review_queue.csv 溯源。
  置信度低于 CONFIDENCE_THRESHOLD 的 yes 判定强制标记 human_review_required=1
  （标杆片一律 human_review_required=1，需人工确认后才算终态）。

用法：
    py scripts/llm_judge_tier2b.py --export
    py scripts/llm_judge_tier2b.py --apply data/tier2b_gray_zone_review.csv
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
EVIDENCE = BASE / "data" / "tier2b_evidence.csv"
SRC = BASE / "data" / "cleaned" / "derived_movies.csv"
REVIEW_CSV = BASE / "data" / "tier2b_gray_zone_review.csv"
RECOVERED_CSV = BASE / "data" / "tier2b_recovered.csv"
REVIEW_QUEUE = BASE / "data" / "cleaned" / "review_queue.csv"

sys.path.insert(0, str(Path(__file__).resolve().parent))

CONFIDENCE_THRESHOLD = 0.7
API_MODEL = "gemini-2.0-flash"
API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{API_MODEL}:generateContent?key=")

PROMPT_TEMPLATE = """你是方言电影研究助理。判断以下中国影片是否属于"方言电影"：
影片对白中中国境内语言变体（汉语方言或少数民族语言）成规模出现（非仅一两句点缀）。
影片信息：
片名：{title}（{year}）
导演：{director}
豆瓣语言标签：{lang}
剧情简介：{synopsis}
已有评语：{gemini}
只输出 JSON：{{"verdict": "yes|no|uncertain", "confidence": 0到1小数, "reason": "30字内中文理由"}}"""


def load_gray_zone():
    rows = list(csv.DictReader(open(EVIDENCE, encoding="utf-8-sig")))
    return [r for r in rows if r["verdict"] == "gray_zone"]


def load_details(ids):
    detail = {}
    for r in csv.DictReader(open(SRC, encoding="utf-8-sig")):
        if r["movie_id"] in ids:
            detail[r["movie_id"]] = r
    return detail


def export_review() -> None:
    gray = load_gray_zone()
    detail = load_details({r["movie_id"] for r in gray})
    fieldnames = ["movie_id", "片名", "年份", "导演", "语言", "制片国家/地区",
                  "豆瓣评分", "评价人数", "benchmark", "score", "hits",
                  "剧情简介_前200", "Gemini评价", "来源URL",
                  "final_decision", "confidence", "reason"]
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in sorted(gray, key=lambda x: -int(float(x["评价人数"] or 0))):
            d = detail.get(r["movie_id"], {})
            w.writerow({
                **{k: r.get(k, "") for k in
                   ["movie_id", "片名", "年份", "导演", "语言", "制片国家/地区",
                    "豆瓣评分", "评价人数", "benchmark", "score", "hits", "来源URL"]},
                "剧情简介_前200": str(d.get("剧情简介") or "")[:200],
                "Gemini评价": str(d.get("Gemini评价") or ""),
                "final_decision": "", "confidence": "", "reason": "",
            })
    print(f"灰区 {len(gray)} 部已导出: {REVIEW_CSV}")
    print("请回填 final_decision(yes/no/uncertain)/confidence/reason 后运行 --apply")


def judge_via_api(row, detail) -> dict:
    d = detail.get(row["movie_id"], {})
    prompt = PROMPT_TEMPLATE.format(
        title=row["片名"], year=row["年份"], director=row["导演"],
        lang=row["语言"], synopsis=str(d.get("剧情简介") or "")[:300],
        gemini=str(d.get("Gemini评价") or "")[:200])
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0}}).encode("utf-8")
    req = urllib.request.Request(
        API_URL + os.environ["GEMINI_API_KEY"], data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    text = text[text.find("{"):text.rfind("}") + 1]
    return json.loads(text)


def run_api() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("未设置 GEMINI_API_KEY，请改用 --export 走离线回填路径")
    gray = load_gray_zone()
    detail = load_details({r["movie_id"] for r in gray})
    for i, r in enumerate(gray, 1):
        try:
            j = judge_via_api(r, detail)
        except Exception as e:  # noqa: BLE001
            j = {"verdict": "uncertain", "confidence": 0, "reason": f"API错误:{e}"}
        print(f"[{i}/{len(gray)}] {r['片名']} → {j['verdict']} ({j['confidence']})")


def apply_judgments(path: str) -> None:
    judged = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    judged = [r for r in judged if (r.get("final_decision") or "").strip()]
    recovered, queue_rows = [], []
    for r in judged:
        decision = r["final_decision"].strip().lower()
        try:
            conf = float(r.get("confidence") or 0)
        except ValueError:
            conf = 0.0
        bench = r.get("benchmark") == "1"
        human_required = "1" if (bench or conf < CONFIDENCE_THRESHOLD) else "0"
        source = "BENCHMARK" if bench else "LLM_JUDGE"
        if decision == "yes":
            recovered.append({
                "movie_id": r["movie_id"], "片名": r["片名"], "年份": r["年份"],
                "语言": r["语言"], "evidence": source,
                "confidence": r.get("confidence", ""),
                "human_review_required": human_required,
                "reason": r.get("reason", ""),
            })
        queue_rows.append({
            "movie_id": r["movie_id"], "片名": r["片名"], "年份": r["年份"],
            "语言": r["语言"],
            "处置": "tier2b补回" if decision == "yes" else "tier2b默认排除",
            "原因": f"{source} 判定 {decision}(conf={r.get('confidence', '')}): "
                    f"{r.get('reason', '')}",
            "审计日期": "2026-08-15",
            "依据": "v4.1 Tier2b 证据漏斗（score_tier2b.py + llm_judge_tier2b.py）",
            "来源": "scripts/llm_judge_tier2b.py",
        })

    fieldnames = ["movie_id", "片名", "年份", "语言", "evidence", "confidence",
                  "human_review_required", "reason"]
    with RECOVERED_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(recovered)
    print(f"补回白名单 {len(recovered)} 部 → {RECOVERED_CSV}")

    # 全部补判结论进复核队列溯源（追加；review_queue.csv 表头 12 列对齐）
    with REVIEW_QUEUE.open("a", encoding="utf-8-sig", newline="") as f:
        with REVIEW_QUEUE.open(encoding="utf-8-sig") as rf:
            existing_fields = next(csv.reader(rf), None)
        assert existing_fields, "review_queue.csv 为空，请先确认表头"
        w = csv.DictWriter(f, fieldnames=existing_fields, extrasaction="ignore")
        for row in queue_rows:
            row_full = dict.fromkeys(existing_fields, "")
            row_full.update(row)
            w.writerow(row_full)
    print(f"补判结论 {len(queue_rows)} 条已追加 → {REVIEW_QUEUE}")
    n_human = sum(1 for x in recovered if x["human_review_required"] == "1")
    print(f"其中强制人工复核（标杆/低置信）: {n_human} 部")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true", help="导出灰区复核 CSV")
    parser.add_argument("--api", action="store_true", help="调用 Gemini API 逐部判定")
    parser.add_argument("--apply", metavar="CSV", help="应用已回填的判定 CSV")
    args = parser.parse_args()
    if args.apply:
        apply_judgments(args.apply)
    elif args.api:
        run_api()
    else:
        export_review()


if __name__ == "__main__":
    main()
