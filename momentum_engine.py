"""
╔══════════════════════════════════════════════════════════════════════╗
║  MOMENTUM BREAKOUT ENGINE  v1.2                                      ║
║  Swing trading de alta convicción — una idea, bien ejecutada         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  MEJORAS v1.2:                                                       ║
║  • Compresión ≤ 25% + Vol breakout ≥ 60% → más trades                ║
║  • Pullback MR activada → reduce sequías                            ║
║  • Trailing fase 0 + BE a 0.30R desde +3% → protege picos +8%       ║
║  • Riesgo máximo 9% en activos normales                              ║
║                                                                      ║
║  Dashboard HTML intacto (igual al original v1.1)                     ║
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

# ────────────────────────────────────────────────────────────────
# UNIVERSO (sin cambios)
# ────────────────────────────────────────────────────────────────

UNIVERSE = {
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

HIGH_VOL_ASSETS = {"VIXL.DE", "DXS3.DE", "LQQ.PA", "IBEXA.MC", "DBPG.DE"}

TIER1_ASSETS = {"ZPDJ.DE","EXV1.DE","IBEXA.MC","DFEN.DE","WTIC.DE",
                "XLE","XLI","XME","ITA","COPX","LIT",
                "GOOGL","AVGO","TDG","PANW","CRWD","VST","RCL"}

TIER2_ASSETS = {"IS0E.DE","SLVR.DE","VVSM.DE","WTIF.DE","EMXC.DE",
                "XLK","XBI","MSFT","NOW","NOC","AEM","SMCI",
                "BKNG","AXON","NLR","SLX","UBER","KRW.PA"}

# ────────────────────────────────────────────────────────────────
# PARÁMETROS v1.2
# ────────────────────────────────────────────────────────────────

COMPRESSION_BARS = 10
TREND_BARS = 60
TREND_ATR_MULTIPLE = 1.5
TREND_EMA = 50

COMPRESSION_VOL_PERCENTILE = 25      # ← cambio clave
PANIC_VOL_PERCENTILE = 80
BREAKOUT_VOL_PERCENTILE = 60        # ← cambio clave

TP_R_MULTIPLE       = 5.0
SL_BUFFER_PCT       = 0.5
MAX_HOLD_DAYS       = 40
BREAKEVEN_AT_R      = 0.35          # más temprano
BREAKEVEN_EARLY_R   = 0.30          # protección ultra-temprana

TRAIL_ACT_0_R       = 0.5           # nueva fase
TRAIL_ACT_1_R       = 1.0
TRAIL_ACT_2_R       = 2.0
TRAIL_ACT_3_R       = 3.0

TRAIL_PCT_0         = 0.08
TRAIL_PCT_1         = 0.05
TRAIL_PCT_2         = 0.035
TRAIL_PCT_3         = 0.02

TRAIL_GAIN_0        = 0.25
TRAIL_GAIN_1        = 0.40
TRAIL_GAIN_2        = 0.55
TRAIL_GAIN_3        = 0.75

COMMISSION_PCT = 0.10
SLIPPAGE_PCT   = 0.05
IS_RATIO = 0.65

# Pullback parameters (activados)
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

# ────────────────────────────────────────────────────────────────
# INDICADORES (sin cambios)
# ────────────────────────────────────────────────────────────────

def compute_indicators(df):
    c  = df['Close'].squeeze().astype(float)
    h  = df['High'].squeeze().astype(float)
    lo = df['Low'].squeeze().astype(float)
    op = df['Open'].squeeze().astype(float)
    v  = df['Volume'].squeeze().astype(float)

    tr   = pd.concat([h - lo,
                      (h - c.shift()).abs(),
                      (lo - c.shift()).abs()], axis=1).max(axis=1)
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

# ────────────────────────────────────────────────────────────────
# CONDICIONES (usando nuevos percentiles)
# ────────────────────────────────────────────────────────────────

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
    defensivos = {"VIXL.DE","DXS3.DE","3QQS.DE","DBPK.DE","VZLD.DE","PHAG.DE","IDTL.DE","IBTA.DE"}
    es_defensivo = ticker in defensivos
    ema200_now   = _v(ind, 'ema200', i)
    above_ema200 = es_defensivo or (price_now > ema200_now and ema200_now > 0)
    ok = strong_trend and above_ema50 and above_ema200
    return ok, {'price_change_pct': round((price_change / price_then * 100), 1) if price_then > 0 else 0}

def check_compression(ind, i):
    if i < COMPRESSION_BARS + 252: return False, {}
    vp = ind['vol_pct'][i]
    if np.isnan(vp): return False, {}
    compressed = vp <= COMPRESSION_VOL_PERCENTILE
    comp_start = i - COMPRESSION_BARS
    comp_high  = float(np.max(ind['h'][comp_start:i+1]))
    comp_low   = float(np.min(ind['lo'][comp_start:i+1]))
    return compressed, {'vol_percentile': round(vp, 1), 'comp_high': round(comp_high, 4), 'comp_low': round(comp_low, 4)}

def check_breakout(ind, i):
    if i < COMPRESSION_BARS + 252: return False, {}
    high    = _v(ind, 'h', i)
    close   = _v(ind, 'c', i)
    vr      = ind['vol_rank'][i]
    if np.isnan(vr): return False, {}
    prev_high = float(np.max(ind['h'][i - COMPRESSION_BARS:i]))
    atr_now   = _v(ind, 'atr14', i)
    min_breakout = prev_high + 0.20 * atr_now
    daily_range = _v(ind, 'h', i) - _v(ind, 'lo', i)
    close_pct   = (close - _v(ind, 'lo', i)) / daily_range if daily_range > 0 else 0.5
    broke_out   = high >= min_breakout and close_pct >= 0.4
    strong_vol  = vr >= BREAKOUT_VOL_PERCENTILE
    ok = broke_out and strong_vol
    return ok, {'vol_rank': round(vr, 1)}

def compute_levels(ind, i, comp_detail, ticker=""):
    entry = _v(ind, 'c', i) * (1 + (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
    comp_low = comp_detail.get('comp_low', entry * 0.95)
    sl  = comp_low * (1 - SL_BUFFER_PCT / 100)
    risk_pct  = (entry - sl) / entry
    max_sl_pct = 0.12 if ticker in HIGH_VOL_ASSETS else 0.09   # ← cambio clave
    if risk_pct > max_sl_pct: return None, None, None, None
    risk = entry - sl
    if risk <= 0 or risk / entry < 0.010: return None, None, None, None
    tp   = entry + risk * TP_R_MULTIPLE
    rr   = round((tp - entry) / risk, 2)
    return round(entry, 4), round(sl, 4), round(tp, 4), rr

# ────────────────────────────────────────────────────────────────
# BACKTEST MOMENTUM (con trailing mejorado)
# ────────────────────────────────────────────────────────────────

def backtest(ticker, ind):
    n      = ind['n']
    trades = []
    diag   = {'panic':0, 'no_trend':0, 'no_comp':0, 'no_bo':0, 'all3':
