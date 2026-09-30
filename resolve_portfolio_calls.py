import json, csv, os
import pandas as pd

LOG_FILE = "portfolio_calls_log.csv"
HORIZONS = [30, 60, 90, 120]

def resolve():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run log_portfolio_calls.py first")
        return

    rows = list(csv.DictReader(open(LOG_FILE)))
    fieldnames = list(rows[0].keys())
    updated = 0

    for r in rows:
        sym = r["symbol"]
        fp = f"{sym}_price.json"
        if not os.path.exists(fp):
            continue
        d = json.load(open(fp))
        df = pd.DataFrame(d["prices"])
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date").drop_duplicates("trade_date").reset_index(drop=True)

        logged_date = pd.Timestamp(r["price_date"] or r["logged_date"])
        idx = df.index[df["trade_date"] <= logged_date]
        if len(idx) == 0:
            continue
        i = idx[-1]

        for h in HORIZONS:
            ret_col = f"fwd_{h}d_return_pct"
            price_col = f"fwd_{h}d_price"
            date_col = f"fwd_{h}d_date"
            correct_col = f"call_correct_{h}d"

            if r.get(ret_col):
                continue  # already resolved at this horizon, never overwrite
            if i + h >= len(df):
                continue  # not enough trading days have passed yet for this horizon

            p0 = float(r["price_at_logging"])
            p1 = df["close_price"].iloc[i + h]
            ret_pct = round((p1 / p0 - 1) * 100, 2)

            r[price_col] = p1
            r[ret_col] = ret_pct
            r[date_col] = df["trade_date"].iloc[i + h].strftime("%Y-%m-%d")

            call = r["call"]
            if "Buy" in call:
                r[correct_col] = "yes" if ret_pct > 0 else "no"
            elif call in ("Sell/Trim", "Sell", "Trim", "Avoid"):
                r[correct_col] = "yes" if ret_pct < 0 else "no"
            else:
                r[correct_col] = "n/a (Hold)"

            updated += 1

    if updated:
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    print(f"Newly resolved values this run: {updated}\n")
    for h in HORIZONS:
        ret_col = f"fwd_{h}d_return_pct"
        correct_col = f"call_correct_{h}d"
        resolved = [r for r in rows if r.get(ret_col)]
        directional = [r for r in resolved if r.get(correct_col) != "n/a (Hold)"]
        correct = [r for r in directional if r.get(correct_col) == "yes"]
        if resolved:
            pct = f"{len(correct)/len(directional)*100:.0f}%" if directional else "n/a"
            print(f"  {h}-day: {len(resolved)} of {len(rows)} resolved | "
                  f"directional calls correct: {len(correct)} of {len(directional)} ({pct})")
        else:
            print(f"  {h}-day: not enough trading days have passed yet for any row")

if __name__ == "__main__":
    resolve()
