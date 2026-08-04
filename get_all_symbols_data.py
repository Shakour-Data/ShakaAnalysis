#!/usr/bin/env python3
"""
Comprehensive symbol data extractor from finpy_tse module
Fetches all symbols, price data, and indicators from beginning of data available
"""

import ssl
import urllib3
import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# Patch requests to bypass SSL verification
session = requests.Session()
session.verify = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Bypass SSL verification at a deeper level
import urllib3.poolmanager
urllib3.poolmanager.PoolManager.connection_pool_kw = {'verify_ssl': False}

import finpy_tse as fpy

def get_all_symbols():
    """Get all symbols from TSE market"""
    print("Fetching all symbols from TSE market...")
    try:
        df = fpy.Build_Market_StockList(
            bourse=True,
            farabourse=True,
            payeh=True,
            detailed_list=True,
            show_progress=True,
            save_excel=False,
            save_csv=False
        )
        
        if not df.empty:
            symbols = []
            for _, row in df.iterrows():
                symbol_data = {
                    'symbol': row.get('Ticker', ''),
                    'name': row.get('Name', ''),
                    'exchange': row.get('Market', ''),
                    'webid': row.get('WEB-ID', ''),
                    'type': 'Stock',
                    'industry': 'Various'
                }
                symbols.append(symbol_data)
            
            print(f"Found {len(symbols)} symbols")
            return symbols
        else:
            print("No symbols found")
            return []
            
    except Exception as e:
        print(f"Error getting symbols: {str(e)}")
        return []

def get_symbol_data(symbol_name, symbol_name_persian):
    """Get comprehensive price data and indicators for a specific symbol"""
    try:
        print(f"Fetching data for {symbol_name} ({symbol_name_persian})...")
        
        price_df = fpy.Get_Price_History(
            stock=symbol_name_persian,
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            adjust_price=True,
            show_weekday=False,
            double_date=False
        )
        
        ri_df = fpy.Get_RI_History(
            stock=symbol_name_persian,
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            show_weekday=False,
            double_date=False,
            alt=False
        )
        
        indices = {}
        
        indices['cwi'] = fpy.Get_CWI_History(
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            just_adj_close=False,
            show_weekday=False,
            double_date=False
        )
        
        indices['ewi'] = fpy.Get_EWI_History(
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            just_adj_close=True,
            show_weekday=False,
            double_date=False
        )
        
        indices['indi'] = fpy.Get_INDI_History(
            start_date='1395-01-01',
            end_date='1403-12-29',
            ignore_date=True,
            just_adj_close=False,
            show_weekday=False,
            double_date=False
        )
        
        combined_data = {
            'symbol': symbol_name,
            'name': symbol_name_persian,
            'price_data': price_df.to_dict('records') if not price_df.empty else [],
            'ri_data': ri_df.to_dict('records') if not ri_df.empty else [],
            'indices': indices,
            'metadata': {
                'total_records': len(price_df) if not price_df.empty else 0,
                'start_date': '1395-01-01',
                'end_date': '1403-12-29',
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }
        }
        
        print(f"Successfully fetched {len(combined_data['price_data'])} price records for {symbol_name}")
        return combined_data
        
    except Exception as e:
        print(f"Error fetching data for {symbol_name}: {str(e)}")
        return None

def main():
    """Main function to get all data"""
    print("=" * 80)
    print("COMPREHENSIVE SYMBOL DATA EXTRACTION FROM FINPY_TSE")
    print("=" * 80)
    
    symbols = get_all_symbols()
    
    if not symbols:
        print("Failed to get symbols list. Exiting.")
        return
    
    comprehensive_data = {
        'metadata': {
            'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_symbols': len(symbols),
            'data_period': {
                'start_date': '1395-01-01',
                'end_date': '1403-12-29'
            },
            'sources': ['TSE Market', 'Farabourse Market', 'Payeh Market', 'Indices']
        },
        'symbols_data': {}
    }
    
    for i, symbol in enumerate(symbols):
        print(f"\nProcessing symbol {i+1}/{len(symbols)}: {symbol.get('symbol', 'N/A')}")
        
        symbol_name = symbol.get('symbol', '')
        name_persian = symbol.get('name', '')
        
        if symbol_name and name_persian:
            symbol_data = get_symbol_data(symbol_name, name_persian)
            if symbol_data:
                comprehensive_data['symbols_data'][symbol_name] = symbol_data
    
    output_filename = f"comprehensive_symbols_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE!")
    print(f"Total symbols processed: {len(comprehensive_data['symbols_data'])}")
    print(f"Data saved to: {output_filename}")
    print("=" * 80)
    
    total_price_records = sum(
        len(symbol_data['price_data']) 
        for symbol_data in comprehensive_data['symbols_data'].values()
        if symbol_data and 'price_data' in symbol_data
    )
    
    print(f"\nSUMMARY:")
    print(f"  Symbols with data: {len(comprehensive_data['symbols_data'])}")
    print(f"  Total price records: {total_price_records:,}")
    
    if comprehensive_data['symbols_data']:
        first_symbol = list(comprehensive_data['symbols_data'].keys())[0]
        print(f"\nSAMPLE DATA STRUCTURE (Symbol: {first_symbol}):")
        print(f"  Price records: {len(comprehensive_data['symbols_data'][first_symbol]['price_data'])}")
        print(f"  Indices included: {list(comprehensive_data['symbols_data'][first_symbol]['indices'].keys())}")
        if comprehensive_data['symbols_data'][first_symbol]['price_data']:
            print(f"  Sample price record fields: {list(comprehensive_data['symbols_data'][first_symbol]['price_data'][0].keys())}")

if __name__ == '__main__':
    main()