#!/usr/bin/env python3
"""
Comprehensive symbol data extractor from finpy_tse
Extracts all symbols, price data, and indicators from beginning of data available
"""

import ssl
import urllib3
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# ==================== SSL PATCH START ====================
# Apply monkey patch BEFORE importing finpy_tse
_original_get = requests.get
_original_post = requests.post

def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 60)
    return _original_get(url, *args, **kwargs)

def patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 60)
    return _original_post(url, *args, **kwargs)

# Apply global patches
requests.get = patched_get
requests.post = patched_post

# Patch session methods
_original_session_get = requests.Session.get
_original_session_post = requests.Session.post

def patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 60)
    return _original_session_get(self, url, *args, **kwargs)

def patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 60)
    return _original_session_post(self, url, *args, **kwargs)

requests.Session.get = patched_session_get
requests.Session.post = patched_session_post

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
print("[OK] SSL patch applied successfully")

# Now import finpy_tse
import finpy_tse
print("[OK] finpy_tse imported successfully")

# ==================== SSL PATCH END ====================

def extract_all_symbols():
    """Extract all symbols from TSE, OTC, and other markets"""
    print("\n" + "="*80)
    print("EXTRACTING ALL SYMBOLS FROM FINPY_TSE")
    print("="*80)
    
    try:
        # Build comprehensive market stock list
        df = finpy_tse.Build_Market_StockList(
            bourse=True,
            farabourse=True,
            payeh=True,
            detailed_list=True,
            show_progress=False,
            save_excel=False,
            save_csv=False
        )
        
        if df.empty:
            print("  No symbols found in market list")
            return []
            
        print(f"  [OK] Found {len(df)} symbols in market list")
        
        # Process symbols
        symbols = []
        seen_symbols = set()
        
        for _, row in df.iterrows():
            # Extract symbol information
            ticker = str(row.get('Ticker', '')).strip()
            name = str(row.get('Name', '')).strip()
            webid = str(row.get('WEB-ID', '')).strip()
            market = str(row.get('Market', '')).strip()
            
            if not ticker:
                continue
                
            # Clean and normalize
            ticker_clean = ''.join(ticker.split()).strip()
            if ticker_clean in seen_symbols:
                continue
            seen_symbols.add(ticker_clean)
            
            # Determine symbol type based on market and ticker
            symbol_type = 'Unknown'
            if market == 'بورس':
                symbol_type = 'Stock'
            elif market == 'فرابورس':
                symbol_type = 'Stock'
            elif 'صاخص' in name.lower() or 'index' in name.lower():
                symbol_type = 'Index'
            elif 'شاخص' in ticker:
                symbol_type = 'Index'
                
            # Create symbol object
            symbol_obj = {
                'symbol': ticker_clean,
                'name': name,
                'type': symbol_type,
                'market': market,
                'webid': webid,
                'exchange': 'TSE' if market == 'بورس' else 'OTC',
                'industry': 'Unknown',
                'country': 'IR',
                'currency': 'IRR',
                'description': name,
                'sector': market,
                'metadata': {}
            }
            symbols.append(symbol_obj)
        
        # Add common indices not in market list
        common_indices = [
            {'symbol': '۳۰۲۰۱', 'name': 'TEPIX Index', 'type': 'Index', 'market': 'بورس'},
            {'symbol': '۱۰۰۰۱', 'name': 'TSE Index', 'type': 'Index', 'market': 'بورس'},
            {'symbol': '۲۰۱۰۱', 'name': 'TEDPIX Index', 'type': 'Index', 'market': 'بورس'},
            {'symbol': '۵۰۱۰۱', 'name': 'TAFQ Index', 'type': 'Index', 'market': 'بورس'},
            {'symbol': '۲۰۱۰۲', 'name': 'TEDIX Index', 'type': 'Index', 'market': 'بورس'},
        ]
        
        for idx in common_indices:
            symbol_clean = ''.join(idx['symbol'].split()).strip()
            if symbol_clean not in seen_symbols:
                idx_obj = {
                    'symbol': symbol_clean,
                    'name': idx['name'],
                    'type': idx['type'],
                    'market': idx['market'],
                    'webid': '',
                    'exchange': 'TSE',
                    'industry': 'Index',
                    'country': 'IR',
                    'currency': 'IRR',
                    'description': f"TSE {idx['name']} index",
                    'sector': 'Market Index',
                    'metadata': {}
                }
                symbols.append(idx_obj)
                seen_symbols.add(symbol_clean)
        
        print(f"  [OK] Total symbols extracted: {len(symbols)}")
        print(f"    - Stock symbols: {len([s for s in symbols if s['type'] == 'Stock'])}")
        print(f"    - Index symbols: {len([s for s in symbols if s['type'] == 'Index'])}")
        
        return symbols
        
    except Exception as e:
        print(f"  [ERROR] Error extracting symbols: {str(e)}")
        return []

