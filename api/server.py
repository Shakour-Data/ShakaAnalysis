import os
import json
import datetime
import ssl
import sys
import sqlite3
from flask import Flask, jsonify, send_from_directory, request, send_file, Response
import pandas as pd
import jdatetime
import finpy_tse as tse
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

app = Flask(__name__, static_folder='../frontend', template_folder='../frontend')
app.config['JSON_AS_ASCII'] = False

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'market_data.db')
REPORTS_DIR = os.path.join(PROJECT_DIR, 'reports')
LOGS_DIR = os.path.join(PROJECT_DIR, 'logs')
ANALYSIS_DIR = os.path.join(PROJECT_DIR, 'analysis')

for dir_path in [ANALYSIS_DIR, REPORTS_DIR, LOGS_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def save_analysis_record(symbol, analysis_text):
    """Save analysis record to database."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO analysis_records (symbol, analysis) VALUES (?, ?)',
            (symbol, analysis_text)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def db_query(query, params=(), fetch_all=True):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if fetch_all:
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        else:
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def make_json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype='application/json; charset=utf-8'
    )


def make_error_response(error_msg, status=500):
    return make_json_response({'error': error_msg}, status)


def map_price_row(row):
    return {
        'Date': row.get('date', ''),
        'Open': row.get('open', 0),
        'High': row.get('high', 0),
        'Low': row.get('low', 0),
        'Close': row.get('close', 0),
        'Volume': row.get('volume', 0),
        'FinalPrice': row.get('final_price', 0),
        'Value': row.get('value', 0),
        'SMA_20': row.get('sma_20'),
        'SMA_50': row.get('sma_50'),
        'RSI': row.get('rsi'),
        'MACD': row.get('macd'),
        'Signal': row.get('macd_signal'),
        'Histogram': row.get('macd_histogram'),
        'BB_Upper': row.get('bb_upper'),
        'BB_Lower': row.get('bb_lower'),
        'ADX': row.get('adx'),
        'CCI': row.get('cci'),
        'MFI': row.get('mfi'),
        'MA_100': row.get('ma_100'),
    }


def get_symbol_id(symbol):
    row = db_query(
        'SELECT id FROM symbols WHERE symbol = ? AND is_active = 1',
        (symbol,), fetch_all=False
    )
    return row['id'] if row else None


def symbol_exists(symbol):
    return get_symbol_id(symbol) is not None


@app.route('/api/test')
def test():
    return make_json_response({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/symbols')
def get_symbols():
    try:
        rows = db_query('SELECT symbol, name, type, exchange FROM symbols WHERE is_active = 1 ORDER BY symbol')
        symbols = [r['symbol'] for r in rows]
        return make_json_response(symbols)
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/symbols/info')
def get_symbols_info():
    try:
        rows = db_query('SELECT symbol, name, type, exchange, industry, sector FROM symbols WHERE is_active = 1 ORDER BY symbol')
        return make_json_response(rows)
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/data/<symbol>')
def get_symbol_data(symbol):
    try:
        sym_id = get_symbol_id(symbol)
        if sym_id is None:
            return make_error_response(f'Symbol {symbol} not found', 404)

        rows = db_query(
            'SELECT date, open, high, low, close, volume, final_price, value, '
            'sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, '
            'bb_upper, bb_lower, adx, cci, mfi, ma_100 '
            'FROM price_data WHERE symbol_id = ? ORDER BY date ASC',
            (sym_id,)
        )

        data = [map_price_row(r) for r in rows]

        if not data:
            return make_error_response(f'No data found for symbol {symbol}', 404)

        return make_json_response(data)
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/indicators/<symbol>')
def get_symbol_indicators(symbol):
    try:
        sym_id = get_symbol_id(symbol)
        if sym_id is None:
            return make_error_response(f'Symbol {symbol} not found', 404)

        rows = db_query(
            'SELECT date, open, high, low, close, volume, '
            'sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, '
            'bb_upper, bb_lower, adx, cci, mfi, ma_100 '
            'FROM price_data WHERE symbol_id = ? ORDER BY date DESC LIMIT 1000',
            (sym_id,)
        )

        data = [map_price_row(r) for r in rows]
        return make_json_response(data)
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/fetch/<symbol>')
def fetch_symbol_data(symbol):
    try:
        sym_id = get_symbol_id(symbol)
        if sym_id is None:
            return make_error_response(f'Symbol {symbol} not found in database', 404)

        today = jdatetime.date.today()
        end_date = today.strftime('%Y-%m-%d')
        start_date = today.replace(year=today.year - 4).strftime('%Y-%m-%d')

        df = tse.Get_Price_History(
            stock=symbol,
            start_date=start_date,
            end_date=end_date,
            ignore_date=True,
            adjust_price=True
        )

        if df is None or df.empty:
            return make_error_response(f'Failed to fetch data for symbol {symbol}', 404)

        df = df.reset_index()

        def jalali_to_iso(jdate_str):
            try:
                parts = str(jdate_str).split('-')
                if len(parts) == 3:
                    jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                    gdate = jdatetime.date(jy, jm, jd).togregorian()
                    return gdate.isoformat()
            except Exception:
                pass
            return None

        if 'J-Date' in df.columns:
            df['Date'] = df['J-Date'].apply(jalali_to_iso)
            df = df.drop(columns=['J-Date'])
        else:
            df['Date'] = df.index

        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.sort_values('Date')
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        if 'Close' in df.columns:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

        records = df.to_dict(orient='records')
        for rec in records:
            rec['symbol_id'] = sym_id

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.executemany(
                'INSERT OR REPLACE INTO price_data '
                '(symbol_id, date, weekday, open, high, low, close, final_price, volume, value, '
                'adj_close, adj_final, sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, '
                'bb_upper, bb_lower, adx, cci, mfi, ma_100, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime("now"))',
                [(
                    rec.get('symbol_id', sym_id),
                    rec.get('Date'),
                    rec.get('weekday', ''),
                    rec.get('Open'), rec.get('High'), rec.get('Low'), rec.get('Close'),
                    rec.get('FinalPrice', rec.get('close')), rec.get('Volume', 0), rec.get('Value', 0),
                    rec.get('adj_close'), rec.get('adj_final'),
                    rec.get('SMA_20'), rec.get('SMA_50'), rec.get('RSI'),
                    rec.get('MACD'), rec.get('Signal'), rec.get('Histogram'),
                    rec.get('BB_Upper'), rec.get('BB_Lower'),
                    rec.get('ADX'), rec.get('CCI'), rec.get('MFI'), rec.get('MA_100'),
                ) for rec in records]
            )
            conn.commit()
        finally:
            conn.close()

        return make_json_response({
            'success': True,
            'symbol': symbol,
            'records': len(records),
            'message': f'Data for {symbol} fetched and saved successfully'
        })
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/analysis/save', methods=['POST'])
def save_analysis():
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'unknown')
        analysis_text = data.get('analysis', '')

        if not analysis_text.strip():
            return make_error_response('Analysis text is empty', 400)

        if not symbol_exists(symbol):
            return make_error_response(f'Symbol {symbol} not found', 404)

        filename = f"{symbol}_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(ANALYSIS_DIR, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n")
            f.write(analysis_text)

        save_analysis_record(symbol, analysis_text)

        return make_json_response({
            'success': True,
            'filename': filename,
            'message': 'Analysis saved successfully'
        })
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/analysis/list/<symbol>')
def list_analyses(symbol):
    try:
        analyses = db_query(
            'SELECT id, symbol, analysis, created_at FROM analysis_records WHERE symbol = ? ORDER BY created_at DESC LIMIT 50',
            (symbol,)
        )
        return make_json_response(analyses)
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/api/download/<symbol>/<filetype>')
def download_file(symbol):
    try:
        sym_id = get_symbol_id(symbol)
        if sym_id is None:
            return make_error_response(f'Symbol {symbol} not found', 404)

        rows = db_query(
            'SELECT date, open, high, low, close, volume, final_price, value, '
            'sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, '
            'bb_upper, bb_lower, adx, cci, mfi, ma_100 '
            'FROM price_data WHERE symbol_id = ? ORDER BY date ASC',
            (sym_id,)
        )

        if not rows:
            return make_error_response(f'No data found for symbol {symbol}', 404)

        df = pd.DataFrame([map_price_row(r) for r in rows])

        if filetype == 'price':
            cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        elif filetype == 'indicators':
            indicator_cols = [c for c in df.columns if c not in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            cols = ['Date'] + indicator_cols
        else:
            cols = None

        download_df = df[cols] if cols else df

        temp_file = os.path.join(REPORTS_DIR, f"temp_{symbol}_{filetype}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        download_df.to_csv(temp_file, index=False)

        return send_file(
            temp_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{symbol}_{filetype}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        )
    except Exception as e:
        return make_error_response(str(e), 500)


@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=False)