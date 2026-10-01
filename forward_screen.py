import json, re, csv, os
from datetime import datetime, timedelta, timezone

DISCLOSURES_FILE = "ngx_disclosures_full_history.json"
OUTFILE = "forward_screen_candidates.csv"
LOOKBACK_DAYS = 21

AUDITOR_KEYWORDS = ['auditor resign', 'resignation of auditor', 'external auditor']
INSIDER_SELL_KEYWORDS = ['sale', 'sold', 'disposal']

# --- Earnings-quality soft flag (NEW) ---
# Confirmed real, repeated pattern this project found by hand: Conhallplc's earnings
# surge was investment-gain-driven, not core business. PZ's FY26 profit was inflated
# by a one-time JV divestment gain. Stanbic's H1 2026 profit beat came entirely from
# trading revenue while core net interest income fell 14%. All three were caught only
# because a human read the actual filing - no keyword rule would have caught Stanbic's
# case specifically, since "trading revenue" alone isn't inherently suspicious.
# This is NOT a hard disqualifier like auditor resignation - it is a MANDATORY human
# check: any candidate hitting one of these keywords CANNOT be marked verdict=real_growth
# until earnings_quality_check is explicitly filled in. This forces the same discipline
# that caught Stanbic, rather than letting a clean-looking PBT% pass silently.
EARNINGS_QUALITY_KEYWORDS = [
    'trading revenue', 'trading income', 'gain on disposal', 'gain on sale',
    'fair value gain', 'one-off', 'one off', 'exceptional item',
    'impairment reversal', 'profit on disposal', 'divestment gain',
]

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

def earnings_quality_flag(r):
    """Returns True if the filing's own title/description mentions anything that
    HISTORICALLY correlated with a non-core earnings driver in this project. This
    is a trigger for mandatory human review, NOT proof of a problem - Stanbic's
    real case shows the keyword can be absent even when the issue is real, so a
    'False' here does not mean the filing is clean, only that it needs the same
    manual read either way per the mandatory column below."""
    desc = (r.get('URL', {}).get('Description') or '').lower()
    return any(kw in desc for kw in EARNINGS_QUALITY_KEYWORDS)

d = json.load(open(DISCLOSURES_FILE))
cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
recent = [r for r in d if r.get('Modified', '') >= cutoff]

fs_by_symbol = {}
for r in recent:
    if is_financial_statement(r):
        sym = (r.get('CompanySymbol') or '').strip()
        if sym:
            fs_by_symbol.setdefault(sym, []).append(r)

long_cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
long_recent = [r for r in d if r.get('Modified', '') >= long_cutoff]

disqualified = set()
insider_activity = {}

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

candidates = []
for sym, filings in fs_by_symbol.items():
    if sym in disqualified:
        continue
    ins = insider_activity.get(sym, {"buys": 0, "sells": 0})
    if ins["sells"] >= 2 and ins["sells"] > ins["buys"]:
        continue
    latest_filing = max(filings, key=lambda x: x.get('Modified', ''))
    eq_flag = earnings_quality_flag(latest_filing)
    candidates.append({
        "symbol": sym,
        "filing_date": latest_filing.get('Modified', '')[:10],
        "filing_description": latest_filing.get('URL', {}).get('Description', ''),
        "filing_url": latest_filing.get('URL', {}).get('Url', ''),
        "recent_insider_buys": ins["buys"],
        "recent_insider_sells": ins["sells"],
        "earnings_quality_keyword_hit": eq_flag,
        "screened_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "pending_manual_read",
        "pbt_growth_pct": "",
        "earnings_quality_check": "",  # MANDATORY - fill in: core_business / non_core_driven / mixed
        "verdict": "",  # may ONLY be real_growth if earnings_quality_check is filled AND = core_business
        "fwd_60d_return_pct": "",
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
    qflag = " [EARNINGS QUALITY KEYWORD HIT - mandatory check]" if c["earnings_quality_keyword_hit"] else ""
    print(f"  {c['symbol']}: filed {c['filing_date']}, insider buys={c['recent_insider_buys']} sells={c['recent_insider_sells']}{qflag}")
print(f"\nSaved to {OUTFILE}")
print("REMINDER: 'earnings_quality_check' must be filled in for every row before giving a")
print("verdict of real_growth - a blank keyword hit does NOT mean the filing is clean")
print("(Stanbic's real case had no matching keyword at all). Read every filing regardless.")
