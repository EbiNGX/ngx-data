import json, os, time
from urllib.request import Request, urlopen

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://stockanalysis.com/",
}

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

OUTFILE = "stockanalysis_full_statements.json"

# Verified byte-identical against real ARADEL payloads before this went live -
# same resolver already proven correct on the ratios endpoint, confirmed to work
# unchanged on income statement, balance sheet, and cash flow too.
def resolve(data, idx, depth=0, max_depth=12):
    if depth > max_depth or idx is None or idx < 0:
        return None
    val = data[idx]
    if isinstance(val, list):
        return [resolve(data, i, depth + 1) for i in val]
    elif isinstance(val, dict):
        return {k: resolve(data, i, depth + 1) for k, i in val.items()}
    else:
        return val

def resolve_field(data, field_map, field_name):
    idx = field_map.get(field_name)
    if idx is None or idx < 0:
        return None
    return resolve(data, idx)

def fetch_data_json(url):
    req = Request(url, headers=headers)
    with urlopen(req) as r:
        return json.loads(r.read())

# Fields confirmed present in each statement's real payload for Aradel -
# core summary lines, not every granular sub-item (those resist reliable
# automated extraction, per the earlier AFRINSURE PDF-table findings).
STATEMENT_FIELDS = {
    "income-statement": ["revenue", "cor", "gp", "sgna", "opex", "opinc",
        "interestExpense", "pretax", "taxexp", "netinc", "epsBasic", "epsdil",
        "ebitda", "grossMargin", "operatingMargin", "profitMargin"],
    "balance-sheet": ["cashneq", "totalcash", "receivables", "inventory", "assetsc",
        "netPPE", "assets", "accountsPayable", "debtc", "currentLiabilities",
        "debtnc", "liabilities", "retearn", "equity", "sharesOutTotalCommon"],
    "cash-flow-statement": ["netIncomeCF", "ncfo", "capex", "ncfi", "ncff", "ncf",
        "fcf", "commonDividendCF"],
}

def extract_statement(symbol, statement_type):
    url = f"https://stockanalysis.com/quote/ngx/{symbol}/financials/{statement_type}/__data.json"
    raw = fetch_data_json(url)
    fin_data = raw["nodes"][2]["data"]
    root_map = fin_data[0]
    fd_idx = root_map.get("financialData")
    if fd_idx is None:
        return {"error": "no financialData found"}
    fd_map = fin_data[fd_idx]

    result = {"fiscal_periods": resolve_field(fin_data, fd_map, "datekey")}
    for field in STATEMENT_FIELDS[statement_type]:
        result[field] = resolve_field(fin_data, fd_map, field)
    return result

existing = json.load(open(OUTFILE)) if os.path.exists(OUTFILE) else {}

for sym in WATCHLIST:
    print(f"{sym}: fetching...")
    ticker_result = {}
    for statement_type in ["income-statement", "balance-sheet", "cash-flow-statement"]:
        try:
            ticker_result[statement_type.replace("-", "_")] = extract_statement(sym, statement_type)
            time.sleep(2)
        except Exception as e:
            ticker_result[statement_type.replace("-", "_")] = {"error": str(e)}
            time.sleep(2)
    existing[sym] = ticker_result
    rev = ticker_result.get("income_statement", {}).get("revenue")
    print(f"  revenue (TTM..5yr): {rev}")
    json.dump(existing, open(OUTFILE, "w"))  # save after every ticker, not just at the end

print(f"\nDone. Saved to {OUTFILE}")
