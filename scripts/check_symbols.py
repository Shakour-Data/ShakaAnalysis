import sqlite3

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Get all symbols with their types
cursor.execute('SELECT symbol, name, type FROM symbols ORDER BY type, symbol')
rows = cursor.fetchall()

# Write to file to avoid console encoding issues
with open('symbols_report.txt', 'w', encoding='utf-8') as f:
    f.write(f'Total symbols in database: {len(rows)}\n')
    f.write('=' * 70 + '\n')
    
    for i, (symbol, name, t) in enumerate(rows):
        f.write(f'{i+1:3}. {symbol:15} | {name:25} | {t or "None"}\n')
    
    f.write(f'\nActive symbols: {cursor.execute("SELECT COUNT(*) FROM symbols WHERE is_active = 1").fetchone()[0]}\n')
    
    # Get data per symbol type
    cursor.execute('SELECT type, COUNT(*) as cnt FROM symbols WHERE is_active = 1 GROUP BY type')
    type_summary = cursor.fetchall()
    f.write('\nSymbols by type:\n')
    for t, cnt in type_summary:
        f.write(f'  {t}: {cnt}\n')
    
    # Check what indices/symbols are missing
    f.write(f'\nTotal price data rows: {cursor.execute("SELECT COUNT(*) FROM price_data").fetchone()[0]}\n')

print('Report written to symbols_report.txt')
conn.close()