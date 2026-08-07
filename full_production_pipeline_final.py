#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shaka Analysis - FULL PRODUCTION PIPELINE
Processes ALL 1,289 symbols (TSE, OTC, Indices) with daily update capability
Jalali dates kept as strings
"""

import sys
import os
import sqlite3
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

DATA_DIR = 'data/market_data.db'
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("="*70)
print("SHAKA ANALYSIS - FULL PRODUCTION PIPELINE")
print("="*70)

conn = sqlite3.connect(DATA_DIR)
conn.row_factory = sqlite3.Row

symbols_df = pd.read_sql("SELECT * FROM symbols ORDER BY id", conn)
print("Total symbols in database:", len(symbols_df))

print("\nLoading ALL price data...")
df_data = pd.read_sql("""
    SELECT s.symbol, s.name, s.type, s.exchange, 
           p.date, p.open, p.high, p.low, p.close, 
           p.volume, p.value, p.sma_20, p.sma_50, 
           p.rsi, p.macd, p.macd_signal, 
           p.bb_upper, p.bb_lower, p.adx, p.cci, p.mfi
    FROM price_data p 
    JOIN symbols s ON p.symbol_id = s.id 
    ORDER BY p.date
""", conn)

conn.close()

# Keep date as string (Jalali dates are not Gregorian)
df_data['return'] = df_data.groupby('symbol')['close'].pct_change()

print("Loaded", len(df_data), "price rows for", df_data['symbol'].nunique(), "symbols")

print("\nRunning BACKTESTING on ALL symbols...")

def run_backtest(symbol, symbol_df):
    if len(symbol_df) < 50:
        return {'symbol': symbol, 'status': 'insufficient_data'}
    
    price_df = symbol_df[['open', 'high', 'low', 'close', 'volume']].copy()
    price_df['sma_20'] = price_df['close'].rolling(20).mean()
    price_df['sma_50'] = price_df['close'].rolling(50).mean()
    
    price_df['ma_buy'] = (price_df['close'] > price_df['sma_50']) & (price_df['close'].shift(1) <= price_df['sma_50'].shift(1))
    price_df['ma_sell'] = (price_df['close'] < price_df['sma_50']) & (price_df['close'].shift(1) >= price_df['sma_50'].shift(1))
    
    capital = 10000
    shares = 0
    entry_price = 0
    portfolio = [capital]
    
    for i in range(1, len(price_df)):
        if price_df['ma_buy'].iloc[i] and shares == 0:
            if price_df['open'].iloc[i] > 0:
                shares = int(capital / price_df['open'].iloc[i])
                entry_price = price_df['open'].iloc[i]
        elif price_df['ma_sell'].iloc[i] and shares > 0:
            pnl = (price_df['close'].iloc[i] - entry_price) / entry_price
            portfolio.append(portfolio[-1] * (1 + pnl))
            shares = 0
            entry_price = 0
        portfolio.append(portfolio[-1])
    
    final_value = portfolio[-1]
    total_return = (final_value / capital) - 1
    
    return {
        'symbol': symbol,
        'final_value': final_value,
        'total_return': total_return,
        'num_trades': len([t for t in portfolio if t != capital])
    }

results = []
symbol_list = df_data['symbol'].unique()
total_symbols = len(symbol_list)
for i, symbol in enumerate(symbol_list):
    symbol_data = df_data[df_data['symbol'] == symbol]
    if len(symbol_data) > 20:
        result = run_backtest(symbol, symbol_data)
        results.append(result)
    if (i + 1) % 150 == 0:
        print(f"  Processed {i+1}/{total_symbols} symbols...")

results_df = pd.DataFrame(results)
results_df.to_csv(f'{OUTPUT_DIR}/all_symbols_backtest.csv', index=False)
print("Backtesting complete. Processed", len(results_df), "symbols")

print("\nRunning TECHNICAL SCREENER on ALL symbols...")
latest = df_data.groupby('symbol').tail(1).reset_index()
screener_results = []

for _, row in latest.iterrows():
    symbol = row['symbol']
    sym_data = df_data[df_data['symbol'] == symbol]
    
    signals = []
    if row['rsi'] < 30: signals.append('RSI_OVERSOLD')
    if row['rsi'] > 70: signals.append('RSI_OVERBOUGHT')
    
    # Get previous values for comparison
    prev_row = sym_data.iloc[-2] if len(sym_data) > 1 else row
    
    if row['close'] > row['sma_50'] and prev_row['close'] <= prev_row['sma_50']:
        signals.append('SMA50_BREAKOUT')
    if row['close'] < row['sma_50'] and prev_row['close'] >= prev_row['sma_50']:
        signals.append('SMA50_BREAKDOWN')
    
    if len(sym_data) > 20:
        vol_avg = sym_data['volume'].rolling(20).mean().iloc[-1]
        if row['volume'] > vol_avg * 2: signals.append('VOLUME_SPIKE')
    
    if row['adx'] is not None and row['adx'] > 25:
        signals.append('STRONG_TREND')
    
    if signals:
        screener_results.append({
            'symbol': symbol,
            'name': row['name'],
            'price': row['close'],
            'rsi': row['rsi'],
            'sma_20': row['sma_20'],
            'sma_50': row['sma_50'],
            'vol': row['volume'],
            'adx': row['adx'],
            'signals': ', '.join(signals),
            'signal_count': len(signals)
        })

screener_df = pd.DataFrame(screener_results)
screener_df.to_csv(f'{OUTPUT_DIR}/all_screener_signals.csv', index=False)
print("Screener complete. Symbols with signals:", len(screener_df))

print("\nCalculating RISK METRICS for ALL symbols...")
risk_results = []
for symbol in df_data['symbol'].unique():
    symbol_returns = df_data[df_data['symbol'] == symbol]['return'].dropna()
    if len(symbol_returns) < 20:
        continue
    
    vol = symbol_returns.std()
    mean_return = symbol_returns.mean()
    var_95 = np.percentile(symbol_returns, 5)
    var_99 = np.percentile(symbol_returns, 1)
    
    cum_returns = (1 + symbol_returns).cumprod()
    running_max = cum_returns.expanding().max()
    drawdown = (cum_returns - running_max) / running_max
    max_dd = drawdown.min()
    
    sharpe = (mean_return / vol) * np.sqrt(252)
    downside = symbol_returns[symbol_returns < 0].std()
    sortino = (mean_return / downside) * np.sqrt(252) if downside > 0 else 0
    
    risk_results.append({
        'symbol': symbol,
        'volatility': vol,
        'VaR_95': var_95,
        'VaR_99': var_99,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'annual_return': mean_return * 252
    })

risk_df = pd.DataFrame(risk_results)
risk_df = risk_df.sort_values('sharpe_ratio', ascending=False)
risk_df.to_csv(f'{OUTPUT_DIR}/all_risk_metrics.csv', index=False)
print("Risk metrics calculated for", len(risk_df), "symbols")

print("\nRunning CORRELATION ANALYSIS...")
volume_rank = df_data.groupby('symbol')['volume'].sum().sort_values(ascending=False)
top_50_symbols = volume_rank.head(50).index

pivot = df_data[df_data['symbol'].isin(top_50_symbols)].pivot_table(
    index='date', columns='symbol', values='close'
).dropna(axis=1, thresh=30)

corr_matrix = pivot.corr()
corr_matrix.to_csv(f'{OUTPUT_DIR}/correlation_matrix_full.csv')

high_corr_pairs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i+1, len(corr_matrix.columns)):
        corr_val = corr_matrix.iloc[i, j]
        if corr_val > 0.7:
            high_corr_pairs.append({
                'symbol1': corr_matrix.columns[i],
                'symbol2': corr_matrix.columns[j],
                'correlation': corr_val
            })

pd.DataFrame(high_corr_pairs).to_csv(f'{OUTPUT_DIR}/high_correlation_pairs.csv', index=False)
print("Correlation analysis complete. High-correlation pairs:", len(high_corr_pairs))

print("\nBuilding ML Feature Matrix...")
feature_cols = ['close', 'volume', 'sma_20', 'sma_50', 'rsi', 'macd', 'macd_signal', 
                'bb_upper', 'bb_lower', 'adx', 'cci', 'mfi', 'return']

ml_data = []
for symbol in df_data['symbol'].unique():
    sym_data = df_data[df_data['symbol'] == symbol].copy()
    if len(sym_data) < 60:
        continue
    
    for col in feature_cols:
        sym_data[f'{col}_lag1'] = sym_data[col].shift(1)
    
    sym_data['target_next_return'] = sym_data['return'].shift(-1)
    sym_data['target_direction'] = (sym_data['target_next_return'] > 0).astype(int)
    sym_data['symbol'] = symbol
    sym_data['name'] = sym_data['name'].iloc[0]
    
    ml_data.append(sym_data)

ml_df = pd.concat(ml_data, ignore_index=True)
ml_df.dropna(subset=['target_next_return'], inplace=True)
ml_df.to_csv(f'{OUTPUT_DIR}/all_ml_features.csv', index=False)
print("ML feature matrix:", len(ml_df), "rows,", ml_df.shape[1], "features")

print("\nCreating Daily Update System...")

daily_update_script = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, sqlite3, pandas as pd
import ssl, urllib3, requests
from datetime import datetime
from finpy_tse import Get_Price_History

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
urllib3.PoolManager.__init__ = lambda self, *a, **k: (setattr(self, 'ssl_context', ctx) or urllib3.PoolManager.__init__(self, *a, **k))
requests.get = lambda url, *a, **k: requests.get(url, verify=False, timeout=180, *a, **k)

def update_data():
    conn = sqlite3.connect("data/market_data.db")
    c = conn.cursor()
    c.execute("SELECT id, symbol FROM symbols WHERE is_active = 1")
    symbols = c.fetchall()
    
    for sym_id, symbol in symbols:
        c.execute("SELECT MAX(date) FROM price_data WHERE symbol_id = ?", (sym_id,))
        last_date = c.fetchone()[0]
        if not last_date:
            continue
        try:
            df = Get_Price_History(stock=symbol, start_date=last_date, end_date=datetime.now().strftime("%Y-%m-%d"))
            if df is not None and not df.empty:
                for jdate in df.index:
                    row = df.loc[jdate]
                    c.execute("INSERT OR REPLACE INTO price_data (symbol_id, date, open, high, low, close, final_price, volume, value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (sym_id, str(jdate), row.get('Open',0), row.get('High',0), row.get('Low',0), row.get('Close',0), row.get('Final',0), row.get('Volume',0), row.get('Value',0)))
                conn.commit()
                print("Updated", symbol, ":", len(df), "rows")
        except Exception as e:
            print("Error updating", symbol, ":", e)
    conn.close()
    print("Daily update complete.")

if __name__ == "__main__":
    update_data()
'''

with open(f'{OUTPUT_DIR}/daily_update.py', 'w') as f:
    f.write(daily_update_script)

scheduler_config = '''# SHAKA ANALYSIS - DAILY UPDATE SCHEDULER
# Windows Task Scheduler:
#   schtasks /create /tn "ShakaDailyUpdate" /tr "python E:\\Shakour\\MyAnalysis\\Chapar\\ShakaAnalysis\\outputs\\daily_update.py" /sc daily /st 16:00
# Linux/Mac (cron):
#   0 16 * * 1-5 /usr/bin/python3 /path/to/daily_update.py
'''

with open(f'{OUTPUT_DIR}/scheduler_config.txt', 'w') as f:
    f.write(scheduler_config)

print("\nGenerating Final Report...")
report = f"""
SHAKA ANALYSIS - FULL PRODUCTION PIPELINE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DATABASE STATUS:
   Total Symbols: {len(symbols_df)}
   Stocks (TSE/OTC): {len(symbols_df[symbols_df['type']=='Stock'])}
   Total Price Records: {len(df_data):,}
   Date Range: {df_data['date'].min()} to {df_data['date'].max()}

