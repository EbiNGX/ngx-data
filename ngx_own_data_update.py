import json, os
from datetime import datetime
from urllib.parse import quote
from urllib.request import Request, urlopen

headers = {"Accept": "application/json;odata=verbose", "User-Agent": "Mozilla/5.0"}

def get_json(url):
    req = Request(url, headers=headers)
    with urlopen(req) as r:
        return json.loads(r.read())

def extract_records(data):
    if isinstance(data, dict) and "d" in data and "results" in data["d"]:
        return data["d"]["results"]
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    if isinstance(data, list):
        return data
    return []

# ---------- PART 1: incremental disclosures update ----------
DISCLOSURES_FILE = "ngx_disclosures_full_history.json"

if os.path.exists(DISCLOSURES_FILE):
    existing = json.load(open(DISCLOSURES_FILE))
    known_urls = {r["URL"]["Url"] for r in existing if isinstance(r.get("URL"), dict) and "Url" in r["URL"]}
    last_date = max((r.get("Modified", "") for r in existing if r.get("Modified")), default="2014-01-01T00:00:00.000Z")

    filter_clause = quote(f"Modified ge '{last_date}'")
    url = (
        "https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('XFinancial_News')/items/"
        "?$select=URL,Modified,Created,CompanyName,CompanySymbol,InternationSecIN,Type_of_Submission"
        "&$orderby=Created%20desc"
        f"&$filter={filter_clause}"
        "&$top=1000"
    )
    try:
        new_records = extract_records(get_json(url))
        added = [r for r in new_records
                 if isinstance(r.get("URL"), dict) and r["URL"].get("Url") not in known_urls]
        if added:
            existing.extend(added)
            json.dump(existing, open(DISCLOSURES_FILE, "w"))
            print(f"Disclosures: added {len(added)} new record(s), {len(existing)} total")
        else:
            print("Disclosures: no new records")
    except Exception as e:
        print(f"Disclosures: FAILED - {e}")
else:
    print(f"Disclosures: {DISCLOSURES_FILE} not found - run ngx_disclosures_backfill.py first")

# ---------- PART 2: daily equities price-list snapshot ----------
PRICELIST_FILE = "ngx_equities_pricelist_history.json"
PRICELIST_URL = "https://doclib.ngxgroup.com/REST/api/statistics/equities/?market=&sector=&orderby=&pageSize=300&pageNo=0"

try:
    today_data = get_json(PRICELIST_URL)
    today_records = extract_records(today_data) if not isinstance(today_data, list) else today_data
    if not today_records and isinstance(today_data, dict):
        today_records = today_data.get("Result", today_data.get("Data", []))

    if os.path.exists(PRICELIST_FILE):
        history = json.load(open(PRICELIST_FILE))
    else:
        history = []

    existing_keys = {(r.get("Symbol"), r.get("TradeDate")) for r in history}
    added = [r for r in today_records if (r.get("Symbol"), r.get("TradeDate")) not in existing_keys]
    if added:
        history.extend(added)
        json.dump(history, open(PRICELIST_FILE, "w"))
        print(f"Equities price list: added {len(added)} record(s) for {added[0].get('TradeDate')}, {len(history)} total rows in history")
    else:
        print("Equities price list: today's session already saved, no new rows")
except Exception as e:
    print(f"Equities price list: FAILED - {e}")