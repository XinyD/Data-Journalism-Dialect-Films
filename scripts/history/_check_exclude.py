"""Check exclude list films in current data."""
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dialect_defs import DIALECT_AUDIT_EXCLUDE_MOVIE_IDS

df = pd.read_csv(ROOT / "data" / "cleaned" / "derived_movies.csv",
                 encoding="utf-8-sig", dtype={"movie_id": "str"}, low_memory=False)

print(f"Total rows: {len(df)}")
print(f"Exclude list: {len(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS)} IDs")

for mid in sorted(DIALECT_AUDIT_EXCLUDE_MOVIE_IDS):
    rows = df[df["movie_id"] == mid]
    if len(rows) == 1:
        r = rows.iloc[0]
        lang_col = "语言"
        lang = str(r[lang_col]) if pd.notna(r[lang_col]) else "(empty)"
        print(f"  {mid:12s} Region={r['Region']:15s} D={int(r['Is_Dialect'])} Lang={lang[:50]}")
    else:
        print(f"  {mid:12s} NOT IN DATA ({len(rows)} rows)")
