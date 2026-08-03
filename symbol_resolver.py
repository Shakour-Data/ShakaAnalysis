import sys
sys.stdout.reconfigure(encoding='utf-8')
import finpy_tse as tse
import pandas as pd
import numpy as np

def resolve_valid_symbols():
    """Get and decode valid market symbols for use with Get_Price_History"""
    print('Fetching market watch data...')
    try:
        result = tse.Get_MarketWatch()
        if isinstance(result, tuple):
            df = result[0]
            print('Market watch columns:', df.columns.tolist())
            print('Available symbols and names:')
            symbols = []
            for _, row in df.head(100).iterrows():
                name = str(row.get('Name', '')).strip()
                ticker = str(row.get('Ticker', '')).strip()
                market = str(row.get('Market', '')).strip()
                if name and ticker != 'نامعلوم':
                    symbols.append((name, ticker, market))
                    print(f'  {name[:30]} ({ticker[:10]}) - {market}')
            return symbols
        else:
            print('Error: MarketWatch returned non-tuple response')
            return []
    except Exception as e:
        print('Error fetching market watch:', str(e))
        return []

def get_price_data(symbol, start_jdate, end_jdate, adjust=True):
    """Get price data with proper Jalali date formatting"""
    try:
        # Validate dates are Jalali
        start_jalali = start_jdate
        end_jalali = end_jdate
        
        print(f'Fetching data for {symbol} from {start_jalali} to {end_jalali}')
        df = tse.Get_Price_History(
            stock=symbol,
            start_date=start_jalali,
            end_date=end_jalali,
            adjust_price=adjust
        )
        
        if df is not None and not df.empty:
            print(f'Success: Retrieved {df.shape[0]} rows')
            return df
        else:
            print(f'No data returned for {symbol}')
            return None
    except Exception as e:
        print(f'Error fetching data for {symbol}: {str(e)}')
        return None

def validate_dates(start_input, end_input):
    """Validate Jalali date format and range"""
    # Simple validation - ensure they are in YYYY-MM-DD format
    if start_input and end_input:
        start_parts = start_input.split('-')
        end_parts = end_input.split('-')
        if (len(start_parts) == 3 and len(end_parts) == 3 and
            all(part.isdigit() for part in start_parts + end_parts)):
            return start_input, end_input
    print('Please enter valid Jalali dates in YYYY-MM-DD format')
    return None, None

if __name__ == '__main__':
    # Example usage for testing
    print('=== Symbol Resolution Test ===')
    
    # 1. Get valid symbols
    symbols = resolve_valid_symbols()
    
    # 2. Try fetching data with a few symbols
    if symbols:
        test_symbols = [s[1] for s in symbols[:10]]
        print('\nTesting symbols:')
        for sym in test_symbols:
            try:
                df = get_price_data(
                    symbol=sym,
                    start_jdate='1402-01-01',
                    end_jdate='1402-12-31',
                    adjust=True
                )
                if df is not None:
                    print(f'✓ {sym}: {df.shape[0]} rows')
            except Exception as e:
                print(f'✗ {sym}: {str(e)}')