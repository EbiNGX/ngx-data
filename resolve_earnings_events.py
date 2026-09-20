import csv, json, os
import pandas as pd
from datetime import datetime

LOG_FILE = "ngx_earnings_growth_log.csv"

def resolve_pending():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run this from your ngx-data folder")
        return
    rows = list(csv.DictReader(open(LOG_FILE)))
    updated = 0
    for r in rows:
        sym = r["symbol"]
        fp = f"{sym}_price.json"
        if not os.path.exists(fp):
            continue
        d = json.load(open(fp))
        df = pd.DataFrame(d["prices"])
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").reset_index(drop=True)
        ev = pd.Timestamp(r["filing_date"])
        idx = df[df["trade_date"] <= ev].index
        if len(idx) == 0:
            continue
        i = idx[-1]
        p0 = df["close_price"].iloc[i]
        for horizon, key in [(5,"fwd_5d_pct"),(20,"fwd_20d_pct"),(60,"fwd_60d_pct")]:
            if r.get(key, "") == "" and i + horizon < len(df):
                r[key] = round((df["close_price"].iloc[i+horizon]/p0 - 1)*100, 2)
                updated += 1
    if updated:
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"Filled in {updated} newly-eligible value(s) across {len(rows)} logged earnings events.")

if __name__ == "__main__":
    resolve_pending()

# To log a NEW earnings event: add a row with symbol, filing_date, and pbt_growth_yoy_pct
# (from the weekly disclosures read), leave the three fwd_*_pct columns blank.
