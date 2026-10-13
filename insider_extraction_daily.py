import fitz
import json, re, time, csv, os
from urllib.request import Request, urlopen

# OCR fallback for scanned PDFs (like several ZenithBank dealings, WAPIC, NPFMCRFBK,
# OKOMUOIL forms we've had to skip entirely until now) - only imported if available,
# so this script still runs fine without it, just without the OCR capability.
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

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

    # If native extraction got almost nothing, this is likely a scanned image -
    # try OCR before giving up, rather than just flagging and moving on.
    if len(text.strip()) < 100 and OCR_AVAILABLE:
        try:
            images = convert_from_path(pdf_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            if len(ocr_text.strip()) > len(text.strip()):
                return ocr_text, True  # (text, was_ocr_used)
        except Exception:
            pass  # OCR attempt failed - fall through to the original (likely empty) text
    return text, False

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

DISCLOSURES_FILE = "ngx_disclosures_full_history.json"
OUTFILE = "insider_extraction_full.csv"
FIELDNAMES = ["insider_name","position","nature","volume","price","transaction_date",
              "raw_text_length","likely_scanned","extracted_via_ocr","symbol","filing_date","source_url"]

if not os.path.exists(DISCLOSURES_FILE):
    print(f"{DISCLOSURES_FILE} not found - run ngx_own_data_update.py first")
    exit()

d = json.load(open(DISCLOSURES_FILE))

# Figure out what's already been extracted, and the most recent filing date covered -
# only look for genuinely new filings past that point, never rescan everything.
already_done = set()
last_filing_date = "2024-01-01T00:00:00Z"
if os.path.exists(OUTFILE):
    with open(OUTFILE, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            url = row.get("source_url")
            if url:
                already_done.add(url)
            fd = row.get("filing_date", "")
            if fd > last_filing_date:
                last_filing_date = fd

print(f"Existing extractions: {len(already_done)}, checking for filings after {last_filing_date}")

raw_targets = [r for r in d
               if (r.get('CompanySymbol') or '').strip() in WATCHLIST
               and r.get('Modified','') > last_filing_date
               and is_real_dealing(r)]

# Dedupe by URL within this batch too - NGX's own index has confirmed genuine
# duplicate entries (one real filing logged under 70 separate index records).
seen_urls = set()
targets = []
for r in raw_targets:
    url = r.get("URL", {}).get("Url")
    if url and url not in seen_urls and url not in already_done:
        seen_urls.add(url)
        targets.append(r)

print(f"New filings to process: {len(targets)}")

if not targets:
    print("Nothing new today.")
    exit()

file_exists = os.path.exists(OUTFILE)
mode = "a" if file_exists else "w"
with open(OUTFILE, mode, newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if not file_exists:
        w.writeheader()

    for r in targets:
        url = r.get("URL", {}).get("Url")
        try:
            download_pdf(url, "temp.pdf")
            text, was_ocr_used = extract_text("temp.pdf")
            parsed = parse_directors_dealing(text)
            parsed["symbol"] = r.get("CompanySymbol")
            parsed["filing_date"] = r.get("Modified")
            parsed["source_url"] = url
            parsed["extracted_via_ocr"] = was_ocr_used
            w.writerow(parsed)
            f.flush()
            already_done.add(url)
            ocr_note = " (via OCR)" if was_ocr_used else ""
            print(f"  {parsed['symbol']}: {parsed.get('insider_name') or '(scanned/unparsed)'} "
                  f"- {parsed.get('nature')}{ocr_note}")
        except Exception as e:
            print(f"{r.get('CompanySymbol')}: FAILED - {e}")
        time.sleep(2)

print(f"\nDone. {len(targets)} new filing(s) processed.")
