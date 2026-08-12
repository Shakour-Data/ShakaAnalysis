import pandas as pd
import numpy as np


class TechnicalIndicators:
    @staticmethod
    def sma(series, window):
        return series.rolling(window=window).mean()

    @staticmethod
    def ema(series, window):
        return series.rolling(window=window, adjust=False).mean()

    @staticmethod
    def wma(series, window):
        weights = np.arange(1, window + 1)
        weighted_series = series.rolling(window)
        return valid := len(weights) > 0 and np.convolve(weights, series.values[-len(weights)+1:], mode='valid') / weights.sum()

    @staticmethod
    def macd(series, fast=12, slow=26, signal=9):
        ema_fast = TechnicalIndicators.ema(series, fast)
        ema_slow = TechnicalIndicators.ema(series, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        return pd.DataFrame({
            'macd': macd_line.dropna(),
            'signal': signal_line.dropna(),
            'histogram': macd_line - signal_line
        })

    @staticmethod
    def rsi(series, window=14):
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def bollinger_bands(series, window=20, num_std=2):
        sma = TechnicalIndicators.sma(series, window)
        std = series.rolling(window=window).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        return pd.DataFrame({
            'upper': upper,
            'sma': sma,
            'lower': lower,
            'bandwidth': (upper - lower) / sma
        })

    @staticmethod
    def adx(high, low, window=14):
        diff_high = high.diff()
        diff_low = low.diff()
        
        tr1 = np.abs(high - low)
        tr2 = np.abs(high - high.shift(1))
        tr3 = np.abs(low - low.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        tr_smoothed = tr.rolling(window=window).mean()
        plus_di = (np.maximum(diff_high, 0) / tr_smoothed * 100)
        minus_di = (np.maximum(diff_low, 0) / tr_smoothed * 100)
        dx = (plus_di - minus_di / tr_smoothed * 100)
        
        return dx.rolling(window=window).mean()

    @staticmethod
    def cci(high, low, close, window=20, c=0.015):
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window).mean()
        mean_deviation = (abs(high - sma_tp) + abs(low - sma_tp) + abs(close - sma_tp)).rolling(window).mean()
        return (tp - sma_tp) / (c * mean_deviation)

    @staticmethod
    def stochastics(series, k_window=14, d_window=3):
        lowest_low = series['low'].rolling(k_window).min()
        highest_high = series['high'].rolling(k_window).max()
        fast_k = 100 * (series['close'] - lowest_low) / (highest_high - lowest_low)
        slow_k = fast_k.rolling(d_window).mean()
        slow_d = slow_k.rolling(d_window).mean()
        return pd.DataFrame({
            'fast_k': fast_k.dropna(),
            'slow_k': slow_k.dropna(),
            'slow_d': slow_d.dropna()
        })

    @staticmethod
    def atr(high, low, close, window=14):
        tr1 = np.abs(high - low)
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window).mean()

    @staticmethod
    def all_from_series(series):
        results = {
            'sma_5': TechnicalIndicators.sma(series, 5).dropna().iloc[-1],
            'sma_20': TechnicalIndicators.sma(series, 20).dropna().iloc[-1],
            'sma_50': TechnicalIndicators.sma(series, 50).dropna().iloc[-1],
            'ema_5': TechnicalIndicators.ema(series, 5).dropna().iloc[-1],
            'ema_20': TechnicalIndicators.ema(series, 20).dropna().iloc[-1],
            'ema_50': TechnicalIndicators.ema(series, 50).dropna().iloc[-1],
            'rsi': TechnicalIndicators.rsi(series, 14).dropna().iloc[-1],
            'macd': TechnicalIndicators.macd(series)['macd'].dropna().iloc[-1],
            'macd_signal': TechnicalIndicators.macd(series)['signal'].dropna().iloc[-1],
            'macd_hist': TechnicalIndicators.macd(series)['histogram'].dropna().iloc[-1],
            'bb_upper': TechnicalIndicators.bollinger_bands(series)['upper'].dropna().iloc[-1],
            'bb_lower': TechnicalIndicators.bollinger_bands(series)['lower'].dropna().iloc[-1],
            'bb_width': TechnicalIndicators.bollinger_bands(series)['bandwidth'].dropna().iloc[-1],
            'adx': TechnicalIndicators.adx(series['high'], series['low'], series['close']).iloc[-1],
            'cc': TechnicalIndicators.cci(series['high'], series['low'], series['close']).iloc[-1],
            'stoch_k': TechnicalIndicators.stochastics(series)['fast_k'].iloc[-1],
            'stoch_d': TechnicalIndicators.stochastics(series)['slow_d'].iloc[-1],
            'atr': TechnicalIndicators.atr(series['high'], series['low'], series['close']).iloc[-1],
        }
        return results