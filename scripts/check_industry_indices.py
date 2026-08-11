import sqlite3

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Get all Index type symbols (industry indices)
cursor.execute('SELECT symbol, name, type, sector FROM symbols WHERE type = "Index" ORDER BY name')
index_symbols = cursor.fetchall()

output = []
output.append('=== INDUSTRY INDICES IN SYSTEM ===')
output.append(f'Total Index symbols: {len(index_symbols)}')
output.append('')

# Group by sector if available
for symbol, name, type_rel, sector in index_symbols:
    sector_info = f' [{sector}]' if sector else ''
    output.append(f'{symbol:25} | {name:30} {sector_info}')

# Also check for any "Industry" type symbols
cursor.execute('SELECT symbol, name, type, sector FROM symbols WHERE type = "Industry" ORDER BY name')
industry_symbols = cursor.fetchall()
if industry_symbols:
    output.append('')
    output.append('=== INDUSTRY TYPE SYMBOLS ===')
    output.append(f'Total Industry symbols: {len(industry_symbols)}')
    for symbol, name, type_rel, sector in industry_symbols:
        sector_info = f' [{sector}]' if sector else ''
        output.append(f'{symbol:25} | {name:30} {sector_info}')

# Check sectors for Stock type
cursor.execute('SELECT DISTINCT sector FROM symbols WHERE sector IS NOT NULL AND sector != "" ORDER BY sector')
sectors = cursor.fetchall()
output.append('')
output.append('=== ALL UNIQUE SECTORS IN DATABASE ===')
for sector_tuple in sectors:
    output.append(f'  {sector_tuple[0]}')

conn.close()

# Write to file
with open('industry_indices_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('Industry indices report written to industry_indices_report.txt')