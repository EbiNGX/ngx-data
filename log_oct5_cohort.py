import csv, os

LOG_FILE = os.environ.get("NGX_LOG_FILE", "portfolio_calls_log.csv")
COHORT_DATE = "2026-10-05"
HORIZONS = [30, 60, 90, 120]

# Oct 5 cohort. Baseline is VWAP only: price_at_logging and price_date are left blank on
# purpose, and vwap_at_logging is filled automatically by the resolver from the NGX-native
# price list once the Oct 5 session is in it (tonight's run). Never edited after logging.
# Holds are not scored. UBA, ACCESSCORP, ETI and PZ stay labelled Hold, so their
# conviction changes are recorded in the rationale text, not in a score.
CALLS = [
    ("UCAP", "Buy", "Strongest insider and PBT (+79.6%) combination; VWAP 17.59 on Oct 5; deep, executable book"),
    ("NGXGROUP", "Buy", "PBT +170.3%; fell 8.9% on the week (185.00 to 168.60) with no filing; earnings thesis unchanged"),
    ("CUSTODIAN", "Buy", "MD bought 19.5M units, PBT +41.5%; spread about 4%, use limit orders"),
    ("BUAFOODS", "Buy", "Margin expansion; bid depth swings 2,741 to 135,477; a 40,000-unit position is about 30% of bid depth"),
    ("SEPLAT", "Buy", "Capital-return catalyst; Elumelu entity bought 6M shares Sept 30 during the closed period (compliance flag); thin book"),
    ("UPDCREIT", "Buy", "Confirmed growth; extended, VWAP up 5.6% since Sept 30, not an entry at these levels"),
    ("MAYBAKER", "Buy", "PBT +50.8%; dip checked clean of disclosures"),
    ("CWG", "Buy-lean", "NED bought 1M at about 18.11; offers outnumber bids 21 to 1 on Oct 5"),
    ("AIICO", "Buy", "PBT +20.6%; up sharply since Sept 30; deep book"),
    ("TIP", "Buy", "PBT +119.6%, two prior loss years"),
    ("FIDSON", "Buy", "PBT +30.1%"),
    ("ETERNA", "Buy", "PBT +388%; unexplained 5-day +22% spike unwinding (VWAP 41.00 vs 44.00 official)"),
    ("DANGSUGAR", "Buy", "Recovery thesis after three loss years"),
    ("NASCON", "Buy", "Earnings +115%; now in the pipeline, tracked on VWAP from Oct 5"),
    ("PZ", "Hold", "REFINED Oct 5: Q1 headline PAT -65.6% is a base effect (underlying PBT about +48%) but operating cash flow -N4.3bn and a N2bn related-party loan; VWAP -9.5% after the print; ex-date near Oct 9, wait"),
    ("GTCO", "Hold, lean Sell", "H1 PAT -7.8%, litigation provision doubled to N20.8bn, CBN fine N150m; ex-date near Oct 12"),
    ("UBA", "Hold", "REFINED Oct 5, conviction lowered: no audited H1 results by the extended Sept 30 deadline and no extension notice found in the NGX index"),
    ("ETI", "Hold", "REFINED Oct 5: EGM on Oct 26 with the sole agenda item of revoking directors mandates; who called it and why is unverified"),
    ("WAPIC", "Hold", "Real -24% 2-year decline, no red flag, skipped FY2025 dividend"),
    ("FIRSTHOLDCO", "Hold", "Real -45% 2-year decline undercuts the insider-accumulation thesis"),
    ("STANBIC", "Hold", "H1 PAT +38.2% led by trading revenue while core net interest income fell 14% (Sept 30 read); interim N4.50, ex-date near Oct 15"),
    ("ACCESSCORP", "Hold", "REFINED Oct 5, conviction lowered: H1 results missed the extended Sept 30 deadline, awaiting an unnamed regulatory approval; 434.6M shares traded on Oct 5 at a flat price, cause unverified"),
    ("MTNN", "Hold, lean Buy", "2023-24 balance-sheet crisis confirmed, IHS acquisition is real de-risking; liquid book"),
    ("ZENITHBANK", "Hold", "No major flag; Q3 board Oct 29"),
    ("ARADEL", "Hold", "REFINED Oct 5: real VWAP slid from 1,498 (Sept 25) to 1,378 against a frozen 1,530 official close, no filing explains it; debt +12,183% and Q3 on Oct 27 still open; offers outnumber bids 11 to 1"),
    ("UACN", "Hold, lean Buy", "Livestock Feeds sale priced at N19.5bn cash; DP World Logistics sale still unpriced"),
    ("NEM", "Hold", "No major flag either way"),
    ("UNILEVER", "Hold", "Unexplained decline, no red flag"),
    ("BUACEMENT", "Hold, lean Trim", "Debt +219%; analyst target below price"),
    ("CONHALLPLC", "Hold", "Earnings surge is investment-gain driven; NED purchase disclosed 6 weeks late"),
    ("TRANSCORP", "Hold", "Insider buys on this ticker tested and failed"),
    ("DANGCEM", "Hold", "Balance-sheet strengthening, no red flag"),
    ("PRESCO", "Hold", "Litigation resolved but no bids for weeks, 1.88M units offered at the limit-down price"),
    ("OKOMUOIL", "Hold", "No bids for weeks, 807k units offered at the limit-down price"),
    ("NAHCO", "Hold", "ED Lasisi third sale since mid-August; NED Shobayo bought 248,879 on Sept 29"),
    ("NPFMCRFBK", "Hold", "Thin data, never deeply vetted"),
    ("BETAGLAS", "Hold, lean Sell", "PBT -11.3%, exited a takeover offer"),
    ("MBENEFIT", "Trim", "PBT -15.7%, ambiguous insider cluster"),
    ("INTBREW", "Hold", "4 of 5 years were losses, offsets the return-of-capital"),
    ("LEARNAFRCA", "Sell/Trim", "Sustained insider selling; note it rose 9.8% on Oct 5"),
    ("CUTIX", "Sell/Trim", "Auditor resigned and swung to a loss"),
    ("CHAMS", "Sell", "Escalating insider selling, net seller of 65.7M shares Sept 22-23"),
    ("ROYALEX", "Avoid", "4 of 5 years were losses"),
    ("TANTALIZER", "Avoid", "4 of 5 years were losses"),
    ("OANDO", "Avoid", "Negative equity in all 6 periods checked"),
]

