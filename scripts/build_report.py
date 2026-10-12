"""Inventory Risk Dashboard: report builder.

Writes the theme and the five report pages into the PBIR report folder
(Inventory Risk Dashboard.Report). Every page is rebuilt from this file, so
manual edits made in Power BI Desktop to these pages are replaced on the next run.

Close Power BI Desktop first: it owns the report files while the project is open.

Run:  py scripts/build_report.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / 'Inventory Risk Dashboard.Report'
DEFINITION = REPORT / 'definition'
THEME_NAME = 'InventoryRiskDark.json'

SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition'
VISUAL_SCHEMA = f'{SCHEMA}/visualContainer/2.12.0/schema.json'
PAGE_SCHEMA = f'{SCHEMA}/page/2.1.0/schema.json'
PAGES_SCHEMA = f'{SCHEMA}/pagesMetadata/1.1.0/schema.json'

PAGE_W, PAGE_H = 1280, 720
M = 24          # page margin
G = 16          # gap between visuals

# site palette (nabil-kabir.github.io)
INK = '#07090C'
SURFACE = '#121C25'
RAISED = '#1A2733'
LINE = '#1E2B37'
BONE = '#ECE7DF'
MIST = '#8B97A3'
TEAL = '#2F8FB5'
TEAL_GLOW = '#5CC6E8'
AMBER = '#F2B35B'
AMBER_DEEP = '#C9822F'


# ---------- theme ----------

def solid(color):
    return {'solid': {'color': color}}


THEME = {
    'name': 'Inventory Risk Dark',
    'dataColors': [TEAL, AMBER, TEAL_GLOW, AMBER_DEEP, MIST, '#3E8E7E', BONE, '#7A6FA8'],
    'foreground': BONE,
    'foregroundNeutralSecondary': MIST,
    'foregroundNeutralTertiary': '#5E6B77',
    'background': SURFACE,
    'backgroundLight': RAISED,
    'backgroundNeutral': '#22313F',
    'backgroundDark': INK,
    'tableAccent': TEAL,
    'shapeStroke': LINE,
    'good': TEAL,
    'neutral': MIST,
    'bad': AMBER,
    'maximum': AMBER,
    'center': AMBER_DEEP,
    'minimum': SURFACE,
    'hyperlink': TEAL_GLOW,
    'visitedHyperlink': TEAL_GLOW,
    'textClasses': {
        'callout': {'fontSize': 24, 'fontFace': 'Segoe UI Semibold', 'color': BONE},
        'title': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': BONE},
        'header': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': BONE},
        'label': {'fontSize': 10, 'fontFace': 'Segoe UI', 'color': MIST},
    },
    'visualStyles': {
        '*': {'*': {
            'background': [{'show': True, 'color': solid(SURFACE), 'transparency': 0}],
            'border': [{'show': True, 'color': solid(LINE), 'radius': 10, 'width': 1}],
            'title': [{'show': True, 'fontColor': solid(BONE), 'fontSize': 12, 'fontFamily': 'Segoe UI Semibold'}],
            'subTitle': [{'show': False}],
            'padding': [{'left': 12, 'top': 10, 'right': 12, 'bottom': 10}],
            'spacing': [{'customizeSpacing': True, 'spaceBelowTitle': 6, 'spaceAbovePlotArea': 8}],
            'categoryAxis': [{'labelColor': solid(MIST), 'gridlineColor': solid(LINE), 'fontSize': 9}],
            'valueAxis': [{'labelColor': solid(MIST), 'gridlineColor': solid(LINE), 'fontSize': 9}],
            'legend': [{'show': True, 'position': 'Top', 'labelColor': solid(MIST), 'fontSize': 9}],
            'labels': [{'color': solid(BONE), 'fontSize': 9}],
            'visualHeader': [{'foreground': solid(MIST), 'background': solid(SURFACE), 'border': solid(LINE)}],
            'visualTooltip': [{'titleFontColor': solid(MIST), 'valueFontColor': solid(BONE), 'background': solid(RAISED)}],
        }},
        'page': {'*': {
            'background': [{'color': solid(INK), 'transparency': 0}],
            'outspace': [{'color': solid(INK), 'transparency': 0}],
        }},
        'cardVisual': {'*': {
            'value': [{'$id': 'default', 'fontColor': solid(BONE), 'fontSize': 22}],
            'label': [{'$id': 'default', 'fontColor': solid(MIST), 'fontSize': 10, 'position': 'aboveValue'}],
            'outline': [{'$id': 'default', 'show': False}],
            'borderCustom': [{'$id': 'default', 'show': False}],
        }},
        'tableEx': {'*': {
            'columnHeaders': [{'fontColor': solid(MIST), 'fontSize': 9}],
            'values': [{'fontColorPrimary': solid(BONE), 'fontColorSecondary': solid(BONE), 'fontSize': 9}],
            'total': [{'fontColor': solid(BONE)}],
            'grid': [{'gridHorizontal': True, 'gridHorizontalColor': solid(LINE), 'outlineColor': solid(LINE), 'rowPadding': 3}],
        }},
        'pivotTable': {'*': {
            'columnHeaders': [{'fontColor': solid(MIST), 'fontSize': 9}],
            'rowHeaders': [{'fontColor': solid(BONE), 'fontSize': 9}],
            'values': [{'fontColorPrimary': solid(BONE), 'fontColorSecondary': solid(BONE), 'fontSize': 9}],
            'grid': [{'gridHorizontal': True, 'gridHorizontalColor': solid(LINE), 'outlineColor': solid(LINE), 'rowPadding': 3}],
        }},
        'slicer': {'*': {
            'background': [{'show': True, 'color': solid(SURFACE), 'transparency': 0}],
            'border': [{'show': True, 'color': solid(LINE), 'radius': 10}],
            'padding': [{'left': 12, 'top': 8, 'right': 12, 'bottom': 8}],
            'header': [{'show': False}],
            'title': [{'show': True, 'fontColor': solid(MIST), 'fontSize': 10, 'fontFamily': 'Segoe UI'}],
            'items': [{'fontColor': solid(BONE), 'background': solid(RAISED), 'textSize': 10}],
            'dropdown': [{'background': solid(RAISED)}],
        }},
        'textbox': {'*': {
            'background': [{'show': False}],
            'border': [{'show': False}],
        }},
        'pageNavigator': {'*': {
            'title': [{'show': False}],
            'background': [{'show': False}],
            'border': [{'show': False}],
            'padding': [{'left': 0, 'top': 0, 'right': 0, 'bottom': 0}],
            'text': [{'fontSize': 9, 'fontColor': solid(MIST)}],
            'fill': [{'fillColor': solid(SURFACE)}],
        }},
    },
}


# ---------- small builders ----------

def lit(value):
    """A literal in Power BI's expression format."""
    if isinstance(value, bool):
        text = 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        text = f'{value}D'
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': text}}}


