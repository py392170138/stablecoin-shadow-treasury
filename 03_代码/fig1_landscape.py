"""图 1：影子国债需求的格局——稳定币体量、储备构成、在国库券市场中的位置。"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from fig_common import *  # noqa: F401,F403
from viz_style import *  # noqa: F401,F403

fig = plt.figure(figsize=(7.4, 8.6))
gs = fig.add_gridspec(3, 2, hspace=0.72, wspace=0.40, left=0.07, right=0.90, top=0.945, bottom=0.07)
yr = mdates.YearLocator(); yf = mdates.DateFormatter("%y")

# ---------------- a 稳定币供给
ax = fig.add_subplot(gs[0, 0])
w = SC.resample("W-FRI").last().loc["2018-01-01":]
stk = [bn(w["USDT"].fillna(0)), bn(w["USDC"].fillna(0)), bn(w["OTHER"].fillna(0))]
ax.stackplot(w.index, *stk, colors=[ENT["USDT"], ENT["USDC"], LGRAY], linewidth=0.6, edgecolor=SURF)
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
ax.text(SIGNED, 322, " GENIUS Act\n signed", fontsize=6.4, color=INK2, va="top", ha="right")
last = w.index[-1]
tot = 0
for lab, ser, col in [("USDT", stk[0], ENT["USDT"]), ("USDC", stk[1], ENT["USDC"]), ("Other", stk[2], GRAY)]:
    endlabel(ax, last, tot + ser.iloc[-1] / 2, f"{lab} {ser.iloc[-1]:.0f}", col if lab != "Other" else INK2)
    tot += ser.iloc[-1]
ax.set_xlim(w.index[0], last); ax.set_ylim(0, 335)
ax.xaxis.set_major_locator(yr); ax.xaxis.set_major_formatter(yf)
panel(ax, "a", "Dollar stablecoin supply", "$ billion, top-25 USD-pegged tokens, weekly")

# ---------------- b Tether 储备构成
ax = fig.add_subplot(gs[0, 1])
t = TT.copy().set_index("report_date")
sup = SC["USDT"].reindex(t.index, method="nearest")
t["repo"] = t[["on_rrp", "term_rrp", "reverse_repo_other"]].fillna(0).sum(axis=1)
sh = pd.DataFrame({
    "T-bills": t["us_tbills"].fillna(0) / sup, "Reverse repo": t["repo"] / sup,
    "CP & CDs": t["commercial_paper"].fillna(0) / sup, "MMF & cash": (t["money_market_funds"].fillna(0) + t["cash_bank"].fillna(0)) / sup}) * 100
sh = sh[t.index >= "2021-06-30"]
sh["Other"] = (100 - sh.sum(axis=1)).clip(lower=0)
colors = [BLUE_SEQ[4], BLUE_SEQ[2], C["yellow"], C["aqua"], LGRAY]
x = np.arange(len(sh)); bottom = np.zeros(len(sh))
for (col, ser), c in zip(sh.items(), colors):
    ax.bar(x, ser.values, bottom=bottom, color=c, width=0.82, linewidth=0.6, edgecolor=SURF, label=col)
    bottom += ser.values
ax.set_xticks(x[::2]); ax.set_xticklabels([d.strftime("%y-%m") for d in sh.index[::2]], rotation=60, ha="right", fontsize=6.2)
ax.set_ylim(0, 100); ax.set_xlim(-0.6, len(sh) - 0.4)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=5, fontsize=6.0, handlelength=0.9, columnspacing=0.8, handletextpad=0.4)
ax.text(len(sh) - 1, 100.6, f"{sh['T-bills'].iloc[-1]:.0f}%", fontsize=6.6, color=BLUE_SEQ[4], ha="center", va="bottom", fontweight="bold")
ax.text(0, 100.6, f"{sh['T-bills'].iloc[0]:.0f}%", fontsize=6.6, color=BLUE_SEQ[4], ha="center", va="bottom", fontweight="bold")
panel(ax, "b", "Tether reserves: from commercial paper to T-bills", "% of USDT in circulation, quarterly BDO attestations")

# ---------------- c Circle 储备
ax = fig.add_subplot(gs[1, 0])
c = CC.set_index("report_date")
c = c[c.index >= "2023-01-01"].copy()
c["repo"] = c["repo"].fillna(0)
c["cash"] = c["cash_fund"].fillna(0) + c["cash_banks"].fillna(0)
parts = [("Treasuries", bn(c["treasuries"].fillna(0)), BLUE_SEQ[4]), ("Repo", bn(c["repo"]), BLUE_SEQ[2]), ("Cash", bn(c["cash"]), C["aqua"])]
ax.stackplot(c.index, *[p[1] for p in parts], colors=[p[2] for p in parts], linewidth=0.6, edgecolor=SURF, step="post")
ax.legend([plt.Rectangle((0,0),1,1,color=p[2]) for p in parts], [p[0] for p in parts], loc="upper left", ncol=3, fontsize=6.4, handlelength=0.9, columnspacing=1.0)
ax.text(c.index[-1] - pd.Timedelta(days=14), c["treasuries"].fillna(0).iloc[-1]/1e9/2, f"{c['treasuries'].fillna(0).iloc[-1]/1e9:.0f}", color="white", fontsize=6.6, fontweight="bold", ha="right", va="center")
ax.text(c.index[-1] - pd.Timedelta(days=14), (c["treasuries"].fillna(0).iloc[-1]+c["repo"].iloc[-1]/2)/1e9, f"{c['repo'].iloc[-1]/1e9:.0f}", color=INK, fontsize=6.6, fontweight="bold", ha="right", va="center")
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
ax.set_xlim(c.index[0], c.index[-1]); ax.set_ylim(0, 100)
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%y"))
panel(ax, "c", "Circle (USDC): repo has displaced T-bills", "$ billion at report dates, Circle Reserve Fund & bank cash")

# ---------------- d 国库券持有人排名
ax = fig.add_subplot(gs[1, 1])
tic = TIC[~TIC.country.str.contains("Total|Of Which|Memo|All Countries|Grand|International")]
st = tic[tic.date == tic.date.max()].set_index("country")["st_hold"].sort_values(ascending=False) / 1e9
rank = st.head(10).copy()
rank["Tether (USDT)"] = float(TT.set_index("report_date")["us_tbills"].iloc[-1]) / 1e9
rank["Circle (USDC)"] = float(CC.set_index("report_date")["treasuries"].iloc[-1]) / 1e9
rank = rank.sort_values()
cols = [ENT["SDT"] if "(" in k else (LGRAY if k not in ("Japan", "China, Mainland") else "#bdbcb6") for k in rank.index]
ax.barh(range(len(rank)), rank.values, color=cols, height=0.68, linewidth=0)
ax.set_yticks(range(len(rank))); ax.set_yticklabels([k.replace("China, Mainland", "China").replace("Cayman Islands", "Cayman Is.").replace("United Arab Emirates", "UAE").replace("United Kingdom", "UK") for k in rank.index], fontsize=6.9)
for i, (k, v) in enumerate(rank.items()):
    ax.text(v + 3, i, f"{v:.0f}", va="center", fontsize=6.8, color=ENT["SDT"] if "(" in k else INK2, fontweight="bold" if "(" in k else "normal")
for lab in ax.get_yticklabels():
    if "(" in lab.get_text():
        lab.set_color(ENT["SDT"]); lab.set_fontweight("bold")
ax.set_xlim(0, rank.max() * 1.15); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
ax.set_ylim(-0.6, len(rank) - 0.4)
panel(ax, "d", "Tether alone ranks #2 among foreign bill holders", "short-term U.S. Treasuries, $ billion; TIC Jul-2026, issuers at latest attestation")

# ---------------- e SDT 占比
ax = fig.add_subplot(gs[2, 0])
d = P.loc["2021-07-01":]
ax.plot(d.index, d["SDT_tether_pct"], color=ENT["USDT"], lw=1.4)
ax.plot(d.index, d["SDT_broad_pct"], color=ENT["SDT"], lw=1.0, ls=(0, (2.5, 1.5)))
ax.plot(d.index, d["SDT_pct"], color=ENT["SDT"], lw=1.9)
ax.axvline(SIGNED, color=INK, lw=0.8, ls=(0, (3, 2)))
l1, l2, l3 = d["SDT_pct"].dropna().iloc[-1], d["SDT_tether_pct"].dropna().iloc[-1], d["SDT_broad_pct"].dropna().iloc[-1]
xr = d.index[-1] + pd.Timedelta(days=20)
ax.set_xlim(d.index[0], d.index[-1] + pd.Timedelta(days=330)); ax.set_ylim(0, 3.7)
ax.text(xr, l3 + 0.02, f"incl. repo {l3:.1f}%", color=ENT["SDT"], fontsize=6.3, va="bottom")
ax.text(xr, l1 - 0.02, f"T-bills {l1:.1f}%", color=ENT["SDT"], fontsize=6.5, fontweight="bold", va="top")
ax.text(xr, l2 - 0.30, f"Tether only {l2:.1f}%", color=ENT["USDT"], fontsize=6.3, va="top")
ax.annotate("Circle shifts\nT-bills to repo", xy=(pd.Timestamp("2023-05-20"), 1.55), xytext=(pd.Timestamp("2023-08-20"), 3.15), fontsize=6.0, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6), ha="left")
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
b = P["bills_usd"].dropna(); s_ = P["SDT_bills_usd"].dropna()
ds, db = s_.iloc[-1] - s_.loc[:"2025-10-13"].iloc[-1], b.iloc[-1] - b.loc[:"2025-10-13"].iloc[-1]
ax.text(0.40, 0.22, f"Past 12 months: issuers' direct T-bills {'+' if ds >= 0 else '\u2212'}${abs(bn(ds)):.0f}B\nvs net bill issuance +${bn(db):.0f}B", transform=ax.transAxes, fontsize=6.5, color=INK2, va="top")
panel(ax, "e", "Shadow demand is still small", "issuers' direct T-bills / T-bills outstanding (SDT)")

# ---------------- f 国库券持有结构
ax = fig.add_subplot(gs[2, 1])
o = OWN.copy().sort_index()
o = o[o.index >= "2023-01-31"]
shares = pd.DataFrame({
    "Foreign official": o["off_st"] / o["bills_usd"], "Foreign private": o["priv_st"] / o["bills_usd"],
    "Stablecoin issuers": o["SDT_bills_usd"] / o["bills_usd"]}) * 100
shares["Domestic & other"] = 100 - shares.sum(axis=1)
cols = [ENT["OFFICIAL"], ENT["PRIVATE"], ENT["SDT"], LGRAY]
ax.stackplot(shares.index, *[shares[c_] for c_ in shares.columns], colors=cols, linewidth=0.6, edgecolor=SURF)
cum = 0
for (name, ser), col in zip(shares.items(), cols):
    if name == "Domestic & other":
        pass
    else:
        endlabel(ax, shares.index[-1], cum + ser.iloc[-1] / 2, f"{name.replace('Stablecoin issuers', 'Stablecoins')} {ser.iloc[-1]:.1f}%", col, fs=6.4)
    cum += ser.iloc[-1]
ax.set_xlim(shares.index[0], shares.index[-1]); ax.set_ylim(0, 40)
ax.text(0.02, 0.96, f"Domestic & other holds the remaining {shares['Domestic & other'].iloc[-1]:.0f}%", transform=ax.transAxes, fontsize=6.6, color=INK2, va="top")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
panel(ax, "f", "Who owns the bill market", "% of T-bills outstanding, month-end (TIC, issuer reports, MSPD)")

fig.text(0.07, 0.025, "Sources: DefiLlama; Circle and Tether attestation reports; U.S. Treasury TIC (SLT Table 3) and Fiscal Data (MSPD, DTS); author calculations.\n"
         "Dashed line: GENIUS Act signed (2025-07-18). SDT counts direct T-bill holdings only; reverse repo is shown separately. Other fiat-backed tokens are excluded (lower bound).",
         fontsize=6.1, color=MUTED, va="top")
save(fig, "Fig1_shadow_demand_landscape")
