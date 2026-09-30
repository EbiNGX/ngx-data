import csv

LOG_FILE = "portfolio_calls_log.csv"

old_rows = list(csv.DictReader(open(LOG_FILE)))

new_fieldnames = ["symbol", "call", "rationale", "logged_date", "price_at_logging", "price_date"]
for h in [30, 60, 90, 120]:
    new_fieldnames += [f"fwd_{h}d_price", f"fwd_{h}d_return_pct", f"fwd_{h}d_date", f"call_correct_{h}d"]

new_rows = []
for r in old_rows:
    new_row = {k: r.get(k, "") for k in ["symbol", "call", "rationale", "logged_date",
                                          "price_at_logging", "price_date"]}
    # carry over any already-resolved 60-day values from the old schema (there shouldn't
    # be any yet, since 0 trading days have passed, but this is safe either way)
    new_row["fwd_60d_price"] = r.get("fwd_60d_price", "")
    new_row["fwd_60d_return_pct"] = r.get("fwd_60d_return_pct", "")
    new_row["fwd_60d_date"] = r.get("fwd_60d_date", "")
    new_row["call_correct_60d"] = r.get("call_correct", "")
    for h in [30, 90, 120]:
        new_row[f"fwd_{h}d_price"] = ""
        new_row[f"fwd_{h}d_return_pct"] = ""
        new_row[f"fwd_{h}d_date"] = ""
        new_row[f"call_correct_{h}d"] = ""
    new_rows.append(new_row)

with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=new_fieldnames)
    w.writeheader()
    w.writerows(new_rows)

print(f"Migrated {len(new_rows)} rows to the 4-horizon schema (30/60/90/120 days).")
print("Run this script only once - running it again is harmless but unnecessary.")