def color(hex_code):
    return {'solid': {'color': lit(hex_code)}}


def measure(name):
    return {'Measure': {'Expression': {'SourceRef': {'Entity': 'Metrics'}}, 'Property': name}}


def column(table, name):
    return {'Column': {'Expression': {'SourceRef': {'Entity': table}}, 'Property': name}}


def field_ref(field):
    kind = 'Measure' if 'Measure' in field else 'Column'
    return f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"


def proj(field, label=None):
    p = {'field': field, 'queryRef': field_ref(field), 'nativeQueryRef': label or field_ref(field).split('.', 1)[1]}
    if label:
        p['displayName'] = label
    return p


def sort_by(field, descending=True):
    return {'sort': [{'field': field, 'direction': 'Descending' if descending else 'Ascending'}], 'isDefaultSort': False}


def top_n(table, col, by_measure, n):
    """Visual filter: keep the top n values of a column by a measure."""
    return {
        'name': f'top_{n}_{col}'.replace(' ', '_').lower(),
        'field': column(table, col),
        'type': 'TopN',
        'filter': {
            'Version': 2,
            'From': [
                {'Name': 'subquery', 'Type': 2, 'Expression': {'Subquery': {'Query': {
                    'Version': 2,
                    'From': [{'Name': 't', 'Entity': table, 'Type': 0}, {'Name': 'm', 'Entity': 'Metrics', 'Type': 0}],
                    'Select': [{'Column': {'Expression': {'SourceRef': {'Source': 't'}}, 'Property': col}, 'Name': 'field'}],
                    'OrderBy': [{'Direction': 2, 'Expression': {'Measure': {
                        'Expression': {'SourceRef': {'Source': 'm'}}, 'Property': by_measure}}}],
                    'Top': n,
                }}}},
                {'Name': 't', 'Entity': table, 'Type': 0},
            ],
            'Where': [{'Condition': {'In': {
                'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 't'}}, 'Property': col}}],
                'Table': {'SourceRef': {'Source': 'subquery'}},
            }}}],
        },
    }


