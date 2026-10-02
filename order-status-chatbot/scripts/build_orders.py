"""
Solution showcase 4: order-status chatbot.
Builds a compact orders.json for the client-side bot from the synthetic
orders.csv and customers.csv, plus data.js (charts) and results.json.

orders.json layout (kept small so the page loads fast):
  asOf      snapshot date (ISO)
  cols      column names for each order row
  customers list of [name, emirate]; rows refer to them by index
  orders    rows; dates are stored as day offsets from asOf (0 = asOf, -3 = three days before)

Usage: python build_orders.py <data_folder> <output_folder>
All data is synthetic. Tidewell Distribution LLC is an invented company modelled on a UAE distributor.
"""
import sys, os, json
import pandas as pd
import numpy as np

DATA, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("data", ".")
SNAP = pd.Timestamp("2026-09-30")
o = pd.read_csv(os.path.join(DATA, "orders.csv"), parse_dates=["order_date", "promised_date", "delivered_date"])
c = pd.read_csv(os.path.join(DATA, "customers.csv")).set_index("customer_id")
o = o.join(c[["customer_name", "emirate"]], on="customer_id")
cust_list = sorted(o.customer_id.unique()); idx = {k: i for i, k in enumerate(cust_list)}
off = lambda d: None if pd.isna(d) else int((d - SNAP).days)
rows = [[r.order_id, off(r.order_date), off(r.promised_date), off(r.delivered_date), r.status, idx[r.customer_id], r.branch, round(r.order_value), int(r["items"])]
        for _, r in o.iterrows()]
payload = {"asOf": str(SNAP.date()), "company": "Tidewell Distribution LLC",
           "cols": ["id", "ordered", "promised", "delivered", "status", "customer", "branch", "value", "items"],
           "customers": [[c.at[k, "customer_name"], c.at[k, "emirate"]] for k in cust_list], "orders": rows}
open(os.path.join(OUT, "orders.json"), "w").write(json.dumps(payload, separators=(",", ":")))

# ---------------- metrics and charts
dl = o[o.status == "Delivered"].copy()
dl["on_time"] = dl.delivered_date <= dl.promised_date
dl["lead"] = (dl.delivered_date - dl.order_date).dt.days
by_em = dl.groupby("emirate").agg(on_time=("on_time", "mean"), orders=("order_id", "count")).sort_values("on_time")
st = o.status.value_counts()
daily = o.groupby([o.order_date.dt.date, "status"]).size().unstack(fill_value=0)
daily = daily.reindex(pd.date_range(o.order_date.min(), SNAP).date, fill_value=0)
examples = {}
for s in ["Delivered", "Out for delivery", "Packed", "Picking", "Received", "On hold, credit check", "Cancelled"]:
    x = o[o.status == s]
    if s == "Delivered":
        late = x[x.delivered_date > x.promised_date]
        if len(late): examples["Delivered late"] = late.sort_values("order_date").iloc[-1].order_id
        x = x[x.delivered_date <= x.promised_date]
    if len(x): examples[s] = x.sort_values("order_date").iloc[-1].order_id
results = {"orders": int(len(o)), "customers": len(cust_list), "delivered": int(st.get("Delivered", 0)),
           "on_time_pct": round(float(dl.on_time.mean() * 100), 1), "avg_lead_days": round(float(dl.lead.mean()), 1),
           "open_orders": int(o.status.isin(["Received", "Picking", "Packed", "Out for delivery", "On hold, credit check"]).sum()),
           "on_hold": int(st.get("On hold, credit check", 0)), "cancelled": int(st.get("Cancelled", 0)),
           "worst_emirate": by_em.index[0], "worst_emirate_on_time_pct": round(float(by_em.on_time.iloc[0] * 100), 1),
           "best_emirate": by_em.index[-1], "best_emirate_on_time_pct": round(float(by_em.on_time.iloc[-1] * 100), 1),
           "json_bytes": os.path.getsize(os.path.join(OUT, "orders.json")), "examples": examples}
json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=2)
order = ["Delivered", "Out for delivery", "Packed", "Picking", "Received", "On hold, credit check", "Cancelled"]
data = {"results": results,
        "status": {"labels": [s for s in order if s in st], "values": [int(st[s]) for s in order if s in st]},
        "emirate": {"labels": list(by_em.index), "on_time": [round(v * 100, 1) for v in by_em.on_time], "orders": [int(v) for v in by_em.orders]},
        "daily": {"labels": [d.strftime("%d %b") for d in daily.index], "series": {s: [int(v) for v in daily[s]] for s in order if s in daily.columns}}}
open(os.path.join(OUT, "data.js"), "w").write("window.PROJECT_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(json.dumps(results, indent=2))
