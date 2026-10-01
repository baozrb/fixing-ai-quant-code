"""Regression tests for every bug found in the original script."""
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adjust import back_adjust
from backtest import FIXED, ORIGINAL, load_prices, performance, run, strategy_returns


def test_original_settings_reproduce_the_original_script_exactly():
    """Proves the bug list is complete: switching every fix off gives the client's numbers."""
    out = subprocess.run([sys.executable, "original/backtest_from_chatgpt.py"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    printed = {k: float(v) for k, v in re.findall(r"(\w[\w ]+): (-?[\d.]+)", out)}
    _, ours = run(ORIGINAL)
    assert printed["Total Return"] == pytest.approx(ours["Total return"] * 100, abs=0.01)
    assert printed["Sharpe Ratio"] == pytest.approx(ours["Sharpe"], abs=0.01)
    assert printed["Max Drawdown"] == pytest.approx(ours["Max drawdown"] * 100, abs=0.01)
    (ROOT / "original_equity.png").unlink(missing_ok=True)


def test_back_adjust_matches_yahoo_adjusted_close():
    ours = load_prices(adjusted=True)
    yahoo = pd.read_csv(ROOT / "data/yahoo_adj_close.csv", parse_dates=["date"]).pivot(
        index="date", columns="symbol", values="adj_close")
    assert ((ours / yahoo - 1).abs().max() < 1e-5).all()


def test_back_adjust_removes_split_and_dividend_gaps():
    idx = pd.bdate_range("2024-01-01", periods=4)
    raw = pd.DataFrame({"X": [100.0, 102.0, 25.5, 24.5]}, index=idx)  # 4:1 split, then $1 dividend
    actions = pd.DataFrame({"date": [idx[2], idx[3]], "symbol": "X", "type": ["split", "dividend"], "value": [4.0, 1.0]})
    adj = back_adjust(raw, actions)
    assert adj["X"].iloc[-1] == 24.5  # latest price untouched
    assert adj["X"].pct_change().iloc[2] == pytest.approx(0.0)  # split no longer looks like -75%
    assert adj["X"].pct_change().iloc[3] == pytest.approx(0.0)  # the $1 ex-dividend drop is not a loss


@pytest.mark.parametrize("settings, leaks", [(FIXED, False), (ORIGINAL, True)])
def test_lookahead(settings, leaks):
    """Changing prices after a cut-off date must not change any return before it."""
    prices = load_prices(adjusted=True)
    cut = prices.index[1000]
    shocked = prices.copy()
    shocked.loc[shocked.index > cut] *= np.linspace(1, 3, (shocked.index > cut).sum())[:, None]
    before = strategy_returns(prices, settings)[:cut]
    after = strategy_returns(shocked, settings)[:cut]
    assert (not np.allclose(before, after)) == leaks


def test_split_days_are_not_losses_after_adjustment():
    raw_ret = strategy_returns(load_prices(adjusted=False), replace(FIXED, adjusted_prices=False, cost_bps=0))
    adj_ret = strategy_returns(load_prices(adjusted=True), replace(FIXED, cost_bps=0))
    split_days = pd.to_datetime(["2020-08-31", "2022-08-25", "2024-06-10", "2021-07-20"])
    assert set(raw_ret.nsmallest(4).index) == set(split_days)  # raw prices: worst days are all splits
    assert adj_ret[split_days].min() > -0.05


def test_metrics_compound_and_use_trading_days():
    ret = pd.Series([0.10, -0.05, 0.02])
    honest, original = performance(ret), performance(ret, honest=False)
    assert honest["Total return"] == pytest.approx(1.10 * 0.95 * 1.02 - 1)
    assert original["Total return"] == pytest.approx(0.07)  # summing returns ignores compounding
    assert original["Sharpe"] / honest["Sharpe"] == pytest.approx((365 / 252) ** 0.5)