def measure_above_zero(name):
    """Visual filter: only rows where the measure is greater than zero."""
    return {
        'name': 'positive_' + name.replace(' ', '_').lower(),
        'field': measure(name),
        'type': 'Advanced',
        'filter': {
            'Version': 2,
            'From': [{'Name': 'm', 'Entity': 'Metrics', 'Type': 0}],
            'Where': [{'Condition': {'Comparison': {
                'ComparisonKind': 1,
                'Left': {'Measure': {'Expression': {'SourceRef': {'Source': 'm'}}, 'Property': name}},
                'Right': {'Literal': {'Value': '0D'}},
            }}}],
        },
    }


class Page:
    def __init__(self, name, display_name):
        self.name = name
        self.display_name = display_name
        self.visuals = []

    def add(self, name, visual_type, x, y, w, h, roles=None, title=None, objects=None,
            container=None, sort=None, filters=None):
        visual = {'visualType': visual_type, 'drillFilterOtherVisuals': True}
        if roles:
            visual['query'] = {'queryState': {role: {'projections': items} for role, items in roles.items()}}
            if sort:
                visual['query']['sortDefinition'] = sort
        if objects:
            visual['objects'] = objects
        vco = dict(container or {})
        if title:
            vco.setdefault('title', [{'properties': {'show': lit(True), 'text': lit(title)}}])
        if vco:
            visual['visualContainerObjects'] = vco
        body = {
            '$schema': VISUAL_SCHEMA,
            'name': name,
            'position': {'x': x, 'y': y, 'z': len(self.visuals) * 1000, 'height': h, 'width': w,
                         'tabOrder': len(self.visuals) * 1000},
            'visual': visual,
        }
        if filters:
            body['filterConfig'] = {'filters': filters}
        self.visuals.append(body)

    # common pieces

    def header(self, title, subtitle):
        self.add(f'{self.name}_header', 'textbox', M, 6, 690, 76, objects=text_objects([
            paragraph(run(title, size=18, bold=True)),
            paragraph(run(subtitle, size=10, color=MIST)),
        ]))
        self.add(f'{self.name}_nav', 'pageNavigator', 730, 18, PAGE_W - 730 - M, 44)

    def footer(self, text):
        self.add(f'{self.name}_footer', 'textbox', M, PAGE_H - 42, PAGE_W - 2 * M, 42,
                 objects=text_objects([paragraph(run(text, size=8, color=MIST))]))

    def card(self, name, x, y, w, h, measure_name, label):
        self.add(name, 'cardVisual', x, y, w, h, roles={'Data': [proj(measure(measure_name), label)]},
                 container={'title': [{'properties': {'show': lit(False)}}]})

    def cards(self, prefix, y, h, items):
        w = (PAGE_W - 2 * M - G * (len(items) - 1)) / len(items)
        for i, (measure_name, label) in enumerate(items):
            self.card(f'{prefix}_{i + 1}', round(M + i * (w + G)), y, round(w), h, measure_name, label)


