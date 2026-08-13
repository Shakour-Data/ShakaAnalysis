import sqlite3
import pandas as pd
import os

db_path = 'data/market_data.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get all symbols with name and type
c.execute("SELECT symbol, name, type, exchange FROM symbols ORDER BY type, symbol")
rows = c.fetchall()

# Separate into stocks and indices
stocks = []
indices = []
for row in rows:
    symbol, name, typ, exch = row
    if typ == 'Stock':
        stocks.append((symbol, name, exch))
    elif typ == 'Index':
        indices.append((symbol, name, exch))
    else:
        # fallback
        stocks.append((symbol, name, exch))

conn.close()

# Write to markdown file
output_dir = 'docs'
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'symbols_and_indices.md')

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('# Companies and Market Indices\n\n')
    f.write('## Companies (Stocks)\n\n')
    f.write('| Symbol | Name | Exchange |\n')
    f.write('|--------|------|----------|\n')
    for symbol, name, exch in stocks:
        # Escape pipe characters in name
        name_esc = str(name).replace('|', '\\|')
        f.write(f'| {symbol} | {name_esc} | {exch} |\n')
    
    f.write('\n## Market Indices\n\n')
    f.write('| Symbol | Name | Exchange |\n')
    f.write('|--------|------|----------|\n')
    for symbol, name, exch in indices:
        name_esc = str(name).replace('|', '\\|')
        f.write(f'| {symbol} | {name_esc} | {exch} |\n')

print(f'Written {len(stocks)} stocks and {len(indices)} indices to {output_file}')