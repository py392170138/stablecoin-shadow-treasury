"""Phase 3：回购渠道与扩展样本。

1. 回购渠道局部投影：稳定币发行商回购放款 (Tether 隔夜+定期逆回购、Circle 回购) 对 SOFR−IORB、TGCR−ON RRP、SOFR 分位离差。
2. 扩展样本：Tether 单独的国库券持有对 3M 国库券利差，样本 2021-08 起（n≈270），提高功效。
3. 回购利差事件研究（剔除月末/季末窗口与 FOMC 窗口）。
设定冻结在文件顶部。
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "05_中间数据"
T = ROOT / "06_结果" / "tables"
P = pd.read_parquet(O / "panel_daily.parquet")
H = list(range(0, 9))
OUT: dict = {}

EVENTS = {"E02": "2025-06-17", "E03": "2025-07-17", "E04": "2025-07-18", "E05": "2025-09-19", "E07": "2026-02-25", "E08": "2026-03-02",
          "E09": "2026-04-03", "E10": "2026-04-08", "E11": "2026-04-10", "E13": "2026-08-17"}


def weekly() -> pd.DataFrame:
    W = P.resample("W-FRI")
    d = pd.DataFrame(index=W.last().index)
    for k in ["sofr_iorb", "tgcr_rrp", "sofr_disp", "sp_sofr", "sp_dff"]:
        d[k] = W[k].mean()                                   # 周均值，平滑日内/月末噪声
    last = W.last()
    d["repo_usd"] = last["SDT_repo_usd"]
    d["bills_t_usd"] = last["USDT_bills"]
    d["dRepo"] = d["repo_usd"].diff() / 1e11
    d["dTether"] = d["bills_t_usd"].diff() / 1e11
    d["dbills"] = last["bills_usd"].diff() / 1e11
    d["dTGA"] = last["WTREGEN"].diff() / 1e5
    d["dRRP"] = last["RRPONTSYD"].diff() / 100
    d["dRES"] = last["WRESBAL"].diff() / 1e5
    d["dVIX"] = last["VIXCLS"].diff()
    d["dDFF"] = last["DFF"].diff() * 100
    d["dExp"] = last["sp_2y_dff"].diff()
    idx = d.index
    # 月末/季末周虚拟变量：该周（前 6 个自然日至周五）含当月最后一个工作日
    def last_bday(dte):
        return (dte.weekday() < 5) and ((dte + pd.offsets.BDay(1)).month != dte.month)
    me, qe = [], []
    for f in idx:
        days = pd.date_range(f - pd.Timedelta(days=6), f)
        lb = [x for x in days if last_bday(x)]
        me.append(len(lb) > 0); qe.append(len(lb) > 0 and lb[0].month in (3, 6, 9, 12))
    me, qe = np.array(me), np.array(qe)
    d["me"] = me.astype(float); d["qe"] = qe.astype(float)
    return d


def lp(d, shock, outs, controls, start, end, label):
    rows = []
    samp = d.loc[start:end]
    for y in outs:
        for h in H:
            dd = samp.copy()
            dd["Y"] = d[y].shift(-h).loc[dd.index] - d[y].shift(1).loc[dd.index]
            dd["Ylag"] = d[y].diff().shift(1).loc[dd.index]
            dd = dd.dropna(subset=["Y", shock, "Ylag"] + controls)
            if len(dd) < 40:
                continue
            m = sm.OLS(dd["Y"], sm.add_constant(dd[[shock] + controls + ["Ylag"]])).fit(cov_type="HAC", cov_kwds={"maxlags": max(4, h)})
            rows.append(dict(spec=label, outcome=y, h=h, n=len(dd), b=m.params[shock], se=m.bse[shock], p=m.pvalues[shock]))
    return pd.DataFrame(rows)


def repo_events():
    ev_dates = [pd.Timestamp(v) for v in EVENTS.values()]
    dff = (P["DFF"] * 100).dropna()

    def dff_move(t, back=5):
        seg = dff[(dff.index >= t - pd.Timedelta(days=back)) & (dff.index <= t)]
        return float(seg.max() - seg.min()) if len(seg) else 0.0

    def near_me(t0, t1):
        for dte in pd.date_range(t0, t1):
            if dte.is_month_end or (dte + pd.offsets.BDay(1)).month != dte.month or dte.day <= 1 or dte.day >= 29:
                return True
        return False

    rows = []
    for col in ["tgcr_rrp", "sofr_iorb", "sp_sofr"]:
        s = P[col].dropna(); s = s[s.index >= "2023-01-01"]
        chg = s.diff(3).dropna()
        ok = []
        for t in chg.index:
            i = s.index.get_loc(t)
            ok.append((dff_move(t) <= 1.0) and not near_me(s.index[i - 3], t) and not any((t >= d - pd.Timedelta(days=7)) and (t <= d + pd.Timedelta(days=7)) for d in ev_dates))
        base = chg[np.array(ok)]
        for eid, d_ in EVENTS.items():
            t0 = pd.Timestamp(d_)
            i = s.index.searchsorted(t0)
            if i < 2 or i + 1 >= len(s):
                continue
            tstart, tend = s.index[i - 2], s.index[i + 1]
            if dff_move(tend) > 1.0 or near_me(tstart, tend):
                rows.append(dict(event=eid, date=d_, series=col, change_bp=np.nan, z=np.nan, p=np.nan, excluded="FOMC or month-end window"))
                continue
            x = s.iloc[i + 1] - s.iloc[i - 2]
            rows.append(dict(event=eid, date=d_, series=col, change_bp=x, z=(x - base.mean()) / base.std(), p=(np.abs(base) >= abs(x)).mean(), excluded="", placebo_sd=base.std(), n_base=len(base)))
    ev = pd.DataFrame(rows); ev.to_csv(T / "repo_event_study.csv", index=False)
    return ev


if __name__ == "__main__":
    d = weekly()
    d.to_csv(T / "weekly_repo_panel.csv")
    ctrl = ["dbills", "dTGA", "dRRP", "dRES", "dVIX", "dDFF", "me", "qe"]
    r1 = lp(d, "dRepo", ["sofr_iorb", "tgcr_rrp", "sofr_disp", "sp_sofr"], ctrl, "2023-02-03", "2026-10-09", "Repo lending, 2023-02 on")
    ctrl2 = ["dbills", "dTGA", "dRRP", "dVIX", "dDFF", "dExp"]
    r2 = lp(d, "dTether", ["sp_dff", "sp_sofr"], ctrl2, "2021-08-06", "2026-10-09", "Tether T-bills, 2021-08 on")
    r3 = lp(d, "dTether", ["sp_dff", "sp_sofr"], ctrl2, "2023-02-03", "2026-10-09", "Tether T-bills, 2023-02 on")
    res = pd.concat([r1, r2, r3]); res.to_csv(T / "repo_local_projections.csv", index=False)
    ev = repo_events()
    # 规模统计
    last = P.dropna(subset=["SDT_repo_usd"]).iloc[-1]
    OUT["scale"] = dict(date=str(last.name.date()), repo_usd_bn=float(last.SDT_repo_usd / 1e9), tgcr_vol_bn=float(P["TGCR_VOL"].dropna().iloc[-1]),
                        share_tgcr_pct=float(last.SDT_repo_usd / 1e9 / P["TGCR_VOL"].dropna().iloc[-1] * 100),
                        onrrp_bn=float(P["RRPONTSYD"].dropna().iloc[-1]))
    json.dump(OUT, open(ROOT / "06_结果" / "results_repo.json", "w"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 200)
    print(json.dumps(OUT, indent=1))
    for sp in res.spec.unique():
        sub = res[res.spec == sp]
        print("==", sp, "n =", int(sub.n.max()))
        print(sub.pivot(index="h", columns="outcome", values="b").round(1).to_string())
        print((sub.pivot(index="h", columns="outcome", values="b") / sub.pivot(index="h", columns="outcome", values="se")).round(2).to_string())
    print(ev[["event", "series", "change_bp", "z", "p", "excluded"]].round(2).to_string())