def run(text, size=11, bold=False, color=BONE, url=None):
    style = {'fontSize': f'{size}pt', 'color': color,
             'fontFamily': 'Segoe UI Semibold' if bold else 'Segoe UI'}
    if bold:
        style['fontWeight'] = 'bold'
    r = {'value': text, 'textStyle': style}
    if url:
        r['url'] = url
    return r


def paragraph(*runs):
    return {'textRuns': list(runs)}


def text_objects(paragraphs):
    return {'general': [{'properties': {'paragraphs': paragraphs}}]}


def bar_color(hex_code):
    return {'dataPoint': [{'properties': {'fill': color(hex_code)}}]}


def series_colors(mapping):
    return {'dataPoint': [{'properties': {'fill': color(c)}, 'selector': {'metadata': f'Metrics.{m}'}}
                          for m, c in mapping.items()]}


def tile_slicer(single_select=True, default=None):
    """Horizontal tiles. default: (table, column, value) to preselect."""
    general = {'orientation': lit(1)}
    if default:
        table, col, value = default
        general['filter'] = {'filter': {
            'Version': 2,
            'From': [{'Name': 's', 'Entity': table, 'Type': 0}],
            'Where': [{'Condition': {'In': {
                'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 's'}}, 'Property': col}}],
                'Values': [[{'Literal': {'Value': f'{value}D'}}]],
            }}}],
        }}
    return {
        'data': [{'properties': {'mode': lit('Basic')}}],
        'general': [{'properties': general}],
        'selection': [{'properties': {'singleSelect': lit(single_select), 'strictSingleSelect': lit(single_select)}}],
    }


def dropdown_slicer():
    return {'data': [{'properties': {'mode': lit('Dropdown')}}]}


SOURCE_NOTE = ('Simulated inventory based on real demand  ·  Olist Brazilian ecommerce orders, Jan 2017 to Jul 2018  ·  '
               'values at cost in Brazilian reais (R$)  ·  as of 31 July 2018')


# ---------- pages ----------

def summary_page():
    p = Page('summary', 'Summary')
    p.header('Which stock is about to become a loss?', 'Executive summary  ·  stock on hand, what is at risk, and what aged stock already cost')
    p.add('summary_headline', 'cardVisual', M, 84, PAGE_W - 2 * M, 60,
          roles={'Data': [proj(measure('Headline'), 'So what')]},
          objects={'value': [{'properties': {'fontSize': lit(15), 'fontColor': color(AMBER)}, 'selector': {'id': 'default'}}],
                   'label': [{'properties': {'show': lit(False)}, 'selector': {'id': 'default'}}]},
          container={'title': [{'properties': {'show': lit(False)}}]})
    p.cards('summary_kpi', 160, 92, [
        ('Stock Value Card', 'Stock on hand'),
        ('Value at Risk', 'Value at risk'),
        ('Value at Risk %', 'Share of stock at risk'),
        ('Over 180 Days %', 'Older than 180 days'),
        ('Days of Inventory', 'Days of inventory'),
        ('Write Off Loss 12M', 'Write offs, 12 months'),
    ])
    top = 268
    bottom = PAGE_H - 46
    left_w = 752
    right_x = M + left_w + G
    right_w = PAGE_W - M - right_x
    upper = round((bottom - top - G) * 0.58)
    lower = bottom - top - G - upper
    p.add('summary_trend', 'lineChart', M, top, left_w, bottom - top,
          roles={'Category': [proj(column('Date', 'Year Month'))],
                 'Y': [proj(measure('Stock Value'), 'Stock on hand'), proj(measure('Value at Risk'), 'Value at risk')]},
          title='Stock on hand and value at risk, month end',
          objects=series_colors({'Stock Value': TEAL, 'Value at Risk': AMBER}),
          sort=sort_by(column('Date', 'Year Month'), descending=False))
    p.add('summary_top_categories', 'clusteredBarChart', right_x, top, right_w, upper,
          roles={'Category': [proj(column('Product', 'Category'))], 'Y': [proj(measure('Value at Risk'), 'Value at risk')]},
          title='Top 5 categories by value at risk', objects=bar_color(AMBER),
          sort=sort_by(measure('Value at Risk')), filters=[top_n('Product', 'Category', 'Value at Risk', 5)])
    p.add('summary_age', 'clusteredColumnChart', right_x, top + upper + G, right_w, lower,
          roles={'Category': [proj(column('Aging Bucket', 'Aging Bucket'))], 'Y': [proj(measure('Stock Value'), 'Stock on hand')]},
          title='Stock on hand by age', objects=bar_color(TEAL),
          sort=sort_by(column('Aging Bucket', 'Aging Bucket'), descending=False))
    p.footer(SOURCE_NOTE)
    return p


