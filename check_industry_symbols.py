#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check symbols with industry keywords and update the indices file
"""

import sys
import os
import io
import sqlite3

# Windows encoding fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

conn = sqlite3.connect('data/market_data.db')
c = conn.cursor()

# Check all symbols that contain industry-related keywords
print('Checking symbols in database...')

# Get all indices
c.execute("SELECT symbol, name, type FROM symbols WHERE type = 'Index'")
indices = c.fetchall()
print('\nIndices found ({0}):'.format(len(indices)))
for sym, name, typ in indices:
    print('  {0} - {1}'.format(sym, name))

# Get all stocks
c.execute("SELECT COUNT(*) FROM symbols WHERE type = 'Stock'")
stock_count = c.fetchone()[0]
print('\nStocks: {0}'.format(stock_count))

# Get some specific industry-related names
print('\nSearching for specific industry symbols...')

industry_patterns = [
    ('کارخانه', 'factory'),
    ('فلزات', 'metals'),
    ('ساختمان', 'construction'),
    ('حديد', 'steel'),
    ('فولاد', 'steel'),
    ('پترو', 'petrochemical'),
    ('نفت', 'oil'),
    ('خودرو', 'auto'),
    ('صنعت', 'industry'),
]

for pattern, desc in industry_patterns:
    c.execute("SELECT symbol, name FROM symbols WHERE name LIKE ? OR symbol LIKE ? LIMIT 3", (f'%{pattern}%', f'%{pattern}%'))
    rows = c.fetchall()
    if rows:
        print('  {0} ({1}): {2} symbols found'.format(pattern, desc, len(rows)))
        for sym, name in rows:
            print('    {0} - {1}'.format(sym, name))

conn.close()

print('\nDone.')