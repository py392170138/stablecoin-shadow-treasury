"""构造分析面板（日度 / 月度），输出到 05_中间数据。

输出：
  stablecoin_daily.parquet   稳定币日度流通量、净发行、国库券持有额（SDT）
  bills_daily.parquet        国库券余额日度重构（MSPD 月末锚 + DTS 日度净发行）
  panel_daily.parquet        利率、利差、风险、加密价格与 SDT 的日度合并面板
  tic_country_monthly.parquet  TIC 国别美债持有（总额/长期/短期）
"""
from __future__ import annotations

import glob
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "04_原始数据"
O = ROOT / "05_中间数据"


def fred(sid: str) -> pd.Series:
    df = pd.read_csv(R / "fred" / f"{sid}.csv")
    df.columns = ["date", sid]
    df["date"] = pd.to_datetime(df["date"])
    df[sid] = pd.to_numeric(df[sid], errors="coerce")
    return df.dropna().set_index("date")[sid]


# ---------------------------------------------------------------- 稳定币
def stablecoins() -> pd.DataFrame:
    cols = {}
    for f in sorted(glob.glob(str(R / "defillama/charts_all/*.json"))):
        sym = Path(f).stem.split("_", 1)[1]
        js = json.load(open(f))
        s = pd.Series({pd.to_datetime(int(r["date"]), unit="s").normalize(): r["totalCirculatingUSD"].get("peggedUSD", np.nan) for r in js})
        cols[sym] = s[~s.index.duplicated()]
    df = pd.DataFrame(cols).sort_index()
    full = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full).ffill()
    df.index.name = "date"
    df["TOTAL_TOP25"] = df.sum(axis=1)
    df["OTHER"] = df["TOTAL_TOP25"] - df["USDT"].fillna(0) - df["USDC"].fillna(0)
    return df


def reserve_share(df_rep: pd.DataFrame, num_cols: list[str], supply: pd.Series, name: str) -> pd.Series:
    """报告日的 (持有额 / 当日流通量) 占比，按日线性插值；末次报告后保持不变。"""
    d = df_rep.copy()
    d["date"] = pd.to_datetime(d["report_date"])
    d = d.sort_values("date").drop_duplicates("date").set_index("date")
    held = d[num_cols].fillna(0).sum(axis=1)
    sup = supply.reindex(d.index, method="nearest")
    share = (held / sup).rename(name)
    full = pd.date_range(share.index.min(), supply.index.max(), freq="D")
    return share.reindex(full.union(share.index)).interpolate(method="time").ffill().reindex(full)


def build_sdt(sc: pd.DataFrame) -> pd.DataFrame:
    tt = pd.read_csv(O / "tether_reserves_q.csv")
    cc = pd.read_csv(O / "circle_reserves.csv")
    cc["repo"] = cc["repo"].fillna(0)
    tt["tbill"] = tt["us_tbills"]
    tt["repo"] = tt[["on_rrp", "term_rrp", "reverse_repo_other"]].fillna(0).sum(axis=1)
    tt_ok = tt.dropna(subset=["tbill"])
    out = pd.DataFrame(index=sc.index)
    sh_t_b = reserve_share(tt_ok, ["tbill"], sc["USDT"], "t_bill_share")
    sh_t_r = reserve_share(tt_ok, ["repo"], sc["USDT"], "t_repo_share")
    sh_c_b = reserve_share(cc, ["treasuries"], sc["USDC"], "c_bill_share")
    sh_c_r = reserve_share(cc, ["repo"], sc["USDC"], "c_repo_share")
    out["USDT_bills"] = (sh_t_b.reindex(sc.index) * sc["USDT"])
    out["USDT_repo"] = (sh_t_r.reindex(sc.index) * sc["USDT"])
    out["USDC_bills"] = (sh_c_b.reindex(sc.index) * sc["USDC"])
    out["USDC_repo"] = (sh_c_r.reindex(sc.index) * sc["USDC"])
    out["SDT_bills_usd"] = out[["USDT_bills", "USDC_bills"]].sum(axis=1, min_count=2)   # 两家都有：2023-01-17 起
    out["SDT_bills_usd_tether_only"] = out["USDT_bills"]
    out["SDT_broad_usd"] = out[["USDT_bills", "USDT_repo", "USDC_bills", "USDC_repo"]].sum(axis=1, min_count=4)
    return out


