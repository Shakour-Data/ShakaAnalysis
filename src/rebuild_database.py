#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rebuild complete database schema with proper relationships."""

import sqlite3
import os

PROJECT_DIR = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'market_data.db')


def rebuild_schema():
    """Rebuild the database with complete schema and relationships."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript('''
    PRAGMA foreign_keys = ON;
    
    CREATE TABLE symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT UNIQUE NOT NULL,
        name TEXT,
        full_name TEXT,
        type TEXT NOT NULL CHECK(type IN ('Stock', 'Index', 'Currency', 'Commodity', 'OTC', 'ETF')),
        exchange TEXT DEFAULT 'TSE',
        industry TEXT,
        sector TEXT,
        webid TEXT,
        country TEXT DEFAULT 'Iran',
        currency TEXT DEFAULT 'IRR',
        unit TEXT DEFAULT 'Toman',
        decimals INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        weekday TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        final_price REAL,
        volume INTEGER DEFAULT 0,
        value REAL DEFAULT 0,
        adj_close REAL,
        adj_final REAL,
        sma_20 REAL,
        sma_50 REAL,
        sma_100 REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        macd_histogram REAL,
        bb_upper REAL,
        bb_lower REAL,
        adx REAL,
        cci REAL,
        mfi REAL,
        resistances TEXT,
        supports TEXT,
        ema_12 REAL,
        ema_26 REAL,
        atr REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
        UNIQUE(symbol_id, date)
    );
    
    CREATE TABLE indices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        close REAL NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        volume INTEGER DEFAULT 0,
        value REAL DEFAULT 0,
        adj_close REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE,
        UNIQUE(symbol_id, date)
    );
    
    CREATE TABLE indicator_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT,
        params TEXT,
        description TEXT,
        is_active INTEGER DEFAULT 1
    );
    
    CREATE TABLE analysis_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        analysis TEXT,
        timeframe TEXT,
        sentiment TEXT CHECK(sentiment IN ('Bullish', 'Bearish', 'Neutral')),
        target_price REAL,
        stop_loss REAL,
        confidence REAL CHECK(confidence >= 0 AND confidence <= 100),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
    );
    
    CREATE TABLE export_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_type TEXT NOT NULL,
        symbol_id INTEGER,
        format TEXT NOT NULL,
        file_path TEXT,
        record_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE SET NULL
    );
    
    CREATE TABLE data_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER,
        data_type TEXT,
        start_date TEXT,
        end_date TEXT,
        total_records INTEGER DEFAULT 0,
        last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE SET NULL
    );
    
    CREATE INDEX idx_price_data_symbol_date ON price_data(symbol_id, date DESC);
    CREATE INDEX idx_indices_symbol_date ON indices(symbol_id, date DESC);
    CREATE INDEX idx_analysis_symbol ON analysis_records(symbol_id);
    CREATE UNIQUE INDEX idx_analysis_symbol_timeframe ON analysis_records(symbol_id, timeframe);
    CREATE INDEX idx_export_created ON export_history(created_at DESC);
    CREATE UNIQUE INDEX idx_export_unique ON export_history(export_type, symbol_id);
    
    
    PRAGMA foreign_keys = ON;

    cur.executescript('''
    PRAGMA foreign_keys = ON;

    CREATE TRIGGER update_symbol_timestamp 
    AFTER UPDATE ON symbols
    FOR EACH ROW
    BEGIN
        UPDATE symbols SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = NEW.id;
    END;
    ''')

    # Insert indicator configurations
    indicators = [
        ('RSI_14', 'RSI (14)', '{"window": 14}', 'Relative Strength Index'),
        ('MACD', 'MACD', '{"fast": 12, "slow": 26, "signal": 9}', 'Moving Average Convergence Divergence'),
        ('SMA_20', 'SMA 20', '{"window": 20}', 'Simple Moving Average 20'),
        ('SMA_50', 'SMA 50', '{"window": 50}', 'Simple Moving Average 50'),
        ('SMA_100', 'SMA 100', '{"window": 100}', 'Simple Moving Average 100'),
        ('EMA_12', 'EMA 12', '{"span": 12}', 'Exponential Moving Average 12'),
        ('EMA_26', 'EMA 26', '{"span": 26}', 'Exponential Moving Average 26'),
        ('BB_20', 'Bollinger Bands', '{"window": 20, "std": 2}', 'Bollinger Bands'),
        ('ADX_14', 'ADX', '{"window": 14}', 'Average Directional Index'),
        ('CCI_14', 'CCI', '{"window": 14}', 'Commodity Channel Index'),
        ('MFI_14', 'MFI', '{"window": 14}', 'Money Flow Index'),
        ('ATR_14', 'ATR', '{"window": 14}', 'Average True Range'),
    ]
    cur.executemany('INSERT INTO indicator_config (name, display_name, params, description) VALUES (?,?, ?,  ?)', indicators)

    conn.commit()
    conn.close()
    print(f'Database rebuilt successfully at {DB_PATH}')


if __name__ == '__main__':
    rebuild_schema()