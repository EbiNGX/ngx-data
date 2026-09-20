import os, json
from urllib.request import Request, urlopen

headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# All confirmed via live browser Network-tab inspection - plain public GET, no auth,
# no cookies required. Each record carries a unique "id" field, used below for safe dedup.
ENDPOINTS = {
    "cbn_inflation": "https://www.cbn.gov.ng/api/GetAllInflationRates",
    "cbn_money_market": "https://www.cbn.gov.ng/api/GetAllMoneyMarketIndicators",
    "cbn_securities_ntb": "https://www.cbn.gov.ng/api/GetAllSecuritiesNTB",
    "cbn_securities_fgnbond": "https://www.cbn.gov.ng/api/GetAllSecuritiesFGNBond",
    "cbn_securities_omo": "https://www.cbn.gov.ng/api/GetAllSecuritiesOMO",
    "cbn_securities_cbnbill": "https://www.cbn.gov.ng/api/GetAllSecuritiesCBNBill",
    "cbn_interbank": "https://www.cbn.gov.ng/api/GetAllInterbankRates?format=json",
    "cbn_reserves": "https://www.cbn.gov.ng/api/GetAllReserves?format=json",
}

def fetch_and_merge(name, url):
    filename = f"{name}.json"
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as r:
            new_records = json.loads(r.read())
    except Exception as e:
        print(f"{name}: FAILED - {e}")
        return

    if not isinstance(new_records, list):
        print(f"{name}: unexpected response shape - {type(new_records)}, saving raw for inspection")
        json.dump(new_records, open(filename, "w"))
        return

    if os.path.exists(filename):
        existing = json.load(open(filename))
        existing_ids = {r["id"] for r in existing if "id" in r}
        added = [r for r in new_records if r.get("id") not in existing_ids]
        if added:
            existing.extend(added)
            json.dump(existing, open(filename, "w"))
            print(f"{name}: added {len(added)} new record(s), {len(existing)} total")
        else:
            print(f"{name}: no new records ({len(existing)} total, unchanged)")
    else:
        json.dump(new_records, open(filename, "w"))
        print(f"{name}: saved fresh, {len(new_records)} records")

    # Flag if the row count looks suspiciously small - a sign the API added pagination
    # or changed behavior server-side, since these calls are currently confirmed to
    # return the full unfiltered dataset in one response.
    final = json.load(open(filename))
    if len(final) < 50 and name != "cbn_reserves":
        print(f"  ⚠ {name} has only {len(final)} records - worth double-checking this "
              f"wasn't silently paginated by CBN's API")

for name, url in ENDPOINTS.items():
    fetch_and_merge(name, url)
