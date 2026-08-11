import sqlite3
import csv

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Get current counts
cursor.execute('SELECT COUNT(*) FROM symbols')
total_symbols = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM price_data')
total_price_rows = cursor.fetchone()[0]

print('CURRENT STATUS:')
print(f'Total symbols in database: {total_symbols}')
print(f'Total price data rows: {total_price_rows}')

# Get symbol types
cursor.execute('SELECT type, COUNT(*) FROM symbols WHERE is_active = 1 GROUP BY type')
type_counts = cursor.fetchall()
print('')
print('CURRENT SYMBOL TYPES:')
for t, cnt in type_counts:
    print(f'  {t:20} ({cnt} symbols)')

# Check existing price data per symbol
cursor.execute('''
    SELECT s.symbol, s.type, COUNT(pd.id) as rows
    FROM symbols s
    LEFT JOIN price_data pd ON pd.symbol_id = s.id
    WHERE s.is_active = 1
    GROUP BY s.symbol
    ORDER BY rows DESC
''')

print('')
print('PRICE DATA BY SYMBOL:')
for (symbol, type_rel, rows) in cursor.fetchall():
    print(f'  {symbol:15} | {type_rel} | {rows} rows')

# Check what types of symbols we have
unique_types = cursor.execute('SELECT DISTINCT type FROM symbols WHERE is_active = 1').fetchall()
print('')
print('SYMBOL TYPES IN DATABASE:')
for tup in unique_types:
    print(f'  {tup[0]}')

print('')
print('USER REQUIREMENTS:')
print('- Must support "Total Stock Index"')
print('- Must support "Total Equal Weight Index"')  
print('- Must support "Industry Indices"')
print('- Must support comprehensive market indices (100%)')

print('')
print('ANALYSIS:')
print(f'Current symbols: {total_symbols}')
print('User expects at least 105 symbols total')
print(f'Additional symbols needed: {max(0, 105 - total_symbols)}')

print('')
print('RECOMMENDATION:')
print('1. Add Total Stock Index symbol')
print('2. Add Total Equal Weight Index symbol') 
print('3. Add Industry Index symbols (multiple)')
print('4. Ensure price data exists for all symbols')
print('5. Verify test suite passes with comprehensive data')

conn.close()