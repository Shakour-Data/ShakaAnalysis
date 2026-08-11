import sqlite3

conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Add index symbol "شاخص کل"
cursor.execute("INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, sector, is_active) VALUES (?, ?, ?, ?, ?, 1)",
    ('\u0634\u0627\u062e\u0635 \u06a9\u0644', '\u0634\u0627\u062e\u0635 \u06a9\u0644', 'Index', 'TSE', None))

# Add stock symbol "فولاد"
cursor.execute("INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, sector, is_active) VALUES (?, ?, ?, ?, ?, 1)",
    ('\u0641\u0648\u0644\u0627\u062f', '\u0641\u0648\u0644\u0627\u062f', 'Stock', 'TSE', None))

conn.commit()

# Verify without printing Unicode
cursor.execute('SELECT symbol FROM symbols WHERE symbol IN ("\u0634\u0627\u062e\u0635 \u06a9\u0644", "\u0641\u0648\u0644\u0627\u062f")')
rows = cursor.fetchall()
print("Added symbols count:", len(rows))

conn.close()