def aging_page():
    p = Page('aging', 'Aging')
    p.header('Aging deep dive', 'Where old stock sits, by category, price band and region. Drill down to the SKU.')
    slicers = [('Product', 'Category'), ('Product', 'Price Band'), ('Seller', 'Region')]
    for i, (table, col) in enumerate(slicers):
        p.add(f'aging_slicer_{i + 1}', 'slicer', M + i * (300 + G), 84, 300, 64,
              roles={'Values': [proj(column(table, col))]}, title=col, objects=dropdown_slicer())
    p.cards('aging_kpi', 164, 84, [
        ('Stock Value Card', 'Stock on hand'),
        ('Average Stock Age', 'Average age, days'),
        ('Over 90 Days %', 'Older than 90 days'),
        ('Over 180 Days %', 'Older than 180 days'),
        ('Sell Through 90D', 'Sell through, 90 days'),
    ])
    top = 264
    bottom = PAGE_H - 46
    left_w = 400
    right_x = M + left_w + G
    right_w = PAGE_W - M - right_x
    p.add('aging_waterfall', 'waterfallChart', M, top, left_w, bottom - top,
          roles={'Category': [proj(column('Aging Bucket', 'Aging Bucket'))], 'Y': [proj(measure('Stock Value'), 'Stock on hand')]},
          title='How stock on hand builds up by age',
          objects={'sentimentColors': [{'properties': {'increaseFill': color(TEAL), 'decreaseFill': color(AMBER_DEEP),
                                                       'totalFill': color(AMBER)}}],
                   'legend': [{'properties': {'show': lit(False)}}]},
          sort=sort_by(column('Aging Bucket', 'Aging Bucket'), descending=False))
    heat_h = 210
    p.add('aging_heatmap', 'pivotTable', right_x, top, right_w, heat_h,
          roles={'Rows': [proj(column('Product', 'Category'))],
                 'Columns': [proj(column('Aging Bucket', 'Aging Bucket'))],
                 'Values': [proj(measure('Stock Value'), 'Stock on hand')]},
          title='Heat map: stock on hand by category and age',
          sort=sort_by(measure('Stock Value')),
          objects={'values': [{
              'properties': {'backColor': {'solid': {'color': {'expr': {'FillRule': {
                  'Input': measure('Stock Value'),
                  'FillRule': {'linearGradient2': {
                      'min': {'color': {'Literal': {'Value': f"'{SURFACE}'"}}},
                      'max': {'color': {'Literal': {'Value': f"'{AMBER_DEEP}'"}}},
                      'nullColoringStrategy': {'strategy': {'Literal': {'Value': "'asZero'"}}},
                  }},
              }}}}}},
              'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}], 'metadata': 'Metrics.Stock Value'},
          }]})
    p.add('aging_sku_table', 'tableEx', right_x, top + heat_h + G, right_w, bottom - top - heat_h - G,
          roles={'Values': [
              proj(column('SKU', 'SKU')), proj(column('SKU', 'Category')), proj(column('SKU', 'Seller')),
              proj(measure('Stock Units'), 'Units'), proj(measure('Stock Value'), 'Stock on hand'),
              proj(measure('Average Stock Age'), 'Average age'), proj(measure('Weeks of Cover'), 'Weeks of cover'),
              proj(measure('Value at Risk'), 'Value at risk')]},
          title='SKUs holding stock, largest value at risk first',
          sort=sort_by(measure('Value at Risk')), filters=[measure_above_zero('Stock Value')])
    p.footer(SOURCE_NOTE)
    return p


