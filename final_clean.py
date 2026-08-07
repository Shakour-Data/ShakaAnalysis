#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final clean extraction script - process a few symbols and verify database
"""

import sys
import os
import io
import contextlib
import ssl
import urllib3
import requests
import sqlite3
import re

# Windows console fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

orig_pool_init = urllib3.PoolManager.__init__
def patched_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = patched_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests
orig_get = requests.get
def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return orig_get(url, *args, **kwargs)
requests.get = patched_get
requests.Session.get = patched_get

import finpy_tse

DB_PATH = 'data/market_data.db'

print("=== Final Extraction - Testing price data flow ===")

# Connect to DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get a known working symbol
# First, let's check what's in symbols
c.execute("SELECT id, symbol, name FROM symbols LIMIT 10")
symbols = c.fetchall()
print(f"First 10 symbols from DB:")
for s in symbols:
    print(f"  ID={s[0]}, Symbol='{s[1][:30]}', Name='{s[2][:30]}'")

# Test with خودرو from earlier verification
print("\nTesting with 'خودرو' (known working symbol)...")

f_out = io.StringIO()
with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
    df = finpy_tse.Get_Price_History(
        stock='خودرو',
        start_date='1395-01-01',
        end_date='1403-12-29',
        show_weekday=True,
        adjust_price=True,
        ignore_date=False
    )

if df is not None and not df.empty:
    print(f"Retrieved {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    print(f"Index (dates): {df.index[:3].tolist()}")
    print(f"Sample row 0: {df.iloc[0].to_dict()}")
    
    # Get the symbol ID
    c.execute("SELECT id FROM symbols WHERE symbol LIKE '%خودرو%' LIMIT 1")
    row = c.fetchone()
    if row:
        sym_id = row[0]
        print(f"Found symbol ID: {sym_id}")
        
        # Insert data
        inserted = 0
        for jdate in df.index[:10]:  # Just first 10 for testing
            row_data = df.loc[jdate]
            
            date_val = str(jdate)
            open_p = float(row_data.get('Open', row_data.get('open', 0)))
            high_p = float(row_data.get('High', row_data.get('high', 0)))
            low_p = float(row_data.get('Low', row_data.get('low', 0)))
            close_p = float(row_data.get('Close', row_data.get('close', 0)))
            final_p = float(row_data.get('Final', row_data.get('final_price', 0)))
            vol = int(row_data.get('Volume', row_data.get('volume', 0)))
            val = float(row_data.get('Value', row_data.get('value', 0)))
            
            c.execute('''
                INSERT INTO price_data 
                (symbol_id, date, weekday, open, high, low, close, final_price,
                 volume, value, adj_close, adj_final)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                  vol, val, 0, 0))
            inserted += 1
        
        conn.commit()
        print(f"Inserted {inserted} test rows")
    else:
        print("Symbol not found in DB")
else:
    print("No data returned")

# Verify
c.execute("SELECT COUNT(*) FROM price_data")
rows_in_db = c.fetchone()[0]
print(f"\nPrice data rows in DB: {rows_in_db}")

conn.close()
print("\nDone!")