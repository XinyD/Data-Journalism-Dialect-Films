# -*- coding: utf-8 -*-
"""Check report_data_strict.json file."""
import json

path = 'd:/movie-rating-data-story-main/dialect-movie-data-story-main/data/dialect_films/report_data_strict.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Keys:', list(data.keys()))
print('dialect_films_count:', data.get('dialect_films_count', 'N/A'))
print('total_chinese_films:', data.get('total_chinese_films', 'N/A'))
print('tier1_count:', data.get('tier1_count', 'N/A'))
print('tier2a_count:', data.get('tier2a_count', 'N/A'))
print('tier2b_count:', data.get('tier2b_count', 'N/A'))