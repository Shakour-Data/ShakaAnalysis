import sqlite3

indices = [
    'شاخص کل سهم',       # Total Stock Index
    'شاخص برابر وزن',    # Total Equal Weight Index
    'شاخص صنعت'        # Industry Indices
]

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Verify all 3 requested indices exist
output = []
output.append('INDEX VERIFICATION:')
for idx in indices:
    cursor.execute('SELECT symbol, name, type FROM symbols WHERE symbol = ?', (idx,))
    row = cursor.fetchone()
    status = 'EXISTS' if row else 'MISSING'
    type_info = row[2] if row else 'N/A'
    output.append(f'{idx}: {status} - Type: {type_info}')

# Check price data availability
cursor.execute('SELECT symbol, name, type FROM symbols WHERE type = "Index"')
index_symbols = cursor.fetchall()
output.append('')
output.append(f'Total Index-type symbols: {len(index_symbols)}')
for sym in index_symbols:
    output.append(f'  {sym[0]} - {sym[1]}')

# Verify price data count
cursor.execute('SELECT COUNT(*) FROM price_data')
total_rows = cursor.fetchone()[0]
output.append('')
output.append(f'Total price data rows: {total_rows}')

# Check data per symbol
cursor.execute('''
    SELECT s.symbol, COUNT(pd.id) as data_rows
    FROM symbols s
    LEFT JOIN price_data pd ON pd.symbol_id = s.id
    GROUP BY s.symbol
    ORDER BY s.type, s.symbol
    LIMIT 10
''')
output.append('')
output.append('Sample data counts per symbol:')
for row in cursor.fetchall():
    output.append(f'  {row[0]}: {row[1]} rows')

conn.close()

# Write to file
with open('verification_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('Verification report written to verification_report.txt')