"""图 7：回购渠道——稳定币发行商的回购放款、回购利差、局部投影、扩展样本与事件研究。"""
from __future__ import annotations

import json

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

RP = pd.read_csv(T / "repo_local_projections.csv")
RE = pd.read_csv(T / "repo_event_study.csv", parse_dates=["date"])
WR = pd.read_csv(T / "weekly_repo_panel.csv", index_col=0, parse_dates=True)
SCALE = json.load(open(ROOT / "06_结果" / "results_repo.json"))["scale"]

fig = plt.figure(figsize=(7.4, 8.8))
gs = fig.add_gridspec(3, 2, hspace=0.66, wspace=0.62, left=0.085, right=0.95, top=0.945, bottom=0.085)

# ---------------- a 回购放款
ax = fig.add_subplot(gs[0, 0])
d = P.loc["2023-01-17":]
ax.stackplot(d.index, d["USDT_repo"].fillna(0) / 1e9, d["USDC_repo"].fillna(0) / 1e9, colors=[ENT["USDT"], ENT["USDC"]], linewidth=0.6, edgecolor=SURF)
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
x_r = d.index[-1] + pd.Timedelta(days=12)
ax.set_xlim(d.index[0], d.index[-1] + pd.Timedelta(days=330)); ax.set_ylim(0, 95)
ax.text(x_r, d["USDC_repo"].iloc[-1] / 1e9 / 2 + d["USDT_repo"].iloc[-1] / 1e9, f"USDC {d['USDC_repo'].iloc[-1] / 1e9:.0f}", color=ENT["USDC"], fontsize=6.4, fontweight="bold", va="center")
ax.text(x_r, d["USDT_repo"].iloc[-1] / 1e9 / 2, f"USDT {d['USDT_repo'].iloc[-1] / 1e9:.0f}", color=ENT["USDT"], fontsize=6.4, fontweight="bold", va="center")
ax.text(0.03, 0.95, f"Total \\${SCALE['repo_usd_bn']:.0f}B = {SCALE['share_tgcr_pct']:.1f}% of daily tri-party\nrepo volume (TGCR); Fed ON RRP take-up\nis \\${SCALE['onrrp_bn']:.1f}B (peak \\$2.4T, Jan-2023)", transform=ax.transAxes, fontsize=6.4, color=INK2, va="top")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
panel(ax, "a", "Stablecoin issuers have become repo lenders", "reverse repo lent by Tether and Circle, \\$ billion")

# ---------------- b 回购利差
ax = fig.add_subplot(gs[0, 1])
w = WR.loc["2023-02-03":]
for i in w.index[w["qe"] > 0]:
    ax.axvspan(i - pd.Timedelta(days=6), i, color=MID, lw=0, zorder=0)
ax.plot(w.index, w["tgcr_rrp"], color=C["aqua"], lw=1.4)
ax.plot(w.index, w["sofr_iorb"], color=C["violet"], lw=1.4)
zero_line(ax)
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
ax.set_xlim(w.index[0], w.index[-1] + pd.Timedelta(days=330)); ax.set_ylim(-16, 30)
x_r = w.index[-1] + pd.Timedelta(days=12)
ax.text(x_r, w["tgcr_rrp"].dropna().iloc[-1] + 2, "TGCR − ON RRP", color=C["aqua"], fontsize=6.4, fontweight="bold", va="center")
ax.text(x_r, w["sofr_iorb"].dropna().iloc[-1] - 3, "SOFR − IORB", color=C["violet"], fontsize=6.4, fontweight="bold", va="center")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
panel(ax, "b", "Repo spreads: funding pressure at quarter-ends", "basis points, weekly mean; grey = quarter-end weeks")

# ---------------- c/d IRF
def irf(ax, sub, color, title, letter, sub_t):
    ax.fill_between(sub["h"], sub["b"] - 1.96 * sub["se"], sub["b"] + 1.96 * sub["se"], color=color, alpha=0.16, lw=0)
    ax.plot(sub["h"], sub["b"], color=color, lw=1.8, marker="o", ms=2.8)
    zero_line(ax); ax.set_xlim(-0.3, 8.3); ax.set_xticks(range(0, 9, 2))
    ax.set_xlabel("weeks after the shock (h)", labelpad=1.5); ax.set_ylabel("bp per \\$100B", labelpad=2)
    mt = (sub["b"] / sub["se"]).abs().max()
    ax.text(0.03, 0.95, f"n = {int(sub.n.iloc[0])} weeks\nmax |t| = {mt:.1f}", transform=ax.transAxes, fontsize=6.4, color=INK2, va="top")
    panel(ax, letter, title, sub_t)


