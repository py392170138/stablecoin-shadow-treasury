# Shadow Treasury Demand: stablecoin reserves, T-bills and repo

Code and public data for a study of how U.S. dollar stablecoin issuers' reserve holdings — U.S. Treasury bills and repo — relate to short-term Treasury and repo market prices, and to foreign holders of bills, around the GENIUS Act (signed 2025-07-18, operating framework effective 2027-01-18).

This repository contains **research code and small public-data tables**. It does not contain a manuscript or analysis results. Data redistribution follows the terms of each original source; see [DATA_SOURCES.md](DATA_SOURCES.md).

## What is implemented

| Stage | Scripts |
|---|---|
| Direct-connection downloads with retries, size guard and SHA-256 ledger | `03_代码/dl_common.py`, `fetch_core.py`, `fetch_tether.py` |
| Reserve-report parsing (Tether quarterly, Circle monthly; regular expressions, no model calls) | `parse_reserves.py` |
| Daily panel: stablecoin supply, issuer T-bill and repo holdings, T-bills outstanding (Fiscal Data reconstruction reconciled to MSPD month-ends), rates and spreads, TIC country panel | `build_panel.py` |
| Event study, weekly local projections (OLS, 2SLS with Anderson–Rubin sets), machine-learning counterfactual, foreign-holder regressions | `analysis.py` |
| Repo channel, longer Tether-only sample, repo-spread event study | `analysis_repo.py` |
| Figures (matplotlib) | `viz_style.py`, `fig_common.py`, `fig1_landscape.py` … `fig7_repo.py` |
| USDC mint/burn aggregate query | `sql/usdc_mint_burn_daily.sql` |

Design choices fixed before estimation (event list and exclusion rules, windows, controls, instruments, country classification) are at the top of `analysis.py` and `analysis_repo.py`.

## Reproducing

Python 3.12. Package versions used are in `requirements.lock.txt`.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.lock.txt
cd 03_代码
# 1. Download public data (direct connection; proxies are ignored by design)
../.venv/bin/python fetch_core.py all
../.venv/bin/python fetch_tether.py
# 2. Parse issuer reports and build panels
../.venv/bin/python parse_reserves.py
../.venv/bin/python build_panel.py
# 3. Analysis and figures
../.venv/bin/python analysis.py
../.venv/bin/python analysis_repo.py
for f in fig1_landscape fig2_prices fig3_events fig4_lp fig5_ml fig6_foreign fig7_repo; do ../.venv/bin/python $f.py; done
```

Notes:

- `fetch_tether.py` holds report links that were read from the Tether transparency page on 2026-10-13; if Tether changes its hosting the links must be refreshed.
- The USDC mint/burn file is produced by running `sql/usdc_mint_burn_daily.sql` once in BigQuery (free sandbox) and saving the CSV to `04_原始数据/onchain/`. The result as retrieved on 2026-10-13 is included.
- `build_panel.py` expects the FRED series including VIX and BTC/ETH prices, which are third-party data and are **not** redistributed here (`fetch_core.py fred` downloads them). `05_中间数据/panel_daily_public.csv.gz` is the panel without those columns.
- FRED answers browser-like User-Agent headers with long hangs; `fetch_core.py` uses a curl-style identifier for FRED.
- Library versions, the Apple-silicon macOS platform and random seeds can affect numerical results at the last digits.

## Directory layout

```
02_数据字典/       data_inventory.csv (coverage and sizes of the original downloads)
03_代码/           all scripts
04_原始数据/       events/ (GENIUS timeline with sources), onchain/ (USDC mint/burn aggregate)
05_中间数据/       derived public tables (see DATA_SOURCES.md for what is and is not included)
sql/               BigQuery query
```

## Limitations stated up front

- Issuer reserve data are periodic attestations; series between reports are interpolated.
- Issuer-demand measures cover Tether and Circle only and are lower bounds for the whole stablecoin sector.
- The code estimates conditional associations and event-window responses; it makes no claim of a completed causal effect.

## License

Code: MIT (see `LICENSE`). Data: the terms of the original sources (see `DATA_SOURCES.md`).
