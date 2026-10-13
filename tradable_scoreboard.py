import csv, json, os
from datetime import datetime, timedelta

# Tradable-price scoreboard. Official closes freeze and VWAP is a day average; neither is a price
# you can transact at. This scores each logged call on the order book instead:
#   Buy-side and Hold rows: in at the best OFFER on the logging day, out at the best BID from the
#       Meristem pull nearest the horizon date (round trip, so the spread is paid). No bid = "n/a (no bid)".
#   Sell-side rows (Sell, Trim, Avoid): correct if the best offer (the price to buy at) fell.
#   Hold rows are not scored.
# Baseline book = the pull dated the logging day's trading session (the last session on or before it).
# Cohorts with no pull on that day have no tradable baseline and are skipped.
# A horizon resolves only once its target session exists in the NGX feed AND a 5-day window past it
# has closed, using the nearest pull inside +/-5 calendar days, so a result can't flip as pulls arrive.
# Output is derived and rewritten each run: portfolio_calls_tradable.csv

LOG_FILE = "portfolio_calls_log.csv"
BOOK_FILE = "meristem_book_log.csv"
PRICELIST_FILE = "ngx_equities_pricelist_history.json"
OUT_FILE = "portfolio_calls_tradable.csv"
HORIZONS = [30, 60, 90, 120]
TOL_DAYS = 5
SELL_SIDE = ("Sell/Trim", "Sell", "Trim", "Avoid")

def fnum(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None

def kind(call):
    p = call.split(",")[0].strip()
    if p.startswith("Buy"):
        return "buy"
    if p in SELL_SIDE:
        return "sell"
    return "hold"

def load_calendar():
    if not os.path.exists(PRICELIST_FILE):
        return []
    days = {(r.get("TradeDate") or "")[:10] for r in json.load(open(PRICELIST_FILE))}
    days.discard("")
    return sorted(days)

def est_date(base_day, n):
    d = datetime.strptime(base_day, "%Y-%m-%d").date()
    c = 0
    while c < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            c += 1
    return d.isoformat()

def day_diff(a, b):
    return (datetime.strptime(a, "%Y-%m-%d") - datetime.strptime(b, "%Y-%m-%d")).days

def load_book():
    book, pulls = {}, {}
    if os.path.exists(BOOK_FILE):
        for r in csv.DictReader(open(BOOK_FILE, encoding="utf-8")):
            book[(r["pull_date"], r["symbol"])] = r
            pulls.setdefault(r["symbol"], []).append(r["pull_date"])
    return book, pulls

def main(horizons=None, log_file=None, out_file=None):
    horizons = horizons or HORIZONS
    log_file = log_file or LOG_FILE
    out_file = out_file or OUT_FILE
    if not os.path.exists(log_file):
        print(f"{log_file} not found")
        return
    rows = list(csv.DictReader(open(log_file, encoding="utf-8")))
    calendar = load_calendar()
    book, pulls = load_book()
    last_day = calendar[-1] if calendar else None
    out, no_base, due = [], {}, {}

    for r in rows:
        sym, logged, call = r["symbol"], r["logged_date"], r["call"]
        if not calendar or logged > last_day:
            continue
        cand = [k for k, d in enumerate(calendar) if d <= logged]
        if not cand:
            continue
        bi = cand[-1]
        bd = calendar[bi]
        b0 = book.get((bd, sym))
        offer0 = fnum(b0.get("best_offer")) if b0 else None
        if not offer0:
            no_base.setdefault(logged, []).append(sym)
            continue
        bid0 = fnum(b0.get("best_bid"))
        rec = {"symbol": sym, "cohort": logged, "call": call, "baseline_pull_date": bd,
               "entry_offer": offer0, "entry_bid": bid0 if bid0 else "",
               "entry_spread_pct": round((offer0 - bid0) / offer0 * 100, 2) if bid0 else ""}
        kd = kind(call)
        for h in horizons:
            ti = bi + h
            exact = ti < len(calendar)
            tdate = calendar[ti] if exact else est_date(bd, h)
            rec[f"h{h}_target_date"] = tdate
            rec[f"h{h}_target_is_estimate"] = "" if exact else "yes"
            blank = {f"h{h}_{f}": "" for f in ("pull_date", "days_off", "exit_bid", "exit_offer", "return_pct", "correct")}
            if not (exact and day_diff(last_day, tdate) >= TOL_DAYS):
                rec.update(blank)
                due.setdefault(logged, {})[h] = (tdate, not exact)
                continue
            best = None
            for pdate in pulls.get(sym, []):
                if pdate <= bd:
                    continue
                off = abs(day_diff(pdate, tdate))
                if off <= TOL_DAYS and (best is None or off < best[0]):
                    best = (off, pdate)
            if best is None:
                rec.update(blank)
                rec[f"h{h}_correct"] = "no pull within window"
                continue
            pr = book[(best[1], sym)]
            bid_h, off_h = fnum(pr.get("best_bid")), fnum(pr.get("best_offer"))
            ret, status = None, ""
            if kd == "sell":
                if off_h:
                    ret = (off_h / offer0 - 1) * 100
                else:
                    status = "n/a (no offer)"
            else:
                if bid_h:
                    ret = (bid_h / offer0 - 1) * 100
                else:
                    status = "n/a (no bid)"
            if ret is not None:
                ret = round(ret, 2)
                if ret == 0:
                    status = "n/a (flat)"
                elif kd == "buy":
                    status = "yes" if ret > 0 else "no"
                elif kd == "sell":
                    status = "yes" if ret < 0 else "no"
                else:
                    status = "n/a (Hold)"
            rec[f"h{h}_pull_date"] = best[1]
            rec[f"h{h}_days_off"] = day_diff(best[1], tdate)
            rec[f"h{h}_exit_bid"] = bid_h or ""
            rec[f"h{h}_exit_offer"] = off_h or ""
            rec[f"h{h}_return_pct"] = "" if ret is None else ret
            rec[f"h{h}_correct"] = status
        out.append(rec)

    if out:
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)

    print(f"Tradable scoreboard: {len(out)} rows with a book baseline -> {out_file}")
    for c, syms in sorted(no_base.items()):
        print(f"  cohort {c}: {len(syms)} rows have no book pull on their baseline day (not scored here)")
    for h in horizons:
        lines = []
        for c in sorted({r["cohort"] for r in out}):
            grp = [r for r in out if r["cohort"] == c]
            res = [r for r in grp if r[f"h{h}_return_pct"] != ""]
            nb = [r for r in grp if str(r[f"h{h}_correct"]).startswith("n/a (no bid")]
            if not res and not nb:
                continue
            dr = [r for r in res if r[f"h{h}_correct"] in ("yes", "no")]
            ok = [r for r in dr if r[f"h{h}_correct"] == "yes"]
            pct = f"{len(ok)/len(dr)*100:.0f}%" if dr else "n/a"
            lines.append(f"  {h}-day cohort {c}: {len(res)}/{len(grp)} priced | directional correct {len(ok)}/{len(dr)} ({pct}) | exit impossible (no bid): {len(nb)}")
        print("\n".join(lines) if lines else f"  {h}-day: pending")
    for c, d in sorted(due.items()):
        h = min(d)
        tdate, est = d[h]
        print(f"  cohort {c}: next book pull needed around {tdate}{' (estimate)' if est else ''} for the {h}-day mark (any pull within +/-{TOL_DAYS} days works)")

if __name__ == "__main__":
    main()
