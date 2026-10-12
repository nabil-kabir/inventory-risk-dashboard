"""Inventory Risk Dashboard: model builder.

Reads the real Olist orders (data/raw) and writes a star schema to data/model:
    real demand      -> fact_sales
    simulated stock  -> fact_receipts, fact_stock_snapshot, fact_writeoffs
    dimensions       -> dim_product, dim_seller, dim_sku, dim_date, dim_aging_bucket

Olist has no inventory, so stock is simulated from the real sales. Every SKU
(product sold by one seller) gets purchase batches timed to meet its real demand.
Batch quantities come from a buyer forecast that blends recent sales with the
coming period, multiplied by a per SKU and per seller bias, so some buyers
over order and stock ages the way it does in a real business. Sales consume
batches first in, first out. Batches still unsold nine months after arrival are
cleared at month end for a fraction of cost, as a real business eventually would.
Everything is seeded, so reruns give identical files.

Run:  py scripts/build_model.py
Experiments:  set SIM_OVERRIDES='{"coverDays": [45, 90]}' and SIM_OUT=some/folder first.
"""

import bisect
import csv
import json
import math
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'raw'
OUT = Path(os.environ.get('SIM_OUT') or ROOT / 'data' / 'model')

CONFIG = {
    'seed': 'olist-inventory-v1',
    'asOf': '2018-07-31',           # last complete month (Olist's final weeks of August taper off)
    'firstSnapshot': '2017-01-31',
    'validStatuses': ['delivered', 'shipped', 'invoiced', 'processing', 'approved', 'created'],
    'costRatio': [0.50, 0.72],      # unit cost as share of selling price, drawn per category
    'batchCostJitter': 0.05,        # supplier price moves +/- 5% between batches
    'coverDays': [45, 90],          # how far ahead each buyer plans a purchase
    'initialLeadDays': [5, 30],     # first batch lands this long before the first sale
    'restockLeadDays': [1, 10],     # a sold out SKU is restocked this long before the sale that needs it
    'supplierLeadDays': [5, 20],    # reorders placed at the reorder point arrive after this long
    'safetyDays': [7, 14],          # reorder point = daily rate x (lead time + safety days)
    'forecastBias': {'median': 1.00, 'sigma': 0.30},
    'pastWeight': 0.2,              # reorder forecasts blend recent sales (this weight) with the coming period
    'overBuyerShare': 0.15,         # share of sellers who habitually over order
    'overBuyerFactor': 1.6,
    'newSkuSpares': [[0, 0.90], [1, 0.10]],  # extra units a buyer adds to a first, test order
    'newSkuBiasDamping': 0.5,       # first orders are cautious: only half of the buyer bias applies
    'clearanceAgeDays': 270,        # batches older than this are cleared at month end
    'clearanceRecovery': [0.10, 0.40],  # share of cost recovered when cleared
    'velocityWindow': 90,           # trailing days used for sales velocity
    'minVelocityWindow': 30,
    'riskAgeDays': 180,             # stock older than this at the time it sells counts as at risk
}
CONFIG.update(json.loads(os.environ.get('SIM_OVERRIDES') or '{}'))


# ---------- helpers ----------

EPOCH = date(1970, 1, 1).toordinal()


def to_day(text):
    """'2018-07-31 10:56:33' -> days since 1970-01-01."""
    return date.fromisoformat(text[:10]).toordinal() - EPOCH


def fmt_day(day):
    return date.fromordinal(day + EPOCH).isoformat()


def js_round(x):
    """Round half up, like JavaScript's Math.round (Python's round() rounds half to even)."""
    f = math.floor(x)
    return f + 1 if x - f >= 0.5 else f


def round2(x):
    return js_round(x * 100) / 100


def round4(x):
    return js_round(x * 10000) / 10000


def median(xs):
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def read_csv(name):
    """Olist file as a list of dicts with every value kept as text."""
    df = pd.read_csv(RAW / name, dtype=str, na_filter=False, encoding='utf-8-sig')
    return df.to_dict('records')


def cell(value):
    """Shortest text for a number: 130.0 -> '130', 0.1 -> '0.1'."""
    if value is None:
        return ''
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


