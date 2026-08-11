import sqlite3

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Add missing market indices
indices_to_add = [
    ('\u0634\u0627\u062e\u0635 \u06a9\u0644 \u0633\u0647\u0645', 'Total Stock Index', 'Index', 'TSE'),
    ('\u0634\u0627\u062e\u0635 \u0628\u0631\u0627\u0628\u0631 \u0648\u0632\u0646', 'Total Equal Weight Index', 'Index', 'TSE'),
    ('\u0634\u0627\u062e\u0635 \u0635\u0646\u0639\u062a', 'Industry Indices', 'Index', 'TSE'),
]

# Check if they exist
for symbol, name, type_, exchange in indices_to_add:
    cursor.execute('SELECT 1 FROM symbols WHERE symbol = ?', (symbol,))
    if cursor.fetchone() is None:
        cursor.execute('''INSERT INTO symbols (symbol, name, type, exchange, sector, is_active) 
                        VALUES (?, ?, ?, ?, ?, 1)''', (symbol, name, type_, exchange, None))
        
conn.commit()

# Verify
cursor.execute('SELECT symbol, name, type FROM symbols WHERE is_active = 1 ORDER BY type')
rows = cursor.fetchall()

with open('symbols_after_add.txt', 'w', encoding='utf-8') as f:
    f.write(f'Total symbols after adding indices: {len(rows)}\n')
    for r in rows:
        f.write(f'  {r[0]:20} | {r[1]:30} | {r[2]}\n')

print(f'Done. Total symbols: {len(rows)}. Written to symbols_after_add.txt')
conn.close()