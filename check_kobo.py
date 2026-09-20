import os, json
from urllib.request import Request, urlopen
from urllib.error import HTTPError

KEY = os.environ["KOBO_KEY"]
url = "https://koboterminal.com/api/ngxdata/indices/asi/history?from=1996-01-01"
req = Request(url, headers={
    "X-API-Key": KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
})

try:
    with urlopen(req) as response:
        data = json.loads(response.read())
except HTTPError as e:
    print("The request failed. Here is the exact error message the server sent back:")
    print("Status code:", e.code)
    print(e.read().decode("utf-8", errors="replace"))
    input("Press Enter to close this window...")
    raise SystemExit

print("count:", data.get("count"))
print("first_date:", data.get("first_date"), " last_date:", data.get("last_date"))

hist = {row["date"]: row["value"] for row in data.get("history", [])}
checks = {
    "2025-12-31": 155613.03,
    "2026-06-24": 235074.54,
    "2026-06-30": 229419.18,
    "2026-05-12": 252411.70,
}
print()
print("--- Verification against known real values ---")
for d, real in checks.items():
    got = hist.get(d)
    if got is None:
        print(d, "-> MISSING from data")
    else:
        diff = abs(got - real) / real
        print(d, "-> API says:", got, " | real value:", real, " | ", "OK" if diff < 0.01 else "MISMATCH")

with open("asi_history_full.json", "w") as f:
    json.dump(data, f)
print()
print("Saved full data to asi_history_full.json in this folder.")
input("Press Enter to close this window...")