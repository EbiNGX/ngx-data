import csv, json, os
import pandas as pd
from datetime import datetime

LOG_FILE = "ngx_macro_event_log.csv"
ASI_FILE = "asi_history_full.json"

def resolve_pending():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run this from the folder that has it (your ngx-data repo)")
        return
    if not os.path.exists(ASI_FILE):
        print(f"{ASI_FILE} not found - the real verified ASI history needs to be in this folder too")
        return

    d = json.load(open(ASI_FILE))
    df = pd.DataFrame(d["history"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    rows = list(csv.DictReader(open(LOG_FILE)))
    updated = 0
    for r in rows:
        ev = pd.Timestamp(r["date"])
        idx = df[df["date"] <= ev].index
        if len(idx) == 0:
            continue
        i = idx[-1]
        p0 = df["value"].iloc[i]
        for horizon, key in [(20,"fwd_20d_asi_pct"),(60,"fwd_60d_asi_pct"),
                              (120,"fwd_120d_asi_pct"),(250,"fwd_250d_asi_pct")]:
            if r.get(key, "") == "" and i + horizon < len(df):
                r[key] = round((df["value"].iloc[i+horizon]/p0 - 1)*100, 1)
                updated += 1

    if updated:
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"Filled in {updated} newly-eligible horizon value(s) across {len(rows)} logged events.")

if __name__ == "__main__":
    resolve_pending()

# To log a NEW macro decision (e.g. the Sept 21-22, 2026 MPC outcome once announced):
# open ngx_macro_event_log.csv and add a row with columns: date, decision (hike/cut/hold),
# rate_before, rate_after, note, source, then leave all four fwd_*_asi_pct columns blank
# and logged_on as today's date. This script fills in whichever horizons become
# eligible each time it's run - never overwrites a horizon that's already filled.
