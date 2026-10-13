"""图 4：局部投影——OLS 脉冲响应、安慰剂期限、IV 与弱工具诊断、可检测效应。"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 8.4))
gs = fig.add_gridspec(3, 2, hspace=0.66, wspace=0.34, left=0.085, right=0.95, top=0.945, bottom=0.085)
HX = list(range(0, 13))


def irf(ax, df, col, color, label=None, band=True, ls="-", lw=1.8):
    b = df[f"{col}_b"].values; se = df[f"{col}_se"].values
    if band:
        ax.fill_between(df["h"], b - 1.96 * se, b + 1.96 * se, color=color, alpha=0.16, lw=0)
    ax.plot(df["h"], b, color=color, lw=lw, ls=ls, marker="o", ms=2.8, label=label)


def style(ax, ylab="bp per $100B"):
    zero_line(ax)
    ax.set_xlim(-0.3, 12.3); ax.set_xticks(range(0, 13, 2))
    ax.set_xlabel("weeks after the shock (h)", labelpad=1.5); ax.set_ylabel(ylab.replace("$", "\\$"), labelpad=2)


# ---------------- a 3M-EFFR
ax = fig.add_subplot(gs[0, 0])
d = LP[LP.outcome == "sp_dff"]
irf(ax, d, "ols", C["blue"])
style(ax); ax.set_ylim(-230, 150)
i = d.ols_b.idxmin(); r = d.loc[i]
ax.annotate(f"trough {r.ols_b:.0f} bp\n(h = {int(r.h)}, p = {r.ols_p:.2f})", (r.h, r.ols_b), xytext=(r.h + 1.2, -170), fontsize=6.4, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
ax.text(0.03, 0.95, f"n = {int(d.n.iloc[0])} weeks; HAC 95% band\nall 13 horizons: |t| < 1.7", transform=ax.transAxes, fontsize=6.4, color=INK2, va="top")
panel(ax, "a", "3M bill − EFFR", "response to +$100B issuer T-bill demand; OLS".replace("$", "\\$"))

# ---------------- b 3M-SOFR
ax = fig.add_subplot(gs[0, 1])
d2 = LP[LP.outcome == "sp_sofr"]
irf(ax, d2, "ols", C["aqua"])
style(ax); ax.set_ylim(-230, 150)
j = d2.ols_p.idxmin(); r2 = d2.loc[j]
ax.annotate(f"smallest p = {r2.ols_p:.2f}\n(h = {int(r2.h)}, {r2.ols_b:.0f} bp)", (r2.h, r2.ols_b), xytext=(r2.h + 1.4, -185), fontsize=6.4, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
panel(ax, "b", "3M bill − SOFR", "same design, repo-market benchmark")

# ---------------- c 安慰剂
ax = fig.add_subplot(gs[1, 0])
for y, col, lab in [("sp_1y", C["violet"], "1Y − EFFR"), ("sp_2y", C["yellow"], "2Y − EFFR")]:
    dd = LP[LP.outcome == y]
    irf(ax, dd, "ols", col, lab)
style(ax, "bp per $100B"); ax.set_ylim(-900, 700)
ax.legend(loc="lower left", fontsize=6.3, handlelength=1.1)
ax.text(0.97, 0.95, "longer tenors should not respond\nto bill-specific demand", transform=ax.transAxes, fontsize=6.3, color=INK2, ha="right", va="top")
panel(ax, "c", "Placebo tenors", "OLS with 95% HAC bands; same shock and controls")

# ---------------- d IV
ax = fig.add_subplot(gs[1, 1])
irf(ax, d, "iv", C["orange"])
style(ax); ax.set_ylim(-1000, 1000)
ax.text(0.03, 0.95, "Anderson–Rubin 95% set:\n(−∞, +∞) at every horizon", transform=ax.transAxes, fontsize=6.7, color=C["orange"], fontweight="bold", va="top")
ax.text(0.03, 0.05, "IV is unidentified: crypto returns\nbarely move issuer bill demand", transform=ax.transAxes, fontsize=6.3, color=INK2, va="bottom")
panel(ax, "d", "IV with BTC/ETH returns (2SLS)", "95% bands are not reliable under weak instruments")

# ---------------- e 第一阶段
ax = fig.add_subplot(gs[2, 0])
ax.bar(d["h"], d["f_first"], color=C["orange"], width=0.62, linewidth=0)
ax.axhline(10, color=INK, lw=0.9, ls=(0, (3, 2)))
ax.text(12.3, 10.35, "rule-of-thumb F = 10", fontsize=6.4, color=INK, ha="right", va="bottom")
ax.set_ylim(0, 12); ax.set_xlim(-0.6, 12.6); ax.set_xticks(range(0, 13, 2))
ax.set_xlabel("weeks after the shock (h)", labelpad=1.5); ax.set_ylabel("first-stage F (HAC)", labelpad=2)
ax.text(0.03, 0.62, f"F ≈ {d.f_first.mean():.1f}\npartial R² ≈ {d.partial_r2.mean() * 100:.0f}%\ninstruments: BTC, ETH\nreturns at t and t−1", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
panel(ax, "e", "Instruments are weak", "joint exclusion test of the four return instruments")

# ---------------- f 可检测效应
ax = fig.add_subplot(gs[2, 1])
mde = 2.8 * d["ols_se"] / 100                       # bp per $1B
ax.fill_between(d["h"], 0, mde, color=LGRAY, lw=0)
ax.plot(d["h"], mde, color=INK2, lw=1.5, marker="o", ms=2.8)
cum = bn_ = None
ax.set_xlim(-0.3, 12.3); ax.set_xticks(range(0, 13, 2)); ax.set_ylim(0, 2.5)
ax.set_xlabel("weeks after the shock (h)", labelpad=1.5); ax.set_ylabel("bp per \\$1B", labelpad=2)
ax.text(0.03, 0.95, "80%-power minimum detectable effect\n(2.8 × OLS s.e.)", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
ax.axhline(0.10, color=C["orange"], lw=1.1, ls=(0, (3, 2)))
ax.text(12.3, 0.115, "bp per \\$1B if \\$1T of demand moved bills by 100 bp", fontsize=6.0, color=C["orange"], ha="right", va="bottom")
ax.text(12.3, 2.15, f"h = 4 weeks: ±{mde.iloc[4]:.2f} bp per \\$1B", fontsize=6.3, color=INK2, ha="right")
panel(ax, "f", "What the sample can and cannot rule out", "minimum detectable effect per \\$1B of issuer demand")

fig.text(0.085, 0.032, "Weekly local projections, Jan-2023 to Oct-2026. Outcome: change from t−1 to t+h. Shock: weekly change in issuers' direct T-bill holdings (\\$100B units). Controls: change in bills outstanding, TGA, ON RRP, VIX, EFFR,\n"
         "2Y−EFFR expectations proxy, lagged outcome. HAC (Bartlett, bandwidth max(4, h)+1). Anderson–Rubin sets by grid search over [−1500, 1500] bp per \\$100B; the set covers the whole grid at every h.",
         fontsize=6.0, color=MUTED, va="top")
save(fig, "Fig4_local_projections")
