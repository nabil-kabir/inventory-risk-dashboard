# Build it yourself: Inventory Risk Dashboard

A page by page recipe for rebuilding the five report pages by hand, for practice. Every visual lists its
type, fields, title and exact position, so your version can match the finished one pixel for pixel.

The data model (tables, relationships, 52 measures) is already done, so this is purely report building.
Allow two to four hours for all five pages. Page 3 (Liquidation) teaches the most.

## Before you start

1. **Open the practice copy:** `practice/Inventory Risk Practice.pbip`. It has its own copy of the model and
   a blank report, so nothing you do there touches the finished dashboard in `Inventory Risk Dashboard.pbip`.
   Keep the finished one closed while you practise, or open it side by side for reference.
2. **Page size:** click an empty spot on the canvas, open the Format pane, go to **Canvas settings**, choose
   Type **Custom**, Width **1280**, Height **720**. All positions below assume this size.
3. **Theme:** **View > Themes > Browse for themes** and pick `theme/InventoryRiskDark.json`. This gives the dark
   background, the site colours, card and table styling, in one step.
4. **Exact positions:** select a visual, then **Format > General > Properties > Size and position**. Type the
   numbers from the tables below: X is Horizontal, Y is Vertical.
5. **Renaming a field inside a visual:** in the Build pane, double click the field (or use its dropdown,
   **Rename for this visual**). The tables below show the display name after a colon, for example
   `Stock Value Card: Stock on hand`.
6. **All measures** live in the `Metrics` table, grouped in display folders (Stock, Risk, Aging, Sales,
   Velocity, Write Offs, Scenario, Card Labels).
7. Rename the starter page to **Summary** (double click the tab) and add four more pages: **Aging**,
   **Liquidation**, **Sellers**, **About**.

Tip: build one visual fully, then copy and paste it (Ctrl+C, Ctrl+V) and swap the field. Formatting comes along.

## Colours

| Name | Hex | Used for |
|---|---|---|
| Ink | `#07090C` | page background (from the theme) |
| Surface | `#121C25` | visual backgrounds (from the theme) |
| Bone | `#ECE7DF` | main text |
| Mist | `#8B97A3` | labels and small text |
| Teal | `#2F8FB5` | stock, the "act now" side |
| Amber | `#F2B35B` | risk, the "wait" side |
| Amber deep | `#C9822F` | top of the heat map scale |
| Teal glow | `#5CC6E8` | links |

## Page 1: Summary

The one page an executive reads. Shows the problem, its size, the trend and where it sits.

| Visual | Fields | Title | X | Y | W | H |
|---|---|---|---|---|---|---|
| Text box | (header, see below) | none | 24 | 6 | 690 | 76 |
| Page navigator | none | none | 730 | 18 | 526 | 44 |
| Card | Value: `Headline` | none | 24 | 84 | 1232 | 60 |
| Card | Value: `Stock Value Card: Stock on hand` | none | 24 | 160 | 192 | 92 |
| Card | Value: `Value at Risk: Value at risk` | none | 232 | 160 | 192 | 92 |
| Card | Value: `Value at Risk %: Share of stock at risk` | none | 440 | 160 | 192 | 92 |
| Card | Value: `Over 180 Days %: Older than 180 days` | none | 648 | 160 | 192 | 92 |
| Card | Value: `Days of Inventory: Days of inventory` | none | 856 | 160 | 192 | 92 |
| Card | Value: `Write Off Loss 12M: Write offs, 12 months` | none | 1064 | 160 | 192 | 92 |
| Line chart | X axis: `Date[Year Month]`. Y axis: `Stock Value: Stock on hand`, `Value at Risk: Value at risk` | Stock on hand and value at risk, month end | 24 | 268 | 752 | 406 |
| Clustered bar chart | Y axis: `Product[Category]`. X axis: `Value at Risk: Value at risk` | Top 5 categories by value at risk | 792 | 268 | 464 | 226 |
| Clustered column chart | X axis: `Aging Bucket[Aging Bucket]`. Y axis: `Stock Value: Stock on hand` | Stock on hand by age | 792 | 510 | 464 | 164 |
| Text box | (footer, see below) | none | 24 | 678 | 1232 | 42 |

How to:

* **Header text box:** Insert > Text box. Line 1 "Which stock is about to become a loss?" in Segoe UI Semibold 18, bold.
  Line 2 "Executive summary  ·  stock on hand, what is at risk, and what aged stock already cost" in 10, colour Mist.
  If a scrollbar appears, the box is too short: make it taller.
* **Page navigator:** Insert > Buttons > Navigator > **Page navigator**. It makes one button per page automatically.
* **Headline card:** the `Headline` measure returns a full sentence. Format > Callout > Value: size 15, colour Amber.
  Turn **Label** off and the visual **Title** off.
* **KPI cards:** turn the visual Title off on each; the label shows the renamed field.
  Why `Stock Value Card` and not `Stock Value`? This card visual rounds numbers automatically
  (R$1,093,689 shows as "R$1M") and has no setting to stop it, so a text measure formats the value as "R$1.09M".
