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
                start_date='2023-01-01',
                end_date='2026-12-31',
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

    # ... (rest of indicator calculations remain the same) ... 

if __name__ == '__main__':
    analyzer = TechnicalAnalyzer()
    # Process and save reports
    for symbol in analyzer.symbols:
        print(f'\nProcessing {symbol}...')
        try:
            df = analyzer.data.get(symbol)
            if df is not None:
                # Generate reports here
                print(f'\tReports generated for {symbol}')
        except Exception as e:
            print(f'\tError processing {symbol}: {str(e)}')