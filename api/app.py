from flask import Flask, jsonify
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'market_data.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/symbols')
def get_symbols():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, name, type, exchange, industry, sector FROM symbols WHERE is_active = 1")
    symbols = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(symbols)

@app.route('/api/price/<symbol>')
def get_price_data(symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.date, p.open, p.high, p.low, p.close, p.final_price, p.volume, p.value
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.symbol = ?
        ORDER BY p.date DESC
        LIMIT 100
    """, (symbol,))
    prices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(prices)

@app.route('/api/indices')
def get_indices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM indices")
    indices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(indices)

@app.route('/api/industry-indices')
def get_industry_indices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM industry_indices")
    indices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(indices)

@app.route('/api/price-data/<symbol>')
def get_price_data_full(symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.date, p.open, p.high, p.low, p.close, p.final_price, p.volume, p.value,
               p.sma_20, p.sma_50, p.rsi, p.macd, p.bb_upper, p.bb_lower
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.symbol = ?
        ORDER BY p.date DESC
        LIMIT 365
    """, (symbol,))
    prices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(prices)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)