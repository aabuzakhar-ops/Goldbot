from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

p = Path('results/bars_and_signals.csv')
if not p.exists():
    raise SystemExit('Run python run_backtest.py first')
df = pd.read_csv(p, index_col=0, parse_dates=[0])
selection = df.iloc[:3000]
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(selection.index, selection['close'], label='Last trade close', lw=1)
hi = selection.dropna(subset=['confirmed_fractal_high'])
lo = selection.dropna(subset=['confirmed_fractal_low'])
ax.scatter(hi.index, hi['confirmed_fractal_high'], marker='v', s=15, label='High fractal confirmed')
ax.scatter(lo.index, lo['confirmed_fractal_low'], marker='^', s=15, label='Low fractal confirmed')
ax.set(title='Time-aware fractal confirmations (research only)', xlabel='UTC time', ylabel='Price (USD / troy oz)')
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig('results/fractal_confirmations.png', dpi=150)
plt.close(fig)

p2 = Path('results/completed_trades.csv')
if p2.exists():
    trades = pd.read_csv(p2)
    if len(trades) and 'net_usd' in trades:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(trades['net_usd'].cumsum().to_numpy())
        ax.set(title='Toy model: cumulative completed-trade P&L (not live-executable)',
               xlabel='Completed trade number', ylabel='Illustrative net P&L (USD)')
        fig.tight_layout()
        fig.savefig('results/toy_equity_curve.png', dpi=150)
        plt.close(fig)
print('Saved plots in results/')
