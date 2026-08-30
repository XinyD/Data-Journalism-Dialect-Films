# -*- coding: utf-8 -*-
"""Append language tags parsed from Douban page text into the backfill cache.

Usage:
  python scripts/ingest_language_plaintext.py mapping.json
where mapping.json is {movie_id: page_text_or_language_line}.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import LANGUAGE_BACKFILL_CACHE, LANGUAGE_BACKFILL_OVERRIDES  # noqa: E402
from language_backfill_lib import (  # noqa: E402
    append_jsonl,
    load_jsonl_cache,
    parse_language_from_plaintext,
    write_overrides_csv,
)


def ingest(mapping: dict[str, str]) -> tuple[int, int]:
    ok = skipped = 0
    fetched_at = datetime.now(timezone.utc).isoformat()
    for movie_id, text in mapping.items():
        movie_id = str(movie_id).strip()
        lang = parse_language_from_plaintext(text)
        if not lang and text and " / " in text and "语言" not in text and len(text) < 80:
            lang = text.strip()
        if not movie_id:
            continue
        if not lang:
            skipped += 1
            record = {
                "movie_id": movie_id,
                "status": "no_language",
                "语言": "",
                "http_status": 200,
                "fetched_at": fetched_at,
                "error": "plaintext_miss",
            }
        else:
            ok += 1
            record = {
                "movie_id": movie_id,
                "status": "ok",
                "语言": lang,
                "http_status": 200,
                "fetched_at": fetched_at,
                "source": "douban_page",
            }
        append_jsonl(LANGUAGE_BACKFILL_CACHE, record)
    cache = load_jsonl_cache(LANGUAGE_BACKFILL_CACHE)
    write_overrides_csv(cache, LANGUAGE_BACKFILL_OVERRIDES)
    return ok, skipped


def main() -> None:
    path = Path(sys.argv[1])
    mapping = json.loads(path.read_text(encoding="utf-8"))
    ok, skipped = ingest(mapping)
    print(f"ingested ok={ok} skipped={skipped} -> {LANGUAGE_BACKFILL_OVERRIDES}")


if __name__ == "__main__":
    main()
