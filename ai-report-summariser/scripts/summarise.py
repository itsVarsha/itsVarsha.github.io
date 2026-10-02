"""
Solution showcase 3: AI report summariser (rules and templates, no paid APIs).

For each month it computes a set of KPIs, runs a list of rules that each
produce a candidate sentence with a "materiality" score in AED, keeps the most
material ones, and assembles a plain-English narrative from templates.
Deterministic: the same data always gives the same text, and every sentence
can be traced back to a number.

Usage: python summarise.py <data_folder> <output_folder>
Writes: data.js (charts and narratives), results.json, narratives/<yyyy-mm>.md
All data is synthetic. Tidewell Distribution LLC is an invented company modelled on a UAE distributor.
"""
import sys, os, json
import pandas as pd
import numpy as np

DATA, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("data", ".")
rd = lambda f, **k: pd.read_csv(os.path.join(DATA, f), **k)
meta = json.load(open(os.path.join(DATA, "meta.json")))
products = rd("products.csv"); cust = rd("customers.csv")
sl = rd("sales_lines.csv", parse_dates=["invoice_date"]).merge(products[["sku", "category"]], on="sku")
inv = rd("invoices.csv", parse_dates=["invoice_date", "due_date", "paid_date"])
bank = rd("bank_transactions.csv", parse_dates=["txn_date"])
sl["month"] = sl.invoice_date.dt.to_period("M")
names = cust.set_index("customer_id").customer_name
MONTHS = pd.period_range("2024-10", "2026-09", freq="M")

def aed(v):
    v = abs(v)
    return f"AED {v/1e6:.2f}M" if v >= 1e6 else f"AED {v/1e3:.0f}K" if v >= 1e4 else f"AED {v:,.0f}"
def pct(a, b): return (a / b - 1) * 100 if b else 0.0
def verb(p, up="rose", down="fell", flat="was broadly flat", tol=1.0):
    return flat if abs(p) < tol else up if p > 0 else down

# ---------------- monthly KPI table
k = sl.groupby("month").agg(net=("net_amount", "sum"), cost=("cost_amount", "sum"), invoices=("invoice_no", "nunique"))
k["gm"] = (1 - k.cost / k.net) * 100
cat = sl.groupby(["month", "category"]).agg(net=("net_amount", "sum"), cost=("cost_amount", "sum"))
cat["gm"] = (1 - cat.cost / cat.net) * 100
br = sl.groupby(["month", "branch"]).net_amount.sum().unstack()
cm = sl.groupby(["month", "customer_id"]).net_amount.sum().unstack(fill_value=0)
def ar_stats(me):
    o = inv[(inv.invoice_date <= me) & (inv.paid_date.isna() | (inv.paid_date > me))]
    od = (me - o.due_date).dt.days
    s90 = inv[(inv.invoice_date > me - pd.Timedelta(days=90)) & (inv.invoice_date <= me)].amount_incl_vat.sum()
    return o.amount_incl_vat.sum(), o[od > 0].amount_incl_vat.sum(), o[od > 0].amount_incl_vat.sum() / max(o.amount_incl_vat.sum(), 1) * 100, o.amount_incl_vat.sum() / s90 * 90
ar = pd.DataFrame([ar_stats(m.to_timestamp(how="end").normalize()) for m in MONTHS], index=MONTHS, columns=["ar", "overdue", "overdue_pct", "dso"])
bank["month"] = bank.txn_date.dt.to_period("M")
flow = bank.groupby("month").amount.sum().reindex(MONTHS, fill_value=0)
cash = meta["opening_cash_aed"] + flow.cumsum()

