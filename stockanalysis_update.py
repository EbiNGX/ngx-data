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

OUTFILE = "stockanalysis_fundamentals.json"

def resolve(data, idx, depth=0, max_depth=12):
    """SvelteKit devalue format: every field maps to an index into the same flat
    array. If that position holds a list, each element is itself a reference to
    resolve recursively; if a dict, each value is a reference. Anything else
    (string/number/bool/null) is a leaf - confirmed by manually tracing real
    payloads (e.g. roe -> [150..155] -> [0.44294, 0.42639, ...]) and verified
    against real data before this went live."""
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
    """Resolve only ONE named field's reference chain, not the whole object -
    verified necessary: eagerly resolving the full root object also walks into
    unrelated huge structures (like the complete price chart) just to read a
    single scalar like peRatio. This avoids that entirely."""
    idx = field_map.get(field_name)
    if idx is None or idx < 0:
        return None
    return resolve(data, idx)

def fetch_data_json(url):
    req = Request(url, headers=headers)
    with urlopen(req) as r:
        return json.loads(r.read())

def extract_fundamentals(symbol):
    quote_url = f"https://stockanalysis.com/quote/ngx/{symbol}/__data.json"
    ratios_url = f"https://stockanalysis.com/quote/ngx/{symbol}/financials/ratios/__data.json"

    result = {"symbol": symbol}

    try:
        quote_raw = fetch_data_json(quote_url)
        quote_data = quote_raw["nodes"][2]["data"]
        field_map = quote_data[0]  # the field-name -> index map, NOT resolved yet
        for out_key, field_name in [
            ("market_cap","marketCap"), ("revenue","revenue"), ("net_income","netIncome"),
            ("shares_out","sharesOut"), ("eps","eps"), ("eps_growth","epsGrowth"),
            ("pe_ratio","peRatio"), ("forward_pe","forwardPE"), ("dividend","dividend"),
            ("ex_dividend_date","exDividendDate"), ("beta","beta"),
            ("earnings_date","earningsDate"), ("dps","dps"),
            ("dividend_yield_quote_page","dividendYield"),
            ("payout_ratio_quote_page","payoutRatio"),
        ]:
            result[out_key] = resolve_field(quote_data, field_map, field_name)
    except Exception as e:
        result["quote_page_error"] = str(e)

    try:
        ratios_raw = fetch_data_json(ratios_url)
        ratios_data = ratios_raw["nodes"][2]["data"]
        root_map = ratios_data[0]
        fd_idx = root_map.get("financialData")
        fd_map = ratios_data[fd_idx] if fd_idx is not None else {}
        # Each of these resolves to a list: [TTM, FY-1, FY-2, ...] - full history kept,
        # TTM (most current) also surfaced separately for easy use.
        for field in ["pe", "pb", "roe", "roa", "roic", "roce", "debtequity",
                       "currentratio", "quickRatio", "assetturnover",
                       "dividendyield", "payoutratio", "earningsyield", "fcfyield"]:
            series = resolve_field(ratios_data, fd_map, field)
            if series is not None:
                result[f"{field}_history_ttm_first"] = series
                result[f"{field}_ttm"] = series[0] if isinstance(series, list) and series else None
        result["fiscal_periods"] = resolve_field(ratios_data, fd_map, "datekey")
    except Exception as e:
        result["ratios_page_error"] = str(e)

    return result

existing = json.load(open(OUTFILE)) if os.path.exists(OUTFILE) else {}

for sym in WATCHLIST:
    print(f"{sym}: fetching...")
    try:
        result = extract_fundamentals(sym)
        existing[sym] = result
        pe = result.get("pe_ratio")
        roe = result.get("roe_ttm")
        print(f"  PE={pe}  ROE(TTM)={roe}")
    except Exception as e:
        print(f"  FAILED - {e}")
    time.sleep(2)  # respectful pacing - this is a live website, not a documented public API
    json.dump(existing, open(OUTFILE, "w"))  # save after every ticker, not just at the end

print(f"\nDone. Saved to {OUTFILE}")