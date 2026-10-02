"""
Solution showcase 2: receivables and cash-flow monitor.
Computes AR ageing, overdue alerts, the DSO trend, a collections priority list
and a cash-flow view from the synthetic data, then writes data.js and results.json.

Usage: python analyse_receivables.py <data_folder> <output_folder>
All data is synthetic. Tidewell Distribution LLC is an invented company modelled on a UAE distributor.
"""
import sys, os, json
import pandas as pd
import numpy as np

DATA, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("data", ".")
SNAP = pd.Timestamp("2026-09-30")
meta = json.load(open(os.path.join(DATA, "meta.json")))
rd = lambda f, **k: pd.read_csv(os.path.join(DATA, f), **k)
cust = rd("customers.csv")
inv = rd("invoices.csv", parse_dates=["invoice_date", "due_date", "paid_date"])
bank = rd("bank_transactions.csv", parse_dates=["txn_date"])
inv_only = inv[inv.invoice_no.str.startswith("INV")]

def open_at(d):
    x = inv[(inv.invoice_date <= d) & (inv.paid_date.isna() | (inv.paid_date > d))]
    return x

# ---------------- ageing at snapshot
op = open_at(SNAP).copy()
op["days_overdue"] = (SNAP - op.due_date).dt.days
bins = [-10000, 0, 30, 60, 90, 10000]; labels = ["Not yet due", "1 to 30 days", "31 to 60 days", "61 to 90 days", "Over 90 days"]
op["bucket"] = pd.cut(op.days_overdue, bins, labels=labels)
ageing = op.groupby("bucket", observed=False).agg(amount=("amount_incl_vat", "sum"), invoices=("invoice_no", "count"))
ageing_branch = op.pivot_table(index="bucket", columns="branch", values="amount_incl_vat", aggfunc="sum", observed=False).fillna(0)
total_ar = op.amount_incl_vat.sum(); overdue = op[op.days_overdue > 0].amount_incl_vat.sum()

# ---------------- DSO trend (count-back over the last 90 days of credit sales)
dso = []
for me in pd.date_range("2025-01-31", SNAP, freq="ME"):
    bal = open_at(me).amount_incl_vat.sum()
    sales90 = inv[(inv.invoice_date > me - pd.Timedelta(days=90)) & (inv.invoice_date <= me)].amount_incl_vat.sum()
    dso.append((me.strftime("%b %y"), round(bal / sales90 * 90, 1), round(bal)))
terms = (inv_only.merge(cust[["customer_id", "credit_terms_days"]], on="customer_id")
         .assign(w=lambda x: x.credit_terms_days * x.amount_incl_vat))
weighted_terms = terms.w.sum() / terms.amount_incl_vat.sum()

# ---------------- customer view, alerts and collections priority
paid = inv_only[inv_only.paid_date.notna()].copy()
paid["delay"] = (paid.paid_date - paid.due_date).dt.days
hist = paid[paid.paid_date > SNAP - pd.Timedelta(days=365)].groupby("customer_id").delay.mean()
c = op.groupby("customer_id").agg(open_amount=("amount_incl_vat", "sum"))
c["overdue_amount"] = op[op.days_overdue > 0].groupby("customer_id").amount_incl_vat.sum()
c["overdue_60"] = op[op.days_overdue > 60].groupby("customer_id").amount_incl_vat.sum()
c["oldest_overdue_days"] = op[op.days_overdue > 0].groupby("customer_id").days_overdue.max()
c = c.fillna(0).join(cust.set_index("customer_id")[["customer_name", "credit_limit", "salesperson", "branch"]]).join(hist.rename("avg_delay_12m"))
c["over_limit"] = c.open_amount > c.credit_limit
# priority score: overdue amount, weighted up for age, for exceeding the credit limit and for a slow payment history
c["score"] = (c.overdue_amount * (1 + c.oldest_overdue_days.clip(upper=180) / 60) * np.where(c.over_limit, 1.3, 1.0)
              * (1 + c.avg_delay_12m.fillna(0).clip(lower=0, upper=60) / 120))
def action(r):
    if r.oldest_overdue_days > 365: return "Review old disputed invoices; agree a payment plan or provision"
    if r.oldest_overdue_days > 90: return "Escalate: owner call, consider credit hold"
    if r.over_limit: return "Hold new orders until payment"
    if r.oldest_overdue_days > 30: return "Call this week, send statement"
    return "Friendly reminder"
