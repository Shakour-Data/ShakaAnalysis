#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, sqlite3, pandas as pd
import ssl, urllib3, requests
from datetime import datetime
from finpy_tse import Get_Price_History

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
urllib3.PoolManager.__init__ = lambda self, *a, **k: (setattr(self, 'ssl_context', ctx) or urllib3.PoolManager.__init__(self, *a, **k))
requests.get = lambda url, *a, **k: requests.get(url, verify=False, timeout=180, *a, **k)

def update_data():
    conn = sqlite3.connect("data/market_data.db")
    c = conn.cursor()
    c.execute("SELECT id, symbol FROM symbols WHERE is_active = 1")
    symbols = c.fetchall()
    
    for sym_id, symbol in symbols:
        c.execute("SELECT MAX(date) FROM price_data WHERE symbol_id = ?", (sym_id,))
        last_date = c.fetchone()[0]
        if not last_date:
            continue
        try:
            df = Get_Price_History(stock=symbol, start_date=last_date, end_date=datetime.now().strftime("%Y-%m-%d"))
            if df is not None and not df.empty:
                for jdate in df.index:
                    row = df.loc[jdate]
                    c.execute("INSERT OR REPLACE INTO price_data (symbol_id, date, open, high, low, close, final_price, volume, value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (sym_id, str(jdate), row.get('Open',0), row.get('High',0), row.get('Low',0), row.get('Close',0), row.get('Final',0), row.get('Volume',0), row.get('Value',0)))
                conn.commit()
                print("Updated", symbol, ":", len(df), "rows")
        except Exception as e:
            print("Error updating", symbol, ":", e)
    conn.close()
    print("Daily update complete.")

if __name__ == "__main__":
    update_data()
