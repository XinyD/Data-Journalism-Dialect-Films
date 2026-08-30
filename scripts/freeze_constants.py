"""Frozen v4.7 publication baseline counts (partial Douban 语言 backfill).

Imported by tests, verify_freeze_readiness.py, and replay_v44_baseline.py so a
caliber change only needs one edit. Region still uses v4.5 first-listed country.
Language/dialect counts reflect Douban 语言 tags fetched by 2026-08-30; remaining
unfetched China delivery rows stay default 汉语普通话 with EMPTY_LANG_DEFAULTED.
Wikidata P364 fills Language_Code gaps only and does not mint China dialect rows.
2026-08-30 patch: 乐山话 whitelist recovers 《椒麻堂会》; E8 list excludes
《万千星辉颁奖典礼 2020》. China dialect n stays 3076.
"""

PUBLICATION_RECORDS = 63_025
CHINA_DIALECT = 3076
CHINA_MANDARIN = 9715
CHINA_TOTAL = CHINA_DIALECT + CHINA_MANDARIN  # 12,791
TIER1_PURE = 2309
TIER2A_DIALECT_FIRST = 421
TIER2B_MANDARIN_FIRST = 346
TIER2B_EXCLUDED = 354
TIER_BASELINE = (CHINA_DIALECT, TIER1_PURE, TIER2A_DIALECT_FIRST, TIER2B_MANDARIN_FIRST)
OPERA_CONCERT_EXCLUDED = 50
AUDIT_EXCLUDED = 22
PLAN_A_EXCLUDED = 56
DIALECT_ALL_REGIONS = 3369
F7_PYONGYANG_MOVIE_ID = "10478122"
