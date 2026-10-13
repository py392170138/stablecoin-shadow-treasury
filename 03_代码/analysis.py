"""核心分析：事件研究、局部投影（OLS / IV）、机器学习反事实、外国持有人回归。

输入：05_中间数据/*.parquet；输出：06_结果/tables/*.csv 与 06_结果/results.json
所有设定在运行前冻结于本文件顶部，不根据结果调整。
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS
from sklearn.ensemble import GradientBoostingRegressor

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "05_中间数据"
T = ROOT / "06_结果" / "tables"
T.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------- 冻结设定
EVENTS = {  # id: (日期, 类别)；E01/E06/E12/E14/E15/E16 不进入事件研究（引入、争议日期、周末、单一来源或未来日期）
    "E02": ("2025-06-17", "legislative"), "E03": ("2025-07-17", "legislative"), "E04": ("2025-07-18", "legislative"),
    "E05": ("2025-09-19", "rulemaking"), "E07": ("2026-02-25", "rulemaking"), "E08": ("2026-03-02", "rulemaking"),
    "E09": ("2026-04-03", "rulemaking"), "E10": ("2026-04-08", "rulemaking"), "E11": ("2026-04-10", "rulemaking"),
    "E13": ("2026-08-17", "rulemaking"),
}
EV_LABEL = {"E02": "Senate passes", "E03": "House passes", "E04": "Signed into law", "E05": "Treasury ANPRM",
            "E07": "OCC NPRM announced", "E08": "OCC NPRM in FR", "E09": "Treasury state-regime NPRM",
            "E10": "Treasury/OFAC AML NPRM", "E11": "FDIC prudential NPRM", "E13": "Treasury issuance NPRM"}
TENORS = {"DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M", "DGS1": "1Y", "DGS2": "2Y", "DGS10": "10Y"}
LP_H = list(range(0, 13))
SAMPLE_START, SAMPLE_END = "2023-01-27", "2026-10-09"
PLACEBO_START = "2022-09-01"

P = pd.read_parquet(O / "panel_daily.parquet")
TIC = pd.read_parquet(O / "tic_country_monthly.parquet")
OUT: dict = {}


def first_stage(endog: pd.Series, exog: pd.DataFrame, inst: pd.DataFrame, lags: int = 4):
    """手工第一阶段：排除性工具变量的稳健 F 与偏 R²。"""
    X_u = sm.add_constant(pd.concat([exog, inst], axis=1))
    X_r = sm.add_constant(exog)
    u = sm.OLS(endog, X_u).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    r = sm.OLS(endog, X_r).fit()
    f = u.f_test(" , ".join(f"{c} = 0" for c in inst.columns))
    return float(np.squeeze(f.fvalue)), float(f.pvalue), float((r.ssr - u.ssr) / r.ssr)


# ----------------------------------------------------------------- A. 事件研究
def event_study():
    X = pd.DataFrame({k: P[k] * 100 for k in TENORS})                      # 基点
    X["spread_3m_dff"] = P["sp_dff"]
    X["spread_3m_sofr"] = P["sp_sofr"]
    X = X.dropna(how="all")

    def window_change(s: pd.Series, t0: pd.Timestamp) -> float:
        s = s.dropna()
        i = s.index.searchsorted(t0)
        if i < 2 or i + 1 >= len(s):
            return np.nan
        if dff_move(s.index[i + 1]) > 1.0:                                  # 预先规则：窗口内政策利率变动则排除（FOMC 混淆）
            return np.nan
        return s.iloc[i + 1] - s.iloc[i - 2]                                # [-1,+1] 三日变动

    ev_dates = [pd.Timestamp(v[0]) for v in EVENTS.values()]
    dff = (P["DFF"] * 100).dropna()

    def dff_move(t_end: pd.Timestamp, back_days: int = 5) -> float:
        """窗口 [t0-2, t0+1] 内联邦基金有效利率的最大绝对变动（基点）。"""
        seg = dff[(dff.index >= t_end - pd.Timedelta(days=back_days)) & (dff.index <= t_end)]
        return float(seg.max() - seg.min()) if len(seg) else 0.0

    rows = []
    for col in X.columns:
        s = X[col].dropna()
        s = s[s.index >= PLACEBO_START]
        chg = s.diff(3).dropna()
        mask = np.ones(len(chg), bool)
        for d in ev_dates:
            mask &= ~((chg.index >= d - pd.Timedelta(days=7)) & (chg.index <= d + pd.Timedelta(days=7)))
        mask &= np.array([dff_move(t) <= 1.0 for t in chg.index])
        base = chg[mask]
        mu, sd = base.mean(), base.std()
        for eid, (d, cat) in EVENTS.items():
            x = window_change(X[col], pd.Timestamp(d))
            p = (np.abs(base) >= abs(x)).mean() if not np.isnan(x) else np.nan
            rows.append(dict(event=eid, label=EV_LABEL[eid], date=d, category=cat, series=col, change_bp=x, z=(x - mu) / sd, p_placebo=p))
    ev = pd.DataFrame(rows)
    ev.to_csv(T / "event_study_window.csv", index=False)

    # 汇总：各类别平均 z 与基于"置换"的 p 值（随机日期构成的同规模平均）
    rng = np.random.default_rng(20261013)
    summ = []
    for col in X.columns:
        s = X[col].dropna(); s = s[s.index >= PLACEBO_START]; chg = s.diff(3).dropna()
        mask = np.ones(len(chg), bool)
        for d in ev_dates:
            mask &= ~((chg.index >= d - pd.Timedelta(days=7)) & (chg.index <= d + pd.Timedelta(days=7)))
        mask &= np.array([dff_move(t) <= 1.0 for t in chg.index])
        base = chg[mask].values
        if col in ("spread_3m_dff", "DGS3MO"):
            pd.Series(base, name=col).to_csv(T / f"event_placebo_base_{col}.csv", index=False)
        for cat in ["legislative", "rulemaking", "all"]:
            sub = ev[(ev.series == col) & ((ev.category == cat) | (cat == "all"))].dropna(subset=["change_bp"])
            m = sub.change_bp.mean()
            if len(sub) == 0:
                continue
            perm = rng.choice(base, size=(20000, len(sub))).mean(axis=1)
            summ.append(dict(series=col, category=cat, n=len(sub), mean_bp=m, p_perm=(np.abs(perm) >= abs(m)).mean(), placebo_sd=perm.std()))
    summ = pd.DataFrame(summ); summ.to_csv(T / "event_study_summary.csv", index=False)

    # 事件路径（DTB3-DFF）：k=-10..+10，相对 t0-2 的收盘价；及随机日期置换包络
    path = {}
    s = P["sp_dff"].dropna()
    for cat in ["legislative", "rulemaking"]:
        arr = []
        for eid, (d, c) in EVENTS.items():
            if c != cat:
                continue
            i = s.index.searchsorted(pd.Timestamp(d))
            if i - 12 < 0 or i + 11 > len(s):
                continue
            seg = s.iloc[i - 12: i + 11].values
            arr.append(seg - seg[2])        # 以 t0-10 的位置为基准（seg[2] 对应 k=-10）
        path[cat] = np.mean(arr, axis=0) if arr else None
    base_idx = s.index[s.index >= PLACEBO_START]
    envel = []
    for _ in range(2000):
        pick = rng.choice(len(base_idx) - 25, size=7) + 12
        a = [s.loc[base_idx[p - 12: p + 11]].values for p in pick]
        envel.append(np.mean([x - x[2] for x in a], axis=0))
    envel = np.array(envel)
    pe = pd.DataFrame({"k": np.arange(-10, 11), "legislative": path["legislative"][2:], "rulemaking": path["rulemaking"][2:],
                       "lo5": np.percentile(envel[:, 2:], 5, axis=0), "hi95": np.percentile(envel[:, 2:], 95, axis=0),
                       "lo25": np.percentile(envel[:, 2:], 25, axis=0), "hi75": np.percentile(envel[:, 2:], 75, axis=0)})
    pe.to_csv(T / "event_study_path.csv", index=False)
    OUT["event_all_3m_dff"] = summ[(summ.series == "spread_3m_dff") & (summ.category == "all")].iloc[0].to_dict()
    OUT["event_all_3m_yield"] = summ[(summ.series == "DGS3MO") & (summ.category == "all")].iloc[0].to_dict()
    return ev, summ, pe


# ----------------------------------------------------------------- B. 周度局部投影
def weekly() -> pd.DataFrame:
    W = P.resample("W-FRI").last()
    d = pd.DataFrame(index=W.index)
    d["sp_dff"] = W["sp_dff"]; d["sp_sofr"] = W["sp_sofr"]
    d["sp_6m"] = W["sp_6m_dff"]; d["sp_1y"] = W["sp_1y_dff"]; d["sp_2y"] = W["sp_2y_dff"]
    d["DTB3"] = W["DTB3"]
    d["SDT_usd"] = W["SDT_bills_usd"]; d["bills"] = W["bills_usd"]
    d["dSDT"] = d["SDT_usd"].diff() / 1e11                       # 每 1000 亿美元
    d["dbills"] = d["bills"].diff() / 1e11
    d["dTGA"] = W["WTREGEN"].diff() / 1e5                         # WTREGEN 为百万美元 -> 每 1000 亿
    d["dRRP"] = W["RRPONTSYD"].diff() / 100                       # 十亿美元 -> 每 1000 亿
    d["dVIX"] = W["VIXCLS"].diff()
    d["dDFF"] = W["DFF"].diff() * 100
    d["dExp"] = d["sp_2y"].diff()
    d["btc"] = 100 * np.log(W["CBBTCUSD"]).diff()
    d["eth"] = 100 * np.log(W["CBETHUSD"]).diff()
    d["btc_l1"] = d["btc"].shift(1); d["eth_l1"] = d["eth"].shift(1)
    d["vol_btc"] = 100 * np.log(P["CBBTCUSD"]).diff().abs().resample("W-FRI").mean()
    return d


def anderson_rubin(Y, endog, exog, inst, grid=np.arange(-1500, 1501, 10), lags=4):
    """弱工具稳健的 Anderson–Rubin 95% 置信集：对每个 β0 检验 inst 在 (Y-β0·endog) 回归中联合为零。"""
    keep = []
    for b0 in grid:
        y0 = Y - b0 * endog
        X = sm.add_constant(pd.concat([exog, inst], axis=1))
        m = sm.OLS(y0, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        f = m.f_test(" , ".join(f"{c} = 0" for c in inst.columns))
        if float(f.pvalue) > 0.05:
            keep.append(b0)
    if not keep:
        return np.nan, np.nan
    lo = keep[0] if keep[0] > grid[0] else -np.inf
    hi = keep[-1] if keep[-1] < grid[-1] else np.inf
    return lo, hi


def local_projections(d: pd.DataFrame):
    controls = ["dbills", "dTGA", "dRRP", "dVIX", "dDFF", "dExp"]
    outs = {"sp_dff": "3M bill − EFFR", "sp_sofr": "3M bill − SOFR", "sp_1y": "1Y − EFFR (placebo)", "sp_2y": "2Y − EFFR (placebo)"}
    res = []
    samp = d.loc[SAMPLE_START:SAMPLE_END]
    for y, lab in outs.items():
        for h in LP_H:
            dd = samp.copy()
            dd["Y"] = d[y].shift(-h).loc[dd.index] - d[y].shift(1).loc[dd.index]
            dd["Ylag"] = d[y].diff().shift(1).loc[dd.index]
            INST = ["btc", "eth", "btc_l1", "eth_l1"]
            dd = dd.dropna(subset=["Y", "dSDT", "Ylag"] + controls + INST)
            Xc = sm.add_constant(dd[["dSDT"] + controls + ["Ylag"]])
            ols = sm.OLS(dd["Y"], Xc).fit(cov_type="HAC", cov_kwds={"maxlags": max(4, h)})
            iv = IV2SLS(dd["Y"], sm.add_constant(dd[controls + ["Ylag"]]), dd[["dSDT"]], dd[INST]).fit(cov_type="kernel", kernel="bartlett", bandwidth=max(4, h) + 1)
            fF, fP, pR2 = first_stage(dd["dSDT"], dd[controls + ["Ylag"]], dd[INST])
            ar_lo, ar_hi = anderson_rubin(dd["Y"], dd["dSDT"], dd[controls + ["Ylag"]], dd[INST], lags=max(4, h)) if y in ("sp_dff", "sp_sofr") else (np.nan, np.nan)
            res.append(dict(outcome=y, label=lab, h=h, n=len(dd), ar_lo=ar_lo, ar_hi=ar_hi, ols_b=ols.params["dSDT"], ols_se=ols.bse["dSDT"], ols_p=ols.pvalues["dSDT"],
                            iv_b=iv.params["dSDT"], iv_se=iv.std_errors["dSDT"], iv_p=iv.pvalues["dSDT"], f_first=fF, f_p=fP, partial_r2=pR2))
    lp = pd.DataFrame(res); lp.to_csv(T / "local_projections.csv", index=False)
    r0 = lp[(lp.outcome == "sp_dff") & (lp.h == 0)].iloc[0]
    r4 = lp[(lp.outcome == "sp_dff") & (lp.h == 4)].iloc[0]
    OUT["lp_h0"] = r0.to_dict(); OUT["lp_h4"] = r4.to_dict()
    return lp


# ----------------------------------------------------------------- C. 机器学习反事实
def ml_counterfactual(d: pd.DataFrame):
    W = P.resample("W-FRI").last()
    F = pd.DataFrame(index=W.index)
    F["slope_6m3m"] = (W["DGS6MO"] - W["DGS3MO"]) * 100
    F["exp_1y"] = W["sp_1y_dff"]; F["exp_2y"] = W["sp_2y_dff"]
    F["term_10_2"] = W["term_10_2"]; F["vix"] = W["VIXCLS"];
    F["tga"] = W["WTREGEN"] / 1e6; F["rrp"] = W["RRPONTSYD"]; F["reserves"] = W["WRESBAL"] / 1e6
    F["bills_g13"] = (W["bills_usd"] / W["bills_usd"].shift(13) - 1) * 100
    F["be5"] = W["T5YIE"]; F["usd"] = W["DTWEXBGS"]
    F["fed_bills"] = W["WSHOBL"] / 1e6
    y = W["sp_dff"]
    D = pd.concat([y.rename("y"), F], axis=1).loc["2018-06-01":].dropna()
    preds = []
    for yr in [2023, 2024, 2025, 2026]:
        tr = D[D.index < f"{yr}-01-01"]; te = D[(D.index >= f"{yr}-01-01") & (D.index < f"{yr + 1}-01-01")]
        if te.empty:
            continue
        m = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.8, random_state=7).fit(tr.drop(columns="y"), tr["y"])
        preds.append(pd.Series(m.predict(te.drop(columns="y")), index=te.index))
    m_final = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.8, random_state=7).fit(D.drop(columns="y"), D["y"])
    pd.Series(m_final.feature_importances_, index=D.drop(columns="y").columns, name="importance").sort_values(ascending=False).to_csv(T / "ml_importance.csv")
    pr = pd.concat(preds).rename("pred")
    cf = pd.concat([D["y"], pr], axis=1).dropna()
    cf["resid"] = cf["y"] - cf["pred"]
    cf = cf.join(W[["SDT_pct", "SDT_bills_usd", "bills_usd"]])
    cf["dSDT13"] = cf["SDT_bills_usd"].diff(13) / 1e11
    cf["dSDT1"] = cf["SDT_bills_usd"].diff(1) / 1e11
    r2 = 1 - ((cf.y - cf.pred) ** 2).sum() / ((cf.y - cf.y.mean()) ** 2).sum()
    # 残差对 SDT 变动
    reg = cf.dropna(subset=["dSDT13"])
    m1 = sm.OLS(reg["resid"], sm.add_constant(reg["dSDT13"])).fit(cov_type="HAC", cov_kwds={"maxlags": 13})
    reg1 = cf.dropna(subset=["dSDT1"]); reg1 = reg1.assign(res_d=reg1["resid"].diff())
    m2 = sm.OLS(reg1["res_d"].dropna(), sm.add_constant(reg1.loc[reg1["res_d"].notna(), "dSDT1"])).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    cf.to_csv(T / "ml_counterfactual.csv")
    OUT["ml"] = dict(oos_r2=float(r2), n=len(cf), b13=float(m1.params["dSDT13"]), se13=float(m1.bse["dSDT13"]), p13=float(m1.pvalues["dSDT13"]),
                     b1=float(m2.params["dSDT1"]), se1=float(m2.bse["dSDT1"]), p1=float(m2.pvalues["dSDT1"]))
    return cf


# ----------------------------------------------------------------- D. 外国持有人（TIC）
def foreign():
    t = TIC.copy()
    def ser(name, col):
        s = t[t.country == name].set_index("date")[col]
        return s[~s.index.duplicated()]
    M = pd.DataFrame({
        "off_st": ser("Of Which: Foreign Official", "st_hold"), "priv_st": ser("Of Which: Foreign Non-Official", "st_hold"),
        "all_st": ser("All Countries", "st_hold"), "off_tot": ser("Of Which: Foreign Official", "tot_hold"),
        "priv_tot": ser("Of Which: Foreign Non-Official", "tot_hold"),
    })
    D = P.resample("ME").last()
    M = M.join(D[["SDT_bills_usd", "SDT_bills_usd_tether_only", "bills_usd", "CBBTCUSD", "VIXCLS", "DFF", "RRPONTSYD", "WTREGEN"]], how="inner").dropna(subset=["SDT_bills_usd"])
    M["domestic_st"] = M["bills_usd"] - M["all_st"] - M["SDT_bills_usd"]
    M.to_csv(T / "bill_ownership_monthly.csv")
    d = pd.DataFrame(index=M.index)
    for k in ["off_st", "priv_st", "all_st"]:
        d["d_" + k] = M[k].diff() / 1e9
    d["dSDT"] = M["SDT_bills_usd"].diff() / 1e9
    d["dbills"] = M["bills_usd"].diff() / 1e9
    d["dDFF"] = M["DFF"].diff() * 100
    d["dVIX"] = M["VIXCLS"].diff()
    d["btc"] = 100 * np.log(M["CBBTCUSD"]).diff()
    d["btc_l1"] = d["btc"].shift(1)
    d = d.dropna()
    rows = []
    for k in ["d_off_st", "d_priv_st", "d_all_st"]:
        ols = sm.OLS(d[k], sm.add_constant(d[["dSDT", "dbills", "dDFF", "dVIX"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        rows.append(dict(spec="OLS", outcome=k, b=ols.params["dSDT"], se=ols.bse["dSDT"], p=ols.pvalues["dSDT"], n=int(ols.nobs), r2=ols.rsquared))
        try:
            iv = IV2SLS(d[k], sm.add_constant(d[["dbills", "dDFF", "dVIX"]]), d[["dSDT"]], d[["btc", "btc_l1"]]).fit(cov_type="kernel", kernel="bartlett", bandwidth=4)
            fF, fP, pR2 = first_stage(d["dSDT"], d[["dbills", "dDFF", "dVIX"]], d[["btc", "btc_l1"]], lags=3)
            rows.append(dict(spec="IV(BTC)", outcome=k, b=iv.params["dSDT"], se=iv.std_errors["dSDT"], p=iv.pvalues["dSDT"], n=int(iv.nobs), r2=np.nan, f_first=fF))
        except Exception as e:  # noqa: BLE001
            rows.append(dict(spec="IV(BTC)", outcome=k, b=np.nan, se=np.nan, p=np.nan, n=len(d), r2=np.nan, f_first=np.nan))
    fr = pd.DataFrame(rows); fr.to_csv(T / "foreign_holders_regressions.csv", index=False)
    OUT["foreign"] = fr.to_dict("records")

    # 国别异质性：Δ短期持有（十亿美元）对 ΔSDT 的斜率
    official_heavy = ["Japan", "China, Mainland", "India", "Saudi Arabia", "Brazil", "Taiwan", "Korea, South", "Switzerland", "Singapore", "Hong Kong",
                      "Russia", "Poland", "Israel", "Thailand", "Mexico", "Kuwait", "Norway"]
    fin_centers = ["Cayman Islands", "Luxembourg", "Ireland", "Belgium", "United Kingdom", "Bermuda", "Canada", "Bahamas", "British Virgin Islands", "Netherlands", "Jersey", "Guernsey"]
    allc = t[~t.country.str.contains("Total|Of Which|Memo|All Countries|Grand")]
    last = allc[allc.date == allc.date.max()].set_index("country")["st_hold"].sort_values(ascending=False)
    top = [c for c in last.index if c in official_heavy + fin_centers][:20]
    crow = []
    for c in top:
        s = allc[allc.country == c].set_index("date")["st_hold"].diff() / 1e9
        dd = pd.concat([s.rename("y"), d[["dSDT", "dbills", "dDFF", "dVIX"]]], axis=1).dropna()
        if len(dd) < 24:
            continue
        m = sm.OLS(dd["y"], sm.add_constant(dd[["dSDT", "dbills", "dDFF", "dVIX"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        crow.append(dict(country=c, group="official-heavy" if c in official_heavy else "financial center", b=m.params["dSDT"], se=m.bse["dSDT"], p=m.pvalues["dSDT"],
                         st_hold_bn=last[c] / 1e9, n=len(dd)))
    cr = pd.DataFrame(crow).sort_values("b"); cr.to_csv(T / "foreign_country_slopes.csv", index=False)
    return M, fr, cr


if __name__ == "__main__":
    ev, summ, pe = event_study()
    d = weekly()
    lp = local_projections(d)
    cf = ml_counterfactual(d)
    M, fr, cr = foreign()
    d.to_csv(T / "weekly_panel.csv")
    json.dump(OUT, open(ROOT / "06_结果" / "results.json", "w"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 230)
    print("== EVENT SUMMARY (3M-EFFR spread, 3M yield, 1Y, 2Y)")
    print(summ[summ.series.isin(["spread_3m_dff", "DGS3MO", "DGS1", "DGS2"])].round(2).to_string())
    print("== EVENT window z, spread_3m_dff"); print(ev[ev.series == "spread_3m_dff"][["event", "label", "date", "change_bp", "z", "p_placebo"]].round(2).to_string())
    print("== LP sp_dff"); print(lp[lp.outcome == "sp_dff"][["h", "n", "ols_b", "ols_se", "ols_p", "iv_b", "iv_se", "iv_p", "f_first", "partial_r2"]].round(3).to_string())
    print("== LP sp_2y placebo h=0,4,8"); print(lp[(lp.outcome == "sp_2y") & lp.h.isin([0, 4, 8])][["h", "ols_b", "ols_p", "iv_b", "iv_p"]].round(3).to_string())
    print("== ML"); print(json.dumps(OUT["ml"], indent=1))
    print("== Foreign"); print(fr.round(3).to_string())
    print("== Country slopes"); print(cr.round(3).to_string())
