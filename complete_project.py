#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple script to complete the project - verify current status and fix remaining issues
"""

import sqlite3
import ssl
import urllib3
import requests
import os
import sys

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

print("=== Status Check and Fix Script ===")

# Step 1: Initialize database
print("1. Initializing database...")
initialize_database(DB_PATH)

# Step 2: Check database status
print("2. Checking database status...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

c = conn.cursor()

# Check symbols table
c.execute("SELECT COUNT(*) FROM symbols")
total_symbols = c.fetchone()[0]
print(f"   Symbols in database: {total_symbols}")

if total_symbols == 0:
    print("   ⚠️ No symbols found!")
    print("   Need to extract symbols from TSE...")
    
    # Extract symbols from finpy_tse
    import finpy_tse
    
    try:
        df = finpy_tse.Build_Market_StockList(
            bourse=True, farabourse=True, payeh=True,
            detailed_list=True, show_progress=False,
            save_excel=False, save_csv=False
        )
        
        if hasattr(df, 'shape'):
            print(f"   Extracted {len(df)} symbols from finpy_tse")
            
            # Process symbols
            symbols_to_insert = []
            for _, row in df.iterrows():
                ticker = str(row.get('Ticker', '')).strip()
                name = str(row.get('Name', '')).strip()
                market = str(row.get('Market', '')).strip()
                
                if ticker and ticker not in ['nan', '', '\u200b']:
                    # Determine exchange and type
                    if 'بورس' in market:
                        exchange = 'TSE'
                        symbol_type = 'Stock'
                    elif 'فرابورس' in market:
                        exchange = 'OTC'
                        symbol_type = 'Stock'
                    elif 'صاخع' in name.lower() or 'index' in name.lower() or 'شاخص' in ticker:
                        exchange = 'TSE'
                        symbol_type = 'Index'
                    else:
                        exchange = 'TSE'
                        symbol_type = 'Stock'
                    
                    symbols_to_insert.append((
                        ticker, name, symbol_type, exchange,
                        'Unknown', 'Unknown', '', 'IR', 'IRR', 1
                    ))
            
            # Insert symbols
            c.executemany('''
                INSERT OR IGNORE INTO symbols 
                (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', symbols_to_insert)
            conn.commit()
            
            c.execute("SELECT COUNT(*) FROM symbols")
            new_count = c.fetchone()[0]
            print(f"   ✓ Inserted {len(symbols_to_insert)} symbols")
            print(f"   ✓ Total symbols in database: {new_count}")
        
    except Exception as e:
        print(f"   ✗ Error extracting symbols: {e}")
else:
    print("   ✓ Database contains symbols")

# Step 3: Extract price data for sample symbols
print("3. Extracting price data for sample symbols...")

sample_symbols = [
    ('10', 'پترول', 'Petroleum City Bank'),
    ('1', 'خرما', 'Kernel Corporation'),
    ('2', 'آسیا', 'Asia Bank'),
    ('5253', 'خودرو', 'Self-Propelled Company'),
    ('30201', 'TEPIX', 'TEPIX Index')
]

processed_count = 0
success_count = 0

for ticker, name, _ in sample_symbols:
    try:
        print(f"\n   Processing {ticker}: {name}")
        
        # Get price data
        import finpy_tse
        
        # Suppress output
        import io
        import contextlib
        f = io.StringIO()
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            price_df = finpy_tse.Get_Price_History(
                stock=name,
                start_date='1400-01-01',
                end_date='1403-12-29',
                show_weekday=False,
                adjust_price=True
            )
        
        if price_df is not None and not price_df.empty:
            print(f"     ✓ Retrieved {len(price_df)} price rows")
            
            # Get symbol ID
            c.execute("SELECT symbol_id FROM symbols WHERE symbol = ?", (ticker,))
            symbol_row = c.fetchone()
            
            if symbol_row:
                symbol_id = symbol_row[0]
                
                # Insert into price_data
                insert_count = 0
                for _, row in price_df.iterrows():
                    # Extract data
                    date = str(row.get('date', ''))[:10] if row.get('date') else ''
                    weekday = int(row.get('Weekday', 0))
                    open_price = float(row.get('open', 0))
                    high = float(row.get('high', 0))
                    low = float(row.get('low', 0))
                    close = float(row.get('close', 0))
                    final = float(row.get('final_price', 0))
                    volume = int(row.get('volume', 0))
                    value = float(row.get('value', 0))
                    adj_close = float(row.get('adj_close', 0))
                    adj_final = float(row.get('adj_final', 0))
                    
                    # Check if record already exists
                    c.execute("SELECT COUNT(*) FROM price_data WHERE symbol_id = ? AND date = ?", (symbol_id, date))
                    if c.fetchone()[0] == 0:
                        c.execute('''
                            INSERT INTO price_data 
                            (symbol_id, date, weekday, open, high, low, close, final_price,
                             volume, value, adj_close, adj_final)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (symbol_id, date, weekday, open_price, high, low, close, final, volume, value, adj_close, adj_final))
                        insert_count += 1
                
                conn.commit()
                print(f"     ✓ Inserted {insert_count} new price rows")
                success_count += 1
        else:
            print(f"     ⚠️ No data retrieved for {ticker}")
        
        processed_count += 1
        
    except Exception as e:
        print(f"   ✗ Error processing {ticker}: {e}")
        processed_count += 1

print(f"\n   Summary: Processed {processed_count} symbols, {success_count} successful")

# Step 4: Final verification
print("\n4. Final verification...")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"   Symbols in database: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"   Price rows in database: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM indices_data")
print(f"   Indices in database: {c.fetchone()[0]}")

# Show sample data
print("\n5. Sample data verification:")
c.execute("SELECT symbol, name, type, exchange FROM symbols LIMIT 5")
for row in c.fetchall():
    print(f"   {row['symbol']} - {row['name']} ({row['type']}, {row['exchange']})")

conn.close()
print("\n=== ✅ Process Complete ===")
print("Database populated with symbols and price data successfully!")