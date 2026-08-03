import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

import finpy_tse
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

log_file = 'errors.log'

def get_price_history(stock, start_date='1400-01-01', end_date='1403-12-29', adjust_price=True):
    try:
        df = finpy_tse.Get_Price_History(
            stock=stock,
            start_date=start_date,
            end_date=end_date,
            ignore_date=True,
            adjust_price=adjust_price
        )
        if df is not None and not df.empty:
            # Reset index to get J-Date as column
            df = df.reset_index()
            df['Weekday'] = pd.to_datetime(df['J-Date']).dt.day_name()
            return df[['J-Date', 'Weekday', 'Open', 'High', 'Low', 'Close', 'Final',
                      'Volume', 'Value', 'No', 'Ticker', 'Name', 'Market',
                      'Adj Open', 'Adj High', 'Adj Low', 'Adj Close', 'Adj Final']]
        return None
    except Exception as e:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'Error fetching {stock}: {str(e)}\n')
        return None

def get_all_indices():
    valid_symbols = [
        'خودرو',
        'ایرانخودرو',
        'پاسارگاد',
        'شاخص قیمت',
        'شاخص هم وزن',
        'سهم بانک'
    ]
    all_data = {}
    for stock in valid_symbols:
        df = get_price_history(stock)
        if df is not None:
            all_data[stock] = df[['J-Date', 'Adj Close', 'Adj Final']].set_index('J-Date')
    if all_data:
        return pd.concat(all_data.values(), axis=1, keys=all_data.keys())
    return pd.DataFrame()

if __name__ == '__main__':
    indices_df = get_all_indices()
    print(f'Retrieved data shape: {indices_df.shape}')
    if not indices_df.empty:
        print('Sample data:')
        print(indices_df.head())
    else:
        print('No valid data retrieved. Check errors.log for details.')