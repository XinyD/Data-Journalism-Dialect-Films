"""Frozen v4.6 publication baseline counts (Douban language backfill + 隐入尘烟).

Imported by tests, verify_freeze_readiness.py, and replay_v44_baseline.py so a
caliber change only needs one edit. Region still uses v4.5 first-listed country;
language/dialect counts reflect 2026-08-30 Douban 语言 backfill (Wikidata P364
fills Language_Code gaps only and does not mint China dialect rows), plus the
manual LANG_FIX_20260830 for 《隐入尘烟》(35131346).
"""

PUBLICATION_RECORDS = 63_025
CHINA_DIALECT = 3067
CHINA_MANDARIN = 9724
CHINA_TOTAL = CHINA_DIALECT + CHINA_MANDARIN  # 12,791
TIER1_PURE = 2303
TIER2A_DIALECT_FIRST = 418
TIER2B_MANDARIN_FIRST = 346
TIER2B_EXCLUDED = 354
TIER_BASELINE = (CHINA_DIALECT, TIER1_PURE, TIER2A_DIALECT_FIRST, TIER2B_MANDARIN_FIRST)
OPERA_CONCERT_EXCLUDED = 49
AUDIT_EXCLUDED = 22
PLAN_A_EXCLUDED = 56
DIALECT_ALL_REGIONS = 3360
F7_PYONGYANG_MOVIE_ID = "10478122"
