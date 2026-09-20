# NGX Sage-Investor Parameter Framework
*Compiled Sept 20, 2026 — every parameter a hypothetically all-knowing, unbiased NGX/Lagos Stock Exchange investor would weigh, honestly sorted by what we actually have, what's been tested, and what's missing.*

---

## TWO NEW FINDINGS FROM TESTING THIS FRAMEWORK TODAY — READ FIRST

**1. Ex-dividend price drop: real, strong, and previously untested — the single most reliable pattern found in this entire project.**
Tested 582 real ex-dividend events (2020-2026) using data already in hand. **77.3% showed a genuine price decline on the ex-date, mean -4.0%, median -2.13%.** This beats every other pattern tested this conversation by a wide margin (the cross-sectional price-pattern model: ~56%; the insider-event log: ~60%). This is a well-known market mechanic globally, but now quantified specifically for NGX with real magnitude and real hit-rate.
**Direct implication for entry/exit timing**: all else equal, buying *after* a stock's ex-dividend date rather than before captures a real, statistically reliable ~2-4% better entry price. Selling *before* the ex-date (if not planning to hold through it) avoids that predictable markdown. This should be a standing rule in any entry-timing decision, not a footnote.

**2. Nigerian election cycles: no reliable pattern at all — a real answer to a question that's been asked narratively without ever being tested.**
Tested real ASI performance around all 7 Nigerian presidential elections since 1999 (60 days before, 20/60/120 days after). **Results ranged from -20.4% to +34.5% at the 120-day horizon, with no consistent direction pre- or post-election.** "Elections create predictable volatility/direction" is not supported by NGX's own history. This directly bears on the Jan 2027 election, repeatedly flagged as a catalyst this conversation — the honest answer is: treat it as a real source of uncertainty, not a source of directional edge.

---

## PART 1: Macro & Monetary

| Parameter | Status | Notes |
|---|---|---|
| CBN MPR level & trajectory | **HAVE, tested** | 3 real historical rate-change events tested (ngx_macro_event_log.csv); directionally consistent (cuts bullish, hikes bearish near-term) but small sample |
| Inflation (CPI) trend | **HAVE, narrative only** | Monthly prints tracked; never tested as a continuous variable against forward returns the way MPR was |
| Real interest rate (MPR − inflation) | **HAVE, narrative only** | Referenced in every MACRO section; never backtested as its own signal |
| FX rate (NGN/USD) level & volatility | **MISSING** | Not systematically gathered. Source: CBN's own FX rate page (free), or Trading Economics/Investing.com historical series |
| FX reserves / CBN intervention capacity | **MISSING** | Source: CBN's monthly reserves reports (free, public) |
| T-bill/bond yields | **PARTIAL** | One auction snapshot + biweekly pulls building a short history; not yet long enough to test |
| Global oil price (Brent) | **MISSING** | Directly relevant given Seplat/Aradel/Oando's oil exposure and Nigeria's oil-dependent macro. Source: any free commodities API or Trading Economics |
| Diaspora remittances | **MISSING** | Real driver of FX stability. Source: CBN balance-of-payments releases (quarterly, free, public) |
| Government fiscal position (deficit, debt/GDP) | **MISSING** | Source: DMO Nigeria (Debt Management Office) public reports |

## PART 2: Market Structure & Liquidity

