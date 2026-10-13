"""fit_index_proxy.py - MANUAL (monthly) calibration of the Kobo-free index proxy.
Needs numpy + scipy (NOT run in the daily workflow).  Writes index_proxy_weights.json and
index_proxy_validation.json.

Model: change in index points ~= sum_i c_i * (change in close of stock i), c_i >= 0, where c_i is an
'effective share' coefficient (shares x free-float x index divisor).  Where stockanalysis gives shares
outstanding, c_i is capped at shares_i * k (k = ASI points per naira of market cap); the cap keeps the fit
economically sane.  Stock-days with |move| > 10.5% (corporate actions) are zeroed.
"""
import json, glob, sys, os
import numpy as np
from scipy.optimize import lsq_linear

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
def J(f): return json.load(open(os.path.join(ROOT, f)))

K_ASI_PER_NAIRA = 250273.50 / 162.495e12   # ASI close / NGX market cap, 6 Oct 2026
CLIP = 0.105
BANKS = ["ACCESSCORP","ETI","FCMB","FIDELITYBK","FIRSTHOLDCO","GTCO","JAIZBANK","STANBIC","STERLINGNG","UBA","UNITYBNK","WEMABANK","ZENITHBANK"]

def load_closes():
    P = {}
    for fn in glob.glob(os.path.join(ROOT, "*_price.json")):
        d = json.load(open(fn))
        P[d["symbol"]] = {r["trade_date"]: r["close_price"] for r in d["prices"] if r.get("close_price")}
    pl = J("ngx_equities_pricelist_history.json")
    sector = {}
    for r in pl:
        sector[r["Symbol"]] = r.get("Sector")
        if r.get("ClosePrice"): P.setdefault(r["Symbol"], {})[r["TradeDate"][:10]] = r["ClosePrice"]
    return P, sector, pl

def num(x):
    m = {"T":1e12,"B":1e9,"M":1e6,"K":1e3}
    try: return float(x[:-1]) * m[x[-1]] if x[-1] in m else float(x)
    except Exception: return None

def panel(P, dates, syms):
    M = np.full((len(dates), len(syms)), np.nan)
    for j, s in enumerate(syms):
        d = P[s]; ks = sorted(d); last = None; k = 0
        for i, dt in enumerate(dates):
            while k < len(ks) and ks[k] <= dt: last = d[ks[k]]; k += 1
            if last is not None and ks[0] <= dt: M[i, j] = last
    return M

def design(P, idx, start, end, syms):
    dates = [d for d, _ in idx if start <= d <= end]
    v = np.array([x for d, x in idx if start <= d <= end])
    M = panel(P, dates, syms)
    dP = np.diff(M, axis=0); rel = dP / M[:-1]; dP[np.abs(rel) > CLIP] = 0
    return np.nan_to_num(dP), np.diff(v)

def fit(P, idx, start, end, syms, shares):
    X, y = design(P, idx, start, end, syms)
    ub = np.array([shares[s] * K_ASI_PER_NAIRA if s in shares else 100e9 * K_ASI_PER_NAIRA for s in syms])
    r = lsq_linear(X * ub, y, bounds=(0, 1))
    c = r.x * ub
    yh = X @ c
    r2 = 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return c, r2

def path(P, syms, c, dates):
    """Chain-linked index points from dates[0]=0, same clipping as the fit."""
    M = panel(P, dates, syms)
    dP = np.diff(M, axis=0); rel = dP / M[:-1]; dP[np.abs(rel) > CLIP] = 0
    return np.concatenate([[0], np.cumsum(np.nan_to_num(dP) @ c)])

def main():
    P, sector, pl = load_closes()
    F = J("stockanalysis_fundamentals.json")
    shares = {s: num(v.get("shares_out") or "") for s, v in F.items()}
    shares = {s: x for s, x in shares.items() if x}
    # liquidity ranking for NGX-30 candidate set
    val = {}
    for r in pl: val[r["Symbol"]] = val.get(r["Symbol"], 0) + (r.get("Value") or 0)
    big = [s for s, _ in sorted(((s, shares[s] * list(sorted(P[s].items()))[-1][1]) for s in shares if s in P), key=lambda t: -t[1])[:40]]
    liquid = [s for s, _ in sorted(val.items(), key=lambda t: -t[1])[:20]]
    ng30 = sorted(set(big) | set(liquid))
    fs = [s for s in P if sector.get(s) == "FINANCIAL SERVICES"]
    sets = {
        "asi": ("asi_history_full.json", [s for s in P if len([d for d in P[s] if d >= "2025-01-01"]) >= 150], "2025-01-02"),
        "ngx-30": ("index_ngx-30.json", ng30, "2024-01-02"),
        "ngx-bnk": ("index_ngx-bnk.json", [s for s in BANKS if s in P], "2024-01-02"),
        "ngx-ins": ("index_ngx-ins.json", [s for s in fs if s not in BANKS], "2024-01-02"),
        "ngx-cnsmrgds": ("index_ngx-cnsmrgds.json", [s for s in P if sector.get(s) == "CONSUMER GOODS"], "2024-01-02"),
        "ngx-oilgas": ("index_ngx-oilgas.json", [s for s in P if sector.get(s) == "OIL AND GAS"], "2024-01-02"),
    }
    out = {"model": "dIndex = sum c_i * dClose_i", "k_asi_per_naira": K_ASI_PER_NAIRA, "indices": {}}
    val_out = {}
    for name, (fn, syms, start) in sets.items():
        d = J(fn)
        idx = [(h["date"], h["value"]) for h in d["history"] if h.get("source") not in ("derived",)]
        idx = [x for x in idx]
        last = max(dt for dt, _ in idx if True)
        syms = [s for s in syms if len([x for x in P[s] if x >= start]) >= 100]
        # validation fit: train to 2026-09-11, test the sessions after (only where official values exist)
        c_v, r2_v = fit(P, idx, start, "2026-09-11", syms, shares)
        test_dates = [dt for dt, _ in idx if dt >= "2026-09-11"]
        errs = {}
        if len(test_dates) > 1:
            pa = path(P, syms, c_v, test_dates); off = dict(idx)
            for dt, p in zip(test_dates[1:], pa[1:]):
                errs[dt] = round(float(((off["2026-09-11"] + p) / off[dt] - 1) * 100), 3)
        # final fit through the last official date
        c, r2 = fit(P, idx, start, last, syms, shares)
        out["indices"][name] = {"file": fn, "fit_start": start, "fit_through": last, "r2_daily_changes": round(r2, 3),
                                "coef": {s: float(x) for s, x in zip(syms, c) if x > 1e-6 * max(c)}}
        val_out[name] = {"train_through": "2026-09-11", "r2_train": round(r2_v, 3), "out_of_sample_error_pct_by_date": errs}
        print(name, "n", len(syms), "R2", round(r2, 3), "nonzero", int((c > 0).sum()), "OOS", list(errs.items())[-3:])
    json.dump(out, open(os.path.join(ROOT, "index_proxy_weights.json"), "w"), indent=1)
    json.dump(val_out, open(os.path.join(ROOT, "index_proxy_validation.json"), "w"), indent=1)

main()
