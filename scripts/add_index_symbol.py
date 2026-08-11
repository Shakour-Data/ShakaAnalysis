import sqlite3

# Connect to database
conn = sqlite3.connect('data/market_data.db')
cursor = conn.cursor()

# Add index symbol
cursor.execute("INSERT OR IGNORE INTO symbols (symbol, name, type, exchange, sector, is_active) VALUES (?, ?, ?, ?, ?, 1)",
               ('شاخص کل', 'شاخص کل', 'Index', 'TSE', None))

# Commit changes
conn.commit()

# Verify the addition using ASCII-safe output
cursor.execute("SELECT symbol FROM symbols WHERE symbol = ?", ('شاخص کل',))
row = cursor.fetchone()
if row:
    print('Index symbol added successfully (symbol length:', len(row[0]), ')')
else:
    print('Failed to add index symbol')

# Also verify FARAZ symbol
cursor.execute("SELECT symbol FROM symbols WHERE symbol = ?", ('FARAZ',))
row = cursor.fetchone()
if row:
    print('FARAZ symbol verified (symbol length:', len(row[0]), ')')
else:
    print('FARAZ symbol not found')

conn.close()