#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/market_data.db')
c = conn.cursor()
c.execute('SELECT symbol, name, type FROM symbols ORDER BY type, symbol')
rows = c.fetchall()
print(f'Total: {len(rows)}')
for r in rows:
    print(f'- {r[0]} | {r[1]} | {r[2]}')
conn.close()