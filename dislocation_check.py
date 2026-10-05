import os, json

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM","NIDF","NASCON","MCNICHOLS"]

# Ported directly from daily_update.py's check_dislocation() - identical logic,
# zero Kobo dependency. Reads only {SYM}_price.json, which bridge_price_data.py
# keeps current for free from the NGX-native source now that Kobo is retired.
def check_dislocation(sym, flat_threshold_days=5, volume_threshold=100_000):
    filename = f"{sym}_price.json"
    if not os.path.exists(filename):
        return None
    data = json.load(open(filename))
    prices = sorted(data.get("prices", []), key=lambda p: p["trade_date"])
    if len(prices) < flat_threshold_days + 1:
        return None
    closes = [p["close_price"] for p in prices]
    vols = [p.get("volume", 0) or 0 for p in prices]
    n = len(closes)
    i = n - 1
    while i > 0 and closes[i] == closes[i - 1]:
        i -= 1
    flat_days = n - 1 - i
    if flat_days < flat_threshold_days:
        return None
    cum_volume = sum(vols[i + 1:])
    if cum_volume >= volume_threshold:
        return {"symbol": sym, "flat_days": flat_days,
                "cum_volume_during_freeze": cum_volume,
                "stale_price": closes[-1], "since": prices[i]["trade_date"]}
    return None

alerts = []
for sym in WATCHLIST:
    alert = check_dislocation(sym)
    if alert:
        alerts.append(alert)

if alerts:
    print(f"DISLOCATION ALERTS - {len(alerts)} ticker(s):")
    for a in alerts:
        print(f"  {a['symbol']}: frozen at {a['stale_price']} for {a['flat_days']} days "
              f"(since {a['since']}), but {a['cum_volume_during_freeze']:,} shares traded "
              f"during that stretch - the published price is very likely stale")
else:
    print("Dislocation check: no alerts today")

summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
if summary_path:
    with open(summary_path, "a") as f:
        if alerts:
            f.write("## DISLOCATION ALERTS - check Meristem for these\n\n")
            for a in alerts:
                f.write(f"- **{a['symbol']}**: frozen at {a['stale_price']} for {a['flat_days']} days "
                        f"(since {a['since']}), but {a['cum_volume_during_freeze']:,} shares traded "
                        f"during that stretch - the published price is very likely stale\n")
        else:
            f.write("## Dislocation check: no alerts today\n")
