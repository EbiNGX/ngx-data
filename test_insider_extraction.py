import fitz
import json, re, time, csv, os
from urllib.request import Request, urlopen

def download_pdf(url, out_path):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as r:
        data = r.read()
    with open(out_path, "wb") as f:
        f.write(data)

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def parse_directors_dealing(text):
    def find_line(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    block_match = re.search(r"Details of the Director/Insider(.*?)(?:\n\s*2\.|\Z)",
                             text, re.IGNORECASE | re.DOTALL)
    insider_name = None
    if block_match:
        name_match = re.search(r"Name\s*\n\s*(.+)", block_match.group(1))
        insider_name = name_match.group(1).strip() if name_match else None

    position = find_line(r"Position/status\s*\n\s*(.+)")
    nature = find_line(r"Nature of the transaction\s*\n\s*(.+)")

    pv_match = re.search(r"Price\(s\) and volume\(s\)\s*\n\s*([\d,]+)\s*units?\s*at\s*N?([\d,.]+)\s*per\s*share",
                          text, re.IGNORECASE)
    volume = pv_match.group(1) if pv_match else None
    price = pv_match.group(2) if pv_match else None

    transaction_date = find_line(r"Date of Transaction\s*\n\s*(.+)")

    return {
        "insider_name": insider_name,
        "position": position,
        "nature": nature,
        "volume": volume,
        "price": price,
        "transaction_date": transaction_date,
        "raw_text_length": len(text),
        "likely_scanned": len(text.strip()) < 100,
    }

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

KEYWORDS = ['dealing', 'pdmr', 'insider', r'director.*shar', r'shar.*purchas', r'shar.*sal']

def is_real_dealing(r):
    t = (r.get('Type_of_Submission') or '').strip().lower()
    if 'directorsdealing' in t:
        return True
    desc = (r.get('URL', {}).get('Description') or '')
    return any(re.search(kw, desc, re.IGNORECASE) for kw in KEYWORDS)

d = json.load(open("ngx_disclosures_full_history.json"))
targets = [r for r in d
           if (r.get('CompanySymbol') or '').strip() in WATCHLIST
           and r.get('Modified','') >= '2024-01-01'
           and is_real_dealing(r)]

OUTFILE = "insider_extraction_full.csv"
FIELDNAMES = ["insider_name","position","nature","volume","price","transaction_date",
              "raw_text_length","likely_scanned","symbol","filing_date","source_url"]

# Resume-safe: if this file already exists from a previous partial run, skip
# whatever URLs are already in it instead of redoing completed work.
already_done = set()
file_exists = os.path.exists(OUTFILE)
if file_exists:
    with open(OUTFILE, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            already_done.add(row.get("source_url"))
    print(f"Resuming - {len(already_done)} filings already saved from a previous run, skipping those")

mode = "a" if file_exists else "w"
with open(OUTFILE, mode, newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if not file_exists:
        w.writeheader()

    print(f"Processing {len(targets)} matching filings - this will take a while, don't close the window")
    done_count = 0
    for i, r in enumerate(targets):
        url = r.get("URL", {}).get("Url")
        if not url or url in already_done:
            continue
        try:
            download_pdf(url, "temp.pdf")
            text = extract_text("temp.pdf")
            parsed = parse_directors_dealing(text)
            parsed["symbol"] = r.get("CompanySymbol")
            parsed["filing_date"] = r.get("Modified")
            parsed["source_url"] = url
            w.writerow(parsed)
            f.flush()  # write to disk immediately - never lose more than one row
            done_count += 1
            if done_count % 25 == 0:
                print(f"  ...{done_count} newly processed (of {len(targets)-len(already_done)} remaining)")
        except Exception as e:
            print(f"{r.get('CompanySymbol')}: FAILED - {e}")
        time.sleep(2)

print(f"\nDone. Saved to {OUTFILE}")