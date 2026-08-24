# -*- coding: utf-8 -*-
"""Check report_data_strict.json file structure."""
import json

path = 'd:/movie-rating-data-story-main/dialect-movie-data-story-main/data/dialect_films/report_data_strict.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Top-level keys:', list(data.keys()))

if 'summary' in data:
    print('\nSummary keys:', list(data['summary'].keys()))
    print('Summary content:')
    for k, v in data['summary'].items():
        print(f'  {k}: {v}')
        
if 'movies' in data:
    print(f'\nMovies: {len(data["movies"])} entries')
    
if 'dialect_groups' in data:
    print(f'\nDialect groups keys:', list(data['dialect_groups'].keys()))
    for group, items in data['dialect_groups'].items():
        print(f'  {group}: {len(items) if isinstance(items, list) else items} items')