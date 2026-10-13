import fitz
import json, re, time, csv, os
from urllib.request import Request, urlopen

# OCR fallback for scanned dividend PDFs, same approach validated for insider dealings.
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

    if len(text.strip()) < 100 and OCR_AVAILABLE:
        try:
            images = convert_from_path(pdf_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img) + "\n"
            if len(ocr_text.strip()) > len(text.strip()):
                return ocr_text, True
        except Exception:
            pass
    return text, False

def parse_dividend(text):
    def find_block(pattern, max_len=60):
        """Captures up to the next known label, but capped at max_len as a safety
        net - confirmed necessary: companies that don't use the exact expected
        header (Seplat, UCAP, Unilever, Aradel all phrase things differently)
        caused the capture to run to the end of the document instead of stopping
        cleanly. A real date is always short; anything longer than max_len means
        the stopping keyword wasn't found, so truncate rather than dump everything."""
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        raw = m.group(1)
        joined = re.sub(r'\s*\n\s*', ' ', raw).strip()
        joined = re.sub(r'(\d)\s+(st|nd|rd|th)\b', r'\1\2', joined, flags=re.IGNORECASE)
        return joined[:max_len].strip()

    period_ended = find_block(
        r"(?:Period|Year) Ended\s*\n(.*?)(?:\n\s*Proposed Dividend|\Z)", max_len=40)

    proposed_dividend_text = find_block(
        r"Proposed Dividend\s*\n(.*?)(?:\n\s*Proposed Bonus|\n\s*Closure of Register|\n\s*Qualification Date|\Z)",
        max_len=2000)

    # Best-effort numeric amount, kept separate so a failed parse never loses the raw text.
    # Searches the FULL text, not just the "Proposed Dividend" sub-block - confirmed
    # necessary: Seplat's template doesn't use that section header the same way
    # UCAP/MTNN do, so gating the search on that sub-block missed Seplat entirely.
    # CRITICAL: kobo, naira, and US cents are three different scales - confirmed via real
    # samples that Custodian states amounts in kobo, MTNN in naira, and Seplat (dual
    # LSE/NGX listed) in US cents ("US5 cents", "US$0.03/share").
    naira_match = re.search(r"[₦N]\s*([\d,]+\.?\d*)\s*per", text, re.IGNORECASE)
    kobo_match = re.search(r"([\d,]+\.?\d*)\s*kobo", text, re.IGNORECASE)
    usd_match = re.search(r"US\$?\s*([\d,]+\.?\d*)\s*cents?", text, re.IGNORECASE)
    if not usd_match:
        # Fallback: some filings state cents in a parenthetical without "US" directly
        # attached (e.g. "US$0.03/share (3 cents per Ordinary Share)") - confirmed
        # via a real Seplat sample using this exact phrasing.
        usd_match = re.search(r"\((\d+\.?\d*)\s*cents?", text, re.IGNORECASE)
    amount_best_effort = None
    amount_usd_cents = None
    if naira_match:
        amount_best_effort = float(naira_match.group(1).replace(",", ""))
    elif kobo_match:
        amount_best_effort = float(kobo_match.group(1).replace(",", "")) / 100
    if usd_match:
        amount_usd_cents = float(usd_match.group(1).replace(",", ""))

    qualification_date = find_block(
        r"Qualification Date\s*\n(.*?)(?:\n\s*Payment Date|\Z)")
    payment_date = find_block(
        r"Payment Date\s*\n?(.*?)(?:\n\s*E-Dividend|\n\s*Date of Annual|\Z)")

    return {
        "period_ended": period_ended,
        "proposed_dividend_text": proposed_dividend_text,
        "amount_best_effort": amount_best_effort,
        "amount_usd_cents": amount_usd_cents,
        "qualification_date": qualification_date,
        "payment_date": payment_date,
        "raw_text_length": len(text),
        "likely_scanned": len(text.strip()) < 100,
    }

