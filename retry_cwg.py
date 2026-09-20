import os, json
from urllib.request import Request, urlopen

KEY = os.environ["KOBO_KEY"]
headers = {"X-API-Key": KEY, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def fetch(name, url):
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as r:
            data = json.loads(r.read())
        with open(f"{name}.json", "w") as f:
            json.dump(data, f)
        print(name, "saved")
    except Exception as e:
        print(name, "FAILED:", e)

# --- 1. MBENEFIT and TANTALIZER: correct tickers confirmed via Meristem/disclosures,
#     never actually retried against the API with the fixed symbols ---
for sym in ["MBENEFIT", "TANTALIZER"]:
    fetch(f"{sym}_price", f"https://koboterminal.com/api/ngxdata/prices/{sym}?from=2000-01-01")
    fetch(f"{sym}_fundamentals", f"https://koboterminal.com/api/ngxdata/fundamentals/{sym}")
    fetch(f"{sym}_dividends", f"https://koboterminal.com/api/ngxdata/dividends/{sym}")

# --- 2. BETAGLAS dividends: price and fundamentals were pulled earlier, dividends never was ---
fetch("BETAGLAS_dividends", "https://koboterminal.com/api/ngxdata/dividends/BETAGLAS")

# --- 3. NASCON dividends: requested in an earlier batch but never actually came back ---
fetch("NASCON_dividends", "https://koboterminal.com/api/ngxdata/dividends/NASCON")

# --- 4. The two items from an earlier combined pull that never returned ---
fetch("index_ngx-ind", "https://koboterminal.com/api/ngxdata/indices/ngx-ind/history?from=2024-01-01")
fetch("news", "https://koboterminal.com/api/news")

# --- 5. REITs - newly identified this session, zero API data pulled on any of them yet ---
for sym in ["UPDCREIT", "UHOMREIT", "NREIT", "SFSREIT"]:
    fetch(f"{sym}_price", f"https://koboterminal.com/api/ngxdata/prices/{sym}?from=2000-01-01")
    fetch(f"{sym}_fundamentals", f"https://koboterminal.com/api/ngxdata/fundamentals/{sym}")
    fetch(f"{sym}_dividends", f"https://koboterminal.com/api/ngxdata/dividends/{sym}")

# --- 6. CWG price: one more attempt. This is a long shot - we already confirmed this
#     endpoint throws a genuine 500 server error specific to this symbol, not a wrong-ticker
#     issue, since fundamentals/dividends work fine under the same symbol. Included in case
#     it's been fixed since; if it fails again, that's expected, not a new problem.
fetch("CWG_price_retry2", "https://koboterminal.com/api/ngxdata/prices/CWG?from=2000-01-01")