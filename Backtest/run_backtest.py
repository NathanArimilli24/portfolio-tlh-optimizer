#!/usr/bin/env python3
"""
run_backtest.py
===============
Reproducible canonical backtest for the Vise TLH capstone.

Runs every combination of:
    4 portfolios  x  6 market periods  x  8 rebalancing strategies  x  {TLH on, TLH off}
        = 192 matched TLH-vs-no-TLH comparisons = 384 individual simulation runs

Every run uses the lot-level tax engine (run_optimizer_simulation) so that
taxes, transaction costs, wash-sale rules, and forward-fill are identical across
the TLH-on and TLH-off legs. The only difference between a matched pair is the
TLH threshold.

Returns are price-only by default. Running every strategy (TLH-on and TLH-off,
calendar and threshold) through the same engine on the same basis keeps the
cross-strategy comparison apples-to-apples and keeps tax-loss harvesting confined
to real position lots rather than hundreds of tiny dividend-reinvestment lots.
Pass --dividends to model dividend reinvestment (DRIP, total-return) instead.

Outputs (written next to this script):
    comparative_analysis_results.csv          - 384 rows, one per run
    outputs/12_etf_portfolio.csv              - the three institutional portfolios
    outputs/3_etf_test_portfolio.csv          - the 3-ETF diversified test portfolio

This is the single source of truth for the numbers in the report, slides, and
README. Regenerate the data it needs first with:  python scripts/prepare_data.py
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from time import time

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine import build_prices_wide, compute_drift, compute_strategy_metrics  # noqa: E402
from optimizer_msba_v1_engine import run_optimizer_simulation  # noqa: E402

# ── Simulation parameters ─────────────────────────────────────────────────────
TIME_PERIODS = {
    'Bear (2007–2008)':     ('2007-01-01', '2008-12-31'),
    'Baseline (2010–2019)': ('2010-01-01', '2019-12-31'),
    'Bull (2023–2024)':     ('2023-01-01', '2024-12-31'),
    'Past 5Y (2021–2025)':  ('2021-01-01', '2025-12-31'),
    'Past 10Y (2016–2025)': ('2016-01-01', '2025-12-31'),
    'Past 20Y (2006–2025)': ('2006-01-01', '2025-12-31'),
}
INITIAL_CAPITAL = 1_000_000.0
TAX_RATES = {'st_rate': 0.35, 'lt_rate': 0.20}
PRICE_FIELD = 'PRICECLOSE'
COST_CONFIG = {'commission_bps': 5.0, 'slippage_bps': 5.0, 'bid_ask_bps': 2.0}
TLH_THRESHOLD = 0.10
CALENDAR_FREQS = ['Monthly', 'Quarterly', 'Yearly']
ABS_THRESHOLDS = [0.05, 0.10, 0.20]
REL_THRESHOLDS = [0.25, 0.50]

# 40/60 Target Allocation ETF portfolio (see notebook for original->proxy mapping;
# IAU replaced with GLD to avoid an unadjusted 10x split artifact, cash redistributed).
PORTFOLIO_4060 = {
    "AGG": 0.240, "IVV": 0.175, "LQD": 0.075, "MBB": 0.075, "TLH": 0.070,
    "EFA": 0.045, "EFV": 0.045, "IVW": 0.045, "IVE": 0.040, "EEM": 0.030,
    "TIP": 0.030, "EFG": 0.025, "EMB": 0.020, "IEF": 0.020, "OEF": 0.020,
    "GLD": 0.015, "IWF": 0.015, "IYW": 0.015,
}
PORTFOLIO_1000 = {
    "IVV": 0.415, "EFV": 0.125, "IVW": 0.110, "IVE": 0.100, "EEM": 0.075,
    "IYW": 0.050, "OEF": 0.050, "EFG": 0.045, "IWF": 0.030,
}
PORTFOLIO_2ETF = {"IVV": 0.60, "EFA": 0.40}
PORTFOLIO_3ETF = {"SPY": 0.40, "TLT": 0.40, "GLD": 0.20}
PORTFOLIOS = {
    "40/60 (TA ETF)": PORTFOLIO_4060,
    "100/0 (TA ETF)": PORTFOLIO_1000,
    "2-ETF (IVV/EFA)": PORTFOLIO_2ETF,
    "3-ETF (SPY/TLT/GLD)": PORTFOLIO_3ETF,
}


def strategy_label(strat_type, strat_val, tlh_on):
    tlh_tag = 'TLH=10%' if tlh_on else 'No TLH'
    if strat_type == 'calendar':
        return f'{strat_val} Rebal | {tlh_tag}'
    if strat_type == 'abs':
        return f'Abs Threshold {int(strat_val * 100)}% | {tlh_tag}'
    return f'Rel Threshold {int(strat_val * 100)}% | {tlh_tag}'


def load_inputs(data_dir: Path):
    """Load prices (parquet), dividends (ticker-mapped CSV), and proxy table."""
    prices = pd.read_parquet(data_dir / 'price_data.parquet')
    prices['PRICEDATE'] = pd.to_datetime(prices['PRICEDATE'], errors='coerce')
    if 'TRADINGITEMSTATUSID' in prices.columns:
        prices = prices[prices['TRADINGITEMSTATUSID'].isin([1, 15])].copy()
    prices['PRICECLOSE'] = pd.to_numeric(prices['PRICECLOSE'], errors='coerce')
    prices = prices.dropna(subset=['PRICECLOSE'])
    prices['TICKERSYMBOL'] = prices['TICKERSYMBOL'].astype(str).str.strip().str.upper()

    div = pd.read_csv(data_dir / 'dividend_data.csv')
    if 'PAYDATE' in div.columns:
        div['PAYDATE'] = pd.to_datetime(div['PAYDATE'], errors='coerce')

    px = pd.read_csv(data_dir / 'proxy_lookup.csv')
    px['symbol'] = px['symbol'].astype(str).str.strip().str.upper()
    px['lookup_symbol'] = px['lookup_symbol'].astype(str).str.strip().str.upper()
    proxy_full = (px[['symbol', 'lookup_type', 'lookup_symbol', 'order']]
                  .drop_duplicates(subset=['symbol', 'lookup_symbol'])
                  .sort_values(['symbol', 'order']).reset_index(drop=True))
    return prices, div, proxy_full


def build_proxy_df(portfolio_tickers, start_date, end_date, prices_df, proxy_full):
    """Proxies for held tickers that actually have price data in the period."""
    avail = set(prices_df[(prices_df['PRICEDATE'] >= pd.Timestamp(start_date)) &
                          (prices_df['PRICEDATE'] <= pd.Timestamp(end_date))]['TICKERSYMBOL'].unique())
    sub = proxy_full[proxy_full['symbol'].isin(portfolio_tickers) &
                     proxy_full['lookup_symbol'].isin(avail)].copy()
    return sub.reset_index(drop=True)


def compute_metrics(nav_series, initial_capital, benchmark_nav=None):
    """Title-cased metrics matching the results schema (CAGR uses (n-1)/252)."""
    if nav_series is None or len(nav_series) < 2:
        return {}
    bm_vals = None
    if benchmark_nav is not None:
        bm_aligned = benchmark_nav.reindex(nav_series.index).ffill().dropna()
        common = nav_series.index.intersection(bm_aligned.index)
        if len(common) > 2:
            bm_vals = bm_aligned.loc[common].values
            nav_series = nav_series.loc[common]
    m = compute_strategy_metrics(nav_series, initial_capital, benchmark_values=bm_vals)
    return {
        'Final NAV ($)':     round(nav_series.iloc[-1], 2),
        'Total Return':      m['total_return'],
        'CAGR':              m['cagr'],
        'Volatility':        m['annualized_vol'],
        'Sharpe Ratio':      m['sharpe'],
        'Max Drawdown':      m['max_drawdown'],
        'Skewness':          m['skewness'],
        'Kurtosis':          m['kurtosis'],
        'Tracking Error':    m['tracking_error'],
        'Information Ratio': m['information_ratio'],
    }


def _threshold_trigger_dates(prices_wide, avail_tickers, norm_weights, strat_val, drift_mode):
    """Pre-compute drift-band rebalance dates (shared by TLH on/off legs)."""
    pw = prices_wide[avail_tickers]
    shares = {tk: INITIAL_CAPITAL * norm_weights[tk] / float(pw.iloc[0][tk]) for tk in avail_tickers}
    triggers, cooldown = set(), 0
    for i, dt in enumerate(pw.index):
        if i == 0:
            continue
        pt = {tk: float(pw.loc[dt, tk]) for tk in avail_tickers}
        tv = sum(shares[tk] * pt[tk] for tk in avail_tickers)
        if tv <= 0:
            continue
        cw = {tk: shares[tk] * pt[tk] / tv for tk in avail_tickers}
        drift = compute_drift(cw, norm_weights, drift_mode)
        if cooldown <= 0 and any(drift[tk] > strat_val for tk in avail_tickers):
            triggers.add(dt)
            cooldown = 5
            for tk in avail_tickers:
                shares[tk] = norm_weights[tk] * tv / pt[tk] if pt[tk] > 0 else shares[tk]
        if cooldown > 0:
            cooldown -= 1
    return triggers


def _run_sim_safe(repo_root_str, sim_params):
    """Worker: run one simulation in a (possibly spawned) process."""
    import sys as _sys
    if repo_root_str not in _sys.path:
        _sys.path.insert(0, repo_root_str)
    from optimizer_msba_v1_engine import run_optimizer_simulation as _run
    try:
        return {'ok': True, 'res': _run(**sim_params)}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'error': str(e)}


def load_models_portfolios(data_dir: Path, price_tickers=None):
    """Load every model portfolio from Models.xlsx (latest snapshot, cash removed,
    weights renormalized) plus an equity-allocation category for each. When
    price_tickers is given, also record 'Models Coverage' = the fraction of each
    portfolio's weight whose ticker has price history (the rest, e.g. mutual funds,
    is renormalized away in the backtest)."""
    raw = pd.read_excel(data_dir / 'Models.xlsx')
    raw['Trade Date'] = pd.to_datetime(raw['Trade Date'])
    raw['Ticker'] = raw['Ticker'].astype(str).str.strip().str.upper()
    raw['Weight'] = pd.to_numeric(raw['Weight'], errors='coerce').fillna(0.0)
    latest = raw.groupby('full_name')['Trade Date'].max().reset_index()
    rows = raw.merge(latest, on=['full_name', 'Trade Date'])
    rows = rows[rows['Ticker'] != '$'].copy()
    equity = {'US Equities', 'International/Global Equities',
              'Emerging Market Equities', 'Global Equities'}
    portfolios, meta = {}, {}
    for name, g in rows.groupby('full_name'):
        total = g['Weight'].sum()
        if total < 1e-6:
            continue
        pd_dict = {}
        for tk, w in zip(g['Ticker'], g['Weight']):
            if w > 1e-8:
                pd_dict[tk] = pd_dict.get(tk, 0.0) + w / total
        if not pd_dict:
            continue
        eq = g.loc[g['Asset Class'].isin(equity), 'Weight'].sum() / total
        cat = 'Equity-Heavy' if eq >= 0.70 else ('Balanced' if eq >= 0.30 else 'Fixed Income-Heavy')
        portfolios[name] = pd_dict
        coverage = (round(sum(w for t, w in pd_dict.items() if t in price_tickers), 3)
                    if price_tickers is not None else None)
        meta[name] = {'Category': cat, 'Model Family': g['Model_Family'].iloc[0],
                      'Equity Allocation': round(eq, 3), 'Models Coverage': coverage}
    return portfolios, meta


def build_jobs(prices_raw, div_df, proxy_full, portfolios=PORTFOLIOS):
    # Tickers with at least one price in each period (so build_prices_wide never
    # sees a ticker that is entirely absent from the window, which it rejects).
    period_tickers = {}
    for period_name, (start, end) in TIME_PERIODS.items():
        mask = ((prices_raw["PRICEDATE"] >= pd.Timestamp(start)) &
                (prices_raw["PRICEDATE"] <= pd.Timestamp(end)))
        period_tickers[period_name] = set(prices_raw.loc[mask, "TICKERSYMBOL"].unique())

    jobs = []
    for port_name, port_dict in portfolios.items():
        for period_name, (start, end) in TIME_PERIODS.items():
            tickers = [t for t in port_dict if t in period_tickers[period_name]]
            if not tickers:
                continue
            prices_wide = build_prices_wide(prices_raw, tickers, start, end)
            avail_tickers = [t for t in tickers if t in prices_wide.columns]
            if not avail_tickers:
                continue
            raw_weights = {t: port_dict[t] for t in avail_tickers}
            total_w = sum(raw_weights.values())
            norm_weights = {t: w / total_w for t, w in raw_weights.items()}
            norm_w_list = [norm_weights[t] for t in avail_tickers]

            period_proxy_df = build_proxy_df(avail_tickers, start, end, prices_raw, proxy_full)
            all_needed = set(avail_tickers)
            if not period_proxy_df.empty:
                all_needed |= set(period_proxy_df['lookup_symbol'].unique())
            group_prices = prices_raw[
                prices_raw['TICKERSYMBOL'].isin(all_needed) &
                (prices_raw['PRICEDATE'] >= pd.Timestamp(start)) &
                (prices_raw['PRICEDATE'] <= pd.Timestamp(end))
            ].copy()

            strategies = ([('calendar', f) for f in CALENDAR_FREQS] +
                          [('abs', t) for t in ABS_THRESHOLDS] +
                          [('rel', t) for t in REL_THRESHOLDS])

            for strat_type, strat_val in strategies:
                strat_key = f'{strat_type}_{strat_val}'
                trigger_dates = set()
                threshold_rebal_count = 0
                if strat_type in ('abs', 'rel'):
                    drift_mode = 'Absolute' if strat_type == 'abs' else 'Relative'
                    trigger_dates = _threshold_trigger_dates(
                        prices_wide, avail_tickers, norm_weights, strat_val, drift_mode)
                    threshold_rebal_count = len(trigger_dates & set(prices_wide.index))

                for tlh_on in (False, True):
                    params = dict(
                        prices_df=group_prices, dividends_df=div_df,
                        tickers=avail_tickers, weights=norm_w_list,
                        start_date=start, end_date=end,
                        rebalance_frequency=strat_val if strat_type == 'calendar' else 'None',
                        tax_rates=TAX_RATES,
                        tlh_threshold=TLH_THRESHOLD if tlh_on else 0.0,
                        reinvest_dividends=True, initial_capital=INITIAL_CAPITAL,
                        price_field=PRICE_FIELD, static=False, cost_config=COST_CONFIG,
                        proxy_df=period_proxy_df, wash_sale_days=30,
                        compute_tax_alpha=tlh_on,
                    )
                    if strat_type != 'calendar':
                        params['forced_rebalance_dates'] = trigger_dates
                    meta = dict(port_name=port_name, period_name=period_name,
                                strat_type=strat_type, strat_val=strat_val,
                                strat_key=strat_key, tlh_on=tlh_on,
                                label=strategy_label(strat_type, strat_val, tlh_on),
                                threshold_rebal_count=threshold_rebal_count)
                    jobs.append((params, meta))
    return jobs


def run_jobs(jobs, n_jobs):
    if n_jobs != 1:
        try:
            from joblib import Parallel, delayed
            return Parallel(n_jobs=n_jobs, verbose=5)(
                delayed(_run_sim_safe)(str(REPO_ROOT), p) for p, _ in jobs)
        except ImportError:
            pass
    return [_run_sim_safe(str(REPO_ROOT), p) for p, _ in jobs]


def assemble(jobs, raw_results):
    benchmark_navs = {}
    for (_, meta), raw in zip(jobs, raw_results):
        if raw['ok'] and not meta['tlh_on']:
            benchmark_navs[(meta['port_name'], meta['period_name'], meta['strat_key'])] = \
                raw['res']['nav_series']

    rows, failed = [], []
    for (_, meta), raw in zip(jobs, raw_results):
        run_id = (meta['port_name'], meta['period_name'], meta['label'])
        if not raw['ok']:
            failed.append({'run_id': run_id, 'error': raw['error']})
            continue
        res = raw['res']
        nav_series = res['nav_series']
        rdf = res.get('realized_df', pd.DataFrame())
        tlh_events = int(rdf['reason'].str.startswith('TLH_SELL').sum()) \
            if not rdf.empty and 'reason' in rdf.columns else 0
        tlh_losses = rebal_losses = 0.0
        if not rdf.empty and 'reason' in rdf.columns and 'gain_loss' in rdf.columns:
            is_tlh = rdf['reason'].str.startswith('TLH_SELL')
            is_init = rdf['reason'].str.startswith('INIT')
            tlh_losses = float(rdf.loc[is_tlh & (rdf['gain_loss'] < 0), 'gain_loss'].abs().sum())
            rebal_losses = float(rdf.loc[~is_tlh & ~is_init & (rdf['gain_loss'] < 0), 'gain_loss'].abs().sum())

        extra = {
            'Tax Paid ($)': res.get('tax_paid_total', 0),
            'Losses Harvested ($)': res.get('losses_harvested', 0),
            'TLH Losses ($)': tlh_losses, 'Rebal Losses ($)': rebal_losses,
            'TLH Events': tlh_events, 'Exec Costs ($)': res.get('transaction_costs_total', 0),
            'Tax Alpha 2 ($)': res.get('tax_alpha_2_final', None),
            'Loss CF ST ($)': res.get('loss_carryforward_st', None),
            'Loss CF LT ($)': res.get('loss_carryforward_lt', None),
            'Liquidation NAV ($)': res.get('liquidation_nav', None),
            'Unrealized Gain ST ($)': res.get('unrealized_gain_st', None),
            'Unrealized Gain LT ($)': res.get('unrealized_gain_lt', None),
            'Liquidation Tax ($)': res.get('liquidation_tax', None),
            'Liquidation Exec Cost ($)': res.get('liquidation_exec_cost', None),
        }
        bm_nav = benchmark_navs.get((meta['port_name'], meta['period_name'], meta['strat_key'])) \
            if meta['tlh_on'] else None
        row = {
            'Portfolio': meta['port_name'], 'Period': meta['period_name'],
            'Strategy': meta['label'], 'Strategy Type': meta['strat_type'],
            'Strategy Value': meta['strat_val'],
            'TLH': 'On (10%)' if meta['tlh_on'] else 'Off',
            'Rebal/Threshold': meta['strat_key'],
        }
        row.update(compute_metrics(nav_series, INITIAL_CAPITAL, benchmark_nav=bm_nav))
        row.update(extra)
        rows.append(row)
    return pd.DataFrame(rows), failed


RENAME = {
    'Period': 'Market State', 'Strategy': 'Strategy Label', 'Strategy Type': 'Rebal Type',
    'Strategy Value': 'Rebal Value', 'TLH': 'TLH Status', 'Final NAV ($)': 'Final NAV',
    'Volatility': 'Volatility (Ann)', 'Tracking Error': 'Tracking Error (Ann)',
    'Skewness': 'Return Skewness', 'Kurtosis': 'Return Kurtosis', 'Tax Paid ($)': 'Tax Paid',
    'Losses Harvested ($)': 'Realized Losses (All)', 'TLH Losses ($)': 'TLH Losses',
    'Rebal Losses ($)': 'Rebal Losses', 'TLH Events': 'TLH Event Count',
    'Exec Costs ($)': 'Execution Costs', 'Tax Alpha 2 ($)': 'Tax Alpha 2',
    'Loss CF ST ($)': 'Loss Carryforward ST', 'Loss CF LT ($)': 'Loss Carryforward LT',
    'Liquidation NAV ($)': 'Liquidation NAV', 'Unrealized Gain ST ($)': 'Unrealized Gain ST',
    'Unrealized Gain LT ($)': 'Unrealized Gain LT', 'Liquidation Tax ($)': 'Liquidation Tax',
    'Liquidation Exec Cost ($)': 'Liquidation Exec Cost',
}
CONDITION_MAP = {
    'Bear (2007–2008)': 'Bear Market', 'Baseline (2010–2019)': 'Baseline Market',
    'Bull (2023–2024)': 'Bull Market', 'Past 5Y (2021–2025)': 'Past 5 Years',
    'Past 10Y (2016–2025)': 'Past 10 Years', 'Past 20Y (2006–2025)': 'Past 20 Years',
}
TYPE_MAP = {'calendar': 'Calendar', 'abs': 'Absolute Threshold', 'rel': 'Relative Threshold'}
ORDERED_COLS = [
    'Portfolio', 'Market Condition', 'Market State', 'Rebal Type', 'Rebal Value',
    'TLH Status', 'Strategy Label', 'Final NAV', 'Total Return', 'CAGR',
    'Volatility (Ann)', 'Sharpe Ratio', 'Max Drawdown', 'Return Skewness', 'Return Kurtosis',
    'Tracking Error (Ann)', 'Information Ratio', 'Tax Paid', 'Realized Losses (All)',
    'TLH Losses', 'Rebal Losses', 'TLH Event Count', 'Execution Costs', 'Tax Alpha 2',
    'Loss Carryforward ST', 'Loss Carryforward LT', 'Liquidation NAV', 'Unrealized Gain ST',
    'Unrealized Gain LT', 'Liquidation Tax', 'Liquidation Exec Cost',
]
PERIOD_ORDER = {'Bear Market': 0, 'Baseline Market': 1, 'Bull Market': 2,
                'Past 5 Years': 3, 'Past 10 Years': 4, 'Past 20 Years': 5}


def export(results_df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = results_df.rename(columns=RENAME)
    df['Market Condition'] = df['Market State'].map(CONDITION_MAP).fillna(df['Market State'])
    df['Rebal Type'] = df['Rebal Type'].map(TYPE_MAP).fillna(df['Rebal Type'])
    df = df[[c for c in ORDERED_COLS if c in df.columns]]
    df['_sort'] = df['Market Condition'].map(PERIOD_ORDER).fillna(9)
    df = (df.sort_values(['Portfolio', '_sort', 'Rebal Type', 'Strategy Label', 'TLH Status'])
          .drop(columns=['_sort']).reset_index(drop=True))

    csv_path = out_dir / 'comparative_analysis_results.csv'
    df.to_csv(csv_path, index=False, float_format='%.6f')
    print(f'Wrote {csv_path}  ({df.shape[0]} rows x {df.shape[1]} cols)')

    outputs = out_dir / 'outputs'
    outputs.mkdir(exist_ok=True)
    main_keys = ["40/60 (TA ETF)", "100/0 (TA ETF)", "2-ETF (IVV/EFA)"]
    df[df['Portfolio'].isin(main_keys)].reset_index(drop=True).to_csv(
        outputs / '12_etf_portfolio.csv', index=False, float_format='%.6f')
    df[df['Portfolio'] == "3-ETF (SPY/TLT/GLD)"].reset_index(drop=True).to_csv(
        outputs / '3_etf_test_portfolio.csv', index=False, float_format='%.6f')
    return df


def export_full(results_df, meta, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = results_df.rename(columns=RENAME)
    df['Market Condition'] = df['Market State'].map(CONDITION_MAP).fillna(df['Market State'])
    df['Rebal Type'] = df['Rebal Type'].map(TYPE_MAP).fillna(df['Rebal Type'])
    meta_df = pd.DataFrame.from_dict(meta, orient='index')
    for col in ['Category', 'Model Family', 'Equity Allocation', 'Models Coverage']:
        df[col] = df['Portfolio'].map(meta_df[col]) if col in meta_df else None
    cols = ['Portfolio', 'Category', 'Model Family', 'Equity Allocation', 'Models Coverage'] + \
           [c for c in ORDERED_COLS if c != 'Portfolio']
    df = df[[c for c in cols if c in df.columns]]
    df['_sort'] = df['Market Condition'].map(PERIOD_ORDER).fillna(9)
    df = (df.sort_values(['Portfolio', '_sort', 'Rebal Type', 'Strategy Label', 'TLH Status'])
          .drop(columns=['_sort']).reset_index(drop=True))
    df.to_csv(out_dir / 'full_results.csv', index=False, float_format='%.6f')
    print(f'Wrote full_results.csv ({df.shape[0]} rows, {df["Portfolio"].nunique()} portfolios)')
    outputs = out_dir / 'outputs'
    outputs.mkdir(exist_ok=True)
    for cat, fname in [('Equity-Heavy', 'equity_heavy.csv'), ('Balanced', 'balanced.csv'),
                       ('Fixed Income-Heavy', 'fixed_income_heavy.csv')]:
        sub = df[df['Category'] == cat].reset_index(drop=True)
        sub.to_csv(outputs / fname, index=False, float_format='%.6f')
        print(f'  {fname}: {len(sub)} rows')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default=str(REPO_ROOT / 'data'))
    ap.add_argument('--out-dir', default=str(NOTEBOOK_DIR))
    ap.add_argument('--n-jobs', type=int, default=-1, help='-1 = all cores - 1; 1 = sequential')
    ap.add_argument('--dividends', action='store_true',
                    help='Model dividend reinvestment (DRIP, total-return). Default: price-only.')
    ap.add_argument('--full', action='store_true',
                    help='Sweep every portfolio in Models.xlsx instead of the 4 canonical ones.')
    args = ap.parse_args()

    t0 = time()
    print('Loading inputs ...', flush=True)
    prices_raw, div_df, proxy_full = load_inputs(Path(args.data_dir))
    basis = 'total-return (DRIP)' if args.dividends else 'price-only'
    print(f'  prices: {len(prices_raw):,} rows | dividends: {len(div_df):,} | '
          f'proxies: {len(proxy_full):,} | basis: {basis}', flush=True)
    if not args.dividends:
        div_df = None

    meta = {}
    if args.full:
        portfolios, meta = load_models_portfolios(
            Path(args.data_dir), set(prices_raw['TICKERSYMBOL'].unique()))
        print(f'  full sweep: {len(portfolios)} model portfolios from Models.xlsx', flush=True)
    else:
        portfolios = PORTFOLIOS

    jobs = build_jobs(prices_raw, div_df, proxy_full, portfolios)
    print(f'Prepared {len(jobs)} jobs ({time() - t0:.1f}s). Running ...', flush=True)

    import os
    n_jobs = max(1, (os.cpu_count() or 2) - 1) if args.n_jobs == -1 else args.n_jobs
    t1 = time()
    raw_results = run_jobs(jobs, n_jobs)
    print(f'Simulations done in {time() - t1:.1f}s', flush=True)

    results_df, failed = assemble(jobs, raw_results)
    print(f'Assembled {len(results_df)} rows, {len(failed)} failed', flush=True)
    for f in failed[:10]:
        print(f'  FAILED {f["run_id"]}: {f["error"]}', flush=True)

    if args.full:
        export_full(results_df, meta, Path(args.out_dir))
    else:
        export(results_df, Path(args.out_dir))
    print(f'\nDone in {time() - t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