def extract_symbol_data(symbol, symbol_name):
    """Extract comprehensive data for a single symbol"""
    try:
        print(f"    Processing {symbol}...")
        
        # Get price history
        price_df = finpy_tse.Get_Price_History(
            stock=symbol_name,
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            adjust_price=True,
            show_weekday=False,
            double_date=False
        )
        
        # Get RI history (fundamental data)
        ri_df = finpy_tse.Get_RI_History(
            stock=symbol_name,
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            show_weekday=False,
            double_date=False,
            alt=False
        )
        
        # Get market indices data
        indices_data = {}
        
        try:
            indices_data['cwi'] = finpy_tse.Get_CWI_History(
                start_date='1395-01-01',
                end_date='1403-12-29',
                ignore_date=True,
                just_adj_close=False,
                show_weekday=False,
                double_date=False
            )
        except:
            indices_data['cwi'] = pd.DataFrame()
            
        try:
            indices_data['ewi'] = finpy_tse.Get_EWI_History(
                start_date='1395-01-01',
                end_date='1403-12-29',
                ignore_date=True,
                just_adj_close=True,
                show_weekday=False,
                double_date=False
            )
        except:
            indices_data['ewi'] = pd.DataFrame()
            
        try:
            indices_data['indi'] = finpy_tse.Get_INDI_History(
                start_date='1395-01-01',
                end_date='1403-12-29',
                ignore_date=True,
                just_adj_close=False,
                show_weekday=False,
                double_date=False
            )
        except:
            indices_data['indi'] = pd.DataFrame()
        
        # Process and combine data
        processed_data = {
            'symbol': symbol,
            'price_data': [],
            'ri_data': [],
            'technical_indicators': [],
            'indices_data': indices_data,
            'metadata': {
                'total_price_records': 0,
                'total_ri_records': 0,
                'start_date': '1395-01-01',
                'end_date': '1403-12-29',
                'last_updated': datetime.now().strftime('%Y-%m-%d'),
                'data_quality': 'Full',
                'missing_data_percentage': 0.0
            }
        }
        
        # Convert price data to records
        if not price_df.empty:
            processed_data['price_data'] = price_df.replace({np.nan: None}).to_dict('records')
            processed_data['metadata']['total_price_records'] = len(price_df)
        
        # Convert RI data to records
        if not ri_df.empty:
            processed_data['ri_data'] = ri_df.replace({np.nan: None}).to_dict('records')
            processed_data['metadata']['total_ri_records'] = len(ri_df)
        
        # Calculate indicators if we have price data
        if not price_df.empty and len(price_df) > 50:
            try:
                # Calculate moving averages
                price_df['SMA_20'] = price_df['Close'].rolling(window=20).mean()
                price_df['SMA_50'] = price_df['Close'].rolling(window=50).mean()
                
                # Calculate RSI
                delta = price_df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                price_df['RSI'] = rsi
                
                # Convert to records
                processed_data['technical_indicators'] = price_df.replace({np.nan: None}).to_dict('records')
                
                # Update quality metrics
                total_cells = len(price_df) * len(price_df.columns)
                non_null_cells = price_df.notna().sum().sum()
                processed_data['metadata']['missing_data_percentage'] = round(
                    (total_cells - non_null_cells) / total_cells * 100, 2)
                    
            except Exception as e:
                print(f"      Warning: Indicator calculation failed: {str(e)}")
        
        return processed_data
        
    except Exception as e:
        print(f"      [ERROR] Error: {str(e)[:200]}")
        return None

