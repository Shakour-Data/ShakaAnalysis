import sqlite3
conn = sqlite3.connect('data/market_data.db')
c = conn.cursor()

print('=== DATABASE CONTENT ===')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', tables)
c.execute('SELECT COUNT(*) FROM symbols')
print('Symbols count:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM price_data')
print('Price data rows:', c.fetchone()[0])

# Sample stocks
c.execute("SELECT symbol, name FROM symbols WHERE type='Stock' ORDER BY symbol LIMIT 15")
print('\nSample stocks:')
for r in c.fetchall():
    print('  {0} - {1}'.format(r[0], r[1]))

# Sample indices
c.execute("SELECT symbol, name FROM symbols WHERE type='Index'")
print('\nIndices:')
for r in c.fetchall():
    print('  {0} - {1}'.format(r[0], r[1]))

conn.close()