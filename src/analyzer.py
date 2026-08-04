import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import finpy_tse
import pandas as pd
import numpy as np
import jdatetime
import warnings
warnings.filterwarnings('ignore')

THESE_VALID_SYMBOLS = [
    'خودرو',
    'فولاد',
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
            if not self._validate_symbol(symbol):
                raise ValueError(f'Invalid symbol: {symbol}')
            df = finpy_tse.Get_Price_History(
                stock=symbol,
                start_date='1400-01-01',
                end_date='1400-12-29',
                adjust_price=True,
                ignore_date=True
            )
            if df is not None and not df.empty:
                df = self._process_dataframe(df)
                return df
        except Exception as e:
            print(f'Error fetching {symbol}: {str(e)}')
            return None

    def _validate_symbol(self, symbol):
        try:
            df = finpy_tse.Get_Price_History(
                stock=symbol,
                start_date='1400-01-01',
                end_date='1400-01-02',
                adjust_price=True,
                ignore_date=True
            )
            return df is not None and not df.empty
        except:
            return False

    def _process_dataframe(self, df):
        df = df.reset_index()
        def jalali_to_gregorian(jdate_str):
            parts = jdate_str.split('-')
            jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
            gdate = jdatetime.date(jy, jm, jd).togregorian()
            return gdate
        df['Date'] = df['J-Date'].apply(jalali_to_gregorian)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Weekday'] = df['Date'].dt.day_name()
        df = df.drop(columns=['J-Date'])
        return df[['Date', 'Weekday', 'Open', 'High', 'Low', 'Close', 'Final',
                  'Volume', 'Adj Open', 'Adj High', 'Adj Low', 'Adj Close', 'Adj Final']]

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
    mean_dev = abs(typical_price - sma).rolling(window=period).mean()
    cci = (typical_price - sma) / (0.015 * mean_dev)
    return cci

def calculate_mfi(high, low, close, volume, period):
    tp = (high + low + close) / 3
    rmf = tp * volume
    # Positive money flow: TP > previous TP
    positive_flow = rmf.where(tp > tp.shift(1), 0)
    # Negative money flow: TP < previous TP
    negative_flow = rmf.where(tp < tp.shift(1), 0)
    positive_sum = positive_flow.rolling(window=period, min_periods=1).sum()
    negative_sum = negative_flow.rolling(window=period, min_periods=1).sum()
    money_ratio = positive_sum / (negative_sum + 1e-9)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi

def calculate_bbands(series, period, std_dev):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, lower

def calculate_adx(high, low, close, period):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    # Use Wilder's smoothing (EMA with alpha=1/period)
    alpha = 1.0 / period
    plus_dm_smoothed = plus_dm.ewm(alpha=alpha, min_periods=period).mean()
    minus_dm_smoothed = minus_dm.ewm(alpha=alpha, min_periods=period).mean()
    tr_smoothed = tr.ewm(alpha=alpha, min_periods=period).mean()
    plus_di = (plus_dm_smoothed / tr_smoothed).replace([np.inf, -np.inf], 0) * 100
    minus_di = (minus_dm_smoothed / tr_smoothed).replace([np.inf, -np.inf], 0) * 100
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9) * 100
    adx = dx.ewm(alpha=alpha, min_periods=period).mean()
    return adx

