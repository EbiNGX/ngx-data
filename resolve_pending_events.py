import csv, json, os
import pandas as pd
from datetime import datetime

LOG_FILE = "ngx_insider_event_log.csv"

def resolve_pending():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run this from the folder that has it (your ngx-data repo)")
        return
    rows = list(csv.DictReader(open(LOG_FILE)))
    updated = 0
    for r in rows:
        if r["status"] != "pending":
            continue
        sym = r["ticker"]
        fp = f"{sym}_price.json"
        if not os.path.exists(fp):
            continue
        d = json.load(open(fp))
        df = pd.DataFrame(d["prices"])
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").reset_index(drop=True)
        ev = pd.Timestamp(r["event_date"])
        idx = df[df["trade_date"] <= ev].index
        if len(idx) == 0:
            continue
        i = idx[-1]
        if i + 20 < len(df):
            p0 = df["close_price"].iloc[i]
            r["fwd_20d_return_pct"] = round((df["close_price"].iloc[i+20]/p0 - 1)*100, 1)
            if i + 60 < len(df):
                r["fwd_60d_return_pct"] = round((df["close_price"].iloc[i+60]/p0 - 1)*100, 1)
            r["status"] = "resolved"
            updated += 1

    if updated:
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"Resolved {updated} newly-eligible event(s). "
          f"{sum(1 for r in rows if r['status']=='pending')} still pending, "
          f"{sum(1 for r in rows if r['status']=='resolved')} resolved total.")

if __name__ == "__main__":
    resolve_pending()

# To log a NEW event: open ngx_insider_event_log.csv directly and add a row with the
# same columns (ticker, event_date, direction, note, source, fwd_20d_return_pct,
# fwd_60d_return_pct, status, logged_on) - leave the two return columns blank and
# status as "pending". This script will fill them in automatically once eligible.
