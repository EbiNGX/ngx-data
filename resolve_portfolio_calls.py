import json, csv, os

LOG_FILE = "portfolio_calls_log.csv"
HORIZONS = [30, 60, 90, 120]

def load_price_series(sym):
    fp = f"{sym}_price.json"
    if not os.path.exists(fp):
        return None
    d = json.load(open(fp))
    rows = sorted(d["prices"], key=lambda p: p["trade_date"])
    seen = {}
    for r in rows:
        seen[r["trade_date"]] = r
    dates = sorted(seen.keys())
    return dates, seen

def resolve():
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found - run log_portfolio_calls.py first")
        return

    rows = list(csv.DictReader(open(LOG_FILE)))
    fieldnames = list(rows[0].keys())
    updated = 0

    for r in rows:
        sym = r["symbol"]
        series = load_price_series(sym)
        if series is None:
            continue
        dates, by_date = series

        target = r["price_date"] or r["logged_date"]
        candidates = [d for d in dates if d <= target]
        if not candidates:
            continue
        i = dates.index(candidates[-1])

        for h in HORIZONS:
            ret_col = f"fwd_{h}d_return_pct"
            price_col = f"fwd_{h}d_price"
            date_col = f"fwd_{h}d_date"
            correct_col = f"call_correct_{h}d"

            if r.get(ret_col):
                continue
            if i + h >= len(dates):
                continue

            p0 = float(r["price_at_logging"])
            fwd_date = dates[i + h]
            p1 = by_date[fwd_date]["close_price"]
            ret_pct = round((p1 / p0 - 1) * 100, 2)

            r[price_col] = p1
            r[ret_col] = ret_pct
            r[date_col] = fwd_date

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
