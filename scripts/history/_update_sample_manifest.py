# -*- coding: utf-8 -*-
"""
Update sample_manifest.json to match current derived_movies.csv state.
This script recalculates the fingerprint and updates counts to match current data.
"""
import hashlib
import json
import pandas as pd
from pathlib import Path

BASE = Path("d:/movie-rating-data-story-main/dialect-movie-data-story-main")
DATA = BASE / "data"

# Load current derived_movies.csv
derived_path = DATA / "cleaned" / "derived_movies.csv"
df = pd.read_csv(derived_path, encoding='utf-8-sig', low_memory=False)

print(f"Processing {len(df)} records from derived_movies.csv")

# Calculate new SHA256 fingerprint
# Create a string representation of the dataframe that captures essential content
content_str = df.to_csv(index=False, encoding='utf-8')
sha256_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()

print(f"New fingerprint: {sha256_hash}")

# Load current manifest
manifest_path = DATA / "cleaned" / "sample_manifest.json"
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

# Update manifest with current values
manifest['publication_records'] = len(df)
manifest['sample_fingerprint_sha256'] = sha256_hash

# Update counts based on current data
region_counts = df['Region'].value_counts().to_dict()
language_counts = df['Language_Category'].value_counts().to_dict() if 'Language_Category' in df.columns else {}
decade_counts = df['Decade'].value_counts().to_dict()
# For source, use the '数据来源' column which is likely in Chinese
source_col_name = None
for col in df.columns:
    if '来源' in col or 'Source' in col:
        source_col_name = col
        break

source_counts = df[source_col_name].value_counts().to_dict() if source_col_name else {}

# Update the counts section
manifest['counts']['region'] = region_counts
manifest['counts']['language'] = language_counts
manifest['counts']['decade'] = decade_counts
manifest['counts']['source'] = source_counts

# Update stages information
manifest['stages']['deduplicated_records'] = len(df)

# Save updated manifest
with open(manifest_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print("sample_manifest.json updated successfully!")
print(f"  publication_records: {manifest['publication_records']}")
print(f"  sample_fingerprint_sha256: {manifest['sample_fingerprint_sha256'][:16]}...")
print(f"  China region count: {region_counts.get('China', 0)}")