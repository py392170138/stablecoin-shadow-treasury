# Pre-registered forward test windows (filed 21 October 2026)

This file fixes, before the events occur, the outcomes, windows, exclusion rules, placebo construction, and pass criteria for three forward events in the GENIUS Act implementation sequence. It is committed to a public repository so that the specification carries a verifiable timestamp. The test will be run once, after the last event date, with the code in `03_代码/analysis.py` (function `event_study`) and `03_代码/analysis_repo.py` (function `repo_events`), unchanged except for the event list.

## Events

| ID | Event | Date rule |
|---|---|---|
| F1 | Publication in the Federal Register of the OCC final rule implementing the GENIUS Act | the publication date printed in the Federal Register |
| F2 | Operating framework effective date | 18 January 2027, or the earlier date triggered 120 days after final rules if that applies; whichever the statute makes operative |
| F3 | First public issuance of a US-dollar payment stablecoin by the bank consortium announced on 1 September 2026 | the first calendar day on which circulating supply of that token exceeds USD 1 billion on DefiLlama |

If an event has no single date (for example, an OCC rule published in two parts), the first date is used. Events that fall within seven calendar days of each other are tested jointly, not separately.

## Outcomes (basis points)

1. Three-month Treasury bill coupon-equivalent yield minus the effective federal funds rate (primary).
2. Three-month bill yield minus SOFR.
3. TGCR minus the ON RRP award rate.
4. SOFR minus IORB.
5. Placebo tenors: one-year and two-year constant-maturity yields minus the effective federal funds rate.

## Window and statistic

Three-day change: close of day t0+1 minus close of day t0−2, where t0 is the event date (next trading day if t0 is not a trading day). A secondary eleven-day window [t0−5, t0+5] is reported but is not used for the pass criterion.

## Exclusion rules (applied mechanically)

- Any window in which the effective federal funds rate moves by more than one basis point over [t0−5, t0+1] is excluded (FOMC contamination).
- For repo outcomes (3 and 4), any window that contains the last business day of a month is excluded.
- Excluded windows are reported as excluded; no substitute date is chosen.

## Placebo distribution

All three-day changes from 1 September 2022 to the day before F1 (or the earliest forward event), excluding windows within seven trading days of any event in the 2025–2026 event table (E02–E13) and windows failing the exclusion rules above. The p-value is the share of 20,000 draws of the same number of windows whose mean absolute change is at least as large as the observed pooled mean.

## Pass criteria

- The reserve-demand hypothesis is supported for the bill channel if the pooled three-day change in outcome 1 is negative and lies outside the 95% placebo band, and the pooled change in the two-year placebo tenor does not.
- The repo channel hypothesis is supported if the pooled change in outcome 3 is negative and outside its 95% placebo band.
- Any other pattern, including a significant move with the opposite sign or a significant move that is matched at the two-year tenor, is reported as not supporting the hypothesis.

## What will not be changed after the fact

The event list, outcomes, window, exclusion rules, placebo construction, and pass criteria above. Any deviation will be stated as a deviation in the write-up, with the pre-registered result reported alongside.

SHA-256 of the analysis scripts at filing time is recorded in `CODE_SHA256SUMS.txt`.
