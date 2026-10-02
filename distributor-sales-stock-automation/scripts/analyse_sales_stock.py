"""
Solution showcase 1: distributor sales and stock automation.
Reads the synthetic CSVs (see shared/generate_data.py), computes every metric
shown on the case-study page, writes data.js for the charts, results.json, and
renders the example weekly email (example-weekly-email.html).

Usage: python analyse_sales_stock.py <data_folder> <output_folder>
All data is synthetic. Tidewell Distribution LLC is an invented company modelled on a UAE distributor.
"""
import sys, os, json, html
import pandas as pd
import numpy as np

DATA, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("data", ".")
SNAP = pd.Timestamp("2026-09-30")
rd = lambda f, **k: pd.read_csv(os.path.join(DATA, f), **k)
products = rd("products.csv"); customers = rd("customers.csv")
sl = rd("sales_lines.csv", parse_dates=["invoice_date"])
lots = rd("stock_lots_snapshot.csv", parse_dates=["receipt_date"])
po = rd("open_purchase_orders.csv", parse_dates=["expected_date"])
rs = rd("reorder_settings.csv")
sl = sl.merge(products[["sku", "category", "product_name"]], on="sku")

# ---------------- sales KPIs
l12 = sl[sl.invoice_date > SNAP - pd.DateOffset(months=12)]
p12 = sl[(sl.invoice_date <= SNAP - pd.DateOffset(months=12)) & (sl.invoice_date > SNAP - pd.DateOffset(months=24))]
net12, netp12 = l12.net_amount.sum(), p12.net_amount.sum()
gm12 = 1 - l12.cost_amount.sum() / net12

daily = sl.groupby("invoice_date")["net_amount"].sum().reindex(pd.date_range(SNAP - pd.Timedelta(days=89), SNAP), fill_value=0)
ma7 = sl.groupby("invoice_date")["net_amount"].sum().rolling(7).mean().reindex(daily.index)
monthly = sl.groupby([sl.invoice_date.dt.to_period("M"), "category"])["net_amount"].sum().unstack(fill_value=0)
mtot = monthly.sum(axis=1)

# ---------------- stock
lots["age_days"] = (SNAP - lots.receipt_date).dt.days
lots["value"] = lots.qty_on_hand * lots.unit_cost
bins = [-1, 30, 60, 90, 180, 10000]; labels = ["0 to 30 days", "31 to 60 days", "61 to 90 days", "91 to 180 days", "Over 180 days"]
lots["bucket"] = pd.cut(lots.age_days, bins, labels=labels)
ageing = lots.pivot_table(index="bucket", columns="branch", values="value", aggfunc="sum", observed=False).fillna(0)
stock_value = lots.value.sum(); aged180 = lots[lots.age_days > 180].value.sum()

oh = lots.groupby(["sku", "branch"]).qty_on_hand.sum()
oo = po.groupby(["sku", "branch"]).qty_on_order.sum()
dem = sl[(sl.qty > 0) & (sl.invoice_date > SNAP - pd.Timedelta(days=90))].groupby(["sku", "branch"]).qty.sum() / 90
pos = rs.set_index(["sku", "branch"]).join(oh).join(oo).join(dem.rename("avg_daily")).fillna(0).reset_index()
pos["days_cover"] = np.where(pos.avg_daily > 0, pos.qty_on_hand / pos.avg_daily, np.inf)
pos = pos.merge(products[["sku", "product_name", "category", "lead_time_days"]], on="sku")
alerts = pos[(pos.qty_on_hand + pos.qty_on_order) < pos.reorder_level].copy()
alerts["suggested_qty"] = (alerts.reorder_level + alerts.reorder_qty - alerts.qty_on_hand - alerts.qty_on_order).astype(int)
alerts["risk"] = np.where(alerts.days_cover < alerts.lead_time_days, "Stock-out risk before delivery", "Reorder now")
alerts = alerts.sort_values("days_cover")
stockouts = int(((pos.qty_on_hand == 0) & (pos.avg_daily > 0)).sum())

slow = lots[lots.age_days > 180].groupby(["sku", "branch"]).agg(value=("value", "sum"), qty=("qty_on_hand", "sum"), oldest=("age_days", "max")).reset_index()
slow = slow.merge(products[["sku", "product_name", "category"]], on="sku")
sold90 = sl[(sl.invoice_date > SNAP - pd.Timedelta(days=90)) & (sl.qty > 0)].groupby(["sku", "branch"]).qty.sum()
slow = slow.join(sold90.rename("sold_90d"), on=["sku", "branch"]).fillna({"sold_90d": 0}).sort_values("value", ascending=False)

