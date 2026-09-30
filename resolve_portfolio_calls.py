import json, csv, os
import pandas as pd

LOG_FILE = "portfolio_calls_log.csv"
HORIZON_DAYS = 60

def resolve():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run log_portfolio_calls.py first")
        return

    rows = list(csv.DictReader(open(LOG_FILE)))
    updated = 0
    for r in rows:
        if r["fwd_60d_return_pct"]:
            continue  # already resolved, never overwrite
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
        if i + HORIZON_DAYS >= len(df):
            continue  # not enough trading days have passed yet

        p0 = float(r["price_at_logging"])
        p1 = df["close_price"].iloc[i + HORIZON_DAYS]
        fwd_date = df["trade_date"].iloc[i + HORIZON_DAYS].strftime("%Y-%m-%d")
        ret_pct = round((p1 / p0 - 1) * 100, 2)

        r["fwd_60d_price"] = p1
        r["fwd_60d_return_pct"] = ret_pct
        r["fwd_60d_date"] = fwd_date

        call = r["call"]
        if "Buy" in call:
            r["call_correct"] = "yes" if ret_pct > 0 else "no"
        elif call in ("Sell/Trim", "Sell", "Trim", "Avoid"):
            r["call_correct"] = "yes" if ret_pct < 0 else "no"
        else:  # Hold - no directional prediction, mark as n/a
            r["call_correct"] = "n/a (Hold)"

        updated += 1

    if updated:
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    resolved = [r for r in rows if r["fwd_60d_return_pct"]]
    directional = [r for r in resolved if r["call_correct"] != "n/a (Hold)"]
    correct = [r for r in directional if r["call_correct"] == "yes"]
    print(f"Newly resolved this run: {updated}")
    print(f"Total resolved so far: {len(resolved)} of {len(rows)}")
    if directional:
        print(f"Directional calls (Buy/Sell/Trim/Avoid) correct: {len(correct)} of {len(directional)} "
              f"({len(correct)/len(directional)*100:.0f}%)")

if __name__ == "__main__":
    resolve()
