# Trend-following strategy backtest
# Strategy: hold stocks trading above their 50-day moving average,
# skip high-volatility periods, equal weight across active positions.
#
# (This is the client's original script, kept unchanged as received.)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Load price data
df = pd.read_csv("data/prices_raw.csv", parse_dates=["date"])
prices = df.pivot(index="date", columns="symbol", values="close")

# Calculate daily returns
returns = prices.pct_change()

# Trend filter: price above 50-day moving average
sma = prices.rolling(50).mean()
signal = (prices > sma).astype(int)

# Volatility filter: avoid the most volatile 20% of days
volatility = returns.rolling(20).std()
vol_threshold = volatility.quantile(0.8)
signal = signal * (volatility < vol_threshold)

# Equal weight across active signals
weights = signal.div(signal.sum(axis=1), axis=0).fillna(0)

# Strategy returns
strategy_returns = (weights * returns).sum(axis=1)

# Performance metrics
cumulative_returns = strategy_returns.cumsum()
total_return = cumulative_returns.iloc[-1]
years = len(strategy_returns) / 252
annual_return = total_return / years
sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(365)
max_drawdown = (cumulative_returns - cumulative_returns.cummax()).min()

print(f"Total Return: {total_return:.2%}")
print(f"Annual Return: {annual_return:.2%}")
print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
print(f"Max Drawdown: {max_drawdown:.2%}")

# Plot equity curve
cumulative_returns.plot(title="Strategy Cumulative Returns", figsize=(12, 6))
plt.savefig("original_equity.png")
