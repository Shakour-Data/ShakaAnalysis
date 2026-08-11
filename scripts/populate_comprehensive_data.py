import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Get IDs for new indices
cursor.execute("SELECT id, symbol FROM symbols WHERE symbol IN ('\u0634\u0627\u062e\u0635 \u06a9\u0644 \u0633\u0647\u0645', '\u0634\u0627\u062e\u0635 \u0628\u0631\u0627\u0628\u0631 \u0648\u0632\u0646', '\u0634\u0627\u062e\u0635 \u0635\u0646\u0639\u062a')")
index_ids = cursor.fetchall()
print(f'Found {len(index_ids)} new indices to populate')

# Add 100 days of price data for each new index
base_date = datetime(2026, 1, 1)

for idx_id, symbol in index_ids:
    base_price = random.uniform(15000, 25000)
    for i in range(100):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        # Add some market-like volatility
        daily_change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + daily_change * 0.3)
        close_price = base_price * (1 + daily_change)
        high = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        volume = random.randint(500000, 5000000)
        value = ((high + low) / 2) * volume
        adj_close = close_price
        
        cursor.execute('''INSERT INTO price_data 
            (symbol_id, Date, Open, High, Low, Close, Volume, Value, adj_close) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (idx_id, date, round(open_price, 2), round(high, 2), round(low, 2), 
             round(close_price, 2), volume, round(value, 2), round(adj_close, 2)))
        
        base_price = close_price  # Use close as next day's base

# Add price data for all stocks
cursor.execute('''
    SELECT s.id, s.symbol FROM symbols s
    WHERE s.is_active = 1 AND s.type = 'Stock'
    AND NOT EXISTS (SELECT 1 FROM price_data WHERE symbol_id = s.id)
''')
stocks_no_data = cursor.fetchall()

print(f'\nAdding price data for {len(stocks_no_data)} stocks without data...')
for stock_id, stock_symbol in stocks_no_data:
    base_price = random.uniform(1000, 50000)
    for i in range(100):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_change = random.uniform(-0.03, 0.03)
        open_price = base_price * (1 + daily_change * 0.3)
        close_price = base_price * (1 + daily_change)
        high = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        volume = random.randint(10000, 1000000)
        value = ((high + low) / 2) * volume
        adj_close = close_price
        
        cursor.execute('''INSERT INTO price_data 
            (symbol_id, Date, Open, High, Low, Close, Volume, Value, adj_close) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (stock_id, date, round(open_price, 2), round(high, 2), round(low, 2), 
             round(close_price, 2), volume, round(value, 2), round(adj_close, 2)))
        
        base_price = close_price

# Get the final counts
cursor.execute('SELECT COUNT(*) FROM symbols WHERE is_active = 1')
final_symbols = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM price_data')
final_price_rows = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT symbol_id) FROM price_data')
symbols_with_data = cursor.fetchone()[0]

print(f'\n=== FINAL SUMMARY ===')
print(f'Total symbols: {final_symbols}')
print(f'Total price data rows: {final_price_rows}')
print(f'Symbols with price data: {symbols_with_data}')
print(f'Average rows per symbol: {final_price_rows // max(1, symbols_with_data)}')

conn.close()
print('\nPopulation complete.')