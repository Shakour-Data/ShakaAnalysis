#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Symbol extraction from HTML table data captured from finpy_tse
"""

import sqlite3
import ssl
import sys
import os
import html
import re
import io

# Setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# SSL Bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

import urllib3
_orig_pool = urllib3.PoolManager.__init__
def _patched(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return _orig_pool(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get
requests.Session.get = _patched_get

from src.database import get_db_connection, initialize_database

DB_PATH = 'data/market_data.db'

# Step 1: Initialize database
print("Step 1: Initializing database...")
initialize_database(DB_PATH)

# Step 2: Get symbols from finpy_tse, suppressing stdout
print("Step 2: Fetching symbols from TSE...")
import finpy_tse

# Save original stdout
original_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    df = finpy_tse.Build_Market_StockList(
        bourse=True, farabourse=True, payeh=True,
        detailed_list=True, show_progress=False,
        save_excel=False, save_csv=False
    )
    sys.stdout = original_stdout
    output = sys.stdout.getvalue() if hasattr(sys.stdout, 'getvalue') else ""
    
    # Check what we got
    if isinstance(df, str):
        print(f"Returned HTML string ({len(df)} chars), parsing...")
        # Parse the HTML table
        from bs4 import BeautifulSoup
        import pandas as pd
        
        soup = BeautifulSoup(df, 'html.parser')
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        if tables:
            parsed_dfs = pd.read_html(str(tables[0]))
            if parsed_dfs:
                df = parsed_dfs[0]
                print(f"Parsed table: {len(df)} rows")
    elif hasattr(df, 'shape'):
        print(f"Returning DataFrame: {df.shape}")
    else:
        print(f"Unexpected type: {type(df)}")
    
except Exception as e:
    sys.stdout = original_stdout
    print(f"Error: {e}")
    output = ""
    
# Step 3: Process extracted symbols
if df is not None:
    print(f"\nProcessing {len(df)} symbols...")
    
    # Get column names to identify correct columns
    print(f"Columns: {list(df.columns)}")
    
    # Check if required columns exist
    if 'Ticker' in df.columns and 'Name' in df.columns:
        symbols_to_insert = []
        
        for _, row in df.iterrows():
            ticker = str(row.get('Ticker', '')).strip()
            name = str(row.get('Name', '')).strip()
            
            if ticker and ticker != '\u200b' and ticker != 'nan':
                market = str(row.get('Market', '')).strip()
                webid = str(row.get('WEB-ID', '')).strip()
                
                # Determine exchange and type
                if 'بورس' in market:
                    exchange = 'TSE'
                    symbol_type = 'Stock'
                elif 'فرابورس' in market:
                    exchange = 'OTC'
                    symbol_type = 'Stock'
                else:
                    exchange = 'TSE'
                    symbol_type = 'Stock'
                
                symbols_to_insert.append((
                    ticker, name, symbol_type, exchange,
                    str(row.get('صنعت', 'Unknown')),
                    str(row.get('Market', 'Unknown')),
                    webid, 'IR', 'IRR', 1
                ))
        
        print(f"Found {len(symbols_to_insert)} valid symbols to insert")
        
        # Insert into database
        conn = get_db_connection(DB_PATH)
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT OR IGNORE INTO symbols 
            (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', symbols_to_insert[:500])  # Insert top 500 first
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM symbols')
        count = cursor.fetchone()[0]
        print(f"Symbols in database: {count}")
        
        conn.close()
    else:
        print("Required columns not found in DataFrame")
else:
    print("No data extracted")