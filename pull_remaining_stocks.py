import os, json, time
from urllib.request import Request, urlopen

KEY = os.environ["KOBO_KEY"]
headers = {"X-API-Key": KEY, "User-Agent": "Mozilla/5.0", "Accept": "application/json"}

MISSING_TICKERS = ['ABBEYBANK','ABCTRANS','ACADEMY','AFRINSURE','AFRIPRUD','AFROMEDIA',
    'AIRTELAFRI','ALEX','AUSTINLAZ','AVACAP','AVAIF','BAPLC','BERGER','CADBURY','CAP',
    'CAVERTON','CHAMPION','CHELLARAM','CILEASING','CMFC','CNIF','CONOIL','CORNERST',
    'DAARCOMM','EKOCORP','ELLAHLAKES','ENAMELWA','ETERNA','ETI','ETRANZACT','EUNISELL',
    'FCMB','FIDELITYBK','FIRSTHOLDCO','FTGINSURE','FTNCOCOA','GEREGU','GOLDBREW',
    'GUINEAINS','GUINNESS','HBMNG','HMCALL','HONYFLOUR','IKEJAHOTEL','IMG','INFINITY',
    'INTBREW','INTENEGINS','JAIZBANK','JAPAULGOLD','JBERGER','JOHNHOLT','JULI','LASACO',
    'LEARNAFRCA','LEGENDINT','LINKASSURE','LIVESTOCK','LIVINGTRUST','MANSARD','MAYBAKER',
    'MCNICHOLS','MECURE','MEYER','MOFIREIF','MORISON','MULTITREX','MULTIVERSE','NB',
    'NCR','NEIMETH','NESTLE','NIDF','NNFM','NSLTECH','OANDO','OMATEK','PHARMDEKO',
    'PREMPAINTS','PRESTIGE','PZ','REDSTAREX','REGALINS','RONCHESS','ROYALEX','RTBRISCOE',
    'SCOA','SKYAVN','SOVRENINS','STACO','STANBIC','STERLINGNG','SUNUASSUR','THOMASWY',
    'TOTAL','TRANSCOHOT','TRANSCORP','TRANSEXPR','TRANSPOWER','TRIPPLEG','UNILEVER',
    'UNIONDICON','UNITYBNK','UNIVINSURE','UPDC','UPL','VERITASKAP','VFDGROUP','VITAFOAM',
    'WAPIC','WEMABANK','ZICHIS']

def fetch_if_missing(name, url):
    filename = f"{name}.json"
    if os.path.exists(filename):
        print(name, "SKIPPED - already on disk")
        return
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as r:
            data = json.loads(r.read())
        with open(filename, "w") as f:
            json.dump(data, f)
        print(name, "saved")
    except Exception as e:
        print(name, "FAILED:", e)
    time.sleep(3.5)  # keeps us under 20 req/min even across 224 total calls

for sym in MISSING_TICKERS:
    fetch_if_missing(f"{sym}_price", f"https://koboterminal.com/api/ngxdata/prices/{sym}?from=2000-01-01")
    fetch_if_missing(f"{sym}_dividends", f"https://koboterminal.com/api/ngxdata/dividends/{sym}")

print("\nDone. This will have taken roughly", len(MISSING_TICKERS)*2*3.5//60, "minutes due to pacing.")