import json, re, csv, os
from datetime import datetime, timedelta, timezone

DISCLOSURES_FILE = "ngx_disclosures_full_history.json"
OUTFILE = "forward_screen_candidates.csv"
LOOKBACK_DAYS = 21  # a real financial-statement filing needs to be recent to matter

# --- Hard disqualifiers, regardless of any other signal ---
AUDITOR_KEYWORDS = ['auditor resign', 'resignation of auditor', 'external auditor']
INSIDER_SELL_KEYWORDS = ['sale', 'sold', 'disposal']

def is_financial_statement(r):
    return (r.get('Type_of_Submission') or '').strip() == 'Financial Statements'

def is_auditor_flag(r):
    desc = (r.get('URL', {}).get('Description') or '').lower()
    return any(kw in desc for kw in AUDITOR_KEYWORDS)

def is_directors_dealing(r):
    t = (r.get('Type_of_Submission') or '').strip().lower()
    if 'directorsdealing' in t:
        return True
    desc = (r.get('URL', {}).get('Description') or '').lower()
    return 'dealing' in desc or 'pdmr' in desc

def dealing_direction(r):
    desc = (r.get('URL', {}).get('Description') or '').lower()
    if any(kw in desc for kw in INSIDER_SELL_KEYWORDS):
        return "sell"
    if 'purchas' in desc or 'buy' in desc:
        return "buy"
    return "unknown"

d = json.load(open(DISCLOSURES_FILE))
cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

recent = [r for r in d if r.get('Modified', '') >= cutoff]

# Real Financial Statement filings, company-wide, in the lookback window -
# these are the actual candidates. We do NOT try to auto-extract PBT/revenue
# numbers here - that was tested and found unreliable for anything beyond a
# handful of rigid templates (the AFRINSURE table-scrambling problem). This
# script's job is to surface WHICH companies have something worth a manual
# read, not to fabricate a number.
fs_by_symbol = {}
for r in recent:
    if is_financial_statement(r):
        sym = (r.get('CompanySymbol') or '').strip()
        if sym:
            fs_by_symbol.setdefault(sym, []).append(r)

# Hard disqualifiers, checked over a longer window (90 days) since these
# matter regardless of how recent the earnings filing is
long_cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
long_recent = [r for r in d if r.get('Modified', '') >= long_cutoff]

disqualified = set()
insider_activity = {}  # symbol -> {"buys": n, "sells": n}

for r in long_recent:
    sym = (r.get('CompanySymbol') or '').strip()
    if not sym:
        continue
    if is_auditor_flag(r):
        disqualified.add(sym)
    if is_directors_dealing(r):
        direction = dealing_direction(r)
        rec = insider_activity.setdefault(sym, {"buys": 0, "sells": 0})
        if direction == "buy":
            rec["buys"] += 1
        elif direction == "sell":
            rec["sells"] += 1

# Build the candidate list
candidates = []
for sym, filings in fs_by_symbol.items():
    if sym in disqualified:
        continue  # hard exclusion, no exceptions
    ins = insider_activity.get(sym, {"buys": 0, "sells": 0})
    # An escalating-sell pattern (more sells than buys, and at least 2 sells)
    # is itself a disqualifier per the Chams precedent
    if ins["sells"] >= 2 and ins["sells"] > ins["buys"]:
        continue
    latest_filing = max(filings, key=lambda x: x.get('Modified', ''))
    candidates.append({
        "symbol": sym,
        "filing_date": latest_filing.get('Modified', '')[:10],
        "filing_description": latest_filing.get('URL', {}).get('Description', ''),
        "filing_url": latest_filing.get('URL', {}).get('Url', ''),
        "recent_insider_buys": ins["buys"],
        "recent_insider_sells": ins["sells"],
        "screened_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "pending_manual_read",  # PBT/revenue growth must be read manually
        "pbt_growth_pct": "",  # filled in by hand after reading the filing
        "verdict": "",  # filled in by hand: real_growth / no_growth / disqualified_on_read
        "fwd_60d_return_pct": "",  # filled in by resolve script once 60 trading days pass
    })

os.makedirs(os.path.dirname(OUTFILE) or ".", exist_ok=True)
file_exists = os.path.exists(OUTFILE)
existing_keys = set()
if file_exists:
    with open(OUTFILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing_keys.add((row["symbol"], row["filing_date"]))

new_rows = [c for c in candidates if (c["symbol"], c["filing_date"]) not in existing_keys]

mode = "a" if file_exists else "w"
with open(OUTFILE, mode, newline="", encoding="utf-8") as f:
    fieldnames = list(candidates[0].keys()) if candidates else []
    w = csv.DictWriter(f, fieldnames=fieldnames)
    if not file_exists and fieldnames:
        w.writeheader()
    w.writerows(new_rows)

print(f"Financial Statement filings in last {LOOKBACK_DAYS} days: {len(fs_by_symbol)} companies")
print(f"Disqualified (auditor resignation, 90-day window): {sorted(disqualified)}")
print(f"New candidates added this run: {len(new_rows)}")
for c in new_rows:
    print(f"  {c['symbol']}: filed {c['filing_date']}, insider buys={c['recent_insider_buys']} sells={c['recent_insider_sells']}")
print(f"\nSaved to {OUTFILE} - each new row needs the actual filing read by hand")
print("(same discipline as everything else this project has tested: read real content, don't guess)")