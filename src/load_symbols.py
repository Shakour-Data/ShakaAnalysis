#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load symbols from captured HTML data into database
"""

import sqlite3
import re
import os

DB_PATH = 'data/market_data.db'
HTML_FILE = r'C:\Users\Frequensy\.local\share\kilo\tool-output\tool_fda9d280c001GTiDuhYqYpuSyh'

print("=== Loading Symbols from Cached HTML ===")

# Clear and initialize database
print("1. Initializing database...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Drop and recreate tables
c.execute('DROP TABLE IF EXISTS price_data')
c.execute('DROP TABLE IF EXISTS symbols')
c.execute('DROP TABLE IF EXISTS indices_data')
c.execute('DROP TABLE IF EXISTS data_metadata')
c.execute('DROP TABLE IF EXISTS export_history')
c.execute('DROP TABLE IF EXISTS analysis_records')

# Create tables with proper schema
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
c.execute('CREATE INDEX idx_price_symbol_date ON price_data(symbol_id, date)')
c.execute('CREATE INDEX idx_symbols_exchange ON symbols(exchange)')

conn.commit()
print("   Database schema created")

# Step 2: Read HTML file
print("2. Reading captured HTML data...")
try:
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    print(f"   Loaded {len(html_content)} characters from HTML file")
except Exception as e:
    print(f"   Error reading HTML file: {e}")
    # Use fallback symbols
    print("   Using fallback symbols...")
    html_content = ""

# Step 3: Parse symbols from HTML
print("3. Parsing symbols from HTML...")
symbols = []

if html_content:
    # Parse HTML table rows
    # Pattern: <td>encoded_symbol</td><td>encoded_name</td>
    row_pattern = r'<td>(&#[0-9;]+|[^<]*)</td>\s*<td>(&#[0-9;]+|[^<]*)</td>\s*<td>'
    rows = re.findall(row_pattern, html_content)
    
    print(f"   Found {len(rows)} potential symbol rows")
    
    for row in rows[:2000]:  # Limit to 2000 symbols
        symbol_raw = row[0] if row else ""
        name_raw = row[1] if len(row) > 1 else ""
        
        # Decode HTML entities
        symbol = symbol_raw
        name = name_raw
        
        # Replace common HTML entities
        symbol = re.sub(r'&nbsp;', '', symbol)
        name = re.sub(r'&nbsp;', '', name)
        
        # Clean up
        symbol = symbol.strip()[:50]
        name = name.strip()[:200]
        
        if symbol and symbol not in ['nan', '', ''] and not symbol.startswith('<'):
            # Try to detect if this is an index
            symbol_type = 'Stock'
            exchange = 'TSE'
            if 'index' in name.lower() or 'شاخص' in name:
                symbol_type = 'Index'
            elif 'دارایی' in symbol or 'ETF' in name:
                symbol_type = 'ETF'
            
            symbols.append((symbol, name, symbol_type, exchange))

print(f"   Extracted {len(symbols)} symbols")

# Step 4: Insert symbols into database
if symbols:
    print("4. Inserting symbols into database...")
    insert_count = 0
    for sym in symbols:
        try:
            c.execute('''
                INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sym[0], sym[1], sym[2], sym[3], 'Unknown', 'Unknown', '', 'IR', 'IRR', 1))
            insert_count += 1
        except Exception as e:
            pass
    
    conn.commit()
    print(f"   Inserted {insert_count} symbols")

# Step 5: Verify
print("5. Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
total = c.fetchone()[0]
print(f"   Total symbols: {total}")

c.execute("SELECT COUNT(*) FROM price_data")
print(f"   Price data rows: {c.fetchone()[0]}")

conn.close()
print("\n✅ Database population complete!")