BACKTESTING RESULTS:
   Symbols Tested: {len(results_df)}
   Avg Total Return: {results_df['total_return'].mean()*100:.2f}%
   Best Return: {results_df['total_return'].max()*100:.2f}%

SCREENER:
   Signals Found: {len(screener_df)} symbols

RISK METRICS:
   Symbols Analyzed: {len(risk_df)}
   Best Sharpe: {risk_df['sharpe_ratio'].max():.2f}
   Worst Drawdown: {risk_df['max_drawdown'].min()*100:.2f}%

CORRELATION:
   High-Corr Pairs: {len(high_corr_pairs)}
"""

with open(f'{OUTPUT_DIR}/complete_analysis_report.txt', 'w') as f:
    f.write(report)

print("\n" + "="*70)
print("FULL PRODUCTION PIPELINE COMPLETE!")
print("="*70)
print(f"""
OUTPUT FILES IN {OUTPUT_DIR}/:
   1. all_symbols_backtest.csv - {len(results_df)} symbols tested
   2. all_screener_signals.csv - {len(screener_df)} signals
   3. all_risk_metrics.csv - {len(risk_df)} symbols analyzed
   4. correlation_matrix_full.csv - Full matrix
   5. high_correlation_pairs.csv - {len(high_corr_pairs)} pairs
   6. all_ml_features.csv - {len(ml_df)} rows
   7. daily_update.py - Daily updater
   8. scheduler_config.txt - Scheduler
   9. complete_analysis_report.txt - Summary

DATABASE: data/market_data.db ({len(symbols_df)} symbols, {len(df_data):,} price rows)

READY FOR DEPLOYMENT!
""")