WATCHLIST = ["MTNN","ZENITHBANK","ARADEL","UACN","GTCO","NEM","UNILEVER","ETERNA",
    "MAYBAKER","CWG","MBENEFIT","BUACEMENT","BETAGLAS","SEPLAT","CONHALLPLC",
    "LEARNAFRCA","STANBIC","FIDSON","TRANSCORP","ACCESSCORP","ETI","PZ","UCAP",
    "UBA","UPDCREIT","FIRSTHOLDCO","AIICO","TIP","NGXGROUP","CUTIX","WAPIC",
    "OANDO","ROYALEX","INTBREW","CHAMS","NAHCO","TANTALIZER","NPFMCRFBK",
    "CUSTODIAN","DANGSUGAR","PRESCO","OKOMUOIL","BUAFOODS","DANGCEM"]

def is_real_dividend_declaration(r):
    """Confirmed against 10 real samples: excluding these three words correctly
    separated all 6 genuine declarations from all 4 false positives (unclaimed-
    dividend lists, an FX-rate notice, and a dividend policy announcement) -
    more reliable than requiring specific wording like 'interim' or 'final',
    which PZ's real title didn't even contain."""
    desc = (r.get('URL', {}).get('Description') or '').lower()
    if 'unclaimed' in desc or 'currency exchange' in desc or 'policy' in desc:
        return False
    return 'dividend' in desc

DISCLOSURES_FILE = "ngx_disclosures_full_history.json"
OUTFILE = "dividend_extraction_full.csv"
FIELDNAMES = ["period_ended","proposed_dividend_text","amount_best_effort","amount_usd_cents",
              "qualification_date","payment_date","raw_text_length","likely_scanned",
              "extracted_via_ocr","symbol","filing_date","source_url"]

if not os.path.exists(DISCLOSURES_FILE):
    print(f"{DISCLOSURES_FILE} not found - run ngx_own_data_update.py first")
    exit()

d = json.load(open(DISCLOSURES_FILE))

already_done = set()
seen_content = set()
last_filing_date = "2024-01-01T00:00:00Z"
if os.path.exists(OUTFILE):
    with open(OUTFILE, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            url = row.get("source_url")
            if url:
                already_done.add(url)
            seen_content.add((row.get("symbol"), row.get("period_ended"),
                              row.get("amount_best_effort"), row.get("amount_usd_cents")))
            fd = row.get("filing_date", "")
            if fd > last_filing_date:
                last_filing_date = fd

print(f"Existing extractions: {len(already_done)}, checking for filings after {last_filing_date}")

raw_targets = [r for r in d
               if (r.get('CompanySymbol') or '').strip() in WATCHLIST
               and r.get('Modified','') > last_filing_date
               and is_real_dividend_declaration(r)]

# NGX's own disclosures index contains genuine duplicate entries pointing to the
# same physical PDF (confirmed earlier for insider dealings). Dedupe by URL
# before processing.
seen_urls = set()
targets = []
for r in raw_targets:
    url = r.get("URL", {}).get("Url")
    if url and url not in seen_urls and url not in already_done:
        seen_urls.add(url)
        targets.append(r)

print(f"New dividend filings to process: {len(targets)}")

if not targets:
    print("Nothing new.")
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
            parsed = parse_dividend(text)
            parsed["symbol"] = r.get("CompanySymbol")
            parsed["filing_date"] = r.get("Modified")
            parsed["source_url"] = url
            parsed["extracted_via_ocr"] = was_ocr_used

            # Different URLs can still hold the same real content (confirmed:
            # DANGCEM/FIDSON/BUAFOODS each appeared twice under this exact
            # scenario) - skip writing if this symbol+period+amount combo is
            # already in the file, even though the URL itself is new.
            content_key = (parsed["symbol"], parsed.get("period_ended"),
                           parsed.get("amount_best_effort"), parsed.get("amount_usd_cents"))
            if content_key in seen_content:
                print(f"  {parsed['symbol']}: skipped - same period/amount already recorded under a different URL")
                already_done.add(url)
                time.sleep(2)
                continue
            seen_content.add(content_key)

            w.writerow(parsed)
            f.flush()
            already_done.add(url)
            ocr_note = " (via OCR)" if was_ocr_used else ""
            print(f"  {parsed['symbol']}: period={parsed.get('period_ended')} "
                  f"amount~{parsed.get('amount_best_effort')} usd_cents~{parsed.get('amount_usd_cents')} "
                  f"qual={parsed.get('qualification_date')}{ocr_note}")
        except Exception as e:
            print(f"{r.get('CompanySymbol')}: FAILED - {e}")
        time.sleep(2)

print(f"\nDone. {len(targets)} filing(s) processed.")
