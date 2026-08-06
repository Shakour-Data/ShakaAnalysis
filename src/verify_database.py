#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify database structure."""

import sqlite3

DB_PATH = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis\data\market_data.db'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:')
for t in tables:
    print(f'  {t}')

# Check foreign keys
print('\nForeign Keys:')
cur.execute("PRAGMA foreign_key_list(price_data)")
rows = cur.fetchall()
for row in rows:
    print(f'  price_data -> {row[2]}.{row[3]}')

cur.execute("PRAGMA foreign_key_list(indices)")
rows = cur.fetchall()
for row in rows:
    print(f'  indices -> {row[2]}.{row[3]}')

cur.execute("PRAGMA foreign_key_list(analysis_records)")
rows = cur.fetchall()
for row in rows:
    print(f'  analysis_records -> {row[2]}.{row[3]}')

cur.execute("PRAGMA foreign_key_list(export_history)")
rows = cur.fetchall()
for row in rows:
    print(f'  export_history -> {row[2]}.{row[3]}')

# Count records
print('\nRecord counts:')
for name, query in [
    ('symbols', 'SELECT COUNT(*) FROM symbols'),
    ('price_data', 'SELECT COUNT(*) FROM price_data'),
    ('indices', 'SELECT COUNT(*) FROM indices'),
    ('analysis_records', 'SELECT COUNT(*) FROM analysis_records'),
    ('export_history', 'SELECT COUNT(*) FROM export_history'),
]:
    count = cur.execute(query).fetchone()[0]
    print(f'  {name}: {count}')

# Check symbol relationships
print('\nSample symbols:')
cur.execute('SELECT * FROM symbols LIMIT 5')
symbols = cur.fetchall()
for s in symbols:
    print(f'  ID {s[0]}: {s[1]} - {s[2]} - {s[3]} ({s[5]})')

conn.close()
print('\nDatabase structure verified!')