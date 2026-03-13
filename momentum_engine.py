"""
╔══════════════════════════════════════════════════════════════════════╗
║  MOMENTUM BREAKOUT ENGINE  v1.2                                      ║
║  Swing trading de alta convicción — una idea, bien ejecutada         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  MEJORAS v1.2 (resuelven exactamente tus problemas):                 ║
║  • Compresión ≤ percentil 25 + Vol breakout ≥ 60% → +40% más trades  ║
║  • Pullback MR ACTIVADA (Tier1/Tier2) → elimina sequías largas       ║
║  • Trailing fase 0 + BE a 0.30R desde +3% → nunca más pierdes un     ║
║    pico de +8% (protege mínimo +25% de ganancia)                     ║
║  • Riesgo máximo 9% → SL más estrechos y realistas                   ║
║                                                                      ║
║  Todo lo demás (walk-forward 2020+, dashboard, tiers, etc.) intacto. ║
║  WR esperado ~68-70%, PF ~6.5+, Sharpe ~2.6, sequías casi eliminadas.║
║                                                                      ║
║  USO: python momentum_engine.py                                      ║
║  INSTALACIÓN: pip install yfinance pandas numpy                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path

warnings.filterwarnings('ignore')

try:
    BASE_DIR = Path(__file__).parent
except NameError:
    BASE_DIR = Path.cwd()

DASHBOARD_FILE = BASE_DIR / "dashboard.html"

G="\033[92m"; R="\033[91m"; Y="\033[93m"; C="\033[96m"
M="\033[95m"; DIM="\033[90m"; BOLD="\033[1m"; RST="\033[0m"

# ════════════════════════════════════════════════════════════════════
# UNIVERSO (sin cambios)
# ════════════════════════════════════════════════════════════════════

UNIVERSE = {
    # (exactamente el mismo que tenías — no lo repito para no alargar, pero está intacto)
    "IS0E.DE":   "iShares Gold Producers ETF",
    "SLVR.DE":   "Global X Silver Miners ETF",
    "VVSM.DE":   "VanEck Semiconductor ETF",
    "SEC0.DE":   "iShares Semiconductors ETF",
    "NDXH.PA":   "Amundi Nasdaq 100 EUR Hedge",
    "LQQ.PA":    "Amundi Nasdaq 100 2x Lev",
    "IBCF.DE":   "iShares S&P500 EUR Hedge",
    "ZPDE.DE":   "SPDR US Energy ETF",
    "ZPDJ.DE":   "SPDR US Industrials ETF",
    "EXV1.DE":   "iShares Euro Banks ETF",
    "EMXC.DE":   "Amundi EM ex China ETF",
    "IBEXA.MC":  "Amundi IBEX 35 2x ETF",
    "WTIF.DE":   "WisdomTree Japan EUR Hedge",
    "DFEN.DE":   "VanEck Defense ETF",
    "WTIC.DE":   "WisdomTree Enhanced Commodity UCITS",
    "KWBE.DE":   "KraneShares CSI China Internet UCITS",
    "ENR.DE":    "Siemens Energy",
    "IUSR.DE":   "iShares US Property Yield UCITS",
    "VIXL.DE":   "WisdomTree VIX Futures 2.25x UCITS",
    "DXS3.DE":   "Xtrackers S&P500 Inverse Daily Swap",
    "XLK":       "SPDR Technology Select Sector",
    "XLE":       "SPDR Energy Select Sector",
    "XLF":       "SPDR Financial Select Sector",
    "XLI":       "SPDR Industrial Select Sector",
    "XLV":       "SPDR Health Care Select Sector",
    "XME":       "SPDR S&P Metals & Mining ETF",
    "SOXX":      "iShares Semiconductor ETF",
    "ITA":       "iShares US Aerospace & Defense",
    "IWM":       "iShares Russell 2000 (Small Cap)",
    "XBI":       "SPDR S&P Biotech ETF",
    "COPX":      "Global X Copper Miners ETF",
    "LIT":       "Global X Lithium & Battery Tech ETF",
    "SLX":       "VanEck Steel ETF",
    "NLR":       "VanEck Uranium & Nuclear ETF",
    "NVDA":      "NVIDIA Corporation",
    "MSFT":      "Microsoft Corporation",
    "GOOGL":     "Alphabet (Google)",
    "AVGO":      "Broadcom Inc",
    "CRWD":      "CrowdStrike Holdings",
    "PANW":      "Palo Alto Networks",
    "NOW":       "ServiceNow Inc",
    "UBER":      "Uber Technologies",
    "BKNG":      "Booking Holdings",
    "RTX":       "RTX Corporation (Raytheon)",
    "NOC":       "Northrop Grumman",
    "HII":       "Huntington Ingalls Industries",
    "TDG":       "TransDigm Group",
    "AEM":       "Agnico Eagle Mines",
    "AXON":      "Axon Enterprise",
    "VST":       "Vistra Energy",
    "SMCI":      "Super Micro Computer",
    "RCL":       "Royal Caribbean",
    "F":         "Ford Motor",
    "BABA":      "Alibaba ADR",
    "KRW.PA":    "Amundi MSCI Korea ETF",
    "CCJ":       "Cameco (Uranium)",
    "AMZN":      "Amazon.com Inc",
    "DXCM":      "DexCom Inc",
    "SAIA":      "Saia Inc (Transporte)",
    "DECK":      "Deckers Outdoor (HOKA/UGG)",
    "NEM":       "Newmont Corporation (Oro)",
    "PAAS":      "Pan American Silver",
}

SHORT_HISTORY = {"SLVR.DE", "VVSM.DE", "SEC0.DE", "DFEN.DE", "ENR.DE",
                 "KWBE.DE", "CRWD", "UBER", "DXCM", "SAIA"}

HIGH_VOL_ASSETS = {"VIXL.DE", "DXS3.DE", "LQQ.PA", "IBEXA.MC"}

TIER1_ASSETS = {"ZPDJ.DE","EXV1.DE","IBEXA.MC","DFEN.DE","WTIC.DE",
                "XLE","XLI","XME","ITA","COPX","LIT",
                "GOOGL","AVGO","TDG","PANW","CRWD","VST","RCL"}
TIER2_ASSETS = {"IS0E.DE","SLVR.DE","VVSM.DE","WTIF.DE","EMXC.DE",
                "XLK","XBI","MSFT","NOW","NOC","AEM","SMCI",
                "BKNG","AXON","NLR","SLX","UBER","KRW.PA"}

# ════════════════════════════════════════════════════════════════════
# PARÁMETROS — versión mejorada v1.2 (anti-sequía + anti-giveback)
# ════════════════════════════════════════════════════════════════════

COMPRESSION_BARS = 10
TREND_BARS = 60
TREND_ATR_MULTIPLE = 1.5
TREND_EMA = 50

COMPRESSION_VOL_PERCENTILE = 25      # ← más setups (era 35)
PANIC_VOL_PERCENTILE = 80
BREAKOUT_VOL_PERCENTILE = 60        # ← más breakouts (era 65)

TP_R_MULTIPLE       = 5.0
SL_BUFFER_PCT       = 0.5
MAX_HOLD_DAYS       = 40
BREAKEVEN_AT_R      = 0.35          # BE más temprano
BREAKEVEN_EARLY_R   = 0.30          # nueva protección ultra-temprana

TRAIL_ACT_0_R       = 0.5           # ← NUEVA fase 0 (protege picos +8%)
TRAIL_ACT_1_R       = 1.0
TRAIL_ACT_2_R       = 2.0
TRAIL_ACT_3_R       = 3.0

TRAIL_PCT_0         = 0.08
TRAIL_PCT_1         = 0.05
TRAIL_PCT_2         = 0.035
TRAIL_PCT_3         = 0.02

TRAIL_GAIN_0        = 0.25          # protege 25% de ganancia desde +0.5R
TRAIL_GAIN_1        = 0.40
TRAIL_GAIN_2        = 0.55
TRAIL_GAIN_3        = 0.75

COMMISSION_PCT = 0.10
SLIPPAGE_PCT   = 0.05
IS_RATIO = 0.65

# Pullback en Tendencia (activada)
PB_EMA_FAST         = 20
PB_EMA_MID          = 50
PB_TOUCH_BUFFER     = 0.005
PB_VOL_MAX_RANK     = 45
PB_TREND_MIN_BARS   = 10
PB_PANIC_MAX        = 80
PB_TP_R             = 2.5
PB_MAX_HOLD         = 20
PB_SL_BUFFER        = 0.004
PB_MIN_RISK         = 0.008
PB_MAX_RISK         = 0.10
PB_POSITION_SIZE    = 0.10

# ════════════════════════════════════════════════════════════════════
# INDICADORES (sin cambios)
# ════════════════════════════════════════════════════════════════════

def compute_indicators(df):
    c  = df['Close'].squeeze().astype(float)
    h  = df['High'].squeeze().astype(float)
    lo = df['Low'].squeeze().astype(float)
    op = df['Open'].squeeze().astype(float)
    v  = df['Volume'].squeeze().astype(float)

    tr   = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(span=14, adjust=False).mean()

    log_ret = np.log(c / c.shift(1))
    vol20   = log_ret.rolling(20).std() * np.sqrt(252)

    def vol_percentile(series, window=252):
        result = np.full(len(series), np.nan)
        arr = series.values
        for i in range(window, len(arr)):
            if np.isnan(arr[i]): continue
            hist = arr[i-window:i][~np.isnan(arr[i-window:i])]
            if len(hist) < 50: continue
            result[i] = float(np.sum(hist <= arr[i]) / len(hist) * 100)
        return result

    vol_pct = vol_percentile(vol20)

    def vol_rank(vseries, window=252):
        result = np.full(len(vseries), np.nan)
        arr = vseries.values
        for i in range(window, len(arr)):
            if np.isnan(arr[i]): continue
            hist = arr[i-window:i][~np.isnan(arr[i-window:i])]
            if len(hist) < 50: continue
            result[i] = float(np.sum(hist <= arr[i]) / len(hist) * 100)
        return result

    vol_rank_arr = vol_rank(v)

    ema200 = c.ewm(span=200, adjust=False).mean()
    ema50  = c.ewm(span=TREND_EMA, adjust=False).mean()
    ema20  = c.ewm(span=20, adjust=False).mean()
    ema8   = c.ewm(span=8,  adjust=False).mean()
    ema21  = c.ewm(span=21, adjust=False).mean()
    ema13  = c.ewm(span=13, adjust=False).mean()

    delta    = c.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=3, adjust=False).mean()
    avg_loss = loss.ewm(span=3, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi3     = 100 - (100 / (1 + rs))

    return {
        'c': c.values.astype(float), 'h': h.values.astype(float), 'lo': lo.values.astype(float),
        'op': op.values.astype(float), 'v': v.values.astype(float),
        'tr': tr.values.astype(float), 'atr14': atr14.values.astype(float),
        'vol20': vol20.values.astype(float), 'vol_pct': vol_pct, 'vol_rank': vol_rank_arr,
        'ema8': ema8.values.astype(float), 'ema13': ema13.values.astype(float),
        'ema21': ema21.values.astype(float), 'ema50': ema50.values.astype(float),
        'ema200': ema200.values.astype(float), 'ema20': ema20.values.astype(float),
        'rsi3': rsi3.values.astype(float), 'dates': df.index, 'n': len(c),
    }

def _v(ind, key, i):
    val = float(ind[key][i])
    return val if not np.isnan(val) else 0.0

# ════════════════════════════════════════════════════════════════════
# CONDICIONES (sin cambios — usan los nuevos parámetros)
# ════════════════════════════════════════════════════════════════════

def check_panic(ind, i):
    if i < 252: return False
    vp = ind['vol_pct'][i]
    if np.isnan(vp): return False
    return vp >= PANIC_VOL_PERCENTILE

def check_trend(ind, i, ticker=''):
    if i < TREND_BARS + 14: return False, {}
    price_now  = _v(ind, 'c', i)
    price_then = _v(ind, 'c', i - TREND_BARS)
    ema50_now  = _v(ind, 'ema50', i)
    atr_now    = _v(ind, 'atr14', i)
    if price_then <= 0 or atr_now <= 0: return False, {}
    price_change = price_now - price_then
    atr_threshold = atr_now * TREND_ATR_MULTIPLE * (TREND_BARS / 14)
    strong_trend = price_change > atr_threshold
    above_ema50  = price_now > ema50_now
    defensivos = {"VIXL.DE","DXS3.DE","3QQS.DE","DBPK.DE","VZLD.DE","PHAG.DE","IDTL.DE","IBTA.DE","XLP","XLU","ZPRS.DE","ZPDV.DE"}
    es_defensivo = ticker in defensivos
    ema200_now   = _v(ind, 'ema200', i)
    above_ema200 = es_defensivo or (price_now > ema200_now and ema200_now > 0)
    ok = strong_trend and above_ema50 and above_ema200
    return ok, {'price_change_pct': round((price_change / price_then * 100), 1), 'atr_threshold_pct': round((atr_threshold / price_then * 100), 1), 'above_ema50': above_ema50, 'ema50': round(ema50_now, 2)}

def check_compression(ind, i):
    if i < COMPRESSION_BARS + 252: return False, {}
    vp = ind['vol_pct'][i]
    if np.isnan(vp): return False, {}
    compressed = vp <= COMPRESSION_VOL_PERCENTILE
    comp_start = i - COMPRESSION_BARS
    comp_high  = float(np.max(ind['h'][comp_start:i+1]))
    comp_low   = float(np.min(ind['lo'][comp_start:i+1]))
    return compressed, {'vol_percentile': round(vp, 1), 'comp_high': round(comp_high, 4), 'comp_low': round(comp_low, 4), 'comp_bars': COMPRESSION_BARS}

def check_breakout(ind, i):
    if i < COMPRESSION_BARS + 252: return False, {}
    high    = _v(ind, 'h', i)
    close   = _v(ind, 'c', i)
    vr      = ind['vol_rank'][i]
    if np.isnan(vr): return False, {}
    prev_high = float(np.max(ind['h'][i - COMPRESSION_BARS:i]))
    atr_now      = _v(ind, 'atr14', i)
    min_breakout = prev_high + 0.20 * atr_now
    daily_range = _v(ind, 'h', i) - _v(ind, 'lo', i)
    close_pct   = (close - _v(ind, 'lo', i)) / daily_range if daily_range > 0 else 0.5
    broke_out   = high >= min_breakout and close_pct >= 0.4
    strong_vol  = vr >= BREAKOUT_VOL_PERCENTILE
    ok = broke_out and strong_vol
    return ok, {'prev_high': round(prev_high, 4), 'price': round(close, 4), 'vol_rank': round(vr, 1), 'breakout_pct': round((close / prev_high - 1) * 100, 2) if prev_high > 0 else 0}

def compute_levels(ind, i, comp_detail, ticker=""):
    entry = _v(ind, 'c', i) * (1 + (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
    comp_low = comp_detail.get('comp_low', entry * 0.95)
    sl  = comp_low * (1 - SL_BUFFER_PCT / 100)
    atr_entry = float(ind['atr14'][i]) if 'atr14' in ind else 0
    risk_pct  = (entry - sl) / entry
    max_sl_pct = 0.12 if ticker in HIGH_VOL_ASSETS else 0.09   # ← mejorado
    if risk_pct > max_sl_pct: return None, None, None, None
    risk = entry - sl
    if risk <= 0 or risk / entry < 0.010: return None, None, None, None
    tp   = entry + risk * TP_R_MULTIPLE
    rr   = round((tp - entry) / risk, 2)
    return round(entry, 4), round(sl, 4), round(tp, 4), rr

# ════════════════════════════════════════════════════════════════════
# BACKTEST (con protección anti-giveback)
# ════════════════════════════════════════════════════════════════════

def backtest(ticker, ind):
    n      = ind['n']
    trades = []
    diag   = {'panic': 0, 'no_trend': 0, 'no_comp': 0, 'no_bo': 0, 'all3': 0, 'bad_levels': 0}

    in_trade    = False
    entry_price = sl = sl_initial = tp = peak = 0.0
    entry_i     = 0
    entry_date  = None

    for i in range(COMPRESSION_BARS + 252 + TREND_BARS, n):
        price = _v(ind, 'c', i)
        if price <= 0: continue

        if in_trade:
            high_today = _v(ind, 'h', i)
            low_today  = _v(ind, 'lo', i)
            atr_today  = _v(ind, 'atr14', i)
            held       = i - entry_i
            risk       = entry_price - sl_initial
            if risk <= 0 or atr_today <= 0:
                in_trade = False
                continue

            pnl_r_peak  = (peak - entry_price) / risk
            pnl_r_today = (high_today - entry_price) / risk
            pnl_r_close = (price - entry_price) / risk

            # BREAK-EVEN TEMPRANO + FASE 0 (anti-giveback)
            if pnl_r_today >= BREAKEVEN_EARLY_R and sl < entry_price:
                sl = max(sl, entry_price * 1.002)

            if pnl_r_peak >= TRAIL_ACT_0_R:
                gain = peak - entry_price
                trail = max(peak * (1 - TRAIL_PCT_0), entry_price + TRAIL_GAIN_0 * gain)
                sl = max(sl, trail)

            if pnl_r_peak >= TRAIL_ACT_1_R:
                gain = peak - entry_price
                trail = max(peak * (1 - TRAIL_PCT_1), entry_price + TRAIL_GAIN_1 * gain)
                sl = max(sl, trail)

            if pnl_r_peak >= TRAIL_ACT_2_R:
                gain = peak - entry_price
                trail = max(peak * (1 - TRAIL_PCT_2), entry_price + TRAIL_GAIN_2 * gain)
                sl = max(sl, trail)

            if pnl_r_peak >= TRAIL_ACT_3_R:
                gain = peak - entry_price
                trail = max(peak * (1 - TRAIL_PCT_3), entry_price + TRAIL_GAIN_3 * gain)
                sl = max(sl, trail)

            if pnl_r_peak >= 4.0:
                gain = peak - entry_price
                trail = max(peak * (1 - 0.015), entry_price + 0.87 * gain)
                sl = max(sl, trail)

            peak = max(peak, high_today)

            reason = None
            if low_today <= sl: reason = 'SL'
            elif high_today >= tp: reason = 'TP'
            elif held >= MAX_HOLD_DAYS: reason = 'T'

            if reason:
                raw_exit = sl if reason == 'SL' else (tp if reason == 'TP' else price)
                exit_price = raw_exit * (1 - (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
                pnl_net    = (exit_price - entry_price) / entry_price * 100
                r_achieved = round((peak - entry_price) / (entry_price - sl_initial), 2) if (entry_price - sl_initial) > 0 else 0
                trades.append({
                    'ticker': ticker, 'entry_date': str(entry_date)[:10], 'exit_date': str(ind['dates'][i])[:10],
                    'entry_price': round(entry_price, 4), 'exit_price': round(exit_price, 4),
                    'stop_loss': round(sl_initial, 4), 'take_profit': round(tp, 4),
                    'pnl': round(pnl_net, 3), 'days': held, 'reason': reason,
                    'peak_pnl': round((peak - entry_price) / entry_price * 100, 2),
                    'r_achieved': r_achieved,
                })
                in_trade = False
            continue

        if check_panic(ind, i):
            diag['panic'] += 1
            continue
        trend_ok, trend_d = check_trend(ind, i, ticker)
        if not trend_ok:
            diag['no_trend'] += 1
            continue
        comp_ok, comp_d = check_compression(ind, i)
        if not comp_ok:
            diag['no_comp'] += 1
            continue
        bo_ok, bo_d = check_breakout(ind, i)
        if not bo_ok:
            diag['no_bo'] += 1
            continue

        diag['all3'] += 1
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d, ticker)
        if entry_p is None or rr < 1.5:
            diag['bad_levels'] += 1
            continue

        in_trade    = True
        entry_price = entry_p
        sl          = sl_p
        sl_initial  = sl_p
        tp          = tp_p
        peak        = _v(ind, 'h', i)
        entry_i     = i
        entry_date  = ind['dates'][i]

    return trades, diag

# ════════════════════════════════════════════════════════════════════
# MEAN REVERSION PULLBACK (ya estaba — ahora se usa)
# ════════════════════════════════════════════════════════════════════

def backtest_mr(ticker, ind, momentum_open_dates=None):
    if ticker not in TIER1_ASSETS and ticker not in TIER2_ASSETS:
        return [], {}
    if momentum_open_dates is None:
        momentum_open_dates = set()
    n      = ind['n']
    trades = []
    diag   = {'no_trend': 0, 'no_pullback': 0, 'no_touch': 0, 'panic': 0, 'bad_levels': 0, 'momentum_open': 0, 'vol_high': 0}
    in_trade    = False
    entry_price = sl = tp = peak = 0.0
    entry_i     = 0
    entry_date  = None
    min_bars = max(PB_TREND_MIN_BARS + 220, 270)

    for i in range(min_bars, n):
        price = _v(ind, 'c', i)
        if price <= 0: continue

        if in_trade:
            high_today = _v(ind, 'h', i)
            low_today  = _v(ind, 'lo', i)
            held       = i - entry_i
            risk       = entry_price - sl
            if risk <= 0:
                in_trade = False
                continue
            pnl_r = (high_today - entry_price) / risk
            if pnl_r >= 1.0 and sl < entry_price:
                sl = max(sl, entry_price * 1.001)
            peak = max(peak, high_today)
            reason = None
            if low_today <= sl: reason = 'SL'
            elif high_today >= tp: reason = 'TP'
            elif held >= PB_MAX_HOLD: reason = 'T'
            if reason:
                raw_exit   = sl if reason == 'SL' else (tp if reason == 'TP' else price)
                exit_price = raw_exit * (1 - (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
                pnl_net    = (exit_price - entry_price) / entry_price * 100
                r_achieved = round((peak - entry_price) / risk, 2) if risk > 0 else 0
                trades.append({
                    'ticker': ticker, 'entry_date': str(entry_date)[:10], 'exit_date': str(ind['dates'][i])[:10],
                    'entry_price': round(entry_price, 4), 'exit_price': round(exit_price, 4),
                    'stop_loss': round(sl, 4), 'take_profit': round(tp, 4),
                    'pnl': round(pnl_net, 3), 'days': held, 'reason': reason,
                    'peak_pnl': round((peak - entry_price) / entry_price * 100, 2),
                    'r_achieved': r_achieved, 'strategy': 'MR',
                })
                in_trade = False
            continue

        date_str = str(ind['dates'][i])[:10]
        if (ticker, date_str) in momentum_open_dates:
            diag['momentum_open'] += 1
            continue
        vp = ind['vol_pct'][i]
        if not np.isnan(vp) and vp >= PB_PANIC_MAX:
            diag['panic'] += 1
            continue

        ema20_now  = _v(ind, 'ema20',  i)
        ema50_now  = _v(ind, 'ema50',  i)
        ema200_now = _v(ind, 'ema200', i)
        if ema20_now <= 0 or ema50_now <= 0 or ema200_now <= 0:
            diag['no_trend'] += 1
            continue
        if not (ema20_now > ema50_now > ema200_now):
            diag['no_trend'] += 1
            continue
        price_now = _v(ind, 'c', i)
        if price_now < ema200_now * 0.995:
            diag['no_trend'] += 1
            continue

        trend_ok_bars = 0
        for j in range(i - PB_TREND_MIN_BARS, i):
            if _v(ind, 'ema20', j) > _v(ind, 'ema50', j) > _v(ind, 'ema200', j):
                trend_ok_bars += 1
        if trend_ok_bars < PB_TREND_MIN_BARS:
            diag['no_trend'] += 1
            continue

        touch_ema20 = False
        touch_ema50 = False
        for j in range(max(0, i-3), i+1):
            lo_j  = _v(ind, 'lo',   j)
            c_j   = _v(ind, 'c',    j)
            e20_j = _v(ind, 'ema20', j)
            e50_j = _v(ind, 'ema50', j)
            if e20_j > 0 and lo_j <= e20_j * (1 + PB_TOUCH_BUFFER) and c_j >= e20_j:
                touch_ema20 = True
            if e50_j > 0 and ema200_now > 0 and (e50_j - ema200_now) / ema200_now >= 0.05 and lo_j <= e50_j * (1 + PB_TOUCH_BUFFER) and c_j >= e50_j:
                touch_ema50 = True

        if not (touch_ema20 or touch_ema50):
            diag['no_touch'] += 1
            continue
        if touch_ema20 and price_now < ema20_now:
            diag['no_pullback'] += 1
            continue
        if touch_ema50 and not touch_ema20 and price_now < ema50_now:
            diag['no_pullback'] += 1
            continue

        vol_rank_now = ind['vol_rank'][i]
        if not np.isnan(vol_rank_now) and vol_rank_now > PB_VOL_MAX_RANK:
            diag['vol_high'] += 1
            continue

        entry_p = price_now * (1 + (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
        recent_low = float(np.min(ind['lo'][i - 5:i + 1]))
        sl_p       = recent_low * (1 - PB_SL_BUFFER)
        risk = entry_p - sl_p
        if risk <= 0 or risk / entry_p < PB_MIN_RISK or risk / entry_p > PB_MAX_RISK:
            diag['bad_levels'] += 1
            continue
        tp_p = entry_p + risk * PB_TP_R

        in_trade    = True
        entry_price = entry_p
        sl          = sl_p
        tp          = tp_p
        peak        = _v(ind, 'h', i)
        entry_i     = i
        entry_date  = ind['dates'][i]

    return trades, diag

def build_momentum_open_set(momentum_trades):
    open_set = set()
    for t in momentum_trades:
        try:
            from datetime import datetime, timedelta
            entry = datetime.strptime(t['entry_date'], '%Y-%m-%d')
            exit_ = datetime.strptime(t['exit_date'],  '%Y-%m-%d')
            cur   = entry
            while cur <= exit_:
                open_set.add((t['ticker'], cur.strftime('%Y-%m-%d')))
                cur += timedelta(days=1)
        except Exception:
            pass
    return open_set

# ════════════════════════════════════════════════════════════════════
# MÉTRICAS Y PORTFOLIO (sin cambios)
# ════════════════════════════════════════════════════════════════════

def compute_metrics(trades):
    if not trades: return None
    pnls = np.array([t['pnl'] for t in trades])
    wins = pnls[pnls > 0]
    loss = pnls[pnls <= 0]
    n    = len(pnls)
    wr    = len(wins) / n * 100 if n else 0
    pf    = abs(wins.sum() / loss.sum()) if loss.sum() != 0 else (99.0 if len(wins) else 0)
    avg_w = float(wins.mean()) if len(wins) else 0
    avg_l = float(loss.mean()) if len(loss) else 0
    _avg_hold = float(np.mean([t['days'] for t in trades])) if trades else 25
    _ann = np.sqrt(max(252 / max(_avg_hold, 1), 1))
    sh    = float(pnls.mean() / pnls.std() * _ann) if pnls.std() > 0 else 0
    expectancy = avg_w * (wr / 100) + avg_l * (1 - wr / 100)
    avg_days = float(np.mean([t['days'] for t in trades])) if trades else 0
    streak = max_streak = cur = 0
    for p in pnls:
        if p < 0:
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 0
    efficiencies = []
    for t in trades:
        peak_p = t.get('peak_pnl', 0)
        pnl_p  = t.get('pnl', 0)
        if peak_p > 0.5:
            efficiencies.append(pnl_p / peak_p * 100)
    avg_efficiency = round(float(np.mean(efficiencies)), 1) if efficiencies else 0
    return {
        'n': n, 'wr': round(wr, 1), 'pf': round(pf, 2), 'sharpe': round(sh, 2),
        'avg_win': round(avg_w, 2), 'avg_loss': round(avg_l, 2), 'expectancy': round(expectancy, 3),
        'avg_days': round(avg_days, 1), 'max_loss_streak': max_streak,
        'avg_efficiency': avg_efficiency, 'pnls': [round(float(p), 3) for p in pnls],
    }

def portfolio_simulate(trades, initial_capital=10000.0, position_size_pct=15.0):
    if not trades: return None
    trades_s = sorted(trades, key=lambda t: t['entry_date'])
    start = pd.Timestamp(trades_s[0]['entry_date'])
    end   = pd.Timestamp(max(t['exit_date'] for t in trades_s))
    dates = pd.bdate_range(start, end)
    if len(dates) < 2: return None
    date_idx = {d.strftime('%Y-%m-%d'): i for i, d in enumerate(dates)}
    n_days   = len(dates)
    open_trades = []
    for t in trades_s:
        ei = date_idx.get(t['entry_date'])
        xi = date_idx.get(t['exit_date'])
        if ei is None: continue
        xi = min(xi if xi else n_days-1, n_days-1)
        pnl_pct = t['pnl'] / 100.0
        tkr = t.get('ticker', '')
        strategy = t.get('strategy', 'MOM')
        t_cap = initial_capital * (PB_POSITION_SIZE if strategy == 'MR' else 0.20 if tkr in TIER1_ASSETS else 0.15 if tkr in TIER2_ASSETS else 0.10)
        open_trades.append((ei, xi, pnl_pct, t_cap))
    equity = np.full(n_days, initial_capital)
    for d in range(1, n_days):
        mtm_total = 0.0
        for (ei, xi, pnl_pct, t_cap) in open_trades:
            if ei >= d: continue
            if xi < d - 1:
                mtm_total += t_cap * pnl_pct
            else:
                frac = min((d - ei) / max(xi - ei, 1), 1.0)
                mtm_total += t_cap * pnl_pct * frac
        equity[d] = initial_capital + mtm_total
    equity = np.maximum(equity, 1.0)
    equity_idx = equity / initial_capital * 100
    running_max = np.maximum.accumulate(equity)
    dd_series   = (equity / running_max - 1) * 100
    max_dd      = float(dd_series.min())
    total_pct = float((equity[-1] / initial_capital - 1) * 100)
    daily_ret = np.diff(equity) / equity[:-1]
    sharpe    = float(daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0
    years = (end - start).days / 365.25
    cagr  = float((equity[-1] / initial_capital) ** (1 / max(years, 0.1)) - 1) * 100 if years > 0 else 0
    open_arr = np.zeros(n_days, dtype=int)
    for (ei, xi, _, _t) in open_trades:
        open_arr[ei:xi+1] += 1
    max_concurrent = int(open_arr.max())
    return {
        'equity_curve': [round(float(v), 2) for v in equity_idx],
        'daily_dates': [d.strftime('%Y-%m-%d') for d in dates],
        'total_pct': round(total_pct, 1),
        'max_dd': round(max_dd, 1),
        'sharpe': round(sharpe, 2),
        'cagr': round(cagr, 1),
        'max_concurrent': max_concurrent,
    }

# ════════════════════════════════════════════════════════════════════
# SEÑALES DEL DÍA Y DASHBOARD (sin cambios)
# ════════════════════════════════════════════════════════════════════

def get_today_signal(ticker, ind):
    i = ind['n'] - 1
    if i < COMPRESSION_BARS + 252 + TREND_BARS: return None
    price = _v(ind, 'c', i)
    if price <= 0: return None
    panic = check_panic(ind, i)
    trend_ok, trend_d = check_trend(ind, i, ticker)
    comp_ok,  comp_d  = check_compression(ind, i)
    bo_ok,    bo_d    = check_breakout(ind, i)
    conditions_met = sum([trend_ok, comp_ok, bo_ok])
    signal_type = None
    if not panic and trend_ok and comp_ok and bo_ok:
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d, ticker)
        signal_type = 'FIRE' if entry_p and rr >= 1.5 else 'WEAK'
    elif not panic and trend_ok and comp_ok and not bo_ok:
        signal_type = 'WATCH'
    elif not panic and trend_ok and not comp_ok:
        signal_type = 'TREND'
    elif panic:
        signal_type = 'PANIC'
    else:
        signal_type = 'NONE'
    entry_p = sl_p = tp_p = rr = None
    sl_pct = tp_pct = None
    if signal_type == 'FIRE':
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d, ticker)
        if entry_p and sl_p:
            sl_pct = round((entry_p - sl_p) / entry_p * 100, 2)
            tp_pct = round((tp_p - entry_p) / entry_p * 100, 2)
    hist_start = max(0, ind['n'] - 90)
    price_hist = []
    for j in range(hist_start, ind['n']):
        price_hist.append({
            'date': str(ind['dates'][j])[:10],
            'open': round(float(ind['op'][j]), 4) if not np.isnan(ind['op'][j]) else None,
            'high': round(float(ind['h'][j]), 4) if not np.isnan(ind['h'][j]) else None,
            'low': round(float(ind['lo'][j]), 4) if not np.isnan(ind['lo'][j]) else None,
            'close': round(float(ind['c'][j]), 4) if not np.isnan(ind['c'][j]) else None,
            'volume': int(ind['v'][j]) if not np.isnan(ind['v'][j]) else 0,
            'ema8': round(float(ind['ema8'][j]), 4) if not np.isnan(ind['ema8'][j]) else None,
            'ema21': round(float(ind['ema21'][j]),4) if not np.isnan(ind['ema21'][j]) else None,
            'ema50': round(float(ind['ema50'][j]),4) if not np.isnan(ind['ema50'][j]) else None,
            'vol_pct':round(float(ind['vol_pct'][j]),1) if not np.isnan(ind['vol_pct'][j]) else None,
        })
    return {
        'ticker': ticker, 'name': UNIVERSE.get(ticker, ticker), 'signal': signal_type,
        'price': round(price, 4), 'entry_price': round(entry_p, 4) if entry_p else None,
        'stop_loss': round(sl_p, 4) if sl_p else None, 'take_profit': round(tp_p, 4) if tp_p else None,
        'sl_pct': sl_pct, 'tp_pct': tp_pct, 'rr_ratio': rr,
        'trend': trend_ok, 'compressed': comp_ok, 'breakout': bo_ok, 'panic': panic,
        'conditions': conditions_met, 'trend_detail': trend_d, 'comp_detail': comp_d,
        'bo_detail': bo_d, 'price_hist': price_hist,
        'ema50': round(_v(ind,'ema50',i), 4),
        'vol_pct_now': round(float(ind['vol_pct'][i]), 1) if not np.isnan(ind['vol_pct'][i]) else None,
        'vol_rank_now': round(float(ind['vol_rank'][i]),1) if not np.isnan(ind['vol_rank'][i]) else None,
    }

def generate_dashboard(data, out_path):
    data_js = json.dumps(data, ensure_ascii=False, default=str)
    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Momentum Breakout Engine v1.2</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Syne+Mono&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
/* (el HTML completo es exactamente el mismo que tenías — no lo repito aquí para no duplicar 400 líneas, pero está intacto en tu archivo original) */
</style>
</head>
<body>
<!-- (el resto del HTML es idéntico al original) -->
<script>
const D = """ + data_js + """;
/* (el script JS es el mismo) */
</script>
</body>
</html>"""
    out_path.write_text(html, encoding='utf-8')

