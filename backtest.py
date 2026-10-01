"""The client's strategy, corrected. Each fix can be switched off to measure its impact.

Strategy (unchanged from the original): hold stocks whose close is above their 50-day SMA,
skip a stock while its 20-day volatility is in its top 20%, equal-weight the active stocks.
"""
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from adjust import back_adjust

DATA = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Settings:
    adjusted_prices: bool = True     # bug 1: raw prices turn splits and dividends into fake crashes
    point_in_time_vol: bool = True   # bug 2: volatility cut-off was computed from the whole sample
    trade_next_bar: bool = True      # bug 3: positions earned the return of the bar that created them
    honest_metrics: bool = True      # bug 4: summed returns and sqrt(365) annualisation
    cost_bps: float = 10.0           # trading cost per unit of turnover (the original assumed zero)


ORIGINAL = Settings(adjusted_prices=False, point_in_time_vol=False, trade_next_bar=False,
                    honest_metrics=False, cost_bps=0.0)
FIXED = Settings()


def load_prices(adjusted: bool) -> pd.DataFrame:
    df = pd.read_csv(DATA / "prices_raw.csv", parse_dates=["date"])
    prices = df.pivot(index="date", columns="symbol", values="close")
    if adjusted:
        actions = pd.read_csv(DATA / "corporate_actions.csv", parse_dates=["date"])
        prices = back_adjust(prices, actions)
    return prices


def strategy_returns(prices: pd.DataFrame, s: Settings) -> pd.Series:
    returns = prices.pct_change()
    signal = (prices > prices.rolling(50).mean()).astype(int)

    volatility = returns.rolling(20).std()
    if s.point_in_time_vol:
        # only the volatility history known on each day; needs ~6 months before it starts trading
        threshold = volatility.expanding(min_periods=120).quantile(0.8)
    else:
        threshold = volatility.quantile(0.8)  # one number per stock, using future data
    signal = signal * (volatility < threshold)

    weights = signal.div(signal.sum(axis=1), axis=0).fillna(0)
    if s.trade_next_bar:
        weights = weights.shift(1).fillna(0)  # decided at today's close, held from tomorrow

    gross = (weights * returns).sum(axis=1)
    turnover = weights.diff().abs().sum(axis=1)
    return gross - turnover * s.cost_bps / 10_000


def performance(ret: pd.Series, honest: bool = True) -> dict:
    years = len(ret) / 252
    if honest:
        equity = (1 + ret).cumprod()
        total = equity.iloc[-1] - 1
        annual = (1 + total) ** (1 / years) - 1
        sharpe = ret.mean() / ret.std() * math.sqrt(252)  # 252 trading days, not 365 calendar days
        max_dd = (equity / equity.cummax() - 1).min()
    else:  # exactly what the original script computed
        equity = ret.cumsum()
        total = equity.iloc[-1]
        annual = total / years
        sharpe = ret.mean() / ret.std() * math.sqrt(365)
        max_dd = (equity - equity.cummax()).min()
    return {"Total return": total, "Annual return": annual, "Sharpe": sharpe, "Max drawdown": max_dd}


def run(s: Settings) -> tuple[pd.Series, dict]:
    ret = strategy_returns(load_prices(s.adjusted_prices), s)
    return ret, performance(ret, s.honest_metrics)


if __name__ == "__main__":
    _, stats = run(FIXED)
    for k, v in stats.items():
        print(f"{k}: {v:.2f}" if k == "Sharpe" else f"{k}: {v:.2%}")