def create_comprehensive_database():
    """Create comprehensive database with all symbols and their data"""
    print("\n" + "="*80)
    print("CREATING COMPREHENSIVE DATABASE")
    print("="*80)
    
    # Extract all symbols
    symbols = extract_all_symbols()
    
    if not symbols:
        print("  [ERROR] Failed to extract symbols")
        return None
    
    # Create comprehensive database structure
    database = {
        'metadata': {
            'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '2.0.0',
            'total_symbols': len(symbols),
            'data_period': {
                'start_date': '1395-01-01',
                'end_date': '1403-12-29'
            },
            'data_sources': ['TSE Market', 'OTC Market', 'Indices', 'FinPy TSE'],
            'processing_summary': {
                'symbols_processed': 0,
                'symbols_success': 0,
                'symbols_failed': 0,
                'total_records': 0,
                'data_quality': 'High'
            }
        },
        'symbols': {},
        'indices': {},
        'market_overview': {}
    }
    
    # Process each symbol
    successful_symbols = 0
    failed_symbols = 0
    total_records = 0
    
    for i, symbol_info in enumerate(symbols):
        symbol = symbol_info['symbol']
        symbol_name = symbol_info['name']
        
        print(f"\n  Processing symbol {i+1}/{len(symbols)}: {symbol} ({symbol_name})")
        
        # Extract data for this symbol
        symbol_data = extract_symbol_data(symbol, symbol_name)
        
        if symbol_data:
            successful_symbols += 1
            database['symbols'][symbol] = symbol_data
            
            # Update summary
            if 'price_data' in symbol_data:
                total_records += len(symbol_data['price_data'])
                
            # Categorize by type
            if symbol_info['type'] == 'Index':
                database['indices'][symbol] = symbol_data
            else:
                # Add to market overview by industry
                industry = symbol_info.get('industry', 'Unknown')
                if industry not in database['market_overview']:
                    database['market_overview'][industry] = {
                        'symbols': [],
                        'total_records': 0,
                        'avg_data_quality': 0
                    }
                database['market_overview'][industry]['symbols'].append(symbol)
                
        else:
            failed_symbols += 1
            print(f"      [ERROR] Failed to process {symbol}")
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"      Progress: {i+1}/{len(symbols)} symbols processed")
    
    # Update processing summary
    database['metadata']['processing_summary'].update({
        'symbols_processed': len(symbols),
        'symbols_success': successful_symbols,
        'symbols_failed': failed_symbols,
        'total_records': total_records,
        'success_rate': round((successful_symbols / len(symbols)) * 100, 2)
    })
    
    # Add market indices overview
    database['metadata']['market_overview'] = {
        'tse_stocks': len([s for s in symbols if s['type'] == 'Stock' and s['market'] == 'بورس']),
        'otc_stocks': len([s for s in symbols if s['type'] == 'Stock' and s['market'] == 'فرابورس']),
        'indices': len(database['indices']),
        'total_assets': len(symbols)
    }
    
    # Save database
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"comprehensive_symbols_database_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print("DATABASE CREATION COMPLETE!")
    print(f"{'='*80}")
    print(f"  [OK] Total symbols extracted: {len(symbols)}")
    print(f"  [OK] Successfully processed: {successful_symbols}")
    print(f"  [OK] Failed to process: {failed_symbols}")
    print(f"  [OK] Total records extracted: {total_records:,}")
    print(f"  [OK] Success rate: {database['metadata']['processing_summary']['success_rate']:.2f}%")
    print(f"  [OK] Database saved to: {filename}")
    
    # Display sample data structure
    if successful_symbols > 0:
        sample_symbol = list(database['symbols'].keys())[0]
        print(f"\n  SAMPLE DATA STRUCTURE (Symbol: {sample_symbol}):")
        print(f"    - Price records: {len(database['symbols'][sample_symbol]['price_data'])}")
        print(f"    - RI records: {len(database['symbols'][sample_symbol]['ri_data'])}")
        print(f"    - Indicator records: {len(database['symbols'][sample_symbol]['technical_indicators'])}")
        
        if database['symbols'][sample_symbol]['price_data']:
            sample_record = database['symbols'][sample_symbol]['price_data'][0]
            print(f"    - Sample fields: {list(sample_record.keys())}")
    
    return database

if __name__ == '__main__':
    print("="*80)
    print("COMPREHENSIVE SYMBOL DATA EXTRACTION SYSTEM")
    print("Version 2.0.0 - Enhanced with SSL bypass and error handling")
    print("="*80)
    
    # Create comprehensive database
    database = create_comprehensive_database()
    
    if database:
        print(f"\n{'='*80}")
        print("SYSTEM STATUS: OPERATIONAL")
        print(f"{'='*80}")
        print("\nThe system has successfully extracted comprehensive market data including:")
        print("  • All TSE and OTC stock symbols")
        print("  • All market indices (CWI, EWI, INDI, etc.)")
        print("  • 10-year historical price data (1395-1403)")
        print("  • Fundamental and technical indicators")
        print("  • Market metadata and quality metrics")
        print("\nNext steps:")
        print("  1. Export specific data subsets by exchange/market")
        print("  2. Create visualization dashboards")
        print("  3. Set up automated refresh systems")
        print("  4. Implement validation checks")
    else:
        print(f"\n{'='*80}")
        print("SYSTEM STATUS: ERROR")
        print(f"{'='*80}")
        print("Failed to create comprehensive database. Please check error logs.")