# ---------------------------------------------------------------- 国库券余额
def bills_daily() -> pd.DataFrame:
    m = pd.read_json(R / "fiscaldata/mspd_table_3_market.jsonl", lines=True, dtype=False)
    b = m[(m.security_class1_desc == "Bills Maturity Value") & (m.security_class2_desc == "Total Treasury Bills")].copy()  # 只取总计行，避免与单只国库券明细重复计数
    b["o"] = pd.to_numeric(b.outstanding_amt, errors="coerce")
    me = b.groupby("record_date").o.sum() * 1e6          # 美元
    me.index = pd.to_datetime(me.index)
    t = pd.read_json(R / "fiscaldata/dts_public_debt_transactions.jsonl", lines=True, dtype=False)
    t = t[(t.security_market == "Marketable") & (t.security_type == "Bills")].copy()
    t["amt"] = pd.to_numeric(t.transaction_today_amt, errors="coerce") * 1e6
    t["date"] = pd.to_datetime(t.record_date)
    iss = t[(t.transaction_type == "Issues") & t.security_type_desc.isin(["Regular Series", "Cash Management Series"])].groupby("date").amt.sum()
    red = t[t.transaction_type == "Redemptions"].groupby("date").amt.sum()
    net = (iss.reindex(red.index.union(iss.index)).fillna(0) - red.reindex(red.index.union(iss.index)).fillna(0)).rename("dts_net")
    # 校验：DTS 月内累计净发行 vs MSPD 月末差分
    chk = []
    for a, b2 in zip(me.index[:-1], me.index[1:]):
        if a >= pd.Timestamp("2017-01-31"):
            chk.append((b2, (net[(net.index > a) & (net.index <= b2)].sum()), me[b2] - me[a]))
    chk = pd.DataFrame(chk, columns=["month_end", "dts_net_sum", "mspd_diff"]).set_index("month_end")
    chk["ratio"] = chk.dts_net_sum / chk.mspd_diff
    chk.to_csv(O / "bills_dts_vs_mspd_check.csv")
    # 日度重构：相邻 MSPD 月末锚之间，用 DTS 日度净发行逐日累加，并把累计误差线性分摊，保证月末与 MSPD 精确一致
    days = pd.date_range("2017-01-31", net.index.max(), freq="D")
    s = pd.Series(np.nan, index=days)
    for d0, v in me[me.index >= "2017-01-31"].items():
        s[d0] = v
    netd = net.reindex(days).fillna(0)
    anchors = [d for d in days if not np.isnan(s[d])]
    rec = pd.Series(index=days, dtype=float)
    for a, b2 in zip(anchors[:-1], anchors[1:]):
        idx = days[(days >= a) & (days <= b2)]
        inc = netd.loc[idx].cumsum() - netd.loc[a]
        total_inc = inc.iloc[-1]
        resid = (s[b2] - s[a]) - total_inc
        w = np.linspace(0, 1, len(idx))
        rec.loc[idx] = s[a] + inc.values + resid * w
    last = anchors[-1]
    tail = days[days > last]
    rec.loc[tail] = s[last] + netd.loc[tail].cumsum().values
    res = pd.DataFrame({"bills_usd": rec, "dts_net_usd": netd})
    res.index.name = "date"
    return res, chk


# ---------------------------------------------------------------- TIC
def tic_country() -> pd.DataFrame:
    lines = open(R / "tic/slt_table3.txt", encoding="latin-1").read().splitlines()
    rows = [l.split("\t") for l in lines[9:] if l.count("\t") >= 9 and l.split("\t")[2][:2] == "20"]
    df = pd.DataFrame(rows).iloc[:, :10]
    df.columns = ["country", "code", "date", "tot_hold", "tot_net", "lt_hold", "lt_net", "lt_valchg", "st_hold", "st_net"]
    for c in df.columns[3:]:
        df[c] = pd.to_numeric(df[c], errors="coerce") * 1e6
    df["date"] = pd.to_datetime(df["date"] + "-01") + pd.offsets.MonthEnd(0)
    return df


