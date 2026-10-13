# Data sources, terms and what this repository redistributes

All inputs are free and publicly accessible without credentials. Retrieval date for every file: **2026-10-13**. The scripts re-download everything from the original sources; `07_文献与日志/download_ledger.jsonl` is written locally on each run with URL, bytes and SHA-256.

## Redistribution policy

- **Included**: small derived tables built from public-domain or openly licensed sources, numeric facts extracted from public reports, a hand-compiled event list with source links, and one aggregate query result from a public blockchain dataset.
- **Not included (reproduced by scripts)**: large raw API dumps (Fiscal Data, 363 MB), raw TIC text files, FRED CSV files, DefiLlama JSON.
- **Not included (third-party restrictions)**: FRED series whose copyright is held by third parties — CBOE VIX (`VIXCLS`), ICE BofA High Yield OAS (`BAMLH0A0HYM2`), Coinbase BTC/ETH prices (`CBBTCUSD`, `CBETHUSD`). They are removed from `05_中间数据/panel_daily_public.csv.gz`; the scripts download them from FRED when you run them yourself, subject to FRED's and the owners' terms.
- **Not included (issuer copyright)**: Circle and Tether attestation PDFs. Only the numbers parsed from them (`tether_reserves_q.csv`, `circle_reserves.csv`) are included; the scripts download the PDFs.

## Sources

| Source | Content | Access | Terms / redistribution | In this repository |
|---|---|---|---|---|
| FRED (Federal Reserve Bank of St. Louis) | T-bill and constant-maturity yields, EFFR, SOFR and percentiles, IORB, ON RRP, TGA, Fed balance sheet, broad dollar index, 5y breakeven | https://fred.stlouisfed.org/graph/fredgraph.csv?id=… | Series originating at the Federal Reserve and U.S. Treasury are U.S. government data; series owned by third parties are excluded (see above) | Derived columns in `panel_daily_public.csv.gz` |
| U.S. Treasury Fiscal Data | Auctions, Monthly Statement of the Public Debt (MSPD), Daily Treasury Statement (DTS) | https://api.fiscaldata.treasury.gov | U.S. government work, public domain | Derived `bills_daily.csv`, `bills_dts_vs_mspd_check.csv` |
| U.S. Treasury yield curve | Daily par yield curve, bill rates, real yield curve | https://home.treasury.gov/resource-center/data-chart-center/interest-rates | U.S. government work, public domain | Not stored; scripted |
| U.S. Treasury TIC | SLT Tables 1, 3, 5 (foreign holdings by country, official and non-official) | https://ticdata.treasury.gov/Publish/ | U.S. government work, public domain | Derived `tic_country_monthly.csv.gz` |
| Federal Reserve Bank of New York | TGCR, BGCR (rates, volumes) | https://markets.newyorkfed.org/api/rates/secured/ | Free to use with attribution to the NY Fed | Columns in `panel_daily_public.csv.gz` (`TGCR`, `BGCR`, `*_VOL`) |
| DefiLlama stablecoins API | Daily circulating supply of USD-pegged stablecoins | https://stablecoins.llama.fi | Free public API; attribution to DefiLlama; check their current terms before commercial reuse | Derived `stablecoin_daily.csv.gz` |
| Circle transparency | USDC monthly examination reports (reserve composition), 2023-01 onward parsed | https://www.circle.com/transparency | Issuer copyright on PDFs; facts (numbers) are not redistributed as documents | Parsed `circle_reserves.csv` |
| Tether transparency | Quarterly BDO ISAE 3000R reports (reserve composition), 2021-02 onward | https://tether.to/en/transparency/?tab=reports | Issuer copyright on PDFs | Parsed `tether_reserves_q.csv` |
| Google BigQuery public datasets | `bigquery-public-data.crypto_ethereum.token_transfers` | https://cloud.google.com/blockchain-analytics/docs/public-datasets | Public blockchain data in the Google Cloud Public Datasets program | One aggregate result `usdc_ethereum_daily_mint_burn.csv`; query in `sql/usdc_mint_burn_daily.sql` |
| GENIUS Act timeline | Legislative and rulemaking dates | Links in the file | Hand-compiled facts with source URLs and a verification flag per row | `04_原始数据/events/genius_events.csv` |

## Known data limits

- Circle publishes no reserve composition table before 2023-01; the combined issuer series therefore starts 2023-01-17. Tether-only series start 2021-06.
- Reserve shares are linearly interpolated between report dates and held flat after the last report.
- TIC country rows do not split official from private holders; the official/non-official split exists only in the two aggregate rows of SLT Table 3.
- DefiLlama covers the 25 largest USD-pegged tokens; other fiat-backed tokens and tokenised T-bill funds are outside the issuer series, so the issuer-demand measures are lower bounds.
- Attestation numbers are point-in-time management or auditor-attested figures, not continuous holdings.