# ---------------- rules: each returns (materiality_in_AED, sentence) or None
def rules(m):
    p, y = m - 1, m - 12
    out = []
    # 1. headline sales vs last month and last year (always included, scored high)
    mom, yoy = pct(k.net[m], k.net[p]), (pct(k.net[m], k.net[y]) if y in k.index else None)
    s = f"Net sales {verb(mom, flat='were broadly flat')} {'at' if abs(mom) < 1 else 'to'} {aed(k.net[m])} in {m.strftime('%B %Y')}, {mom:+.1f}% on {p.strftime('%B')}"
    s += f" and {yoy:+.1f}% on {y.strftime('%B %Y')}." if yoy is not None else "."
    out.append((1e12, s, "headline"))
    # 2. seasonality context, so a seasonal swing is not misread
    if y in k.index and abs(mom) >= 8 and np.sign(pct(k.net[y], k.net[y - 1])) == np.sign(mom):
        out.append((5e5, f"A similar {'rise' if mom > 0 else 'drop'} happened in the same month last year ({pct(k.net[y], k.net[y-1]):+.1f}%), so part of this movement is seasonal.", "context"))
    # 3. category drivers: biggest absolute contributors to the change
    d = (cat.net.xs(m, level="month") - cat.net.xs(p, level="month")).sort_values()
    top, bot = d.index[-1], d.index[0]
    if d.iloc[-1] > 15000: out.append((d.iloc[-1], f"{top} added the most, up {aed(d.iloc[-1])} on the previous month.", "driver"))
    if d.iloc[0] < -15000: out.append((-d.iloc[0], f"{bot} was the largest drag, down {aed(d.iloc[0])}.", "driver"))
    # 4. gross margin movement (overall and the category behind it)
    gmd = k.gm[m] - k.gm[p]
    if abs(gmd) >= 0.3:
        cg = (cat.gm.xs(m, level="month") - cat.gm.xs(p, level="month")) * cat.net.xs(m, level="month")
        who = cg.idxmin() if gmd < 0 else cg.idxmax()
        out.append((abs(gmd) / 100 * k.net[m] * 3, f"Gross margin {'improved' if gmd > 0 else 'slipped'} to {k.gm[m]:.1f}% ({gmd:+.1f} points), mainly in {who}, where margin moved {cat.gm[(m, who)] - cat.gm[(p, who)]:+.1f} points.", "margin"))
    # 5. branch with an unusual move
    bd = br.loc[m] / br.loc[p] - 1
    w = bd.abs().idxmax()
    if abs(bd[w]) >= 0.10:
        out.append((abs(br.loc[m, w] - br.loc[p, w]), f"{w} stood out, {'up' if bd[w] > 0 else 'down'} {abs(bd[w])*100:.0f}% month on month.", "branch"))
    # 6. customers: lost regulars and biggest single swing
    regulars = cm.loc[[p - 2, p - 1, p]].gt(0).all() if (p - 2) in cm.index else cm.loc[p].gt(0)
    lost = cm.columns[regulars & cm.loc[m].eq(0)]
    if len(lost) >= 3:
        val = cm.loc[[p - 2, p - 1, p], lost].mean().sum() if (p - 2) in cm.index else cm.loc[p, lost].sum()
        out.append((val, f"{len(lost)} customers who ordered in each of the previous three months did not order this month (usually worth about {aed(val)} a month). Worth a call from the sales team.", "customers"))
    sw = (cm.loc[m] - cm.loc[p]); c_up, c_dn = sw.idxmax(), sw.idxmin()
    if sw[c_dn] < -25000: out.append((-sw[c_dn], f"The biggest single drop was {names[c_dn]}, down {aed(sw[c_dn])}.", "customers"))
    if sw[c_up] > 25000: out.append((sw[c_up] * 0.8, f"{names[c_up]} grew the most, up {aed(sw[c_up])}.", "customers"))
    # 7. receivables and DSO
    dd = ar.dso[m] - ar.dso[p]
    if abs(dd) >= 2 or ar.overdue_pct[m] >= 25:
        out.append((abs(ar.overdue[m] - ar.overdue[p]) + 1e5, f"Receivables: DSO {'lengthened' if dd > 0 else 'shortened'} to {ar.dso[m]:.0f} days ({dd:+.0f}), with {ar.overdue_pct[m]:.0f}% of open receivables ({aed(ar.overdue[m])}) past due.", "receivables"))
    # 8. cash
    if flow[m] < -150000 or cash[m] < 400000:
        out.append((abs(flow[m]), f"Cash: the bank balance {'fell' if flow[m] < 0 else 'rose'} by {aed(flow[m])} to {aed(cash[m])} at month end. Check the next month's supplier payments against expected collections.", "cash"))
    elif flow[m] > 250000:
        out.append((flow[m] * 0.5, f"Cash: the bank balance rose by {aed(flow[m])} to {aed(cash[m])}.", "cash"))
    return out

def narrative(m, max_points=5):
    cand = sorted(rules(m), key=lambda x: -x[0])
    head = cand[0][1]
    ctx = [c[1] for c in cand if c[2] == "context"]
    body = [c for c in cand[1:] if c[2] != "context"][:max_points - 1]
    watch = [c[1] for c in body if c[2] in ("customers", "receivables", "cash")]
    expl = [c[1] for c in body if c[2] not in ("customers", "receivables", "cash")]
    para1 = " ".join([head] + ctx + expl)
    return {"month": m.strftime("%B %Y"), "key": str(m), "summary": para1, "watch": watch,
            "rules_fired": len(cand), "kpis": {"net_sales": round(k.net[m]), "gm_pct": round(k.gm[m], 1), "dso": round(ar.dso[m], 1),
            "overdue_pct": round(ar.overdue_pct[m], 1), "cash": round(cash[m])}}

nar = [narrative(m) for m in MONTHS[12:]]       # Oct 2025 to Sep 2026 (needs a year of history for comparisons)
os.makedirs(os.path.join(OUT, "narratives"), exist_ok=True)
for n in nar:
    md = f"# Tidewell Distribution LLC: {n['month']} summary\n\n{n['summary']}\n\n" + ("## Watch list\n\n" + "\n".join(f"- {w}" for w in n["watch"]) + "\n" if n["watch"] else "")
    open(os.path.join(OUT, "narratives", f"{n['key']}.md"), "w").write(md + "\n_Generated automatically from synthetic data by summarise.py. No figures were written by hand._\n")
results = {"months_summarised": len(nar), "rules": 8, "avg_rules_fired": round(float(np.mean([n["rules_fired"] for n in nar])), 1),
           "sales_lines": int(len(sl)), "invoices": int(len(inv)), "bank_rows": int(len(bank)),
           "best_month": max(nar, key=lambda n: n["kpis"]["net_sales"])["month"], "weakest_month": min(nar, key=lambda n: n["kpis"]["net_sales"])["month"]}
json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=2)
data = {"results": results, "narratives": nar,
        "chart": {"labels": [m.strftime("%b %y") for m in MONTHS], "net": [round(v) for v in k.net], "gm": [round(v, 2) for v in k.gm],
                  "dso": [round(v, 1) for v in ar.dso]}}
open(os.path.join(OUT, "data.js"), "w").write("window.PROJECT_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
for n in nar: print(n["month"], "|", n["summary"], "| WATCH:", " ".join(n["watch"]), "\n")
print(json.dumps(results, indent=2))
