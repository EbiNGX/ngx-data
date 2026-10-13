import csv, glob, os, re, sys

# Loads Meristem order-book pulls (the text a Chrome pull produces) into meristem_book_log.csv.
# Handles the three layouts seen so far (=== TICKER === blocks, [01] TICKER blocks, and the
# "Best Bid (price x qty)" variant). One row per (pull_date, symbol). An existing row is never
# overwritten unless --replace is given, so the book you saw when a cohort was logged stays put.
#   python load_book_pulls.py meristem_pull_2026-10-12.txt --note="15:10 WAT intraday"
#   options: --date=YYYY-MM-DD (otherwise read from the "As of <date>" page stamp), --replace

BOOK_FILE = "meristem_book_log.csv"
FIELDS = ["pull_date", "pull_note", "symbol", "best_bid", "bid_qty", "best_offer", "offer_qty",
          "bid_depth", "offer_depth", "volume", "value", "vwap", "last_price", "source_file"]
NUM = r"\d[\d,]*(?:\.\d+)?"
MONTHS = {m: i for i, m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], 1)}
HDR = re.compile(r"^(?:={3,}\s*|\[\d+\]\s+)([A-Z][A-Z0-9]{1,14})\b")

def num(s):
    m = re.search(NUM, (s or "").replace("₦", ""))
    return float(m.group(0).replace(",", "")) if m else None

def parse_book(s):
    s = (s or "").replace("₦", "")
    if re.search(r"\bnone\b|no orders|no bids|no offers|empty", s, re.I):
        return None, None
    m = re.search(rf"({NUM})\s*[x×]\s*({NUM})", s)
    if not m:
        return None, None
    p, q = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    return (p if p > 0 else None), (q if q > 0 else None)

def find_date(text, fname):
    m = re.search(r"as of\s+([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})", text, re.I)
    if m and m.group(1)[:3].lower() in MONTHS:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(fname))
    return m.group(1) if m else None

def parse_text(text, pull_date, note, source):
    blocks, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        m = HDR.match(line)
        if m:
            cur = {"symbol": m.group(1), "pull_date": pull_date, "pull_note": note, "source_file": source}
            blocks.append(cur)
            continue
        if cur is None or ":" not in line:
            continue
        key, val = line.split(":", 1)
        nk = re.sub(r"[^a-z ]", "", key.lower()).strip()
        if nk.startswith("last vs"):
            continue
        if nk.startswith("last"):
            cur["last_price"] = num(val)
        elif nk.startswith("vwap"):
            cur["vwap"] = num(val)
        elif nk.startswith("best bid"):
            cur["best_bid"], cur["bid_qty"] = parse_book(val); cur["_book"] = True
        elif nk.startswith("best offer"):
            cur["best_offer"], cur["offer_qty"] = parse_book(val); cur["_book"] = True
        elif nk.startswith("bid depth"):
            cur["bid_depth"] = num(val)
        elif nk.startswith("offer depth"):
            cur["offer_depth"] = num(val)
        elif nk.startswith("volume"):
            cur["volume"] = num(val)
        elif nk.startswith("value"):
            cur["value"] = num(val)
    return [b for b in blocks if b.get("_book")]

def check(rec):
    w = []
    v, q, vw = rec.get("value"), rec.get("volume"), rec.get("vwap")
    if v and q and vw and abs(v / q / vw - 1) > 0.002:
        w.append(f"stated VWAP {vw} vs value/volume {v/q:.4f}")
    b, o = rec.get("best_bid"), rec.get("best_offer")
    if b and o and b > o:
        w.append(f"bid {b} above offer {o}")
    return w

def fmt(v):
    if v is None or v == "":
        return ""
    v = float(v)
    return str(int(v)) if v.is_integer() else ("%.4f" % v).rstrip("0").rstrip(".")

def merge(new_rows, replace=False):
    existing = {}
    if os.path.exists(BOOK_FILE):
        for r in csv.DictReader(open(BOOK_FILE, encoding="utf-8")):
            existing[(r["pull_date"], r["symbol"])] = r
    added = skipped = replaced = 0
    for r in new_rows:
        k = (r["pull_date"], r["symbol"])
        if k in existing and not replace:
            skipped += 1
            continue
        replaced += k in existing
        added += k not in existing
        existing[k] = {f: (r.get(f, "") if f in ("pull_date", "pull_note", "symbol", "source_file") else fmt(r.get(f)))
                       for f in FIELDS}
    rows = sorted(existing.values(), key=lambda r: (r["pull_date"], r["symbol"]))
    with open(BOOK_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return added, skipped, replaced

def main(argv):
    replace = "--replace" in argv
    date_arg = next((a.split("=", 1)[1] for a in argv if a.startswith("--date=")), None)
    note_arg = next((a.split("=", 1)[1] for a in argv if a.startswith("--note=")), None)
    files = [a for a in argv if not a.startswith("--")] or sorted(glob.glob("meristem_pull_*.txt"))
    if not files:
        print("No pull files given and none match meristem_pull_*.txt")
        return 1
    for f in files:
        text = open(f, encoding="utf-8", errors="replace").read()
        d = date_arg or find_date(text, f)
        if not d:
            print(f"{f}: could not find the pull date - pass --date=YYYY-MM-DD")
            continue
        rows = parse_text(text, d, note_arg or f"from {os.path.basename(f)}", os.path.basename(f))
        added, skipped, replaced = merge(rows, replace)
        print(f"{f}: pull date {d}, parsed {len(rows)} tickers -> added {added}, replaced {replaced}, skipped {skipped} (already logged)")
        for r in rows:
            for w in check(r):
                print(f"  WARNING {r['symbol']}: {w}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
