# -*- coding: utf-8 -*-
"""Fill remaining language gaps from Wikidata P364 (Douban ID = P4529).

Used only when Douban rexxar is rate-limited. Maps Wikidata language labels
to Douban-style tags. Does not invent dialect tags that Wikidata does not have.

Usage:
  python scripts/fetch_wikidata_languages.py --only-china
  python scripts/fetch_wikidata_languages.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import (  # noqa: E402
    LANGUAGE_BACKFILL_CACHE,
    LANGUAGE_BACKFILL_CANDIDATES,
    LANGUAGE_BACKFILL_OVERRIDES,
)
from language_backfill_lib import append_jsonl, load_jsonl_cache, write_overrides_csv  # noqa: E402

SPARQL = "https://query.wikidata.org/sparql"
QLEVER = "https://qlever.dev/api/wikidata"
BATCH = 25
LABEL_MAP = {
    "现代标准汉语": "汉语普通话",
    "官话": "汉语普通话",
    "普通话": "汉语普通话",
    "汉语": "汉语普通话",
    "Standard Chinese": "汉语普通话",
    "Mandarin Chinese": "汉语普通话",
    "Chinese": "汉语普通话",
    "粤语": "粤语",
    "Yue Chinese": "粤语",
    "Cantonese": "粤语",
    "吴语": "吴语",
    "Wu Chinese": "吴语",
    "闽南语": "闽南语",
    "Min Nan": "闽南语",
    "Southern Min": "闽南语",
    "客家话": "客家话",
    "Hakka Chinese": "客家话",
    "四川话": "四川话",
    "Sichuanese": "四川话",
    "日语": "日语",
    "Japanese": "日语",
    "韩语": "韩语",
    "朝鲜语": "朝鲜语",
    "Korean": "韩语",
    "英语": "英语",
    "English": "英语",
    "法语": "法语",
    "French": "法语",
    "德语": "德语",
    "German": "德语",
    "西班牙语": "西班牙语",
    "Spanish": "西班牙语",
    "意大利语": "意大利语",
    "Italian": "意大利语",
    "俄语": "俄语",
    "Russian": "俄语",
    "葡萄牙语": "葡萄牙语",
    "Portuguese": "葡萄牙语",
    "藏语": "藏语",
    "Tibetan": "藏语",
    "维吾尔语": "维吾尔语",
    "Uyghur": "维吾尔语",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-china", action="store_true")
    parser.add_argument(
        "--dump",
        action="store_true",
        help="One SPARQL dump (year>=2018 P4529+P364) then join locally; fewer 429s than batched VALUES.",
    )
    parser.add_argument(
        "--dump-all",
        action="store_true",
        help="QLever dump of all P4529+P364 (no date filter) then join locally.",
    )
    parser.add_argument("--delay", type=float, default=1.0)
    return parser.parse_args()


def map_label(label: str) -> str:
    text = (label or "").strip()
    if not text:
        return ""
    if text in LABEL_MAP:
        return LABEL_MAP[text]
    return text


def _http_json(url: str, timeout: float = 120.0, data: bytes | None = None, headers: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers
        or {
            "User-Agent": "movie-rating-data-story language-backfill/1.0 (research)",
            "Accept": "application/sparql-results+json",
        },
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _bindings_to_map(payload: dict) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    for row in payload.get("results", {}).get("bindings", []):
        mid = row.get("douban", {}).get("value", "")
        label = map_label(row.get("langLabel", {}).get("value", ""))
        if not mid:
            continue
        found.setdefault(mid, [])
        if label and label not in found[mid]:
            found[mid].append(label)
    return {mid: " / ".join(tags) for mid, tags in found.items() if tags}


def sparql_languages(ids: list[str]) -> dict[str, str]:
    values = " ".join(f'"{mid}"' for mid in ids)
    query = f"""
    SELECT ?douban ?langLabel WHERE {{
      VALUES ?douban {{ {values} }}
      ?item wdt:P4529 ?douban .
      OPTIONAL {{ ?item wdt:P364 ?lang . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
    }}
    """
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    payload = _http_json(
        SPARQL,
        timeout=90,
        data=body,
        headers={
            "User-Agent": "movie-rating-data-story language-backfill/1.0 (research)",
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    return _bindings_to_map(payload)


def sparql_dump_year(year: int) -> dict[str, str]:
    query = f"""
    SELECT ?douban ?langLabel WHERE {{
      ?item wdt:P4529 ?douban .
      ?item wdt:P364 ?lang .
      ?item wdt:P577 ?date .
      FILTER(YEAR(?date) = {year})
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
    }}
    """
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    payload = _http_json(
        SPARQL,
        timeout=180,
        data=body,
        headers={
            "User-Agent": "movie-rating-data-story language-backfill/1.0 (research)",
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    return _bindings_to_map(payload)


def qlever_dump(since: str | None = "2018-01-01T00:00:00Z") -> dict[str, str]:
    date_lines = ""
    if since:
        date_lines = f"""
      ?item wdt:P577 ?date .
      FILTER (?date >= "{since}"^^xsd:dateTime)
"""
    query = f"""
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?douban ?langLabel WHERE {{
      ?item wdt:P4529 ?douban .
      ?item wdt:P364 ?lang .
      {date_lines}
      ?lang rdfs:label ?langLabel .
      FILTER (LANG(?langLabel) = "zh" || LANG(?langLabel) = "en")
    }}
    """
    body = urllib.parse.urlencode({"query": query}).encode("utf-8")
    payload = _http_json(
        QLEVER,
        timeout=180,
        data=body,
        headers={
            "User-Agent": "movie-rating-data-story language-backfill/1.0 (research)",
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    return _bindings_to_map(payload)


def rewrite_overrides(cache: dict[str, dict]) -> None:
    write_overrides_csv(cache, LANGUAGE_BACKFILL_OVERRIDES)


def main() -> None:
    args = parse_args()
    candidates = pd.read_csv(LANGUAGE_BACKFILL_CANDIDATES, dtype={"movie_id": "str"})
    if args.only_china:
        candidates = candidates[candidates["Region"].astype(str) == "China"]
    cache = load_jsonl_cache(LANGUAGE_BACKFILL_CACHE)
    pending = [
        str(mid)
        for mid in candidates["movie_id"].astype(str)
        if cache.get(str(mid), {}).get("status") not in {"ok", "no_language"}
    ]
    print(f"Wikidata pending: {len(pending):,}")
    fetched_at = datetime.now(timezone.utc).isoformat()
    filled = 0

    if args.dump or args.dump_all:
        mapped: dict[str, str] = {}
        try:
            mapped = qlever_dump(None if args.dump_all else "2018-01-01T00:00:00Z")
            print(f"qlever dump rows: {len(mapped):,}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"qlever failed: {exc}", flush=True)
        if not mapped:
            for year in range(2018, 2027):
                try:
                    year_map = sparql_dump_year(year)
                except Exception as exc:  # noqa: BLE001
                    print(f"year {year} failed: {exc}", flush=True)
                    time.sleep(8)
                    continue
                print(f"year {year}: {len(year_map):,}", flush=True)
                mapped.update(year_map)
                time.sleep(2)
        print(f"dump rows with language: {len(mapped):,}")
        for mid in pending:
            lang = mapped.get(mid, "")
            if not lang or cache.get(mid, {}).get("status") == "ok":
                continue
            record = {
                "movie_id": mid,
                "status": "ok",
                "语言": lang,
                "http_status": 200,
                "fetched_at": fetched_at,
                "source": "wikidata_p364",
            }
            cache[mid] = record
            append_jsonl(LANGUAGE_BACKFILL_CACHE, record)
            filled += 1
        print(f"dump filled {filled} of {len(pending):,}", flush=True)
    else:
        for offset in range(0, len(pending), BATCH):
            chunk = pending[offset: offset + BATCH]
            try:
                mapped = sparql_languages(chunk)
            except Exception as exc:  # noqa: BLE001
                print(f"batch {offset} failed: {exc}", flush=True)
                time.sleep(65 if "429" in str(exc) else 2)
                continue
            for mid in chunk:
                lang = mapped.get(mid, "")
                if not lang:
                    continue
                if cache.get(mid, {}).get("status") == "ok":
                    continue
                record = {
                    "movie_id": mid,
                    "status": "ok",
                    "语言": lang,
                    "http_status": 200,
                    "fetched_at": fetched_at,
                    "source": "wikidata_p364",
                }
                cache[mid] = record
                append_jsonl(LANGUAGE_BACKFILL_CACHE, record)
                filled += 1
            print(f"  {offset + len(chunk)}/{len(pending)} filled+={filled}", flush=True)
            time.sleep(args.delay)
    rewrite_overrides(cache)
    print(f"Wikidata filled {filled}; overrides {LANGUAGE_BACKFILL_OVERRIDES}")


if __name__ == "__main__":
    main()
