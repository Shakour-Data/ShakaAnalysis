#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Database schema initialization module for Shaka Analysis."""

import sqlite3


def initialize_database(database_path):
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    # Enable WAL mode for better concurrency
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA cache_size=10000")
    cur.execute("PRAGMA temp_store=MEMORY")

    # Drop existing tables to ensure clean schema (for fresh data population)
    cur.execute("DROP TABLE IF EXISTS analysis_records")
    cur.execute("DROP TABLE IF EXISTS export_history")
    cur.execute("DROP TABLE IF EXISTS data_metadata")
    cur.execute("DROP TABLE IF EXISTS indices_data")
    cur.execute("DROP TABLE IF EXISTS price_data")
    cur.execute("DROP TABLE IF EXISTS symbols")

    # Symbols table
    cur.execute('''CREATE TABLE symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE NOT NULL,
        name TEXT,
        type TEXT,
        exchange TEXT,
        industry TEXT,
        sector TEXT,
        webid TEXT,
        country TEXT DEFAULT 'IR',
        currency TEXT DEFAULT 'IRR',
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Price data table with technical indicators
    cur.execute('''CREATE TABLE price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        date TEXT,
        weekday TEXT,
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
        FOREIGN KEY (symbol_id) REFERENCES symbols (id)
    )''')

    # Indices data table (for market indices like TEPIX, TEDPIX)
    cur.execute('''CREATE TABLE indices_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Data metadata table (tracking extraction status, last update, etc.)
    cur.execute('''CREATE TABLE data_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Export history table
    cur.execute('''CREATE TABLE export_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_type TEXT NOT NULL,  -- 'symbol_list', 'price_data', 'indices', etc.
        symbol TEXT,
        format TEXT NOT NULL,       -- 'csv', 'json', 'excel'
        file_path TEXT NOT NULL,
        record_count INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Analysis records table (for storing calculated indicators, signals, etc.)
    cur.execute('''CREATE TABLE analysis_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        analysis_type TEXT NOT NULL,  -- 'technical', 'fundamental', 'sentiment'
        analysis_data TEXT,           -- JSON serialized analysis results
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Create indexes for better performance
    cur.execute('CREATE INDEX idx_price_symbol_date ON price_data(symbol_id, date)')
    cur.execute('CREATE INDEX idx_price_date ON price_data(date)')
    cur.execute('CREATE INDEX idx_indices_symbol ON indices_data(symbol)')
    cur.execute('CREATE INDEX idx_indices_symbol_date ON indices_data(symbol, date)')
    cur.execute('CREATE INDEX idx_symbols_exchange ON symbols(exchange)')
    cur.execute('CREATE INDEX idx_symbols_type ON symbols(type)')
    cur.execute('CREATE INDEX idx_symbols_industry ON symbols(industry)')

    # Insert initial metadata
    cur.execute('''INSERT INTO data_metadata (key, value) VALUES 
        ('database_version', '1.0'),
        ('initialized_at', datetime('now')),
        ('last_full_update', NULL),
        ('last_incremental_update', NULL)
    ''')

    conn.commit()
    conn.close()
    print(f"Database schema initialized successfully at {database_path}")


def get_db_connection(database_path):
    """Get a connection to the database with WAL mode enabled."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode on connection as well
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


if __name__ == '__main__':
    initialize_database('data/market_data.db')
    print("Database schema initialized successfully")