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

fetch("all_stocks_master_list", "https://koboterminal.com/api/ngxdata/stocks")
fetch("all_fundamentals_bulk", "https://koboterminal.com/api/ngxdata/fundamentals")
fetch("all_identifiers_bulk", "https://koboterminal.com/api/ngxdata/identifiers?limit=500")