| Parameter | Status | Notes |
|---|---|---|
| 100,000-share minimum trade-size rule | **HAVE, confirmed** | Directly explains the frozen-price phenomenon on DANGCEM/OKOMUOIL/BUAFOODS/PRESCO — a genuinely unique NGX structural quirk, real regulatory finding |
| Live bid/offer depth & spread | **HAVE, manual, Meristem** | Only as fresh as the last Chrome session — never automated, can't be |
| Foreign portfolio investor (FPI) flow data | **MISSING** | NGX/CBN sometimes publish this specifically, distinct from general sentiment. Source: NGX's own monthly domestic/foreign participation reports (check ngxgroup.com's market reports section) |
| Domestic vs. foreign participation ratio | **MISSING** | Same source as above |
| Free float / real available shares per stock | **PARTIAL** | Seen ad hoc in specific disclosures (e.g. Okomu's shareholding pages); not systematized across the watchlist |
| Market cap concentration (top names dominate NGX) | **HAVE, computable** | Already have full market-cap data via the bulk stocks endpoint; never explicitly analyzed for concentration risk |

## PART 3: Company Fundamentals

| Parameter | Status | Notes |
|---|---|---|
| P/E, ROE, F-score, dividend yield | **HAVE, tested extensively** | Core of every fundamentals vetting pass this conversation |
| Debt/equity (general) | **HAVE** | In bulk fundamentals |
| **FX-denominated debt exposure specifically** | **MISSING** | Critical in Nigeria given devaluation history — a company with USD-denominated debt is exposed in a way general debt/equity doesn't show. Not a standard field; would require reading annual report notes directly, company by company |
| Sector-specific macro sensitivity | **PARTIAL** | Some sector benchmarking done (banking index vs. individual banks); never built into a systematic "which sectors are most exposed to X macro factor" framework |
| Related-party/ownership concentration | **PARTIAL** | Encountered repeatedly in disclosures (BUA Cement intra-family trades, Dangote-entity structures) but never systematized as a screened risk factor |
| Regulatory/recapitalization risk (CBN bank recap, NAICOM insurer recap) | **PARTIAL** | Seen ad hoc (MBENEFIT's NAICOM clearance); no standing regulatory-deadline calendar |

## PART 4: Corporate Actions & Events

| Parameter | Status | Notes |
|---|---|---|
| Insider dealings | **HAVE, tested, growing log** | ngx_insider_event_log.csv, 10 resolved events, real buy/sell asymmetry emerging |
| General disclosures (litigation, M&A, governance) | **HAVE, weekly pipeline** | The single highest-value manual input this whole project |
| Dividend history & policy | **HAVE, tested today** | See ex-dividend finding above |
| Stock splits / bonus issues | **MISSING as a tracked category** | Would show up in disclosures if read for it specifically; never tagged as its own type |
| Rights issues / capital raises | **PARTIAL** | Seen ad hoc (Oando's ₦200bn raise, Presco's rights issue); no standing tracker |
| M&A / control changes | **PARTIAL** | Seen ad hoc (BetaGlas takeover); no standing tracker |

## PART 5: Technical / Price

| Parameter | Status | Notes |
|---|---|---|
| RSI, moving averages, 52-week range | **HAVE, extensively tested** | Real cross-sectional backtest, 611,870 predictions, modest genuine edge found |
| Frozen-price dislocation detection | **HAVE, built, automated** | Runs daily via the GitHub pipeline |
| Historical volatility regimes | **HAVE** | Used in the original EPRM regime classifier (accurate at *recognizing* acute crises once underway, not predicting them) |

## PART 6: Calendar / Seasonal

| Parameter | Status | Notes |
|---|---|---|
| Ex-dividend date effects | **NOW TESTED — see top of document** | Real, strong, actionable |
| Earnings season effects | **MISSING, testable now** | We have both disclosure dates and price data — this is a natural next test, same method as the ex-dividend one |
| Election cycle effects | **NOW TESTED — see top of document** | No reliable pattern found |
| Ramadan / religious-calendar effects | **MISSING** | A real, sometimes-discussed Nigerian market pattern given the country's large Muslim population; never tested. Sourceable via public Islamic calendar dates + existing price data |
| FTSE Russell reclassification / index-inclusion effects | **MISSING, testable with more work** | Would need historical dates of prior NGX index reclassification events, likely findable via news archive search the same way the insider-event log was built |

## PART 7: Sentiment & News

| Parameter | Status | Notes |
|---|---|---|
| News volume/sentiment | **PARTIAL** | One point-in-time pull; not a maintained feed |
| Social media / retail sentiment | **MISSING** | No clean free source identified |

## PART 8: Cross-Market / Global

| Parameter | Status | Notes |
|---|---|---|
| Correlation with global EM equity flows / DXY | **MISSING** | Sourceable via free financial data APIs (Trading Economics, Yahoo Finance) |
| Correlation with other African markets (JSE, EGX) | **MISSING** | Same sourcing approach |

---

## PART 9: How this actually feeds decisions — implementation

**Buy/Hold/Sell**: unchanged from the existing research prompt's rating discipline — every rating still needs supporting *and* contradicting evidence listed. What changes: the ex-dividend finding is now a mandatory check before any BUY rating on a stock with an upcoming ex-date, and the election-cycle finding means the Jan 2027 election should never be cited as directional evidence in either direction.

**Entry timing**: the ex-dividend effect is the first genuinely reliable, quantified timing rule this project has produced. Concretely: check the target stock's next ex-dividend date before entering; if it falls within the next 1-3 weeks, the honest expectation is a ~2-4% markdown is coming regardless of the company's fundamentals — waiting captures that.

**Exit timing / stop-losses**: nothing in this framework yet produces a validated stop-loss level — that would need its own dedicated test (e.g., checking what stop-loss percentage would have avoided the worst real drawdowns in the price-pattern backtest without triggering on normal noise). Worth building as a fourth permanent log, same pattern as the other three, if useful.

**Which stocks warrant monitoring**: the free-float, FX-debt-exposure, and related-party-concentration gaps above are the biggest blind spots in the current watchlist tiers — a stock could look clean on P/E and F-score while carrying real, invisible-to-us FX debt risk or a tiny real float behind a large nominal market cap. Worth a targeted pass on the Tier A names specifically before treating them as fully vetted.

**Next most valuable single test, given what today found**: earnings-season price effects, using the exact same method as the ex-dividend test — we already have both the disclosure dates and the price data sitting in hand right now.
