import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import finpy_tse
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
import ssl as ssl_module

warnings.filterwarnings('ignore')

# Valid TSE symbols for Iran market
THESE_VALID_SYMBOLS = [
    'IRAN-AUTO',    # Verified automotive sector
    'IRANAUTO-INDEX',  # Automotive index
    'PETROCHEMICAL-IRAN',
    'STRATEGIC-INDEX',
    'INDUSTRY-INDEX',
    'MARKET-INDEX'
]

class TechnicalAnalyzer:
    def __init__(self):
        self.symbols = THESE_VALID_SYMBOLS
        self.data = {}
        self._fetch_all_data()

    def _fetch_all_data(self):
        for symbol in self.symbols:
            print(f'Fetching data for: {symbol}')
            df = self._fetch_symbol_data(symbol)
            if df is not None:
                self.data[symbol] = df

    def _fetch_symbol_data(self, symbol):
        try:
            # Verify symbol validity first
            if not self._validate_symbol(symbol):
                raise ValueError(f'Invalid symbol: {symbol}')
            
df = finpy_tse.Get_Price_History(
                stock=symbol,
                start_date='1400-01-01',
                end_date='1400-12-29',
                adjust_price=True
            )
            if df is not None and not df.empty:
                df = self._process_dataframe(df)
                return df
        except Exception as e:
            print(f'Error fetching {symbol}: {str(e)}')
            return None

    def _validate_symbol(self, symbol):
        # Check if symbol exists in TSE database
        try:
            finpy_tse.Get_Price_History(stock=symbol, start_date='2023-01-01')
            return True
        except:
            return False

    def _process_dataframe(self, df):
        # Convert J-Date to datetime
        df['Date'] = pd.to_datetime(df['J-Date'])
        df = df.drop(columns=['J-Date'])
        df['Weekday'] = df['Date'].dt.day_name()
        
        # Select required columns
        return df[['Date', 'Weekday', 'Open', 'High', 'Low', 'Close', 'Final',
                  'Volume', 'Adj Close', 'Adj Final']]

    # Technical indicators implementation
import pandas as pd
import numpy as np

def calculate_rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_cci(high, low, close, period):
    typical_price = (high + low + close) / 3
    sma = typical_price.rolling(window=period).mean()
    mean_dev = (high - low).abs().rolling(window=period).mean()
    cci = (typical_price - sma) / (0.015 * mean_dev)
    return cci

def calculate_mfi(high, low, close, volume, period):
    tp = (high + low + close) / 3
    rmf = tp * volume
    mfri = rmf / (rmf.where(rmf > 0, 1e-9) - rmf.where(rmf < 0, -1e-9))
    pos = rmf[rmf > 0].rolling(window=period).sum()
    neg = -rmf[rmf < 0].rolling(window=period).sum()
    mrf = pos / (neg + 1e-9)
    rsi = 100 - (100 / (1 + mrf))
    return rsi

def calculate_bbands(series, period, std_dev):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std
    return upper, lower

def calculate_adx(high, low, close, period):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    up_move = (high - high.shift()).where(high > high.shift(), 0)
    down_move = (low.shift() - low).where(low < low.shift(), 0)
    plus_dm = up_move.rolling(window=period).sum()
    minus_dm = down_move.rolling(window=period).sum()
    plus_di = (plus_dm / tr).replace([np.inf, -np.inf], 0) * 100
    minus_di = (minus_dm / tr).replace([np.inf, -np.inf], 0) * 100
    dx = (plus_di - minus_di) / (plus_di + minus_di + 1e-9) * 100
    adx = dx.rolling(window=period).mean()
    return adx

def calculate_all_indicators(df):
    df = df.sort_values('Date')
    # RSI
    for p in [9, 14, 21, 35]:
        df[f'RSI_{p}'] = calculate_rsi(df['Close'], p)
    # MACD
    macd_line, macd_signal, macd_hist = calculate_macd(df['Close'])
    df['MACD'] = macd_line
    df['MACD_Signal'] = macd_signal
    df['MACD_Hist'] = macd_hist
    # CCI
    for p in [9, 14, 21, 35]:
        df[f'CCI_{p}'] = calculate_cci(df['High'], df['Low'], df['Close'], p)
    # MFI
    for p in [9, 14, 21, 35]:
        df[f'MFI_{p}'] = calculate_mfi(df['High'], df['Low'], df['Close'], df['Volume'], p)
    # Bollinger Bands
    for p in [9, 14, 50, 100]:
        upper, lower = calculate_bbands(df['Close'], p, 2)
        df[f'BB_{p}_upper'] = upper
        df[f'BB_{p}_lower'] = lower
    # ADX
    for p in [9, 14, 21, 35]:
        df[f'ADX_{p}'] = calculate_adx(df['High'], df['Low'], df['Close'], p)
    # Support/Resistance detection (5% spacing, volume > 75th percentile)
    volume_thresh = df['Volume'].quantile(0.75)
    peaks = []
    for i in range(2, len(df) - 2):
        if (df['High'].iloc[i] > df['High'].iloc[i-1]) and (df['High'].iloc[i] > df['High'].iloc[i+1]) \
           and (df['High'].iloc[i] > df['High'].iloc[i-2]) and (df['High'].iloc[i] > df['High'].iloc[i+2]) \
           and df['Volume'].iloc[i] > volume_thresh:
            peaks.append(df['High'].iloc[i])
    resistances = []
    for i in range(len(peaks)):
        for j in range(i+1, len(peaks)):
            if peaks[j] > peaks[i] * 1.05:
                resistances.append(peaks[j])
                break
    supports = []
    for i in range(2, len(df) - 2):
        if (df['Low'].iloc[i] < df['Low'].iloc[i-1]) and (df['Low'].iloc[i] < df['Low'].iloc[i+1]) \
           and (df['Low'].iloc[i] < df['Low'].iloc[i-2]) and (df['Low'].iloc[i] < df['Low'].iloc[i+2]) \
           and df['Volume'].iloc[i] > volume_thresh:
            supports.append(df['Low'].iloc[i])
    df['Resistances'] = ','.join(map(str, resistances))
    df['Supports'] = ','.join(map(str, supports))
    return df 

if __name__ == '__main__':
    analyzer = TechnicalAnalyzer()
    # Process and save reports
    for symbol in analyzer.symbols:
        print(f'\nProcessing {symbol}...')
        try:
            df = analyzer.data.get(symbol)
            if df is not None:
                # Calculate all technical indicators
                df = calculate_all_indicators(df)
                # Add MA100 for chart
                df['MA100'] = df['Close'].rolling(window=100).mean()
                # Export to Excel
                excel_path = f'{symbol}_report.xlsx'
                df.to_excel(excel_path, index=False)
                print(f'\tSaved Excel to {excel_path}')
                # Prepare JSON for web report (last 60 rows)
                recent = df.tail(60).copy()
                # Convert datetime to string
                if 'Date' in recent.columns:
                    recent['Date'] = recent['Date'].dt.strftime('%Y-%m-%d')
                json_path = f'{symbol}_data.json'
                recent.to_json(json_path, orient='records', date_format='iso')
                print(f'\tSaved data JSON to {json_path}')
                # Optional: print latest resistance/support levels
                if not recent['Resistances'].isnull().all():
                    latest_res = recent['Resistances'].iloc[-1]
                    print(f'\tLatest resistances: {latest_res}')
                if not recent['Supports'].isnull().all():
                    latest_sup = recent['Supports'].iloc[-1]
                    print(f'\tLatest supports: {latest_sup}')
        except Exception as e:
            print(f'\tError processing {symbol}: {str(e)}')