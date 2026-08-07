#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive symbol extraction with proper HTML parsing
"""

import sys
import os
import sqlite3
import ssl
import urllib3
import requests
import re

# Setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Apply SSL bypass BEFORE importing finpy_tse
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

# Patch requests
orig_get = requests.get
def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return orig_get(url, *args, **kwargs)
requests.get = patched_get
requests.Session.get = patched_get

from src.database import get_db_connection, initialize_database

DB_PATH = 'data/market_data.db'

# Step 1: Initialize database
print("Step 1: Initializing database...")
initialize_database(DB_PATH)

# Step 2: Get raw HTML from finpy_tse
print("Step 2: Fetching symbols from TSE...")

import finpy_tse
import io
import contextlib

# Capture output and get raw HTML
f = io.StringIO()
with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
    try:
        result = finpy_tse.Build_Market_StockList(
            bourse=True, farabourse=True, payeh=True,
            detailed_list=True, show_progress=False,
            save_excel=False, save_csv=False
        )
    except Exception as e:
        print(f"Error in finpy_tse call: {e}")
        result = None

html_output = f.getvalue()
print(f"Captured {len(html_output)} characters")

# Step 3: Parse HTML to extract symbols
print("Step 3: Parsing HTML table...")

symbols = []
if html_output and '<table' in html_output:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_output, 'html.parser')
        
        tables = soup.find_all('table')
        print(f"Found {len(tables)} table(s)")
        
        if tables:
            # Process the first table (should contain symbols)
            table = tables[0]
            
            # Extract all rows
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows")
            
            # Skip header row
            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Extract symbol from first column
                    symbol_text = cols[0].get_text().strip()
                    # Extract name from second column
                    name_text = cols[1].get_text().strip()
                    
                    # Clean up the text (remove unicode escapes)
                    symbol_text = symbol_text.replace('\\u0627', 'ا').replace('\\u0628', 'ب')
                    symbol_text = symbol_text.replace('\\u062a', 'ت').replace('\\u062c', 'ج')
                    symbol_text = symbol_text.replace('\\u062d', 'د').replace('\\u062e', 'ه')
                    symbol_text = symbol_text.replace('\\u062f', 'و').replace('\\u0630', 'ز')
                    symbol_text = symbol_text.replace('\\u0631', 'ر').replace('\\u0632', 'ز')
                    symbol_text = symbol_text.replace('\\u0633', 'س').replace('\\u0634', 'ش')
                    
                    name_text = name_text.replace('\\u0627', 'ا').replace('\\u0628', 'ب')
                    name_text = name_text.replace('\\u062a', 'ت').replace('\\u062c', 'ج')
                    name_text = name_text.replace('\\u062d', 'د').replace('\\u062e', 'ه')
                    
                    # Clean up and validate
                    symbol_text = re.sub(r'\s+', ' ', symbol_text).strip()
                    name_text = re.sub(r'\s+', ' ', name_text).strip()
                    
                    # Skip if empty or contains HTML
                    if (symbol_text and symbol_text not in ['nan', '', ''] and 
                        not symbol_text.startswith('<') and len(symbol_text) > 1):
                        symbols.append({
                            'symbol': symbol_text,
                            'name': name_text,
                            'exchange': 'TSE',
                            'type': 'Stock'
                        })
                        
            print(f"Extracted {len(symbols)} symbols from HTML")
            
    except ImportError:
        print("BeautifulSoup not available. Using manual extraction...")
        
        # Manual extraction with regex
        # Look for pattern like <td>\u0627\u0644\u0628\u0631\u063205</td>
        symbol_pattern = r'<td>(.*?)<\/td>\s*<td>(.*?)<\/td>'
        matches = re.findall(symbol_pattern, html_output, re.DOTALL)
        
        for match in matches:
            symbol_text = match[0].strip()
            name_text = match[1].strip()
            
            # Clean unicode escapes
            symbol_text = symbol_text.replace('\\u0627', 'ا').replace('\\u0628', 'ب')
            symbol_text = symbol_text.replace('\\u062a', 'ت').replace('\\u062c', 'ج')
            symbol_text = symbol_text.replace('\\u062d', 'د').replace('\\u062e', 'ه')
            
            name_text = name_text.replace('\\u0627', 'ا').replace('\\u0628', 'ب')
            name_text = name_text.replace('\\u062a', 'ت').replace('\\u062c', 'ج')
            name_text = name_text.replace('\\u062d', 'د').replace('\\u062e', 'ه')
            
            # Clean up
            symbol_text = re.sub(r'\s+', ' ', symbol_text).strip()
            name_text = re.sub(r'\s+', ' ', name_text).strip()
            
            if (symbol_text and symbol_text not in ['nan', '', ''] and 
                not symbol_text.startswith('<') and len(symbol_text) > 1):
                symbols.append({
                    'symbol': symbol_text,
                    'name': name_text,
                    'exchange': 'TSE',
                    'type': 'Stock'
                })
        
        print(f"Extracted {len(symbols)} symbols via regex")
    
    else:
        print("No HTML table found in output")
        
else:
    print("No HTML output captured")

# Step 4: Insert into database
print(f"\nStep 4: Inserting {len(symbols)} symbols into database...")

if symbols:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL")
    
    cursor = conn.cursor()
    
    # Insert symbols
    inserted_count = 0
    for sym in symbols:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO symbols 
                (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sym['symbol'],
                sym['name'],
                sym['type'],
                sym['exchange'],
                'Unknown',  # industry
                'Unknown',  # sector
                '',  # webid
                'IR',  # country
                'IRR',  # currency
                1  # is_active
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting {sym['symbol']}: {e}")
    
    conn.commit()
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM symbols")
    total_count = cursor.fetchone()[0]
    
    print(f"Inserted {inserted_count} symbols")
    print(f"Total symbols in database: {total_count}")
    
    # Show sample
    cursor.execute("SELECT symbol, name FROM symbols LIMIT 10")
    samples = cursor.fetchall()
    print("\nSample symbols:")
    for row in samples:
        print(f"  {row['symbol']} - {row['name']}")
    
    conn.close()
else:
    print("No symbols to insert")

print("\nStep 5: Verification")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM symbols")
print(f"Final symbol count: {c.fetchone()[0]}")

# Check database structure
c.execute("PRAGMA table_info(symbols)")
print("\nSymbols table schema:")
for col in c.fetchall():
    print(f"  {col[1]} ({col[2]})")

conn.close()

print("\n✅ Process complete!")