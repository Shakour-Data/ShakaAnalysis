#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get all market indices from finpy_tse using Build_Market_StockList
"""

import sys
import os
import io
import contextlib
import ssl
import urllib3
import requests
import sqlite3

# Windows encoding fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Proper SSL bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

_orig_pool_init = urllib3.PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return _orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get
requests.Session.get = _patched_get

sys.path.insert(0, '.')
import finpy_tse

print("Getting market stock list from finpy_tse...")

# Get the full market stock list with detailed info
f_out = io.StringIO()
with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
    try:
        # Try to get the detailed list
        df = finpy_tse.Build_Market_StockList(
            bourse=True, 
            farabourse=True, 
            payeh=True,
            detailed_list=True,
            show_progress=False,
            save_excel=False,
            save_csv=False
        )
        print(f"Got data: {type(df)}")
        if df is not None:
            print(f"Shape: {df.shape if hasattr(df, 'shape') else 'N/A'}")
            if hasattr(df, 'columns'):
                print(f"Columns: {list(df.columns)}")
            print(f"First 5 rows:\n{df.head() if hasattr(df, 'head') else df}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Also check the database for all symbols
conn = sqlite3.connect('data/market_data.db')
c = conn.cursor()
c.execute("SELECT symbol, name, type FROM symbols WHERE type = 'Index'")
indices = c.fetchall()
print(f"\nIndices in database: {len(indices)}")
for sym, name, typ in indices:
    print(f"  {sym} - {name}")

# Also check for any symbol that looks like an industry index
c.execute("SELECT symbol, name FROM symbols WHERE name LIKE '%صنعت%' OR name LIKE '%صندوق%' OR name LIKE '%پایه%' OR name LIKE '%فرابورس%' OR name LIKE '%صنعت%'")
ind_symbols = c.fetchall()
print(f"\nIndustry-like symbols: {len(ind_symbols)}")
for sym, name in ind_symbols:
    print(f"  {sym} - {name}")

conn.close()