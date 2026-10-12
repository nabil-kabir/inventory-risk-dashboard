"""Integrity checks for data/model. Run after build_model.py:

    py scripts/validate_model.py
"""

import sys
from pathlib import Path

import pandas as pd

MODEL = Path(__file__).resolve().parent.parent / 'data' / 'model'
AS_OF = '2018-07-31'

T = {f.stem: pd.read_csv(f, dtype=str, na_filter=False) for f in MODEL.glob('*.csv')}
failures = []


def check(ok, message):
    if not ok:
        failures.append(message)


def num(table, column):
    return pd.to_numeric(T[table][column])


# every unit received is sold, cleared, or still on hand at the as of date
received = num('fact_receipts', 'units_received').groupby(T['fact_receipts']['sku_key']).sum()
sold = num('fact_sales', 'units').groupby(T['fact_sales']['sku_key']).sum()
cleared = num('fact_writeoffs', 'units').groupby(T['fact_writeoffs']['sku_key']).sum()
latest = T['fact_stock_snapshot'][T['fact_stock_snapshot']['snapshot_date'] == AS_OF]
on_hand = pd.to_numeric(latest['units_on_hand']).groupby(latest['sku_key']).sum()
balance = pd.concat({'received': received, 'sold': sold, 'cleared': cleared, 'on_hand': on_hand}, axis=1).fillna(0)
unbalanced = (balance['received'] != balance['sold'] + balance['cleared'] + balance['on_hand']).sum()
check(unbalanced == 0, f'{unbalanced} SKUs where units received != sold + cleared + on hand')

# keys resolve
products = set(T['dim_product']['product_key'])
sellers = set(T['dim_seller']['seller_key'])
skus = set(T['dim_sku']['sku_key'])
dates = set(T['dim_date']['date'])
buckets = set(T['dim_aging_bucket']['aging_bucket_key'])
batches = set(T['fact_receipts']['batch_id'])
date_column = {'fact_sales': 'order_date', 'fact_receipts': 'received_date',
               'fact_stock_snapshot': 'snapshot_date', 'fact_writeoffs': 'writeoff_date'}
for fact, col in date_column.items():
    df = T[fact]
    bad = (~df['product_key'].isin(products) | ~df['seller_key'].isin(sellers)
           | ~df['sku_key'].isin(skus) | ~df[col].isin(dates))
    if fact != 'fact_receipts':
        bad |= ~df['batch_id'].isin(batches)
    check(not bad.any(), f'{fact}: {bad.sum()} rows with a key or date missing from its dimension')

# row level sanity
snap = T['fact_stock_snapshot']
units, at_risk = num('fact_stock_snapshot', 'units_on_hand'), num('fact_stock_snapshot', 'units_at_risk')
check((snap['aging_bucket_key'].isin(buckets) & (num('fact_stock_snapshot', 'age_days') >= 0)
       & (units > 0) & (at_risk >= 0) & (at_risk <= units)).all(), 'snapshot rows with impossible values')
check((num('fact_sales', 'age_at_sale_days') >= 0).all(), 'sales from batches not yet received')
check(not T['fact_sales'].duplicated(['order_id', 'order_item_id']).any(), 'duplicate sales lines')

# labels shown on the dashboard carry no dashes
labels = {
    'dim_product': ['product_code', 'category', 'price_band'],
    'dim_seller': ['seller_code', 'seller_city', 'state_name', 'region'],
    'dim_sku': ['sku_code'], 'dim_aging_bucket': ['aging_bucket'],
    'dim_date': ['quarter', 'month_name', 'year_month'],
}
for table, cols in labels.items():
    for c in cols:
        bad = T[table][c][T[table][c].str.contains('[-–—]', regex=True)]
        check(bad.empty, f"{table}.{c} has dashes, e.g. {' | '.join(bad.head(3))}")

if failures:
    print('FAILED\n  ' + '\n  '.join(failures))
    sys.exit(1)
print(f"All checks passed ({len(balance)} SKUs, {len(T['fact_sales'])} sales lines, "
      f"{len(snap)} snapshot rows)")
