"""
tax_alpha_chart.py
------------------
Two-panel summary of the central finding.

  Left  : net after-tax value-add of harvesting by portfolio, split into tax saved
          vs replacement-ETF tracking. Tax saved is positive everywhere; the
          tracking term decides whether the net is positive or negative.
  Right : mean composite rank by rebalancing strategy (lower is better). Wide-band
          and low-frequency rebalancing win; monthly rebalancing ranks worst.

Output: tax_alpha_chart.png

Run after run_backtest.py + build_playbook.py:  python Backtest/outputs/tax_alpha_chart.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
BACKTEST = HERE.parent
CSV = BACKTEST / "comparative_analysis_results.csv"
PLAYBOOK = BACKTEST / "strategy_playbook.xlsx"
OUT = HERE / "tax_alpha_chart.png"

NAVY, GREEN, RED, GREY = "#1F3864", "#1E6B36", "#B0301F", "#9aa6b6"

df = pd.read_csv(CSV)
on = df[df["TLH Status"] == "On (10%)"].copy()
off = df[df["TLH Status"] == "Off"].copy()
keys = ["Portfolio", "Market Condition", "Rebal Type", "Rebal Value"]
m = on.merge(off[keys + ["Final NAV", "Tax Paid", "Execution Costs"]], on=keys, suffixes=("", "_off"))
m["net"] = m["Final NAV"] - m["Final NAV_off"]
m["tax"] = m["Tax Paid_off"] - m["Tax Paid"]
m["cost"] = m["Execution Costs_off"] - m["Execution Costs"]
m["track"] = m["net"] - m["tax"] - m["cost"]
port = m.groupby("Portfolio")[["tax", "track", "net"]].mean().sort_values("net", ascending=False)

pb = pd.read_excel(PLAYBOOK, sheet_name="Playbook")
pb["s"] = pb["Strategy Label"].str.replace(r" \| TLH=10%", "", regex=True)
strat = pb.groupby("s")["Rank"].mean().sort_values(ascending=False)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.8))
fig.patch.set_facecolor("white")
fig.subplots_adjust(wspace=0.34, left=0.17, right=0.96, top=0.82, bottom=0.16)

# ── Left: decomposition (tax saved vs tracking vs net) by portfolio ────────────
y = np.arange(len(port))
h = 0.26
axL.barh(y + h, port["tax"], height=h, color=GREEN, label="Tax saved", zorder=3)
axL.barh(y, port["track"], height=h, color=NAVY, label="Replacement tracking", zorder=3)
axL.barh(y - h, port["net"], height=h, color=GREY, label="Net value-add", zorder=3)
axL.set_yticks(y)
axL.set_yticklabels(port.index, fontsize=9)
axL.invert_yaxis()
axL.axvline(0, color="#888", lw=0.8)
axL.set_title("Net value-add of harvesting, decomposed", fontsize=12, fontweight="bold", color=NAVY)
axL.set_xlabel("Mean per $1M (USD)", fontsize=9)
axL.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
axL.tick_params(axis="x", labelsize=8)
for sp in ("top", "right"):
    axL.spines[sp].set_visible(False)
axL.grid(axis="x", color="#eee", lw=0.7, zorder=0)
axL.legend(fontsize=8, frameon=False, loc="lower right")
for yi, v in zip(y, port["net"]):
    axL.text(v + (2500 if v >= 0 else -2500), yi - h, f"${v:,.0f}",
             va="center", ha="left" if v >= 0 else "right", fontsize=7.5,
             color=GREEN if v >= 0 else RED, fontweight="bold")

# ── Right: composite rank by strategy ─────────────────────────────────────────
yy = np.arange(len(strat))
colors = [GREEN if r <= strat.median() else NAVY for r in strat]
axR.barh(yy, strat.values, color=colors, zorder=3)
axR.set_yticks(yy)
axR.set_yticklabels(strat.index, fontsize=9)
axR.set_title("Strategy ranking (lower is better)", fontsize=12, fontweight="bold", color=NAVY)
axR.set_xlabel("Mean composite rank across portfolios x regimes", fontsize=9)
axR.tick_params(axis="x", labelsize=8)
for sp in ("top", "right"):
    axR.spines[sp].set_visible(False)
axR.grid(axis="x", color="#eee", lw=0.7, zorder=0)
for yi, v in zip(yy, strat.values):
    axR.text(v + 0.06, yi, f"{v:.2f}", va="center", fontsize=7.5, color="#444")

fig.suptitle("Harvesting Saves Tax, but Replacement-ETF Tracking Decides the Net",
             fontsize=14, fontweight="bold", color="#1a1a1a", y=0.95)
fig.text(0.5, 0.04,
         "192 matched TLH vs no-TLH comparisons  |  $1M capital  |  35% ST / 20% LT  |  price basis",
         ha="center", fontsize=8, color="#888", style="italic")

plt.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
print(f"Saved -> {OUT}")
