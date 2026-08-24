# -*- coding: utf-8 -*-
"""Check current values in key data files."""
import json
import pandas as pd
from pathlib import Path

BASE = Path("d:/movie-rating-data-story-main/dialect-movie-data-story-main")
DATA = BASE / "data"

# Check report_data_strict.json
report_path = DATA / "dialect_films" / "report_data_strict.json"
if report_path.exists():
    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    print("report_data_strict.json:")
    print(f"  total_chinese_films: {report_data.get('total_chinese_films', 'N/A')}")
    print(f"  dialect_films_count: {report_data.get('dialect_films_count', 'N/A')}")
    print(f"  tier1_count: {report_data.get('tier1_count', 'N/A')}")
    print(f"  tier2a_count: {report_data.get('tier2a_count', 'N/A')}")
    print(f"  tier2b_count: {report_data.get('tier2b_count', 'N/A')}")
else:
    print("report_data_strict.json not found")

# Check narrative_facts.json
narrative_path = DATA / "narrative_facts.json"
if narrative_path.exists():
    with open(narrative_path, 'r', encoding='utf-8') as f:
        narrative_data = json.load(f)
    print("\nnarrative_facts.json:")
    print(f"  languages keys: {list(narrative_data.get('languages', {}).keys())}")
    print(f"  languages Chinese: {narrative_data.get('languages', {}).get('Chinese', 'N/A')}")
    print(f"  languages 普通话: {narrative_data.get('languages', {}).get('普通话', 'N/A')}")
    print(f"  languages 方言: {narrative_data.get('languages', {}).get('方言', 'N/A')}")
else:
    print("narrative_facts.json not found")

# Check derived_movies.csv stats
derived_path = DATA / "cleaned" / "derived_movies.csv"
if derived_path.exists():
    df = pd.read_csv(derived_path, encoding='utf-8-sig', low_memory=False)
    print(f"\nderived_movies.csv:")
    print(f"  Total rows: {len(df)}")
    print(f"  Is_Dialect sum: {df['Is_Dialect'].sum()}")
    print(f"  Region China count: {(df['Region'] == 'China').sum()}")
    # Check if 'Language' column exists
    if 'Language' in df.columns:
        print(f"  Language Chinese count: {(df['Language'] == 'Chinese').sum()}")
    else:
        print(f"  Language column: NOT FOUND")
        print(f"  Available columns: {list(df.columns)}")
else:
    print("derived_movies.csv not found")

# Check sample_manifest.json
manifest_path = DATA / "cleaned" / "sample_manifest.json"
if manifest_path.exists():
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)
    print(f"\nsample_manifest.json:")
    print(f"  publication_records: {manifest_data.get('publication_records', 'N/A')}")
    print(f"  sample_fingerprint_sha256: {manifest_data.get('sample_fingerprint_sha256', 'N/A')[:16]}...")
    print(f"  region China count: {manifest_data.get('counts', {}).get('region', {}).get('China', 'N/A')}")
else:
    print("sample_manifest.json not found")