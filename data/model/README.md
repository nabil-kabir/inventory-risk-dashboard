# Model data: how it was built

Built by `scripts/build_model.py` from the Olist Brazilian E-Commerce dataset in `data/raw`.
Checked by `scripts/validate_model.py`. Both need Python 3 with pandas (`py -m pip install pandas`).

```
py scripts/build_model.py
py scripts/validate_model.py
```

The build is seeded, so every run produces identical files (about 20 seconds).

To try different assumptions without editing the script, set overrides first (PowerShell):

```
$env:SIM_OVERRIDES = '{"clearanceAgeDays": 365}'; $env:SIM_OUT = 'C:	emp	rial'
py scripts/build_model.py
```

Every assumption is in the `CONFIG` block at the top of `build_model.py`.

## What is real and what is simulated

**Real (Olist):** every order line, its date, price, freight, product, category, seller and customer state.
104,884 order lines from 91,785 orders, January 2017 to July 2018, excluding canceled and unavailable orders.

**Simulated:** inventory. Olist publishes no stock data, so stock is rebuilt from the real sales.
On the dashboard this is labelled "simulated inventory based on real demand".

**As of date:** 31 July 2018, the last complete month. Olist's final weeks of August 2018 taper off
(orders fall from about 300 a day to 16), so August is left out.

## Simulation method

A SKU is one product sold by one seller (31,981 SKUs).

1. **Unit cost.** Each category gets a cost ratio between 50% and 72% of selling price. Each purchase batch
   moves up to 5% either way, as supplier prices do.
2. **First purchase.** A SKU's first batch lands 5 to 30 days before its first sale. The buyer orders for a
   planned cover of 45 to 90 days (fixed per SKU), with a cautious test order and occasionally a spare unit.
3. **Reorders.** After each sale, if stock falls to the reorder point (daily sales rate times lead time plus
   7 to 14 safety days), a reorder arrives 5 to 20 days later. If a SKU sells out first, the supplier is
   chased and delivers in time for the sale.
4. **Buyer bias.** Order quantities are the buyer's forecast times a per SKU bias (median 1.0, so some buy too
   much and some too little). 15% of sellers habitually over order by 1.6 times. Forecasts lean mostly on the
   coming period with 20% weight on recent sales, so a product whose demand is fading still gets reordered,
   which is how real aged stock forms.
5. **First in, first out.** Each sale consumes the oldest batch, so every sale carries its batch cost and its
   age at sale.
6. **Clearance.** Batches still unsold 270 days after arrival are cleared at month end, recovering 10% to 40%
   of cost. These are logged in `fact_writeoffs`, which shows what aged stock has already cost.

## Value at risk

At each month end, for every batch on hand:

* **Velocity** is the SKU's average daily units over the last 90 days (at least 30 days for new SKUs).
* Units sell in FIFO order at that velocity. A unit with `p` units ahead of it sells in `p / velocity` days.
* A unit is **at risk** if its age when it sells would pass 180 days. A SKU with no sales in 90 days has all
  of its stock at risk.

`units_at_risk` and `value_at_risk` are stored per batch; the dashboard sums them.

## Headline numbers, 31 July 2018

| Measure | Value |
|---|---|
| Stock on hand at cost | R$1,093,689 (15,319 units, 6,637 SKUs) |
| Days of inventory | 60 |
| Over 180 days old | R$203,420 (18.6%) |
| Value at risk | R$494,233 (45.2%) |
| Cleared in the last 12 months | R$357,871 at cost, R$267,452 lost |

Age mix: 0 to 30 days 21.6%, 31 to 60 days 18.0%, 61 to 90 days 11.3%, 91 to 180 days 30.5%, over 180 days 18.6%.

Most of the risk sits in SKUs whose demand has faded while the seller is still trading: the long tail.

## Tables

| Table | Grain | Rows |
|---|---|---|
| `fact_sales` | order line (1 unit) | 104,884 |
| `fact_receipts` | purchase batch | 50,267 |
| `fact_stock_snapshot` | month end x batch on hand | 86,807 |
| `fact_writeoffs` | cleared batch | 3,313 |
| `dim_sku` | product x seller | 31,981 |
| `dim_product` | product, with English category and price band | 30,657 |
| `dim_seller` | seller, with state and region | 2,902 |
| `dim_date` | day, 2016 to 2018 | 1,096 |
| `dim_aging_bucket` | 5 aging buckets | 5 |

Relationships (all one to many, single direction):

* `dim_sku[sku_key]`, `dim_product[product_key]`, `dim_seller[seller_key]` to every fact table
* `dim_date[date]` to `fact_sales[order_date]`, `fact_receipts[received_date]`,
  `fact_stock_snapshot[snapshot_date]`, `fact_writeoffs[writeoff_date]`
* `dim_aging_bucket[aging_bucket_key]` to `fact_stock_snapshot[aging_bucket_key]`

Note: `product_key` and `seller_key` also live on `dim_sku`. In Power BI, relate the facts to `dim_sku` and
snowflake `dim_sku` to product and seller, or relate the facts to all three directly. Pick one, not both,
to avoid ambiguous paths.

Money is in Brazilian reais (R$), as in the source. Around July 2018, US$1 was about R$3.8.
