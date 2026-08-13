#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import sys
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM symbols LIMIT 5")
print('SAMPLE SYMBOLS:')
for row in cursor.fetchall():
    print(f'  ID: {row[0]}, Symbol: {row[1]}, Name: {row[2]}, Type: {row[3]}')

cursor.execute("SELECT symbol, type FROM symbols WHERE type='Index' LIMIT 10")
print('\nINDEXES FOUND:')
for row in cursor.fetchall():
    print(f'  {row[0]} - {row[1]}')

cursor.execute("SELECT COUNT(*) FROM symbols")
total = cursor.fetchone()[0]
print(f'\nTOTAL SYMBOLS: {total}')

cursor.execute("SELECT COUNT(*) FROM price_data")
prices = cursor.fetchone()[0]
print(f'TOTAL PRICE ROWS: {prices}')

cursor.execute("SELECT MIN(Date), MAX(Date) FROM price_data")
date_range = cursor.fetchone()
print(f'DATE RANGE: {date_range[0]} to {date_range[1]}')

conn.close()