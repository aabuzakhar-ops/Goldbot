import numpy as np
import pandas as pd

TICK_SIZE = 0.10
DOLLARS_PER_POINT = 100.0


def load_ticks(path):
    df = pd.read_csv(path)
    needed = {'ts_event', 'price', 'size'}
    if not needed.issubset(df):
        raise ValueError(f'Expected {sorted(needed)}, got {df.columns.tolist()}')
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, errors='raise', format='mixed')
    df['price'] = pd.to_numeric(df['price'], errors='raise')
    df['size'] = pd.to_numeric(df['size'], errors='raise')
    if df[['ts_event', 'price', 'size']].isna().any().any():
        raise ValueError('Null timestamps, trade prices or sizes found')
    if (df['price'] <= 0).any() or (df['size'] <= 0).any():
        raise ValueError('Nonpositive price or trade size found')
    if not df['ts_event'].is_monotonic_increasing:
        print('Warning: trade timestamps out of order, sorting by exchange event time.')
        df = df.sort_values('ts_event', kind='stable')
    return df


def bars_from_ticks(df, bar_ms=100):
    if bar_ms < 1:
        raise ValueError('bar_ms must be >= 1')
    indexed = df.set_index('ts_event').sort_index(kind='stable')
    rule = f'{bar_ms}ms'
    bars = indexed['price'].resample(rule, label='right', closed='left').ohlc()
    bars['volume'] = indexed['size'].resample(rule, label='right', closed='left').sum().fillna(0)
    bars['trade_count'] = indexed['price'].resample(rule, label='right', closed='left').count()
    return bars


def add_signals(bars, fast=20, slow=50):
    if fast >= slow:
        raise ValueError('fast must be lower than slow')
    out = bars.copy()
    hi, lo, close = out['high'], out['low'], out['close']
    confirmed_high = (hi.shift(1) > hi.shift(2)) & (hi.shift(1) > hi)
    confirmed_low = (lo.shift(1) < lo.shift(2)) & (lo.shift(1) < lo)
    out['confirmed_fractal_high'] = hi.shift(1).where(confirmed_high)
    out['confirmed_fractal_low'] = lo.shift(1).where(confirmed_low)
    out['last_fractal_high'] = out['confirmed_fractal_high'].ffill()
    out['last_fractal_low'] = out['confirmed_fractal_low'].ffill()
    last_price = close.ffill()
    out['ema_fast'] = last_price.ewm(span=fast, adjust=False, min_periods=slow).mean()
    out['ema_slow'] = last_price.ewm(span=slow, adjust=False, min_periods=slow).mean()
    prev_close = close.shift(1)
    long_signal = (close > out['last_fractal_high']) & (prev_close <= out['last_fractal_high']) & (out['ema_fast'] > out['ema_slow'])
    short_signal = (close < out['last_fractal_low']) & (prev_close >= out['last_fractal_low']) & (out['ema_fast'] < out['ema_slow'])
    out['signal'] = np.select([long_signal.fillna(False), short_signal.fillna(False)], [1, -1], default=0)
    out.loc[out['trade_count'].eq(0), 'signal'] = 0
    return out


def toy_backtest(bars, max_hold_bars=30, adverse_ticks_per_side=1.0, commission_per_side=2.50):
    trades = []
    position = 0
    entry_price = 0.0
    entry_at = -1
    entry_time = None
    entry_signal_time = None

    for i in range(len(bars) - 1):
        current = bars.iloc[i]
        next_bar = bars.iloc[i + 1]
        signal = int(current['signal'])
        if not np.isfinite(next_bar['open']):
            continue

        if position != 0 and (signal == -position or i - entry_at >= max_hold_bars):
            exit_price = float(next_bar['open']) - position * adverse_ticks_per_side * TICK_SIZE
            gross = position * (exit_price - entry_price) * DOLLARS_PER_POINT
            net = gross - 2 * commission_per_side
            trades.append(dict(
                signal_time=entry_signal_time, entry_time=entry_time,
                exit_time=str(bars.index[i + 1]), side='LONG' if position == 1 else 'SHORT',
                entry_price=entry_price, exit_price=exit_price,
                gross_usd=round(gross, 2), net_usd=round(net, 2),
                bar_count=i + 1 - entry_at))
            position = 0
            continue

        if position == 0 and signal != 0:
            position = signal
            entry_price = float(next_bar['open']) + position * adverse_ticks_per_side * TICK_SIZE
            entry_at = i + 1
            entry_time = str(bars.index[i + 1])
            entry_signal_time = str(bars.index[i])

    return pd.DataFrame(trades), bool(position != 0)


def summary(trades):
    if len(trades) == 0:
        return 'No completed trades. Try longer datasets or inspect your signal filters; do not claim profitability.'
    pnl = trades['net_usd']
    equity = pnl.cumsum()
    max_drawdown = float((equity.cummax().clip(lower=0) - equity).max())
    profits = float(pnl[pnl > 0].sum())
    losses = float(-pnl[pnl < 0].sum())
    pf = profits / losses if losses else float('inf')
    return (f'Closed trades: {len(trades)} | Win rate: {(pnl>0).mean():.1%} | '
            f'Net P&L: ${pnl.sum():,.2f} | Profit factor: {pf:.2f} | '
            f'Max closed-trade drawdown proxy: ${max_drawdown:,.2f}')
