import ssl
import urllib3
import sys
import os

# Apply SSL bypass to urllib3.PoolManager
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
_orig_init = urllib3.PoolManager.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    _orig_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_init
urllib3.disable_warnings()

sys.path.insert(0, '.')

# Import necessary modules
from src.database import get_db_connection, initialize_database
import finpy_tse

# Initialize database
print('Initializing database...')
initialize_database()

# Get symbols
print('Fetching symbol list from TSE...')
df = finpy_tse.Build_Market_StockList(
    bourse=True,
    farabourse=True,
    payeh=True,
    detailed_list=True,
    show_progress=False,
    save_excel=False,
    save_csv=False
)
print(f'Found {len(df)} symbols')

# Prepare data for insertion
symbols_to_insert = []
for _, row in df.iterrows():
    ticker = str(row.get('Ticker', '')).strip()
    name = str(row.get('Name', '')).strip()
    market = str(row.get('Market', '')).strip()
    webid = str(row.get('WEB-ID', '')).strip()
    
    if not ticker:
        continue
        
    # Determine exchange and type
    if market == 'بورس':
        exchange = 'TSE'
        symbol_type = 'Stock'
    elif market == 'فرابورس':
        exchange = 'OTC'
        symbol_type = 'Stock'
    elif 'صاخع' in name.lower() or 'index' in name.lower() or 'شاخص' in ticker:
        exchange = 'TSE'
        symbol_type = 'Index'
    else:
        exchange = 'TSE'
        symbol_type = 'Unknown'
        
    symbols_to_insert.append((
        ticker, name, symbol_type, exchange,
        'Unknown', market, webid, 'IR', 'IRR', 1
    ))

# Insert into database
conn = get_db_connection()
cursor = conn.cursor()

# Clear existing symbols
cursor.execute('DELETE FROM symbols')

# Insert symbols
cursor.executemany('''
    INSERT INTO symbols (symbol, name, type, exchange, industry, sector, webid, country, currency, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', symbols_to_insert)

conn.commit()
print(f'Inserted {len(symbols_to_insert)} symbols into database')

# Verify
cursor.execute('SELECT COUNT(*) FROM symbols')
count = cursor.fetchone()[0]
print(f'Total symbols in database: {count}')

cursor.execute('SELECT symbol, name, type, exchange FROM symbols LIMIT 5')
rows = cursor.fetchall()
print('Sample symbols:')
for r in rows:
    print(f'  {r[0]} - {r[1]} ({r[2]}, {r[3]})')

conn.close()
print('Done!')