def write_csv(name, rows):
    columns = list(rows[0].keys())
    with open(OUT / name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(columns)
        for row in rows:
            writer.writerow([cell(row[c]) for c in columns])
    return len(rows)


M32 = 0xFFFFFFFF


def hash32(text):
    """FNV-1a, 32 bit."""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & M32
    return h


def rng(key):
    """Seeded random stream (mulberry32). One stream per key, so results never depend on run order."""
    a = hash32(CONFIG['seed'] + '|' + key)

    def next_value():
        nonlocal a
        a = (a + 0x6D2B79F5) & M32
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & M32
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & M32)) & M32
        return ((t ^ (t >> 14)) & M32) / 4294967296

    return next_value


def uniform(r, bounds):
    lo, hi = bounds
    return lo + (hi - lo) * r()


def int_between(r, bounds):
    lo, hi = bounds
    return lo + math.floor(r() * (hi - lo + 1))


def normal(r):
    u = max(r(), 1e-12)
    v = r()
    return math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * v)


def pick_weighted(r, table):
    x = r()
    for value, weight in table:
        x -= weight
        if x <= 0:
            return value
    return table[-1][0]


# ---------- reference data ----------

REGIONS = {
    'AC': ('Acre', 'North'), 'AP': ('Amapa', 'North'), 'AM': ('Amazonas', 'North'), 'PA': ('Para', 'North'),
    'RO': ('Rondonia', 'North'), 'RR': ('Roraima', 'North'), 'TO': ('Tocantins', 'North'),
    'AL': ('Alagoas', 'Northeast'), 'BA': ('Bahia', 'Northeast'), 'CE': ('Ceara', 'Northeast'),
    'MA': ('Maranhao', 'Northeast'), 'PB': ('Paraiba', 'Northeast'), 'PE': ('Pernambuco', 'Northeast'),
    'PI': ('Piaui', 'Northeast'), 'RN': ('Rio Grande do Norte', 'Northeast'), 'SE': ('Sergipe', 'Northeast'),
    'DF': ('Distrito Federal', 'Center West'), 'GO': ('Goias', 'Center West'),
    'MT': ('Mato Grosso', 'Center West'), 'MS': ('Mato Grosso do Sul', 'Center West'),
    'ES': ('Espirito Santo', 'Southeast'), 'MG': ('Minas Gerais', 'Southeast'),
    'RJ': ('Rio de Janeiro', 'Southeast'), 'SP': ('Sao Paulo', 'Southeast'),
    'PR': ('Parana', 'South'), 'RS': ('Rio Grande do Sul', 'South'), 'SC': ('Santa Catarina', 'South'),
}

# Olist's translation file misses two categories and has a few typos.
CATEGORY_FIXES = {
    'pc_gamer': 'pc_gamer',
    'portateis_cozinha_e_preparadores_de_alimentos': 'kitchen_portables_and_food_preparers',
    'fashio_female_clothing': 'fashion_female_clothing',
    'home_confort': 'home_comfort',
    'costruction_tools_garden': 'construction_tools_garden',
    'costruction_tools_tools': 'construction_tools_tools',
}

PRICE_BANDS = [  # (upper limit, sort, label)
    (50, 1, 'Under R$50'),
    (100, 2, 'R$50 to 100'),
    (200, 3, 'R$100 to 200'),
    (500, 4, 'R$200 to 500'),
    (math.inf, 5, 'Over R$500'),
]

AGING_BUCKETS = [
    {'aging_bucket_key': 1, 'aging_bucket': '0 to 30 days', 'min_days': 0, 'max_days': 30},
    {'aging_bucket_key': 2, 'aging_bucket': '31 to 60 days', 'min_days': 31, 'max_days': 60},
    {'aging_bucket_key': 3, 'aging_bucket': '61 to 90 days', 'min_days': 61, 'max_days': 90},
    {'aging_bucket_key': 4, 'aging_bucket': '91 to 180 days', 'min_days': 91, 'max_days': 180},
    {'aging_bucket_key': 5, 'aging_bucket': 'Over 180 days', 'min_days': 181, 'max_days': 99999},
]


MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']


def bucket_for(age):
    return next(b['aging_bucket_key'] for b in AGING_BUCKETS if age <= b['max_days'])


