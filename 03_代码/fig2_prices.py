"""图 2：价格动态——利率水平、国库券利差、曲线热图、发行吸收与滚动相关。"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 8.8))
gs = fig.add_gridspec(3, 2, hspace=0.62, wspace=0.40, left=0.075, right=0.915, top=0.945, bottom=0.075)

# ---------------- a 利率水平
ax = fig.add_subplot(gs[0, 0])
w = P.resample("W-FRI").last().loc["2018-04-06":]
ax.axvspan(SIGNED, w.index[-1], color=MID, zorder=0)
ax.plot(w.index, w["DFF"], color=INK2, lw=1.2, label="Effective fed funds")
ax.plot(w.index, w["SOFR"], color=C["aqua"], lw=1.0)
ax.plot(w.index, w["DTB3"], color=C["blue"], lw=1.6)
for lab, col, ser in [("3M bill", C["blue"], w["DTB3"]), ("SOFR", C["aqua"], w["SOFR"]), ("EFFR", INK2, w["DFF"])]:
    pass
x_r = w.index[-1] + pd.Timedelta(days=15)
ax.set_xlim(w.index[0], w.index[-1] + pd.Timedelta(days=300)); ax.set_ylim(0, 5.8)
ev = {"3M bill": (w["DTB3"].dropna().iloc[-1] + 0.30, C["blue"], "bold"), "EFFR": (w["DFF"].dropna().iloc[-1] - 0.02, INK2, "normal"), "SOFR": (w["SOFR"].dropna().iloc[-1] - 0.34, C["aqua"], "normal")}
vals = {"3M bill": w["DTB3"].dropna().iloc[-1], "EFFR": w["DFF"].dropna().iloc[-1], "SOFR": w["SOFR"].dropna().iloc[-1]}
for k, (yy, col, wt) in ev.items():
    ax.text(x_r, yy, f"{k} {vals[k]:.2f}", color=col, fontsize=6.4, fontweight=wt, va="center")
ax.text(SIGNED + pd.Timedelta(days=12), 5.6, "post-GENIUS", fontsize=6.2, color=INK2, va="top")
ax.xaxis.set_major_locator(mdates.YearLocator(2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
panel(ax, "a", "Bill yields track the policy rate", "%, weekly; shaded = after GENIUS Act signing")

# ---------------- b 利差
ax = fig.add_subplot(gs[0, 1])
d = P.loc["2021-07-01":, ["sp_dff"]].dropna()
d["ma"] = d["sp_dff"].rolling(65, min_periods=30).mean()
ax.plot(d.index, d["sp_dff"].clip(-60, 100), color=LGRAY, lw=0.6)
ax.plot(d.index, d["ma"], color=C["blue"], lw=1.8)
zero_line(ax)
ev_y = -57
for eid in EV_IDS:
    col = INK if eid in ("E02", "E03", "E04") else C["orange"]
    ax.plot(EV_DATE[eid], ev_y, marker="^", ms=4.2, color=col, mec=SURF, mew=0.5, clip_on=False, zorder=5)
ax.text(EV_DATE["E02"] - pd.Timedelta(days=15), ev_y + 3, "legislative", fontsize=5.8, color=INK, ha="right", va="bottom")
ax.text(EV_DATE["E13"] + pd.Timedelta(days=25), ev_y + 3, "rulemaking", fontsize=5.8, color=C["orange"], ha="right", va="bottom")
ax.set_ylim(-62, 100)
endlabel(ax, d.index[-1], d["ma"].iloc[-1], f"{d['ma'].iloc[-1]:.0f} bp", C["blue"])
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
panel(ax, "b", "3M bill spread to EFFR", "basis points; daily (grey) and 65-day mean (blue)")

# ---------------- c 曲线热图
ax = fig.add_subplot(gs[1, 0])
ten = {"1M": "sp_1m_dff", "3M": "sp_dff", "6M": "sp_6m_dff", "1Y": "sp_1y_dff", "2Y": "sp_2y_dff"}
H = pd.DataFrame({k: P[v].resample("ME").mean() for k, v in ten.items()}).loc["2022-07-31":].dropna()
cmap = LinearSegmentedColormap.from_list("div", [C["blue"], MID, C["red"]])
im = ax.imshow(H.T.values, aspect="auto", cmap=cmap, norm=TwoSlopeNorm(vmin=-70, vcenter=0, vmax=70), interpolation="nearest")
ax.set_yticks(range(5)); ax.set_yticklabels(list(ten.keys())); ax.grid(False)
ticks = [i for i, dd in enumerate(H.index) if dd.month in (1, 7)]
ax.set_xticks(ticks); ax.set_xticklabels([H.index[i].strftime("%b\n%y") for i in ticks])
sg = H.index.get_indexer([SIGNED + pd.offsets.MonthEnd(0)])[0]
ax.axvline(sg, color=INK, lw=0.9, ls=(0, (3, 2)))
for sp in ax.spines.values():
    sp.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02, aspect=18)
cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6, length=0)
cb.set_ticks([-60, -30, 0, 30, 60])
ax.set_ylim(4.5, -0.5)
panel(ax, "c", "Term structure of the bill-curve gap", "yield minus EFFR, bp, monthly mean; blue = cuts priced")

# ---------------- d binscatter
ax = fig.add_subplot(gs[1, 1])
dd = WK.loc["2023-01-27":"2026-10-09"].copy()
dd["dy"] = dd["sp_dff"].diff()
dd["dSDT"] = dd["dSDT"] * 100  # 每 1000 亿 -> 十亿美元
dd = dd.dropna(subset=["dSDT", "dy"])
ax.scatter(dd["dSDT"], dd["dy"], s=7, color=LGRAY, alpha=0.9, lw=0, zorder=2)
q = pd.qcut(dd["dSDT"], 8, duplicates="drop")
g = dd.groupby(q, observed=True).agg(x=("dSDT", "mean"), y=("dy", "mean"), se=("dy", lambda v: v.std() / np.sqrt(len(v))))
ax.errorbar(g["x"], g["y"], yerr=1.96 * g["se"], fmt="o", color=C["orange"], ms=4.8, mec=SURF, mew=0.6, ecolor=C["orange"], elinewidth=1.0, capsize=0, zorder=4)
X = sm.add_constant(dd["dSDT"]); m = sm.OLS(dd["dy"], X).fit(cov_type="HC1")
xs = np.linspace(dd["dSDT"].min(), dd["dSDT"].max(), 50); pr = m.get_prediction(sm.add_constant(xs)).summary_frame(alpha=0.05)
ax.fill_between(xs, pr["mean_ci_lower"], pr["mean_ci_upper"], color=C["orange"], alpha=0.15, lw=0, zorder=1)
ax.plot(xs, pr["mean"], color=C["orange"], lw=1.4, zorder=3)
zero_line(ax)
ax.text(0.03, 0.96, f"slope {m.params['dSDT']:+.2f} bp per \\$1B (se {m.bse['dSDT']:.2f})\nn = {len(dd)} weeks, p = {m.pvalues['dSDT']:.2f}", transform=ax.transAxes, fontsize=6.6, color=INK2, va="top")
ax.set_xlabel("Weekly change in issuers' T-bill holdings, \\$ billion", labelpad=2); ax.set_ylabel("Weekly change in 3M spread, bp", labelpad=2)
ax.grid(axis="x")
panel(ax, "d", "No visible week-to-week price footprint", "grey = weeks, orange = octile bins (±1.96 se), line = OLS fit")

# ---------------- e 发行吸收
ax = fig.add_subplot(gs[2, 0])
mo = P.resample("ME").last().loc["2023-01-31":]
net = mo["bills_usd"].diff() / 1e9; sdt = mo["SDT_bills_usd"].diff() / 1e9
net, sdt = net.dropna(), sdt.dropna()
x = np.arange(len(net))
ax.bar(x, net.values, color=LGRAY, width=0.82, label="Net bill issuance", linewidth=0)
ax.bar(x, sdt.reindex(net.index).values, color=C["orange"], width=0.42, label="Issuers' T-bill holdings", linewidth=0)
zero_line(ax)
ticks = [i for i, dd_ in enumerate(net.index) if dd_.month in (1, 7)]
ax.set_xticks(ticks); ax.set_xticklabels([net.index[i].strftime("%b\n%y") for i in ticks])
ax.set_xlim(-0.8, len(net) - 0.2)
ax.legend(loc="upper left", fontsize=6.4, handlelength=0.9)
cs = sdt.sum(); cn = net.sum()
ax.text(0.99, 0.04, f"cumulative since 2023: issuers +\\${cs:.0f}B vs net issuance +\\${cn:.0f}B ({cs / cn * 100:.0f}%)", transform=ax.transAxes, ha="right", fontsize=6.3, color=INK2)
ax.set_ylim(-420, 520)
panel(ax, "e", "Treasury's bill issuance dwarfs issuer demand", "\\$ billion per month")

# ---------------- f 滚动相关
ax = fig.add_subplot(gs[2, 1])
dw = WK.loc["2022-06-01":].copy()
dw["dy"] = dw["sp_dff"].diff()
rc = dw["dy"].rolling(26).corr(dw["dSDT"]).dropna()
rc = rc.loc["2023-12-01":] if len(rc) else rc
band = 1.96 / np.sqrt(26)
ax.fill_between(rc.index, -band, band, color=MID, lw=0)
ax.plot(rc.index, rc, color=C["blue"], lw=1.6)
zero_line(ax)
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
ax.text(rc.index[-1], -band - 0.03, "grey band: ±1.96/√26", fontsize=6.1, color=MUTED, va="top", ha="right")
out = (rc.abs() > band).mean() * 100
ax.text(0.02, 0.96, f"{out:.0f}% of windows outside the band;\nmean correlation {rc.mean():+.2f}", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
ax.set_ylim(-0.8, 0.8)
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
panel(ax, "f", "The relationship is unstable and mostly inside noise", "26-week rolling correlation: Δ3M spread vs Δ issuer bill holdings")

fig.text(0.075, 0.032, "Sources: FRED (DTB3, SOFR, DFF), U.S. Treasury yield curve, Fiscal Data (MSPD, DTS), DefiLlama, issuer attestations; author calculations. Weekly panel Jan-2023 to Oct-2026 (n = 194).\n"
         "Panel d: HC1 robust se. Triangles in b mark the ten event-study dates (see Fig. 3); the FOMC-contaminated Tsy ANPRM window is excluded from the tests.",
         fontsize=6.1, color=MUTED, va="top")
save(fig, "Fig2_price_dynamics")
