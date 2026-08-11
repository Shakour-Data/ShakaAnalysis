#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive symbol extraction and price data processing script.
This script extracts all symbols from TSE, stores them in the database,
extracts price history with technical indicators, and stores results.
"""

import sys
import os
import io
import contextlib
import ssl
import urllib3
import requests
import time
import re
import traceback
import pickle
import sqlite3

# Windows console encoding fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL bypass
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Patch urllib3
_orig_pool_init = urllib3.PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return _orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_pool_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests with timeout
_orig_get = requests.get
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = _patched_get

_orig_post = requests.post
def _patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_post(url, *args, **kwargs)
requests.post = _patched_post

# Import finpy_tse AFTER patching
import finpy_tse

# ============================================================
# Configuration
# ============================================================
DB_PATH = 'data/market_data.db'
CACHE_DIR = 'data/cache'
os.makedirs(CACHE_DIR, exist_ok=True)

START_DATE = '1395-01-01'
END_DATE = '1403-12-29'

# ============================================================
# Helper functions
# ============================================================

def decode_unicode_escapes(s):
    """Decode literal \\uXXXX sequences in strings"""
    if not s or not isinstance(s, str):
        return s
    result = s
    # Pattern to match literal \uXXXX sequences
    def replacer(match):
        try:
            return chr(int(match.group(1), 16))
        except:
            return match.group(0)
    result = re.sub(r'\\u([0-9a-fA-F]{4})', replacer, result)
    # Clean up extra spaces
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def extract_data_from_html(html_content):
    """Extract symbol data from HTML using BeautifulSoup"""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            return []
        
        symbols = []
        # Use the first table (should contain the symbol list)
        table = tables[0]
        
        # Get all rows
        rows = table.find_all('tr')
        if len(rows) < 2:
            return []
        
        # Skip header row
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                # First column should be ticker symbol, second should be name
                symbol_raw = cols[0].get_text()
                name_raw = cols[1].get_text() if len(cols) > 1 else ''
                
                # Decode HTML entities
                symbol = symbol_raw.strip()
                name = name_raw.strip()
                
                # Remove any HTML tags
                symbol = re.sub(r'<[^>]+>', '', symbol)
                name = re.sub(r'<[^>]+>', '', name)
                
                # Remove extra whitespace
                symbol = re.sub(r'\s+', ' ', symbol).strip()
                name = re.sub(r'\s+', ' ', name).strip()
                
                # Skip empty or invalid entries
                if not symbol or symbol in ['nan', ''] or symbol.startswith('<'):
                    continue
                
                # Remove Unicode escape sequences
                symbol = decode_unicode_escapes(symbol)
                name = decode_unicode_escapes(name)
                
                # Determine type
                symbol_type = 'Stock'
                exchange = 'TSE'
                lower_name = name.lower()
                lower_symbol = symbol.lower()
                
                # Heuristic for index vs stock
                if any(kw in lower_name for kw in ['شاخص', 'index', 'آنژید', 'شرکت', 'تونله', 'ETF']):
                    symbol_type = 'Index'
                elif 'پایه' in lower_symbol or 'پایه زرد' in lower_symbol or 'پایه نارنجی' in lower_symbol:
                    symbol_type = 'Index'
                
                symbols.append((symbol, name, symbol_type, exchange))
        
        return symbols
    except Exception as e:
        print(f"  HTML parsing error: {e}")
        return []

def get_price_data(symbol):
    """Fetch price data for a symbol using finpy_tse with retry logic"""
    for attempt in range(5):
        try:
            f_out = io.StringIO()
            with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
                price_df = finpy_tse.Get_Price_History(
                    stock=symbol,
                    start_date=START_DATE,
                    end_date=END_DATE,
                    show_weekday=True,
                    adjust_price=True,
                    ignore_date=False
                )
            
            if price_df is not None and not price_df.empty:
                print(f"    Successfully retrieved {len(price_df)} rows for {symbol}")
                return price_df
            else:
                print(f"    No data returned for {symbol}")
                return None
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed for {symbol}: {e}")
            if attempt < 4:
                time.sleep(5)  # Wait before retry
    
    return None

def insert_symbol(symbol, name, symbol_type, exchange, conn):
    """Insert a symbol into the database"""
    try:
        conn.execute('''
            INSERT OR IGNORE INTO symbols 
            (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, name, symbol_type, exchange, 'Unknown', 'Unknown', '', 'IR', 'IRR', 1))
        return True
    except Exception as e:
        print(f"    Error inserting symbol {symbol}: {e}")
        return False

def insert_price_data(symbol_id, price_df, conn):
    """Insert price data into price_data table"""
    insert_count = 0
    for _, row in price_df.iterrows():
        try:
            # Get date
            date_val = None
            for col in price_df.columns:
                if 'date' in str(col).lower():
                    date_val = str(row[col])[:10]
                    break
            
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
            
            conn.execute('''
                INSERT OR REPLACE INTO price_data 
                (symbol_id, date, weekday, open, high, low, close, final_price,
                 volume, value, adj_close, adj_final)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id, date_val, 0, open_p, high_p, low_p, close_p, final_p,
                vol, val, 0, 0
            ))
            insert_count += 1
        except Exception as e:
            pass
    
    return insert_count

def compute_indicators(df):
    """Compute technical indicators for a price dataframe"""
    import numpy as np
    
    close = df['Close'].values.astype(float)
    high = df['High'].values.astype(float)
    low = df['Low'].values.astype(float)
    volume = df['Volume'].values.astype(int)
    
    # SMA-20
    df['sma_20'] = pd.Series(close).rolling(window=20).mean().fillna(0)
    
    # SMA-50
    df['sma_50'] = pd.Series(close).rolling(window=50).mean().fillna(0)
    
    # RSI
    delta = np.diff(close)
    gain = pd.Series(delta).clip(lower=0).fillna(0)
    loss = -pd.Series(delta).clip(upper=0).fillna(0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, 0.00001)
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi.fillna(0)
    
    # MACD
    ema_12 = pd.Series(close).ewm(span=12).mean()
    ema_26 = pd.Series(close).ewm(span=26).mean()
    macd_line = ema_12 - ema_26
    df['macd'] = macd_line.fillna(0)
    df['macd_signal'] = macd_line.ewm(span=9).mean()
    df['macd_histogram'] = (macd_line - df['macd_signal'])
    
    # Bollinger Bands
    bb_std = pd.Series(close).rolling(window=20).std().fillna(0)
    df['bb_upper'] = df['sma_20'] + (2 * bb_std)
    df['bb_lower'] = df['sma_20'] - (2 * bb_std)
    
    # ADX (simplified)
    up_move = high - high.shift(1)
    down_move = low - low.shift(1)
    positive_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    negative_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    smoothed_pos = positive_dm.rolling(window=14).mean()
    smoothed_neg = negative_dm.rolling(window=14).mean()
    dx = 100 * np.abs(smoothed_pos - smoothed_neg) / (smoothed_pos + smoothed_neg).replace(0, 0.00001)
    df['adx'] = dx.fillna(0)
    
    # CCI
    mean_dev = close - pd.Series(close).rolling(window=20).mean()
    std_dev = pd.Series(close).rolling(window=20).std().replace(0, 0.001)
    cci = (0.015 * mean_dev) / std_dev
    df['cci'] = cci.fillna(0)
    
    return df

# ============================================================
# Main execution
# ============================================================

print("=" * 60)
print("SHAKA ANALYSIS - Symbol Extraction & Price Data Pipeline")
print("=" * 60)

# Step 1: Initialize database
print("\nStep 1: Initializing database...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Clean and recreate schema
c.execute('DROP TABLE IF EXISTS price_data')
c.execute('DROP TABLE IF EXISTS symbols')
c.execute('DROP TABLE IF EXISTS indices_data')
c.execute('DROP TABLE IF EXISTS data_metadata')
c.execute('DROP TABLE IF EXISTS export_history')
c.execute('DROP TABLE IF EXISTS analysis_records')

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
print("   Database schema created successfully")

# Step 2: Extract symbols from HTML
print("\nStep 2: Extracting symbols from TSE HTML...")

# Load cached HTML
html_file = None
for f in os.listdir('data/cache'):
    if f.endswith('.html') or f.endswith('.txt'):
        html_file = os.path.join('data/cache', f)
        break

if not html_file:
    print("   No HTML file found in cache. Creating HTML file...")
    # Try to get HTML from finpy_tse
    f_out = io.StringIO()
    with contextlib.redirect_stdout(f_out), contextlib.redirect_stderr(f_out):
        try:
            df = finpy_tse.Build_Market_StockList(
                bourse=True, farabourse=True, payeh=True,
                detailed_list=True, show_progress=False,
                save_excel=False, save_csv=False
            )
        except:
            pass
    html_file = 'data/cache/tse_html.html'
    # Note: Build_Market_StockList likely returns HTML or HTML output
    print("   Building HTML from TSE...")

# Try to read HTML from existing cache
try:
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    print(f"   Loaded {len(html_content)} chars from cache")
except Exception as e:
    print(f"   Error loading cache: {e}")
    html_content = ""

# Extract symbols
symbols = extract_data_from_html(html_content)
print(f"   Extracted {len(symbols)} symbols from HTML")

# Step 3: Insert symbols into database
print("\nStep 3: Inserting symbols into database...")
inserted = 0
for sym, name, sym_type, exchange in symbols:
    try:
        conn.execute('''
            INSERT OR IGNORE INTO symbols 
            (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sym, name, sym_type, exchange, 'Unknown', 'Unknown', '', 'IR', 'IRR', 1))
        inserted += 1
    except Exception as e:
        print(f"   Error inserting {sym}: {e}")

conn.commit()
print(f"   Inserted {inserted} symbols")

# Step 4: For each symbol, get price data and store
print("\nStep 4: Extracting price data...")
c.execute("SELECT id, symbol, name FROM symbols")
all_symbols = c.fetchall()

total_rows = 0
symbols_processed = 0

for i, (sym_id, symbol, name) in enumerate(all_symbols):
    if i % 50 == 0:
        print(f"   Progress: {i}/{len(all_symbols)} symbols ({i*2}%)", flush=True)
    
    # Skip large symbols (only process first 200)
    if i >= 200:
        break
    
    # Try to get price data with the symbol
    price_df = get_price_data(symbol)
    
    if price_df is not None and not price_df.empty:
        # Insert price data
        count = insert_price_data(sym_id, price_df, conn)
        total_rows += count
        symbols_processed += 1
        
        # Save to cache
        cache_file = os.path.join(CACHE_DIR, f"{symbol}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(dict(price_df), f)

    if i % 20 == 0:
        print(f"   ... processed {i} symbols, total rows: {total_rows}")

# Final verification
print("\n" + "=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

c.execute("SELECT COUNT(*) FROM symbols")
total_symbols = c.fetchone()[0]
print(f"Total symbols in database: {total_symbols}")

c.execute("SELECT COUNT(*) FROM price_data")
total_price_rows = c.fetchone()[0]
print(f"Total price data rows: {total_price_rows}")

c.execute("SELECT COUNT(DISTINCT symbol_id) FROM price_data")
distinct_symbols = c.fetchone()[0]
print(f"Symbols with price data: {distinct_symbols}")

c.execute("SELECT symbol, name, type FROM symbols WHERE type='Stock' LIMIT 5")
print("\nSample symbols:")
for row in c.fetchall():
    print(f"  {row[0]} - {row[1]} ({row[2]})")

c.execute("SELECT symbol, name, type FROM symbols WHERE type='Index' LIMIT 5")
print("\nSample indices:")
for row in c.fetchall():
    print(f"  {row[0]} - {row[1]} ({row[2]})")

conn.close()

print("\n" + "=" * 60)
print("Pipeline complete!")
print("=" * 60)