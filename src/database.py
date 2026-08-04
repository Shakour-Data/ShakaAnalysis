import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'market_data.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Stock', 'Index', 'OTC', 'Sector')),
            exchange TEXT NOT NULL CHECK(exchange IN ('TSE', 'OTC', 'Farabourse', 'Payeh')),
            industry TEXT,
            sector TEXT,
            webid TEXT,
            country TEXT DEFAULT 'IR',
            currency TEXT DEFAULT 'IRR',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol_id INTEGER NOT NULL,
            date TEXT NOT NULL,
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
            resistances TEXT,
            supports TEXT,
            ma_100 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol_id, date),
            FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indices_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_symbol TEXT NOT NULL,
            index_name TEXT NOT NULL,
            date TEXT NOT NULL,
            close REAL,
            adj_close REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(index_symbol, date)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            total_records INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'complete',
            UNIQUE(symbol, data_type)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS export_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_type TEXT NOT NULL,
            symbol TEXT,
            format TEXT NOT NULL,
            file_path TEXT,
            record_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_data(symbol_id, date)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbols_symbol ON symbols(symbol)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_indices_date ON indices_data(index_symbol, date)
    ''')

    conn.commit()
    conn.close()
    return True

def bulk_insert_symbols(symbols_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = 0
    for sym in symbols_list:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, industry, sector, webid)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sym.get('symbol', ''),
                sym.get('name', ''),
                sym.get('type', 'Stock'),
                sym.get('exchange', 'TSE'),
                sym.get('industry', ''),
                sym.get('sector', ''),
                sym.get('webid', '')
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted

def bulk_insert_price_data(symbol_id, price_records):
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = 0
    for record in price_records:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO price_data
                (symbol_id, date, weekday, open, high, low, close, final_price,
                 volume, value, adj_close, adj_final, sma_20, sma_50, rsi,
                 macd, macd_signal, macd_histogram, bb_upper, bb_lower, adx,
                 cci, mfi, resistances, supports, ma_100)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id,
                record.get('Date', ''),
                record.get('Weekday', ''),
                record.get('Open'),
                record.get('High'),
                record.get('Low'),
                record.get('Close'),
                record.get('Final'),
                record.get('Volume'),
                record.get('Value'),
                record.get('Adj Close'),
                record.get('Adj Final'),
                record.get('SMA_20'),
                record.get('SMA_50'),
                record.get('RSI'),
                record.get('MACD'),
                record.get('MACD_Signal'),
                record.get('MACD_Hist'),
                record.get('BB_Upper'),
                record.get('BB_Lower'),
                record.get('ADX'),
                record.get('CCI'),
                record.get('MFI'),
                record.get('Resistances'),
                record.get('Supports'),
                record.get('MA100')
            ))
            if cursor.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted

def get_symbol_id(symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM symbols WHERE symbol = ?', (symbol,))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None

def get_all_symbols():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM symbols WHERE is_active = 1 ORDER BY symbol')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_price_data(symbol, start_date=None, end_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    symbol_id = get_symbol_id(symbol)
    if not symbol_id:
        conn.close()
        return []

    query = 'SELECT * FROM price_data WHERE symbol_id = ?'
    params = [symbol_id]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    query += ' ORDER BY date'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_data_metadata(symbol, data_type, start_date, end_date, total_records):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO data_metadata (symbol, data_type, start_date, end_date, total_records, last_updated, status)
        VALUES (?, ?, ?, ?, ?, ?, 'complete')
    ''', (symbol, data_type, start_date, end_date, total_records, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_data_completeness():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total FROM symbols WHERE is_active = 1')
    total_symbols = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(DISTINCT symbol_id) as symbols_with_data FROM price_data')
    symbols_with_data = cursor.fetchone()['symbols_with_data']

    cursor.execute('SELECT COUNT(*) as total_records FROM price_data')
    total_records = cursor.fetchone()['total_records']

    cursor.execute('''
        SELECT s.symbol, s.name, s.type,
               (SELECT COUNT(*) FROM price_data pd WHERE pd.symbol_id = s.id) as record_count
        FROM symbols s
        WHERE s.is_active = 1
        ORDER BY record_count DESC
    ''')
    symbol_stats = cursor.fetchall()

    conn.close()

    return {
        'total_symbols': total_symbols,
        'symbols_with_data': symbols_with_data,
        'total_records': total_records,
        'completeness_percentage': round((symbols_with_data / total_symbols * 100) if total_symbols > 0 else 0, 2),
        'symbol_details': [dict(row) for row in symbol_stats]
    }

def export_to_json(symbol, data_type='price', format='json'):
    conn = get_db_connection()
    cursor = conn.cursor()
    symbol_id = get_symbol_id(symbol)

    if not symbol_id:
        conn.close()
        return None

    if data_type == 'price':
        cursor.execute('SELECT * FROM price_data WHERE symbol_id = ? ORDER BY date', (symbol_id,))
    elif data_type == 'all':
        cursor.execute('SELECT * FROM price_data WHERE symbol_id = ? ORDER BY date', (symbol_id,))
    else:
        conn.close()
        return None

    rows = cursor.fetchall()
    conn.close()

    data = [dict(row) for row in rows]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{symbol}_{data_type}_export_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(DB_PATH), 'exports', filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    cursor = get_db_connection().cursor()
    cursor.execute('''
        INSERT INTO export_history (export_type, symbol, format, file_path, record_count)
        VALUES (?, ?, ?, ?, ?)
    ''', (data_type, symbol, format, filepath, len(data)))
    conn.commit()
    conn.close()

    return filepath

def export_to_csv(symbol, data_type='price'):
    conn = get_db_connection()
    cursor = conn.cursor()
    symbol_id = get_symbol_id(symbol)

    if not symbol_id:
        conn.close()
        return None

    if data_type == 'price':
        cursor.execute('SELECT * FROM price_data WHERE symbol_id = ? ORDER BY date', (symbol_id,))
    else:
        conn.close()
        return None

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    import csv
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{symbol}_{data_type}_export_{timestamp}.csv"
    filepath = os.path.join(os.path.dirname(DB_PATH), 'exports', filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    columns = [desc[0] for desc in cursor.description]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    return filepath

if __name__ == '__main__':
    initialize_database()
    print("Database initialized successfully")