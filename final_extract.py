#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final comprehensive extraction script with proper Unicode handling.
Decodes Unicode escape sequences in symbols before using them with finpy_tse.
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
import pickle

# Windows console fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

orig_pool_init = urllib3.PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get
requests.Session.get = _patched_get

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

def process_symbols(conn, start_id=1, end_id=100):
    """Process symbols and extract price data"""
    c = conn.cursor()
    c.execute("SELECT id, symbol, name FROM symbols WHERE id BETWEEN ? AND ?", (start_id, end_id))
    symbols = c.fetchall()
    
    print(f"Processing symbols {start_id}-{end_id} ({len(symbols)} total)")
    
    total_rows = 0
    processed_count = 0
    
    for sym_id, raw_symbol, raw_name in symbols:
        try:
            # Decode Unicode escape sequences
            decoded_symbol = decode_unicode_escapes(raw_symbol)
            decoded_name = decode_unicode_escapes(raw_name)
            
            # Skip if decoding doesn't produce valid text
            if not decoded_symbol or not decoded_symbol[0].isalpha():
                print(f"  Skipping {sym_id}: no valid decoded symbol")
                continue
            
            # For this symbol, try to get price data
            # Use the decoded symbol as the search term
            try:
                f_out = io.StringIO()
                with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                    price_df = finpy_tse.Get_Price_History(
                        stock=decoded_symbol,
                        start_date='1395-01-01',
                        end_date='1403-12-29',
                        show_weekday=True,
                        adjust_price=True,
                        ignore_date=False
                    )
                
                if price_df is not None and not price_df.empty:
                    print(f"  {sym_id}: {decoded_symbol} - SUCCESS ({len(price_df)} rows)")
                    
                    # Insert price data
                    insert_count = 0
                    for _, row in price_df.iterrows():
                        date_val = str(row.get('date', ''))[:10] if 'date' in row else ''
                        
                        # Also try the J-Date column
                        jdate = str(row.get('jdate', ''))[:10] if 'jdate' in row else ''
                        if not date_val or not date_val[0].isdigit():
                            date_val = jdate
                        
                        if not date_val or not date_val[0].isdigit():
                            continue
                        
                        # Extract numeric values
                        open_p = float(row.get('open', row.get('Open', 0)) or 0)
                        high_p = float(row.get('high', row.get('High', 0)) or 0)
                        low_p = float(row.get('low', row.get('Low', 0)) or 0)
                        close_p = float(row.get('close', row.get('Close', 0)) or 0)
                        final_p = float(row.get('final_price', row.get('Final', 0)) or 0)
                        vol = int(row.get('volume', row.get('Volume', 0)) or 0)
                        val = float(row.get('value', row.get('Value', 0)) or 0)
                        
                        try:
                            conn.execute('''
                                INSERT OR REPLACE INTO price_data 
                                (symbol_id, date, weekday, open, high, low, close, final_price,
                                 volume, value, adj_close, adj_final)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                                  vol, val, 0, 0))
                            insert_count += 1
                        except:
                            pass
                    
                    conn.commit()
                    total_rows += insert_count
                    processed_count += 1
                    
                else:
                    print(f"  {sym_id}: {decoded_symbol} - No data returned")
                    
            except Exception as e:
                print(f"  {sym_id}: {decoded_symbol} - Error: {e}")
        except Exception as e:
            print(f"  {sym_id}: Error - {e}")
    
    return processed_count, total_rows

# Connect to database and process
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM symbols")
total_symbols = c.fetchone()[0]
print(f"\nTotal symbols in database: {total_symbols}")

# Process all symbols
processed_count, total_rows = process_symbols(conn, 1, total_symbols)

print(f"\n=== Summary ===")
print(f"Symbols processed: {processed_count}")
print(f"Total price data rows: {total_rows}")

conn.close()
print("Done!")