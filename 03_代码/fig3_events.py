"""图 3：事件研究——GENIUS 法案十个监管/立法节点上的国库券价格反应。"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 9.2))
gs = fig.add_gridspec(4, 2, height_ratios=[1, 1, 1, 0.78], hspace=0.78, wspace=0.40, left=0.115, right=0.93, top=0.945, bottom=0.07)
COLS = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS10", "spread_3m_dff", "spread_3m_sofr"]
CLAB = ["1M", "3M", "6M", "1Y", "2Y", "10Y", "3M−EFFR", "3M−SOFR"]
cmap = LinearSegmentedColormap.from_list("div", [C["blue"], MID, C["red"]])

# ---------------- a 热图
ax = fig.add_subplot(gs[0:2, 0])
Z = EVW.pivot(index="event", columns="series", values="z").reindex(index=EV_IDS, columns=COLS)
B = EVW.pivot(index="event", columns="series", values="change_bp").reindex(index=EV_IDS, columns=COLS)
im = ax.imshow(np.ma.masked_invalid(Z.values), aspect="auto", cmap=cmap, norm=TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3))
ax.grid(False)
for i, eid in enumerate(EV_IDS):
    for j, cc in enumerate(COLS):
        v = B.loc[eid, cc]
        if np.isnan(v):
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=SURF, edgecolor=LGRAY, hatch="////", lw=0))
        else:
            z = Z.loc[eid, cc]
            ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=6.4, color="white" if abs(z) > 1.7 else INK)
ax.set_xticks(range(len(COLS))); ax.set_xticklabels(CLAB, fontsize=6.6)
ax.xaxis.tick_top()
ax.set_yticks(range(len(EV_IDS)))
ax.set_yticklabels([f"{EV_SHORT[e]}\n{EV_DATE[e]:%d %b %y}" for e in EV_IDS], fontsize=6.0, linespacing=1.0)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.axhline(2.5, color=INK, lw=0.8)
ax.text(-0.5, 2.65, "", fontsize=6)
ax.text(len(COLS) - 0.35, 1.0, "legislative", rotation=270, fontsize=6.2, color=INK2, va="center", ha="left")
ax.text(len(COLS) - 0.35, 6.0, "rulemaking", rotation=270, fontsize=6.2, color=C["orange"], va="center", ha="left")
cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.032, pad=0.03, aspect=30)
cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6, length=0); cb.set_label("z-score vs placebo 3-day changes (bp in cells)", fontsize=6.3, color=INK2, labelpad=2)
ax.text(0.0, 1.14, "a", transform=ax.transAxes, fontsize=10.5, fontweight="bold", va="bottom")
ax.text(0.07, 1.14, "Three-day price response by event", transform=ax.transAxes, fontsize=8.4, fontweight="bold", va="bottom")
ax.text(0.07, 1.085, "[−1, +1] change, bp; hatched = excluded (FOMC cut inside window)", transform=ax.transAxes, fontsize=6.7, color=MUTED, va="bottom")

# ---------------- b/c 路径
for r, (cat, title, col, lab) in enumerate([("legislative", "Legislative events (n = 3)", INK, "b"), ("rulemaking", "Rulemaking events (n = 6)", C["orange"], "c")]):
    ax = fig.add_subplot(gs[r, 1])
    ax.fill_between(EVP["k"], EVP["lo5"], EVP["hi95"], color=MID, lw=0, label="placebo 5–95%")
    ax.fill_between(EVP["k"], EVP["lo25"], EVP["hi75"], color=LGRAY, alpha=0.7, lw=0, label="placebo 25–75%")
    ax.plot(EVP["k"], EVP[cat], color=col, lw=1.9, marker="o", ms=2.6)
    zero_line(ax); ax.axvline(0, color=INK, lw=0.8, ls=(0, (3, 2)))
    ax.set_xlim(-10, 10); ax.set_xticks([-10, -5, 0, 5, 10]); ax.set_ylim(-16, 16)
    ax.set_xlabel("trading days relative to event", labelpad=1.5)
    if r == 0:
        ax.legend(loc="lower left", fontsize=6.0, handlelength=1.0, ncol=2, bbox_to_anchor=(0.0, 0.0))
    panel(ax, lab, f"3M−EFFR path: {cat}", "bp, relative to day −10; mean over events")

# ---------------- d 置换分布
ax = fig.add_subplot(gs[2, 0])
base = pd.read_csv(T / "event_placebo_base_spread_3m_dff.csv").iloc[:, 0].values
ax.hist(base, bins=np.arange(-30.5, 30.6, 1), color=LGRAY, edgecolor=SURF, lw=0.4, density=True)
ev = EVW[(EVW.series == "spread_3m_dff")].dropna(subset=["change_bp"])
for _, r in ev.iterrows():
    col = INK if r.category == "legislative" else C["orange"]
    ax.plot([r.change_bp] * 2, [0, 0.012], color=col, lw=1.4)
    ax.plot(r.change_bp, 0.014, marker="v", color=col, ms=4.5, mec=SURF, mew=0.4, clip_on=False)
ax.set_xlim(-25, 25)
ax.text(0.97, 0.95, f"placebo: {len(base):,} three-day windows\nmean {base.mean():+.1f}, sd {base.std():.1f} bp\n9 event windows within\n±{1.96 * base.std():.0f} bp (95%)", transform=ax.transAxes, fontsize=6.4, color=INK2, ha="right", va="top")
ax.set_xlabel("3-day change in 3M−EFFR, bp", labelpad=2); ax.set_yticks([])
ax.grid(False)
ax.legend([plt.Line2D([0], [0], color=INK, lw=1.4), plt.Line2D([0], [0], color=C["orange"], lw=1.4)], ["legislative", "rulemaking"], loc="upper left", fontsize=6.2, handlelength=1.0)
panel(ax, "d", "Event moves sit inside the placebo distribution", "no-FOMC windows since Sep-2022; ticks = events")

# ---------------- e 汇总
ax = fig.add_subplot(gs[2, 1])
sm_ = EVS[EVS.category == "all"].set_index("series").reindex(COLS)
yy = np.arange(len(COLS))[::-1]
for y, (k, r) in zip(yy, sm_.iterrows()):
    ci = 1.96 * r.placebo_sd
    ax.plot([-ci, ci], [y, y], color=LGRAY, lw=4.5, solid_capstyle="butt", zorder=1)
    ax.plot(r.mean_bp, y, "o", color=C["orange"], ms=5.2, mec=SURF, mew=0.6, zorder=3)
    ax.text(ci + 0.4, y, f"{r.mean_bp:+.1f}  (p={r.p_perm:.2f})", fontsize=6.2, color=INK2, va="center")
ax.axvline(0, color=INK2, lw=0.7)
ax.set_yticks(yy); ax.set_yticklabels(CLAB, fontsize=6.6); ax.set_ylim(-0.7, len(COLS) - 0.3)
ax.set_xlim(-12, 17); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("mean event-window change, bp", labelpad=2)
panel(ax, "e", "Pooled effect: 95% placebo bounds around zero", "grey bar = ±1.96 placebo s.d. of the 9-event mean; dot = estimate")

# ---------------- f 供给时间线
ax = fig.add_subplot(gs[3, :])
s = SC.loc["2025-04-01":, ["USDT", "USDC"]].sum(axis=1) / 1e9
ax.plot(s.index, s, color=C["orange"], lw=1.9)
ax.fill_between(s.index, s.min() * 0.97, s, color=C["orange"], alpha=0.08, lw=0)
OFF = {"E02": (-9, "top", "center"), "E03": (-10, "top", "center"), "E04": (7, "bottom", "center"), "E05": (7, "bottom", "right"), "E07": (7, "bottom", "right"),
       "E08": (-9, "top", "center"), "E09": (7, "bottom", "right"), "E10": (7, "bottom", "left"), "E11": (-9, "top", "center"), "E13": (7, "bottom", "center")}
for eid in EV_IDS:
    d0 = EV_DATE[eid]
    if d0 < s.index[0]:
        continue
    v = s.loc[:d0].iloc[-1]
    col = INK if eid in ("E02", "E03", "E04") else C["orange"]
    ax.plot(d0, v, marker="o", ms=4.6, color=SURF, mec=col, mew=1.3, zorder=4)
    dy, va, ha = OFF[eid]
    ax.text(d0, v + dy, EV_SHORT[eid], fontsize=5.8, color=INK2, ha=ha, va=va)
ax.set_ylim(s.min() * 0.97, s.max() * 1.07); ax.set_xlim(s.index[0], s.index[-1])
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
ax.text(0.01, 0.94, f"USDT+USDC: \\${s.loc[:'2025-06-17'].iloc[-1]:.0f}B at Senate vote → \\${s.iloc[-1]:.0f}B today", transform=ax.transAxes, fontsize=6.6, color=INK2, va="top")
ax.text(0, 1.24, "f", transform=ax.transAxes, fontsize=10.5, fontweight="bold", va="bottom")
ax.text(0.035, 1.24, "Supply kept growing through the regulatory sequence", transform=ax.transAxes, fontsize=8.4, fontweight="bold", va="bottom")
ax.text(0.035, 1.10, "USDT + USDC outstanding, \\$ billion, with event dates", transform=ax.transAxes, fontsize=6.7, color=MUTED, va="bottom")

fig.text(0.115, 0.03, "Windows: close of day t+1 minus close of day t−2. Placebo: all 3-day windows from Sep-2022 excluding ±7 days around events and any window with an EFFR change (FOMC). "
         "Permutation p-values: 20,000\nrandom draws of the same number of placebo windows. The Treasury ANPRM window (19 Sep 2025) is excluded because of the 17 Sep FOMC cut. Single-source and weekend dates (E01, E06, E12, E14–E16) are not tested.",
         fontsize=6.0, color=MUTED, va="top")
save(fig, "Fig3_event_study")
