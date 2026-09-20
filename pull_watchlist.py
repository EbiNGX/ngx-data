import os, json
from urllib.request import Request, urlopen

KEY = os.environ["KOBO_KEY"]
headers = {"X-API-Key": KEY, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def fetch_if_missing(name, url):
    filename = f"{name}.json"
    if os.path.exists(filename):
        print(name, "SKIPPED - already on disk, not touching it")
        return
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as r:
            data = json.loads(r.read())
        with open(filename, "w") as f:
            json.dump(data, f)
        print(name, "saved")
    except Exception as e:
        print(name, "FAILED:", e)

# --- 1. Dividend history missing for these 21 tickers ---
missing_dividends = ["ACCESSCORP","AIICO","BUACEMENT","BUAFOODS","CHAMS","CUSTODIAN","CUTIX",
    "DANGCEM","DANGSUGAR","FIDSON","GTCO","NAHCO","NASCON","NEM","NGXGROUP","NPFMCRFBK",
    "OKOMUOIL","PRESCO","SEPLAT","TIP","UBA","UCAP"]
for sym in missing_dividends:
    fetch_if_missing(f"{sym}_dividends", f"https://koboterminal.com/api/ngxdata/dividends/{sym}")

# --- 2. NREIT fundamentals - only piece missing for this one ---
fetch_if_missing("NREIT_fundamentals", "https://koboterminal.com/api/ngxdata/fundamentals/NREIT")

# --- 3. Sector indices: retry the one that failed, test three unconfirmed guesses ---
fetch_if_missing("index_ngx-ind", "https://koboterminal.com/api/ngxdata/indices/ngx-ind/history?from=2024-01-01")
for code in ["ngx-ins", "ngx-tel", "ngx-cong"]:
    fetch_if_missing(f"index_{code}", f"https://koboterminal.com/api/ngxdata/indices/{code}/history?from=2024-01-01")

# --- 4. Test whether disclosures respects a date range - only ran once before, bare ---
fetch_if_missing("disclosures_datetest", "https://koboterminal.com/api/ngxdata/disclosures?from=2015-01-01")