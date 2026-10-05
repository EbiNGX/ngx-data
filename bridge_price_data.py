import json, os

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM","NIDF","NASCON","MCNICHOLS"]

PRICELIST_FILE = "ngx_equities_pricelist_history.json"

# This closes the real gap underneath everything else in this project: daily_update.py
# pulls per-ticker price history from Kobo, which lapses next month. ngx_own_data_update.py
# already collects a free, NGX-native daily snapshot into ngx_equities_pricelist_history.json,
# but nothing was appending that into the per-ticker {SYM}_price.json files that every other
# script (RSI, moving averages, the resolvers, frozen-price detection) actually reads from.
# Confirmed byte-for-byte matching against Kobo's own Sept 30 MTNN row before writing this.

if not os.path.exists(PRICELIST_FILE):
    print(f"{PRICELIST_FILE} not found - run ngx_own_data_update.py first")
    exit()

pricelist = json.load(open(PRICELIST_FILE))
by_symbol = {}
for r in pricelist:
    sym = r.get("Symbol")
    if sym:
        by_symbol.setdefault(sym, []).append(r)

total_added = 0
for sym in WATCHLIST:
    fp = f"{sym}_price.json"
    if os.path.exists(fp):
        d = json.load(open(fp))
    else:
        d = {"success": True, "symbol": sym, "prices": [], "count": 0}

    existing_dates = {p["trade_date"] for p in d["prices"]}
    added = 0
    for r in by_symbol.get(sym, []):
        trade_date = (r.get("TradeDate") or "")[:10]
        if not trade_date or trade_date in existing_dates:
            continue  # never overwrite an existing (Kobo-sourced) row for the same date
        d["prices"].append({
            "symbol": sym,
            "trade_date": trade_date,
            "open_price": r.get("OpeningPrice"),
            "high_price": r.get("HighPrice"),
            "low_price": r.get("LowPrice"),
            "close_price": r.get("ClosePrice"),
            "volume": r.get("Volume"),
        })
        existing_dates.add(trade_date)
        added += 1

    if added:
        d["prices"].sort(key=lambda p: p["trade_date"])
        d["count"] = len(d["prices"])
        json.dump(d, open(fp, "w"))
        total_added += added
        print(f"{sym}: added {added} day(s) from the free NGX-native source")

print(f"\nDone. {total_added} total day(s) added across the watchlist.")
print("This runs safely every day regardless of whether Kobo is still working -")
print("it only ever fills genuine gaps, never touches a date that's already there.")
