from flask import Flask, jsonify, make_response
import sqlite3
import os
import time
import csv
import io
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

@app.route('/api/data/<symbol>')
def get_data(symbol):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get price data for the symbol
    cursor.execute("""
        SELECT p.Date, p.Open, p.High, p.Low, p.Close, p.Volume, p.Value,
               p.sma_20, p.sma_50, p.rsi, p.macd, p.macd_signal, p.macd_histogram,
               p.bb_upper, p.bb_lower, p.adx, p.cci, p.mfi, p.ma_100
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.symbol = ?
        ORDER BY p.Date DESC
        LIMIT 1000
    """, (symbol,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return jsonify({'error': 'No data found for symbol'}), 404
    
    data = []
    for row in rows:
        data.append({
            'Date': row['Date'],
            'Open': row['Open'],
            'High': row['High'],
            'Low': row['Low'],
            'Close': row['Close'],
            'Volume': row['Volume'],
            'Value': row['Value'],
            'SMA_20': row['sma_20'],
            'SMA_50': row['sma_50'],
            'RSI': row['rsi'],
            'MACD': row['macd'],
            'Signal': row['macd_signal'],
            'Histogram': row['macd_histogram'],
            'BB_Upper': row['bb_upper'],
            'BB_Lower': row['bb_lower'],
            'ADX': row['adx'],
            'CCI': row['cci'],
            'MFI': row['mfi'],
            'ma_100': row['ma_100']
        })
    
    return jsonify(data)

@app.route('/api/analysis/save', methods=['POST'])
def save_analysis():
    import json
    data = request.get_json()
    
    if not data or 'symbol' not in data or 'analysis' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        # Save to a file
        filename = f"analysis_{data['symbol']}_{int(time.time())}.txt"
        analysis_dir = 'analysis_files'
        os.makedirs(analysis_dir, exist_ok=True)
        
        file_path = os.path.join(analysis_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Symbol: {data['symbol']}\n")
            f.write(f"Analysis: {data['analysis']}\n")
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'Analysis saved successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<symbol>/<type>')
def download_file(symbol, type):
    conn = get_db_connection()
    
    if type == 'price':
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Date, Open, High, Low, Close, Volume, Value
            FROM price_data
            JOIN symbols ON price_data.symbol_id = symbols.id
            WHERE symbols.symbol = ?
            ORDER BY Date
        """, (symbol,))
        data = cursor.fetchall()
        
        if not data:
            conn.close()
            return jsonify({'error': 'No price data found'}), 404
        
        import csv, io
        from datetime import datetime
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Value'])
        
        for row in data:
            writer.writerow([row['Date'], row['Open'], row['High'], row['Low'], row['Close'], row['Volume'], row['Value']])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=price_data_{symbol}.csv'
        conn.close()
        return response
        
    elif type == 'indicators':
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Date, sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, bb_upper, bb_lower
            FROM price_data
            JOIN symbols ON price_data.symbol_id = symbols.id
            WHERE symbols.symbol = ?
            ORDER BY Date
        """, (symbol,))
        data = cursor.fetchall()
        
        if not data:
            conn.close()
            return jsonify({'error': 'No indicator data found'}), 404
        
        import csv, io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'SMA_20', 'SMA_50', 'RSI', 'MACD', 'Signal', 'Histogram', 'BB_Upper', 'BB_Lower'])
        
        for row in data:
            writer.writerow([row['Date'], row['SMA_20'], row['SMA_50'], row['RSI'], row['MACD'], row['Signal'], row['Histogram'], row['BB_Upper'], row['BB_Lower']])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=indicator_data_{symbol}.csv'
        conn.close()
        return response
        
    elif type == 'full':
        # Combine all data
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.Date, p.Open, p.High, p.Low, p.Close, p.Volume, p.Value,
                   p.SMA_20, p.SMA_50, p.RSI, p.MACD, p.Signal, p.Histogram,
                   p.BB_Upper, p.BB_Lower, p.ADX, p.CCI, p.MFI, p.ma_100
            FROM price_data p
            JOIN symbols s ON p.symbol_id = s.id
            WHERE s.symbol = ?
            ORDER BY p.Date
        """, (symbol,))
        data = cursor.fetchall()
        
        if not data:
            conn.close()
            return jsonify({'error': 'No data found'}), 404
        
        import csv, io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Value',
            'SMA_20', 'SMA_50', 'RSI', 'MACD', 'Signal', 'Histogram',
            'BB_Upper', 'BB_Lower', 'ADX', 'CCI', 'MFI', 'ma_100'
        ])
        
        for row in data:
            writer.writerow([
                row['Date'], row['Open'], row['High'], row['Low'], row['Close'], row['Volume'], row['Value'],
                row['SMA_20'], row['SMA_50'], row['RSI'], row['MACD'], row['Signal'], row['Histogram'],
                row['BB_Upper'], row['BB_Lower'], row['ADX'], row['CCI'], row['MFI'], row['ma_100']
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=full_data_{symbol}.csv'
        conn.close()
        return response
        
    conn.close()
    return jsonify({'error': 'Invalid download type'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)