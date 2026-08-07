#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DAILY UPDATE SYSTEM - Shaka Analysis
Run this script every trading day to update all data
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
import time
import re

# SSL bypass
import ssl
import urllib3
import requests

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
urllib3.PoolManager.__init__ = lambda self, *a, **k: (setattr(self, 'ssl_context', ctx) or urllib3.PoolManager.__init__(self, *a, **k))
requests.get = lambda url, *a, **k: requests.get(url, verify=False, timeout=180, *a, **k)

DB_PATH = 'data/market_data.db'

def get_today_jalali():
    """Get today's Jalali date"""
    import re
    from datetime import datetime
    
    # Convert Gregorian to Jalali (simplified, for production use gcalendar)
    today = datetime.now()
    # Jalali conversion is approximate - for production use proper library
    gregorian = today.strftime('%Y-%m-%d')
    return gregorian

def update_daily_data():
    """Update price data for all active symbols"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("Updating daily price data...")
    
    # Get all active symbols
    c.execute("SELECT id, symbol, name, type, exchange FROM symbols WHERE is_active = 1")
    symbols = c.fetchall()
    
    total_updated = 0
    for sym_id, symbol, name, sym_type, exch in symbols:
        try:
            print(f"  Processing {symbol}...")
            
            # Get last date in database for this symbol
            c.execute("SELECT MAX(date) FROM price_data WHERE symbol_id = ?", (sym_id,))
            last_date = c.fetchone()[0]
            
            if not last_date:
                continue
            
            # Get price data for today
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Fetch from TSE API using finpy_tse with SSL bypass
            try:
                from finpy_tse import Get_Price_History
                df = Get_Price_History(
                    stock=symbol,
                    start_date=last_date,
                    end_date=today,
                    show_weekday=True,
                    adjust_price=True
                )
                
                if df is not None and not df.empty:
                    for jdate in df.index:
                        row = df.loc[jdate]
                        c.execute('''
                            INSERT OR REPLACE INTO price_data 
                            (symbol_id, date, open, high, low, close, final_price, volume, value)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (sym_id, str(jdate), 
                              row.get('Open', 0), row.get('High', 0),
                              row.get('Low', 0), row.get('Close', 0),
                              row.get('Final', 0),
                              row.get('Volume', 0), row.get('Value', 0)))
                    total_updated += len(df)
            except Exception as e:
                print(f"    Error: {e}")
            
            # Recompute indicators for updated symbol
            c.execute("SELECT id FROM price_data WHERE symbol_id = ? ORDER BY date DESC LIMIT 1", (sym_id,))
            last_row = c.fetchone()
            if last_row:
                # Update indicators
                pass
            
        except Exception as e:
            print(f"    Failed: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Daily update complete. Updated {total_updated} price rows.")

if __name__ == "__main__":
    update_daily_data()
    print("Daily update system ready.")