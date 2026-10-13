"""index_proxy_update.py - Kobo-free ASI / sector-index updater (stdlib only; runs daily in the workflow).

Official index levels (the Kobo-era history) are NEVER modified.  For sessions after the last official
value, the script writes DERIVED values: value_t = previous value + sum_i c_i * (close_i,t - close_i,t-1),
using calibrated coefficients in index_proxy_weights.json (made by fit_index_proxy.py) and closes from the
per-ticker *_price.json files plus the NGX-native price list.  Any official figure you add to
index_anchors.csv (date,index,value,source) resets the chain, so error never accumulates past the latest
anchor.  Derived rows carry "source": "derived"; anchors carry "source": "anchor".  Idempotent: derived rows
are recomputed from scratch on every run.
"""
import json, csv, os, glob, bisect
from datetime import datetime

MIN_SYMBOLS_FOR_SESSION = 40   # a date counts as a trading session only if this many tickers have a close on it
CLIP = 0.105                   # ignore single-day moves > 10.5% (corporate actions; NGX limit is 10%)

def load_closes():
    P = {}
    for fn in glob.glob("*_price.json"):
        try:
            d = json.load(open(fn))
            P[d["symbol"]] = {r["trade_date"]: r["close_price"] for r in d["prices"] if r.get("close_price")}
        except Exception as e:
            print(f"  skip {fn}: {e}")
    if os.path.exists("ngx_equities_pricelist_history.json"):
        for r in json.load(open("ngx_equities_pricelist_history.json")):
            if r.get("ClosePrice") and r.get("Symbol") and r.get("TradeDate"):
                P.setdefault(r["Symbol"], {})[r["TradeDate"][:10]] = r["ClosePrice"]
    return P

def price_on(sorted_keys, d, date):
    i = bisect.bisect_right(sorted_keys, date) - 1
    return d[sorted_keys[i]] if i >= 0 else None

def load_anchors():
    A = {}
    if os.path.exists("index_anchors.csv"):
        for r in csv.DictReader(open("index_anchors.csv")):
            try: A.setdefault(r["index"].strip(), {})[r["date"].strip()] = (float(r["value"]), r.get("source", "").strip())
            except Exception: pass
    return A

def main():
    if not os.path.exists("index_proxy_weights.json"):
        print("index proxy: index_proxy_weights.json missing - run fit_index_proxy.py once"); return
    W = json.load(open("index_proxy_weights.json"))["indices"]
    P = load_closes()
    keys = {s: sorted(d) for s, d in P.items()}
    counts = {}
    for d in P.values():
        for dt in d: counts[dt] = counts.get(dt, 0) + 1
    sessions = sorted(dt for dt, n in counts.items() if n >= MIN_SYMBOLS_FOR_SESSION)
    anchors = load_anchors()
    for name, spec in W.items():
        fn = spec["file"]
        if not os.path.exists(fn): print(f"index proxy: {fn} missing, skipped"); continue
        doc = json.load(open(fn))
        hist = [h for h in doc["history"] if h.get("source") != "derived"]       # drop old derived rows
        have = {h["date"] for h in hist}
        official_last = max(h["date"] for h in hist if h.get("source") is None)
        for dt, (val, src) in anchors.get(name, {}).items():                      # add anchors (never over official)
            if dt not in have and dt > official_last:
                hist.append({"date": dt, "value": val, "source": "anchor", "anchor_source": src}); have.add(dt)
        hist.sort(key=lambda h: h["date"])
        base_last = max(h["date"] for h in hist)
        coef = spec["coef"]
        syms = [s for s in coef if s in P]
        timeline = sorted(set(d for d in sessions if d > official_last) | {h["date"] for h in hist if h["date"] > official_last})
        anchor_vals = {h["date"]: h["value"] for h in hist if h["date"] > official_last}
        prev_date = official_last
        prev_val = next(h["value"] for h in hist if h["date"] == official_last)
        out_rows = []
        for t in timeline:
            if t in anchor_vals:
                val = anchor_vals[t]
            else:
                delta = 0.0
                for s in syms:
                    p0 = price_on(keys[s], P[s], prev_date); p1 = price_on(keys[s], P[s], t)
                    if p0 and p1 and abs(p1 / p0 - 1) <= CLIP: delta += coef[s] * (p1 - p0)
                val = prev_val + delta
                out_rows.append({"date": t, "value": round(val, 2), "source": "derived"})
            prev_date, prev_val = t, val
        hist = [h for h in hist if h.get("source") != "derived"] + out_rows
        hist.sort(key=lambda h: h["date"])
        doc["history"] = hist
        doc["count"] = len(hist); doc["last_date"] = hist[-1]["date"]
        doc["official_through"] = official_last
        doc["derived_note"] = ("Rows after official_through are DERIVED by index_proxy_update.py (not official NGX figures) "
                               "unless source=='anchor'. Add official closes to index_anchors.csv to reset the chain.")
        json.dump(doc, open(fn, "w"))
        last = hist[-1]
        print(f"index proxy {name}: official through {official_last}; wrote {len(out_rows)} derived row(s); latest {last['date']} = {last['value']} ({last.get('source','official')})")

if __name__ == "__main__":
    try: main()
    except Exception as e: print(f"index proxy: FAILED - {e}")
