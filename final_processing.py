#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final processing script to extract price data and compute technical indicators.
"""

import sqlite3
import ssl
import urllib3
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import io
import contextlib
import os

# ===== 1. SSL BYPASS SETUP =====
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

# ===== 2. SYMBOL PROCESSING CONFIG =====
DB_PATH = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis\data\market_data.db'
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
CONFIG = {
    'MAX_SYMBOLS': 10,  # Process first 10 symbols
    'START_DATE': '1400-01-01',
    'END_DATE': '1403-12-29',
    'INCLUDE_INDICATORS': True,
}

# ===== 3. DATABASE CONNECTION =====
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ===== 4. TECHNICAL INDICATOR CALCULATIONS =====
def compute_indicators(prices):
    """Compute technical indicators from price data"""
    close_prices = prices['close'].values
    
    # Calculate SMA
    prices['sma_20'] = pd.Series(close_prices).rolling(window=20).mean().fillna(0)
    prices['sma_50'] = pd.Series(close_prices).rolling(window=50).mean().fillna(0)
    
    # Calculate RSI
    delta = close_prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, 500)
    prices['rsi'] = 100 - (100 / (1 + rs)).fillna(0)
    
    # Calculate MACD
    ema_12 = pd.Series(close_prices).ewm(span=12).mean()
    ema_26 = pd.Series(close_prices).ewm(span=26).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9).mean()
    prices['macd'] = macd_line.fillna(0)
    prices['macd_signal'] = signal_line.fillna(0)
    prices['macd_histogram'] = macd_line - signal_line
    
    # Calculate Bollinger Bands
    prices['bb_upper'] = prices['sma_20'] + (2 * prices['close'].rolling(window=20).std().fillna(0))
    prices['bb_lower'] = prices['sma_20'] - (2 * prices['close'].rolling(window=20).std().fillna(0))
    
    # ADX calculation (simplified)
    high_current = prices['high']
    low_current = prices['low']
    close_previous = close_prices[:-1]
    
    # Simple ADX using directional movement
    up_move = high_current - high_current.shift(1)
    down_move = low_current - low_current.shift(1)
    
    positive_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    negative_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Smoothed values
    smoothed_positive_dm = pd.Series(positive_dm).rolling(window=14).mean().fillna(0)
    smoothed_negative_dm = pd.Series(negative_dm).rolling(window=14).mean().fillna(0)
    
    # Calculate +DI and -DI
    tr = pd.Series([abs(x) for x in range(14)])  # Placeholder
    di_pos = 100 * smoothed_positive_dm / tr
    di_neg = 100 * smoothed_negative_dm / tr
    
    dx = 100 * abs(di_pos - di_neg) / (di_pos + di_neg)
    prices['adx'] = dx.fillna(0)
    
    # CCI calculation
    mean_dev = prices['close'] - prices['close'].rolling(window=20).mean()
    std_dev = prices['close'].rolling(window=20).std().replace(0, 1)
    prices['cci'] = (0.015 * mean_dev) / std_dev
    
    return prices

# ===== 5. MASTER PROCESSING FUNCTION =====
def process_symbol_prices(symbol_id, symbol_name, symbol_ticker):
    """Process price data for a single symbol and store in database"""
    print(f"\nProcessing {symbol_name} ({symbol_ticker})...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        import finpy_tse
        
        # Get price data
        print("  Fetching price history...")
        price_df = finpy_tse.Get_Price_History(
            stock=symbol_name,
            start_date=CONFIG['START_DATE'],
            end_date=CONFIG['END_DATE'],
            show_weekday=True,
            adjust_price=True
        )
        
        if price_df is None or price_df.empty:
            print(f"  ⚠️ No data for {symbol_ticker}")
            return
        
        print(f"  Retrieved {len(price_df)} price rows")
        
        # Process data
        if CONFIG.get('INCLUDE_INDICATORS', False):
            price_df = compute_indicators(price_df)
        
        # Insert data into database
        print("  Inserting into database...")
        insert_count = 0
        for _, row in price_df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO price_data 
                    (symbol_id, date, weekday, open, high, low, close, final_price,
                     volume, value, adj_close, adj_final, sma_20, sma_50,
                     rsi, macd, macd_signal, macd_histogram)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol_id,
                    str(row.get('date', ''))[:10],
                    int(row.get('Weekday', 0)),
                    float(row.get('open', 0)),
                    float(row.get('High', 0)),
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
                print(f"  Error inserting row: {e}")
        
        conn.commit()
        print(f"  ✓ Inserted {insert_count} rows for {symbol_ticker}")
        
    except Exception as ex:
        print(f"Error processing {symbol_ticker}: {ex}")
    finally:
        conn.close()

# ===== 6. MAIN EXECUTION =====
def main():
    print("=== Shaka Analysis - Price Data & Indicators ===")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get symbols from database
        cursor.execute("""
            SELECT symbol_id, symbol, name, type, exchange 
            FROM symbols 
            WHERE exchange = 'TSE' 
            LIMIT 10
        """)
        
        symbols = cursor.fetchall()
        print(f"Found {len(symbols)} symbols in database")
        
        if not symbols:
            print("No symbols found! Inserting sample symbols first...")
            # Insert sample symbols with known names
            sample_symbols = [
                ('10', 'پترول', 'Petroleum City Bank', 'Stock', 'TSE'),
                ('1', 'خرما', 'Kernel Corporation', 'Stock', 'TSE'),
                ('2', 'آسیا', 'Asia Bank', 'Stock', 'TSE')
            ]
            
            temp_conn = get_connection()
            temp_cursor = temp_conn.cursor()
            for sym in sample_symbols:
                try:
                    temp_cursor.execute('''
                        INSERT OR IGNORE INTO symbols 
                        (symbol, name, type, exchange)
                        VALUES (?, ?, ?, ?)
                    ''', sym)
                except Exception as e:
                    print(f"Insert error: {e}")
            temp_conn.commit()
            temp_conn.close()
            
            cursor.execute("""
                SELECT symbol_id, symbol, name, type, exchange 
                FROM symbols 
                WHERE exchange = 'TSE' 
                LIMIT 10
            """)
            symbols = cursor.fetchall()
        
        # Process each symbol
        processed_count = 0
        for symbol_row in symbols:
            symbol_id = symbol_row['symbol_id']
            symbol_ticker = symbol_row['symbol']
            symbol_name = symbol_row['name']
            
            print(f"\n▶ Processing {symbol_ticker}: {symbol_name}")
            
            process_symbol_prices(symbol_id, symbol_name, symbol_ticker)
            processed_count += 1
            
            if processed_count >= CONFIG['MAX_SYMBOLS']:
                break
        
        print(f"\n✅ Processed {processed_count} symbols")
        
        # Final verification
        cursor.execute("SELECT COUNT(*) FROM symbols")
        print(f"✅ Total symbols in database: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM price_data")  
        print(f"✅ Total price rows stored: {cursor.fetchone()[0]}")
        
    except Exception as ex:
        print(f"Main process error: {ex}")
    finally:
        conn.close()
        print("Database connection closed")

if __name__ == '__main__':
    main()