def clean_city(city, state):
    """Olist city names are typed by sellers: 'sao paulo - sp', 'andira-pr', 'sbc/sp'."""
    c = unicodedata.normalize('NFD', city or '')
    c = re.sub('[̀-ͯ]', '', c)
    c = re.sub('[´`]', "'", c).lower().strip()
    if state:
        c = re.sub(r'\s*[-/,]\s*' + re.escape(state.lower()) + '$', '', c)
    c = re.sub(r'[-/,]+', ' ', c)
    c = re.sub(r'\s+', ' ', c).strip()
    return re.sub(r'\b[a-z]', lambda m: m.group().upper(), c, flags=re.ASCII)


def pretty_category(en):
    s = en.replace('_', ' ').strip()
    return s[:1].upper() + s[1:]


# ---------- simulation ----------

@dataclass
class Batch:
    id: int
    received: int
    qty: int
    remaining: int
    cost: float


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    as_of = to_day(CONFIG['asOf'])
    valid = set(CONFIG['validStatuses'])

    print('Reading Olist files...')
    translation = {r['product_category_name']: r['product_category_name_english']
                   for r in read_csv('product_category_name_translation.csv')}
    products = {r['product_id']: r for r in read_csv('olist_products_dataset.csv')}
    sellers = {r['seller_id']: r for r in read_csv('olist_sellers_dataset.csv')}
    customer_state = {r['customer_id']: r['customer_state'] for r in read_csv('olist_customers_dataset.csv')}

    orders = {}
    for o in read_csv('olist_orders_dataset.csv'):
        if o['order_status'] not in valid or not o['order_purchase_timestamp']:
            continue
        day = to_day(o['order_purchase_timestamp'])
        if day > as_of:
            continue
        orders[o['order_id']] = {'day': day, 'status': o['order_status'],
                                 'state': customer_state.get(o['customer_id'], '')}

    lines = []
    for it in read_csv('olist_order_items_dataset.csv'):
        o = orders.get(it['order_id'])
        if not o:
            continue
        lines.append({
            'order_id': it['order_id'], 'order_item_id': int(it['order_item_id']),
            'product_id': it['product_id'], 'seller_id': it['seller_id'],
            'day': o['day'], 'status': o['status'], 'customer_state': o['state'],
            'price': float(it['price']), 'freight': float(it['freight_value']),
        })
    print(f"  {len(orders)} valid orders, {len(lines)} order lines up to {CONFIG['asOf']}")

    # ---------- dimensions ----------

    def category_of(pid):
        pt = products.get(pid, {}).get('product_category_name', '')
        if not pt:
            return 'uncategorized'
        en = translation.get(pt)
        return CATEGORY_FIXES.get(en) or en or CATEGORY_FIXES.get(pt) or pt

    product_ids = sorted({l['product_id'] for l in lines})
    seller_ids = sorted({l['seller_id'] for l in lines})
    product_key = {pid: i + 1 for i, pid in enumerate(product_ids)}
    seller_key = {sid: i + 1 for i, sid in enumerate(seller_ids)}

    prices_by_product = {}
    for l in lines:
        prices_by_product.setdefault(l['product_id'], []).append(l['price'])

    categories = sorted({category_of(pid) for pid in product_ids})
    cost_ratio = {c: uniform(rng('cost|' + c), CONFIG['costRatio']) for c in categories}

    dim_product = []
    for pid in product_ids:
        p = products.get(pid, {})
        med = median(prices_by_product[pid])
        band = next(b for b in PRICE_BANDS if med < b[0])
        cat = category_of(pid)
        dim_product.append({
            'product_key': product_key[pid], 'product_id': pid,
            'product_code': 'P' + str(product_key[pid]).zfill(5),
            'category_key': cat, 'category': 'Uncategorized' if cat == 'uncategorized' else pretty_category(cat),
            'category_pt': p.get('product_category_name', ''),
            'median_price': round2(med), 'price_band_sort': band[1], 'price_band': band[2],
            'weight_g': p.get('product_weight_g', ''), 'photos': p.get('product_photos_qty', ''),
        })

    over_buyer = {sid: rng('overbuyer|' + sid)() < CONFIG['overBuyerShare'] for sid in seller_ids}
    dim_seller = []
    for sid in seller_ids:
        s = sellers.get(sid, {})
        state = s.get('seller_state', '')
        state_name, region = REGIONS.get(state, ('Unknown', 'Unknown'))
        dim_seller.append({
            'seller_key': seller_key[sid], 'seller_id': sid,
            'seller_code': 'Seller ' + str(seller_key[sid]).zfill(4),
            'seller_city': clean_city(s.get('seller_city', ''), state), 'seller_state': state,
            'state_name': state_name, 'region': region,
        })

    # ---------- simulate stock per SKU ----------

    by_sku = {}
    for l in lines:
        by_sku.setdefault(l['product_id'] + '|' + l['seller_id'], []).append(l)
    sku_ids = sorted(by_sku)

    snapshot_days = []
    d = date.fromisoformat(CONFIG['firstSnapshot'])
    while d.toordinal() - EPOCH <= as_of:
        snapshot_days.append(d.toordinal() - EPOCH)
        y, m = (d.year, d.month + 1) if d.month < 12 else (d.year + 1, 1)
        next_first = date(y + (m == 12), m % 12 + 1, 1)  # first day of the month after next month
        d = date.fromordinal(next_first.toordinal() - 1)   # last day of next month

    dim_sku, fact_sales, fact_receipts, fact_snapshot, fact_writeoffs = [], [], [], [], []
    batch_seq = 0

    for idx, sku_id in enumerate(sku_ids):
        sku_key = idx + 1
        sales = sorted(by_sku[sku_id], key=lambda s: (s['day'], s['order_id'], s['order_item_id']))
        pid, sid = sku_id.split('|')
        r = rng('sku|' + sku_id)
        p_key, s_key = product_key[pid], seller_key[sid]
        list_price = median([s['price'] for s in sales])
        base_cost = list_price * cost_ratio[category_of(pid)]
        cover = int_between(r, CONFIG['coverDays'])
        bias = (math.exp(math.log(CONFIG['forecastBias']['median']) + CONFIG['forecastBias']['sigma'] * normal(r))
                * (CONFIG['overBuyerFactor'] if over_buyer[sid] else 1))

        days = [s['day'] for s in sales]

        def units_between(start, end):
            """Units sold with start <= day < end."""
            return bisect.bisect_left(days, end) - bisect.bisect_left(days, start)

        batches = []
        on_hand = 0
        snap_idx = 0
        last_snap_emitted = -math.inf
        prev_sale_day = -math.inf
        pending = None

        def forecast_from(day, is_first):
            # demand the buyer expects over the cover period starting at day; the data stops
            # at as_of, so the unseen part of the window runs at the recent rate
            past_demand = units_between(day - cover, day)
            seen_days = max(0, min(cover, as_of - day + 1))
            coming_demand = units_between(day, day + seen_days) + (cover - seen_days) * past_demand / cover
            if is_first:
                first_bias = 1 + CONFIG['newSkuBiasDamping'] * (bias - 1)
                return coming_demand * first_bias + pick_weighted(r, CONFIG['newSkuSpares'])
            return ((1 - CONFIG['pastWeight']) * coming_demand + CONFIG['pastWeight'] * past_demand) * bias

        def add_batch(received, forecast):
            nonlocal batch_seq, on_hand
            qty = max(1, js_round(forecast * (0.9 + 0.2 * r())))
            cost = round2(base_cost * (1 + CONFIG['batchCostJitter'] * (2 * r() - 1)))
            batch_seq += 1
            b = Batch(batch_seq, received, qty, qty, cost)
            batches.append(b)
            on_hand += qty
            fact_receipts.append({
                'batch_id': b.id, 'sku_key': sku_key, 'product_key': p_key, 'seller_key': s_key,
                'received_date': fmt_day(received), 'units_received': qty, 'unit_cost': cost,
                'value_at_cost': round2(qty * cost),
            })

        def receive_up_to(day):
            nonlocal pending
            if pending and pending['arrival'] <= day:
                add_batch(pending['arrival'], pending['forecast'])
                pending = None

        def emit_snapshot(snap_day):
            nonlocal last_snap_emitted, on_hand
            last_snap_emitted = snap_day
            for b in batches:
                if b.remaining <= 0 or snap_day - b.received <= CONFIG['clearanceAgeDays']:
                    continue
                recovery = round2(uniform(r, CONFIG['clearanceRecovery']))
                fact_writeoffs.append({
                    'writeoff_date': fmt_day(snap_day), 'batch_id': b.id, 'sku_key': sku_key,
                    'product_key': p_key, 'seller_key': s_key,
                    'age_days': snap_day - b.received, 'units': b.remaining, 'unit_cost': b.cost,
                    'value_at_cost': round2(b.remaining * b.cost), 'recovery_rate': recovery,
                    'recovered_value': round2(b.remaining * b.cost * recovery),
                    'loss_value': round2(b.remaining * b.cost * (1 - recovery)),
                })
                on_hand -= b.remaining
                b.remaining = 0
            if on_hand <= 0:
                return
            first_receipt = batches[0].received
            window = max(CONFIG['minVelocityWindow'], min(CONFIG['velocityWindow'], snap_day - first_receipt + 1))
            velocity = units_between(snap_day - window + 1, snap_day + 1) / window
            ahead = 0
            for b in batches:
                if b.remaining <= 0:
                    continue
                age = snap_day - b.received
                start, end = ahead, ahead + b.remaining
                # units sell in FIFO order at the current velocity; a unit at queue position p
                # sells after p / velocity days, so it is at risk once age + p / velocity > limit
                safe_up_to = velocity * max(0, CONFIG['riskAgeDays'] - age) if velocity > 0 else 0
                at_risk = min(b.remaining, max(0, end - max(start, safe_up_to)))
                fact_snapshot.append({
                    'snapshot_date': fmt_day(snap_day), 'sku_key': sku_key, 'product_key': p_key,
                    'seller_key': s_key, 'batch_id': b.id, 'received_date': fmt_day(b.received),
                    'age_days': age, 'aging_bucket_key': bucket_for(age),
                    'units_on_hand': b.remaining, 'unit_cost': b.cost, 'value_at_cost': round2(b.remaining * b.cost),
                    'units_ahead_fifo': start, 'sku_units_on_hand': on_hand,
                    'sku_velocity_per_day': round4(velocity),
                    'units_at_risk': round2(at_risk), 'value_at_risk': round2(at_risk * b.cost),
                })
                ahead = end

        def emit_until(day):
            nonlocal snap_idx
            while snap_idx < len(snapshot_days) and snapshot_days[snap_idx] < day:
                receive_up_to(snapshot_days[snap_idx])
                emit_snapshot(snapshot_days[snap_idx])
                snap_idx += 1

        for s in sales:
            emit_until(s['day'])
            receive_up_to(s['day'])
            if on_hand == 0:
                if pending:
                    # sold out before the reorder landed: the supplier is chased and delivers now
                    pending['arrival'] = s['day']
                    receive_up_to(s['day'])
                else:
                    is_first = not batches
                    lead = int_between(r, CONFIG['initialLeadDays'] if is_first else CONFIG['restockLeadDays'])
                    received = min(s['day'], max(s['day'] - lead, prev_sale_day, last_snap_emitted + 1))
                    add_batch(received, forecast_from(s['day'], is_first))
            b = next(x for x in batches if x.remaining > 0)
            b.remaining -= 1
            on_hand -= 1
            prev_sale_day = s['day']
            fact_sales.append({
                'order_id': s['order_id'], 'order_item_id': s['order_item_id'], 'order_date': fmt_day(s['day']),
                'sku_key': sku_key, 'product_key': p_key, 'seller_key': s_key, 'batch_id': b.id,
                'customer_state': s['customer_state'], 'order_status': s['status'], 'units': 1,
                'price': round2(s['price']), 'freight': round2(s['freight']), 'unit_cost': b.cost,
                'gross_margin': round2(s['price'] - b.cost), 'age_at_sale_days': s['day'] - b.received,
            })
            # reorder point: SKUs that sell steadily are reordered before they run out
            if not pending:
                rate = units_between(s['day'] - cover + 1, s['day'] + 1) / cover
                lead = int_between(r, CONFIG['supplierLeadDays'])
                reorder_point = rate * (lead + int_between(r, CONFIG['safetyDays']))
                if reorder_point >= 1 and on_hand <= reorder_point:
                    pending = {'arrival': s['day'] + lead, 'forecast': forecast_from(s['day'] + lead, False)}
        emit_until(as_of + 1)

        dim_sku.append({
            'sku_key': sku_key, 'sku_code': 'SKU ' + str(sku_key).zfill(5),
            'product_key': p_key, 'seller_key': s_key, 'list_price': round2(list_price),
            'base_unit_cost': round2(base_cost), 'planned_cover_days': cover, 'forecast_bias': round4(bias),
            'over_buyer_seller': 1 if over_buyer[sid] else 0,
            'first_sale_date': fmt_day(days[0]), 'last_sale_date': fmt_day(days[-1]),
            'lifetime_units': len(days),
        })

    # ---------- date and bucket dimensions ----------

    min_day = min(to_day(x['received_date']) for x in fact_receipts)
    start_day = to_day(fmt_day(min_day)[:4] + '-01-01')
    end_day = to_day('2018-12-31')
    snapshot_set = set(snapshot_days)
    dim_date = []
    for day in range(start_day, end_day + 1):
        dt = date.fromordinal(day + EPOCH)
        month_name = MONTHS[dt.month - 1]
        dim_date.append({
            'date': dt.isoformat(), 'year': dt.year, 'quarter': f'Q{(dt.month - 1) // 3 + 1}',
            'month_num': dt.month, 'month_name': month_name, 'month_short': month_name[:3],
            'year_month': f'{month_name[:3]} {dt.year}', 'year_month_sort': dt.year * 100 + dt.month,
            'day_of_week': dt.isoweekday(),
            'is_month_end': 1 if date.fromordinal(day + EPOCH + 1).day == 1 else 0,
            'is_snapshot_date': 1 if day in snapshot_set else 0,
            'is_as_of_date': 1 if day == as_of else 0,
        })

    # ---------- write ----------

    tables = {
        'dim_product.csv': dim_product, 'dim_seller.csv': dim_seller, 'dim_sku.csv': dim_sku,
        'dim_date.csv': dim_date, 'dim_aging_bucket.csv': AGING_BUCKETS,
        'fact_sales.csv': fact_sales, 'fact_receipts.csv': fact_receipts,
        'fact_stock_snapshot.csv': fact_snapshot, 'fact_writeoffs.csv': fact_writeoffs,
    }
    print(f'Writing {OUT}:')
    for name, rows in tables.items():
        print(f'  {name:<26} {write_csv(name, rows)} rows')

    # ---------- calibration summary ----------

    def money(x):
        return f'R${js_round(x):,}'

    latest = [x for x in fact_snapshot if x['snapshot_date'] == CONFIG['asOf']]
    stock_value = sum(x['value_at_cost'] for x in latest)
    cogs_per_day = sum(x['unit_cost'] for x in fact_sales if to_day(x['order_date']) > as_of - 90) / 90
    print(f"\nAs of {CONFIG['asOf']}")
    print(f"  Revenue (all lines)      {money(sum(x['price'] for x in fact_sales))}")
    print(f"  Stock on hand at cost    {money(stock_value)}  "
          f"({sum(x['units_on_hand'] for x in latest)} units, {len({x['sku_key'] for x in latest})} SKUs)")
    print(f'  Days of inventory        {stock_value / cogs_per_day:.0f}')
    for b in AGING_BUCKETS:
        v = sum(x['value_at_cost'] for x in latest if x['aging_bucket_key'] == b['aging_bucket_key'])
        print(f"  {b['aging_bucket']:<24} {money(v):>12}  {100 * v / stock_value:.1f}%")
    var = sum(x['value_at_risk'] for x in latest)
    print(f'  Value at risk            {money(var)}  {100 * var / stock_value:.1f}%')
    wo12 = [x for x in fact_writeoffs if to_day(x['writeoff_date']) > as_of - 365]
    print(f"  Cleared, last 12 months  {money(sum(x['value_at_cost'] for x in wo12))} at cost, "
          f"loss {money(sum(x['loss_value'] for x in wo12))}")
    print('\nStock value and value at risk by month end:')
    for day in snapshot_days:
        rows = [x for x in fact_snapshot if x['snapshot_date'] == fmt_day(day)]
        print(f"  {fmt_day(day)}  {money(sum(x['value_at_cost'] for x in rows)):>12}  "
              f"{money(sum(x['value_at_risk'] for x in rows)):>12}")


if __name__ == '__main__':
    main()
