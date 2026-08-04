import os
import json
import datetime
import ssl
from flask import Flask, jsonify, send_from_directory, request, send_file
import pandas as pd
import jdatetime
import finpy_tse as tse
import warnings
warnings.filterwarnings('ignore')

# SSL context for finpy_tse
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

app = Flask(__name__, static_folder='../frontend', template_folder='../frontend')

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports')
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
ANALYSIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'analysis')

# Create analysis directory if it doesn't exist
if not os.path.exists(ANALYSIS_DIR):
    os.makedirs(ANALYSIS_DIR)

# Helper function to fetch data for a symbol
def get_symbol_data(symbol):
    """Get data for a symbol from JSON file."""
    json_path = os.path.join(DATA_DIR, f"{symbol}_data.json")
    if not os.path.exists(json_path):
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(data)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
    
    return df

# Helper function to fetch raw data from finpy_tse
def fetch_symbol_data(symbol):
    """Fetch fresh data for a symbol from TSE."""
    try:
        # Calculate date range (4 years back from today)
        import jdatetime
        today = jdatetime.date.today()
        end_date = today.strftime('%Y-%m-%d')
        
        # Go back 4 years
        start_date = today.replace(year=today.year - 4)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        df = tse.Get_Price_History(
            stock=symbol,
            start_date=start_date_str,
            end_date=end_date,
            ignore_date=True,
            adjust_price=True
        )
        
        if df is not None and not df.empty:
            # Convert Jalali dates to ISO format
            df = df.reset_index()
            if 'J-Date' in df.columns:
                def jalali_to_iso(jdate_str):
                    try:
                        parts = str(jdate_str).split('-')
                        if len(parts) == 3:
                            jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                            gdate = jdatetime.date(jy, jm, jd).togregorian()
                            return gdate.isoformat()
                    except:
                        return None
                
                df['Date'] = df['J-Date'].apply(jalali_to_iso)
                df = df.drop(columns=['J-Date'])
            else:
                # If no J-Date column, try using the index
                df['Date'] = df.index
            
            # Ensure proper date handling
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])  # Remove rows with invalid dates
            df = df.sort_values('Date')
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            # Calculate indicators
            df = calculate_indicators(df)
            
            return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Calculate common technical indicators."""
    if 'Close' in df.columns:
        # Simple Moving Averages
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    return df

# API Endpoints

@app.route('/api/symbols')
def get_symbols():
    """Return list of available symbols."""
    try:
        symbols = []
        for f in os.listdir(DATA_DIR):
            if f.endswith('_data.json'):
                symbols.append(f.replace('_data.json', ''))
        return jsonify(symbols)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/<symbol>')
def get_symbol_data_endpoint(symbol):
    """Get data for a specific symbol."""
    try:
        df = get_symbol_data(symbol)
        if df is None:
            return jsonify({'error': f'Symbol {symbol} not found'}), 404
        
        # Return as JSON
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/indicators/<symbol>')
def get_symbol_indicators(symbol):
    """Get calculated indicators for a symbol."""
    try:
        df = get_symbol_data(symbol)
        if df is None:
            return jsonify({'error': f'Symbol {symbol} not found'}), 404
        
        # Calculate some common indicators if they don't exist
        # This is a simplified version - in practice you'd use your technical analyzer
        if 'Close' in df.columns:
            # Calculate simple moving averages
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            
            # Calculate RSI (simplified)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Calculate MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['Histogram'] = df['MACD'] - df['Signal']
            
            # Bollinger Bands
            df['BB_middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
            df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        # Return last 1000 records to limit response size
        df_limited = df.tail(1000) if len(df) > 1000 else df
        return jsonify(df_limited.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# New endpoint to fetch data from TSE
@app.route('/api/fetch/<symbol>')
def fetch_symbol_data_endpoint(symbol):
    """Fetch data from TSE and save it locally."""
    try:
        df = fetch_symbol_data(symbol)
        if df is None or df.empty:
            return jsonify({'error': f'Failed to fetch data for symbol {symbol}'}), 404
        
        # Save to JSON file for future use
        json_path = os.path.join(DATA_DIR, f"{symbol}_data.json")
        df.to_json(json_path, orient='records', date_format='iso')
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'records': len(df),
            'message': f'Data for {symbol} fetched and saved successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/save', methods=['POST'])
def save_analysis():
    """Save user analysis."""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'unknown')
        analysis_text = data.get('analysis', '')
        timestamp = datetime.datetime.now().isoformat()
        
        # Create filename
        filename = f"{symbol}_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(ANALYSIS_DIR, filename)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("="*50 + "\n")
            f.write(analysis_text)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'Analysis saved successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/list/<symbol>')
def list_analyses(symbol):
    """List saved analyses for a symbol."""
    try:
        analyses = []
        for f in os.listdir(ANALYSIS_DIR):
            if f.startswith(symbol) and f.endswith('.txt'):
                analyses.append({
                    'filename': f,
                    'created': os.path.getctime(os.path.join(ANALYSIS_DIR, f))
                })
        # Sort by creation time, newest first
        analyses.sort(key=lambda x: x['created'], reverse=True)
        return jsonify(analyses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<symbol>/<filetype>')
def download_file(symbol, filetype):
    """Download data as CSV or Excel."""
    try:
        df = get_symbol_data(symbol)
        if df is None:
            return jsonify({'error': f'Symbol {symbol} not found'}), 404
        
        # Add indicators if requested
        if filetype in ['indicators', 'full']:
            # Calculate indicators
            if 'Close' in df.columns:
                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                df['SMA_50'] = df['Close'].rolling(window=50).mean()
                
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['RSI'] = 100 - (100 / (1 + rs))
                
                exp1 = df['Close'].ewm(span=12, adjust=False).mean()
                exp2 = df['Close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = exp1 - exp2
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                df['Histogram'] = df['MACD'] - df['Signal']
                
                df['BB_middle'] = df['Close'].rolling(window=20).mean()
                bb_std = df['Close'].rolling(window=20).std()
                df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
                df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        # Prepare data for download
        if filetype == 'price':
            cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        elif filetype == 'indicators':
            indicator_cols = [c for c in df.columns if c not in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            cols = ['Date'] + indicator_cols
        else:  # full
            cols = None  # all columns
        
        download_df = df[cols] if cols else df
        
        # Save to temporary file
        temp_file = os.path.join(REPORTS_DIR, f"temp_{symbol}_{filetype}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        download_df.to_csv(temp_file, index=False)
        
        # Send file
        return send_file(
            temp_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{symbol}_{filetype}_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve frontend files
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


@app.route('/api/test')
def test():
    """Simple test endpoint to verify server is running."""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

if __name__ == '__main__':
    # Run on port 4000
    app.run(host='0.0.0.0', port=4000, debug=False)