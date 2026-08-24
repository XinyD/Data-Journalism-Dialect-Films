"""Frozen v4.5 publication baseline counts (first-listed production country).

Imported by tests, verify_freeze_readiness.py, and replay_v44_baseline.py so a
caliber change only needs one edit. Dialect/Tier counts match v4.4; China and
Mandarin totals reflect the v4.5 region recode.
"""

PUBLICATION_RECORDS = 63_025
CHINA_DIALECT = 3045
CHINA_MANDARIN = 9746
CHINA_TOTAL = CHINA_DIALECT + CHINA_MANDARIN  # 12,791
TIER1_PURE = 2289
TIER2A_DIALECT_FIRST = 410
TIER2B_MANDARIN_FIRST = 346
TIER2B_EXCLUDED = 354
TIER_BASELINE = (CHINA_DIALECT, TIER1_PURE, TIER2A_DIALECT_FIRST, TIER2B_MANDARIN_FIRST)
OPERA_CONCERT_EXCLUDED = 49
AUDIT_EXCLUDED = 22
PLAN_A_EXCLUDED = 54
DIALECT_ALL_REGIONS = 3338
F7_PYONGYANG_MOVIE_ID = "10478122"
