from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 70_000
intervals_ms = rng.exponential(scale=15.0, size=n).astype('int64') + 1
ns = np.cumsum(intervals_ms) * 1_000_000
start = pd.Timestamp('2026-10-05T13:00:00Z')
time = start + pd.to_timedelta(ns, unit='ns')
step = rng.choice([-2, -1, 0, 1, 2], size=n, p=[.04, .20, .52, .20, .04])
price = 3000.0 + 0.1 * np.cumsum(step)
df = pd.DataFrame({'ts_event': time, 'price': price.round(2), 'size': rng.integers(1, 8, size=n)})
Path('data').mkdir(exist_ok=True)
df.to_csv('data/synthetic_trades.csv', index=False)
print('Saved data/synthetic_trades.csv -- SYNTHETIC DATA; never cite performance as real trading evidence')
