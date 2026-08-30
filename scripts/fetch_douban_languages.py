# -*- coding: utf-8 -*-
"""Fetch Douban 语言 tags for untrusted publication rows.

Uses Douban mobile rexxar JSON (`languages`), which matches the subject-page
info-panel tags (e.g. 潮汕话 / 汉语普通话 / 泰语 / 英语). Resumes from a local
JSONL cache and writes successes to language_backfill_overrides.csv.

Usage:
  python scripts/fetch_douban_languages.py --only-china
  python scripts/fetch_douban_languages.py
  python scripts/fetch_douban_languages.py --limit 20 --delay 0.3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
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
from language_backfill_lib import (  # noqa: E402
    append_jsonl,
    languages_from_rexxar,
    load_jsonl_cache,
    write_overrides_csv,
)

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
)
BLOCK_STATUSES = {403, 418, 451}
# not_found is terminal: Douban has no subject. Retrying burns the IP quota.
DONE_CACHE_STATUSES = {"ok", "no_language", "not_found"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only-china", action="store_true", help="Fetch Region=China candidates only.")
    parser.add_argument("--limit", type=int, default=0, help="Max new requests this run (0 = no cap).")
    parser.add_argument("--delay", type=float, default=0.3, help="Seconds between HTTP requests.")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--max-consecutive-blocks",
        type=int,
        default=5,
        help="Stop the run after this many 403/418 in a row.",
    )
    return parser.parse_args()


def rexxar_url(kind: str, movie_id: str) -> str:
    return f"https://m.douban.com/rexxar/api/v2/{kind}/{movie_id}"


def fetch_json(url: str, movie_id: str, timeout: float) -> tuple[int, dict | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://m.douban.com/movie/subject/{movie_id}/",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return int(getattr(response, "status", 200) or 200), None
            return int(getattr(response, "status", 200) or 200), payload
    except urllib.error.HTTPError as exc:
        payload = None
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = None
        code = int(exc.code)
        if isinstance(payload, dict) and (
            payload.get("code") == 1309
            or "rate_limit" in str(payload.get("msg", "")).lower()
        ):
            return 429, payload
        return code, payload


def fetch_rexxar(movie_id: str, timeout: float, retries: int = 3) -> tuple[int, str, str]:
    """Return (http_status, language_string, status_tag).

    429 stops immediately so the IP can cool down; resume with the same command.
    """
    last_status = 0
    for attempt in range(retries):
        status, payload = fetch_json(rexxar_url("movie", movie_id), movie_id, timeout)
        if status == 429:
            return status, "", "rate_limited"
        if status in (400, 404) or (status == 200 and not isinstance(payload, dict)):
            alt, alt_payload = fetch_json(rexxar_url("tv", movie_id), movie_id, timeout)
            if alt == 429:
                return alt, "", "rate_limited"
            if alt == 200 and isinstance(alt_payload, dict):
                status, payload = alt, alt_payload
            elif alt in (400, 404):
                return alt, "", "not_found"
        last_status = status
        if status in BLOCK_STATUSES:
            return status, "", "blocked"
        if status == 200 and isinstance(payload, dict):
            lang = languages_from_rexxar(payload)
            if lang:
                return status, lang, "ok"
            return status, "", "no_language"
        if last_status in (400, 404):
            return last_status, "", "not_found"
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    if last_status in (400, 404):
        return last_status, "", "not_found"
    return last_status, "", "blocked"


def cache_is_done(record: dict | None) -> bool:
    if not record:
        return False
    return str(record.get("status", "")) in DONE_CACHE_STATUSES


def write_overrides(cache: dict[str, dict]) -> int:
    return write_overrides_csv(cache, LANGUAGE_BACKFILL_OVERRIDES)


def main() -> None:
    args = parse_args()
    if not LANGUAGE_BACKFILL_CANDIDATES.is_file():
        raise SystemExit(
            f"Missing {LANGUAGE_BACKFILL_CANDIDATES}. Run scripts/list_untrusted_languages.py first."
        )
    candidates = pd.read_csv(
        LANGUAGE_BACKFILL_CANDIDATES,
        encoding="utf-8-sig",
        dtype={"movie_id": "str"},
    )
    if args.only_china:
        candidates = candidates[candidates["Region"].astype(str) == "China"].copy()
    cache = load_jsonl_cache(LANGUAGE_BACKFILL_CACHE)
    pending = []
    for rec in candidates.to_dict("records"):
        movie_id = str(rec.get("movie_id", "") or "").strip()
        if not movie_id or cache_is_done(cache.get(movie_id)):
            continue
        pending.append(rec)
    print(
        f"Candidates in scope: {len(candidates):,}; "
        f"cache hits: {len(candidates) - len(pending):,}; pending: {len(pending):,}"
    )
    consecutive_blocks = 0
    fetched = 0
    for rec in pending:
        if args.limit and fetched >= args.limit:
            print(f"Reached --limit {args.limit}")
            break
        movie_id = str(rec["movie_id"])
        status_code, lang, tag = fetch_rexxar(movie_id, args.timeout)
        fetched += 1
        fetched_at = datetime.now(timezone.utc).isoformat()
        record = {
            "movie_id": movie_id,
            "status": tag,
            "语言": lang,
            "http_status": status_code,
            "fetched_at": fetched_at,
            "source": "douban_rexxar",
        }
        cache[movie_id] = record
        append_jsonl(LANGUAGE_BACKFILL_CACHE, record)
        title = str(rec.get("片名", "") or "").encode("utf-8", "replace").decode("utf-8")
        line = f"[{fetched}/{len(pending)}] {movie_id} {title} -> {tag} {lang!r}"
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode("gbk", "replace").decode("gbk"), flush=True)
        if tag == "rate_limited":
            remaining = len(pending) - fetched
            print(
                f"Stopping on 429. Remaining pending: {remaining:,}. "
                "Re-run the same command to resume after cooldown.",
                flush=True,
            )
            break
        if tag == "blocked":
            consecutive_blocks += 1
            if consecutive_blocks >= args.max_consecutive_blocks:
                remaining = len(pending) - fetched
                print(
                    f"Stopping after consecutive anti-bot responses. "
                    f"Remaining pending: {remaining:,}. Cache kept for resume.",
                    flush=True,
                )
                break
            time.sleep(max(args.delay, 2.0))
            continue
        consecutive_blocks = 0
        if tag == "not_found":
            time.sleep(max(args.delay, 1.0))
            continue
        time.sleep(args.delay)

    n_overrides = write_overrides(cache)
    ok = sum(1 for row in cache.values() if row.get("status") == "ok" and str(row.get("语言", "")).strip())
    blocked = sum(1 for row in cache.values() if row.get("status") == "blocked")
    missing = sum(1 for row in cache.values() if row.get("status") == "no_language")
    not_found = sum(1 for row in cache.values() if row.get("status") == "not_found")
    still_pending = sum(
        1
        for rec in pending
        if not cache_is_done(cache.get(str(rec.get("movie_id", "") or "").strip()))
    )
    print(
        f"Cache ok={ok} no_language={missing} not_found={not_found} "
        f"blocked={blocked}; overrides={n_overrides}"
    )
    print(f"China-scope still pending (retryable): {still_pending:,}")
    print(f"Wrote {LANGUAGE_BACKFILL_OVERRIDES}")


if __name__ == "__main__":
    main()
