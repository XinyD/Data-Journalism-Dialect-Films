"""Portable paths for the standalone dialect-movie data story."""

import os
import stat
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DERIVED_MOVIES_INFO = DATA_DIR / "cleaned" / "derived_movies.csv"
DERIVED_COMMENTS = DATA_DIR / "derived_comments.csv"
AGGREGATED_STATS = DATA_DIR / "aggregated_stats.json"
SAMPLE_MANIFEST = DATA_DIR / "cleaned" / "sample_manifest.json"
FRONTEND_DATASET = DATA_DIR / "frontend_dataset.json"
MOVIE_DETAILS_DIR = DATA_DIR / "frontend" / "details"
PARTICLES_DATASET = DATA_DIR / "frontend" / "particles.json"
GEO_ENRICHMENT = DATA_DIR / "frontend" / "geo_enrichment.json"
NARRATIVE_FACTS = DATA_DIR / "narrative_facts.json"
REPORT_DATA_STRICT = DATA_DIR / "dialect_films" / "report_data_strict.json"
DIALECT_DETAIL_CSV = DATA_DIR / "dialect_films" / "方言片明细报告.csv"
DIALECT_DETAIL_HTML = BASE_DIR / "方言片详细报告.html"
STORY_UNIVERSE = BASE_DIR / "frontend" / "data" / "story_universe.json"
# 方言叙事聚合载荷（byDecade/yearly/typeCtl/canto/global/director/genreAvg 等，
# 口径固化自 scripts/sync_preview_dialect_v43_20260819.py，见 data_aggregator.build_dialect_aggregates）
DIALECT_AGGREGATES = DATA_DIR / "frontend" / "dialect_aggregates.json"

# Optional only: place an upstream table here when intentionally rebuilding the
# 63,025-film publication snapshot after canonical identity deduplication.
SOURCE_MOVIES_INFO = Path(
    os.getenv(
        "MOVIE_STORY_SOURCE",
        DATA_DIR / "source" / "movies_info.csv",
    )
)

# 合并后的原始数据（delivery_20260817 + movies_info.csv）
SOURCE_MOVIES_MERGED = DATA_DIR / "source" / "movies_info_merged.csv"

# delivery_20260817 交付包路径
DELIVERY_DIR = DATA_DIR / "delivery_20260817" / "data"
DELIVERY_MOVIES_CSV = DELIVERY_DIR / "douban_movies_2020_2026.csv"
DELIVERY_COMMENTS_CSV = DELIVERY_DIR / "douban_comments_2020_2026.csv"

# 清洗后短评数据
DERIVED_COMMENTS_CLEAN = DATA_DIR / "cleaned" / "douban_comments_clean.csv"

# 2020–2026 语言回填（delivery 缺列）：候选清单入库、抓取缓存本地、overrides 入库
LANGUAGE_BACKFILL_CANDIDATES = DATA_DIR / "cleaned" / "language_backfill_candidates.csv"
LANGUAGE_BACKFILL_CACHE = DATA_DIR / "cleaned" / "language_backfill_cache.jsonl"
LANGUAGE_BACKFILL_OVERRIDES = DATA_DIR / "cleaned" / "language_backfill_overrides.csv"

# Import-time mkdir so a fresh checkout can write details shards without a separate bootstrap.
for directory in (DATA_DIR, MOVIE_DETAILS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def atomic_write_text(path: Path, text: str) -> None:
    """Replace ``path`` via a temp file; clear the Windows read-only bit if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    try:
        temporary.replace(path)
    except PermissionError:
        if path.exists():
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            temporary.replace(path)
        else:
            raise
