import sqlite3

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Get the schema for symbols table to understand constraints
cursor.execute('PRAGMA table_info(symbols)')
schema = cursor.fetchall()

# Write to file to avoid encoding issues
with open('schema_info.txt', 'w', encoding='utf-8') as f:
    f.write('Current symbols table schema:\n')
    for col in schema:
        f.write(f'  {col[0]}: {col[2]} {col[4] if col[4] else ""}\n')
    
    f.write('\nType constraint: only Stock, Index, Currency, Commodity, OTC, ETF allowed\n')

print('Schema info written to schema_info.txt')
conn.close()