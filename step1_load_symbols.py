#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 1: Load symbols from cached HTML output of finpy_tse.Build_Market_StockList
"""

import sqlite3
import re
import os
import sys
from pathlib import Path

# Ensure we can write to console without Unicode errors on Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = 'data/market_data.db'
HTML_FILE = r'C:\Users\Frequensy\.local\share\kilo\tool-output\tool_fda9d280c001GTiDuhYqYpuSyh'

print("=== Step 1: Loading Symbols from Cached HTML ===")

# Initialize database
print("1. Initializing database...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Drop and recreate tables to start fresh
c.execute('DROP TABLE IF EXISTS price_data')
c.execute('DROP TABLE IF EXISTS symbols')
c.execute('DROP TABLE IF EXISTS indices_data')
c.execute('DROP TABLE IF EXISTS data_metadata')
c.execute('DROP TABLE IF EXISTS export_history')
c.execute('DROP TABLE IF EXISTS analysis_records')

# Create tables
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

# Create indexes
c.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_data(symbol_id, date)')
c.execute('CREATE INDEX IF NOT EXISTS idx_symbols_exchange ON symbols(exchange)')

conn.commit()
print("   Database schema created")

# Step 2: Read HTML file
print(f"2. Reading HTML from: {HTML_FILE}")
if not os.path.exists(HTML_FILE):
    print(f"   ERROR: File not found: {HTML_FILE}")
    # Try alternative path
    HTML_FILE = r'C:\Users\Frequensy\.local\share\kilo\tool-output\tool_fda9d280c001GTiDuhYqYpuSyh'
    if not os.path.exists(HTML_FILE):
        print("   Cannot find HTML file. Exiting.")
        conn.close()
        sys.exit(1)

try:
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    print(f"   Loaded {len(html_content)} characters from HTML file")
except Exception as e:
    print(f"   Error reading HTML file: {e}")
    conn.close()
    sys.exit(1)

# Step 3: Parse symbols from HTML
print("3. Parsing symbols from HTML...")
symbols = []

# Try to parse with pandas read_html first (more robust)
try:
    import pandas as pd
    from io import StringIO
    
    # Use StringIO to simulate a file
    html_io = StringIO(html_content)
    # Try to read tables
    tables = pd.read_html(html_io)
    print(f"   Found {len(tables)} tables via pandas")
    
    if tables:
        # Use the first table (should contain the symbol list)
        df = tables[0]
        print(f"   Table shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        
        # Try to identify symbol and name columns
        symbol_col = None
        name_col = None
        for col in df.columns:
            col_str = str(col).lower()
            if 'ticker' in col_str or 'symbol' in col_str or 'کد' in col_str:
                symbol_col = col
            if 'name' in col_str or 'نام' in col_str or 'company' in col_str or 'ف perusahaan' in col_str:
                name_col = col
        
        # If not found, use first two columns
        if symbol_col is None and len(df.columns) > 0:
            symbol_col = df.columns[0]
        if name_col is None and len(df.columns) > 1:
            name_col = df.columns[1]
        
        print(f"   Using symbol column: {symbol_col}")
        print(f"   Using name column: {name_col}")
        
        # Extract symbols
        for _, row in df.iterrows():
            symbol_val = str(row[symbol_col]).strip() if symbol_col in row and pd.notna(row[symbol_col]) else ''
            name_val = str(row[name_col]).strip() if name_col in row and pd.notna(row[name_col]) else ''
            
            # Clean up
            symbol_val = re.sub(r'\s+', ' ', symbol_val).strip()
            name_val = re.sub(r'\s+', ' ', name_val).strip()
            
            # Skip if empty or looks like HTML
            if (symbol_val and symbol_val not in ['nan', '', 'NaN', 'None'] and 
                not symbol_val.startswith('<') and len(symbol_val) >= 1):
                # Determine type and exchange based on market column if available
                symbol_type = 'Stock'
                exchange = 'TSE'
                # Check if there's a market column
                market_col = None
                for col in df.columns:
                    if 'market' in str(col).lower() or 'بازار' in str(col):
                        market_col = col
                        break
                if market_col and market_col in row:
                    market_val = str(row[market_col]).strip()
                    if 'فرابورس' in market_val:
                        exchange = 'OTC'
                    elif 'بورس' in market_val:
                        exchange = 'TSE'
                    else:
                        exchange = 'TSE'  # default
                else:
                    # Heuristic: if symbol looks like an index
                    if 'شاخص' in name_val or 'index' in name_val.lower() or 'ETF' in name_val.upper():
                        symbol_type = 'Index'
                        exchange = 'TSE'  # indices are usually on TSE
                
                symbols.append((symbol_val, name_val, symbol_type, exchange))
        
        print(f"   Extracted {len(symbols)} symbols from table")
    
except Exception as e:
    print(f"   Error parsing with pandas: {e}")
    import traceback
    traceback.print_exc()
    # Fallback to regex parsing
    print("   Falling back to regex parsing...")
    
    # Look for table rows with two <td> elements
    # Pattern: <td>content</td><td>content</td>
    # We'll capture content between <td> and </td>
    td_pattern = r'<td[^>]*>(.*?)</td>'
    td_matches = re.findall(td_pattern, html_content, re.DOTALL)
    
    # Process in pairs (symbol, name)
    for i in range(0, len(td_matches)-1, 2):
        symbol_raw = td_matches[i]
        name_raw = td_matches[i+1] if i+1 < len(td_matches) else ''
        
        # Clean HTML entities and extra whitespace
        symbol = re.sub(r'&[a-z]+;', '', symbol_raw).strip()
        name = re.sub(r'&[a-z]+;', '', name_raw).strip()
        
        # Remove any remaining HTML tags
        symbol = re.sub(r'<[^>]+>', '', symbol)
        name = re.sub(r'<[^>]+>', '', name)
        
        # Trim whitespace
        symbol = symbol.strip()
        name = name.strip()
        
        if symbol and symbol not in ['nan', '', 'NaN', 'None'] and len(symbol) <= 20:
            # Heuristic for type/exchange
            symbol_type = 'Stock'
            exchange = 'TSE'
            if 'شاخص' in name or 'index' in name.lower() or 'ETF' in name.upper():
                symbol_type = 'Index'
            elif 'فرابورس' in name or 'OTC' in name.upper():
                exchange = 'OTC'
            
            symbols.append((symbol, name, symbol_type, exchange))
    
    print(f"   Extracted {len(symbols)} symbols via regex")

# Step 4: Insert symbols into database
print(f"4. Inserting {len(symbols)} symbols into database...")
inserted = 0
duplicates = 0
for sym in symbols:
    try:
        c.execute('''
            INSERT OR IGNORE INTO symbols 
            (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sym[0], sym[1], sym[2], sym[3], 'Unknown', 'Unknown', '', 'IR', 'IRR', 1))
        if c.rowcount > 0:
            inserted += 1
        else:
            duplicates += 1
    except Exception as e:
        print(f"   Error inserting {sym[0]}: {e}")

conn.commit()
print(f"   Inserted {inserted} new symbols, {duplicates} duplicates skipped")

# Step 5: Verification
print("5. Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
total_symbols = c.fetchone()[0]
print(f"   Total symbols in database: {total_symbols}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"   Price data rows: {c.fetchone()[0]}")

# Show sample
print("\n6. Sample symbols (first 10):")
c.execute("SELECT symbol, name, type, exchange FROM symbols ORDER BY id LIMIT 10")
for row in c.fetchall():
    print(f"   {row[0]} - {row[1]} ({row[2]}, {row[3]})")

conn.close()
print("\n��✅ Step 1 complete!")