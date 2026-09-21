import json, os, time
from urllib.request import Request, urlopen

headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

OUTFILE = "mystocks_dividend_calendar.json"

def fetch_calendar(symbol):
    url = f"https://mystocks.africa/api/v1/dividends/calendar?symbol={symbol}.NG"
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"{symbol}: FAILED - {e}")
        return None

existing = json.load(open(OUTFILE)) if os.path.exists(OUTFILE) else []
existing_ids = {r["id"] for r in existing if isinstance(r, dict) and "id" in r}

total_added = 0
for sym in WATCHLIST:
    data = fetch_calendar(sym)
    if data is None:
        time.sleep(2)
        continue
    # response may be a bare list or wrapped - handle both defensively
    records = data if isinstance(data, list) else data.get("data", data.get("results", []))
    if not isinstance(records, list):
        print(f"{sym}: unexpected response shape - {type(records)}, skipping")
        time.sleep(2)
        continue

    added = [r for r in records if isinstance(r, dict) and r.get("id") not in existing_ids]
    if added:
        existing.extend(added)
        for r in added:
            existing_ids.add(r.get("id"))
        total_added += len(added)
        # flag anything with a real forward-looking lifecycle stage - the whole point
        # of this endpoint over what we already had from Kobo/stockanalysis
        KNOWN_PAST_STAGES = {"PAID", "CANCELLED", "PAYMENT_DATE_PASSED"}
        upcoming = [r for r in added if (r.get("calendarStage") or "").upper() not in KNOWN_PAST_STAGES]
        if upcoming:
            for u in upcoming:
                print(f"  {sym}: UPCOMING - {u.get('exDividendDate')} amount={u.get('amount')} "
                      f"stage={u.get('calendarStage')} status={u.get('status')}")
    else:
        print(f"{sym}: no new dividend calendar entries")
    time.sleep(2)  # respectful pacing - this is a live site, not a documented public API

json.dump(existing, open(OUTFILE, "w"))
print(f"\nDone. Added {total_added} new record(s) this run. {len(existing)} total in {OUTFILE}")