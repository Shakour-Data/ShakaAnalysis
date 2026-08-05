#!/usr/bin/env python3
"""
Export Module - Export data by subcategory (exchange, type, industry, etc.)
"""

import sqlite3
import csv
import json
import os
from datetime import datetime
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'market_data.db')
EXPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'exports')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def export_by_exchange(exchange='TSE', format='csv'):
    """Export data for a specific exchange"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.symbol, s.name, s.type, s.industry
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.exchange = ? AND s.is_active = 1
        ORDER BY s.symbol, p.date
    """
    
    df = pd.read_sql_query(query, conn, params=(exchange,))
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, f"{exchange}_data", format)

def export_by_type(symbol_type='Stock', format='csv'):
    """Export data for a specific symbol type"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.symbol, s.name, s.exchange, s.industry
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.type = ? AND s.is_active = 1
        ORDER BY s.symbol, p.date
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol_type,))
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, f"{symbol_type}_data", format)

def export_by_industry(industry, format='csv'):
    """Export data for a specific industry"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.symbol, s.name, s.type, s.exchange
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.industry = ? AND s.is_active = 1
        ORDER BY s.symbol, p.date
    """
    
    df = pd.read_sql_query(query, conn, params=(industry,))
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, f"{industry.replace(' ', '_')}_data", format)

def export_by_symbol(symbol, format='csv'):
    """Export data for a specific symbol"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.name as symbol_name, s.type, s.exchange, s.industry
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.symbol = ? AND s.is_active = 1
        ORDER BY p.date
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, f"{symbol}_data", format)

def export_all_data(format='csv'):
    """Export all data"""
    conn = get_db_connection()
    
    query = """
        SELECT p.*, s.symbol, s.name, s.type, s.exchange, s.industry
        FROM price_data p
        JOIN symbols s ON p.symbol_id = s.id
        WHERE s.is_active = 1
        ORDER BY s.symbol, p.date
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, "all_market_data", format)

def export_symbol_list(format='json'):
    """Export the complete symbol list"""
    conn = get_db_connection()
    
    query = """
        SELECT symbol, name, type, exchange, industry, sector
        FROM symbols 
        WHERE is_active = 1
        ORDER BY symbol
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return None
    
    return _save_export(df, "symbol_list", format)

def _save_export(df, filename, format):
    """Save DataFrame to specified format"""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    full_filename = f"{filename}_{timestamp}"
    
    if format.lower() == 'csv':
        filepath = os.path.join(EXPORT_DIR, f"{full_filename}.csv")
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
    elif format.lower() == 'json':
        filepath = os.path.join(EXPORT_DIR, f"{full_filename}.json")
        df.to_json(filepath, orient='records', date_format='iso', force_ascii=False)
    elif format.lower() == 'excel':
        filepath = os.path.join(EXPORT_DIR, f"{full_filename}.xlsx")
        df.to_excel(filepath, index=False)
    else:
        filepath = os.path.join(EXPORT_DIR, f"{full_filename}.csv")
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    # Log export
    log_export(filepath, format, len(df))
    
    return filepath

def log_export(filepath, format, record_count):
    """Log export to database"""
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO export_history (export_type, symbol, format, file_path, record_count)
        VALUES (?, ?, ?, ?, ?)
    """, ('subcategory_export', '', format, filepath, record_count))
    conn.commit()
    conn.close()

def get_export_history():
    """Get export history from database"""
    conn = get_db_connection()
    query = "SELECT * FROM export_history ORDER BY created_at DESC LIMIT 20"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def list_available_exports():
    """List all available export options"""
    conn = get_db_connection()
    
    exchanges = conn.execute("SELECT DISTINCT exchange FROM symbols WHERE is_active = 1").fetchall()
    types = conn.execute("SELECT DISTINCT type FROM symbols WHERE is_active = 1").fetchall()
    industries = conn.execute("SELECT DISTINCT industry FROM symbols WHERE is_active = 1").fetchall()
    symbols = conn.execute("SELECT symbol, name FROM symbols WHERE is_active = 1 ORDER BY symbol").fetchall()
    
    conn.close()
    
    return {
        'exchanges': [dict(e) for e in exchanges],
        'types': [dict(t) for t in types],
        'industries': [dict(i) for i in industries],
        'symbols': [dict(s) for s in symbols]
    }

def run_export_tests():
    """Test all export functionality"""
    print("=" * 60)
    print("EXPORT MODULE TESTS")
    print("=" * 60)
    
    # Test 1: Export symbol list
    print("\n1. Testing symbol list export...")
    result = export_symbol_list(format='json')
    if result:
        print(f"   ✅ Symbol list exported: {result}")
    else:
        print("   ❌ Symbol list export failed")
    
    # Test 2: Export by exchange
    print("\n2. Testing export by exchange (TSE)...")
    result = export_by_exchange('TSE', format='csv')
    if result:
        print(f"   ✅ TSE data exported: {result}")
    else:
        print("   ⚠️  No TSE data available")
    
    # Test 3: Export by type
    print("\n3. Testing export by type (Stock)...")
    result = export_by_type('Stock', format='csv')
    if result:
        print(f"   ✅ Stock data exported: {result}")
    else:
        print("   ⚠️  No stock data available")
    
    # Test 4: Export by symbol
    print("\n4. Testing export by symbol...")
    result = export_by_symbol('خودرو', format='json')
    if result:
        print(f"   ✅ خودرو data exported: {result}")
    else:
        print("   ⚠️  No data for خودرو")
    
    # Test 5: Export all data
    print("\n5. Testing full export...")
    result = export_all_data(format='csv')
    if result:
        print(f"   ✅ All data exported: {result}")
    else:
        print("   ⚠️  No data to export")
    
    # Test 6: Export history
    print("\n6. Testing export history...")
    history = get_export_history()
    if not history.empty:
        print(f"   ✅ Export history: {len(history)} records")
    else:
        print("   ℹ️  No export history yet")
    
    print("\n" + "=" * 60)
    print("EXPORT TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_export_tests()