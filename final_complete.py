#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final fix: Decode Unicode escapes, continue extraction, compute indicators
"""

import sys
import os
import io
import sqlite3
import re
import time
import math

# Windows console fix
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# SSL bypass
import ssl
import urllib3
import requests

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

orig_pool_init = urllib3.PoolManager.__init__
def patched_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    return orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = patched_init
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_orig_get = requests.get
def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 180)
    return _orig_get(url, *args, **kwargs)
requests.get = patched_get
requests.Session.get = patched_get

import finpy_tse

DB_PATH = 'data/market_data.db'

def decode_unicode_escapes(s):
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

print("=== Final Fix: Decode & Complete ===")

# Connect
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Step 1: Fix Unicode escapes in database
print("1. Decoding Unicode escape sequences in symbols table...")
c.execute("SELECT id, symbol, name FROM symbols")
all_symbols = c.fetchall()

updated = 0
for s in all_symbols:
    decoded_sym = decode_unicode_escapes(s['symbol'])
    decoded_name = decode_unicode_escapes(s['name'])
    
    if decoded_sym != s['symbol'] or decoded_name != s['name']:
        c.execute("UPDATE symbols SET symbol = ?, name = ? WHERE id = ?",
                  (decoded_sym, decoded_name, s['id']))
        updated += 1

conn.commit()
print(f"   Updated {updated} symbols")

# Step 2: Show sample decoded symbols
print("\n2. Sample decoded symbols:")
c.execute("SELECT symbol, name, type, exchange FROM symbols ORDER BY id LIMIT 10")
for row in c.fetchall():
    print(f"   {row['symbol']} - {row['name'][:50]} ({row['type']}, {row['exchange']})")

# Step 3: Continue price extraction for missing symbols
print("\n3. Extracting remaining price data...")

# Find symbols that don't have price data yet
c.execute("""
    SELECT s.id, s.symbol, s.name 
    FROM symbols s 
    LEFT JOIN (SELECT DISTINCT symbol_id FROM price_data) p ON s.id = p.symbol_id 
    WHERE p.symbol_id IS NULL AND s.symbol NOT LIKE 'نماد%'
    ORDER BY s.id
""")
missing_symbols = c.fetchall()
print(f"   Found {len(missing_symbols)} symbols without price data")

total_new_rows = 0
processed = 0

for s in missing_symbols[:100]:  # Process next 100
    sym_id = s['id']
    symbol = s['symbol']
    name = s['name']
    
    # Get the first word of the name for search
    search_terms = [symbol, name.split()[0] if name else '', name[:20] if name else '']
    
    for search_term in search_terms:
        if not search_term or len(search_term) < 2:
            continue
            
        try:
            df = finpy_tse.Get_Price_History(
                stock=search_term,
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
                         volume, value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (sym_id, date_val, 0, open_p, high_p, low_p, close_p, final_p, vol, val))
                    inserted += 1
                
                conn.commit()
                print(f"   {s['id']}: {symbol} - {inserted} rows")
                total_new_rows += inserted
                processed += 1
                break
        except Exception:
            continue

print(f"\n   Processed {processed} symbols, {total_new_rows} new rows")

# Step 4: Compute technical indicators for existing price data
print("\n4. Computing technical indicators...")

c.execute("""
    SELECT DISTINCT symbol_id 
    FROM price_data 
    WHERE sma_20 IS NULL OR sma_20 = 0
    LIMIT 50
""")
symbols_to_update = c.fetchall()
print(f"   Found {len(symbols_to_update)} symbols needing indicators")

import numpy as np
import pandas as pd

for sym_row in symbols_to_update[:20]:
    sym_id = sym_row[0]
    
    # Get current price data
    df = pd.read_sql(f"SELECT * FROM price_data WHERE symbol_id = ? ORDER BY date", conn, params=[sym_id])
    
    if len(df) < 20:
        continue  # Not enough data for indicators
    
    # Compute indicators
    close = df['close'].values.astype(float)
    
    # SMA
    df['sma_20'] = pd.Series(close).rolling(window=20, min_periods=1).mean()
    df['sma_50'] = pd.Series(close).rolling(window=50, min_periods=1).mean()
    
    # RSI
    delta = pd.Series(close).diff()
    gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14, min_periods=1).mean()
    rs = gain / loss.replace(0, 0.0001)
    df['rsi'] = (100 - (100 / (1 + rs))).fillna(50)
    
    # MACD
    ema_12 = pd.Series(close).ewm(span=12, min_periods=1).mean()
    ema_26 = pd.Series(close).ewm(span=26, min_periods=1).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, min_periods=1).mean()
    df['macd'] = macd_line
    df['macd_signal'] = signal_line
    df['macd_histogram'] = macd_line - signal_line
    
    # Bollinger Bands
    bb_std = pd.Series(close).rolling(window=20, min_periods=1).std().fillna(0)
    df['bb_upper'] = df['sma_20'] + (2 * bb_std)
    df['bb_lower'] = df['sma_20'] - (2 * bb_std)
    
    # Update database
    for _, row in df.iterrows():
        c.execute('''
            UPDATE price_data 
            SET sma_20 = ?, sma_50 = ?, rsi = ?, macd = ?, macd_signal = ?,
                macd_histogram = ?, bb_upper = ?, bb_lower = ?
            WHERE id = ?
        ''', (
            float(row['sma_20']),
            float(row['sma_50']),
            float(row['rsi']),
            float(row['macd']),
            float(row['macd_signal']),
            float(row['macd_histogram']),
            float(row['bb_upper']),
            float(row['bb_lower']),
            int(row['id'])
        ))
    
    conn.commit()

print(f"   Computed indicators for {min(20, len(symbols_to_update))} symbols")

# Step 5: Final verification
print("\n5. Final Database Verification:")
c.execute("SELECT COUNT(*) FROM symbols")
print(f"   Total symbols: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data")
total_price = c.fetchone()[0]
print(f"   Total price data rows: {total_price}")

c.execute("SELECT COUNT(DISTINCT symbol_id) FROM price_data")
symbols_with_data = c.fetchone()[0]
print(f"   Symbols with price data: {symbols_with_data}")

# Check symbols with indicators
c.execute("SELECT COUNT(*) FROM price_data WHERE sma_20 IS NOT NULL AND sma_20 > 0")
print(f"   Rows with SMA_20 indicator: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data WHERE rsi IS NOT NULL AND rsi > 0")
print(f"   Rows with RSI indicator: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM price_data WHERE macd IS NOT NULL AND macd > 0")
print(f"   Rows with MACD indicator: {c.fetchone()[0]}")

# Show sample data with indicators
print("\n   Sample price data with indicators:")
c.execute("""
    SELECT s.symbol, s.name, p.date, p.open, p.high, p.low, p.close, 
           p.sma_20, p.rsi, p.macd
    FROM price_data p JOIN symbols s ON p.symbol_id = s.id
    WHERE p.sma_20 IS NOT NULL AND p.sma_20 > 0
    ORDER BY p.date DESC
    LIMIT 3
""")
for row in c.fetchall():
    print(f"   {row['symbol']}: {row['date']} - O={row['open']} H={row['high']} L={row['low']} C={row['close']} SMA20={row['sma_20']:.2f} RSI={row['rsi']:.2f} MACD={row['macd']:.4f}")

conn.close()
print("\n✅ All steps complete!")