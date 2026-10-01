| Step                                   | Total return   | Annual return   | Sharpe   | Max drawdown   |
|:---------------------------------------|:---------------|:----------------|:---------|:---------------|
| Original script (as received)          | 658.8%         | 85.3%           | 4.17     | -19.4%         |
| + fix same-bar execution (look-ahead)  | 149.3%         | 19.3%           | 0.72     | -58.1%         |
| + fix volatility filter (look-ahead)   | 149.8%         | 19.4%           | 0.75     | -54.0%         |
| + use split/dividend-adjusted prices   | 237.6%         | 30.8%           | 1.37     | -46.7%         |
| + fix metrics (compounding, sqrt(252)) | 711.1%         | 31.1%           | 1.14     | -38.4%         |
| + 0.10% trading costs                  | 463.4%         | 25.1%           | 0.96     | -40.7%         |
| Benchmark: equal-weight buy & hold     | 1524.6%        | 43.5%           | 1.27     | -49.8%         |
