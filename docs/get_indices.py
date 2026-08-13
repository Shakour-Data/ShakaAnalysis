#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get industry indices from finpy_tse - simplified version
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

print("Getting industry indices from finpy_tse...")

# Common industry index names to try
industry_names = [
    'صندوق صنعت کارخانه',
    'صندوق صنایع',
    'صندوق صنعت',
    'صندوق صنعت ایران',
    'صندوق صنایع ایران',
    'شاخص صنعت',
    'شاخص',
    'پایه',
    'فرابورس',
    'پژوهشی',
    'صندوق صنعت خودرو',
    'صندوق صنایع فلزات',
    'صندوف صنعت',
]

real_indices = []
for name in industry_names:
    try:
        f_out = io.StringIO()
        with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
            df = finpy_tse.Get_Price_History(
                stock=name,
                start_date='1395-01-01',
                end_date='1403-12-29',
                show_weekday=True,
                adjust_price=True
            )
        if df is not None and not df.empty:
            ticker = df.iloc[0].get('Ticker', name) if 'Ticker' in df.columns else name
            print(f"  Found: {name} -> Ticker={ticker}")
            real_indices.append((ticker, name, 'TSE'))
        else:
            print(f"  No data for '{name}'")
    except Exception as e:
        print(f"  Error with '{name}': {e}")

# Combine with known indices
all_indices = [
    ('شاخص کل', 'Total Stock Index (شاخص کل)', 'TSE'),
    ('شاخص برابر وزن', 'Total Equal Weight Index (شاخص برابر وزن)', 'TSE'),
    ('شاخص صنعت', 'Industry Indices (شاخص صنعت)', 'TSE'),
] + real_indices

# Also check from database
conn = sqlite3.connect('data/market_data.db')
c = conn.cursor()
c.execute("SELECT symbol, name FROM symbols WHERE type = 'Index'")
existing = c.fetchall()
print(f"\nExisting indices in database: {len(existing)}")
for s, n in existing:
    print(f"  {s} - {n}")
conn.close()

# Remove duplicates
seen = set()
unique_indices = []
for item in all_indices:
    key = (str(item[0]), str(item[2]))
    if key not in seen:
        seen.add(key)
        unique_indices.append(item)

print(f"\nFinal unique indices: {len(unique_indices)}")
for sym, name, exch in unique_indices:
    print(f"  {sym} | {name} | {exch}")

# Write to markdown file
output_dir = 'docs'
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'symbols_and_indices.md')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('# Companies and Market Indices\n\n')
    f.write('## Market Indices\n\n')
    f.write('| Symbol | Name | Exchange |\n')
    f.write('|--------|------|----------|\n')
    for symbol, name, exch in unique_indices:
        name_esc = str(name).replace('|', '\\|')
        f.write(f'| {symbol} | {name_esc} | {exch} |\n')
    
    # Get stocks from existing file
    f.write('\n## Companies (Stocks)\n\n')
    f.write('| Symbol | Name | Exchange |\n')
    f.write('|--------|------|----------|\n')
    
    # Load symbols from database
    conn = sqlite3.connect('data/market_data.db')
    c = conn.cursor()
    c.execute("SELECT symbol, name, type, exchange FROM symbols WHERE type = 'Stock' ORDER BY symbol")
    stock_rows = c.fetchall()
    print(f"\nWriting {len(stock_rows)} stocks...")
    for symbol, name, typ, exch in stock_rows:
        name_esc = str(name).replace('|', '\\|')
        f.write(f'| {symbol} | {name_esc} | {exch} |\n')
    conn.close()

print(f"\nUpdated {output_file}")