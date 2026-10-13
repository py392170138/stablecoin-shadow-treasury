-- USDC (Ethereum) daily gross mint and burn, 6 decimals.
-- Run in BigQuery against the public dataset (free sandbox is sufficient; one aggregate query).
-- Export the result as CSV to 04_原始数据/onchain/usdc_ethereum_daily_mint_burn.csv
SELECT DATE(block_timestamp) AS d,
  SUM(IF(from_address='0x0000000000000000000000000000000000000000', CAST(value AS BIGNUMERIC), 0))/1e6 AS mint_usd,
  SUM(IF(to_address='0x0000000000000000000000000000000000000000', CAST(value AS BIGNUMERIC), 0))/1e6 AS burn_usd,
  COUNTIF(from_address='0x0000000000000000000000000000000000000000') AS n_mint,
  COUNTIF(to_address='0x0000000000000000000000000000000000000000') AS n_burn
FROM `bigquery-public-data.crypto_ethereum.token_transfers`
WHERE token_address='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
  AND (from_address='0x0000000000000000000000000000000000000000' OR to_address='0x0000000000000000000000000000000000000000')
GROUP BY d ORDER BY d
