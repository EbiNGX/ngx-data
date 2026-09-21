import json
from urllib.request import Request, urlopen

# One-time backfill - run this once to get the full history, then never again.
# Ongoing updates after this happen via ngx_own_data_update.py instead.
URL = ("https://doclib.ngxgroup.com/_api/Web/Lists/GetByTitle('XFinancial_News')/items/"
       "?$select=URL,Modified,Created,CompanyName,CompanySymbol,InternationSecIN,Type_of_Submission"
       "&$orderby=Created%20desc"
       "&$top=50000")

headers = {"Accept": "application/json;odata=verbose", "User-Agent": "Mozilla/5.0"}

def extract_records(data):
    # SharePoint's OData response shape varies by server config - handle both
    if isinstance(data, dict) and "d" in data and "results" in data["d"]:
        return data["d"]["results"]
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    if isinstance(data, list):
        return data
    return []

req = Request(URL, headers=headers)
with urlopen(req) as r:
    raw = json.loads(r.read())

records = extract_records(raw)
print(f"Retrieved {len(records)} disclosure records")
if records:
    dates = sorted(r.get("Modified", "") for r in records if r.get("Modified"))
    print(f"Date range: {dates[0]} to {dates[-1]}")

with open("ngx_disclosures_full_history.json", "w") as f:
    json.dump(records, f)
print("Saved to ngx_disclosures_full_history.json")