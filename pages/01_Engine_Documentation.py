"""Engine Documentation: all five sections in one page with tab navigation.

Documents the live engine in optimizer_msba_v1_engine.py (run_optimizer_simulation,
Portfolio, TaxEngine, WashSaleTracker, ProxyResolver) and engine/metrics.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="Engine Documentation", page_icon="📚", layout="wide")

from ui_style import inject_site_css, render_hero, section_sep, section_header, render_footer
inject_site_css()

render_hero(
    eyebrow="Tax-Aware Simulation Engine",
    title='Built on trades.<br>Not on <em>assumptions.</em>',
    subtitle="A lot-level, transaction-driven engine for portfolio valuation, tax handling, wash-sale-compliant tax-loss harvesting, and dividend reinvestment. Every dollar is traceable. Every gain is correctly taxed. Every price is real.",
    formula='Portfolio Value &nbsp;=&nbsp; <span>(Shares × Price)</span> &nbsp;+&nbsp; Cash',
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Core Engine",
    "Tax Engine",
    "Sell & TLH",
    "Dividends",
    "Valuation & Performance",
])

# ═══════════════════════════════════════════════════════════
# TAB 1: Core Engine Overview
# ═══════════════════════════════════════════════════════════
with tab1:
    section_sep("01", "System Overview")
    section_header(
        "The Problem",
        "Most portfolio models are wrong<br>from the start.",
        "Most simulations compound daily returns, multiplying yesterday's value by today's price change. It is fast, but it cannot answer the question that actually matters: <em>if I liquidated everything right now and paid the tax, what would I walk away with?</em> This engine answers it by tracking every share lot, cost basis, and tax event.",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="vise-label" style="margin-bottom:0.5rem;">What most models do wrong</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="vise-principle" style="border-color: rgba(255,140,97,0.3);">
  <div class="vise-principle-icon" style="background:rgba(255,140,97,0.1);border-color:rgba(255,140,97,0.3);color:var(--accent3);">✕</div>
  <div>
    <div class="vise-principle-title" style="color:var(--accent3);">Inject dividends into the return stream</div>
    <div class="vise-principle-body">Blurs price appreciation and cash received, and prevents lot-level tracking of DRIP shares.</div>
  </div>
</div>
<div class="vise-principle" style="border-color: rgba(255,140,97,0.3);">
  <div class="vise-principle-icon" style="background:rgba(255,140,97,0.1);border-color:rgba(255,140,97,0.3);color:var(--accent3);">✕</div>
  <div>
    <div class="vise-principle-title" style="color:var(--accent3);">Apply taxes as an end-of-year haircut</div>
    <div class="vise-principle-body">Ignores lot-level character (short vs long term), loss carry-forward, and the $3k ordinary offset.</div>
  </div>
</div>
<div class="vise-principle" style="border-color: rgba(255,140,97,0.3);">
  <div class="vise-principle-icon" style="background:rgba(255,140,97,0.1);border-color:rgba(255,140,97,0.3);color:var(--accent3);">✕</div>
  <div>
    <div class="vise-principle-title" style="color:var(--accent3);">Harvest losses without a wash-sale rule</div>
    <div class="vise-principle-body">Overstates the tax benefit by ignoring disallowed losses and the cost of holding a replacement ETF.</div>
  </div>
</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="vise-label" style="margin-bottom:0.5rem;">What this engine does instead</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="vise-principle">
  <div class="vise-principle-icon">✓</div>
  <div>
    <div class="vise-principle-title">Every dollar traces to a trade</div>
    <div class="vise-principle-body">Nothing happens unless a trade executes. No phantom gains, no drift.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">✓</div>
  <div>
    <div class="vise-principle-title">Lot-level, character-aware tax</div>
    <div class="vise-principle-body">Each lot is classified short or long term; gains net by character with a $3k ordinary offset and carry-forward.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">✓</div>
  <div>
    <div class="vise-principle-title">Wash-sale-compliant harvesting</div>
    <div class="vise-principle-body">Loss sales respect a 30-day window and swap into a proxy ETF, so the position stays invested.</div>
  </div>
</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:2rem;">The Core Components</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-card-grid">
  <div class="vise-card">
    <div class="vise-card-num">01</div>
    <div class="vise-card-title">run_optimizer_simulation</div>
    <div><span class="vise-card-tag tag-orchestrator">Orchestrator</span></div>
    <p>The driver function. Builds the forward-filled price matrix once, then walks every trading day: dividends, harvesting, rebalancing, and the daily NAV snapshot. Returns the NAV series and all summary metrics.</p>
  </div>
  <div class="vise-card">
    <div class="vise-card-num">02</div>
    <div class="vise-card-title">Portfolio</div>
    <div><span class="vise-card-tag tag-stateful">Stateful</span></div>
    <p>The central ledger. Holds all state: lots, cash, realized trades, and taxes paid. Exposes buy(), sell(), and process_dividend(); embeds transaction costs on every trade.</p>
  </div>
  <div class="vise-card">
    <div class="vise-card-num">03</div>
    <div class="vise-card-title">TaxEngine</div>
    <div><span class="vise-card-tag tag-stateful">Stateful (annual)</span></div>
    <p>Classifies each lot short or long term, nets gains by character, applies the $3k ordinary offset, carries losses forward, and settles the liability once per year.</p>
  </div>
  <div class="vise-card">
    <div class="vise-card-num">04</div>
    <div class="vise-card-title">WashSaleTracker</div>
    <div><span class="vise-card-tag tag-stateless">Rules</span></div>
    <p>Enforces the 30-day lookback and 30-day forward block. Disallowed losses are not deducted; blocked rebuys are redirected to a proxy.</p>
  </div>
  <div class="vise-card">
    <div class="vise-card-num">05</div>
    <div class="vise-card-title">ProxyResolver</div>
    <div><span class="vise-card-tag tag-stateless">Lookup</span></div>
    <p>Maps each holding to ranked replacement ETFs (from proxy_lookup.csv) so a harvested position keeps market exposure during the wash-sale window.</p>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">How Cash Moves</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-outputs">
  <div class="vise-output-item"><div class="vise-output-name" style="color:var(--accent)">BUY</div><div class="vise-output-desc">Cash out → −(shares × price) × (1 + cost_rate)</div></div>
  <div class="vise-output-item"><div class="vise-output-name" style="color:var(--accent)">SELL</div><div class="vise-output-desc">Cash in → +(shares × price) × (1 − cost_rate); realizes gain/loss</div></div>
  <div class="vise-output-item"><div class="vise-output-name" style="color:var(--accent)">DIVIDEND</div><div class="vise-output-desc">Cash in → +(gross × (1 − lt_rate)) after qualified-dividend tax</div></div>
  <div class="vise-output-item"><div class="vise-output-name" style="color:var(--accent)">DRIP</div><div class="vise-output-desc">Cash out → reinvest the after-tax dividend into a new lot</div></div>
  <div class="vise-output-item"><div class="vise-output-name" style="color:var(--accent)">TAX SETTLEMENT</div><div class="vise-output-desc">Cash out → once per year, the netted capital-gains liability</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">Key Methods at a Glance</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-classref">
  <div class="vise-classref-title">class Portfolio</div>
  <div class="vise-classref-method"><div class="vise-crm-sig">buy(date, ticker, shares, price, source="BUY")</div><div class="vise-crm-desc">Opens a new lot. Embeds transaction cost in the cash outflow and cost basis. Backs out shares from available cash; never goes negative.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">sell(date, ticker, shares, price, lot_selection="TAX_OPTIMAL")</div><div class="vise-crm-desc">Disposes lots via FIFO / LIFO / TAX_OPTIMAL. Realizes gains, routes them through TaxEngine.step(), and respects the wash-sale rule.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">process_dividend(date, ticker, div_per_share, price, reinvest)</div><div class="vise-crm-desc">Taxes the dividend at the long-term (qualified) rate, adds the after-tax cash, and optionally reinvests it as a new DRIP lot.</div></div>
</div>
<div class="vise-classref" style="border-left-color: var(--accent2);">
  <div class="vise-classref-title" style="color:var(--accent2);">function run_optimizer_simulation(...)</div>
  <div class="vise-classref-method"><div class="vise-crm-sig">prices_df, dividends_df, tickers, weights, start_date, end_date, ...</div><div class="vise-crm-desc">Builds the forward-filled price matrix once, then iterates each trading day. Handles dividends, TLH, calendar/threshold rebalancing, optional end liquidation, and returns the NAV series plus metrics.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">tax_rates, cost_config, tlh_threshold, proxy_df, wash_sale_days</div><div class="vise-crm-desc">The levers: tax rates, the 12 bps cost config, the harvest loss threshold, the proxy map, and the wash-sale window.</div></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# TAB 2: Tax Engine
# ═══════════════════════════════════════════════════════════
with tab2:
    section_sep("02", "Tax Engine")
    section_header(
        "Tax Treatment",
        "Two characters.<br>Netted, offset, settled.",
        "Gains and losses are classified short or long term at the lot level, netted by character within the year, reduced by an up-to-$3,000 ordinary-income offset, and the remaining liability is settled once per year. Unused losses carry forward and keep their character.",
    )

    st.markdown("""