def new_columns():
    cols = []
    for h in HORIZONS:
        cols += [f"fwd_{h}d_price", f"fwd_{h}d_return_pct", f"fwd_{h}d_date", f"call_correct_{h}d"]
    cols += ["vwap_at_logging", "vwap_baseline_date"]
    for h in HORIZONS:
        cols += [f"fwd_{h}d_vwap", f"fwd_{h}d_vwap_return_pct", f"call_correct_vwap_{h}d"]
    return cols

if not os.path.exists(LOG_FILE):
    raise SystemExit(f"{LOG_FILE} not found - run this from the ngx-data folder after git pull")

rows = list(csv.DictReader(open(LOG_FILE, encoding="utf-8")))
fieldnames = list(rows[0].keys())
for c in new_columns():
    if c not in fieldnames:
        fieldnames.append(c)

have = {(r["symbol"], r["logged_date"]) for r in rows}
added = 0
for sym, call, why in CALLS:
    if (sym, COHORT_DATE) in have:
        continue
    row = {c: "" for c in fieldnames}
    row.update({"symbol": sym, "call": call, "rationale": why, "logged_date": COHORT_DATE})
    rows.append(row)
    added += 1

with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"Logged {added} new rows for {COHORT_DATE} ({len(CALLS) - added} already present). Log now has {len(rows)} rows.")
