"""报告日（非插值）稳健性：只用发行商报告日的实际持有额，不做插值。

(a) Circle 报告日面板：相邻两个 Circle 报告日之间，Circle 国库券持有额的实际变化 + Tether 持有额在同一区间的变化
    （Tether 为季度报告，区间内按最近报告取值，不插值），对 3M−EFFR / 3M−SOFR 利差在同一区间的变化回归，控制国库券余额变化。
(b) Tether 季度面板：只用 Tether 报告日（2021-06 起，21 个报告，20 个区间）。
输出 06_结果/tables/robustness_reportdate.csv
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
ROOT = Path(__file__).resolve().parents[1]; O = ROOT / "05_中间数据"; T = ROOT / "06_结果" / "tables"
P = pd.read_parquet(O / "panel_daily.parquet")
tt = pd.read_csv(O / "tether_reserves_q.csv", parse_dates=["report_date"]).dropna(subset=["us_tbills"]).set_index("report_date").sort_index()
cc = pd.read_csv(O / "circle_reserves.csv", parse_dates=["report_date"]).set_index("report_date").sort_index()

def at(s, d):  # 最近交易日的值
    s = s.dropna(); i = s.index.searchsorted(d); i = min(max(i, 0), len(s) - 1); return s.iloc[i]

rows = []
# (a) Circle 报告日区间
dates = cc.index[cc.index >= "2023-01-17"]
rec = []
for a, b in zip(dates[:-1], dates[1:]):
    teth_a = tt.us_tbills[tt.index <= a].iloc[-1] if (tt.index <= a).any() else np.nan
    teth_b = tt.us_tbills[tt.index <= b].iloc[-1]
    dSDT = (cc.treasuries.loc[b] - cc.treasuries.loc[a]) + (teth_b - teth_a)
    rec.append(dict(a=a, b=b, days=(b - a).days, dSDT=dSDT / 1e11, dbills=(at(P.bills_usd, b) - at(P.bills_usd, a)) / 1e11,
                    d_sp_dff=at(P.sp_dff, b) - at(P.sp_dff, a), d_sp_sofr=at(P.sp_sofr, b) - at(P.sp_sofr, a), dDFF=(at(P.DFF, b) - at(P.DFF, a)) * 100,
                    dVIX=at(P.VIXCLS, b) - at(P.VIXCLS, a)))
d = pd.DataFrame(rec).dropna()
for y in ["d_sp_dff", "d_sp_sofr"]:
    m = sm.OLS(d[y], sm.add_constant(d[["dSDT", "dbills", "dDFF", "dVIX"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    rows.append(dict(panel="Circle report-date intervals (both issuers, no interpolation)", outcome=y, n=len(d), median_days=int(d.days.median()),
                     b=m.params.dSDT, se=m.bse.dSDT, p=m.pvalues.dSDT))
# (b) Tether 季度区间
rec = []
for a, b in zip(tt.index[:-1], tt.index[1:]):
    rec.append(dict(a=a, b=b, days=(b - a).days, dSDT=(tt.us_tbills.loc[b] - tt.us_tbills.loc[a]) / 1e11, dbills=(at(P.bills_usd, b) - at(P.bills_usd, a)) / 1e11,
                    d_sp_dff=at(P.sp_dff, b) - at(P.sp_dff, a), d_sp_sofr=at(P.sp_sofr, b) - at(P.sp_sofr, a), dDFF=(at(P.DFF, b) - at(P.DFF, a)) * 100, dVIX=at(P.VIXCLS, b) - at(P.VIXCLS, a)))
d2 = pd.DataFrame(rec).dropna()
for y in ["d_sp_dff", "d_sp_sofr"]:
    m = sm.OLS(d2[y], sm.add_constant(d2[["dSDT", "dbills", "dDFF"]])).fit(cov_type="HC1")
    rows.append(dict(panel="Tether quarterly report dates (no interpolation)", outcome=y, n=len(d2), median_days=int(d2.days.median()), b=m.params.dSDT, se=m.bse.dSDT, p=m.pvalues.dSDT))
out = pd.DataFrame(rows); out.to_csv(T / "robustness_reportdate.csv", index=False)
pd.set_option("display.width", 200); print(out.round(3).to_string())
# 对照：周度 LP h=0..4 的 se 量级
lp = pd.read_csv(T / "local_projections.csv"); print("weekly LP se h0-4:", lp[(lp.outcome == "sp_dff") & (lp.h <= 4)].ols_se.round(1).tolist())
