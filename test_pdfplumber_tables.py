import json, pdfplumber, time
from urllib.request import Request, urlopen

d = json.load(open("ngx_disclosures_full_history.json"))

# Same AFRINSURE quarterly filings that broke plain text extraction earlier -
# testing extract_tables() against the exact same known problem case
targets = [r for r in d if (r.get('CompanySymbol') or '').strip() == 'AFRINSURE'
           and (r.get('Type_of_Submission') or '').strip() == 'Financial Statements'
           and r.get('Modified','') >= '2026-09-01'][:3]

for i, rec in enumerate(targets):
    url = rec["URL"]["Url"]
    print(f"\n{'='*60}")
    print(f"=== SAMPLE {i+1} ===")
    print("URL:", url)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as r:
        data = r.read()
    with open("sample.pdf", "wb") as f:
        f.write(data)

    with pdfplumber.open("sample.pdf") as pdf:
        for page_num, page in enumerate(pdf.pages[:3]):  # first 3 pages only
            tables = page.extract_tables()
            print(f"\n--- Page {page_num+1}: {len(tables)} table(s) found ---")
            for t_idx, table in enumerate(tables):
                print(f"Table {t_idx+1}, {len(table)} rows:")
                for row in table[:8]:  # first 8 rows only
                    print("  ", row)
    time.sleep(2)

print("\nDone")