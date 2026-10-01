"""Backward price adjustment for splits and cash dividends (the method Yahoo and CRSP use).

The latest price stays as traded; earlier prices are scaled so that a split or an
ex-dividend drop no longer shows up as a loss in the return series.
"""
import pandas as pd


def back_adjust(raw_close: pd.DataFrame, actions: pd.DataFrame) -> pd.DataFrame:
    """raw_close: wide frame (date x symbol) of unadjusted closes.
    actions: rows of (date, symbol, type, value); a split's value is the ratio (4.0 for 4-for-1),
    a dividend's value is the cash amount actually paid per share."""
    factor = pd.DataFrame(1.0, index=raw_close.index, columns=raw_close.columns)
    for a in actions.itertuples(index=False):
        if a.symbol not in raw_close.columns:
            continue
        before = raw_close.index < pd.Timestamp(a.date)
        if a.type == "split":
            factor.loc[before, a.symbol] /= a.value
        elif a.type == "dividend":
            prev_close = raw_close.loc[before, a.symbol].dropna().iloc[-1]  # last close before ex-date
            factor.loc[before, a.symbol] *= 1 - a.value / prev_close
        else:
            raise ValueError(f"unknown corporate action type: {a.type}")
    return raw_close * factor
