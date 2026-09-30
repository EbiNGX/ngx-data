import json, csv, os
from datetime import datetime

OUTFILE = "portfolio_calls_log.csv"

# Every current call from this project, as of today - the actual recommendation
# being tested, not a re-derivation. This is what gets checked in 60 days.
CURRENT_CALLS = [
    ("UCAP", "Buy", "586-filing insider history + PBT +79.6%, cheap in range"),
    ("NGXGROUP", "Buy", "Strongest earnings growth, +170.3% PBT, but extended vs MA50"),
    ("CUSTODIAN", "Buy", "MD bought 19.5M units + PBT +41.5%"),
    ("BUAFOODS", "Buy", "Real margin expansion; frozen price, liquidity trap"),
    ("SEPLAT", "Buy", "Real capital-return catalyst, live strength"),
    ("UPDCREIT", "Buy", "Confirmed +42.9%/+56.5% growth; extended vs MA50"),
    ("MAYBAKER", "Buy", "PBT +50.8%, unexplained dip already checked clean"),
    ("CWG", "Buy-lean", "Real NED insider purchase Sept 23-24"),
    ("AIICO", "Buy", "PBT +20.6%"),
    ("TIP", "Buy", "PBT +119.6%, tempered by 2 real loss years"),
    ("FIDSON", "Buy", "PBT +30.1%"),
    ("ETERNA", "Buy", "PBT +388%, but +24.5% extended, don't chase here"),
    ("DANGSUGAR", "Buy", "Recovery thesis, real turnaround after 3 loss years"),
    ("NASCON", "Buy", "Real earnings growth +115%"),
    ("PZ", "Hold, lean Buy", "Real turnaround but one-time-gain inflated"),
    ("GTCO", "Hold", "Real -19% 2yr decline, confirmed clean of red flags"),
    ("UBA", "Hold", "Real -56% decline, confirmed clean, same as sector delay pattern"),
    ("ETI", "Hold", "Real decline, disclosed as FX effect"),
    ("WAPIC", "Hold", "Real -24% decline, no red flag, skipped FY2025 dividend"),
    ("FIRSTHOLDCO", "Hold", "Real -45% decline undercuts insider-accumulation thesis"),
    ("STANBIC", "Hold", "Same filing-delay pattern as UBA/Access"),
    ("ACCESSCORP", "Hold", "Same filing-delay pattern; Eurobond redeemed cleanly"),
    ("MTNN", "Hold, lean Buy", "Real 2023-24 crisis confirmed; IHS deal real de-risking"),
    ("ZENITHBANK", "Hold", "No major flag, near highs"),
    ("ARADEL", "Hold", "Debt +12,183%; insider sales below current price"),
    ("UACN", "Hold", "Real DP World Logistics divestment pending, unpriced"),
    ("NEM", "Hold", "No major flag either way"),
    ("UNILEVER", "Hold", "Real unexplained decline, no red flag"),
    ("BUACEMENT", "Hold, lean Trim", "Debt +219%; standing analyst-target concern"),
    ("CONHALLPLC", "Hold", "Earnings surge investment-gain-driven"),
    ("TRANSCORP", "Hold", "Insider buy on this ticker already tested and failed"),
    ("DANGCEM", "Hold", "Real balance-sheet strengthening, no red flag"),
    ("PRESCO", "Hold", "Litigation resolved, zero bid liquidity 4+ sessions"),
    ("OKOMUOIL", "Hold", "Structural liquidity failure, worsening"),
    ("NAHCO", "Hold", "Two EDs sold, no other flag"),
    ("NPFMCRFBK", "Hold", "Thin data, never deeply vetted"),
    ("BETAGLAS", "Hold, lean Sell", "PBT -11.3%, exited a takeover offer"),
    ("MBENEFIT", "Trim", "PBT -15.7%, ambiguous insider cluster"),
    ("INTBREW", "Hold", "4 of 5 years were losses, offsets return-of-capital"),
    ("LEARNAFRCA", "Sell/Trim", "Sustained real insider selling"),
    ("CUTIX", "Sell/Trim", "Auditor resigned + swing to loss"),
    ("CHAMS", "Sell", "Escalating insider selling, 3+ instances"),
    ("ROYALEX", "Avoid", "4 of 5 years were losses"),
    ("TANTALIZER", "Avoid", "4 of 5 years were losses"),
    ("OANDO", "Avoid", "Negative equity every one of 6 periods checked"),
]

today = datetime.now().strftime("%Y-%m-%d")
rows = []
for sym, call, rationale in CURRENT_CALLS:
    price_today = None
    try:
        d = json.load(open(f"{sym}_price.json"))
        latest = max(d['prices'], key=lambda p: p['trade_date'])
        price_today = latest.get('close_price')
        price_date = latest.get('trade_date')
    except FileNotFoundError:
        price_date = None
    rows.append({
        "symbol": sym, "call": call, "rationale": rationale,
        "logged_date": today, "price_at_logging": price_today,
        "price_date": price_date,
        "fwd_30d_price": "", "fwd_30d_return_pct": "", "fwd_30d_date": "", "call_correct_30d": "",
        "fwd_60d_price": "", "fwd_60d_return_pct": "", "fwd_60d_date": "", "call_correct_60d": "",
        "fwd_90d_price": "", "fwd_90d_return_pct": "", "fwd_90d_date": "", "call_correct_90d": "",
        "fwd_120d_price": "", "fwd_120d_return_pct": "", "fwd_120d_date": "", "call_correct_120d": "",
    })

file_exists = os.path.exists(OUTFILE)
existing_keys = set()
if file_exists:
    with open(OUTFILE, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            existing_keys.add((r["symbol"], r["logged_date"]))

new_rows = [r for r in rows if (r["symbol"], r["logged_date"]) not in existing_keys]
mode = "a" if file_exists else "w"
with open(OUTFILE, mode, newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    if not file_exists:
        w.writeheader()
    w.writerows(new_rows)

no_price = [r["symbol"] for r in new_rows if r["price_at_logging"] is None]
print(f"Logged {len(new_rows)} calls as of {today}")
print(f"Buy/Buy-lean: {sum(1 for r in new_rows if 'Buy' in r['call'])}")
print(f"Hold: {sum(1 for r in new_rows if r['call'].startswith('Hold'))}")
print(f"Sell/Trim/Avoid: {sum(1 for r in new_rows if r['call'] in ('Sell/Trim','Sell','Trim','Avoid'))}")
if no_price:
    print(f"\nNo price file found for: {no_price} - check these separately")
print(f"\nSaved to {OUTFILE}. Resolve in 60 trading days with resolve_portfolio_calls.py")
