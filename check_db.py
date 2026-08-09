import sqlite3
import json

conn = sqlite3.connect(r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis\data\market_data.db')
cursor = conn.cursor()

tables = ['symbols', 'price_data', 'indices', 'industry_indices', 'indices_data', 'data_metadata', 'export_history', 'analysis_records']

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"\n=== {table} schema ===")
    for col in columns:
        print(f"  {col[1]} {col[2]}")

print("\n=== Sample data counts ===")
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print("\n=== Sample symbols data ===")
cursor.execute("SELECT * FROM symbols LIMIT 5")
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
for i, row in enumerate(rows):
    print(f"Row {i}: " + ", ".join(f"{col}={val}" for col, val in zip(columns, row)))

print("\n=== Sample price_data ===")
cursor.execute("SELECT * FROM price_data LIMIT 3")
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
for i, row in enumerate(rows):
    print(f"Row {i}: " + ", ".join(f"{col}={val}" for col, val in zip(columns, row)))

print("\n=== Sample indices ===")
cursor.execute("SELECT * FROM indices LIMIT 3")
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
for i, row in enumerate(rows):
    print(f"Row {i}: " + ", ".join(f"{col}={val}" for col, val in zip(columns, row)))

conn.close()