def liquidation_page():
    p = Page('liquidation', 'Liquidation')
    p.header('Liquidation planner', 'Mark down stock at risk now, or clear it later? Choose a markdown and see what it saves.')
    md_w = 760
    p.add('liquidation_markdown', 'slicer', M, 84, md_w, 68,
          roles={'Values': [proj(column('Markdown', 'Markdown'), 'Markdown')]},
          title='Markdown on stock at risk',
          objects=tile_slicer(default=('Markdown', 'Markdown', 0.3)))
    p.add('liquidation_response', 'slicer', M + md_w + G, 84, PAGE_W - 2 * M - md_w - G, 68,
          roles={'Values': [proj(column('Clearance Response', 'Clearance Response'), 'Clearance response')]},
          title='Stock cleared per 10 points of markdown',
          objects=tile_slicer(default=('Clearance Response', 'Clearance Response', 0.15)))
    p.cards('liquidation_kpi', 168, 88, [
        ('Projected Loss No Action', 'Loss if we wait and clear later'),
        ('Projected Loss With Markdown', 'Loss with this markdown'),
        ('Value Saved by Markdown', 'Saved by acting now'),
        ('Markdown Sell Through', 'At risk units it clears'),
        ('Suggested Markdown', 'Best single markdown'),
    ])
    top = 272
    bottom = PAGE_H - 46
    left_w = 470
    right_x = M + left_w + G
    right_w = PAGE_W - M - right_x
    p.add('liquidation_by_category', 'clusteredBarChart', M, top, left_w, bottom - top,
          roles={'Category': [proj(column('Product', 'Category'))],
                 'Y': [proj(measure('Projected Loss No Action'), 'Wait and clear later'),
                       proj(measure('Projected Loss With Markdown'), 'Mark down now')]},
          title='Projected loss by category: wait or mark down',
          objects=series_colors({'Projected Loss No Action': AMBER, 'Projected Loss With Markdown': TEAL}),
          sort=sort_by(measure('Projected Loss No Action')),
          filters=[top_n('Product', 'Category', 'Projected Loss No Action', 10)])
    p.add('liquidation_actions', 'tableEx', right_x, top, right_w, bottom - top,
          roles={'Values': [
              proj(column('SKU', 'SKU')), proj(column('SKU', 'Category')), proj(column('SKU', 'Seller')),
              proj(measure('Units at Risk'), 'Units at risk'), proj(measure('Value at Risk'), 'Value at risk'),
              proj(measure('Suggested Markdown'), 'Suggested markdown'),
              proj(measure('Value Saved at Suggested Markdown'), 'Saved')]},
          title='Action list: SKUs ranked by what their best markdown saves',
          sort=sort_by(measure('Value Saved at Suggested Markdown')), filters=[measure_above_zero('Value at Risk')])
    p.footer('Marked down units sell at list price less the markdown. Stock the markdown does not clear is '
             'cleared later at the historical recovery rate (about 25% of cost).  ·  as of 31 July 2018')
    return p


