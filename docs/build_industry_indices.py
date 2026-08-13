#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get real industry indices from finpy_tse
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
import pandas as pd

# SSL bypass setup
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urllib3.PoolManager.__init__ = lambda self, *a, **k: (setattr(self, 'ssl_context', ctx) or urllib3.PoolManager.__init__(self, *a, **k))

_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get

# Import finpy_tse AFTER patching
sys.path.insert(0, '.')
import finpy_tse

DB_PATH = 'data/market_data.db'

def decode_unicode_escapes(s):
    if not s or not isinstance(s, str):
        return s
    result = s
    def replacer(match):
        try:
            return chr(int(match.group(1), 16))
        except:
            return match.group(0)
    result = re.sub(r'\\u([0-9a-fA-F]{4})', replacer, result)
    return result

# Connect to database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all current symbols
c.execute("SELECT symbol, name, type, exchange FROM symbols ORDER BY type")
rows = c.fetchall()

# Check if we have actual industry indices in the database
industry_indices = []
for row in rows:
    symbol, name, typ, exch = row
    if typ == 'Index':
        # Look for industry keywords in name
        name_lower = str(name).lower()
        if any(kw in name_lower for kw in ['صنع', 'صنایع', 'کارخانه', 'صنعت', 'صنعت‌ها']):
            industry_indices.append((symbol, name, exch))

# Try to get real industry indices using finpy_tse
print("Getting industry indices from finpy_tse...")

# Also check for other common industry index names
common_industry_names = [
    'صندوق صنعت',
    'صندوق صنایع',
    'صندوق صنعت کارخانه',
    'صندوق صنایع خودرو',
    'صندوق صنعت ایران',
    'صندوق صنایع ایران',
    'صندوق صنایع تهران',
    'صندوق صنعت ورزشت',
    'صندوق صنعت инструментов',
]

real_indices = []
for name in common_industry_names:
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
            for _, row in df.iterrows():
                ticker = row.get('Ticker', '')
                if ticker:
                    real_indices.append((ticker, name, 'TSE'))
    except Exception as e:
        print(f"  ⚠️ Error with '{name}': {e}")

# Also fetch some major indices for comparison
major_names = [
    'شاخص',
    'پایه',
    'فرابورس',
    'پژوهشی',
]

for name in major_names:
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
            for _, row in df.iterrows():
                ticker = row.get('Ticker', row.get('Ticker', ''))
                if ticker:
                    real_indices.append((ticker, name, 'TSE'))
    except Exception as e:
        print(f"  ⚠️ Error with '{name}': {e}")

# Combine all results
all_indices = list(set(industry_indices + real_indices))

# Also add the ones we had before
# Total Stock Index, Total Equal Weight Index, Industry Indices
all_indices = [
    ('شاخص کل', 'Total Stock Index', 'TSE'),
    ('شاخص برابر وزن', 'Total Equal Weight Index', 'TSE'),
    ('شاخص صنعت', 'Industry Indices', 'TSE'),
] + all_indices

# Remove duplicates while preserving order
seen = set()
unique_indices = []
for item in all_indices:
    key = (item[0], item[2])
    if key not in seen:
        seen.add(key)
        unique_indices.append(item)

print(f"\nTotal: {len(unique_indices)} unique indices found")
for sym, name, exch in unique_indices:
    print(f"  {sym} | {name} | {exch}")

# Update the markdown file
output_dir = 'docs'
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'symbols_and_indices.md')

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('# Companies and Market Indices\n\n')
    
    # Load stocks from existing file
    existing_file = 'docs/symbols_and_indices.md'
    with open(existing_file, 'r', encoding='utf-8') as existing:
        content = existing.read()
    
    # Find and replace the indices section
    lines = content.split('\n')
    new_lines = []
    in_indices_section = False
    idx_counter = 0
    
    for line in lines:
        if '## Market Indices' in line:
            in_indices_section = True
            new_lines.append(line)
            new_lines.append('')
            new_lines.append('| Symbol | Name | Exchange |')
            new_lines.append('|--------|------|----------|')
        elif in_indices_section:
            if '|' in line and line.strip().startswith('|') and '---' not in line:
                # This is a data line or separator
                if line.strip().startswith('|---'):  # Separator
                    continue  # Skip separator
                else:
                    # This is a data line
                    idx_counter += 1
                    if idx_counter <= len(unique_indices):
                        symbol, name, exch = unique_indices[idx_counter - 1]
                        name_esc = str(name).replace('|', '\\|')
                        new_lines.append(f'| {symbol} | {name_esc} | {exch} |')
                    else:
                        break
            else:
                # Might be a header from the stocks section, keep it
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write updated content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

print(f"\n✓ Updated {output_file} with {len(unique_indices)} indices")