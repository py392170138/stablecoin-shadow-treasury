"""核心公开数据采集：FRED、Treasury Fiscal Data、Treasury 收益率曲线、TIC、DefiLlama。

用法：../.venv/bin/python fetch_core.py [fred|fiscal|curve|tic|llama|all]
全部直连、记账、可重复；已存在且非空的文件默认跳过（--force 覆盖）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import dl_common as d

RAW = d.RAW
FORCE = "--force" in sys.argv

FRED_SERIES = {
    # 国库券与收益率曲线
    "DTB4WK": "4-week T-bill secondary market rate",
    "DTB3": "3-month T-bill secondary market rate",
    "DTB6": "6-month T-bill secondary market rate",
    "DTB1YR": "1-year T-bill secondary market rate",
    "DGS1MO": "1-month constant maturity",
    "DGS3MO": "3-month constant maturity",
    "DGS6MO": "6-month constant maturity",
    "DGS1": "1-year constant maturity",
    "DGS2": "2-year constant maturity",
    "DGS5": "5-year constant maturity",
    "DGS10": "10-year constant maturity",
    "DGS30": "30-year constant maturity",
    "T10Y2Y": "10y-2y spread",
    # 政策利率与货币市场
    "DFF": "Effective federal funds rate (daily)",
    "EFFR": "Effective federal funds rate (NY Fed)",
    "SOFR": "Secured Overnight Financing Rate",
    "SOFR30DAYAVG": "SOFR 30-day average",
    "SOFR90DAYAVG": "SOFR 90-day average",
    "IORB": "Interest on reserve balances",
    "DFEDTARU": "Fed funds target upper",
    "DFEDTARL": "Fed funds target lower",
    "RRPONTSYD": "ON RRP Treasury securities sold (daily)",
    "RRPONTTLD": "ON RRP total (daily)",
    "DCPF3M": "3-month AA financial commercial paper",
    "DCPN3M": "3-month AA nonfinancial commercial paper",
    # 资产负债表与国库现金
    "WTREGEN": "Treasury General Account (weekly, Wed level)",
    "WALCL": "Fed total assets (weekly)",
    "TREAST": "Fed Treasury securities held outright (weekly)",
    "WSHOBL": "Fed holdings of T-bills (weekly)",
    "WRESBAL": "Reserve balances at Fed (weekly)",
    "GFDEBTN": "Federal debt total public debt (quarterly)",
    "FDHBFIN": "Federal debt held by foreign & international investors (quarterly)",
    "FDHBFRBN": "Federal debt held by Federal Reserve Banks (quarterly)",
    # 风险与加密价格
    "VIXCLS": "CBOE VIX",
    "DTWEXBGS": "Broad trade-weighted dollar index",
    "CBBTCUSD": "Coinbase Bitcoin USD",
    "CBETHUSD": "Coinbase Ethereum USD",
    "BAMLH0A0HYM2": "ICE BofA US HY OAS",
    "T5YIE": "5y breakeven inflation",
    # 回购渠道（Phase 3 新增）
    "RRPONTSYAWARD": "ON RRP Treasury award rate",
    "SOFR1": "SOFR 1st percentile",
    "SOFR99": "SOFR 99th percentile",
    "SOFRVOL": "SOFR volume ($bn)",
}


def skip(p: Path) -> bool:
    return p.exists() and p.stat().st_size > 0 and not FORCE


def fred() -> None:
    s = d.session()
    s.headers["User-Agent"] = "curl/8.7.1"  # FRED 对浏览器式 UA 的无头请求会长时间挂起
    out = RAW / "fred"
    for sid, desc in FRED_SERIES.items():
        dest = out / f"{sid}.csv"
        if skip(dest):
            continue
        try:
            d.fetch("https://fred.stlouisfed.org/graph/fredgraph.csv", dest,
                    params={"id": sid, "cosd": "1990-01-01"}, source=f"FRED:{sid}", sess=s,
                    must_contain=b"observation_date")
            print("FRED ok", sid)
        except RuntimeError as e:
            print("FRED FAIL", sid, e)
    (out / "_series_catalog.json").write_text(json.dumps(FRED_SERIES, ensure_ascii=False, indent=1))


def fiscal_pages(endpoint: str, dest: Path, *, params: dict | None = None, page_size: int = 10000,
                 max_pages: int = 400) -> int:
    """Fiscal Data 分页 -> 单个 JSONL。返回行数。"""
    if skip(dest):
        return -1
    s = d.session()
    base = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service" + endpoint
    n, page = 0, 1
    tmp = dest.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as f:
        while page <= max_pages:
            q = {"page[size]": page_size, "page[number]": page, "format": "json"}
            q.update(params or {})
            for attempt in range(5):
                r = s.get(base, params=q, timeout=180)
                if r.status_code == 200:
                    break
                time.sleep(2 * (attempt + 1))
            else:
                raise RuntimeError(f"{endpoint} page {page} HTTP {r.status_code}")
            js = r.json()
            for row in js["data"]:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += len(js["data"])
            if page >= js["meta"]["total-pages"]:
                break
            page += 1
    tmp.replace(dest)
    d.log({"source": f"FiscalData:{endpoint}", "url": base, "file": str(dest.relative_to(d.ROOT)),
           "bytes": dest.stat().st_size, "sha256": d.sha256(dest), "rows": n, "status": 200})
    return n


FISCAL = {
    "auctions_query": ("/v1/accounting/od/auctions_query", {}),
    "upcoming_auctions": ("/v1/accounting/od/upcoming_auctions", {}),
    "debt_to_penny": ("/v2/accounting/od/debt_to_penny", {}),
    "mspd_table_1": ("/v1/debt/mspd/mspd_table_1", {}),
    "mspd_table_3_market": ("/v1/debt/mspd/mspd_table_3_market", {}),
    "avg_interest_rates": ("/v2/accounting/od/avg_interest_rates", {}),
    "dts_operating_cash_balance": ("/v1/accounting/dts/operating_cash_balance", {}),
    "dts_public_debt_transactions": ("/v1/accounting/dts/public_debt_transactions",
                                     {"filter": "record_date:gte:2017-01-01"}),
    "dts_deposits_withdrawals": ("/v1/accounting/dts/deposits_withdrawals_operating_cash",
                                 {"filter": "record_date:gte:2017-01-01"}),
}


def fiscal() -> None:
    for name, (ep, params) in FISCAL.items():
        dest = RAW / "fiscaldata" / f"{name}.jsonl"
        try:
            n = fiscal_pages(ep, dest, params=params)
            print("Fiscal", name, "skipped" if n == -1 else f"{n} rows")
        except Exception as e:
            print("Fiscal FAIL", name, e)


def curve() -> None:
    s = d.session()
    out = RAW / "treasury_curve"
    kinds = {"daily_treasury_yield_curve": range(1990, 2027),
             "daily_treasury_bill_rates": range(2002, 2027),
             "daily_treasury_real_yield_curve": range(2003, 2027)}
    for kind, years in kinds.items():
        for y in years:
            dest = out / kind / f"{y}.csv"
            if skip(dest):
                continue
            url = (f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                   f"daily-treasury-rates.csv/{y}/all")
            try:
                d.fetch(url, dest, params={"type": kind, "field_tdr_date_value": y, "page": "", "_format": "csv"},
                        source=f"TreasuryCurve:{kind}:{y}", sess=s, must_contain=b"Date")
            except RuntimeError as e:
                print("Curve FAIL", kind, y, e)
        print("Curve done", kind)


TIC_FILES = ["mfh.txt", "mfhhis01.txt", "mfhhis01.csv", "slt_table1.txt", "slt_table3.txt",
             "slt_table5.txt", "slt3d.txt", "slt3d_globl.csv", "s1_globl.csv"]


def tic() -> None:
    s = d.session()
    for fn in TIC_FILES:
        dest = RAW / "tic" / fn
        if skip(dest):
            continue
        try:
            d.fetch(f"https://ticdata.treasury.gov/Publish/{fn}", dest, source=f"TIC:{fn}", sess=s, timeout=240)
            print("TIC ok", fn)
        except RuntimeError as e:
            print("TIC FAIL", fn, e)


def llama() -> None:
    s = d.session()
    out = RAW / "defillama"
    lst = out / "stablecoins_list.json"
    if not skip(lst):
        d.fetch("https://stablecoins.llama.fi/stablecoins", lst, params={"includePrices": "true"},
                source="DefiLlama:list", sess=s, must_contain=b"peggedAssets")
    js = json.loads(lst.read_text())
    assets = [a for a in js["peggedAssets"] if a.get("pegType") == "peggedUSD"]
    assets.sort(key=lambda a: -(a.get("circulating", {}).get("peggedUSD") or 0))
    top = assets[:25]
    print("DefiLlama top:", [(a["id"], a["symbol"], round((a["circulating"]["peggedUSD"] or 0) / 1e9, 1)) for a in top[:10]])
    for a in top:
        dest = out / "charts_all" / f"{a['id']}_{a['symbol']}.json"
        if skip(dest):
            continue
        try:
            d.fetch("https://stablecoins.llama.fi/stablecoincharts/all", dest, params={"stablecoin": a["id"]},
                    source=f"DefiLlama:all:{a['symbol']}", sess=s)
        except RuntimeError as e:
            print("Llama FAIL", a["symbol"], e)
    # USDT(1)、USDC(2) 分链日度流通量
    for a in top:
        if a["symbol"] not in ("USDT", "USDC"):
            continue
        chains = sorted((a.get("chainCirculating") or {}).items(),
                        key=lambda kv: -(kv[1].get("current", {}).get("peggedUSD") or 0))[:12]
        for ch, _ in chains:
            dest = out / "charts_chain" / f"{a['symbol']}_{ch}.json"
            if skip(dest):
                continue
            try:
                d.fetch(f"https://stablecoins.llama.fi/stablecoincharts/{ch}", dest,
                        params={"stablecoin": a["id"]}, source=f"DefiLlama:chain:{a['symbol']}:{ch}", sess=s)
            except RuntimeError as e:
                print("Llama FAIL", a["symbol"], ch, e)
    print("DefiLlama done")


def nyfed() -> None:
    """纽约联储担保隔夜利率 API：TGCR、BGCR（含分位数与成交量）。"""
    s = d.session()
    for k in ["tgcr", "bgcr"]:
        dest = RAW / "nyfed" / f"{k}.json"
        if skip(dest):
            continue
        d.fetch(f"https://markets.newyorkfed.org/api/rates/secured/{k}/search.json", dest,
                params={"startDate": "2018-04-02", "endDate": "2026-10-13"}, source=f"NYFed:{k}", sess=s, must_contain=b"refRates")
        print("NYFed ok", k)


STEPS = {"nyfed": nyfed, "fred": fred, "fiscal": fiscal, "curve": curve, "tic": tic, "llama": llama}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")] or ["all"]
    for step in (STEPS if "all" in args else args):
        print(f"== {step}")
        STEPS[step]()
