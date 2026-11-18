import argparse
from pathlib import Path
from strategy import load_ticks, bars_from_ticks, add_signals, toy_backtest, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='data/synthetic_trades.csv')
    p.add_argument('--bar-ms', type=int, default=100)
    p.add_argument('--max-hold-bars', type=int, default=30)
    p.add_argument('--adverse-ticks', type=float, default=1.0)
    p.add_argument('--commission-per-side', type=float, default=2.50)
    args = p.parse_args()

    ticks = load_ticks(args.input)
    if len(ticks) < 100:
        raise SystemExit('Too few ticks. Obtain a longer sample.')
    bars = bars_from_ticks(ticks, bar_ms=args.bar_ms)
    research = add_signals(bars)
    trades, open_position = toy_backtest(
        research, max_hold_bars=args.max_hold_bars,
        adverse_ticks_per_side=args.adverse_ticks,
        commission_per_side=args.commission_per_side)
    Path('results').mkdir(exist_ok=True)
    research.to_csv('results/bars_and_signals.csv')
    trades.to_csv('results/completed_trades.csv', index=False)
    print(f'Loaded {len(ticks):,} trade records and {int((bars.trade_count>0).sum()):,} nonempty bars')
    print(f'Buy/sell signals: {int((research.signal!=0).sum())}')
    print(summary(trades))
    if open_position:
        print('Note: one simulated position remained open and was EXCLUDED from completed-trade metrics.')
    print('IMPORTANT: trade-only proxy fills are NOT executable bid/ask quotes. This is NOT a live-trading backtest.')
    print('Files saved in results/')


if __name__ == '__main__':
    main()
