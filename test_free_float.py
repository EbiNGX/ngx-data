import json, re, time, csv
import pdfplumber
from urllib.request import Request, urlopen

def download_pdf(url, out_path):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as r:
        data = r.read()
    with open(out_path, "wb") as f:
        f.write(data)

def extract_free_float(pdf_path):
    """Searches every page's tables (flattened to text) for the confirmed
    reliable narrative pattern: 'free float percentage of X%... free float
    value of NX' - found in a "Results at a Glance" style summary page.
    Not every Financial Statement filing includes this section - many will
    correctly return None, that's an honest limitation, not a bug."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    for cell in row:
                        if cell:
                            full_text += str(cell) + " "
            # also grab plain page text as a fallback, in case the free-float
            # sentence sits outside a detected table on some filings
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + " "

    pct_match = re.search(r"free float percentage of\s*([\d.]+)\s*%", full_text, re.IGNORECASE)
    val_match = re.search(r"free float value of\s*[₦N]\s*([\d,]+\.?\d*)", full_text, re.IGNORECASE)

    return {
        "free_float_pct": float(pct_match.group(1)) if pct_match else None,
        "free_float_value": float(val_match.group(1).replace(",", "")) if val_match else None,
    }

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

d = json.load(open("ngx_disclosures_full_history.json"))

# Test batch: only the MOST RECENT Financial Statement per ticker, 44 attempts total.
# pdfplumber's table detection is meaningfully slower than plain text extraction -
# testing bounded and small before ever considering the full historical set.
targets = []
for sym in WATCHLIST:
    matches = [r for r in d if (r.get('CompanySymbol') or '').strip() == sym
               and (r.get('Type_of_Submission') or '').strip() == 'Financial Statements']
    if matches:
        most_recent = max(matches, key=lambda r: r.get('Modified',''))
        targets.append(most_recent)

print(f"Testing {len(targets)} filings (most recent Financial Statement per ticker)")

results = []
for i, r in enumerate(targets):
    sym = r.get('CompanySymbol')
    url = r.get("URL", {}).get("Url")
    try:
        download_pdf(url, "temp.pdf")
        ff = extract_free_float("temp.pdf")
        ff["symbol"] = sym
        ff["filing_date"] = r.get("Modified")
        ff["source_url"] = url
        results.append(ff)
        found = "FOUND" if ff["free_float_pct"] is not None else "not present in this filing"
        print(f"  [{i+1}/{len(targets)}] {sym}: {found} - pct={ff['free_float_pct']} value={ff['free_float_value']}")
    except Exception as e:
        print(f"  [{i+1}/{len(targets)}] {sym}: FAILED - {e}")
    time.sleep(2)

with open("free_float_test.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["symbol","free_float_pct","free_float_value","filing_date","source_url"])
    w.writeheader()
    w.writerows(results)

found_count = sum(1 for r in results if r["free_float_pct"] is not None)
print(f"\nDone. Found free-float data in {found_count} of {len(results)} filings. Saved to free_float_test.csv")
