#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract price data and technical indicators for symbols in database
"""

import sqlite3
import ssl
import urllib3
import requests
import os
import sys
import io
import contextlib

# SSL Bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

orig_pool_init = urllib3.PoolManager.__init__
def patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

orig_get = requests.get
def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return orig_get(url, *args, **kwargs)
requests.get = patched_get
requests.Session.get = patched_get

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.database import get_db_connection, initialize_database

DB_PATH = 'data/market_data.db'

print("=== Price Data & Indicators Extraction ===")

# Step 1: Initialize database
print("1. Initializing database...")
initialize_database(DB_PATH)

# Step 2: Load symbols from HTML cache
print("2. Loading symbols from cached HTML output...")
HTML_FILE = r'C:\Users\Frequensy\.local\share\kilo\tool-output\tool_fda9d280c001GTiDuhYqYpuSyh'

try:
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    import pandas as pd
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    print(f"   Found {len(tables)} tables")
    
    if tables:
        # Parse the first table
        dfs = pd.read_html(str(tables[0]))
        if dfs:
            symbol_df = dfs[0]
            print(f"   Parsed table: {len(symbol_df)} rows")
            
            # Find symbol and name columns
            columns = list(symbol_df.columns)
            print(f"   Columns: {columns[:5]}")
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Insert symbols
            symbols_to_insert = []
            for _, row in symbol_df.iterrows():
                # Try to find symbol from common column names
                symbol_val = ''
                name_val = ''
                
                for col in columns:
                    col_lower = str(col).lower()
                    if 'ticker' in col_lower or 'symbol' in col_lower or 'کد' in col_lower:
                        symbol_val = str(row[col]).strip()
                    if 'name' in col_lower or 'نام' in col_lower or 'company' in col_lower:
                        name_val = str(row[col]).strip()
                
                # If not found, use first two columns
                if not symbol_val and len(columns) > 0:
                    symbol_val = str(row[columns[0]]).strip()
                if not name_val and len(columns) > 1:
                    name_val = str(row[columns[1]]).strip()
                
                if symbol_val and symbol_val not in ['nan', '', '\u200b']:
                    symbols_to_insert.append((
                        symbol_val, name_val, 'Stock', 'TSE',
                        'Unknown', 'Unknown', '', 'IR', 'IRR', 1
                    ))
            
            if symbols_to_insert:
                c.executemany('''
                    INSERT OR IGNORE INTO symbols 
                    (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', symbols_to_insert)
                conn.commit()
                
                c.execute('SELECT COUNT(*) FROM symbols')
                count = c.fetchone()[0]
                print(f"   Total symbols in database: {count}")
            
            conn.close()
            
except Exception as e:
    print(f"   Error loading symbols: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Extract price data for sample symbols
print("\n3. Extracting price data for sample symbols...")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT symbol, name, type FROM symbols WHERE type = 'Stock' LIMIT 10")
sample_symbols = c.fetchall()

print(f"   Found {len(sample_symbols)} sample symbols")

for ticker, name, sym_type in sample_symbols[:5]:
    try:
        print(f"   Processing {ticker}: {name}")
        
        import finpy_tse
        
        # Capture output
        f_out = io.StringIO()
        with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
            price_df = finpy_tse.Get_Price_History(
                stock=name,
                start_date='1400-01-01',
                end_date='1403-12-29',
                show_weekday=True,
                adjust_price=True
            )
        
        if price_df is not None and not price_df.empty:
            print(f"     Retrieved {len(price_df)} price rows")
            
            # Get symbol_id
            c.execute("SELECT id FROM symbols WHERE symbol = ?", (ticker,))
            symbol_row = c.fetchone()
            if symbol_row:
                symbol_id = symbol_row[0]
                
                # Insert price data
                insert_count = 0
                for _, row in price_df.iterrows():
                    try:
                        date_val = str(row.get('date', ''))[:10] if row.get('date') else ''
                        if not date_val:
                            continue
                            
                        c.execute('''
                            INSERT OR REPLACE INTO price_data 
                            (symbol_id, date, weekday, open, high, low, close, final_price,
                             volume, value, adj_close, adj_final,
                             sma_20, sma_50, rsi, macd, macd_signal, macd_histogram)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            symbol_id,
                            date_val,
                            int(row.get('Weekday', 0)),
                            float(row.get('open', 0)),
                            float(row.get('high', 0)),
                            float(row.get('Low', 0)),
                            float(row.get('Close', 0)),
                            float(row.get('Final', 0)),
                            int(row.get('volume', 0)),
                            float(row.get('value', 0)),
                            float(row.get('adj_close', 0)),
                            float(row.get('adj_final', 0)),
                            float(row.get('SMA_20', 0)),
                            float(row.get('SMA_50', 0)),
                            float(row.get('RSI', 0)),
                            float(row.get('MACD', 0)),
                            float(row.get('MACD_Signal', 0)),
                            float(row.get('MACD_Histogram', 0))
                        ))
                        insert_count += 1
                    except Exception as e:
                        pass
                
                conn.commit()
                print(f"     Inserted {insert_count} rows")
            else:
                print("     Symbol not found in DB")
        else:
            print("     No data retrieved")
            
    except Exception as e:
        print(f"     Error: {e}")

# Step 4: Final verification
print("\n4. Final Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"   Total symbols: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"   Price data rows: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM indices_data")
print(f"   Indices data: {c.fetchone()[0]}")

conn.close()
print("\nExtraction complete!")
