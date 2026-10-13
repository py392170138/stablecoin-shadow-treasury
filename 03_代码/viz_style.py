"""共享绘图风格：配色（已用 validate_palette.js 验证）、字体、面板标签与保存。

颜色按"实体"固定，不随排名变化：
  USDT 蓝、USDC 青绿、稳定币合计/SDT（焦点实体）橙、外国官方 紫、外国私人 品红、其他/国内 灰。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "06_结果" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

C = dict(blue="#2a78d6", orange="#eb6834", aqua="#1baf7a", yellow="#eda100", magenta="#e87ba4",
         green="#008300", violet="#4a3aa7", red="#e34948")
BLUE_SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, INK2, MUTED, GRID, SURF, MID = "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1", "#fcfcfb", "#f0efec"
GRAY, LGRAY = "#a8a7a2", "#d9d8d3"
ENT = dict(USDT=C["blue"], USDC=C["aqua"], SDT=C["orange"], OFFICIAL=C["violet"], PRIVATE=C["magenta"], OTHER=GRAY, DOMESTIC=LGRAY)

for fam in ["Helvetica Neue", "Helvetica", "Arial"]:
    if any(fam in f.name for f in font_manager.fontManager.ttflist):
        FAMILY = fam
        break
else:
    FAMILY = "DejaVu Sans"

mpl.rcParams.update({
    "font.family": FAMILY, "font.size": 7.6, "axes.titlesize": 8.6, "axes.labelsize": 7.6,
    "xtick.labelsize": 7.0, "ytick.labelsize": 7.0, "legend.fontsize": 7.0,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": LGRAY, "axes.linewidth": 0.7, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "xtick.major.size": 2.5, "ytick.major.size": 0, "xtick.major.width": 0.6,
    "lines.linewidth": 1.5, "lines.solid_capstyle": "round", "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})


def panel(ax, letter: str, title: str, sub: str = "") -> None:
    """面板标签：粗体字母 + 标题（主）+ 灰色副标题（单位/口径）。"""
    ax.text(0, 1.115, letter, transform=ax.transAxes, fontsize=10.5, fontweight="bold", color=INK, va="bottom", ha="left")
    ax.text(0.075 if len(letter) == 1 else 0.09, 1.115, title, transform=ax.transAxes, fontsize=8.4, fontweight="bold", color=INK, va="bottom", ha="left")
    if sub:
        ax.text(0.075 if len(letter) == 1 else 0.09, 1.035, sub, transform=ax.transAxes, fontsize=6.7, color=MUTED, va="bottom", ha="left")


def endlabel(ax, x, y, text, color, dx=0.0, dy=0.0, ha="left", fs=7.0, weight="bold"):
    ax.annotate(text, (x, y), xytext=(4 + dx, dy), textcoords="offset points", color=color, fontsize=fs, fontweight=weight, va="center", ha=ha,
                annotation_clip=False)


def zero_line(ax, y=0.0, **kw):
    ax.axhline(y, color=INK2, lw=0.7, **kw)


def save(fig, name: str) -> None:
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300 if ext == "png" else None, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("saved", name)


def source_note(fig, text: str, y: float = -0.005):
    fig.text(0.012, y, text, fontsize=6.2, color=MUTED, ha="left", va="top", wrap=True)
