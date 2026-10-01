"""One-off script that builds the case-study data set from Yahoo Finance.

Yahoo only serves split-adjusted prices, so this script rebuilds the *raw* prices
that a broker export (like the client's) would contain:
    data/prices_raw.csv          date, symbol, close     (unadjusted, as traded)
    data/corporate_actions.csv   date, symbol, type, value (splits; dividends as paid)
    data/yahoo_adj_close.csv     Yahoo's adjusted close, only used to validate adjust.py
"""
from pathlib import Path

import pandas as pd
import yfinance as yf

SYMBOLS = ["AAPL", "AMZN", "GOOGL", "NVDA", "TSLA"]
START, END = "2019-01-01", "2026-10-01"
DATA = Path(__file__).parent / "data"


def main():
    raw = yf.download(SYMBOLS, start=START, end=END, auto_adjust=False, actions=True, progress=False)
    splits = raw["Stock Splits"].fillna(0).replace(0, 1.0)
    # factor[t] = product of all split ratios strictly after t: turns split-adjusted values back into raw ones
    later_splits = splits[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)

    close = (raw["Close"] * later_splits).round(4)
    dividends = raw["Dividends"].fillna(0) * later_splits

    prices = close.stack().rename("close").reset_index()
    prices.columns = ["date", "symbol", "close"]

    actions = []
    for kind, frame, keep in (("split", raw["Stock Splits"], lambda v: v not in (0, 1)), ("dividend", dividends, lambda v: v > 0)):
        for (date, symbol), value in frame.stack().items():
            if keep(value):
                actions.append({"date": date, "symbol": symbol, "type": kind, "value": round(value, 6)})
    actions = pd.DataFrame(actions).sort_values(["date", "symbol"])

    adj = raw["Adj Close"].stack().rename("adj_close").reset_index()
    adj.columns = ["date", "symbol", "adj_close"]

    DATA.mkdir(exist_ok=True)
    prices.to_csv(DATA / "prices_raw.csv", index=False, date_format="%Y-%m-%d")
    actions.to_csv(DATA / "corporate_actions.csv", index=False, date_format="%Y-%m-%d")
    adj.to_csv(DATA / "yahoo_adj_close.csv", index=False, date_format="%Y-%m-%d", float_format="%.6f")
    print(f"{len(prices)} price rows, {len(actions)} corporate actions")


if __name__ == "__main__":
    main()
