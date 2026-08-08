#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robust comprehensive symbol data extractor from finpy_tse.
Features:
  - Global SSL bypass (urllib3.PoolManager + requests)
  - Retry with exponential backoff on all network calls
  - Direct SQLite storage (symbols + price_data + indices_data)
  - Technical indicator computation (SMA, RSI, MACD, Bollinger, ADX, CCI, MFI)
"""

import sqlite3
import ssl
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import sys
import os
import time
import numpy as np
import pandas as pd
from datetime import datetime

# =============================================================================
# 1. GLOBAL SSL BYPASS (applied BEFORE importing finpy_tse)
# =============================================================================
print("[1/6] Applying global SSL bypass...")

_unverified_ctx = ssl.create_default_context()
_unverified_ctx.check_hostname = False
_unverified_ctx.verify_mode = ssl.CERT_NONE

_orig_pool_init = urllib3.PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = _unverified_ctx
    _orig_pool_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_pool_init

_orig_https_conn_init = urllib3.connection.HTTPSConnection.__init__
def _patched_https_conn_init(self, *args, **kwargs):
    kwargs['assert_hostname'] = False
    kwargs['cert_reqs'] = ssl.CERT_NONE
    _orig_https_conn_init(self, *args, **kwargs)
urllib3.connection.HTTPSConnection.__init__ = _patched_https_conn_init

_orig_requests_get = requests.get
_orig_requests_post = requests.post
_orig_session_get = requests.Session.get
_orig_session_post = requests.Session.post

def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_requests_get(url, *args, **kwargs)

def _patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_requests_post(url, *args, **kwargs)

def _patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_session_get(self, url, *args, **kwargs)

def _patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 120)
    return _orig_session_post(self, url, *args, **kwargs)

requests.get = _patched_get
requests.post = _patched_post
requests.Session.get = _patched_session_get
requests.Session.post = _patched_session_post

_retry_adapter = HTTPAdapter(
    max_retries=Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
)
_session = requests.Session()
_session.mount("http://", _retry_adapter)
_session.mount("https://", _retry_adapter)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
print("  [OK] SSL bypass and retry adapter applied")

# =============================================================================
# 2. IMPORT finpy_tse (now with SSL bypass active)
# =============================================================================
print("[2/6] Importing finpy_tse...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finpy_tse
print("  [OK] finpy_tse imported successfully")

# =============================================================================
# 3. DATABASE CONNECTION
# =============================================================================
print("[3/6] Connecting to database...")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from database import initialize_database, get_db_connection

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'market_data.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
initialize_database(DB_PATH)
conn = get_db_connection(DB_PATH)
cursor = conn.cursor()
print("  [OK] Database connected")

# =============================================================================
# 4. RETRY WRAPPER
# =============================================================================
def retry_call(func, *args, max_retries=3, base_delay=3, **kwargs):
    """Call func with exponential backoff retry."""
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                print(f"    Retry {attempt}/{max_retries} after {delay}s: {str(e)[:100]}")
                time.sleep(delay)
    raise last_exc

# =============================================================================
# 5. EXTRACT ALL SYMBOLS
# =============================================================================
print("[4/6] Extracting symbols from TSE...")

def fetch_symbols():
    df = retry_call(
        finpy_tse.Build_Market_StockList,
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=False,
        save_excel=False,
        save_csv=False
    )
    return df

df_symbols = fetch_symbols()
if df_symbols.empty:
    print("  [ERROR] No symbols found!")
    sys.exit(1)

print(f"  [OK] Found {len(df_symbols)} symbols in market list")

# Process symbols into list of tuples for DB insertion
symbols_to_insert = []
seen = set()

for _, row in df_symbols.iterrows():
    ticker = str(row.get('Ticker', '')).strip()
    name = str(row.get('Name', '')).strip()
    webid = str(row.get('WEB-ID', '')).strip()
    market = str(row.get('Market', '')).strip()

    if not ticker:
        continue

    ticker_clean = ''.join(ticker.split()).strip()
    if ticker_clean in seen:
        continue
    seen.add(ticker_clean)

    if market == 'بورس':
        exchange = 'TSE'
        sym_type = 'Stock'
    elif market == 'فرابورس':
        exchange = 'OTC'
        sym_type = 'Stock'
    elif 'صاخص' in name.lower() or 'index' in name.lower() or 'شاخص' in ticker:
        exchange = 'TSE'
        sym_type = 'Index'
    else:
        exchange = 'TSE'
        sym_type = 'Unknown'

    symbols_to_insert.append((
        ticker_clean, name, sym_type, exchange,
        'Unknown', market, webid, 'IR', 'IRR', 1
    ))

# Clear old data and insert fresh
cursor.execute('DELETE FROM price_data')
cursor.execute('DELETE FROM symbols')
cursor.execute('DELETE FROM indices')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="symbols"')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="price_data"')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="indices"')

cursor.executemany('''
    INSERT INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', symbols_to_insert)
conn.commit()
print(f"  [OK] Inserted {len(symbols_to_insert)} symbols into database")

# Add common indices
common_indices = [
    ('30201', 'TEPIX Index', 'Index', 'TSE'),
    ('10001', 'TSE Index', 'Index', 'TSE'),
    ('20101', 'TEDPIX Index', 'Index', 'TSE'),
    ('50101', 'TAFQ Index', 'Index', 'TSE'),
    ('20102', 'TEDIX Index', 'Index', 'TSE'),
]
for sym, name, stype, exchange in common_indices:
    if sym not in seen:
        cursor.execute('''
            INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sym, name, stype, exchange, 'Index', 'Market Index', '', 'IR', 'IRR', 1))
        seen.add(sym)
conn.commit()

# Get all stock symbols for price data extraction
cursor.execute("SELECT symbol, name, webid FROM symbols WHERE type = 'Stock'")
stock_symbols = cursor.fetchall()
print(f"  [OK] {len(stock_symbols)} stock symbols ready for price extraction")

# =============================================================================
# 6. EXTRACT PRICE DATA FOR EACH SYMBOL
# =============================================================================
print("[5/6] Extracting price data for each symbol...")

def fetch_price_history(symbol_name):
    return retry_call(
        finpy_tse.Get_Price_History,
        stock=symbol_name,
        start_date='1395-01-01',
        end_date='1403-12-29',
        ignore_date=True,
        adjust_price=True,
        show_weekday=False,
        double_date=False
    )

success_count = 0
fail_count = 0
total_price_rows = 0
batch_count = 0

for idx, (symbol, name, webid) in enumerate(stock_symbols):
    if idx % 20 == 0 and idx > 0:
        conn.commit()
        print(f"    Progress: {idx}/{len(stock_symbols)} symbols, {success_count} OK, {total_price_rows} rows")

    try:
        price_df = fetch_price_history(name)
    except Exception as e:
        print(f"    [WARN] Price fetch failed for {symbol} ({name}): {str(e)[:80]}")
        price_df = pd.DataFrame()

    if price_df.empty:
        fail_count += 1
        continue

    # Compute technical indicators
    if len(price_df) > 50:
        try:
            # Moving Averages for multiple time periods
            price_df['SMA_9'] = price_df['Close'].rolling(window=9).mean()
            price_df['SMA_14'] = price_df['Close'].rolling(window=14).mean()
            price_df['SMA_20'] = price_df['Close'].rolling(window=20).mean()
            price_df['SMA_21'] = price_df['Close'].rolling(window=21).mean()
            price_df['SMA_35'] = price_df['Close'].rolling(window=35).mean()
            price_df['SMA_50'] = price_df['Close'].rolling(window=50).mean()
            price_df['SMA_100'] = price_df['Close'].rolling(window=100).mean()
            
            # RSI for multiple time periods
            for window in [9, 14, 21, 35]:
                delta = price_df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss.replace(0, np.nan)
                price_df[f'RSI_{window}'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema12 = price_df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = price_df['Close'].ewm(span=26, adjust=False).mean()
            price_df['MACD'] = ema12 - ema26
            price_df['MACD_Signal'] = price_df['MACD'].ewm(span=9, adjust=False).mean()
            price_df['MACD_Histogram'] = price_df['MACD'] - price_df['MACD_Signal']
            
            # Bollinger Bands (using 20-period as standard)
            sma20 = price_df['Close'].rolling(window=20).mean()
            std20 = price_df['Close'].rolling(window=20).std()
            price_df['BB_Upper'] = sma20 + 2 * std20
            price_df['BB_Lower'] = sma20 - 2 * std20
            
            # ADX (Average Directional Index)
            tr = pd.concat([
                price_df['High'] - price_df['Low'],
                (price_df['High'] - price_df['Close'].shift(1)).abs(),
                (price_df['Low'] - price_df['Close'].shift(1)).abs()
            ], axis=1).max(axis=1)
            plus_dm = price_df['High'].diff()
            minus_dm = price_df['Low'].diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            di_plus = 100 * (plus_dm.ewm(span=14).mean() / tr.ewm(span=14).mean())
            di_minus = 100 * (minus_dm.ewm(span=14).mean() / tr.ewm(span=14).mean())
            dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus)
            price_df['ADX'] = dx.ewm(span=14).mean()
            
            # CCI (Commodity Channel Index)
            tp = (price_df['High'] + price_df['Low'] + price_df['Close']) / 3
            sma_tp = tp.rolling(window=20).mean()
            mad = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            price_df['CCI'] = (tp - sma_tp) / (0.015 * mad)
            
            # MFI (Money Flow Index)
            money_flow = tp * price_df['Volume']
            positive_flow = money_flow.where(tp > tp.shift(1), 0).rolling(window=14).sum()
            negative_flow = money_flow.where(tp < tp.shift(1), 0).rolling(window=14).sum()
            mfi_ratio = positive_flow / negative_flow.replace(0, np.nan)
            price_df['MFI'] = 100 - (100 / (1 + mfi_ratio))
            
        except Exception as e:
            print(f"    [WARN] Indicator calc failed for {symbol}: {str(e)[:60]}")

    # Rename columns to match DB schema
    rename_map = {
        'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close',
        'Final': 'final_price', 'Volume': 'volume', 'Value': 'value',
        'Adj Open': 'adj_close', 'Adj High': 'adj_high', 'Adj Low': 'adj_low',
        'Adj Close': 'adj_close', 'Adj Final': 'adj_final'
    }
    rename = {old: new for old, new in rename_map.items() if old in price_df.columns}
    price_df = price_df.rename(columns=rename)

    if 'close' not in price_df.columns or 'final_price' not in price_df.columns:
        fail_count += 1
        continue

    # Get symbol_id from DB
    cursor.execute("SELECT id FROM symbols WHERE symbol = ?", (symbol,))
    sym_row = cursor.fetchone()
    if sym_row is None:
        fail_count += 1
        continue
    symbol_id = sym_row['id']

# Insert price data rows
    rows_inserted = 0
    for _, rec in price_df.iterrows():
        try:
            cursor.execute('''
                INSERT INTO price_data (
                    symbol_id, date, weekday, open, high, low, close,
                    final_price, volume, value, adj_close, adj_final,
                    sma_9, sma_14, sma_20, sma_21, sma_35, sma_50, sma_100,
                    rsi, rsi_9, rsi_14, rsi_21, rsi_35,
                    macd, macd_signal, macd_histogram,
                    bb_upper, bb_lower, adx, cci, mfi, ma_100, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id,
                rec.get('date'),
                rec.get('Weekday'),
                rec.get('open'), rec.get('high'), rec.get('low'), rec.get('close'),
                rec.get('final_price'), rec.get('volume'), rec.get('value'),
                rec.get('adj_close'), rec.get('adj_final'),
                rec.get('SMA_9'), rec.get('SMA_14'), rec.get('SMA_20'), rec.get('SMA_21'), 
                rec.get('SMA_35'), rec.get('SMA_50'), rec.get('SMA_100'),
                rec.get('RSI_14'), rec.get('RSI_9'), rec.get('RSI_14'), rec.get('RSI_21'), rec.get('RSI_35'),
                rec.get('MACD'), rec.get('MACD_Signal'), rec.get('MACD_Histogram'),
                rec.get('BB_Upper'), rec.get('BB_Lower'), rec.get('ADX'), rec.get('CCI'), rec.get('MFI'), None,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            rows_inserted += 1
        except Exception:
            pass

    if rows_inserted > 0:
        success_count += 1
        total_price_rows += rows_inserted
        batch_count += rows_inserted
        if batch_count >= 5000:
            conn.commit()
            batch_count = 0
            print(f"    [COMMIT] {success_count} symbols, {total_price_rows} rows")
    else:
        fail_count += 1

conn.commit()
print(f"  [OK] Price data extraction complete: {success_count} symbols, {total_price_rows} rows")

# =============================================================================
# 7. FETCH AND STORE MARKET INDICES
# =============================================================================
print("[6/6] Fetching market indices...")

def fetch_index_history(func, name):
    try:
        df = retry_call(func, start_date='1395-01-01', end_date='1403-12-29', ignore_date=True, just_adj_close=False, show_weekday=False, double_date=False)
        if not df.empty:
            print(f"  [OK] {name}: {len(df)} records")
            return df
    except Exception as e:
        print(f"  [WARN] {name} fetch failed: {str(e)[:80]}")
    return pd.DataFrame()

indices_fetched = {}
for idx_name, fetch_func in [('TEPIX', finpy_tse.Get_CWI_History), ('TEDPIX', finpy_tse.Get_EWI_History)]:
    df_idx = fetch_index_history(fetch_func, idx_name)
    if not df_idx.empty:
        indices_fetched[idx_name] = df_idx

# Store indices in indices table
cursor.execute('DELETE FROM indices')
for idx_name, df_idx in indices_fetched.items():
    for _, row in df_idx.iterrows():
        try:
            cursor.execute('''
                INSERT INTO indices (symbol, name, date, open, high, low, close, volume, value, adj_close, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                idx_name, idx_name,
                row.get('Date') or row.get('J-Date'),
                row.get('Open'), row.get('High'), row.get('Low'), row.get('Close'),
                row.get('Volume'), row.get('Value'), row.get('Adj Close'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        except Exception:
            pass

conn.commit()
print(f"  [OK] Stored {len(indices_fetched)} index datasets")

# =============================================================================
# FINALIZE
# =============================================================================
cursor.execute("SELECT COUNT(*) FROM symbols")
total_syms = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM price_data")
total_rows = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM indices_data")
idx_rows = cursor.fetchone()[0]
cursor.execute("SELECT MIN(date), MAX(date) FROM price_data")
date_range = cursor.fetchone()

conn.close()

print("\n" + "=" * 80)
    print("DATABASE POPULATION COMPLETE")
    print("=" * 80)
    print(f"  Total symbols: {total_syms}")
    print(f"  Total price rows: {total_rows}")
    print(f"  Total index rows: {idx_rows}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    print(f"  Symbols with price data: {success_count}")
    print(f"  Symbols failed: {fail_count}")
    print("=" * 80)
    
    # Send notification
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scheduler'))
        from utils import notify_success
        message = f"Extraction complete: {total_syms} symbols, {total_rows} price rows"
        notify_success(message)
    except Exception as e:
        print(f"Failed to send notification: {e}")

except Exception as e:
    print(f"\n[ERROR] Extraction failed: {e}")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scheduler'))
        from utils import notify_error
        notify_error(f"Extraction failed: {e}")
    except:
        pass
    sys.exit(1)
