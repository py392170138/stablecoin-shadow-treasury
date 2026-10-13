"""Tether 季度保证报告（BDO ISAE 3000R）PDF 下载。链接由 tether.to/en/transparency/?tab=reports 展开后读取。"""
import re, dl_common as d
from pathlib import Path
B = "https://assets.ctfassets.net/vyse88cgwfbl/"
ITEMS = """2026-06-30|2kYf7r64h3tzwiu6F0CbUB/2997abd2f11ecea74a21528048b50707/Opinion___Report_-_Tether_International_Financial_Figure_30-06-2026.pdf
2026-03-31|6crn1tXbl6AtWZBWucZnfg/c4ff472d70c1b48c2f689f27b54c84f5/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-03-2026.pdf
2025-12-31|20d2BoOAd28ZfkiQPYPjGN/4ed12f5939e1e06ee5aceccad4effbe4/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-12-2025.pdf
2025-09-30|6GbUTVK4tTYAytefu5daIi/6cac18eb4b526c9c52640a3d2bed9642/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_31-10-2025.pdf
2025-06-30|2SGAAXnsb1wKByIzkhcbSx/9efa4682b3cd4c62d87a4c88ee729693/ISAE_3000R_-_Opinion_Tether_International_Financial_Figure_RC187322025BD0201.pdf
2025-03-31|1LdSmP3HBynDxm6wvkDSsL/c4bcbd1f6fc18a0e8b3a12444ac8ae97/ISAE_3000R_-_Opinion_Tether_International_Financial_Figures___Reserves_Report_31.03.2025_RC187322025BD0040.pdf
2024-12-31|6L2yLNnLltcCP6ZcTxJrll/aea0ec279fea08637445c8be57f63d87/ISAE_3000R_-_Opinion_on_Tether_Consolidated_Financials_Figures_31.12.2024.pdf
2024-09-30|5TKa7xwJVLIAnVBMWb7iTq/5688216da5194fce27f4a0f2e808a486/ISAE_3000R_-_Opinion_on_Tether_Consolidated_Financials_Figures_30.09.2024_.pdf
2024-06-30|6h4YWqZOXbwtBaPtYgICGy/d7462f312aa15b872f8474322ba90363/ISAE_3000R_-_Opinion_on_Consolidated_Financials_Figures_30.06.2024_RC134792024BD0209.pdf
2024-03-31|2JwUN6EeDvWi02CyuQd2nJ/d7b3b4c3800ec70abd7282cc79fa2973/ISAE_3000R_-_Opinion_on_Consolidated_Financials_Figures_and_Reserves_Report_31.03.2024_RC134792024BD0043.pdf
2023-12-31|7DZ8nVyr8zTaWhJqTIsMsH/b8e55bc151c9bb74adf20ff840e84088/ESO.03.01_Std_ISAE_3000R_Opinion_31-12-2023_BDO_Tether_CRR_RC134792023BD0684__1_.pdf
2023-09-30|36XORApdEYAq3AsH1FTXRT/9205ac62f2f57178c47ac5e2eca098c0/Std_ISAE_3000R_Opinion_30-09-2023_BDO_Tether_CRR_RC134792023BD0430.pdf
2023-06-30|63oJePOHqIvrcnXWMPZ1M0/4cfaf2e7cdf80c30b17fdc70faaf741f/ESO.03.01_Std_ISAE_3000R_Opinion_30-06-2023_BDO_Tether_CRR.pdf
2023-03-31|24G4DuQ0HE7h7EQE6vGy4J/8a8a170edf687ea07b3f86048af8b87b/ESO.03.01_Std_ISAE_3000R_Opinion_31-03-2023_BDO_Tether_CRR.pdf
2022-12-31|53L8YRM4ZHCEeqlpKbc3Q8/2e6cbcd1593b3e5ea867718c5938d6c8/Std_ISAE_3000R_Opinion_BDO_31-12-2022_Tether_CRR.pdf
2022-09-30|1Xfu4398CIoMiuKjPhvnHM/6d1608c90bb775d2d432b7b24264da28/ESO.02_Std_ISAE_3000R_Opinion_30-9-2022_RC134792022BD0548.pdf
2022-06-30|2xJyKdUKicdRUWpC9buRWR/6fe2987698dbbf39b947af718d736ddb/Std_ISAE_3000R_Opinion_30-6-2022_RC134792022BD0303.pdf
2022-03-31|1np5dpcwuHrWJ4AgUgI3Vn/e0dac722de3cea07766e05c52773748b/Tether_Assurance_Consolidated_Reserves_Report_2022-03-31__3_.pdf
2021-12-31|4hiNJsZ98LlZqCJHKzrLpV/2b6338482ef0093382885f80ba6f1083/Tether_Assurance-12-31-21.pdf
2021-09-30|01lZdtaNYx7jZ4jU5xmlYO/90aa0d5b1e3559c393ff135f987ddbd0/tether-assurance-sept-30-2021.pdf
2021-06-30|VcNv0hgvQ2a3Ochjs5TqR/59e77f0c076544a88f977d1d36b76dbf/tether_assuranceconsolidated_reserves_report_2021-06-30.pdf
2021-03-31|2UzdY0r33LkkYfr8VDJwwb/7860230f667ed8622fc068949f5fcf94/tether-assurance-mar-2021-2.pdf
2021-02-28|3QHOmpzRBghZuLKa0hLw9c/2c41698f4bffcf9fd91fa611ab04915b/tether-assurance-feb-2021.pdf""".split("\n")
s = d.session()
ok = 0
for it in ITEMS:
    date, path = it.split("|")
    dest = Path(d.RAW / "issuer_reports" / "tether" / f"tether_reserves_{date}.pdf")
    if dest.exists() and dest.stat().st_size > 1000: ok += 1; continue
    try:
        d.fetch(B + path, dest, source=f"Tether:assurance:{date}", sess=s, timeout=90, must_contain=b"%PDF"); ok += 1
    except RuntimeError as e:
        print("FAIL", date, e)
print("tether pdfs", ok, "/", len(ITEMS))