<div class="vise-tax-grid">
  <div class="vise-tax-card st">
    <div class="vise-tax-rate">35%</div>
    <div class="vise-tax-name">Short-Term Capital Gains</div>
    <div class="vise-tax-desc">Lots held <strong>365 days or fewer</strong>. Taxed at the ordinary-income rate. Frequent trading and early exits land here. (Default rate, sidebar-configurable.)</div>
  </div>
  <div class="vise-tax-card lt">
    <div class="vise-tax-rate">20%</div>
    <div class="vise-tax-name">Long-Term Capital Gains</div>
    <div class="vise-tax-desc">Lots held <strong>more than 365 days (366+)</strong>. Preferential rate. The IRS "more than one year" rule, applied at the lot level.</div>
  </div>
  <div class="vise-tax-card div">
    <div class="vise-tax-rate">LT</div>
    <div class="vise-tax-name">Dividend Income</div>
    <div class="vise-tax-desc">Taxed at the <strong>long-term (qualified-dividend) rate</strong> on PAYDATE, applied to the gross dividend before reinvestment. Most ETF dividends qualify.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="vise-label">Holding Period Classification</div>', unsafe_allow_html=True)
        st.markdown("""
<p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:1rem;line-height:1.7;">
Every lot carries an <code style="font-family:'DM Mono',monospace;font-size:0.82em;background:var(--surface2);border:1px solid var(--border);padding:0.1em 0.4em;border-radius:3px;color:var(--accent2);">open_date</code>. When the lot is sold, the engine computes holding days and routes the gain to the correct character.
</p>
<div class="vise-code"><span class="cm"># TaxEngine.classify: IRS "more than one year"</span>
days = (close_date - open_date).days

<span class="kw">if</span> days &gt; <span class="s">365</span>:
    gain_type = <span class="s">'LT'</span>  <span class="cm"># 366+ days = long-term, 20%</span>
<span class="kw">else</span>:
    gain_type = <span class="s">'ST'</span>  <span class="cm"># 365 or fewer = short-term, 35%</span>

<span class="cm"># Happens at LOT level: one sell order
# can realize both ST and LT events.</span></div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="vise-label">Netting, Offset, and Carry-Forward</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="vise-principle">
  <div class="vise-principle-icon">→</div>
  <div>
    <div class="vise-principle-title">Net by character, then cross-net</div>
    <div class="vise-principle-body">Within the year, ST losses offset ST gains and LT losses offset LT gains first; any remaining loss then offsets the other character.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">→</div>
  <div>
    <div class="vise-principle-title">$3,000 ordinary offset</div>
    <div class="vise-principle-body">After netting, up to $3,000 of net loss offsets ordinary income (valued at the ST rate) each year.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">∞</div>
  <div>
    <div class="vise-principle-title">Carry-forward preserves character</div>
    <div class="vise-principle-body">Excess ST loss stays ST and excess LT loss stays LT across years. The remaining liability settles once per year.</div>
  </div>
</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">How TaxEngine Works in Code</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-classref">
  <div class="vise-classref-title">class TaxEngine · accumulates within a year, settles annually</div>
  <div class="vise-classref-method"><div class="vise-crm-sig">classify(open_date, close_date)</div><div class="vise-crm-desc">Returns ('LT', lt_rate) if held more than 365 days, else ('ST', st_rate). Called once per lot during sell().</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">step(date, gain, gain_type)</div><div class="vise-crm-desc">Adds the realized gain/loss to the year's ST or LT bucket and returns the incremental change in tax liability after netting and the $3k offset.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">st_loss_cf · lt_loss_cf</div><div class="vise-crm-desc">Carry-forward balances that persist across the simulation, each keeping its own character. Reset to 0 only at construction.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">annual settlement</div><div class="vise-crm-desc">At each year boundary the netted liability is charged to cash once, and the year's offset usage resets.</div></div>
</div>
<p style="font-size:0.82rem;color:var(--text-muted);margin-top:0.75rem;line-height:1.6;">
TaxEngine is created inside Portfolio.__init__ and stored as self.tax. You never call it directly: Portfolio.sell() and Portfolio.process_dividend() invoke it on every realization event.
</p>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# TAB 3: Sell Handling & TLH
# ═══════════════════════════════════════════════════════════
with tab3:
    section_sep("03", "Sell Handling")
    section_header(
        "Lot Selection, Wash Sales & Tax Alpha",
        "Which shares you sell matters<br>as much as when you sell.",
        "When you hold multiple lots of the same stock at different cost bases, the engine chooses which to sell. That choice changes the tax bill. It supports three strategies, set per sell order via <code style='font-family:DM Mono,monospace;font-size:0.82em;background:#1a1f2e;border:1px solid #232a3a;padding:0.1em 0.4em;border-radius:3px;color:#7b8cff;'>lot_selection</code>.",
    )

    st.markdown("""
<div class="vise-tax-grid" style="margin-bottom:2rem;">
  <div class="vise-tax-card" style="border-top:2px solid var(--accent2);">
    <div class="vise-tax-rate" style="font-size:1.3rem;color:var(--accent2);margin-bottom:0.4rem;">FIFO</div>
    <div class="vise-tax-name">First In, First Out</div>
    <div class="vise-tax-desc">Sells the <strong>oldest lot first</strong>. Simple and predictable. Oldest lots are most likely long term (20%), so FIFO tends to favour lower rates but ignores loss opportunities.</div>
  </div>
  <div class="vise-tax-card" style="border-top:2px solid var(--text-muted);">
    <div class="vise-tax-rate" style="font-size:1.3rem;color:var(--text-muted);margin-bottom:0.4rem;">LIFO</div>
    <div class="vise-tax-name">Last In, First Out</div>
    <div class="vise-tax-desc">Sells the <strong>newest lot first</strong>. Keeps old low-basis lots alive longer, deferring their gain further into the future.</div>
  </div>
  <div class="vise-tax-card lt">
    <div class="vise-tax-rate" style="font-size:1rem;margin-bottom:0.4rem;">TAX_OPTIMAL</div>
    <div class="vise-tax-name">Tax-Loss Harvesting</div>
    <div class="vise-tax-desc">Sells <strong>loss lots first</strong> (largest ST loss first, then LT losses), gain lots last. Crystallizes losses into a carry-forward that offsets future gains.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="vise-label">Wash-Sale Rule & Proxy Substitution</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-steps" style="margin-bottom:2rem;">
  <div class="vise-step"><div class="vise-step-num">1</div><div><div class="vise-step-title">30-day lookback</div><div class="vise-step-detail">A loss sale is disallowed (the deduction is suppressed) if the same security was bought within the prior 30 days.</div></div></div>
  <div class="vise-step"><div class="vise-step-num">2</div><div><div class="vise-step-title">30-day forward block</div><div class="vise-step-detail">After a loss sale, rebuying the same security within 30 days is blocked, so the harvested loss is not reversed.</div></div></div>
  <div class="vise-step"><div class="vise-step-num">3</div><div><div class="vise-step-title">Proxy substitution</div><div class="vise-step-detail">To stay invested during the window, the engine buys a ranked replacement ETF (from proxy_lookup.csv) instead of sitting in cash.</div></div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="vise-label">What "Tax Alpha" Actually Measures</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-example-box" style="margin-bottom:2rem;">
  <div style="padding:1.25rem 1.5rem;font-size:0.9rem;color:var(--text-muted);line-height:1.8;">
    <strong style="color:var(--heading);">Tax Alpha = (harvested portfolio value) − (identical portfolio with no harvesting).</strong> It is the <em>net</em> after-tax value-add of harvesting, and it bundles three effects:
    <br>• <strong style="color:var(--accent);">Tax saved</strong>: harvesting reliably cuts the tax bill (it did so in the large majority of backtested runs).
    <br>• <strong style="color:var(--accent3);">Replacement tracking</strong>: the return difference from holding a proxy ETF instead of the original. Across the study this term usually <em>dominates</em> the net figure.
    <br>• <strong>Transaction cost</strong>: the extra trading the harvest-and-rebuy cycle incurs.
    <br><br>So a positive Tax Alpha depends on the replacement tracking the original well. It is reported as net value-add, not as pure tax savings.
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="vise-label">Loss Carry-Forward</div>', unsafe_allow_html=True)
        st.markdown("""
<p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:1rem;line-height:1.7;">Harvested losses do not disappear. They go into character-specific carry-forward buckets that offset the next gains before tax is computed, with up to $3,000 of net loss offsetting ordinary income each year.</p>
<div class="vise-code"><span class="cm"># Within the year, net by character first:</span>
taxable_st = st_gains - st_losses   <span class="cm"># then cross-net</span>
taxable_lt = lt_gains - lt_losses

<span class="cm"># Up to $3,000 of net loss offsets ordinary income.
# Excess ST loss stays ST; excess LT loss stays LT,
# carried forward to future years unchanged.</span></div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="vise-label">Cost Basis & Realized Gain</div>', unsafe_allow_html=True)
        st.markdown("""
<p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:1rem;line-height:1.7;">Transaction cost is a single round-trip rate (12 bps = 5 commission + 5 slippage + 2 bid-ask), embedded on every trade. Buys cost more and sells net less:</p>
<div class="vise-code">cost_rate = (<span class="s">5</span> + <span class="s">5</span> + <span class="s">2</span>) / <span class="s">10000</span>  <span class="cm"># 12 bps</span>

buy_cash  = shares * price * (<span class="s">1</span> + cost_rate)
net_proceeds = shares * price * (<span class="s">1</span> - cost_rate)
gain = net_proceeds - cost_basis
<span class="cm"># disallowed loss? deduction suppressed (wash sale)</span></div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# TAB 4: Dividends & Cash Flows
# ═══════════════════════════════════════════════════════════
with tab4:
    section_sep("04", "Dividend Handling")
    section_header(
        "DRIP Sequence",
        "Dividends trigger on PAYDATE.<br>Taxed, then reinvested.",
        "Dividends are cash events, not return adjustments. On the payment date the engine taxes the dividend at the qualified (long-term) rate and, if reinvestment is on, buys new shares with the after-tax cash. It checks PAYDATE, not EXDATE.",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div class="vise-steps">
  <div class="vise-step"><div class="vise-step-num">1</div><div><div class="vise-step-title">Count shares held</div><div class="vise-step-detail">Sum open-lot shares for this security as of PAYDATE. If zero, the dividend is silently skipped.</div></div></div>
  <div class="vise-step"><div class="vise-step-num">2</div><div><div class="vise-step-title">Compute gross dividend</div><div class="vise-step-detail">shares_held × div_per_share</div></div></div>
  <div class="vise-step"><div class="vise-step-num">3</div><div><div class="vise-step-title">Apply dividend tax</div><div class="vise-step-detail">tax = gross × lt_rate (qualified-dividend assumption)<br>after_tax = gross − tax</div></div></div>
  <div class="vise-step"><div class="vise-step-num">4</div><div><div class="vise-step-title">Add after-tax cash</div><div class="vise-step-detail">The after-tax dividend is credited to cash.</div></div></div>
  <div class="vise-step"><div class="vise-step-num">5</div><div><div class="vise-step-title">Reinvest (DRIP), if enabled</div><div class="vise-step-detail">drip_shares = after_tax ÷ price, routed through the full cost engine. <strong>Creates a new lot</strong> with today as open_date. If reinvestment is off, the cash simply remains.</div></div></div>
</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="vise-label">Why DRIP Creates a New Lot</div>', unsafe_allow_html=True)
        st.markdown("""
<p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:1.25rem;line-height:1.7;">Reinvestment opens a brand-new lot, with today's price as cost basis and today as the open date.</p>
<div class="vise-principle">
  <div class="vise-principle-icon">→</div>
  <div>
    <div class="vise-principle-title">Different cost basis</div>
    <div class="vise-principle-body">DRIP shares cost today's price, not the original price. Gains are computed correctly when sold.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">→</div>
  <div>
    <div class="vise-principle-title">Its own holding-period clock</div>
    <div class="vise-principle-body">The 366-day long-term threshold starts from the DRIP date, independent of the original position.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon">→</div>
  <div>
    <div class="vise-principle-title">Quarterly dividends spawn many lots</div>
    <div class="vise-principle-body">Over a multi-year hold, a single original buy can produce many DRIP lots, each tracked separately.</div>
  </div>
</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">How Dividends Work in Code</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-classref">
  <div class="vise-classref-title">Portfolio.process_dividend(date, ticker, div_per_share, price, reinvest, *, dividend_tax_rate)</div>
  <div class="vise-classref-method"><div class="vise-crm-sig">Steps 1–2: shares + gross</div><div class="vise-crm-desc">Sums open-lot shares for the ticker. If 0, returns silently. Gross = shares × div_per_share.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">Steps 3–4: tax + cash</div><div class="vise-crm-desc">Taxes the gross at dividend_tax_rate (the long-term / qualified rate) and credits the after-tax amount to cash.</div></div>
  <div class="vise-classref-method"><div class="vise-crm-sig">Step 5: DRIP buy</div><div class="vise-crm-desc">If reinvest is true, calls buy(source='DRIP') with after_tax ÷ price shares, opening a new lot. Dividends are not written to the realized-gains ledger (that ledger holds sale events only).</div></div>
</div>
<div class="vise-classref" style="border-left-color:var(--accent2);margin-top:0.75rem;">
  <div class="vise-classref-title" style="color:var(--accent2);">Dividend lookup in the daily loop</div>
  <div class="vise-classref-method"><div class="vise-crm-sig">div_lookup[(ticker, paydate)]</div><div class="vise-crm-desc">A dict built once before the loop, keyed by (ticker, PAYDATE), so each day's check is O(1). The data must contain TICKERSYMBOL, PAYDATE, and DIVAMOUNT; the engine reads PAYDATE, not EXDATE.</div></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# TAB 5: Valuation & Performance
# ═══════════════════════════════════════════════════════════
with tab5:
    section_sep("05", "Daily Valuation")
    section_header(
        "The Daily Loop",
        "A fixed sequence. Every trading day.<br>No look-ahead, ever.",
        "run_optimizer_simulation iterates each trading day in a fixed order. The order matters: DRIP shares and harvests must be visible in the same day's valuation, and only data up to today is ever used.",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div class="vise-principle">
  <div class="vise-principle-icon" style="font-size:0.65rem;font-weight:500;">01</div>
  <div>
    <div class="vise-principle-title">Price the day</div>
    <div class="vise-principle-body">Use the forward-filled price matrix at today's date. Future prices are never visible (no look-ahead, no backfill).</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon" style="font-size:0.65rem;font-weight:500;">02</div>
  <div>
    <div class="vise-principle-title">Process dividends</div>
    <div class="vise-principle-body">Any PAYDATE matching today taxes the dividend and reinvests it (DRIP) if enabled.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon" style="font-size:0.65rem;font-weight:500;">03</div>
  <div>
    <div class="vise-principle-title">Harvest and rebalance</div>
    <div class="vise-principle-body">Check each lot against the TLH loss threshold (wash-sale aware, with proxy substitution), then apply calendar or drift-band rebalancing.</div>
  </div>
</div>
<div class="vise-principle">
  <div class="vise-principle-icon" style="font-size:0.65rem;font-weight:500;">04</div>
  <div>
    <div class="vise-principle-title">Record NAV snapshot</div>
    <div class="vise-principle-body">Market value + cash. Taxes settle once per year; an optional full liquidation runs on the final day.</div>
  </div>
</div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div class="vise-formula-visual">
  <div class="vise-formula-big">
    <em>Portfolio Value</em><br>= <span>(Shares × Price)</span> + Cash
  </div>
  <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:0.5rem;">Recomputed from first principles every day. Never carries forward yesterday's value.</div>
</div>
<div style="padding:1rem 1.25rem;background:var(--surface);border:1px solid rgba(79,255,176,0.2);border-radius:6px;">
  <div class="vise-label" style="margin-bottom:0.4rem;">The NAV Series Is the After-Tax Series</div>
  <p style="font-size:0.84rem;color:var(--text-muted);line-height:1.65;">Capital-gains tax settles once a year and dividend tax is withheld on receipt, so portfolio value already reflects taxes paid. No separate after-tax adjustment is needed.</p>
</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">Performance Metrics</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-outputs">
  <div class="vise-output-item"><div class="vise-output-name">CAGR</div><div class="vise-output-desc">Compound annual growth of the after-tax NAV over the simulation window.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Volatility</div><div class="vise-output-desc">Annualized standard deviation of daily returns.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Sharpe</div><div class="vise-output-desc">CAGR ÷ annualized volatility at a 0% risk-free rate. Internally consistent for ranking; not the textbook mean-excess-return form.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Max / Avg Drawdown</div><div class="vise-output-desc">Largest and average peak-to-trough declines in the NAV path.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Tracking Error & Information Ratio</div><div class="vise-output-desc">Std. dev. of, and risk-adjusted, active return versus the matched no-TLH benchmark.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Calmar</div><div class="vise-output-desc">CAGR ÷ absolute max drawdown.</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1.5rem;">Edge Cases & Guardrails</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-guardrails">
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Sell &gt; shares held</div><div class="vise-guardrail-response">Order <strong>clamped to available shares</strong>. No crash.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Insufficient cash for buy</div><div class="vise-guardrail-response">Shares are <strong>backed out of available cash</strong>. Cash never goes negative.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Harvest with no proxy available</div><div class="vise-guardrail-response">TLH for that ticker is <strong>skipped</strong> rather than forcing a wash sale.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">No price on a dividend pay date</div><div class="vise-guardrail-response">Uses the <strong>last forward-filled close</strong>. Weekend/holiday paydates handled.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Zero shares at dividend time</div><div class="vise-guardrail-response">Dividend <strong>silently skipped</strong>. The position was already sold.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">End of simulation</div><div class="vise-guardrail-response">Optional <strong>liquidate_at_end</strong> sells everything and books the final tax true-up.</div></div>
</div>
""", unsafe_allow_html=True)

    section_sep("06", "Configuration")
    section_header(
        "The Levers",
        "Tax rates and costs<br>in two simple inputs.",
        "Every run is parameterized by a tax-rates dict and a cost-config dict, passed straight into run_optimizer_simulation. Change them in the sidebar; they flow everywhere.",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
<div class="vise-config-block">
  <div class="vise-config-header">tax_rates</div>
  <div class="vise-config-row"><div class="vise-config-key">st_rate</div><div class="vise-config-val">0.35</div><div class="vise-config-desc">Gains on lots held 365 days or fewer; also the rate for the $3k ordinary offset</div></div>
  <div class="vise-config-row"><div class="vise-config-key">lt_rate</div><div class="vise-config-val">0.20</div><div class="vise-config-desc">Gains on lots held more than 365 days, and the qualified-dividend rate</div></div>
  <div class="vise-config-row"><div class="vise-config-key">lt_holding_days</div><div class="vise-config-val">365</div><div class="vise-config-desc">Threshold: more than this many days is long term (366+)</div></div>
</div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="vise-config-block">
  <div class="vise-config-header">DEFAULT_COST_CONFIG</div>
  <div class="vise-config-row"><div class="vise-config-key">commission_bps</div><div class="vise-config-val">5 bps</div><div class="vise-config-desc">Commission (about $0.005/share on a $100 stock)</div></div>
  <div class="vise-config-row"><div class="vise-config-key">slippage_bps</div><div class="vise-config-val">5 bps</div><div class="vise-config-desc">Market-impact slippage at execution</div></div>
  <div class="vise-config-row"><div class="vise-config-key">bid_ask_bps</div><div class="vise-config-val">2 bps</div><div class="vise-config-desc">Half-spread; the three sum to a 12 bps round-trip rate</div></div>
</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="vise-label" style="margin-top:1rem;">Common Configurations</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="vise-guardrails">
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Tax-deferred account (IRA / 401k)</div><div class="vise-guardrail-response">Set st_rate and lt_rate to <strong>0</strong>; harvesting adds no value.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Commission-free brokerage</div><div class="vise-guardrail-response">Set commission_bps to <strong>0</strong>; keep slippage and bid-ask.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Everything long-term</div><div class="vise-guardrail-response">Set lt_holding_days to <strong>0</strong>; all gains taxed at the LT rate.</div></div>
  <div class="vise-guardrail"><div class="vise-guardrail-trigger">Institutional slippage</div><div class="vise-guardrail-response">Raise slippage_bps to <strong>10–20</strong> for large-order realism.</div></div>
</div>
""", unsafe_allow_html=True)

    section_sep("07", "Reproducibility")
    section_header(
        "Traceable & Repeatable",
        "Every number reproduces<br>from the committed code.",
        "The engine is deterministic: no randomness, no wall-clock dependence. The same inputs produce the same outputs, and every reported figure can be regenerated from the committed data with one command.",
    )

    st.markdown("""
<div class="vise-outputs">
  <div class="vise-output-item"><div class="vise-output-name">Deterministic</div><div class="vise-output-desc">No random seeds needed: the simulation is fully rules-based, so results are bit-for-bit reproducible.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">No look-ahead</div><div class="vise-output-desc">Forward-fill only, never backfill; each day sees only data up to that date.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">One-command backtest</div><div class="vise-output-desc">Backtest/run_backtest.py regenerates the 384-run study; build_playbook.py builds the ranked playbook.</div></div>
  <div class="vise-output-item"><div class="vise-output-name">Tested</div><div class="vise-output-desc">A pytest suite checks buy-and-hold parity, harvest firing, wash-sale handling, the day-count boundary, and NAV reconciliation.</div></div>
</div>
""", unsafe_allow_html=True)

render_footer()
