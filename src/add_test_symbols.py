#!/usr/bin/env python
# -*- coding: utf-8 -*-

symbols_data = {
    'آ toi': {
        'Open': 10000, 'High': 10200, 'Low': 9800, 'Close': 10100,
        'Volume': 1000000, 'RSI': 50, 'MACD': 2.5, 'BB_Upper': 10300,
        'BB_Lower': 9900
    },
    'فولاد': {
        'Open': 18000, 'High': 18500, 'Low': 17500, 'Close': 18300,
        'Volume': 1500000, 'RSI': 60, 'MACD': 4.2, 'BB_Upper': 18600,
        'BB_Lower': 18200
    }
}

import json
import os
from datetime import datetime

PROJECT_DIR = r'E:\Shakour\MyAnalysis\Chapar\ShakaAnalysis'
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

for symbol, data in symbols_data.items():
    file_path = os.path.join(DATA_DIR, f'{symbol}_data.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print('Test symbols created')