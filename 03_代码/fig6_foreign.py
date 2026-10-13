"""图 6：外国持有人与情景推演——是否挤出官方持有人，以及 GENIUS 规模下的需求有多大。"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.ticker import FuncFormatter

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 9.0))
gs = fig.add_gridspec(3, 2, hspace=0.66, wspace=0.52, left=0.12, right=0.95, top=0.945, bottom=0.075)
o = OWN.sort_index()

# ---------------- a 持有结构（美元）
ax = fig.add_subplot(gs[0, 0])
x = o.index
ax.plot(x, o["priv_st"] / 1e9, color=ENT["PRIVATE"], lw=1.7)
ax.plot(x, o["off_st"] / 1e9, color=ENT["OFFICIAL"], lw=1.7)
ax.plot(x, o["SDT_bills_usd"] / 1e9, color=ENT["SDT"], lw=1.9)
last = x[-1]
ax.set_xlim(x[0], last + pd.Timedelta(days=170)); ax.set_ylim(0, 1300)
for col, ser, lab in [(ENT["PRIVATE"], o["priv_st"], "Foreign private"), (ENT["OFFICIAL"], o["off_st"], "Foreign official"), (ENT["SDT"], o["SDT_bills_usd"], "Issuers")]:
    ax.text(last + pd.Timedelta(days=12), ser.iloc[-1] / 1e9, f"{lab}\n{ser.iloc[-1] / 1e9:,.0f}", color=col, fontsize=6.4, fontweight="bold", va="center")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
panel(ax, "a", "Short-term Treasury holdings by holder type", "\\$ billion, month-end; TIC (≤ 1 year) and issuer reserve reports")

# ---------------- b 回归系数
ax = fig.add_subplot(gs[0, 1])
rows = [("Foreign official", "d_off_st", ENT["OFFICIAL"]), ("Foreign private", "d_priv_st", ENT["PRIVATE"]), ("All foreign", "d_all_st", INK2)]
ypos, yl = [], []
yy = 0
for lab, key, col in rows:
    for spec, mk in [("OLS", "o"), ("IV(BTC)", "D")]:
        r = FR[(FR.outcome == key) & (FR.spec == spec)].iloc[0]
        ci = 1.96 * r.se
        ax.plot([r.b - ci, r.b + ci], [yy, yy], color=col, lw=1.6, alpha=0.55 if spec != "OLS" else 1.0)
        ax.plot(r.b, yy, mk, color=col if spec == "OLS" else SURF, mec=col, mew=1.3, ms=5.4)
        ax.text(max(r.b + ci, 0) + 0.35, yy, f"{r.b:+.2f}", fontsize=6.3, color=INK2, va="center")
        ypos.append(yy); yl.append(f"{lab}\n{spec}" if spec == "OLS" else f"{spec}")
        yy -= 1
    yy -= 0.5
ax.set_yticks(ypos); ax.set_yticklabels(yl, fontsize=6.2, linespacing=0.95); ax.set_ylim(yy + 0.6, 0.7)
ax.axvline(0, color=INK2, lw=0.7); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlim(-9, 6.5); ax.set_xlabel("\\$ change in holdings per \\$1 of issuer T-bill demand", labelpad=2)
f1 = FR[(FR.spec == "IV(BTC)")].f_first.iloc[0]
ax.text(0.02, 0.02, f"IV first-stage F = {f1:.1f} (weak)", transform=ax.transAxes, fontsize=6.2, color=INK2, ha="left", va="bottom")
panel(ax, "b", "No crowding-out of official holders", "monthly OLS/IV, 95% HAC intervals, n = 41")

# ---------------- c 国别斜率
ax = fig.add_subplot(gs[1, 0])
cr = CR.sort_values("b", ascending=False).reset_index(drop=True)
for i, r in cr.iterrows():
    col = ENT["OFFICIAL"] if r.group == "official-heavy" else C["aqua"]
    sig = r.p < 0.05
    ax.plot([r.b - 1.96 * r.se, r.b + 1.96 * r.se], [i, i], color=col, lw=1.4, alpha=0.7)
    ax.plot(r.b, i, "o", color=col if sig else SURF, mec=col, mew=1.3, ms=4.6)
ax.set_yticks(range(len(cr))); ax.set_yticklabels([c.replace("China, Mainland", "China").replace("Korea, South", "S. Korea").replace("British Virgin Islands", "BVI").replace("United Kingdom", "UK") for c in cr.country], fontsize=6.0)
ax.axvline(0, color=INK2, lw=0.7); ax.invert_yaxis(); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("\\$ per \\$1 of issuer demand", labelpad=2)
ax.legend([plt.Line2D([0], [0], marker="o", color=ENT["OFFICIAL"], lw=0, mfc=ENT["OFFICIAL"]), plt.Line2D([0], [0], marker="o", color=C["aqua"], lw=0, mfc=C["aqua"]),
           plt.Line2D([0], [0], marker="o", color=INK2, lw=0, mfc=SURF)], ["official-heavy", "financial centre", "p ≥ 0.05 (open)"], loc="upper left", fontsize=5.9, handletextpad=0.2)
npass = int((cr.p < 0.05).sum())
ax.text(0.98, 0.03, f"{npass} of {len(cr)} at p < 0.05;\nBonferroni threshold 0.0025", transform=ax.transAxes, fontsize=5.9, color=INK2, ha="right", va="bottom")
panel(ax, "c", "Country slopes: exploratory", "20 largest bill holders; OLS with HAC 95% intervals")

# ---------------- d 散点
ax = fig.add_subplot(gs[1, 1])
dd = pd.DataFrame({"y": o["off_st"].diff() / 1e9, "x": o["SDT_bills_usd"].diff() / 1e9}).dropna()
ax.scatter(dd["x"], dd["y"], s=14, color=ENT["OFFICIAL"], alpha=0.75, lw=0, zorder=3)
m = sm.OLS(dd["y"], sm.add_constant(dd["x"])).fit(cov_type="HC1")
xs = np.linspace(dd["x"].min(), dd["x"].max(), 40); pr = m.get_prediction(sm.add_constant(xs)).summary_frame()
ax.fill_between(xs, pr["mean_ci_lower"], pr["mean_ci_upper"], color=ENT["OFFICIAL"], alpha=0.14, lw=0); ax.plot(xs, pr["mean"], color=ENT["OFFICIAL"], lw=1.5)
zero_line(ax); ax.axvline(0, color=INK2, lw=0.7)
ax.text(0.03, 0.96, f"slope {m.params['x']:+.2f}  (se {m.bse['x']:.2f}, p = {m.pvalues['x']:.2f})\nn = {len(dd)} months", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
ax.set_xlabel("monthly change in issuers' T-bills, \\$B", labelpad=2); ax.set_ylabel("monthly change in official ST holdings, \\$B", labelpad=2); ax.grid(axis="x")
panel(ax, "d", "Official holdings vs issuer demand", "raw monthly changes, 2023–2026")

# ---------------- e 情景
ax = fig.add_subplot(gs[2, 0])
bills = float(P["bills_usd"].dropna().iloc[-1]) / 1e9
net12 = (P["bills_usd"].dropna().iloc[-1] - P["bills_usd"].dropna().loc[:"2025-10-13"].iloc[-1]) / 1e9
items = [("Issuers' T-bills today", float(P["SDT_bills_usd"].dropna().iloc[-1]) / 1e9, ENT["SDT"], "today"),
         ("Foreign official (ST)", float(o["off_st"].iloc[-1]) / 1e9, ENT["OFFICIAL"], "ref"),
         ("Fed T-bill holdings", float(P["WSHOBL"].dropna().iloc[-1]) / 1e3, GRAY, "ref"),
         ("Net issuance, last 12m", net12, GRAY, "ref"),
         ("Scenario: $1T market", 800, ENT["SDT"], "scn"),
         ("All foreign (ST)", float(o["all_st"].iloc[-1]) / 1e9, GRAY, "ref"),
         ("Scenario: $2T market", 1600, ENT["SDT"], "scn")]
items = sorted(items, key=lambda t: t[1])
for i, (lab, v, col, kind) in enumerate(items):
    ax.barh(i, v, color=col if kind != "scn" else SURF, edgecolor=col, hatch="////" if kind == "scn" else None, lw=1.0 if kind == "scn" else 0, height=0.66)
    ax.text(v + 25, i, f"{v:,.0f}  ({v / bills * 100:.0f}% of bills)", va="center", fontsize=6.2, color=INK2 if kind != "today" else ENT["SDT"], fontweight="bold" if kind == "today" else "normal")
ax.set_yticks(range(len(items))); ax.set_yticklabels([t[0].replace("$", "\\$") for t in items], fontsize=6.3)
ax.set_xlim(0, 2500); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_xlabel("\\$ billion", labelpad=2)
panel(ax, "e", "How big could shadow demand get?", "stablecoin bill demand under market-size scenarios vs reference stocks")

# ---------------- f 吸收份额
ax = fig.add_subplot(gs[2, 1])
mo = P.resample("ME").last()
r12 = (mo["SDT_bills_usd"].diff(12) / mo["bills_usd"].diff(12) * 100).loc["2024-01-31":].dropna()
net12s = (mo["bills_usd"].diff(12) / 1e9).loc[r12.index]
ax.bar(r12.index, net12s, width=22, color=LGRAY, linewidth=0, label="12-month net bill issuance, \\$B")
ax.set_ylim(0, net12s.max() * 1.22); ax.set_ylabel("\\$ billion", labelpad=2)
for d_, v in r12.iloc[::6].items():
    ax.text(d_, net12s.loc[d_] + 25, f"{v:.0f}%", ha="center", fontsize=6.2, color=ENT["SDT"], fontweight="bold")
ax.text(r12.index[-1], net12s.iloc[-1] + 25, f"{r12.iloc[-1]:.0f}%", ha="center", fontsize=6.2, color=ENT["SDT"], fontweight="bold")
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
ax.text(0.98, 0.97, "orange labels = share of that net issuance\nabsorbed by issuers' direct T-bills", transform=ax.transAxes, fontsize=6.4, color=ENT["SDT"], va="top", ha="right")
panel(ax, "f", "Issuer absorption of net issuance is erratic, ~0 today", "12-month net bill issuance (bars) and issuers' absorbed share (labels)")

fig.text(0.12, 0.028, f"Panel e: bills outstanding \\${bills / 1000:.2f}T; scenarios assume 80% of reserves in bills (Tether 2026Q2: 82%) and are illustrative, not forecasts.\nSources: U.S. Treasury TIC SLT Table 3 (official/non-official aggregates, country short-term holdings), MSPD, Fed H.4.1 (WSHOBL), issuer attestations, DefiLlama. Regressions: monthly changes, Feb-2023 to Jul-2026 (n = 41);\n"
         "controls: change in bills outstanding, EFFR, VIX; IV: BTC returns at t and t−1. Country classification (official-heavy vs financial centre) is the author's judgement, fixed before estimation.",
         fontsize=6.0, color=MUTED, va="top")
save(fig, "Fig6_foreign_holders_scenarios")
