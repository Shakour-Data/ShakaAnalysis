#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shaka Analysis Database Populator v2.0

Expansive symbol and index population module for 800+ symbols and 50 market indices
"""

import ssl
import urllib3
import sys
import os

# Apply SSL bypass to urllib3.PoolManager
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
_orig_init = urllib3.PoolManager.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    _orig_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_init
urllib3.disable_warnings()

sys.path.insert(0, '.')

# Import necessary modules
from src.database import get_db_connection, initialize_database
import finpy_tse

# Initialize database
print('Initializing database...')
initialize_database()

# Get symbols (now limited to 800)
print('Fetching market data symbols...')
df_symbols = finpy_tse.Build_Market_StockList(
    bourse=True,
    farabourse=True,
    payeh=True,
    show_progress=False
)
nf_symbols = df_symbols.head(800)  # Ensure exactly 800 symbols

# Get indices (50 market indices)
print('Fetching market indices...')
df_indices = finpy_tse.Build_Market_IndexList(  # New function implementation needed
    show_progress=False
)
nf_indices = df_indices.head(50)  # Ensure exactly 50 indices

# Prepare symbols
symbols_to_insert = []
for _, row in df_symbols.iterrows():
    # ... [existing symbol processing code remains largely unchanged] ...

# Prepare indices
indices_to_insert = []
for _, row in df_indices.iterrows():
    symbols_to_insert.append((
        row['Ticker'],
        row['Name'],
        'Index',  # Fixed type for indices
        row['Exchange'],
        'Unknown',  # Industry/sectors for indices
        row['Market'],
        row.get('WEB-ID', ''),
        'IR',
        'IRR',
        1
    ))

# Insert into database
conn = get_db_connection()
cursor = conn.cursor()

# Clear existing symbols
cursor.execute('DELETE FROM symbols')

# Insert symbols first
cursor.executemany('''
    INSERT INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', symbols_to_insert)

# Insert indices
cursor.executemany('''
    INSERT INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', indices_to_insert)

# Commit and verify
conn.commit()
print(f'Inserted {len(symbols_to_insert)} symbols and {len(indices_to_insert)} indices')
...

