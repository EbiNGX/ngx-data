import os, sys, json, time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen

KEY = os.environ["KOBO_KEY"]
headers = {"X-API-Key": KEY, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}
STATE_FILE = "pull_schedule_state.json"

# Full 44-ticker universe - matches the disclosures pipeline exactly.
# FTGINSURE deliberately excluded: every data source for it contradicted itself.
TICKERS = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

summary_lines = []
fail_count = 0
success_count = 0
dislocation_alerts = []

def load_state():
    return json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

def days_since(state, key):
    if key not in state:
        return 9999
    return (datetime.now() - datetime.strptime(state[key], "%Y-%m-%d")).days

def get_json(url):
    with urlopen(Request(url, headers=headers)) as r:
        return json.loads(r.read())

def log(line):
    print(line)
    summary_lines.append(line)

# ---------- DAILY: extend price history, never overwrite ----------
def append_new_prices(sym):
    global fail_count, success_count
    filename = f"{sym}_price.json"
    if not os.path.exists(filename):
        log(f"- {sym}: SKIPPED (no existing file - run the full historical pull for this ticker first)")
        return
    existing = json.load(open(filename))
    prices = existing.get("prices", [])
    if not prices:
        return
    last_date = max(p["trade_date"] for p in prices)
    from_date = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        new_data = get_json(f"https://koboterminal.com/api/ngxdata/prices/{sym}?from={from_date}")
    except Exception as e:
        log(f"- **{sym}: FAILED** - {e}")
        fail_count += 1
        return
    existing_dates = {p["trade_date"] for p in prices}
    added = [p for p in new_data.get("prices", []) if p["trade_date"] not in existing_dates]
    if added:
        prices.extend(added)
        existing["prices"], existing["count"] = prices, len(prices)
        json.dump(existing, open(filename, "w"))
        log(f"- {sym}: added {len(added)} new row(s)")
        success_count += 1
    else:
        log(f"- {sym}: no new rows since {last_date}")

# ---------- DISLOCATION CHECK: price+volume only, no bid/offer needed ----------
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

# ---------- Run daily price updates + dislocation scan across the full universe ----------
log("## Price updates\n")
for sym in TICKERS:
    append_new_prices(sym)
    alert = check_dislocation(sym)
    if alert:
        dislocation_alerts.append(alert)
    time.sleep(3.5)  # keeps 44 calls safely under the 20 req/min cap

state = load_state()
today = datetime.now().strftime("%Y-%m-%d")

# ---------- WEEKLY (every 7+ days): disclosures, news, sector indices ----------
if days_since(state, "weekly") >= 7:
    log("\n## Weekly pulls\n")
    for name, url in [(f"disclosures_{today}", "https://koboterminal.com/api/ngxdata/disclosures"),
                       (f"news_{today}", "https://koboterminal.com/api/news")]:
        try:
            json.dump(get_json(url), open(f"{name}.json", "w"))
            log(f"- {name}: saved")
            success_count += 1
        except Exception as e:
            log(f"- **{name}: FAILED** - {e}")
            fail_count += 1
        time.sleep(3.5)
    for code in ["ngx-30","ngx-bnk","ngx-cnsmrgds","ngx-oilgas","ngx-ins"]:
        fn = f"index_{code}.json"
        if os.path.exists(fn):
            existing = json.load(open(fn))
            hist = existing.get("history", [])
            last = max(h["date"] for h in hist) if hist else "2024-01-01"
            frm = (datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            try:
                new = get_json(f"https://koboterminal.com/api/ngxdata/indices/{code}/history?from={frm}")
                have = {h["date"] for h in hist}
                added = [h for h in new.get("history", []) if h["date"] not in have]
                hist.extend(added)
                existing["history"] = hist
                json.dump(existing, open(fn, "w"))
                log(f"- {code}: added {len(added)} new row(s)")
                success_count += 1
            except Exception as e:
                log(f"- **{code}: FAILED** - {e}")
                fail_count += 1
            time.sleep(3.5)
    state["weekly"] = today
    save_state(state)

# ---------- BIWEEKLY (every 14+ days): bond auctions ----------
if days_since(state, "biweekly") >= 14:
    log("\n## Biweekly pulls\n")
    try:
        json.dump(get_json("https://koboterminal.com/api/ngxdata/bonds/auctions?limit=100"),
                   open(f"bond_auctions_{today}.json", "w"))
        log("- bond_auctions: saved")
        success_count += 1
    except Exception as e:
        log(f"- **bond_auctions: FAILED** - {e}")
        fail_count += 1
    state["biweekly"] = today
    save_state(state)

# ---------- MONTHLY (every 30+ days): bulk fundamentals (1 call, not 44) + per-ticker dividends ----------
if days_since(state, "monthly") >= 30:
    log("\n## Monthly pulls\n")
    try:
        json.dump(get_json("https://koboterminal.com/api/ngxdata/fundamentals"),
                   open(f"all_fundamentals_bulk_{today}.json", "w"))
        log("- fundamentals (bulk, all tickers): saved")
        success_count += 1
    except Exception as e:
        log(f"- **fundamentals bulk: FAILED** - {e}")
        fail_count += 1
    time.sleep(3.5)
    for sym in TICKERS:
        try:
            json.dump(get_json(f"https://koboterminal.com/api/ngxdata/dividends/{sym}"),
                       open(f"{sym}_dividends_{today}.json", "w"))
            success_count += 1
        except Exception as e:
            log(f"- **{sym} dividends: FAILED** - {e}")
            fail_count += 1
        time.sleep(3.5)
    log("- dividends batch complete")
    state["monthly"] = today
    save_state(state)

# ---------- Write the GitHub run summary - dislocation alerts lead ----------
summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
if summary_path:
    with open(summary_path, "a") as f:
        f.write(f"# NGX Data Pull - {today}\n\n")
        if dislocation_alerts:
            f.write("## DISLOCATION ALERTS - check Meristem for these\n\n")
            for a in dislocation_alerts:
                f.write(f"- **{a['symbol']}**: frozen at {a['stale_price']} for {a['flat_days']} days "
                        f"(since {a['since']}), but {a['cum_volume_during_freeze']:,} shares traded "
                        f"during that stretch - the published price is very likely stale\n")
            f.write("\n")
        else:
            f.write("## Dislocation check: no alerts today\n\n")
        f.write(f"**{success_count} pulls succeeded, {fail_count} failed**\n\n")
        f.write("\n".join(summary_lines))

# Alert if more than half of all attempted calls failed - catches a tier downgrade
# or expired key even though the /market endpoint alone would keep succeeding forever
total_attempts = success_count + fail_count
if total_attempts > 0 and fail_count / total_attempts > 0.5:
    print(f"\nHARD FAILURE: {fail_count}/{total_attempts} calls failed - likely tier downgrade or expired key.")
    sys.exit(1)