# ---------------- weekly email (Mon 21 to Sun 27 Sep 2026)
wk_end = pd.Timestamp("2026-09-27"); wk_start = wk_end - pd.Timedelta(days=6)
def window(a, b): return sl[(sl.invoice_date >= a) & (sl.invoice_date <= b)]
tw = window(wk_start, wk_end); pw = window(wk_start - pd.Timedelta(days=7), wk_end - pd.Timedelta(days=7))
ly = window(wk_start - pd.Timedelta(days=364), wk_end - pd.Timedelta(days=364))
pct = lambda a, b: (a / b - 1) * 100 if b else 0
tws, pws, lys = tw.net_amount.sum(), pw.net_amount.sum(), ly.net_amount.sum()
twm = 1 - tw.cost_amount.sum() / tws
cat_now = tw.groupby("category").net_amount.sum(); cat_prev = pw.groupby("category").net_amount.sum()
cat_chg = (cat_now - cat_prev).sort_values()
top_c = tw.groupby("customer_id").net_amount.sum().nlargest(5).rename("net").reset_index().merge(customers[["customer_id", "customer_name"]], on="customer_id")
br_now = tw.groupby("branch").net_amount.sum(); br_prev = pw.groupby("branch").net_amount.sum()

aed = lambda v: f"AED {v:,.0f}"
def arrow(v): return f'<span style="color:{"#1f7a6f" if v >= 0 else "#B5403A"};font-weight:700">{"+" if v >= 0 else ""}{v:.1f}%</span>'
def row(cells, head=False):
    tag = "th" if head else "td"
    st = 'style="text-align:left;padding:6px 8px;border-bottom:1px solid #DDE3EA;font-size:13px;' + ("background:#F4F6F9;color:#1B365D;" if head else "") + '"'
    return "<tr>" + "".join(f"<{tag} {st}>{c}</{tag}>" for c in cells) + "</tr>"
