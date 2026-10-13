import json, fitz, time
from urllib.request import Request, urlopen

d = json.load(open("ngx_disclosures_full_history.json"))

div_samples = [r for r in d if 'dividend' in (r.get('URL',{}).get('Description') or '').lower()
               and r.get('Modified','') >= '2026-01-01'][:10]
fin_samples = [r for r in d if (r.get('Type_of_Submission') or '').strip() == 'Financial Statements'
               and r.get('Modified','') >= '2026-07-01'][:10]

with open("samples_output.txt", "w", encoding="utf-8") as out:
    def show_samples(label, samples):
        for i, rec in enumerate(samples):
            url = rec["URL"]["Url"]
            out.write(f"\n{'='*60}\n")
            out.write(f"=== {label} SAMPLE {i+1}/10 ===\n")
            out.write(f"Symbol: {rec.get('CompanySymbol')} | Date: {rec.get('Modified')}\n")
            out.write(f"URL: {url}\n")
            out.flush()
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req) as r:
                    data = r.read()
                with open("sample.pdf", "wb") as f:
                    f.write(data)
                doc = fitz.open("sample.pdf")
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
                out.write(text + "\n")
                out.flush()
                print(f"{label} {i+1}/10 done - {rec.get('CompanySymbol')}")
            except Exception as e:
                out.write(f"FAILED: {e}\n")
                print(f"{label} {i+1}/10 FAILED - {e}")
            time.sleep(2)

    show_samples("DIVIDEND", div_samples)
    show_samples("FINANCIAL STATEMENT", fin_samples)

print("Done - written to samples_output.txt")