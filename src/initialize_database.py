#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shaka Analysis Database Initializer
"""

import sqlite3
import os

# Initialize database schema
conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Create symbols table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE,
        name TEXT,
        type TEXT,
        exchange TEXT,
        industry TEXT,
        sector TEXT,
        webid TEXT,
        country TEXT,
        currency TEXT,
        is_active INTEGER
    )''')

# Create price_data table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER,
        date DATE,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        sma_20 REAL,
        sma_50 REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        bb_upper REAL,
        bb_lower REAL,
        adx REAL,
        cci REAL,
        mfi REAL
    )''')

conn.commit()
conn.close()

print('Database schema initialized successfully')
