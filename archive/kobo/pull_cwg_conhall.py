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

for sym in ["CWG", "CONHALLPLC"]:
    fetch(f"{sym}_price", f"https://koboterminal.com/api/ngxdata/prices/{sym}?from=2000-01-01")
    fetch(f"{sym}_fundamentals", f"https://koboterminal.com/api/ngxdata/fundamentals/{sym}")
    fetch(f"{sym}_dividends", f"https://koboterminal.com/api/ngxdata/dividends/{sym}")