import json, fitz
from urllib.request import Request, urlopen

d = json.load(open("ngx_disclosures_full_history.json"))
WATCHLIST = ["UCAP"]
targets = [r for r in d
           if 'directorsdealing' in (r.get('Type_of_Submission') or '').lower()
           and (r.get('CompanySymbol') or '').strip() in WATCHLIST
           and r.get('Modified','') >= '2024-01-01']

url = targets[0]["URL"]["Url"]
print("Downloading:", url)

req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urlopen(req) as r:
    data = r.read()
with open("ucap_sample.pdf", "wb") as f:
    f.write(data)

doc = fitz.open("ucap_sample.pdf")
text = "\n".join(page.get_text() for page in doc)
doc.close()
print("---RAW TEXT BELOW---")
print(text)