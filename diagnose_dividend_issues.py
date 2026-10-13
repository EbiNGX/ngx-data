import json, fitz, time
from urllib.request import Request, urlopen

d = json.load(open("ngx_disclosures_full_history.json"))

def find_and_show(symbol, label):
    matches = [r for r in d if (r.get('CompanySymbol') or '').strip() == symbol
               and 'dividend' in (r.get('URL',{}).get('Description') or '').lower()
               and r.get('Modified','') >= '2025-01-01']
    if not matches:
        print(f"\n=== {label} ({symbol}) === NO MATCHES FOUND")
        return
    rec = matches[0]
    url = rec["URL"]["Url"]
    print(f"\n{'='*60}")
    print(f"=== {label} ({symbol}) ===")
    print("URL:", url)
    print("Description:", rec.get('URL',{}).get('Description'))
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as r:
            data = r.read()
        with open("sample.pdf", "wb") as f:
            f.write(data)
        doc = fitz.open("sample.pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        print(text[:2000])
    except Exception as e:
        print(f"FAILED: {e}")
    time.sleep(2)

with open("problem_samples.txt", "w", encoding="utf-8") as out:
    import sys
    class Tee:
        def write(self, s): out.write(s); sys.__stdout__.write(s)
        def flush(self): out.flush()
    sys.stdout = Tee()

    find_and_show("BUAFOODS", "PARSING BUG")
    find_and_show("SEPLAT", "SUSPECTED CURRENCY ISSUE")
    find_and_show("GTCO", "UNEXPLAINED BLANK")
    find_and_show("ACCESSCORP", "UNEXPLAINED BLANK")

print("\nDone - written to problem_samples.txt")