ax = fig.add_subplot(gs[1, 0])
s1 = RP[(RP.spec == "Repo lending, 2023-02 on") & (RP.outcome == "sofr_iorb")]
irf(ax, s1, C["violet"], "SOFR − IORB", "c", "response to +\\$100B stablecoin repo lending; OLS, 95% HAC")
ax.set_ylim(-100, 130)
ax = fig.add_subplot(gs[1, 1])
s2 = RP[(RP.spec == "Repo lending, 2023-02 on") & (RP.outcome == "tgcr_rrp")]
irf(ax, s2, C["aqua"], "TGCR − ON RRP", "d", "same design; tri-party repo benchmark")
ax.set_ylim(-100, 130)

# ---------------- e 扩展样本
ax = fig.add_subplot(gs[2, 0])
a_ = RP[(RP.spec == "Tether T-bills, 2023-02 on") & (RP.outcome == "sp_sofr")]
b_ = RP[(RP.spec == "Tether T-bills, 2021-08 on") & (RP.outcome == "sp_sofr")]
ax.fill_between(b_["h"], b_["b"] - 1.96 * b_["se"], b_["b"] + 1.96 * b_["se"], color=ENT["USDT"], alpha=0.16, lw=0)
ax.plot(b_["h"], b_["b"], color=ENT["USDT"], lw=1.8, marker="o", ms=2.8, label=f"2021-08 on (n = {int(b_.n.iloc[0])})")
ax.plot(a_["h"], a_["b"], color=GRAY, lw=1.4, marker="o", ms=2.4, ls=(0, (3, 1.5)), label=f"2023-02 on (n = {int(a_.n.iloc[0])})")
zero_line(ax); ax.set_xlim(-0.3, 8.3); ax.set_xticks(range(0, 9, 2)); ax.set_ylim(-700, 600)
ax.set_xlabel("weeks after the shock (h)", labelpad=1.5); ax.set_ylabel("bp per \\$100B", labelpad=2)
ax.legend(loc="lower left", fontsize=6.3, handlelength=1.6)
ax.text(0.97, 0.95, f"longer sample: max |t| = {(b_['b'] / b_['se']).abs().max():.1f}", transform=ax.transAxes, fontsize=6.4, color=INK2, ha="right", va="top")
panel(ax, "e", "Longer sample (Tether only)", "3M bill − SOFR response to Tether T-bill demand; 95% HAC band")

# ---------------- f 回购事件研究
ax = fig.add_subplot(gs[2, 1])
r = RE[RE.series == "tgcr_rrp"].copy()
r["lab"] = r["event"].map(EV_SHORT) + "  " + r["date"].dt.strftime("%d %b %y")
ypos = np.arange(len(r))[::-1]
for y, (_, row) in zip(ypos, r.iterrows()):
    if np.isnan(row.change_bp):
        ax.text(0, y, "excluded (FOMC / month-end window)", fontsize=5.9, color=MUTED, va="center", ha="center")
        continue
    sd = row.placebo_sd
    ax.plot([-1.96 * sd, 1.96 * sd], [y, y], color=LGRAY, lw=4.5, solid_capstyle="butt", zorder=1)
    hit = row.p < 0.10
    ax.plot(row.change_bp, y, "o", color=C["orange"] if hit else SURF, mec=C["orange"], mew=1.3, ms=5.2, zorder=3)
    ax.text(14.5, y, f"{row.change_bp:+.0f} (p={row.p:.2f})", fontsize=6.1, color=C["orange"] if hit else INK2, va="center")
ax.axvline(0, color=INK2, lw=0.7)
ax.set_yticks(ypos); ax.set_yticklabels(r["lab"], fontsize=6.0); ax.set_ylim(-0.7, len(r) - 0.3)
ax.set_xlim(-16, 27); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("3-day change in TGCR − ON RRP, bp", labelpad=2)
panel(ax, "f", "Repo spreads around GENIUS events", "grey bar = ±1.96 placebo s.d.; filled dot = p < 0.10")

fig.text(0.085, 0.032, "Panel f: 3 of 7 tested windows have p < 0.10 (House and Signed windows overlap); not robust to multiple-testing correction.\nWeekly local projections. Shock: weekly change in stablecoin issuers' reverse-repo lending (Tether ON+term RRP, Circle repo; interpolated between reports), \\$100B units. Controls: bills outstanding, TGA, ON RRP, bank reserves, VIX, EFFR,\n"
         "month-end and quarter-end week dummies, lagged outcome; HAC. Panels e: Tether T-bills as shock with 3M−SOFR outcome. Event placebo: 3-day windows since Jan-2023 excluding FOMC, month-end and ±7 days around events.",
         fontsize=6.0, color=MUTED, va="top")
save(fig, "Fig7_repo_channel")
