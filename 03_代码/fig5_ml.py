"""图 5：机器学习反事实——样本外预测的 3M 国债利差与稳定币需求的残差检验。"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 8.2))
gs = fig.add_gridspec(3, 2, hspace=0.66, wspace=0.34, left=0.085, right=0.95, top=0.945, bottom=0.085)

# ---------------- a 实际 vs 预测
ax = fig.add_subplot(gs[0, :])
ax.axvspan(SIGNED, ML.index[-1], color=MID, zorder=0)
ax.fill_between(ML.index, ML["pred"], ML["y"], where=ML["y"] >= ML["pred"], color=C["red"], alpha=0.22, lw=0, interpolate=True)
ax.fill_between(ML.index, ML["pred"], ML["y"], where=ML["y"] < ML["pred"], color=C["blue"], alpha=0.22, lw=0, interpolate=True)
ax.plot(ML.index, ML["pred"], color=INK2, lw=1.2, ls=(0, (3, 1.5)), label="Counterfactual (gradient boosting, expanding window)")
ax.plot(ML.index, ML["y"], color=C["blue"], lw=1.8, label="Actual 3M \u2212 EFFR")
zero_line(ax)
ax.set_xlim(ML.index[0], ML.index[-1])
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.legend(loc="upper center", fontsize=6.5, handlelength=1.8, bbox_to_anchor=(0.46, 1.0))
ax.text(0.01, 0.04, f"out-of-sample R\u00b2 = {RES['ml']['oos_r2']:.2f},  n = {RES['ml']['n']} weeks.  Red = actual above counterfactual; blue = below", transform=ax.transAxes, fontsize=6.5, color=INK2, ha="left", va="bottom")
ax.text(SIGNED, ax.get_ylim()[1] - 2, " post-GENIUS", fontsize=6.2, color=INK2, va="top")
panel(ax, "a", "Counterfactual 3M bill spread without stablecoin information", "bp; model retrained each January on data through the prior year; features exclude all stablecoin variables")

# ---------------- b 残差散点
ax = fig.add_subplot(gs[1, 0])
r = ML.dropna(subset=["dSDT13"])
ax.scatter(r["dSDT13"] * 100, r["resid"], s=9, color=LGRAY, lw=0, zorder=2)
q = pd.qcut(r["dSDT13"], 6, duplicates="drop")
g = r.groupby(q, observed=True).agg(x=("dSDT13", "mean"), y=("resid", "mean"), se=("resid", lambda v: v.std() / np.sqrt(len(v))))
ax.errorbar(g["x"] * 100, g["y"], yerr=1.96 * g["se"], fmt="o", color=C["orange"], ms=5, mec=SURF, mew=0.6, ecolor=C["orange"], elinewidth=1.0, zorder=4)
m = sm.OLS(r["resid"], sm.add_constant(r["dSDT13"] * 100)).fit(cov_type="HAC", cov_kwds={"maxlags": 13})
xs = np.linspace((r["dSDT13"] * 100).min(), (r["dSDT13"] * 100).max(), 50); pr = m.get_prediction(sm.add_constant(xs)).summary_frame()
ax.fill_between(xs, pr["mean_ci_lower"], pr["mean_ci_upper"], color=C["orange"], alpha=0.15, lw=0); ax.plot(xs, pr["mean"], color=C["orange"], lw=1.5)
zero_line(ax)
ax.text(0.03, 0.96, f"slope {m.params.iloc[1]:+.2f} bp per \\$1B\n(HAC se {m.bse.iloc[1]:.2f}, p = {m.pvalues.iloc[1]:.2f})", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
ax.set_xlabel("13-week change in issuers' T-bill holdings, \\$ billion", labelpad=2); ax.set_ylabel("residual, bp", labelpad=2); ax.grid(axis="x")
panel(ax, "b", "Residuals do not line up with issuer demand", "actual minus counterfactual vs 13-week change in SDT")

# ---------------- c 特征重要性
ax = fig.add_subplot(gs[1, 1])
imp = MLI.sort_values().tail(10)
names = {"exp_1y": "1Y \u2212 EFFR", "exp_2y": "2Y \u2212 EFFR", "slope_6m3m": "6M \u2212 3M slope", "term_10_2": "10Y \u2212 2Y", "vix": "VIX", "tga": "TGA", "rrp": "ON RRP",
         "reserves": "Bank reserves", "bills_g13": "Bill supply growth (13w)", "be5": "5Y breakeven", "usd": "Broad dollar", "fed_bills": "Fed bill holdings"}
ax.barh(range(len(imp)), imp.values * 100, color=BLUE_SEQ[4], height=0.66, linewidth=0)
ax.set_yticks(range(len(imp))); ax.set_yticklabels([names.get(k, k) for k in imp.index], fontsize=6.6)
for i, v in enumerate(imp.values * 100):
    ax.text(v + 0.8, i, f"{v:.0f}%", va="center", fontsize=6.4, color=INK2)
ax.set_xlim(0, imp.max() * 100 * 1.18); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("share of total impurity reduction", labelpad=2)
panel(ax, "c", "What drives the counterfactual", "feature importance, model fit on all data")

# ---------------- d 年度 RMSE vs 随机游走
ax = fig.add_subplot(gs[2, 0])
yr = ML.groupby(ML.index.year)
rm = yr.apply(lambda g: np.sqrt(((g["y"] - g["pred"]) ** 2).mean()))
rw = yr.apply(lambda g: np.sqrt(((g["y"] - g["y"].shift(1)) ** 2).dropna().mean()))
mn = yr.apply(lambda g: np.sqrt(((g["y"] - ML["y"].shift(1).loc[g.index].mean() * 0 - g["y"].mean()) ** 2).mean()))
x = np.arange(len(rm)); w_ = 0.36
ax.bar(x - w_ / 2, rm.values, w_, color=C["blue"], label="Gradient boosting", linewidth=0)
ax.bar(x + w_ / 2, rw.values, w_, color=LGRAY, label="Random walk (last week)", linewidth=0)
for i, (a, b) in enumerate(zip(rm.values, rw.values)):
    ax.text(i - w_ / 2, a + 0.2, f"{a:.1f}", ha="center", fontsize=6.4, color=C["blue"], fontweight="bold")
    ax.text(i + w_ / 2, b + 0.2, f"{b:.1f}", ha="center", fontsize=6.4, color=INK2)
ax.set_xticks(x); ax.set_xticklabels([str(i) + ("*" if i == 2026 else "") for i in rm.index]); ax.legend(loc="upper right", fontsize=6.3, handlelength=1.0)
ax.set_ylabel("RMSE, bp", labelpad=2); ax.set_ylim(0, max(rm.max(), rw.max()) * 1.25)
panel(ax, "d", "Counterfactual skill by year", "out-of-sample RMSE; * = Jan\u2013Oct 2026")

# ---------------- e 累计残差
ax = fig.add_subplot(gs[2, 1])
c = ML["resid"].copy()
cum = c.rolling(13).mean()
ax.fill_between(cum.index, 0, cum, where=cum >= 0, color=C["red"], alpha=0.25, lw=0); ax.fill_between(cum.index, 0, cum, where=cum < 0, color=C["blue"], alpha=0.25, lw=0)
ax.plot(cum.index, cum, color=INK2, lw=1.2)
ax2 = ax
zero_line(ax)
sdt = ML["SDT_bills_usd"] / 1e9
ax.set_xlim(ML.index[0], ML.index[-1]); ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
corr = np.corrcoef(cum.dropna().loc[sdt.dropna().index.intersection(cum.dropna().index)], sdt.loc[sdt.dropna().index.intersection(cum.dropna().index)])[0, 1]
ax.text(0.64, 0.96, f"corr(residual, SDT level) = {corr:+.2f}\nresiduals revert to zero", transform=ax.transAxes, fontsize=6.4, color=INK2, va="top")
ax.set_ylabel("13-week mean residual, bp", labelpad=2)
panel(ax, "e", "Residuals stay mean-reverting", "13-week rolling mean of actual minus counterfactual")

fig.text(0.085, 0.032, "Features (weekly): 6M\u22123M slope, 1Y/2Y minus EFFR, 10Y\u22122Y, VIX, TGA, ON RRP, bank reserves, bill-supply growth, 5Y breakeven, broad dollar index, Fed bill holdings. "
         "Training sample 2018-06 onward;\n300 trees, depth 3, learning rate 0.03, subsample 0.8. Residual regression uses HAC (13 lags). Random-walk benchmark = last week's spread.",
         fontsize=6.0, color=MUTED, va="top")
save(fig, "Fig5_ml_counterfactual")