# ---------------------------------------------------------------- 日度面板
def panel(sc, sdt, bills) -> pd.DataFrame:
    idx = pd.date_range("2018-04-03", sc.index.max(), freq="D")
    P = pd.DataFrame(index=idx)
    for sid in ["DTB4WK", "DTB3", "DTB6", "DTB1YR", "DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS10", "SOFR", "SOFR30DAYAVG", "SOFR90DAYAVG",
                "DFF", "EFFR", "IORB", "RRPONTSYD", "RRPONTTLD", "VIXCLS", "CBBTCUSD", "CBETHUSD", "DTWEXBGS", "BAMLH0A0HYM2", "T5YIE", "DFEDTARU"]:
        P[sid] = fred(sid).reindex(idx)
    for sid in ["RRPONTSYAWARD", "SOFR1", "SOFR99", "SOFRVOL"]:
        P[sid] = fred(sid).reindex(idx)
    for k in ["tgcr", "bgcr"]:
        js = json.load(open(R / "nyfed" / f"{k}.json"))["refRates"]
        ser = pd.Series({pd.Timestamp(r["effectiveDate"]): r["percentRate"] for r in js}).sort_index()
        P[k.upper()] = ser.reindex(idx)
        P[k.upper() + "_VOL"] = pd.Series({pd.Timestamp(r["effectiveDate"]): r["volumeInBillions"] for r in js}).sort_index().reindex(idx)
    for sid in ["WTREGEN", "WALCL", "TREAST", "WSHOBL", "WRESBAL"]:
        P[sid] = fred(sid).reindex(idx).ffill()
    P = pd.concat([P, sc[["USDT", "USDC", "OTHER", "TOTAL_TOP25"]], sdt, bills], axis=1).reindex(idx)
    P["bills_usd"] = P["bills_usd"].ffill()
    # 利差（基点）
    P["sp_sofr"] = (P["DTB3"] - P["SOFR"]) * 100
    P["sp_sofr90"] = (P["DTB3"] - P["SOFR90DAYAVG"]) * 100
    P["sp_dff"] = (P["DTB3"] - P["DFF"]) * 100
    P["sp_1m_dff"] = (P["DGS1MO"] - P["DFF"]) * 100
    P["sp_6m_dff"] = (P["DGS6MO"] - P["DFF"]) * 100
    P["sp_1y_dff"] = (P["DGS1"] - P["DFF"]) * 100
    P["sp_2y_dff"] = (P["DGS2"] - P["DFF"]) * 100
    P["term_10_2"] = (P["DGS10"] - P["DGS2"]) * 100
    # 回购渠道利差（基点）
    P["sofr_iorb"] = (P["SOFR"] - P["IORB"]) * 100
    P["tgcr_rrp"] = (P["TGCR"] - P["RRPONTSYAWARD"]) * 100
    P["sofr_iorb_fill"] = P["sofr_iorb"]
    P["sofr_disp"] = (P["SOFR99"] - P["SOFR1"]) * 100
    P["SDT_repo_usd"] = P[["USDT_repo", "USDC_repo"]].sum(axis=1, min_count=2)
    P["repo_share_tgcr_pct"] = P["SDT_repo_usd"] / 1e9 / P["TGCR_VOL"] * 100
    # SDT：稳定币持有国库券 / 国库券余额
    P["SDT_pct"] = P["SDT_bills_usd"] / P["bills_usd"] * 100
    P["SDT_tether_pct"] = P["SDT_bills_usd_tether_only"] / P["bills_usd"] * 100
    P["SDT_broad_pct"] = P["SDT_broad_usd"] / P["bills_usd"] * 100
    # 稳定币净发行（日度，美元）
    P["net_issue_usdt"] = P["USDT"].diff()
    P["net_issue_usdc"] = P["USDC"].diff()
    P["net_issue_total"] = P["TOTAL_TOP25"].diff()
    return P


if __name__ == "__main__":
    sc = stablecoins()
    sdt = build_sdt(sc)
    bills, chk = bills_daily()
    P = panel(sc, sdt, bills)
    tic = tic_country()
    sc.join(sdt).to_parquet(O / "stablecoin_daily.parquet")
    bills.to_parquet(O / "bills_daily.parquet")
    P.to_parquet(O / "panel_daily.parquet")
    tic.to_parquet(O / "tic_country_monthly.parquet")
    pd.set_option("display.width", 220)
    print("stablecoin", sc.shape, sc.index.min().date(), sc.index.max().date())
    print("bills check: median ratio DTS/MSPD", chk.ratio.median().round(3), " MAD", (chk.ratio - 1).abs().median().round(3), " n=", len(chk))
    print("bills latest $T", (P.bills_usd.dropna().iloc[-1] / 1e12).round(3))
    print(P[["DTB3", "SOFR", "DFF", "sp_sofr", "sp_dff", "bills_usd", "USDT_bills", "USDC_bills", "SDT_pct", "SDT_tether_pct", "SDT_broad_pct"]].dropna(subset=["SDT_pct"]).iloc[[0, 200, 500, 800, -1]].round(3).to_string())
    print("TIC", tic.shape, tic.date.min().date(), tic.date.max().date(), tic.country.nunique())