pri = c[c.overdue_amount > 0].sort_values("score", ascending=False).copy()
pri["action"] = pri.apply(action, axis=1)
alerts = c[(c.overdue_60 > 5000) | c.over_limit]

# ---------------- cash flow
bank["month"] = bank.txn_date.dt.to_period("M")
cin = bank[bank.amount > 0].groupby("month").amount.sum()
cout = -bank[bank.amount < 0].groupby("month").amount.sum()
months = pd.period_range("2024-10", "2026-09", freq="M")
cin, cout = cin.reindex(months, fill_value=0), cout.reindex(months, fill_value=0)
closing = meta["opening_cash_aed"] + (cin - cout).cumsum()
out_cat = (-bank[bank.amount < 0].groupby(["month", "category"]).amount.sum()).unstack(fill_value=0).reindex(months, fill_value=0)
# expected collections, next 8 weeks: open invoices expected on due date plus each customer's average delay (floor: tomorrow)
op2 = op[op.invoice_no.str.startswith("INV")].join(hist.rename("d"), on="customer_id")
op2["expected"] = op2.due_date + pd.to_timedelta(op2.d.fillna(10).round().astype(int), unit="D")
op2.loc[op2.expected <= SNAP, "expected"] = SNAP + pd.Timedelta(days=7)    # already late: assume the following week if chased
wk = pd.date_range(SNAP + pd.Timedelta(days=1), periods=8, freq="7D")
exp = [round(op2[(op2.expected >= w) & (op2.expected < w + pd.Timedelta(days=7))].amount_incl_vat.sum()) for w in wk]
beyond = round(op2[op2.expected >= wk[-1] + pd.Timedelta(days=7)].amount_incl_vat.sum())

r1 = lambda v: round(float(v), 1)
results = {
    "open_ar": round(total_ar), "overdue": round(overdue), "overdue_pct": r1(overdue / total_ar * 100),
    "over_90": round(ageing.loc["Over 90 days", "amount"]), "open_invoices": int(len(op)),
    "dso_now": dso[-1][1], "dso_year_ago": [d for d in dso if d[0] == "Sep 25"][0][1], "dso_min": min(d[1] for d in dso), "dso_max": max(d[1] for d in dso),
    "weighted_terms_days": r1(weighted_terms), "customers_overdue": int((c.overdue_amount > 0).sum()),
    "customers_over_limit": int(c.over_limit.sum()), "alert_customers": int(len(alerts)),
    "top10_share_of_overdue_pct": r1(pri.head(10).overdue_amount.sum() / overdue * 100),
    "expected_next_4_weeks": int(sum(exp[:4])), "closing_cash": round(closing.iloc[-1]),
    "lowest_month_end_cash": round(closing.min()), "lowest_month": str(closing.idxmin().strftime("%b %Y")),
    "invoices_analysed": int(len(inv)), "bank_rows": int(len(bank)),
}
json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=2)
data = {
    "results": results,
    "ageing": {"labels": labels, "series": {b: [round(v) for v in ageing_branch[b]] for b in ageing_branch.columns},
               "invoices": [int(v) for v in ageing.invoices]},
    "dso": {"labels": [d[0] for d in dso], "dso": [d[1] for d in dso], "ar": [d[2] for d in dso], "terms": r1(weighted_terms)},
    "priority": [[r.customer_name, r.salesperson, round(r.overdue_amount), int(r.oldest_overdue_days), (None if pd.isna(r.avg_delay_12m) else r1(r.avg_delay_12m)), bool(r.over_limit), r.action] for r in pri.head(15).itertuples()],
    "cash": {"labels": [m.strftime("%b %y") for m in months], "cash_in": [round(v) for v in cin], "cash_out": [round(v) for v in cout],
             "closing": [round(v) for v in closing], "out_categories": {k: [round(v) for v in out_cat[k]] for k in out_cat.columns}},
    "expected": {"labels": ["Week of " + w.strftime("%d %b") for w in wk], "values": exp, "beyond": beyond},
}
open(os.path.join(OUT, "data.js"), "w").write("window.PROJECT_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(json.dumps(results, indent=2))
