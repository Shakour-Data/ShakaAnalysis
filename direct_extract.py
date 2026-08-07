#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct extraction using cached HTML and finpy_tse
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
import traceback
import pickle
import time
from pathlib import Path

# Windows console fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

_orig_pool_init = urllib3.PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return _orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests
_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get
requests.Session.get = _patched_get

# Import finpy_tse
import finpy_tse

DB_PATH = 'data/market_data.db'
HTML_FILE = r'C:\Users\Frequensy\.local\share\kilo\tool-output\tool_fda9d280c001GTiDuhYqYpuSyh'

print("=== Direct Extraction Pipeline ===")

# Step 1: Initialize database
print("Step 1: Initializing database...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Clean tables
c.execute('DROP TABLE IF EXISTS price_data')
c.execute('DROP TABLE IF EXISTS symbols')
c.execute('DROP TABLE IF EXISTS indices_data')

c.execute('''CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT,
    type TEXT DEFAULT 'Stock',
    exchange TEXT DEFAULT 'TSE',
    industry TEXT DEFAULT 'Unknown',
    sector TEXT DEFAULT 'Unknown',
    webid TEXT DEFAULT '',
    country TEXT DEFAULT 'IR',
    currency TEXT DEFAULT 'IRR',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE price_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL,
    date TEXT,
    weekday INTEGER,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    final_price REAL,
    volume INTEGER,
    value REAL,
    adj_close REAL,
    adj_final REAL,
    sma_20 REAL,
    sma_50 REAL,
    rsi REAL,
    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,
    bb_upper REAL,
    bb_lower REAL,
    adx REAL,
    cci REAL,
    mfi REAL,
    ma_100 REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
)''')

c.execute('''CREATE TABLE indices_data (
    symbol TEXT NOT NULL,
    name TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    value REAL,
    adj_close REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_data(symbol_id, date)')
c.execute('CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols(exchange)')
conn.commit()
print("  Database ready")

# Step 2: Extract symbols from cached HTML
print("Step 2: Extracting symbols from cached HTML...")
with open(HTML_FILE, 'r', encoding='utf-8') as f:
    html_content = f.read()
print(f"  Loaded {len(html_content)} chars")

# Use BeautifulSoup to parse
from bs4 import BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')
tables = soup.find_all('table')
print(f"  Found {len(tables)} tables")

if tables:
    table = tables[0]
    rows = table.find_all('tr')
    print(f"  Found {len(rows)} rows")
    
    symbols = []
    for row in rows[1:]:  # Skip header
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 2:
            symbol_raw = cols[0].get_text().strip()
            name_raw = cols[1].get_text().strip() if len(cols) > 1 else ''
            
            symbol = re.sub(r'<[^>]+>', '', symbol_raw).strip()
            name = re.sub(r'<[^>]+>', '', name_raw).strip()
            symbol = re.sub(r'\s+', ' ', symbol)
            name = re.sub(r'\s+', ' ', name)
            
            if symbol and symbol not in ['nan', ''] and not symbol.startswith('<'):
                # Determine type
                sym_type = 'Stock'
                exch = 'TSE'
                lower_name = name.lower()
                if any(kw in lower_name for kw in ['شاخص', 'index', 'ETF', 'صندوق', 'صاح', 'صنهد', 'صنلن']):
                    sym_type = 'Index'
                elif 'فرابورس' in lower_name or 'OTC' in name.upper():
                    exch = 'OTC'
                
                symbols.append((symbol, name, sym_type, exch))
    
    print(f"  Extracted {len(symbols)} symbols")
    
    # Insert symbols
    print("Step 3: Inserting symbols...")
    inserted = 0
    for sym, name, s_type, exch in symbols:
        try:
            c.execute('''
                INSERT OR IGNORE INTO symbols 
                (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym, name, s_type, exch, 'Unknown', 'Unknown', '', 'IR', 'IRR', 1))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {sym}: {e}")
    
    conn.commit()
    print(f"  Inserted {inserted} symbols")

# Step 4: Get price data
print("\nStep 4: Extracting price data...")
c.execute("SELECT id, symbol, name, type FROM symbols")
all_symbols = c.fetchall()
print(f"  Found {len(all_symbols)} symbols to process")

total_rows = 0
processed = 0

# First test with a known symbol
print("\n  Testing with known symbol 'خودرو'...")
test_df = finpy_tse.Get_Price_History(
    stock='خودرو',
    start_date='1395-01-01',
    end_date='1403-12-29',
    show_weekday=True,
    adjust_price=True
)
if test_df is not None and not test_df.empty:
    print(f"  Test successful: {len(test_df)} rows")
    
    # Insert test data
    c.execute("SELECT id FROM symbols WHERE symbol='خودرو' OR name LIKE '%خودرو%' LIMIT 1")
    test_row = c.fetchone()
    if test_row:
        test_id = test_row[0]
        for _, row in test_df.iterrows():
            date_val = str(row.name)[:10] if hasattr(row, 'name') else str(row.get('J-Date', ''))[:10]
            if not date_val or not date_val[0].isdigit():
                date_val = str(row.get('Date', ''))[:10]
            
            open_p = float(row.get('open', row.get('Open', 0)) or 0)
            high_p = float(row.get('high', row.get('High', 0)) or 0)
            low_p = float(row.get('low', row.get('Low', 0)) or 0)
            close_p = float(row.get('close', row.get('Close', 0)) or 0)
            final_p = float(row.get('final_price', row.get('Final', 0)) or 0)
            vol = int(row.get('volume', row.get('Volume', 0)) or 0)
            val = float(row.get('value', row.get('Value', 0)) or 0)
            
            c.execute('''
                INSERT OR REPLACE INTO price_data 
                (symbol_id, date, weekday, open, high, low, close, final_price,
                 volume, value, adj_close, adj_final)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (test_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                  vol, val, 0, 0))
        
        conn.commit()
        total_rows += len(test_df)
        print(f"  Inserted test data for خودرو")

# Now process all symbols - but only first 100 for now to avoid timeout
print("\n  Processing first 100 symbols...")
for i, (sym_id, symbol, name, sym_type) in enumerate(all_symbols[:100]):
    if i % 10 == 0:
        print(f"    Progress: {i}/100 symbols...")
    
    # Try symbol first
    for search_term in [symbol, name[:20] if name else '']:
        if not search_term:
            continue
        try:
            f_out = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                price_df = finpy_tse.Get_Price_History(
                    stock=search_term,
                    start_date='1395-01-01',
                    end_date='1403-12-29',
                    show_weekday=True,
                    adjust_price=True
                )
            
            if price_df is not None and not price_df.empty:
                for _, row in price_df.iterrows():
                    date_val = str(row.name)[:10] if hasattr(row, 'name') else str(row.get('J-Date', ''))[:10]
                    if not date_val or not date_val[0].isdigit():
                        date_val = str(row.get('Date', ''))[:10]
                    
                    open_p = float(row.get('open', row.get('Open', 0)) or 0)
                    high_p = float(row.get('high', row.get('High', 0)) or 0)
                    low_p = float(row.get('low', row.get('Low', 0)) or 0)
                    close_p = float(row.get('close', row.get('Close', 0)) or 0)
                    final_p = float(row.get('final_price', row.get('Final', 0)) or 0)
                    vol = int(row.get('volume', row.get('Volume', 0)) or 0)
                    val = float(row.get('value', row.get('Value', 0)) or 0)
                    
                    c.execute('''
                        INSERT OR REPLACE INTO price_data 
                        (symbol_id, date, weekday, open, high, low, close, final_price,
                         volume, value, adj_close, adj_final)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                          vol, val, 0, 0))
                
                conn.commit()
                total_rows += len(price_df)
                processed += 1
                break
        except Exception as e:
            pass
    
    if i % 20 == 0:
        print(f"    ... {i} symbols processed, {total_rows} total rows")

# Final verification
print("\n=== Final Verification ===")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"Total symbols: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM price_data")
print(f"Total price rows: {c.fetchone()[0]}")
c.execute("SELECT COUNT(DISTINCT symbol_id) FROM price_data")
print(f"Symbols with price data: {c.fetchone()[0]}")

conn.close()
print("\n✅ Pipeline complete!")