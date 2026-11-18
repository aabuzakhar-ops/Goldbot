import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Databento historical CME gold trade downloader')
    parser.add_argument('--start', default='2026-10-05T13:00:00', help='UTC start, inclusive')
    parser.add_argument('--end', default='2026-10-05T13:10:00', help='UTC end, exclusive')
    parser.add_argument('--download', action='store_true', help='Actually download after inspecting cost')
    args = parser.parse_args()

    key = os.getenv('DATABENTO_API_KEY')
    if not key:
        raise SystemExit('Set your DATABENTO_API_KEY environment variable. See README.md')
    import databento as db
    import pandas as pd

    client = db.Historical(key)
    request = dict(dataset='GLBX.MDP3', symbols='GC.v.0', stype_in='continuous',
                   schema='trades', start=args.start, end=args.end)
    print('Request:', request)
    cost = client.metadata.get_cost(**request)
    print(f'Estimated data cost: ${cost:.4f} USD (actual billed amount can differ)')
    if not args.download:
        print('No data downloaded. Add --download only after accepting that price.')
        return

    data = client.timeseries.get_range(**request)
    df = data.to_df().reset_index()
    required = ['ts_event', 'price', 'size']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'Missing trade fields: {missing}; inspect returned columns: {list(df.columns)}')
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, format='mixed')
    df = df[required].sort_values('ts_event', kind='stable')
    Path('data').mkdir(exist_ok=True)
    outfile = Path('data/gold_trades.csv')
    df.to_csv(outfile, index=False)
    print(f'Saved {len(df):,} trades to {outfile}. Note this CSV contains only LAST TRADES, not bid/ask quotes.')


if __name__ == '__main__':
    main()