* **Line chart:** Format > Lines > Colour: Stock on hand Teal, Value at risk Amber. Make sure months run in order:
  on the chart, More options (...) > **Sort axis** > Year Month, then Sort ascending. (Year Month is set to sort by
  a hidden number column in the model, which is why this works.)
* **Top 5 bar chart:** Filters pane > Category > Filter type **Top N** > Show items Top **5** > By value: drag in
  `Value at Risk` > Apply filter. Bar colour Amber. Sort by Value at risk, descending.
* **Stock by age:** bar colour Teal. Aging buckets already sort in age order (Sort by column in the model).
* **Footer:** text box, size 8, colour Mist: "Simulated inventory based on real demand  ·  Olist Brazilian ecommerce
  orders, Jan 2017 to Jul 2018  ·  values at cost in Brazilian reais (R$)  ·  as of 31 July 2018". Copy this
  footer, the header and the navigator to every page (Ctrl+C on this page, Ctrl+V on the next keeps the position).

## Page 2: Aging

Where old stock sits. Introduces slicers, a waterfall and a heat map.

| Visual | Fields | Title | X | Y | W | H |
|---|---|---|---|---|---|---|
| Slicer | Field: `Product[Category]` | Category | 24 | 84 | 300 | 64 |
| Slicer | Field: `Product[Price Band]` | Price Band | 340 | 84 | 300 | 64 |
| Slicer | Field: `Seller[Region]` | Region | 656 | 84 | 300 | 64 |
| Card | `Stock Value Card: Stock on hand` | none | 24 | 164 | 234 | 84 |
| Card | `Average Stock Age: Average age, days` | none | 274 | 164 | 234 | 84 |
| Card | `Over 90 Days %: Older than 90 days` | none | 523 | 164 | 234 | 84 |
| Card | `Over 180 Days %: Older than 180 days` | none | 773 | 164 | 234 | 84 |
| Card | `Sell Through 90D: Sell through, 90 days` | none | 1022 | 164 | 234 | 84 |
| Waterfall chart | Category: `Aging Bucket[Aging Bucket]`. Y axis: `Stock Value: Stock on hand` | How stock on hand builds up by age | 24 | 264 | 400 | 410 |
| Matrix | Rows: `Product[Category]`. Columns: `Aging Bucket[Aging Bucket]`. Values: `Stock Value: Stock on hand` | Heat map: stock on hand by category and age | 440 | 264 | 816 | 210 |
| Table | Columns: `SKU[SKU]`, `SKU[Category]`, `SKU[Seller]`, `Stock Units: Units`, `Stock Value: Stock on hand`, `Average Stock Age: Average age`, `Weeks of Cover: Weeks of cover`, `Value at Risk: Value at risk` | SKUs holding stock, largest value at risk first | 440 | 490 | 816 | 184 |

How to:

* **Dropdown slicers:** Format > Slicer settings > Options > Style **Dropdown**. Turn the slicer header off and the
  visual Title on, with the text shown in the table.
* **Waterfall:** Format > Columns (sentiment colours): Increase Teal, Total Amber. Turn the Legend off.
* **Heat map (matrix):** Format > Cell elements > **Background colour** on > fx > Format style **Gradient**,
  based on Stock on hand. Lowest value `#121C25`, highest value `#C9822F`. Sort the matrix by Stock on hand,
  descending (click the column header, or More options > Sort by).
* **SKU table:** in the Filters pane, on this visual, drag `Stock Value` in, choose **Show items when the value is
  greater than 0**. Sort by Value at risk, descending.
  Why `SKU[Category]` and `SKU[Seller]` and not `Product[Category]` and `Seller[Seller]`? Columns from three
  different tables make Power BI test every combination (32,000 SKUs × 74 categories × 2,900 sellers) before
  filtering. The model copies Category and Seller onto the SKU table so the table reads from one table and
  stays instant. Try the slow version once to feel the difference.

## Page 3: Liquidation

The decision page. Introduces what if sliders and an action list driven by a scenario.

| Visual | Fields | Title | X | Y | W | H |
|---|---|---|---|---|---|---|
| Slicer | Field: `Markdown[Markdown]` | Markdown on stock at risk | 24 | 84 | 760 | 68 |
| Slicer | Field: `Clearance Response[Clearance Response]` | Stock cleared per 10 points of markdown | 800 | 84 | 456 | 68 |
| Card | `Projected Loss No Action: Loss if we wait and clear later` | none | 24 | 168 | 234 | 88 |
| Card | `Projected Loss With Markdown: Loss with this markdown` | none | 274 | 168 | 234 | 88 |
| Card | `Value Saved by Markdown: Saved by acting now` | none | 523 | 168 | 234 | 88 |
| Card | `Markdown Sell Through: At risk units it clears` | none | 773 | 168 | 234 | 88 |
| Card | `Suggested Markdown: Best single markdown` | none | 1022 | 168 | 234 | 88 |
| Clustered bar chart | Y axis: `Product[Category]`. X axis: `Projected Loss No Action: Wait and clear later`, `Projected Loss With Markdown: Mark down now` | Projected loss by category: wait or mark down | 24 | 272 | 470 | 402 |
| Table | Columns: `SKU[SKU]`, `SKU[Category]`, `SKU[Seller]`, `Units at Risk: Units at risk`, `Value at Risk: Value at risk`, `Suggested Markdown: Suggested markdown`, `Value Saved at Suggested Markdown: Saved` | Action list: SKUs ranked by what their best markdown saves | 510 | 272 | 746 | 402 |

