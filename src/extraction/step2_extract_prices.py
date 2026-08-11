#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 2 Fixed: Extract price data with proper Unicode handling
"""

import sys
import os
import sqlite3
import io
import contextlib
import time
import re
import codecs
import pickle
import traceback

# Windows UTF-8 encoding fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL Bypass BEFORE importing finpy_tse
import ssl
import urllib3
import requests

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Patch urllib3
orig_pool_init = urllib3.PoolManager.__init__
def patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests to use timeout
_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get
requests.Session.get = _patched_get

session = requests.Session()
session.verify = False

DB_PATH = 'data/market_data.db'

print("=== Step 2 (Fixed): Extracting Price Data ===")

# Import finpy_tse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finpy_tse

# Function to decode Unicode escape sequences
def decode_unicode_escapes(s):
    """Decode Unicode escape sequences like \\u0622 in strings"""
    if not s or not isinstance(s, str):
        return s
    
    # Handle both \\uXXXX and \uXXXX formats
    result = s
    # Replace literal \uXXXX sequences
    while True:
        match = re.search(r'\\u([0-9a-fA-F]{4})', result)
        if not match:
            break
        codepoint = match.group(1)
        try:
            char = chr(int(codepoint, 16))
            result = result[:match.start()] + char + result[match.end():]
        except:
            result = result[:match.start()] + ' ' + result[match.end():]
    
    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result).strip()
    return result

# Function to clean ticker symbols
def clean_ticker(ticker):
    """Clean ticker symbols for use with finpy_tse"""
    decoded = decode_unicode_escapes(ticker)
    # Remove any non-essential trailing numbers (market codes)
    clean = re.sub(r'\s+', '', decoded)
    return clean.strip()

# Connect to database
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get a test symbol first - try 'خودرو' as that we know works
# First, let's decode some symbols and try a few
print("\n1. Testing symbol resolution...")

# Let's test directly with known good symbols
test_symbols = [
    ('خودرو', 'خودرو'),  # Ticker, Name
    ('آساس', 'آساس'),    # Another ticker
    ('فملی', 'فملی'),
    ('افق', 'افق'),
    ('شاخص', 'شاخص'),  # Index
]

successful_prices = {}

# Test symbol resolution using finpy_tse's webid function
for ticker, name in test_symbols:
    try:
        f_out = io.StringIO()
        with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
            result = finpy_tse.__Get_TSE_WebID__(ticker)
        
        if result is not None and hasattr(result, 'shape') and len(result) > 0:
            print(f"   Found data for {ticker}: {len(result)} rows")
            successful_prices[ticker] = True
        else:
            print(f"   No data for {ticker}")
    except Exception as e:
        print(f"   Error with {ticker}: {e}")

# If direct test fails, let's try with the raw escaped strings from DB
print("\n2. Testing with database symbols...")

# Get a few symbols from the database
c.execute("SELECT id, symbol FROM symbols LIMIT 5")
db_symbols = c.fetchall()

for row in db_symbols:
    sym_id = row['id']
    raw_symbol = row['symbol']
    decoded_symbol = decode_unicode_escapes(raw_symbol)
    clean_symbol = re.sub(r'\s+', '', decoded_symbol)
    
    print(f"   Raw: {repr(raw_symbol[:30])}")
    print(f"   Decoded: {repr(decoded_symbol[:30])}")
    print(f"   Clean: {repr(clean_symbol[:30])}")
    
    # Try to resolve ticker
    try:
        f_out = io.StringIO()
        with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
            # Try with decoded symbol
            result = finpy_tse.__Get_TSE_WebID__(clean_symbol[:10])
        
        if result is not None and hasattr(result, 'shape') and len(result) > 0:
            print(f"   Résolu! Found webid data for {clean_symbol[:10]}")
            # Extract the name from result
            for _, r in result.iterrows():
                name_val = str(r.iloc[0])  # First column is Name
                print(f"   Name: {name_val}")
        else:
            print(f"   No data for {clean_symbol[:10]}")
    except Exception as e:
        print(f"   Error: {e}")

# Step 3: Fix database symbols - decode Unicode escapes
print("\n3. Fixing database symbols (decoding Unicode escapes)...")
c.execute("SELECT id, symbol, name FROM symbols")
all_symbols = c.fetchall()

updated = 0
for row in all_symbols:
    sym_id = row['id']
    raw_symbol = row['symbol']
    raw_name = row['name']
    
    decoded_symbol = decode_unicode_escapes(raw_symbol)
    decoded_name = decode_unicode_escapes(raw_name)
    
    # Check if decoding changed anything
    if decoded_symbol != raw_symbol or decoded_name != raw_name:
        c.execute("UPDATE symbols SET symbol = ?, name = ? WHERE id = ?", 
                  (decoded_symbol, decoded_name, sym_id))
        updated += 1

conn.commit()
print(f"   Updated {updated} symbols")

# Now show properly decoded symbols
print("\n4. Decoded symbols (first 20):")
c.execute("SELECT symbol, name, type, exchange FROM symbols ORDER BY id LIMIT 20")
for row in c.fetchall():
    print(f"   {row['symbol']} - {row['name'][:50]}")

# Step 5: Try price extraction with decoded symbols
print("\n5. Extracting price data for first 5 symbols...")

c.execute("SELECT id, symbol, name FROM symbols ORDER BY id LIMIT 5")
symbols_to_process = c.fetchall()

total_rows = 0
for row in symbols_to_process:
    sym_id = row['id']
    symbol = row['symbol']
    name = row['name']
    
    print(f"\n   Processing: {symbol} ({name[:30]})")
    
    # Try with symbol first, then with name
    for search_term in [symbol, name[:20], name]:
        try:
            f_out = io.StringIO()
            f_err = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_err):
                price_df = finpy_tse.Get_Price_History(
                    stock=search_term,
                    start_date='1395-01-01',
                    end_date='1403-12-29',
                    show_weekday=True,
                    adjust_price=True,
                    ignore_date=False
                )
            
            if price_df is not None and not price_df.empty:
                print(f"     SUCCESS! Got {len(price_df)} rows for {search_term}")
                break
            else:
                print(f"     No data for '{search_term[:20]}'")
        except Exception as e:
            print(f"     Error with '{search_term[:20]}': {type(e).__name__}")
            continue
    else:
        print(f"     All search terms failed for {symbol}")
        continue
    
    # Insert price data into database
    insert_count = 0
    for _, data_row in price_df.iterrows():
        # Get date
        date_val = None
        for col_name in data_row.index:
            if col_name and 'date' in str(col_name).lower():
                date_val = str(data_row[col_name])[:10]
                break
        if not date_val or not date_val[0].isdigit():
            continue
        
        try:
            open_p = float(data_row.get('open', data_row.get('Open', 0)) or 0)
            high_p = float(data_row.get('high', data_row.get('High', 0)) or 0)
            low_p = float(data_row.get('low', data_row.get('Low', 0)) or 0)
            close_p = float(data_row.get('close', data_row.get('Close', 0)) or 0)
            final_p = float(data_row.get('final_price', data_row.get('Final', 0)) or 0)
            vol = int(data_row.get('volume', data_row.get('Volume', 0)) or 0)
            val = float(data_row.get('value', data_row.get('Value', 0)) or 0)
            adj_close_p = float(data_row.get('adj_close', data_row.get('Adj Close', 0)) or 0)
            adj_final_p = float(data_row.get('adj_final', data_row.get('Adj Final', 0)) or 0)
            
            c.execute('''
                INSERT OR REPLACE INTO price_data 
                (symbol_id, date, weekday, open, high, low, close, final_price,
                 volume, value, adj_close, adj_final,
                 sma_20, sma_50, rsi, macd, macd_signal, macd_histogram)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                  vol, val, adj_close_p, adj_final_p, 0, 0, 0, 0, 0, 0))
            insert_count += 1
        except Exception as e:
            pass
    
    conn.commit()
    print(f"     Inserted {insert_count} rows")
    total_rows += insert_count

# Final verification
print("\n6. Final Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"   Symbols: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"   Price rows: {c.fetchone()[0]}")

c.execute("SELECT COUNT(DISTINCT symbol_id) FROM price_data")
print(f"   Symbols with price data: {c.fetchone()[0]}")

conn.close()
print(f"\n✅ Step 2 complete! Extracted {total_rows} price rows")
