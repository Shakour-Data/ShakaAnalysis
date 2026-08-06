#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate database from JSON files."""

import json
import os
import sqlite3
from datetime import datetime

PROJECT_DIR = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'market_data.db')

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all JSON files
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('_data.json')]
    
    for file in json_files:
        symbol = file.replace('_data.json', '')
        json_path = os.path.join(DATA_DIR, file)
        
        # Check if symbol exists
        cur.execute('SELECT id FROM symbols WHERE symbol = ?', (symbol,))
        row = cur.fetchone()
        
        if row:
            sym_id = row['id']
        else:
            # Insert new symbol with valid constraint values
            cur.execute('''INSERT INTO symbols 
                           (symbol, name, type, exchange, industry, sector, 
                            webid, country, currency, is_active)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)''',
                       (symbol, symbol, 'Stock', 'TSE', 'Financial', 'Banking', '', 'Iran', 'IRR'))
            sym_id = cur.lastrowid
        
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f'Processing symbol: {len(data)} records')
        
        # Insert price data - map JSON keys to database columns
        for rec in data:
            # Map JSON keys to database columns
            date_val = rec.get('Date', '')
            open_val = rec.get('Open', 0) or 0
            high_val = rec.get('High', 0) or 0
            low_val = rec.get('Low', 0) or 0
            close_val = rec.get('Close', 0) or 0
            final_val = rec.get('Final', close_val) or close_val
            volume_val = rec.get('Volume', 0) or 0
            value_val = volume_val * close_val
            adj_close_val = rec.get('Adj Close')
            adj_final_val = rec.get('Adj Final')
            rsi_val = rec.get('RSI_14')  # Use RSI_14 as default
            macd_val = rec.get('MACD')
            macd_signal_val = rec.get('MACD_Signal')
            macd_hist_val = rec.get('MACD_Hist')
            bb_upper_val = rec.get('BB_50_upper')  # Use BB_50 as default
            bb_lower_val = rec.get('BB_50_lower')
            adx_val = rec.get('ADX_14')
            cci_val = rec.get('CCI_14')
            mfi_val = rec.get('MFI_14')
            ma_100_val = rec.get('MA100')
            
            cur.execute('''INSERT OR REPLACE INTO price_data 
                            (symbol_id, date, weekday, open, high, low, close, final_price, volume, value,
                             adj_close, adj_final,
                             sma_20, sma_50, rsi, macd, macd_signal, macd_histogram,
                             bb_upper, bb_lower, adx, cci, mfi, ma_100, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sym_id, date_val, rec.get('Weekday', ''), 
                 open_val, high_val, low_val, close_val, final_val, volume_val, value_val,
                 adj_close_val, adj_final_val,
                 None, None,  # sma_20, sma_50 - will compute if needed
                 rsi_val, macd_val, macd_signal_val, macd_hist_val,
                 bb_upper_val, bb_lower_val, adx_val, cci_val, mfi_val, ma_100_val,
                 datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f'Successfully populated database with {len(json_files)} symbols')

if __name__ == '__main__':
    main()