al5 = alerts.head(5)
email = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Weekly sales and stock report (example)</title><meta name="robots" content="noindex"></head>
<body style="margin:0;background:#EEF1F5;font-family:Segoe UI,Arial,sans-serif;color:#1F2937">
<div style="max-width:640px;margin:0 auto;background:#fff">
<div style="background:#E9C46A;color:#3b2f00;font-size:12px;font-weight:700;text-align:center;padding:6px">Example email</div>
<div style="padding:14px 20px;border-bottom:1px solid #DDE3EA;font-size:13px;color:#4B5563">
<div><b>From:</b> Reporting Bot (Power Automate)</div><div><b>To:</b> Management team, Tidewell Distribution LLC</div>
<div><b>Subject:</b> Weekly sales and stock report, week ending Sun 27 Sep 2026</div></div>
<div style="background:#1B365D;color:#fff;padding:18px 20px"><div style="font-size:12px;opacity:.85">Tidewell Distribution LLC</div><div style="font-size:20px;font-weight:700">Weekly sales and stock report</div><div style="font-size:13px;opacity:.85">Mon 21 Sep to Sun 27 Sep 2026. Amounts in AED, excluding VAT.</div></div>
<div style="padding:18px 20px">
<table role="presentation" style="width:100%;border-collapse:collapse"><tr>
<td style="padding:10px;background:#F4F6F9;border-radius:6px;width:33%"><div style="font-size:12px;color:#4B5563">Net sales</div><div style="font-size:18px;font-weight:700;color:#1B365D">{aed(tws)}</div><div style="font-size:12px">{arrow(pct(tws, pws))} vs last week</div></td>
<td style="width:8px"></td>
<td style="padding:10px;background:#F4F6F9;border-radius:6px;width:33%"><div style="font-size:12px;color:#4B5563">Same week last year</div><div style="font-size:18px;font-weight:700;color:#1B365D">{aed(lys)}</div><div style="font-size:12px">{arrow(pct(tws, lys))} this year</div></td>
<td style="width:8px"></td>
<td style="padding:10px;background:#F4F6F9;border-radius:6px;width:33%"><div style="font-size:12px;color:#4B5563">Gross margin</div><div style="font-size:18px;font-weight:700;color:#1B365D">{twm*100:.1f}%</div><div style="font-size:12px;color:#4B5563">{len(tw.invoice_no.unique()):,} invoices</div></td>
</tr></table>
<h2 style="font-size:15px;color:#1B365D;margin:20px 0 6px">Highlights</h2>
<ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.6">
<li>Biggest category increase: <b>{html.escape(cat_chg.index[-1])}</b> ({aed(cat_chg.iloc[-1])} vs last week).</li>
<li>Biggest category drop: <b>{html.escape(cat_chg.index[0])}</b> ({aed(cat_chg.iloc[0])} vs last week).</li>
<li><b>{len(alerts)}</b> item and branch combinations are below reorder level with no open purchase order. <b>{int((alerts.risk != "Reorder now").sum())}</b> may run out before a new delivery arrives.</li>
<li>Stock older than 180 days: <b>{aed(aged180)}</b> at cost ({aged180/stock_value*100:.1f}% of stock value).</li>
</ul>
<h2 style="font-size:15px;color:#1B365D;margin:20px 0 6px">Sales by branch</h2>
<table style="width:100%;border-collapse:collapse">{row(["Branch", "This week", "Last week", "Change"], True)}{"".join(row([b, aed(br_now.get(b, 0)), aed(br_prev.get(b, 0)), arrow(pct(br_now.get(b, 0), br_prev.get(b, 0)))]) for b in br_now.sort_values(ascending=False).index)}</table>
<h2 style="font-size:15px;color:#1B365D;margin:20px 0 6px">Top 5 customers this week</h2>
<table style="width:100%;border-collapse:collapse">{row(["Customer", "Net sales"], True)}{"".join(row([html.escape(r.customer_name), aed(r.net)]) for r in top_c.itertuples())}</table>
<h2 style="font-size:15px;color:#1B365D;margin:20px 0 6px">Reorder now (top 5 by days of cover)</h2>
<table style="width:100%;border-collapse:collapse">{row(["Item", "Branch", "On hand", "Suggested order"], True)}{"".join(row([html.escape(r.product_name), r.branch, f"{int(r.qty_on_hand):,}", f"{int(r.suggested_qty):,}"]) for r in al5.itertuples())}</table>
<p style="font-size:13px;color:#4B5563;margin-top:18px">Full detail is in the Power BI dashboard. This email was generated automatically from the same data model; no figures were typed by hand.</p>
</div>
<div style="background:#F4F6F9;padding:12px 20px;font-size:12px;color:#4B5563">Example output by Varsha Sharma.</div>
</div></body></html>"""
open(os.path.join(OUT, "example-weekly-email.html"), "w").write(email)

# ---------------- outputs
r1 = lambda v: round(float(v), 1)
results = {
    "net_sales_last_12m": round(net12), "net_sales_prior_12m": round(netp12), "growth_pct": r1(pct(net12, netp12)),
    "gross_margin_pct": r1(gm12 * 100), "stock_value": round(stock_value), "aged_180_value": round(aged180),
    "aged_180_pct": r1(aged180 / stock_value * 100), "reorder_alerts": int(len(alerts)),
    "stockout_risk": int((alerts.risk != "Reorder now").sum()), "zero_stock_lines": stockouts,
    "sku_branch_lines": int(len(pos)), "sales_lines": int(len(sl)),
    "week_sales": round(tws), "week_change_pct": r1(pct(tws, pws)), "week_yoy_pct": r1(pct(tws, lys)),
    "slow_lines": int(len(slow)), "slow_no_sales_90d": int((slow.sold_90d == 0).sum()),
}
json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=2)
cats = list(monthly.columns)
data = {
    "results": results,
    "daily": {"labels": [d.strftime("%d %b") for d in daily.index], "sales": [round(v) for v in daily], "ma7": [round(v) for v in ma7]},
    "monthly": {"labels": [p.strftime("%b %y") for p in monthly.index], "series": {c: [round(v) for v in monthly[c]] for c in cats}},
    "ageing": {"labels": labels, "series": {b: [round(v) for v in ageing[b]] for b in ageing.columns}},
    "alerts": [[r.product_name, r.branch, int(r.qty_on_hand), int(r.qty_on_order), int(r.reorder_level), (None if np.isinf(r.days_cover) else r1(r.days_cover)), int(r.suggested_qty), r.risk] for r in alerts.head(15).itertuples()],
    "slow": [[r.product_name, r.branch, int(r.qty), round(r.value), int(r.oldest), int(r.sold_90d)] for r in slow.head(10).itertuples()],
}
open(os.path.join(OUT, "data.js"), "w").write("window.PROJECT_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(json.dumps(results, indent=2))