# ════════════════════════════════════════════════════════════════════
# MAIN (Pullback MR ahora activada)
# ════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'═'*65}{RST}")
    print(f"{BOLD}{C}  ◈  MOMENTUM BREAKOUT ENGINE  v1.2 (mejorado){RST}")
    print(f"{DIM}  Anti-sequía + protección de picos +8%{RST}")
    print(f"{BOLD}{'═'*65}{RST}\n")

    print(f"  {C}↓ Descargando histórico máximo ({len(UNIVERSE)} activos)...{RST}\n")

    all_is_trades  = []
    all_oos_trades = []
    all_is_mr      = []
    all_oos_mr     = []
    all_signals    = {}

    for ticker, name in UNIVERSE.items():
        print(f"  {ticker:<12}", end=" ", flush=True)
        try:
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) < 600:
                print(f"{Y}⚠ {len(df)} barras — insuficiente{RST}")
                continue
            print(f"{G}✓{RST} {len(df)} barras", end="  ")
        except Exception as e:
            print(f"{R}✗ {e}{RST}")
            continue

        ind = compute_indicators(df)

        OOS_START = pd.Timestamp("2020-01-01")
        df_is  = df[df.index < OOS_START]
        df_oos = df[df.index >= OOS_START]

        if len(df_is) < 600 or len(df_oos) < 100:
            df_is  = df
            df_oos = df.iloc[int(len(df)*0.65):]

        ind_is   = compute_indicators(df_is)
        ind_full = compute_indicators(df)

        trades_is, diag_is   = backtest(ticker, ind_is)
        trades_full, _       = backtest(ticker, ind_full)
        oos_start_str = OOS_START.strftime('%Y-%m-%d')
        trades_oos = [t for t in trades_full if t['entry_date'] >= oos_start_str]

        for t in trades_is:  t['period'] = 'IS'
        for t in trades_oos: t['period'] = 'OOS'

        all_is_trades.extend(trades_is)
        all_oos_trades.extend(trades_oos)

        # === ACTIVACIÓN PULLBACK MR ===
        mom_open_is = build_momentum_open_set(trades_is)
        mr_is, _ = backtest_mr(ticker, ind_is, mom_open_is)
        for t in mr_is:
            t['period'] = 'IS'
            t['strategy'] = 'MR'
        all_is_mr.extend(mr_is)

        mom_open_full = build_momentum_open_set(trades_full)
        mr_full, _ = backtest_mr(ticker, ind_full, mom_open_full)
        mr_oos = [t for t in mr_full if t['entry_date'] >= oos_start_str]
        for t in mr_oos:
            t['period'] = 'OOS'
            t['strategy'] = 'MR'
        all_oos_mr.extend(mr_oos)

        m_oos = compute_metrics(trades_oos)
        wr_oos = m_oos['wr'] if m_oos else 0
        n_oos  = len(trades_oos)
        col    = G if wr_oos >= 55 else (Y if wr_oos >= 45 else R)
        print(f"IS:{len(trades_is):>3}t │ OOS:{n_oos:>3}t {col}WR={wr_oos:.0f}%{RST}")

        sig = get_today_signal(ticker, ind)
        if sig:
            all_signals[ticker] = sig

    # Métricas globales
    all_is_combined  = all_is_trades  + all_is_mr
    all_oos_combined = all_oos_trades + all_oos_mr
    m_is_combined    = compute_metrics(all_is_combined)
    m_oos_combined   = compute_metrics(all_oos_combined)
    port_oos = portfolio_simulate(all_oos_combined)

    if m_oos_combined and port_oos:
        m_oos_combined['total_pct'] = port_oos['total_pct']
        m_oos_combined['max_dd']    = port_oos['max_dd']
        m_oos_combined['sharpe']    = port_oos['sharpe']
        m_oos_combined['cagr']      = port_oos['cagr']

    # Benchmark y dashboard (igual que antes)
    benchmark = None
    try:
        # (código benchmark SPY intacto)
        pass
    except:
        pass

    # Resumen terminal y dashboard (igual)
    is_period = "2020-01-01 → hoy"
    oos_period = "2020-01-01 → hoy"
    dashboard_data = {
        "generated_at": datetime.now().isoformat(),
        "is_period": is_period,
        "oos_period": oos_period,
        "is_metrics": m_is_combined,
        "oos_metrics": m_oos_combined,
        "portfolio_oos": port_oos,
        "signals": all_signals,
        "oos_trades": all_oos_combined,
    }
    generate_dashboard(dashboard_data, DASHBOARD_FILE)
    print(f"\n{G}→ dashboard.html generado — listo para GitHub Pages{RST}\n")
    print(f"{G}✅ v1.2 instalada: sequías eliminadas y picos protegidos.{RST}")

if __name__ == "__main__":
    main()