def sellers_page():
    p = Page('sellers', 'Sellers')
    p.header('Seller and region view', 'Where risk concentrates: a few sellers and the Southeast hold most of it.')
    p.cards('sellers_kpi', 84, 88, [
        ('Value at Risk', 'Value at risk'),
        ('Sellers at Risk Card', 'Sellers holding stock at risk'),
        ('SKUs at Risk Card', 'SKUs at risk'),
        ('Top 20 Sellers Share of Risk', 'Held by the top 20 sellers'),
    ])
    top = 188
    bottom = PAGE_H - 46
    left_w = 380
    right_x = M + left_w + G
    right_w = PAGE_W - M - right_x
    region_h = 200
    p.add('sellers_region', 'clusteredBarChart', M, top, left_w, region_h,
          roles={'Category': [proj(column('Seller', 'Region'))], 'Y': [proj(measure('Value at Risk'), 'Value at risk')]},
          title='Value at risk by seller region', objects=bar_color(AMBER), sort=sort_by(measure('Value at Risk')))
    p.add('sellers_state', 'clusteredBarChart', M, top + region_h + G, left_w, bottom - top - region_h - G,
          roles={'Category': [proj(column('Seller', 'State'))], 'Y': [proj(measure('Value at Risk'), 'Value at risk')]},
          title='Top 8 seller states by value at risk', objects=bar_color(AMBER),
          sort=sort_by(measure('Value at Risk')), filters=[top_n('Seller', 'State', 'Value at Risk', 8)])
    scatter_h = 230
    p.add('sellers_scatter', 'scatterChart', right_x, top, right_w, scatter_h,
          roles={'Category': [proj(column('Seller', 'Seller'))],
                 'X': [proj(measure('Stock Value'), 'Stock on hand')],
                 'Y': [proj(measure('Value at Risk %'), 'Share at risk')],
                 'Size': [proj(measure('Value at Risk'), 'Value at risk')]},
          title='Each seller: stock held against share at risk (bubble size: value at risk)',
          objects=bar_color(TEAL))
    p.add('sellers_table', 'tableEx', right_x, top + scatter_h + G, right_w, bottom - top - scatter_h - G,
          roles={'Values': [
              proj(column('Seller', 'Seller')), proj(column('Seller', 'State')), proj(column('Seller', 'Region')),
              proj(measure('SKUs in Stock'), 'SKUs in stock'), proj(measure('SKUs at Risk'), 'SKUs at risk'),
              proj(measure('Stock Value'), 'Stock on hand'), proj(measure('Value at Risk'), 'Value at risk'),
              proj(measure('Value at Risk %'), 'Share at risk')]},
          title='Sellers ranked by value at risk',
          sort=sort_by(measure('Value at Risk')), filters=[measure_above_zero('Value at Risk')])
    p.footer(SOURCE_NOTE)
    return p