How to:

* **Tile sliders:** Format > Slicer settings > Options > Style **Tile**, Orientation **Horizontal**.
  Selection: **Single select** on. Click 30% on the Markdown slider and 15% on Clearance Response so the page opens
  with sensible defaults (the measures also fall back to 30% and 15% when nothing is selected).
* **Cards:** watch them change as you click different markdowns. That is the `Selected Markdown` and
  `Selected Clearance Response` measures reading the sliders with SELECTEDVALUE.
* **Bar chart:** Top N filter on Category, Top **10** by `Projected Loss No Action`. Colours: Wait and clear later
  Amber, Mark down now Teal. Sort by Wait and clear later, descending.
* **Action table:** visual filter `Value at Risk` greater than 0. Sort by Saved, descending.
* **Footer:** "Marked down units sell at list price less the markdown. Stock the markdown does not clear is
  cleared later at the historical recovery rate (about 25% of cost)."

## Page 4: Sellers

Where risk concentrates. Introduces the scatter chart.

| Visual | Fields | Title | X | Y | W | H |
|---|---|---|---|---|---|---|
| Card | `Value at Risk: Value at risk` | none | 24 | 84 | 296 | 88 |
| Card | `Sellers at Risk Card: Sellers holding stock at risk` | none | 336 | 84 | 296 | 88 |
| Card | `SKUs at Risk Card: SKUs at risk` | none | 648 | 84 | 296 | 88 |
| Card | `Top 20 Sellers Share of Risk: Held by the top 20 sellers` | none | 960 | 84 | 296 | 88 |
| Clustered bar chart | Y axis: `Seller[Region]`. X axis: `Value at Risk: Value at risk` | Value at risk by seller region | 24 | 188 | 380 | 200 |
| Clustered bar chart | Y axis: `Seller[State]`. X axis: `Value at Risk: Value at risk` | Top 8 seller states by value at risk | 24 | 404 | 380 | 270 |
| Scatter chart | Values: `Seller[Seller]`. X axis: `Stock Value: Stock on hand`. Y axis: `Value at Risk %: Share at risk`. Size: `Value at Risk: Value at risk` | Each seller: stock held against share at risk (bubble size: value at risk) | 420 | 188 | 836 | 230 |
| Table | Columns: `Seller[Seller]`, `Seller[State]`, `Seller[Region]`, `SKUs in Stock: SKUs in stock`, `SKUs at Risk: SKUs at risk`, `Stock Value: Stock on hand`, `Value at Risk: Value at risk`, `Value at Risk %: Share at risk` | Sellers ranked by value at risk | 420 | 434 | 836 | 240 |

How to:

* **Bars:** colour Amber, sort by Value at risk descending. States chart: Top N filter, Top **8** by `Value at Risk`.
* **Scatter:** each dot is a seller. Top right means big stock and a high share at risk: the sellers to call first.
* **Table:** visual filter `Value at Risk` greater than 0, sort by Value at risk descending.

## Page 5: About

Three text boxes, each 400 wide and 568 tall, at X 24, 440 and 856, Y 96. Turn each text box's background on
(Surface `#121C25`) with a rounded border, and padding of about 18. Headings in Amber, size 13, bold; body in 10.5.

* Column 1: The question, The data
* Column 2: How stock was simulated, How value at risk is measured
* Column 3: The liquidation planner, Built with, Author

Copy the wording from the finished report. To link the website, select the text `nabil-kabir.github.io` and use
the link button in the text box toolbar.

## Check your work

At the default settings your numbers should match the finished report exactly:

| Measure | Value |
|---|---|
| Stock on hand | R$1.09M (R$1,093,689) |
| Value at risk | R$494K, 45.2% of stock |
| Older than 180 days | 18.6% |
| Days of inventory | 60 |
| Write offs, 12 months | R$267K |
| Loss if we wait / with a 30% markdown / saved | R$369K / R$172K / R$197K |
| Best single markdown | 40% |
| Sellers holding stock at risk / SKUs at risk | 1,092 / 4,057 |

If a number differs, check the visual's filters (Filters pane) and that slicers on the page are cleared.

## When you are done

Your practice copy is yours to keep or delete. The finished dashboard is rebuilt from
`scripts/build_report.py`, so if you build something you prefer, tell Claude and it can fold your changes in.
