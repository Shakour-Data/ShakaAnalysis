import numpy as np
import pandas as pd


class RiskMetrics:
    @staticmethod
    def sharpe_ratio(returns, risk_free_rate=0.03):
        if len(returns) == 0:
            return np.nan
        annualized_return = returns.mean() * 252
        annualized_std = returns.std() * np.sqrt(252)
        if annualized_std == 0:
            return np.nan
        return (annualized_return - risk_free_rate) / annualized_std

    @staticmethod
    def sortino_ratio(returns, risk_free_rate=0.03, target_return=0):
        if len(returns) == 0:
            return np.nan
        downside_returns = returns[returns < target_return]
        if len(downside_returns) == 0:
            return np.inf
        annualized_return = returns.mean() * 252
        annualized_downside_std = downside_returns.std() * np.sqrt(252)
        if annualized_downside_std == 0:
            return np.nan
        return (annualized_return - risk_free_rate) / annualized_downside_std

    @staticmethod
    def max_drawdown(returns):
        if len(returns) == 0:
            return np.nan
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    @staticmethod
    def calmar_ratio(returns):
        if len(returns) == 0:
            return np.nan
        annualized_return = returns.mean() * 252
        mdd = abs(RiskMetrics.max_drawdown(returns))
        if mdd == 0:
            return np.inf
        return annualized_return / mdd

    @staticmethod
    def var(returns, confidence=0.95):
        if len(returns) == 0:
            return np.nan
        return np.percentile(returns, (1 - confidence) * 100)

    @staticmethod
    def cvar(returns, confidence=0.95):
        if len(returns) == 0:
            return np.nan
        var = RiskMetrics.var(returns, confidence)
        return returns[returns <= var].mean()

    @staticmethod
    def beta(returns, market_returns):
        if len(returns) != len(market_returns) or len(returns) == 0:
            return np.nan
        cov_matrix = np.cov(returns, market_returns)
        return cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else np.nan

    @staticmethod
    def alpha(returns, market_returns, risk_free_rate=0.03):
        if len(returns) != len(market_returns) or len(returns) == 0:
            return np.nan
        beta = RiskMetrics.beta(returns, market_returns)
        if np.isnan(beta):
            return np.nan
        annualized_return = returns.mean() * 252
        annualized_market_return = market_returns.mean() * 252
        return annualized_return - risk_free_rate - beta * (annualized_market_return - risk_free_rate)

    @staticmethod
    def information_ratio(returns, benchmark_returns):
        if len(returns) != len(benchmark_returns) or len(returns) == 0:
            return np.nan
        excess_returns = returns - benchmark_returns
        tracking_error = excess_returns.std() * np.sqrt(252)
        if tracking_error == 0:
            return np.nan
        return (excess_returns.mean() * 252) / tracking_error

    @staticmethod
    def treynor_ratio(returns, market_returns, risk_free_rate=0.03):
        if len(returns) != len(market_returns) or len(returns) == 0:
            return np.nan
        beta = RiskMetrics.beta(returns, market_returns)
        if beta == 0 or np.isnan(beta):
            return np.nan
        annualized_return = returns.mean() * 252
        return (annualized_return - risk_free_rate) / beta

    @staticmethod
    def omega_ratio(returns, threshold=0):
        if len(returns) == 0:
            return np.nan
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        if losses == 0:
            return np.inf
        return gains / losses

    @staticmethod
    def calculate_all(returns, market_returns=None, risk_free_rate=0.03):
        results = {
            'sharpe': RiskMetrics.sharpe_ratio(returns, risk_free_rate),
            'sortino': RiskMetrics.sortino_ratio(returns, risk_free_rate),
            'max_drawdown': RiskMetrics.max_drawdown(returns),
            'calmar': RiskMetrics.calmar_ratio(returns),
            'var_95': RiskMetrics.var(returns, 0.95),
            'cvar_95': RiskMetrics.cvar(returns, 0.95),
            'omega': RiskMetrics.omega_ratio(returns),
        }
        if market_returns is not None:
            results.update({
                'beta': RiskMetrics.beta(returns, market_returns),
                'alpha': RiskMetrics.alpha(returns, market_returns, risk_free_rate),
                'information_ratio': RiskMetrics.information_ratio(returns, market_returns),
                'treynor': RiskMetrics.treynor_ratio(returns, market_returns, risk_free_rate),
            })
        return results


def calculate_risk_metrics_for_symbol(symbol, price_data, market_data=None):
    returns = price_data['close'].pct_change().dropna()
    if market_data is not None:
        market_returns = market_data['close'].pct_change().dropna()
        common_dates = returns.index.intersection(market_returns.index)
        returns = returns.loc[common_dates]
        market_returns = market_returns.loc[common_dates]
        return RiskMetrics.calculate_all(returns, market_returns)
    return RiskMetrics.calculate_all(returns)