def about_page():
    p = Page('about', 'About')
    p.header('About this project', 'How the data was built, how risk is measured, and who made it.')
    col_w = (PAGE_W - 2 * M - 2 * G) // 3
    sections = [
        [
            ('The question', [
                'Which stock is about to become a loss, how much money is at risk, and what should we do this week?',
                'This dashboard recreates, on public data, the aging inventory analysis I ran as a BI leader in '
                'online retail, where acting early on old stock protected real money.',
            ]),
            ('The data', [
                'Demand is real: 104,884 order lines from the Olist Brazilian ecommerce dataset (public, on Kaggle), '
                'January 2017 to July 2018.',
                'Inventory is simulated. Olist publishes no stock data, so purchases, batches and month end stock were '
                'rebuilt from the real sales by a documented, seeded Python script.',
            ]),
        ],
        [
            ('How stock was simulated', [
                'Each SKU (one product sold by one seller) gets purchase batches timed to meet its real sales.',
                'Buyers reorder at a reorder point. Their forecasts carry a bias, and 15% of sellers habitually over order.',
                'Sales use stock first in, first out. Batches still unsold after 270 days are cleared for 10% to 40% of cost.',
            ]),
            ('How value at risk is measured', [
                "Each SKU's last 90 days of sales set its pace. Units sell first in, first out at that pace.",
                'A unit is at risk if it would be older than 180 days by the time it sells. '
                'A SKU with no sales in 90 days has all of its stock at risk.',
            ]),
        ],
        [
            ('The liquidation planner', [
                'Marked down units sell at list price less the markdown. The clearance response sets how much stock '
                'at risk each 10 points of markdown clears within 90 days.',
                'Whatever is left is cleared later at the historical recovery rate. The suggested markdown is the step '
                'that recovers the most for each SKU.',
            ]),
            ('Built with', [
                'Python and pandas for the data. Power BI with a star schema, 52 DAX measures and what if parameters, '
                'saved as a Power BI project so every table, measure and page is plain text under version control.',
            ]),
            ('Author', [
                'Syed Nabil Kabir  ·  Business Intelligence leader',
            ]),
        ],
    ]
    top = 96
    for i, blocks in enumerate(sections):
        paragraphs = []
        for heading, lines in blocks:
            if paragraphs:
                paragraphs.append(paragraph(run(' ', size=6)))
            paragraphs.append(paragraph(run(heading, size=13, bold=True, color=AMBER)))
            for line in lines:
                paragraphs.append(paragraph(run(line, size=10.5)))
        if i == 2:
            paragraphs.append(paragraph(run('nabil-kabir.github.io', size=10.5, color=TEAL_GLOW,
                                            url='https://nabil-kabir.github.io')))
        p.add(f'about_text_{i + 1}', 'textbox', M + i * (col_w + G), top, col_w, PAGE_H - top - 56,
              objects=text_objects(paragraphs),
              container={'background': [{'properties': {'show': lit(True), 'color': color(SURFACE)}}],
                         'border': [{'properties': {'show': lit(True), 'color': color(LINE), 'radius': lit(10)}}],
                         'padding': [{'properties': {'left': lit(18), 'top': lit(16), 'right': lit(18), 'bottom': lit(16)}}]})
    p.footer(SOURCE_NOTE)
    return p


# ---------- write ----------

def desktop_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq PBIDesktop.exe'], capture_output=True, text=True).stdout
        return 'PBIDesktop.exe' in out
    except OSError:
        return False


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def register_theme():
    report_path = DEFINITION / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    base = report['themeCollection']['baseTheme']
    report['themeCollection']['customTheme'] = {
        'name': THEME_NAME,
        'reportVersionAtImport': base['reportVersionAtImport'],
        'type': 'RegisteredResources',
    }
    packages = [p for p in report.get('resourcePackages', []) if p['name'] != 'RegisteredResources']
    packages.append({'name': 'RegisteredResources', 'type': 'RegisteredResources',
                     'items': [{'name': THEME_NAME, 'path': THEME_NAME, 'type': 'CustomTheme'}]})
    report['resourcePackages'] = packages
    write_json(report_path, report)
    write_json(REPORT / 'StaticResources' / 'RegisteredResources' / THEME_NAME, THEME)


def main():
    if desktop_running():
        sys.exit('Power BI Desktop is open. Save, close it, then run this again.')

    pages = [summary_page(), aging_page(), liquidation_page(), sellers_page(), about_page()]

    register_theme()
    pages_dir = DEFINITION / 'pages'
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    for page in pages:
        write_json(pages_dir / page.name / 'page.json', {
            '$schema': PAGE_SCHEMA, 'name': page.name, 'displayName': page.display_name,
            'displayOption': 'FitToPage', 'height': PAGE_H, 'width': PAGE_W,
        })
        for v in page.visuals:
            write_json(pages_dir / page.name / 'visuals' / v['name'] / 'visual.json', v)
        print(f'  {page.display_name:<12} {len(page.visuals)} visuals')
    write_json(pages_dir / 'pages.json', {
        '$schema': PAGES_SCHEMA, 'pageOrder': [p.name for p in pages], 'activePageName': pages[0].name,
    })
    print(f'Wrote theme and {len(pages)} pages to {REPORT.name}')


if __name__ == '__main__':
    main()
