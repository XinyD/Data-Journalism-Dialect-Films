# -*- coding: utf-8 -*-
"""Shared helpers for 2020–2026 Douban language backfill."""
from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

import pandas as pd

DELIVERY_SOURCE = "douban_delivery_20260817"
AMA_MOVIE_ID = "37116446"
YINRUCHENYAN_MOVIE_ID = "35131346"
PROTECTED_MOVIE_IDS = frozenset({AMA_MOVIE_ID, YINRUCHENYAN_MOVIE_ID})
PROTECTED_EVIDENCE_MARKERS = ("LANG_FIX_20260819", "LANG_FIX_20260830")
CANDIDATE_REASONS = (
    "delivery_empty",
    "delivery_default_mandarin",
    "empty_other",
)

_EMPTY_LANG = frozenset({"", "nan", "none", "null", "<na>"})
_LANG_SPAN_RE = re.compile(
    r'<span class="pl">\s*语言\s*:</span>\s*(.+?)<br\s*/?>',
    re.IGNORECASE | re.DOTALL,
)
_LANG_SPAN_ALT_RE = re.compile(
    r'<span class="pl">\s*语言\s*:</span>\s*([^<]+)',
    re.IGNORECASE,
)


def languages_from_rexxar(payload: object) -> str:
    """Join Douban rexxar `languages` list into the slash-separated info-panel form."""
    if not isinstance(payload, dict):
        return ""
    tags = payload.get("languages")
    if not isinstance(tags, list):
        return ""
    parts = [normalize_fetched_language(str(tag)) for tag in tags if str(tag).strip()]
    parts = [part for part in parts if part]
    return " / ".join(parts)


def is_empty_language(value: object) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    return str(value).strip().casefold() in _EMPTY_LANG


def _evidence_text(row: pd.Series) -> str:
    if "Dialect_Evidence" not in row.index:
        return ""
    value = row.get("Dialect_Evidence", "")
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def is_protected_language_row(row: pd.Series) -> bool:
    if str(row.get("movie_id", "") or "").strip() in PROTECTED_MOVIE_IDS:
        return True
    evidence = _evidence_text(row)
    return any(marker in evidence for marker in PROTECTED_EVIDENCE_MARKERS)


def candidate_reason(row: pd.Series) -> str | None:
    """Return why this publication row's language is untrusted, or None."""
    if is_protected_language_row(row):
        return None
    source = str(row.get("数据来源", "") or "").strip()
    lang = row.get("语言", "")
    empty = is_empty_language(lang)
    if source == DELIVERY_SOURCE:
        if empty:
            return "delivery_empty"
        if str(lang).strip() == "汉语普通话":
            return "delivery_default_mandarin"
        return None
    year = pd.to_numeric(row.get("年份"), errors="coerce")
    if empty and pd.notna(year) and 2020 <= int(year) <= 2026:
        return "empty_other"
    return None


def subject_url(row: pd.Series) -> str:
    url = str(row.get("来源URL", "") or "").strip()
    if "/subject/" in url:
        return url if url.endswith("/") else url + "/"
    movie_id = str(row.get("movie_id", "") or "").strip()
    if movie_id and movie_id.lower() not in _EMPTY_LANG:
        return f"https://movie.douban.com/subject/{movie_id}/"
    return ""


def normalize_fetched_language(raw: str) -> str:
    text = html_lib.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s*\|\s*", " / ", text)
    return text.strip(" /")


def parse_language_from_plaintext(text: str) -> str:
    """Pull a 语言 field out of Douban HTML or Exa markdown."""
    if not text:
        return ""
    match = re.search(r"语言[:：]\s*([^\n<]+)", text)
    if not match:
        return ""
    raw = match.group(1)
    raw = re.split(r"上映日期|片长|又名|IMDb|IMDB", raw, maxsplit=1)[0]
    return normalize_fetched_language(raw)


def parse_douban_language(page_html: str) -> str:
    """Extract the Douban info-panel 语言 field from a subject HTML page."""
    if not page_html:
        return ""
    match = _LANG_SPAN_RE.search(page_html) or _LANG_SPAN_ALT_RE.search(page_html)
    if match:
        parsed = normalize_fetched_language(match.group(1))
        if parsed:
            return parsed
    return parse_language_from_plaintext(page_html)


def load_jsonl_cache(path: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not path.is_file():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            movie_id = str(row.get("movie_id", "") or "").strip()
            if movie_id:
                records[movie_id] = row
    return records


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def override_source(record: dict) -> str:
    """Prefer an explicit source; unlabeled ok rows are Douban rexxar fetches."""
    source = str(record.get("source") or "").strip()
    if source:
        return source
    return "douban_rexxar"


def write_overrides_csv(cache: dict[str, dict], path: Path) -> int:
    rows = []
    for movie_id, record in sorted(cache.items()):
        if record.get("status") != "ok":
            continue
        lang = str(record.get("语言", "") or "").strip()
        if not lang:
            continue
        rows.append({
            "movie_id": movie_id,
            "语言": lang,
            "fetched_at": record.get("fetched_at", ""),
            "http_status": record.get("http_status", ""),
            "source": override_source(record),
        })
    frame = pd.DataFrame(rows, columns=["movie_id", "语言", "fetched_at", "http_status", "source"])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return len(frame)
