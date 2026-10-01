"""Apply the fixes one at a time and record how each one changes the results."""
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest import ORIGINAL, load_prices, performance, run

OUT = Path(__file__).parent / "output"

STEPS = [  # cumulative: each row keeps the fixes above it
    ("Original script (as received)", {}),
    ("+ fix same-bar execution (look-ahead)", {"trade_next_bar": True}),
    ("+ fix volatility filter (look-ahead)", {"point_in_time_vol": True}),
    ("+ use split/dividend-adjusted prices", {"adjusted_prices": True}),
    ("+ fix metrics (compounding, sqrt(252))", {"honest_metrics": True}),
    ("+ 0.10% trading costs", {"cost_bps": 10.0}),
]


def fmt(stats: dict) -> dict:
    return {k: f"{v:.2f}" if k == "Sharpe" else f"{v:.1%}" for k, v in stats.items()}


def main():
    OUT.mkdir(exist_ok=True)
    settings, rows, curves = ORIGINAL, [], {}
    for label, change in STEPS:
        settings = replace(settings, **change)
        ret, stats = run(settings)
        rows.append({"Step": label, **fmt(stats)})
        curves[label] = ret

    bench_ret = load_prices(adjusted=True).pct_change().mean(axis=1).fillna(0)  # equal weight, daily rebalanced
    rows.append({"Step": "Benchmark: equal-weight buy & hold", **fmt(performance(bench_ret))})
    table = pd.DataFrame(rows).to_markdown(index=False, disable_numparse=True)
    print(table)
    (OUT / "audit.md").write_text(table + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(12, 6))
    # compound both curves so they are comparable (the original summed its returns instead)
    ax.plot((1 + curves[STEPS[0][0]]).cumprod(), color="#d1453b", label="Original script (with look-ahead)")
    ax.plot((1 + curves[STEPS[-1][0]]).cumprod(), color="#2a6fdb", label="After all fixes")
    ax.plot((1 + bench_ret).cumprod(), color="#999", label="Equal-weight buy & hold")
    ax.set_yscale("log")
    ax.set_title("Growth of $1 (log scale): original script vs. corrected backtest")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "claimed_vs_fixed.png", dpi=110)


if __name__ == "__main__":
    main()
