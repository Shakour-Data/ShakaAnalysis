#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final complete extraction - adds خودرو symbol and extracts data for all symbols
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
import time

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

orig_get = requests.get
def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return orig_get(url, *args, **kwargs)
requests.get = patched_get
requests.Session.get = patched_get

import finpy_tse

DB_PATH = 'data/market_data.db'

def decode_unicode_escapes(s):
    """Decode literal \\uXXXX sequences in strings"""
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

print("=== Complete Final Extraction ===")

# Connect
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Add known working symbol 'خودرو' if not exists
c.execute("SELECT COUNT(*) FROM symbols WHERE symbol = 'خودرو'")
if c.fetchone()[0] == 0:
    c.execute('''
        INSERT INTO symbols (symbol, name, type, exchange, industry, sector, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('خودرو', 'ایران خودرو', 'Stock', 'TSE', 'ساخت خودرو', 'خودرو', 1))
    conn.commit()
    print("Added 'خودرو' symbol to database")

# Get all symbols
c.execute("SELECT id, symbol, name FROM symbols ORDER BY id")
all_symbols = c.fetchall()
print(f"Total symbols: {len(all_symbols)}")

# Show a few sample decoded symbols
print("\nSample decoded symbols:")
for s in all_symbols[:5]:
    decoded_sym = decode_unicode_escapes(s['symbol'])
    decoded_name = decode_unicode_escapes(s['name'])
    print(f"  ID={s['id']}: {decoded_sym} - {decoded_name[:50]}")

# Process symbols
print("\nProcessing symbols for price data...")
total_rows = 0
processed_count = 0
failed_count = 0

# First, test with خودرو to verify flow
print("\nTesting with 'خودرو' first...")
try:
    df = finpy_tse.Get_Price_History(
        stock='خودرو',
        start_date='1395-01-01',
        end_date='1403-12-29',
        show_weekday=True,
        adjust_price=True
    )
    
    if df is not None and not df.empty:
        # Get symbol ID
        c.execute("SELECT id FROM symbols WHERE symbol = 'خودرو'")
        sym_row = c.fetchone()
        if sym_row:
            sym_id = sym_row[0]
            
            # Insert ALL rows
            inserted = 0
            for jdate in df.index:
                row_data = df.loc[jdate]
                date_val = str(jdate)
                
                # Try both column formats
                open_p = float(row_data.get('Open', 0) or 0)
                high_p = float(row_data.get('High', 0) or 0)
                low_p = float(row_data.get('Low', 0) or 0)
                close_p = float(row_data.get('Close', 0) or 0)
                final_p = float(row_data.get('Final', 0) or 0)
                vol = int(row_data.get('Volume', 0) or 0)
                val = float(row_data.get('Value', 0) or 0)
                
                c.execute('''
                    INSERT OR REPLACE INTO price_data 
                    (symbol_id, date, weekday, open, high, low, close, final_price,
                     volume, value, adj_close, adj_final)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                      vol, val, 0, 0))
                inserted += 1
            
            conn.commit()
            print(f"Inserted {inserted} rows for خودرو")
            total_rows += inserted
            processed_count += 1
except Exception as e:
    print(f"Error with خودرو: {e}")
    import traceback
    traceback.print_exc()

# Now process remaining symbols
for s in all_symbols:
    if s['symbol'] == 'خودرو':
        continue  # Already processed
    
    # Decode symbol for search
    decoded_sym = decode_unicode_escapes(s['symbol'])
    decoded_name = decode_unicode_escapes(s['name'])
    
    if not decoded_sym or not decoded_sym[0].isalpha():
        continue
    
    try:
        df = finpy_tse.Get_Price_History(
            stock=decoded_sym,
            start_date='1395-01-01',
            end_date='1403-12-29',
            show_weekday=True,
            adjust_price=True
        )
        
        if df is not None and not df.empty:
            inserted = 0
            for jdate in df.index:
                row_data = df.loc[jdate]
                date_val = str(jdate)
                
                open_p = float(row_data.get('Open', 0) or 0)
                high_p = float(row_data.get('High', 0) or 0)
                low_p = float(row_data.get('Low', 0) or 0)
                close_p = float(row_data.get('Close', 0) or 0)
                final_p = float(row_data.get('Final', 0) or 0)
                vol = int(row_data.get('Volume', 0) or 0)
                val = float(row_data.get('Value', 0) or 0)
                
                c.execute('''
                    INSERT OR REPLACE INTO price_data 
                    (symbol_id, date, weekday, open, high, low, close, final_price,
                     volume, value, adj_close, adj_final)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (s['id'], date_val, 0, open_p, high_p, low_p, close_p, final_p,
                      vol, val, 0, 0))
                inserted += 1
            
            conn.commit()
            total_rows += inserted
            processed_count += 1
            print(f"  {s['id']}: {decoded_sym[:20]} - {inserted} rows")
        else:
            failed_count += 1
    except Exception as e:
        failed_count += 1
        # Continue silently on errors

# Final verification
print("\n" + "=" * 50)
print("Final Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"Total symbols: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"Total price data rows: {c.fetchone()[0]}")

c.execute("SELECT COUNT(DISTINCT symbol_id) FROM price_data")
print(f"Symbols with price data: {c.fetchone()[0]}")

# Show sample
c.execute('''
    SELECT s.symbol, s.name, COUNT(p.id) as row_count
    FROM symbols s LEFT JOIN price_data p ON s.id = p.symbol_id
    GROUP BY s.id
    ORDER BY row_count DESC
    LIMIT 10
''')
print("\nTop symbols by price data rows:")
for row in c.fetchall():
    print(f"  {row['symbol']}: {row['row_count']} rows")

conn.close()
print("\n✅ Complete!")