def calculate_all_indicators(df):
    df = df.sort_values('Date')
    price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    high_col = 'Adj High' if 'Adj High' in df.columns else 'High'
    low_col = 'Adj Low' if 'Adj Low' in df.columns else 'Low'
    open_col = 'Adj Open' if 'Adj Open' in df.columns else 'Open'
    for p in [9, 14, 21, 35]:
        df[f'RSI_{p}'] = calculate_rsi(df[price_col], p)
    macd_line, macd_signal, macd_hist = calculate_macd(df[price_col])
    df['MACD'] = macd_line
    df['MACD_Signal'] = macd_signal
    df['MACD_Hist'] = macd_hist
    for p in [9, 14, 21, 35]:
        df[f'CCI_{p}'] = calculate_cci(df[high_col], df[low_col], df[price_col], p)
    for p in [9, 14, 21, 35]:
        df[f'MFI_{p}'] = calculate_mfi(df[high_col], df[low_col], df[price_col], df['Volume'], p)
    for p in [9, 14, 50, 100]:
        upper, lower = calculate_bbands(df[price_col], p, 2)
        df[f'BB_{p}_upper'] = upper
        df[f'BB_{p}_lower'] = lower
    for p in [9, 14, 21, 35]:
        df[f'ADX_{p}'] = calculate_adx(df[high_col], df[low_col], df[price_col], p)
    volume_thresh = df['Volume'].quantile(0.75)
    peaks = []
    for i in range(2, len(df) - 2):
        if (df[high_col].iloc[i] > df[high_col].iloc[i-1]) and (df[high_col].iloc[i] > df[high_col].iloc[i+1]) \
           and (df[high_col].iloc[i] > df[high_col].iloc[i-2]) and (df[high_col].iloc[i] > df[high_col].iloc[i+2]) \
           and df['Volume'].iloc[i] > volume_thresh:
            peaks.append(df[high_col].iloc[i])
    resistances = []
    for i in range(len(peaks)):
        for j in range(i+1, len(peaks)):
            if peaks[j] > peaks[i] * 1.05:
                resistances.append(peaks[j])
                break
    supports = []
    for i in range(2, len(df) - 2):
        if (df[low_col].iloc[i] < df[low_col].iloc[i-1]) and (df[low_col].iloc[i] < df[low_col].iloc[i+1]) \
           and (df[low_col].iloc[i] < df[low_col].iloc[i-2]) and (df[low_col].iloc[i] < df[low_col].iloc[i+2]) \
           and df['Volume'].iloc[i] > volume_thresh:
            supports.append(df[low_col].iloc[i])
    df['Resistances'] = ','.join(map(str, sorted(set(resistances))))
    df['Supports'] = ','.join(map(str, sorted(set(supports))))
    return df

if __name__ == '__main__':
    analyzer = TechnicalAnalyzer()
    for symbol in analyzer.symbols:
        print(f'\nProcessing {symbol}...')
        try:
            df = analyzer.data.get(symbol)
            if df is not None:
                df = calculate_all_indicators(df)
                # Recalculate Value with adjusted prices for consistency
                price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
                df['Value_Adjusted'] = df['Volume'] * df[price_col]
                df['MA100'] = df[price_col].rolling(window=100).mean()
                excel_path = f'reports/{symbol}_report.xlsx'
                df.to_excel(excel_path, index=False)
                print(f'\tSaved Excel to {excel_path}')
                recent = df.tail(60).copy()
                if 'Date' in recent.columns:
                    recent['Date'] = recent['Date'].dt.strftime('%Y-%m-%d')
                # Select adjusted columns for JSON
                json_columns = [
                    'Date', 'Weekday', 'Open', 'High', 'Low', 'Close', 'Final',
                    'Adj Open', 'Adj High', 'Adj Low', 'Adj Close', 'Adj Final',
                    'Volume', 'Volume_Adjusted', 'Value_Adjusted', 'Adj Close', 'Adj Final',
                    'Resistances', 'Supports', 'MA100',
                    'RSI_9', 'RSI_14', 'RSI_21', 'RSI_35',
                    'MACD', 'MACD_Signal', 'MACD_Hist',
                    'CCI_9', 'CCI_14', 'CCI_21', 'CCI_35',
                    'MFI_9', 'MFI_14', 'MFI_21', 'MFI_35',
                    'BB_9_upper', 'BB_9_lower', 'BB_14_upper', 'BB_14_lower',
                    'BB_50_upper', 'BB_50_lower', 'BB_100_upper', 'BB_100_lower',
                    'ADX_9', 'ADX_14', 'ADX_21', 'ADX_35'
                ]
                json_columns = list(dict.fromkeys(json_columns))  # Remove duplicates
                json_columns = [col for col in json_columns if col in recent.columns]
                recent = recent[json_columns]
                json_path = f'../data/{symbol}_data.json'
                recent.to_json(json_path, orient='records', date_format='iso')
                print(f'\tSaved data JSON to {json_path}')
                if not recent['Resistances'].isnull().all():
                    latest_res = recent['Resistances'].iloc[-1]
                    print(f'\tLatest resistances: {latest_res}')
                if not recent['Supports'].isnull().all():
                    latest_sup = recent['Supports'].iloc[-1]
                    print(f'\tLatest supports: {latest_sup}')
        except Exception as e:
            print(f'\tError processing {symbol}: {str(e)}')