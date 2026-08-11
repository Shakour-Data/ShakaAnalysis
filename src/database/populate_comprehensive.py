#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate database with comprehensive market data."""

import sqlite3
import json
import os
from datetime import datetime, timedelta
import random

PROJECT_DIR = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'market_data.db')

def populate_database():
    """Populate database with comprehensive sample data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Clear existing data (keeping schema)
    cur.execute('DELETE FROM price_data')
    cur.execute('DELETE FROM indices')
    cur.execute('DELETE FROM analysis_records')
    cur.execute('DELETE FROM export_history')
    cur.execute('DELETE FROM data_metadata')
    cur.execute('DELETE FROM symbols')
    conn.commit()

    # Define industries and sectors
    industries_sectors = [
        # Financial Services
        ('Banking', 'Banks', ['Bank Melli Iran', 'Bank Saderat Iran', 'Bank Tejarat']),
        ('Insurance', 'Financial Services', ['Iran Insurance', 'Asia Insurance', 'Alborz Insurance']),
        ('Investment', 'Financial Services', ['Tamadoni Investment', 'Paya Development']),

        # Manufacturing & Industrial
        ('Automotive', 'Manufacturing', ['Iran Khodro', 'Saipa', 'Pars Khodro']),
        ('Steel', 'Basic Materials', ['Foulad Mobarakeh', 'Foulad Sepahan', 'Khouzestan Steel']),
        ('Cement', 'Basic Materials', ['Sepahan Cement', 'Fars Cement', 'Tehran Cement']),
        ('Petrochemical', 'Energy', ['Jam Petrochemical', 'Marun Petrochemical', 'Aryl Petrochemical']),

        # Technology & Telecom
        ('Telecommunications', 'Technology', ['Mobile Communication', 'Irancell', 'Rightel']),
        ('Information Technology', 'Technology', ['Pardis Technology', 'Shatel', 'Asiatec']),

        # Consumer & Retail
        ('Food & Beverage', 'Consumer Goods', ['Shirin Asal', 'Kalleh', 'Pegah']),
        ('Pharmaceuticals', 'Healthcare', ['Daroupakhsh', 'Ibnu Sina', 'Exir']),
        ('Retail', 'Consumer Services', ['Refah Chain Stores', 'Hyperstar', 'Etka']),

        # Energy & Utilities
        ('Oil & Gas', 'Energy', ['National Iranian Oil', 'Gas Company', 'Power Generation']),
        ('Electricity', 'Utilities', ['Tavanir', 'Regional Power Companies']),

        # Services & Transportation
        ('Transportation', 'Industrials', ['Iran Air', 'IRICA', 'RAJA']),
        ('Logistics', 'Services', ['Post Bank', 'RAILWAY', 'PORT & SHIPPING']),
    ]

    # Insert symbols
    symbol_map = {}  # symbol -> id
    all_symbols = []

    for industry, sector, companies in industries_sectors:
        for company in companies:
            # Generate symbol (first 4 letters of each word)
            symbol_base = ''.join([word[0].upper() for word in company.split()[:2]])
            if len(symbol_base) < 2:
                symbol_base = company[:4].upper()
            symbol = f"{symbol_base}{random.randint(10, 99)}"
            
            # Ensure symbol is unique
            counter = 0
            original_symbol = symbol
            while symbol in [s[0] for s in all_symbols]:
                counter += 1
                symbol = f"{original_symbol[:3]}{counter:02d}"
            
            # Determine type (mostly stocks, with some special cases)
            if 'Bank' in company or 'Insurance' in company or 'Investment' in company:
                sym_type = random.choice(['Stock', 'OTC'])  # Some financials might be OTC
            elif 'Telecom' in company or 'Mobile' in company:
                sym_type = 'Stock'
            else:
                sym_type = 'Stock'
            
            all_symbols.append((symbol, company, sym_type, industry, sector))

    # Add some special symbols
    special_symbols = [
        # Indices
        ('TEPIX', 'TEPIX Index', 'Index', 'Market Index', 'Main Index'),
        ('IFX', 'IFX Index', 'Index', 'Financial Index', 'Financials'),
        ('IDX', 'Industrial Index', 'Index', 'Industrial Index', 'Industrials'),
        # Currencies
        ('USD', 'US Dollar', 'Currency', 'Foreign Exchange', 'Major'),
        ('EUR', 'Euro', 'Currency', 'Foreign Exchange', 'Major'),
        ('GBP', 'British Pound', 'Currency', 'Foreign Exchange', 'Major'),
        # Cryptocurrencies (simulated)
        ('BTC', 'Bitcoin', 'Currency', 'Digital Assets', 'Cryptocurrency'),
        ('ETH', 'Ethereum', 'Currency', 'Digital Assets', 'Cryptocurrency'),
    ]
    
    for symbol, name, sym_type, industry, sector in special_symbols:
        all_symbols.append((symbol, name, sym_type, industry, sector))

    # Insert all symbols
    for symbol, name, sym_type, industry, sector in all_symbols:
        cur.execute('''
            INSERT INTO symbols (symbol, name, full_name, type, exchange, industry, sector, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (symbol, name, name, sym_type, 'TSE', industry, sector))
        symbol_id = cur.lastrowid
        symbol_map[symbol] = symbol_id

    conn.commit()
    print(f'Inserted {len(all_symbols)} symbols')

    # Generate price data for each symbol (last 6 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    total_records = 0
    for symbol, symbol_id in symbol_map.items():
        # Skip indices and currencies for detailed price data (handle separately)
        cur.execute('SELECT type FROM symbols WHERE id = ?', (symbol_id,))
        sym_type = cur.fetchone()[0]
        
        if sym_type in ['Currency']:
            # Simple currency data (fixed or slowly varying)
            base_price = random.uniform(40000, 50000) if 'USD' in symbol else random.uniform(1, 100)
            days = (end_date - start_date).days
            for i in range(days):
                date = start_date + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                # Small random walk
                change = random.uniform(-0.02, 0.02)
                base_price *= (1 + change)
                base_price = max(base_price, 0.01)  # Prevent negative
                
                cur.execute('''
                    INSERT INTO price_data 
                    (symbol_id, date, weekday, open, high, low, close, volume, value, 
                     sma_20, sma_50, rsi, macd, macd_signal, macd_histogram, bb_upper, bb_lower)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol_id, date_str, date.strftime('%A'),
                    base_price * random.uniform(0.995, 1.005),
                    base_price * random.uniform(1.000, 1.010),
                    base_price * random.uniform(0.990, 1.000),
                    base_price,
                    random.randint(1000000, 10000000),
                    base_price * random.randint(1000000, 10000000) * random.uniform(0.9, 1.1),
                    base_price * random.uniform(0.98, 1.02),
                    base_price * random.uniform(0.95, 1.05),
                    random.uniform(30, 70),  # RSI
                    random.uniform(-2, 2),   # MACD
                    random.uniform(-1.5, 1.5), # MACD Signal
                    random.uniform(-0.5, 0.5), # MACD Histogram
                    base_price * random.uniform(1.02, 1.05), # BB Upper
                    base_price * random.uniform(0.95, 0.98)  # BB Lower
                ))
                total_records += 1
        else:
            # Regular stock/OTC price data with more volatility
            base_price = random.uniform(1000, 50000) if sym_type != 'Index' else random.uniform(100000, 2000000)
            days = (end_date - start_date).days
            prices = []
            
            for i in range(days):
                date = start_date + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                # Generate OHLC with some trend and volatility
                daily_volatility = random.uniform(0.01, 0.05)  # 1-5% daily volatility
                trend = random.uniform(-0.001, 0.001)  # Slight trend
                
                if i == 0:
                    open_price = base_price
                else:
                    open_price = prices[-1][4]  # Previous close
                
                # Generate high/low based on volatility
                change = random.uniform(-daily_volatility, daily_volatility) + trend
                close_price = open_price * (1 + change)
                
                high_price = max(open_price, close_price) * (1 + random.uniform(0, daily_volatility/2))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, daily_volatility/2))
                
                # Ensure OHLC relationship
                high_price = max(high_price, open_price, close_price)
                low_price = min(low_price, open_price, close_price)
                
                volume = random.randint(500000, 5000000)
                value = volume * ((open_price + high_price + low_price + close_price) / 4)
                
                # Calculate indicators (simplified)
                prices.append(close_price)
                
                # Simple indicators (would normally be calculated from price series)
                if len(prices) >= 20:
                    sma_20 = sum(prices[-20:]) / 20
                    # Simple RSI approximation
                    gains = [max(0, prices[-j] - prices[-j-1]) for j in range(1, min(15, len(prices)))]
                    losses = [max(0, prices[-j-1] - prices[-j]) for j in range(1, min(15, len(prices)))]
                    avg_gain = sum(gains) / len(gains) if gains else 0
                    avg_loss = sum(losses) / len(losses) if losses else 0.001
                    rs = avg_gain / avg_loss if avg_loss != 0 else 100
                    rsi = 100 - (100 / (1 + rs)) if rs != 0 else 0
                    macd = random.uniform(-5, 5)
                    macd_signal = macd * random.uniform(0.8, 1.2)
                    macd_hist = macd - macd_signal
                    bb_middle = sma_20
                    bb_std = (sum([(p - sma_20)**2 for p in prices[-20:]]) / 20)**0.5 if len(prices) >= 20 else base_price * 0.02
                    bb_upper = bb_middle + (2 * bb_std)
                    bb_lower = bb_middle - (2 * bb_std)
                else:
                    sma_20 = base_price
                    rsi = 50
                    macd = 0
                    macd_signal = 0
                    macd_hist = 0
                    bb_upper = base_price * 1.02
                    bb_lower = base_price * 0.98
                
                cur.execute('''
                    INSERT INTO price_data 
                    (symbol_id, date, weekday, open, high, low, close, final_price, volume, value, 
                     adj_close, adj_final, sma_20, sma_50, rsi, macd, macd_signal, macd_histogram,
                     bb_upper, bb_lower, resistances, supports, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (
                    symbol_id, date_str, date.strftime('%A'),
                    round(open_price, 2), round(high_price, 2), round(low_price, 2), round(close_price, 2),
                    round(close_price * 0.995, 2),  # Final price slightly lower
                    volume, round(value, 2),
                    round(close_price, 2), round(close_price * 0.99, 2),
                    round(sma_20, 2), round(sma_20 * 1.01, 2), round(rsi, 2),
                    round(macd, 4), round(macd_signal, 4), round(macd_hist, 4),
                    round(bb_upper, 2), round(bb_lower, 2),
                    f"{round(high_price * 1.1, 0)},{round(high_price * 1.2, 0)}",
                    f"{round(low_price * 0.9, 0)},{round(low_price * 0.8, 0)}"
                ))
                total_records += 1
                
                prices.append(close_price)
                # Keep only last 100 prices for indicator calculations
                if len(prices) > 100:
                    prices.pop(0)

    conn.commit()
    print(f'Inserted {total_records} price records')

    # Generate some index data (daily values)
    index_symbols = [sym for sym, sid in symbol_map.items() 
                    if cur.execute('SELECT type FROM symbols WHERE id = ?', (sid,)).fetchone()[0] == 'Index']
    
    index_records = 0
    for symbol in index_symbols:
        symbol_id = symbol_map[symbol]
        base_value = random.uniform(100000, 2000000)
        days = (end_date - start_date).days
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Index moves less than individual stocks
            change = random.uniform(-0.015, 0.015)
            base_value *= (1 + change)
            base_value = max(base_value, 1000)  # Floor
            
            cur.execute('''
                INSERT INTO indices (symbol_id, date, close, open, high, low, volume, value, adj_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol_id, date_str,
                round(base_value, 2),
                round(base_value * random.uniform(0.998, 1.002), 2),
                round(base_value * random.uniform(1.000, 1.005), 2),
                round(base_value * random.uniform(0.995, 1.000), 2),
                random.randint(100000, 1000000),
                round(base_value * random.randint(100000, 1000000), 2),
                round(base_value * random.uniform(0.99, 1.01), 2)
            ))
            index_records += 1

    conn.commit()
    print(f'Inserted {index_records} index records')

    # Generate some analysis records
    stock_symbols = [sym for sym, sid in symbol_map.items() 
                    if cur.execute('SELECT type FROM symbols WHERE id = ?', (sid,)).fetchone()[0] in ['Stock', 'OTC']]
    
    analysis_records = 0
    for _ in range(min(20, len(stock_symbols))):  # Up to 20 analyses
        symbol = random.choice(stock_symbols)
        symbol_id = symbol_map[symbol]
        
        cur.execute('''
            INSERT INTO analysis_records 
            (symbol_id, analysis, timeframe, sentiment, target_price, stop_loss, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol_id,
            f'Technical analysis shows {random.choice(["bullish", "bearish"])} momentum with strong support/resistance levels.',
            random.choice(['1W', '1M', '3M', '6M']),
            random.choice(['Bullish', 'Bearish', 'Neutral']),
            round(random.uniform(15000, 50000), 2),
            round(random.uniform(10000, 30000), 2),
            round(random.uniform(60, 95), 2)
        ))
        analysis_records += 1

    conn.commit()
    print(f'Inserted {analysis_records} analysis records')

    # Generate export history
    export_records = 0
    for _ in range(10):
        symbol = random.choice(list(symbol_map.keys()))
        symbol_id = symbol_map[symbol]
        
        cur.execute('''
            INSERT INTO export_history 
            (export_type, symbol_id, format, file_path, record_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            random.choice(['price', 'indicators', 'analysis']),
            symbol_id if random.random() > 0.3 else None,  # Some exports might not be symbol-specific
            random.choice(['CSV', 'Excel', 'PDF']),
            f'/exports/export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{random.choice(["csv", "xlsx", "pdf"]).lower()}',
            random.randint(100, 10000)
        ))
        export_records += 1

    conn.commit()
    print(f'Inserted {export_records} export records')

    # Generate data metadata
    metadata_records = 0
    for symbol in list(symbol_map.keys())[:10]:  # First 10 symbols
        symbol_id = symbol_map[symbol]
        
        cur.execute('''
            INSERT INTO data_metadata 
            (symbol_id, data_type, start_date, end_date, total_records, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            symbol_id,
            'price',
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            random.randint(150, 180),
            random.choice(['complete', 'updating', 'pending'])
        ))
        metadata_records += 1

    conn.commit()
    print(f'Inserted {metadata_records} metadata records')

    # Final verification
    print('\n=== Final Database Summary ===')
    for table, query in [
        ('symbols', 'SELECT COUNT(*) FROM symbols'),
        ('price_data', 'SELECT COUNT(*) FROM price_data'),
        ('indices', 'SELECT COUNT(*) FROM indices'),
        ('analysis_records', 'SELECT COUNT(*) FROM analysis_records'),
        ('export_history', 'SELECT COUNT(*) FROM export_history'),
        ('data_metadata', 'SELECT COUNT(*) FROM data_metadata'),
        ('indicator_config', 'SELECT COUNT(*) FROM indicator_config'),
    ]:
        count = cur.execute(query).fetchone()[0]
        print(f'{table:20}: {count:6} records')

    # Show foreign key relationships
    print('\n=== Foreign Key Relationships ===')
    fk_tables = ['price_data', 'indices', 'analysis_records', 'export_history', 'data_metadata']
    for table in fk_tables:
        cur.execute(f'PRAGMA foreign_key_list({table})')
        fks = cur.fetchall()
        if fks:
            for fk in fks:
                print(f'{table}.{fk[3]} -> {fk[2]}.{fk[4]}')

    conn.close()
    print('\nDatabase population complete!')


if __name__ == '__main__':
    populate_database()