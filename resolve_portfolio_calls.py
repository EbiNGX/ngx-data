import json, csv, os

LOG_FILE = "portfolio_calls_log.csv"
PRICELIST_FILE = "ngx_equities_pricelist_history.json"
HORIZONS = [30, 60, 90, 120]
LOOKBACK = 5  # sessions to walk back when a name has no volume on the target day
SELL_SIDE = ("Sell/Trim", "Sell", "Trim", "Avoid")

# Two scoreboards run side by side on the same locked rows:
#  1. official close - exactly as originally logged. Distorted for names whose
#     official close is frozen (it only moves on 100,000+ unit trades).
#  2. VWAP (Value / Volume from the NGX-native daily price list) - where the stock
#     actually traded. This is the tradable price. Matches Meristem's VWAP exactly.
# Horizons count NGX trading sessions from the logging day, using the trading
# calendar in the NGX-native price list (so holidays like Oct 1 are skipped).

def filled(v):
    return v is not None and v != ""

def score(call, ret):
    if ret == 0:
        return "n/a (flat)"  # a frozen/unchanged price is no evidence either way
    if "Buy" in call:
        return "yes" if ret > 0 else "no"
    if call in SELL_SIDE:
        return "yes" if ret < 0 else "no"
    return "n/a (Hold)"

def load_price_series(sym):
    fp = f"{sym}_price.json"
    if not os.path.exists(fp):
        return None
    d = json.load(open(fp))
    seen = {}
    for p in sorted(d["prices"], key=lambda p: p["trade_date"]):
        seen[p["trade_date"]] = p
    return sorted(seen), seen

def load_pricelist():
    if not os.path.exists(PRICELIST_FILE):
        return None, []
    by, days = {}, set()
    for r in json.load(open(PRICELIST_FILE)):
        sym = (r.get("Symbol") or "").strip()
        day = (r.get("TradeDate") or "")[:10]
        if sym and day:
            by.setdefault(sym, {})[day] = r
            days.add(day)
    return by, sorted(days)

def vwap_on_or_before(by, calendar, sym, idx):
    for j in range(idx, max(idx - LOOKBACK, -1), -1):
        r = by.get(sym, {}).get(calendar[j])
        if r and r.get("Volume") and r.get("Value"):
            return r["Value"] / r["Volume"], calendar[j]
    return None, None

def resolve(horizons=HORIZONS, log_file=LOG_FILE):
    if not os.path.exists(log_file):
        print(f"{log_file} not found - run log_portfolio_calls.py first")
        return
    rows = list(csv.DictReader(open(log_file, encoding="utf-8")))
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    wanted = ["vwap_at_logging", "vwap_baseline_date"]
    for h in horizons:
        wanted += [f"fwd_{h}d_price", f"fwd_{h}d_return_pct", f"fwd_{h}d_date", f"call_correct_{h}d",
                   f"fwd_{h}d_vwap", f"fwd_{h}d_vwap_return_pct", f"call_correct_vwap_{h}d"]
    migrated = False
    for c in wanted:
        if c not in fieldnames:
            fieldnames.append(c)
            migrated = True

    by, calendar = load_pricelist()
    updated = 0
    excluded = []

    for r in rows:
        sym, logged, call = r["symbol"], r["logged_date"], r["call"]
        bi = None
        if calendar:
            cand = [k for k, d in enumerate(calendar) if d <= logged]
            bi = cand[-1] if cand else None
        baseline_day = calendar[bi] if bi is not None else None

        # ---- scoreboard 1: official close, as originally logged ----
        stale = bool(baseline_day and r.get("price_date") and r["price_date"] != baseline_day)
        series = load_price_series(sym)
        if series and r.get("price_at_logging") and not stale:
            dates, by_date = series
            cands = [d for d in dates if d <= (r.get("price_date") or logged)]
            if cands:
                i = dates.index(cands[-1])
                p0 = float(r["price_at_logging"])
                for h in horizons:
                    if filled(r.get(f"fwd_{h}d_return_pct")) or i + h >= len(dates):
                        continue
                    fwd_date = dates[i + h]
                    p1 = by_date[fwd_date].get("close_price")
                    if p1 is None:
                        continue
                    ret = round((p1 / p0 - 1) * 100, 2)
                    r[f"fwd_{h}d_price"] = p1
                    r[f"fwd_{h}d_return_pct"] = ret
                    r[f"fwd_{h}d_date"] = fwd_date
                    r[f"call_correct_{h}d"] = score(call, ret)
                    updated += 1
        else:
            excluded.append(f"{sym} ({logged})")

        # ---- scoreboard 2: VWAP, the price the stock actually traded at ----
        if bi is not None:
            if not filled(r.get("vwap_at_logging")):
                v0, vd = vwap_on_or_before(by, calendar, sym, bi)
                if v0:
                    r["vwap_at_logging"] = round(v0, 4)
                    r["vwap_baseline_date"] = vd
                    updated += 1
            if filled(r.get("vwap_at_logging")):
                v0 = float(r["vwap_at_logging"])
                for h in horizons:
                    if filled(r.get(f"fwd_{h}d_vwap_return_pct")) or bi + h >= len(calendar):
                        continue
                    v1, _ = vwap_on_or_before(by, calendar, sym, bi + h)
                    if not v1:
                        continue
                    ret = round((v1 / v0 - 1) * 100, 2)
                    r[f"fwd_{h}d_vwap"] = round(v1, 4)
                    r[f"fwd_{h}d_vwap_return_pct"] = ret
                    r[f"call_correct_vwap_{h}d"] = score(call, ret)
                    updated += 1

    if updated or migrated:
        with open(log_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    print(f"Newly resolved/filled values this run: {updated}")
    cohorts = sorted({r["logged_date"] for r in rows})
    for h in horizons:
        lines = []
        for label, ret_col, ok_col in (("official-close", f"fwd_{h}d_return_pct", f"call_correct_{h}d"),
                                       ("VWAP", f"fwd_{h}d_vwap_return_pct", f"call_correct_vwap_{h}d")):
            for c in cohorts:
                grp = [r for r in rows if r["logged_date"] == c]
                res = [r for r in grp if filled(r.get(ret_col))]
                if not res:
                    continue
                dr = [r for r in res if not str(r.get(ok_col)).startswith("n/a")]
                ok = [r for r in dr if r.get(ok_col) == "yes"]
                pct = f"{len(ok)/len(dr)*100:.0f}%" if dr else "n/a"
                lines.append(f"  {h}-day [{label}] cohort {c}: {len(res)}/{len(grp)} resolved | "
                             f"directional correct {len(ok)}/{len(dr)} ({pct})")
        print("\n".join(lines) if lines else f"  {h}-day: pending (not enough trading days yet)")
    if excluded:
        print("Excluded from the official-close scoreboard (no or stale baseline): " + ", ".join(sorted(set(excluded))))

if __name__ == "__main__":
    resolve()
