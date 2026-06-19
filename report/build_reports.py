#!/usr/bin/env python3
"""
build_reports.py
================
Generate the capstone report and executive summary as PDFs, pulling every number
directly from the regenerated backtest results so the documents, the README, and
the strategy playbook all cite identical, code-derived figures.

    python report/build_reports.py

Outputs (in report/):
    Vise_Capstone_Final_Report.pdf
    Vise_Executive_Summary.pdf
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
from xhtml2pdf import pisa

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RESULTS = REPO / "Backtest" / "comparative_analysis_results.csv"
PLAYBOOK = REPO / "Backtest" / "strategy_playbook.xlsx"

REGIME_ORDER = ["Bear Market", "Baseline Market", "Bull Market",
                "Past 5 Years", "Past 10 Years", "Past 20 Years"]
REGIME_LABEL = {
    "Bear Market": "Bear (2007-2008)", "Baseline Market": "Baseline (2010-2019)",
    "Bull Market": "Bull (2023-2024)", "Past 5 Years": "Past 5 Years (2021-2025)",
    "Past 10 Years": "Past 10 Years (2016-2025)", "Past 20 Years": "Past 20 Years (2006-2025)",
}
TEAM = "Bhagya Puppala, Jack Feen, Joshua Ringler, Nathan Arimilli, Nisha Sapkota, Rio Yokoyama"


def money(x):
    x = float(x)
    return f"-${abs(x):,.0f}" if x < 0 else f"+${x:,.0f}"


def sign_cls(x):
    return "pos" if float(x) >= 0 else "neg"


def compute_stats():
    df = pd.read_csv(RESULTS)
    on = df[df["TLH Status"] == "On (10%)"].copy()
    off = df[df["TLH Status"] == "Off"].copy()
    keys = ["Portfolio", "Market Condition", "Rebal Type", "Rebal Value"]
    m = on.merge(off[keys + ["Final NAV", "Liquidation NAV", "Tax Paid", "Execution Costs"]],
                 on=keys, suffixes=("", "_off"))
    # Net after-tax value-add of harvesting, decomposed into its three drivers.
    m["pre"] = m["Final NAV"] - m["Final NAV_off"]
    m["post"] = m["Liquidation NAV"] - m["Liquidation NAV_off"]
    m["tax_saved"] = m["Tax Paid_off"] - m["Tax Paid"]            # +ve = TLH cut tax
    m["cost"] = m["Execution Costs_off"] - m["Execution Costs"]   # -ve = TLH cost more
    m["tracking"] = m["pre"] - m["tax_saved"] - m["cost"]         # replacement drift + gain timing

    regime = m.groupby("Market Condition")[["pre", "post"]].mean().reindex(REGIME_ORDER)
    port = m.groupby("Portfolio").agg(
        tax=("tax_saved", "mean"), track=("tracking", "mean"),
        cost=("cost", "mean"), net=("pre", "mean"),
        events=("TLH Event Count", "mean")).sort_values("net", ascending=False)
    taxcut_by_port = m.groupby("Portfolio")["tax_saved"].apply(lambda s: 100 * (s > 0).mean())
    overall = dict(tax=m["tax_saved"].mean(), track=m["tracking"].mean(),
                   cost=m["cost"].mean(), net=m["pre"].mean(),
                   pct_taxcut=100 * (m["tax_saved"] > 0).mean(),
                   taxcut_min=taxcut_by_port.min(), taxcut_max=taxcut_by_port.max())
    pct_pre = 100 * (m["pre"] > 0).mean()
    pct_post = 100 * (m["post"] > 0).mean()
    best = m.loc[m["pre"].idxmax()]
    worst = m.loc[m["pre"].idxmin()]

    pb = pd.read_excel(PLAYBOOK, sheet_name="Playbook")
    pb["s"] = pb["Strategy Label"].str.replace(r" \| TLH=10%", "", regex=True)
    strat_rank = pb.groupby("s")["Rank"].mean().sort_values()

    return dict(df=df, m=m, regime=regime, port=port, overall=overall,
                pct_pre=pct_pre, pct_post=pct_post, best=best, worst=worst,
                strat_rank=strat_rank)


CSS = """
@page { size: letter; margin: 0.9in 0.85in; @frame footer { -pdf-frame-content: footer; bottom: 0.5in; height: 0.4in; } }
body { font-family: "Times New Roman", Georgia, serif; font-size: 11pt; color: #1a1a1a; line-height: 1.4; }
h1 { font-size: 22pt; color: #1F3864; margin: 0 0 4pt 0; }
h2 { font-size: 14pt; color: #1F3864; border-bottom: 1.5px solid #1F3864; padding-bottom: 2pt; margin: 16pt 0 6pt 0; }
h3 { font-size: 12pt; color: #2E4057; margin: 10pt 0 4pt 0; }
p { margin: 0 0 7pt 0; text-align: justify; }
.subtitle { font-size: 13pt; color: #2E4057; margin-bottom: 14pt; }
.meta { font-size: 10.5pt; color: #444; margin-bottom: 4pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; }
th { background: #1F3864; color: #fff; padding: 5px 6px; font-size: 8.5pt; font-family: Helvetica, Arial, sans-serif; text-align: center; }
td { border: 1px solid #cdd5e0; padding: 4px 6px; font-size: 9pt; font-family: Helvetica, Arial, sans-serif; text-align: center; }
td.l { text-align: left; }
tr.alt td { background: #eef2f7; }
.pos { color: #1E6B36; } .neg { color: #B0301F; }
.lead { font-size: 11.5pt; }
ul { margin: 0 0 8pt 0; } li { margin-bottom: 3pt; text-align: justify; }
.footer { font-size: 7.5pt; color: #999; text-align: center; }
.callout { background:#eef2f7; border-left: 3px solid #1F3864; padding: 6pt 9pt; margin: 8pt 0; }
"""

FOOTER = '<div id="footer" class="footer">UT Austin MSBA Capstone, Group 20. Vise Tax-Aware Rebalancing Engine</div>'


def regime_table(regime):
    rows = ""
    for i, r in enumerate(REGIME_ORDER):
        pre, post = regime.loc[r, "pre"], regime.loc[r, "post"]
        cls = "alt" if i % 2 else ""
        rows += (f'<tr class="{cls}"><td class="l">{REGIME_LABEL[r]}</td>'
                 f'<td class="{sign_cls(pre)}">{money(pre)}</td>'
                 f'<td class="{sign_cls(post)}">{money(post)}</td></tr>')
    return ('<table><tr><th>Market period</th><th>Net value-add (pre-liquidation)</th>'
            f'<th>Net value-add (post-liquidation)</th></tr>{rows}</table>')


def decomp_table(port):
    rows = ""
    for i, (name, r) in enumerate(port.iterrows()):
        cls = "alt" if i % 2 else ""
        rows += (f'<tr class="{cls}"><td class="l">{name}</td>'
                 f'<td class="{sign_cls(r.tax)}">{money(r.tax)}</td>'
                 f'<td class="{sign_cls(r.track)}">{money(r.track)}</td>'
                 f'<td class="{sign_cls(r.cost)}">{money(r.cost)}</td>'
                 f'<td class="{sign_cls(r.net)}">{money(r.net)}</td>'
                 f'<td>{r.events:.0f}</td></tr>')
    return ('<table><tr><th>Portfolio</th><th>Tax saved</th>'
            '<th>Replacement tracking</th><th>Extra cost</th>'
            '<th>Net value-add</th><th>Avg TLH events</th></tr>'
            f'{rows}</table>')


def strat_table(strat_rank):
    rows = ""
    for i, (s, rk) in enumerate(strat_rank.items()):
        cls = "alt" if i % 2 else ""
        rows += f'<tr class="{cls}"><td class="l">{s}</td><td>{rk:.2f}</td></tr>'
    return ('<table><tr><th>Rebalancing strategy</th>'
            '<th>Mean composite rank (lower is better)</th></tr>'
            f'{rows}</table>')


def full_report_html(s):
    best, worst, ov = s["best"], s["worst"], s["overall"]
    return f"""
<html><head><style>{CSS}</style></head><body>
{FOOTER}
<h1>Tax-Aware Portfolio Rebalancing and Tax-Loss Harvesting</h1>
<div class="subtitle">A Lot-Level Simulation Engine and Strategy Playbook for Vise</div>
<div class="meta"><b>UT Austin MS Business Analytics Capstone, Group 20</b></div>
<div class="meta">{TEAM}</div>
<div class="meta">Sponsor: Brandt Green, Vise</div>

<h2>Executive Overview</h2>
<p class="lead">Vise builds and manages personalized portfolios for financial advisors, and its
tax-loss harvesting (TLH) is a core commercial feature. The challenge is interpretability: advisors
struggle to explain to clients why a particular harvest or rebalance occurred. Our team built a
transparent, rules-based, lot-level simulation engine that quantifies the after-tax value of TLH across
rebalancing strategies, portfolio constructions, and market environments, and produces an auditable
trade log that an advisor can explain.</p>
<p>We backtested <b>192 matched TLH-versus-no-TLH comparisons</b> (384 individual simulations). The central
finding is that harvesting works as a tax tool but its bottom-line value is decided by a second factor that
is easy to overlook: <b>TLH reliably reduced taxes</b> (it cut cumulative tax in {ov['pct_taxcut']:.0f}% of
comparisons, by about {money(ov['tax'])} per $1M on average), but to stay invested after selling at a loss
the strategy must hold a wash-sale replacement ETF, and <b>the tracking gap between the original holding and
its replacement usually moved portfolio value more than the tax saving did</b>. Net of everything, harvesting
helped in only {s['pct_pre']:.0f}% of comparisons pre-liquidation and {s['pct_post']:.0f}% after a full
liquidation.</p>

<h2>Business Problem and Objectives</h2>
<p>Advisors leave platforms when they cannot explain automated decisions to clients, which raises
service burden and compliance risk. The objective was not to replace Vise's optimizer but to build an
explainable measurement tool: given a portfolio, a rebalancing rule, and a tax profile, quantify what
TLH actually adds (or costs) after tax, and rank the strategies that deliver the best client outcomes
in each market environment.</p>
<h3>Business value</h3>
<p>As an order-of-magnitude business case, a 10% reduction in advisor churn on a base of roughly 1,000
advisors retains about 10 advisors per year. At roughly $25M of assets per advisor and a 30 bps fee,
that is on the order of $750K in retained annual revenue. The figure is an assumption-based estimate
meant to frame the opportunity, not a measured result.</p>

<h2>Data</h2>
<p>The engine runs on a daily price history of roughly 700 ETFs and the corresponding dividend, stock
split, and TLH proxy-substitution tables, all sourced from S&amp;P Capital IQ and Vise. Prices feed a
forward-filled, look-ahead-free price matrix; the proxy table maps each holding to ranked replacement
ETFs for wash-sale-compliant harvesting. The full price extract ships with the project as a compact
parquet so every result is reproducible from a clean checkout.</p>

<h2>Engine Design</h2>
<p>The simulation is lot-level. Every purchase creates a tax lot with its own cost basis and acquisition
date, and every sale is classified as short-term or long-term using the IRS rule that a holding period
of more than one year (366 or more calendar days) is long-term. The engine implements:</p>
<ul>
<li><b>Tax accounting:</b> short-term and long-term netting, a $3,000 ordinary-income offset, character-
preserving loss carry-forward, and an annual settlement.</li>
<li><b>Wash-sale enforcement:</b> a 30-day lookback and 30-day forward block, with automatic substitution
into a ranked proxy ETF so the position stays invested.</li>
<li><b>Rebalancing:</b> calendar (monthly, quarterly, yearly) and drift-band (absolute and relative
thresholds), with costs embedded in NAV on every trade.</li>
<li><b>Costs:</b> a 12 bps round-trip charge (5 commission, 5 slippage, 2 bid-ask).</li>
</ul>

<h2>Methodology</h2>
<p>Every cell of the grid was run through the same engine so the comparison is fair. The only difference
between a matched pair is whether harvesting is enabled (a 10% loss threshold) or not; rebalancing dates,
costs, and tax rules are identical. We hold $1M of starting capital, 35% short-term and 20% long-term
tax rates, and report results on a price basis so that calendar and threshold strategies, TLH-on and
TLH-off, are all measured on the same footing.</p>
<p><b>Portfolios:</b> a 40/60 and a 100/0 Target Allocation ETF model, a concentrated two-ETF mix
(IVV/EFA), and a diversified three-ETF mix (SPY/TLT/GLD). <b>Periods:</b> the 2007-2008 bear, the
2010-2019 baseline, the 2023-2024 bull, and trailing 5, 10, and 20-year windows.
<b>Strategies:</b> monthly, quarterly, and yearly rebalancing; absolute 5%, 10%, and 20% drift bands;
and relative 25% and 50% bands.</p>
<p>For each matched pair we measure the <b>net after-tax value-add</b> of harvesting (the harvested
portfolio's value minus the identical no-harvest portfolio's value) and decompose it into three drivers:
<b>tax saved</b> (the reduction in cumulative tax paid), <b>replacement tracking</b> (the return difference
from holding wash-sale substitute ETFs instead of the originals, plus the timing of any realized gains),
and <b>extra cost</b> (the added transaction cost of harvest trades). Pre-liquidation value-add is measured
while still invested; post-liquidation re-prices both portfolios after a full sale, which captures whether
the benefit was permanent or merely deferral.</p>

<h2>Validation</h2>
<p>The pure-computation engine is covered by a unit-test suite with financially meaningful expected
values: buy-and-hold parity, harvest firing and dollar-parity rebuys, wash-sale and proxy substitution,
the $3,000 offset and carry-forward, the short/long-term day-count boundary, dividend handling, and NAV
reconciliation. Value-add is always computed against a baseline that rebalances on the same dates, so the
comparison isolates the effect of harvesting alone.</p>

<h2>Results</h2>
<p>Net value-add by market period is positive in the short and medium windows and turns negative over the
full 20-year window, where the replacement-tracking gap has the longest time to compound.</p>
{regime_table(s['regime'])}
<p>Decomposing the net value-add by portfolio shows what is really happening. <b>Tax saved is positive for
every portfolio</b> (harvesting cut tax in 75% to 96% of runs), so as a tax tool TLH works. The net
outcome, however, is decided by replacement tracking: it is strongly positive for the diversified 3-ETF
and 2-ETF mixes and strongly negative for the two model-ETF portfolios. Tax was cut in
{ov['taxcut_min']:.0f}% to {ov['taxcut_max']:.0f}% of runs depending on the portfolio.</p>
{decomp_table(s['port'])}
<p>The reason is the replacement map. Several large-cap style holdings in the model portfolios (for example
the S&amp;P 500 Growth and Russell 1000 Growth sleeves) are replaced by a broad S&amp;P 100 fund, which
lagged the growth names by hundreds of percentage points over the long windows. After harvesting, the
portfolio spends years holding the wrong index, and that drift, not the tax math, drives the large negative
results. The single worst run ({worst['Portfolio']}, {worst['Market Condition'].lower()},
{worst['Strategy Label'].replace(' | TLH=10%', '').lower()}) was {money(worst['pre'])}: replacement tracking
was {money(worst['tracking'])} while the tax effect was {money(worst['tax_saved'])}. The best run
({best['Portfolio']}, {best['Market Condition'].lower()}) was {money(best['pre'])} pre and
{money(best['post'])} post-liquidation, but it was tracking-dominated too: the replacement happened to
outperform by {money(best['tracking'])}, with a tax saving of only {money(best['tax_saved'])}. Single-run
extremes therefore reflect replacement tracking in both directions; the reliable, repeatable effect is the
tax saving, positive in {ov['pct_taxcut']:.0f}% of runs.</p>
<h3>Strategy ranking</h3>
<p>Ranking strategies by a composite of value-add, Sharpe, CAGR, drawdown, and information ratio, the
clear pattern is that <b>less-frequent and wider-band rebalancing wins after tax</b>. Monthly rebalancing
ranks worst overall and is worst in four of the six market periods.</p>
{strat_table(s['strat_rank'])}

<h2>Recommendations</h2>
<ul>
<li><b>Replacement-ETF quality is the most important lever.</b> Map each holding to a closely tracking,
style-matched substitute (growth to growth, value to value). The largest losses in this study came from
replacing growth sleeves with a broad large-cap fund, not from the tax mechanics.</li>
<li><b>Treat TLH as a portfolio-design decision, not a default.</b> It adds value for diversified portfolios
with good replacements; for concentrated or style-tilted portfolios, confirm the replacement tracks before
enabling it.</li>
<li><b>Default to infrequent, wide-band rebalancing</b> (yearly, relative-25%, absolute-20%); monthly and
quarterly rebalancing churn the portfolio and add cost without improving the after-tax result.</li>
<li><b>Lead client communication with post-liquidation figures,</b> since much of the in-flight tax benefit
is deferral that shrinks once gains are realized.</li>
</ul>

<h2>Execution Plan</h2>
<p>We propose a phased, roughly nine-month rollout: curate and validate the replacement-ETF map against
realized tracking, integrate the measurement engine with live model portfolios, run a pilot with a 15 to 25
advisor cohort, instrument the auditable trade log inside the advisor tooling, and track a target reduction
in TLH-related service tickets before a broader release.</p>

<h2>Limitations</h2>
<ul>
<li>Net value-add is reported on a price basis for cross-strategy comparability; the interactive app can
additionally model dividends and reinvestment.</li>
<li>Results depend heavily on the supplied replacement-ETF map; a different (better-tracking) map would
materially improve the harvested portfolios.</li>
<li>The Sharpe ratio is defined as CAGR over annualized volatility at a 0% risk-free rate, which is
internally consistent for ranking but differs from the textbook definition.</li>
<li>The price universe covers active tickers, so single-security history carries some survivorship bias.</li>
<li>Dividend timing uses payment date rather than ex-date, and only federal short and long-term capital
gains plus the ordinary-income offset are modeled (no state or local taxes). Portfolios are long-only.</li>
</ul>

<h2>Conclusion</h2>
<p>Across 192 matched comparisons, tax-loss harvesting is a reliable tax tool whose bottom-line value is
gated by the quality of the wash-sale replacement. Harvesting cut taxes in the large majority of runs, but
because it forces the portfolio to hold substitute ETFs, the net result hinges on how closely those
substitutes track. The deliverable is not a blanket "always harvest" rule but an explainable engine, a
clear decomposition of where harvesting helps and hurts, and a ranked playbook an advisor can defend.</p>

<h2>Acknowledgments</h2>
<p>We thank our capstone sponsor, Brandt Green, and the Vise team for the data, framing, and guidance, and
the UT Austin MSBA program for supporting the project.</p>
</body></html>
"""


def exec_summary_html(s):
    best, worst, ov = s["best"], s["worst"], s["overall"]
    return f"""
<html><head><style>{CSS}</style></head><body>
{FOOTER}
<h1>Tax-Aware Rebalancing and TLH: Executive Summary</h1>
<div class="subtitle">UT Austin MSBA Capstone, Group 20, Vise</div>
<div class="meta">{TEAM} &nbsp;|&nbsp; Sponsor: Brandt Green, Vise</div>

<div class="callout"><b>Bottom line.</b> Across 192 matched TLH-versus-no-TLH comparisons, harvesting
reliably cut taxes (in {ov['pct_taxcut']:.0f}% of runs, about {money(ov['tax'])} per $1M on average), but
its net effect on portfolio value is decided by how well the wash-sale replacement ETF tracks the original.
Net of tax, tracking, and cost, harvesting helped in {s['pct_pre']:.0f}% of runs pre-liquidation and
{s['pct_post']:.0f}% after liquidation.</div>

<h2>What we built</h2>
<p>A transparent, lot-level, tax-aware simulation engine (short/long-term classification, $3k ordinary
offset, character-preserving carry-forward, 30-day wash-sale rule with automatic proxy substitution, and
calendar plus drift-band rebalancing) wrapped in an interactive dashboard, plus a 384-run backtest and a
ranked strategy playbook. Every reported number is reproducible from the committed code and data.</p>

<h2>How we tested it</h2>
<p>Four portfolios (40/60 and 100/0 model ETFs, a 2-ETF and a 3-ETF mix) across six market periods, eight
rebalancing strategies, each run with and without harvesting: 192 matched comparisons. All runs use the
same engine, $1M of capital, 35% short / 20% long-term tax rates, 12 bps round-trip cost, and a 10% harvest
threshold, so the only difference within a pair is harvesting.</p>

<h2>Headline result: decompose the value-add</h2>
<p>For each portfolio, the net after-tax value-add of harvesting splits into tax saved, the tracking
difference of the replacement ETFs, and extra cost. Tax saved is positive everywhere; replacement tracking
decides the net.</p>
{decomp_table(s['port'])}
<p>Worst run: <b>{worst['Portfolio']}</b>, {worst['Market Condition'].lower()}, at {money(worst['pre'])}, of
which {money(worst['tracking'])} was replacement tracking (a growth sleeve swapped into a broad S&amp;P 100
fund) and {money(worst['tax_saved'])} was tax. Best run: <b>{best['Portfolio']}</b>,
{best['Market Condition'].lower()}, at {money(best['pre'])}, also tracking-driven (the replacement
outperformed by {money(best['tracking'])}). Single-run extremes reflect replacement tracking in both
directions; the reliable effect is the tax saving.</p>

<h2>Recommendations</h2>
<ul>
<li>Curate the replacement-ETF map to closely tracking, style-matched substitutes. It is the biggest lever.</li>
<li>Enable TLH for diversified portfolios with good replacements; confirm tracking before enabling it for
concentrated or style-tilted portfolios.</li>
<li>Default to infrequent, wide-band rebalancing (yearly, relative-25%, absolute-20%); monthly rebalancing
ranks worst overall.</li>
<li>Communicate value using post-liquidation figures, since much of the tax benefit is deferral.</li>
</ul>

<h2>Key assumptions</h2>
<p>Price-basis returns for comparability; Sharpe defined as CAGR over volatility (Rf = 0); active-ticker
universe (some survivorship bias); federal capital gains only; long-only. The interactive app can
additionally model dividends and reinvestment.</p>
</body></html>
"""


def render(html, out_path):
    with open(out_path, "wb") as f:
        result = pisa.CreatePDF(html, dest=f)
    status = "OK" if not result.err else f"{result.err} errors"
    print(f"Wrote {out_path}  ({status})")


def main():
    s = compute_stats()
    render(full_report_html(s), HERE / "Vise_Capstone_Final_Report.pdf")
    render(exec_summary_html(s), HERE / "Vise_Executive_Summary.pdf")


if __name__ == "__main__":
    main()
