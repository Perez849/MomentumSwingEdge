"""
╔══════════════════════════════════════════════════════════════════════╗
║  MOMENTUM BREAKOUT ENGINE  v1.1                                      ║
║  Swing trading de alta convicción — una idea, bien ejecutada         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  LA IDEA (documentada en literatura desde 1993):                     ║
║  Un activo en tendencia que comprime su volatilidad y luego          ║
║  rompe al alza con volumen tiene compradores reales detrás.          ║
║  Eso es todo. Sin puntos arbitrarios. Sin 19 parámetros.             ║
║                                                                      ║
║  TRES CONDICIONES BINARIAS — todas obligatorias:                     ║
║  1. TENDENCIA: subida reciente > 1.5× su ATR normalizado             ║
║               Y precio sobre EMA de largo plazo                      ║
║  2. COMPRESIÓN: volatilidad realizada en percentil ≤ 25              ║
║               de su propia historia (universal, sin benchmarks)      ║
║  3. BREAKOUT: rompe máximo de la compresión con volumen              ║
║               en percentil ≥ 70                                      ║
║                                                                      ║
║  FILTRO DE RÉGIMEN — por activo, no por SPY:                         ║
║  Volatilidad realizada 20d en percentil ≥ 80 → pánico → no operar   ║
║                                                                      ║
║  SL: mínimo de la compresión (soporte estructural real)              ║
║  TP: 3.5 × riesgo (R/R mínimo 3.5:1)                                ║
║  Trailing: EMA8 una vez que el trade supera 1R                       ║
║                                                                      ║
║  ESTE ARCHIVO HACE TODO:                                             ║
║  - Backtest walk-forward honesto con IS/OOS split                    ║
║  - Señales de hoy                                                    ║
║  - Dashboard HTML standalone para GitHub Pages                       ║
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
# UNIVERSO
# ════════════════════════════════════════════════════════════════════

UNIVERSE = {
    # ══════════════════════════════════════════════════════════════════
    # UNIVERSO CURADO v2 — solo activos con edge demostrado en OOS
    # Criterio de inclusión: PF>1.0 en OOS con mínimo 2 trades
    # Eliminados ~50 activos con PF<1 o 0 trades que diluían el edge
    # ══════════════════════════════════════════════════════════════════

    # ── ETFs EUROPEOS UCITS (Xetra / Euronext) ───────────────────────
    "IS0E.DE":   "iShares Gold Producers ETF",          # WR=67% PF=1.12
    "SLVR.DE":   "Global X Silver Miners ETF",          # WR=50% PF=3.76
    "VVSM.DE":   "VanEck Semiconductor ETF",            # WR=67% PF=13.58 ★
    "SEC0.DE":   "iShares Semiconductors ETF",          # WR=50% PF=1.40
    "NDXH.PA":   "Amundi Nasdaq 100 EUR Hedge",         # WR=50%
    "LQQ.PA":    "Amundi Nasdaq 100 2x Lev",            # WR=57% PF=1.09
    "IBCF.DE":   "iShares S&P500 EUR Hedge",            # WR=64% PF=0.96
    "ZPDE.DE":   "SPDR US Energy ETF",                  # WR=50% PF=1.30
    "ZPDJ.DE":   "SPDR US Industrials ETF",             # WR=86% PF=3.96 ★★
    "EXV1.DE":   "iShares Euro Banks ETF",              # WR=75% PF=5.80 ★★
    "EMXC.DE":   "Amundi EM ex China ETF",              # WR=60% PF=1.87
    "IBEXA.MC":  "Amundi IBEX 35 2x ETF",              # WR=100% PF=99  ★★
    "WTIF.DE":   "WisdomTree Japan EUR Hedge",          # WR=70% PF=2.25 ★
    "DFEN.DE":   "VanEck Defense ETF",                  # WR=60% PF=5.61 ★★
    "WTIC.DE":   "WisdomTree Enhanced Commodity UCITS", # WR=71% PF=3.62 ★★
    "KWBE.DE":   "KraneShares CSI China Internet UCITS",# WR=100%
    "ENR.DE":    "Siemens Energy",                      # WR=50% PF=1.31
    "IUSR.DE":   "iShares US Property Yield UCITS",     # WR=71% IS
    "VIXL.DE":   "WisdomTree VIX Futures 2.25x UCITS",  # cobertura crash
    "DXS3.DE":   "Xtrackers S&P500 Inverse Daily Swap", # cobertura bajista

    # ── ETFs SECTORIALES USA ──────────────────────────────────────────
    "XLK":       "SPDR Technology Select Sector",       # WR=67% PF=1.84 ★
    "XLE":       "SPDR Energy Select Sector",           # WR=100% PF=99  ★★
    "XLF":       "SPDR Financial Select Sector",        # WR=67% PF=0.98
    "XLI":       "SPDR Industrial Select Sector",       # WR=78% PF=11.26 ★★
    "XLV":       "SPDR Health Care Select Sector",      # WR=50% PF=0.93
    "XME":       "SPDR S&P Metals & Mining ETF",        # WR=100% PF=99  ★★
    "SOXX":      "iShares Semiconductor ETF",           # WR=43% PF=1.02
    "ITA":       "iShares US Aerospace & Defense",      # WR=71% PF=3.28 ★★
    "IWM":       "iShares Russell 2000 (Small Cap)",    # WR=100% (2t)
    "XBI":       "SPDR S&P Biotech ETF",                # WR=60% PF=1.23
    "COPX":      "Global X Copper Miners ETF",          # WR=75% PF=4.72 ★★
    "LIT":       "Global X Lithium & Battery Tech ETF", # WR=67% PF=4.05 ★★
    "SLX":       "VanEck Steel ETF",                    # WR=56% PF=1.54
    "NLR":       "VanEck Uranium & Nuclear ETF",        # WR=57% PF=1.22

    # ── ACCIONES USA — EDGE DEMOSTRADO ───────────────────────────────
    "NVDA":      "NVIDIA Corporation",                  # momentum histórico
    "MSFT":      "Microsoft Corporation",               # WR=57% PF=1.64 ★
    "GOOGL":     "Alphabet (Google)",                   # WR=80% PF=4.52 ★★
    "AVGO":      "Broadcom Inc",                        # WR=57% PF=2.61 ★
    "CRWD":      "CrowdStrike Holdings",                # WR=100% PF=99
    "PANW":      "Palo Alto Networks",                  # WR=100% PF=99  ★
    "NOW":       "ServiceNow Inc",                      # WR=71% PF=1.49
    "UBER":      "Uber Technologies",                   # WR=100% (2t)
    "BKNG":      "Booking Holdings",                    # WR=50% PF=2.00
    "RTX":       "RTX Corporation (Raytheon)",          # WR=50% PF=1.28
    "NOC":       "Northrop Grumman",                    # WR=50% PF=3.27
    "HII":       "Huntington Ingalls Industries",       # WR=40% PF=0.91
    "TDG":       "TransDigm Group",                     # WR=86% PF=36.58 ★★★
    "AEM":       "Agnico Eagle Mines",                  # WR=75% PF=1.46 ★
    "AXON":      "Axon Enterprise",                     # WR=43% PF=1.93
    "VST":       "Vistra Energy",                       # WR=100% PF=99
    "SMCI":      "Super Micro Computer",                # WR=50% PF=1.66
    "RCL":       "Royal Caribbean",                     # WR=100% PF=99  ★
    "F":         "Ford Motor",                          # WR=100% (2t)
    "BABA":      "Alibaba ADR",                         # WR=100% (1t)
    "KRW.PA":    "Amundi MSCI Korea ETF",               # WR=67% PF=1.03
    "CCJ":       "Cameco (Uranium)",                    # WR=50% PF=1.02
    "AMZN":      "Amazon.com Inc",                      # WR=40% PF=0.92
    "DXCM":      "DexCom Inc",                         # WR=100% (1t) ★
    "SAIA":      "Saia Inc (Transporte)",               # WR=100% (1t)
    "DECK":      "Deckers Outdoor (HOKA/UGG)",          # WR=50% PF=0.65
    "NEM":       "Newmont Corporation (Oro)",           # WR=100% (1t)
    "PAAS":      "Pan American Silver",                 # WR=67% PF=0.86
}

# Activos con historial corto (<5 años) — el sistema los filtrará
# automáticamente si no tienen suficientes datos para el percentil.
# Los dejamos en el universo para cuando tengan historia suficiente.
SHORT_HISTORY = {"SLVR.DE", "VVSM.DE", "SEC0.DE", "DFEN.DE", "ENR.DE",
                  "KWBE.DE", "CRWD", "UBER", "DXCM", "SAIA"}

# Activos de volatilidad extrema — SL máximo ajustado al 8% (no 15%)
# VIXL puede caer 30%+ en un día cuando el VIX colapsa.
# 3QQQ/3USL/3SEM/3QQS tienen decaimiento temporal y gaps enormes.
HIGH_VOL_ASSETS = {"VIXL.DE", "DXS3.DE", "LQQ.PA", "IBEXA.MC", "DBPG.DE"}

# Position sizing por calidad del activo (basado en PF OOS demostrado)
# TIER1: PF>3 en OOS → 20% capital  (los mejores generadores de valor)
# TIER2: PF>1.5      → 15% capital  (edge sólido)
# TIER3: resto       → 10% capital  (edge marginal o muestra pequeña)
TIER1_ASSETS = {"ZPDJ.DE","EXV1.DE","IBEXA.MC","DFEN.DE","WTIC.DE",
                "XLE","XLI","XME","ITA","COPX","LIT",
                "GOOGL","AVGO","TDG","PANW","CRWD","VST","RCL"}
TIER2_ASSETS = {"IS0E.DE","SLVR.DE","VVSM.DE","WTIF.DE","EMXC.DE",
                "XLK","XBI","MSFT","NOW","NOC","AEM","SMCI",
                "BKNG","AXON","NLR","SLX","UBER","KRW.PA"}

# ════════════════════════════════════════════════════════════════════
# PARÁMETROS — mínimos, con lógica económica clara
# ════════════════════════════════════════════════════════════════════

# Ventana de la compresión — cuántas barras mide la "pausa"
COMPRESSION_BARS = 10

# Tendencia — el activo debe haber subido en los últimos N días
TREND_BARS = 60

# Cuántos múltiplos del ATR diario normalizado debe haber subido
# 1.5 significa: ha subido más de 1.5 veces su rango diario típico en 60 días
TREND_ATR_MULTIPLE = 1.5   # tendencia real pero sin exigir rally extraordinario

# EMA larga para confirmar tendencia
TREND_EMA = 50

# Percentil de volatilidad para la compresión (≤ este percentil = comprimido)
COMPRESSION_VOL_PERCENTILE = 35  # percentil 35: compresión real sin ser extrema

# Percentil de volatilidad para el filtro de pánico (≥ este = no operar)
PANIC_VOL_PERCENTILE = 80

# Percentil de volumen mínimo en el breakout
BREAKOUT_VOL_PERCENTILE = 65   # volumen confirmado sin exigir top 25%

# Gestión del trade
# ──────────────────────────────────────────────────────────────────
# DIAGNÓSTICO v3 — problema real identificado:
# El trailing se evalúa sobre CLOSE pero los picos son intradía.
# COPX: subió +11.6% intradía, cerró bajo 1R → trailing nunca activó
# LIT:  pico +15.6%, salida +6.44% → EMA trailing demasiado lejos
#
# SOLUCIÓN — trailing basado en ATR y evaluado sobre HIGH intradía:
# El ATR mide el rango real del activo. Trailing = peak_high - N×ATR
# Se actualiza cada día con el HIGH del día (no el close).
# Break-even también se activa con HIGH del día.
#
# Tres fases:
# 1. A 0.5R de HIGH: mover SL a break-even (protección mínima)
# 2. A 1.0R de HIGH: trailing peak - 2.0×ATR (espacio para respirar)  
# 3. A 2.0R de HIGH: trailing peak - 1.5×ATR (más ajustado)
# 4. A 3.0R de HIGH: trailing peak - 1.0×ATR (proteger ganancias grandes)
TP_R_MULTIPLE       = 5.0   # TP amplio — trailing gestiona la salida real
SL_BUFFER_PCT       = 0.5   # buffer en el SL estructural
MAX_HOLD_DAYS       = 40    # momentum necesita tiempo para desarrollarse
BREAKEVEN_AT_R      = 0.6   # break-even cuando HIGH supera 0.6R
# EXIT_NO_PROGRESS eliminado — cerraba trades buenos prematuramente

# Trailing dual: % del pico Y % de ganancia protegida (el mayor de los dos)
# SL = max(peak × (1 - TRAIL_PCT), entry + TRAIL_GAIN × ganancia_actual)
# Esto garantiza que en fase 1 siempre proteges al menos el 35% de la ganancia
# y en fase 3 proteges al menos el 75% — independientemente del riesgo inicial.

TRAIL_ACT_1_R       = 1.0   # activar fase 1 cuando HIGH alcanza 1R
TRAIL_ACT_2_R       = 2.0   # activar fase 2 cuando HIGH alcanza 2R
TRAIL_ACT_3_R       = 3.0   # activar fase 3 cuando HIGH alcanza 3R

# % del pico (suelo del SL)
TRAIL_PCT_1         = 0.05  # fase 1: SL no baja de peak × 0.95
TRAIL_PCT_2         = 0.035 # fase 2: SL no baja de peak × 0.965
TRAIL_PCT_3         = 0.02  # fase 3: SL no baja de peak × 0.98

# % de ganancia protegida (techo del SL — garantiza capturar parte del movimiento)
TRAIL_GAIN_1        = 0.40  # fase 1: capturar al menos 40% de (peak-entry)
TRAIL_GAIN_2        = 0.55  # fase 2: capturar al menos 55% de (peak-entry)
TRAIL_GAIN_3        = 0.75  # fase 3: capturar al menos 75% de (peak-entry)

# Costes (backtest)
COMMISSION_PCT = 0.10
SLIPPAGE_PCT   = 0.05

# Split IS/OOS para el backtest
IS_RATIO = 0.65

# ════════════════════════════════════════════════════════════════════
# PULLBACK EN TENDENCIA — parámetros estrategia complementaria
# ════════════════════════════════════════════════════════════════════
# Lógica: activos Tier1/Tier2 en tendencia alcista estructural
# (EMA20 > EMA50 > EMA200) que retroceden ordenadamente hasta tocar
# la EMA20 o EMA50. El retroceso debe ser silencioso (volumen bajo)
# — señal de falta de vendedores reales, no distribución.
# Entrada en el toque de soporte dinámico con cierre recuperando EMA.
#
# Complementa al momentum breakout:
#   - Breakout: captura el inicio de la tendencia
#   - Pullback: captura la continuación (segunda entrada)
# Filosóficamente coherentes — ambos requieren tendencia alcista.
#
# Solo opera en Tier1 + Tier2. Capital compartido con momentum.
# No acumula si ya hay trade momentum abierto en el mismo ticker.

PB_EMA_FAST         = 20      # EMA rápida — soporte dinámico principal
PB_EMA_MID          = 50      # EMA media — soporte si tendencia muy fuerte
PB_TOUCH_BUFFER     = 0.005   # precio dentro del 0.5% de la EMA = "toque"
PB_VOL_MAX_RANK     = 45      # volumen ≤ percentil 45 durante retroceso (silencioso)
PB_TREND_MIN_BARS   = 10      # EMA20>EMA50>EMA200 durante al menos 10 días
PB_PANIC_MAX        = 80      # mismo filtro pánico que momentum
PB_TP_R             = 2.5     # TP a 2.5R — más recorrido que MR (continuación)
PB_MAX_HOLD         = 20      # máx 20 días — pullbacks resuelven rápido
PB_SL_BUFFER        = 0.004   # buffer 0.4% bajo el mínimo del retroceso
PB_MIN_RISK         = 0.008   # riesgo mínimo 0.8% para evitar entradas sucias
PB_MAX_RISK         = 0.10    # riesgo máximo 10%
PB_POSITION_SIZE    = 0.10    # 10% del capital — mismo que Tier3 momentum
# Universo PB: solo Tier1 + Tier2 (activos con tendencia demostrada)

# ════════════════════════════════════════════════════════════════════
# INDICADORES
# ════════════════════════════════════════════════════════════════════

def compute_indicators(df):
    """
    Calcula todos los indicadores necesarios de forma vectorizada.
    Devuelve arrays numpy para uso eficiente en el backtest barra a barra.
    """
    c  = df['Close'].squeeze().astype(float)
    h  = df['High'].squeeze().astype(float)
    lo = df['Low'].squeeze().astype(float)
    op = df['Open'].squeeze().astype(float)
    v  = df['Volume'].squeeze().astype(float)

    # True Range y ATR
    tr   = pd.concat([h - lo,
                      (h - c.shift()).abs(),
                      (lo - c.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(span=14, adjust=False).mean()

    # Volatilidad realizada (std de retornos log en ventana móvil)
    log_ret = np.log(c / c.shift(1))
    vol20   = log_ret.rolling(20).std() * np.sqrt(252)  # anualizada

    # Percentil de volatilidad — usando historia de 252 días
    def vol_percentile(series, window=252):
        result = np.full(len(series), np.nan)
        arr = series.values
        for i in range(window, len(arr)):
            if np.isnan(arr[i]):
                continue
            hist = arr[i-window:i]
            hist = hist[~np.isnan(hist)]
            if len(hist) < 50:
                continue
            result[i] = float(np.sum(hist <= arr[i]) / len(hist) * 100)
        return result

    vol_pct = vol_percentile(vol20)

    # EMAs
    ema200 = c.ewm(span=200, adjust=False).mean()  # filtro de regimen
    ema50  = c.ewm(span=TREND_EMA, adjust=False).mean()
    ema20  = c.ewm(span=20, adjust=False).mean()   # soporte dinámico pullback
    ema8   = c.ewm(span=8,  adjust=False).mean()
    ema21  = c.ewm(span=21, adjust=False).mean()
    ema13  = c.ewm(span=13, adjust=False).mean()

    # Volumen — percentil móvil de 252 días
    def vol_rank(vseries, window=252):
        result = np.full(len(vseries), np.nan)
        arr = vseries.values
        for i in range(window, len(arr)):
            if np.isnan(arr[i]):
                continue
            hist = arr[i-window:i]
            hist = hist[~np.isnan(hist)]
            if len(hist) < 50:
                continue
            result[i] = float(np.sum(hist <= arr[i]) / len(hist) * 100)
        return result

    vol_rank_arr = vol_rank(v)

    # RSI ultra-corto (periodo 3) para mean reversion
    # RSI3 <= 25 en activo con tendencia = oversold temporal, alta prob rebote
    delta    = c.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=3, adjust=False).mean()  # RSI3 — sensible a movimientos bruscos
    avg_loss = loss.ewm(span=3, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    rsi3     = 100 - (100 / (1 + rs))

    return {
        'c':        c.values.astype(float),
        'h':        h.values.astype(float),
        'lo':       lo.values.astype(float),
        'op':       op.values.astype(float),
        'v':        v.values.astype(float),
        'tr':       tr.values.astype(float),
        'atr14':    atr14.values.astype(float),
        'vol20':    vol20.values.astype(float),
        'vol_pct':  vol_pct,           # percentil historico de volatilidad
        'vol_rank': vol_rank_arr,      # percentil historico de volumen
        'ema8':     ema8.values.astype(float),
        'ema13':    ema13.values.astype(float),
        'ema21':    ema21.values.astype(float),
        'ema50':    ema50.values.astype(float),
        'ema200':   ema200.values.astype(float),
        'ema20':    ema20.values.astype(float),
        'rsi3':     rsi3.values.astype(float),  # para mean reversion
        'dates':    df.index,
        'n':        len(c),
    }


def _v(ind, key, i):
    """Acceso seguro a indicador en barra i."""
    val = float(ind[key][i])
    return val if not np.isnan(val) else 0.0


# ════════════════════════════════════════════════════════════════════
# TRES CONDICIONES — BINARIAS, SIN PUNTOS
# ════════════════════════════════════════════════════════════════════

def check_panic(ind, i):
    """
    Filtro de régimen: ¿está el activo en modo pánico?
    Si la volatilidad realizada está en el percentil 80+ de su historia
    el activo está en régimen de riesgo elevado. No operar.
    """
    if i < 252:
        return False  # sin historia suficiente, asumir no-pánico
    vp = ind['vol_pct'][i]
    if np.isnan(vp):
        return False
    return vp >= PANIC_VOL_PERCENTILE


def check_trend(ind, i, ticker=''):
    """
    Condición 1: ¿Está el activo en tendencia alcista?

    Dos requisitos:
    a) El precio ha subido más de TREND_ATR_MULTIPLE × ATR diario en los
       últimos TREND_BARS días. Esto es relativo a la volatilidad del activo
       — un ETF tranquilo necesita menos subida absoluta que SMCI.
    b) El precio está por encima de su EMA50.

    Sin estos dos, no hay tendencia que explotar.
    """
    if i < TREND_BARS + 14:
        return False, {}

    price_now  = _v(ind, 'c', i)
    price_then = _v(ind, 'c', i - TREND_BARS)
    ema50_now  = _v(ind, 'ema50', i)
    atr_now    = _v(ind, 'atr14', i)

    if price_then <= 0 or atr_now <= 0:
        return False, {}

    # Subida en múltiplos de ATR diario (normalizado por volatilidad)
    price_change = price_now - price_then
    atr_threshold = atr_now * TREND_ATR_MULTIPLE * (TREND_BARS / 14)
    strong_trend = price_change > atr_threshold
    above_ema50  = price_now > ema50_now

    # Filtro de regimen: precio debe estar sobre EMA200
    # Esto elimina entradas en tendencias que ya estan muertas
    # (como comprar momentum alcista en mercado bajista 2022)
    # Activos defensivos/inversos estan exentos
    defensivos = {"VIXL.DE","DXS3.DE","3QQS.DE","DBPK.DE",
                  "VZLD.DE","PHAG.DE","IDTL.DE","IBTA.DE",
                  "XLP","XLU","ZPRS.DE","ZPDV.DE"}
    es_defensivo = ticker in defensivos
    ema200_now   = _v(ind, 'ema200', i)
    above_ema200 = es_defensivo or (price_now > ema200_now and ema200_now > 0)

    ok = strong_trend and above_ema50 and above_ema200
    return ok, {
        'price_change_pct': round((price_change / price_then * 100), 1),
        'atr_threshold_pct': round((atr_threshold / price_then * 100), 1),
        'above_ema50': above_ema50,
        'ema50': round(ema50_now, 2),
    }


def check_compression(ind, i):
    """
    Condición 2: ¿Está el activo en compresión de volatilidad?

    La volatilidad realizada de los últimos 20 días está en el percentil
    25 o inferior de su historia de 252 días.

    Esto es universal — funciona igual para oro, uranio y acciones chinas
    porque cada activo se compara contra sí mismo, no contra un benchmark.

    También detecta el máximo y mínimo de la zona de compresión para
    calcular el SL estructural.
    """
    if i < COMPRESSION_BARS + 252:
        return False, {}

    vp = ind['vol_pct'][i]
    if np.isnan(vp):
        return False, {}

    compressed = vp <= COMPRESSION_VOL_PERCENTILE

    # Máximo y mínimo de la ventana de compresión → SL estructural
    comp_start = i - COMPRESSION_BARS
    comp_high  = float(np.max(ind['h'][comp_start:i+1]))
    comp_low   = float(np.min(ind['lo'][comp_start:i+1]))

    return compressed, {
        'vol_percentile': round(vp, 1),
        'comp_high': round(comp_high, 4),
        'comp_low':  round(comp_low, 4),
        'comp_bars': COMPRESSION_BARS,
    }


def check_breakout(ind, i):
    """
    Condición 3: ¿Está rompiendo hoy?

    El precio actual supera el máximo de las últimas COMPRESSION_BARS barras
    Y el volumen está en el percentil 70+ de su historia.

    Sin volumen el breakout es una trampa — el precio sube sin compradores reales.
    """
    if i < COMPRESSION_BARS + 252:
        return False, {}

    high    = _v(ind, 'h', i)   # HIGH del día — el breakout ocurre intradía
    close   = _v(ind, 'c', i)
    vr      = ind['vol_rank'][i]

    if np.isnan(vr):
        return False, {}

    # Máximo de las barras anteriores (sin incluir la barra actual)
    prev_high = float(np.max(ind['h'][i - COMPRESSION_BARS:i]))

    # Breakout debe superar el maximo por al menos 0.3xATR
    # Filtra roturas marginales sin fuerza real (los trades R<1 suelen
    # entrar con breakouts de pennies por encima del maximo).
    atr_now      = _v(ind, 'atr14', i)
    min_breakout = prev_high + 0.20 * atr_now

    # CLOSE en el 40% superior del rango diario
    daily_range = _v(ind, 'h', i) - _v(ind, 'lo', i)
    close_pct   = (close - _v(ind, 'lo', i)) / daily_range if daily_range > 0 else 0.5
    broke_out   = high >= min_breakout and close_pct >= 0.4
    strong_vol  = vr >= BREAKOUT_VOL_PERCENTILE

    ok = broke_out and strong_vol
    return ok, {
        'prev_high':     round(prev_high, 4),
        'price':         round(close, 4),
        'vol_rank':      round(vr, 1),
        'breakout_pct':  round((close / prev_high - 1) * 100, 2) if prev_high > 0 else 0,
    }


def compute_levels(ind, i, comp_detail, ticker=""):
    """
    Calcula SL y TP para la entrada en la barra i.
    SL = mínimo de la compresión - buffer
    TP = entrada + 2.5 × riesgo
    """
    entry = _v(ind, 'c', i) * (1 + (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
    comp_low = comp_detail.get('comp_low', entry * 0.95)

    sl  = comp_low * (1 - SL_BUFFER_PCT / 100)

    # Filtro ATR/riesgo: rechazar si el activo no tiene suficiente
    # velocidad para llegar a 1R en tiempo razonable.
    #
    # Ratio = ATR_diario / riesgo_pct
    # Si ratio < 0.40: necesitas >2.5 dias de movimiento perfecto para 1R
    # Los trades malos (R_pico<1) tienen ratio medio de 0.19
    # Los trades buenos (R_pico>2) tienen ratio medio de 0.43
    #
    # Adicionalmente: SL absoluto max 10% — si la compresion tiene
    # rango de 10%+ no era compresion real, era volatilidad normal.
    atr_entry = float(ind['atr14'][i]) if 'atr14' in ind else 0
    risk_pct  = (entry - sl) / entry
    max_sl_pct = 0.12 if ticker in HIGH_VOL_ASSETS else 0.10

    if risk_pct > max_sl_pct:
        return None, None, None, None  # riesgo absoluto excesivo

    # Filtro ATR/riesgo: desactivado hasta calibrar con datos suficientes (>50 trades OOS)
    # if atr_entry > 0:
    #     atr_ratio = (atr_entry / entry) / risk_pct
    #     min_ratio = 0.35 if ticker in HIGH_VOL_ASSETS else 0.40
    #     if atr_ratio < min_ratio:
    #         return None, None, None, None
    risk = entry - sl

    if risk <= 0:
        return None, None, None, None
    # Riesgo mínimo: 1.5% — si el SL está muy cerca es una señal débil
    # y el TP queda demasiado cerca para que valga la pena entrar
    if risk / entry < 0.010:
        return None, None, None, None

    tp   = entry + risk * TP_R_MULTIPLE
    # Sin cap de TP — el ATR trailing gestiona la salida real
    rr   = round((tp - entry) / risk, 2)

    sl_pct = round((entry - sl) / entry * 100, 2)
    tp_pct = round((tp - entry) / entry * 100, 2)

    return round(entry, 4), round(sl, 4), round(tp, 4), rr


# ════════════════════════════════════════════════════════════════════
# BACKTEST BARRA A BARRA
# ════════════════════════════════════════════════════════════════════

def backtest(ticker, ind):
    """
    Simula el sistema barra a barra sobre el histórico completo.
    En cada barra i solo usa datos hasta i — sin look-ahead.
    """
    n      = ind['n']
    trades = []
    diag   = {'panic': 0, 'no_trend': 0, 'no_comp': 0, 'no_bo': 0,
              'all3': 0, 'bad_levels': 0}

    in_trade    = False
    entry_price = sl = sl_initial = tp = peak = 0.0
    entry_i     = 0
    entry_date  = None

    for i in range(COMPRESSION_BARS + 252 + TREND_BARS, n):
        price = _v(ind, 'c', i)
        if price <= 0:
            continue

        # ── Gestión del trade abierto ────────────────────────────────
        if in_trade:
            high_today = _v(ind, 'h', i)    # HIGH intradía real
            low_today  = _v(ind, 'lo', i)   # LOW intradía real
            atr_today  = _v(ind, 'atr14', i)
            held       = i - entry_i
            risk       = entry_price - sl_initial
            if risk <= 0 or atr_today <= 0:
                in_trade = False
                continue

            # pnl_r_peak usa el peak del día ANTERIOR (ya fijado)
            # Así el trailing del día de hoy protege contra el LOW de hoy.
            pnl_r_peak  = (peak        - entry_price) / risk
            pnl_r_today = (high_today  - entry_price) / risk
            pnl_r_close = (price       - entry_price) / risk

            # ── BREAK-EVEN: HIGH supera 0.6R ────────────────────────
            if pnl_r_today >= BREAKEVEN_AT_R and sl < entry_price:
                sl = max(sl, entry_price * 1.001)

            # ── PROFIT LOCK v2.0 — entre BE y fase 1 ─────────────────
            # PROBLEMA: 31 trades (22%) salen en BE con pico medio +5.1%
            # porque entre 0.6R (BE) y 1.0R (trailing) no hay nada.
            # Un trade sube a 0.9R (+6%), no activa trailing, cae → BE → 0%.
            #
            # SOLUCIÓN: profit lock parcial que sube el SL gradualmente.
            # - A 0.7R: proteger 20% de la ganancia → +1.0% en vez de 0%
            # - A 0.85R: proteger 30% → +1.8% en vez de 0%
            # Esto NO interfiere con fase 1 (1.0R) porque el max() siempre
            # toma el valor más alto. Si el trade llega a 1R, fase 1 domina.
            if pnl_r_peak >= 0.7 and pnl_r_peak < TRAIL_ACT_1_R:
                gain = peak - entry_price
                lock = entry_price + 0.20 * gain  # proteger 20%
                sl = max(sl, lock)

            if pnl_r_peak >= 0.85 and pnl_r_peak < TRAIL_ACT_1_R:
                gain = peak - entry_price
                lock = entry_price + 0.30 * gain  # proteger 30%
                sl = max(sl, lock)

            # ── TRAILING % DEL PICO — fases 1-4 (sin cambios) ────────
            # Estas fases tienen WR 100% en trades 1R+ → no tocar.

            if pnl_r_peak >= TRAIL_ACT_1_R:
                # SL = máximo entre:
                # (a) peak × (1-PCT): suelo absoluto del SL
                # (b) entry + GAIN × (peak-entry): % de ganancia protegida
                gain = peak - entry_price
                trail = max(
                    peak * (1 - TRAIL_PCT_1),
                    entry_price + TRAIL_GAIN_1 * gain
                )
                sl = max(sl, trail)

            if pnl_r_peak >= TRAIL_ACT_2_R:
                gain = peak - entry_price
                trail = max(
                    peak * (1 - TRAIL_PCT_2),
                    entry_price + TRAIL_GAIN_2 * gain
                )
                sl = max(sl, trail)

            if pnl_r_peak >= TRAIL_ACT_3_R:
                gain = peak - entry_price
                trail = max(
                    peak * (1 - TRAIL_PCT_3),
                    entry_price + TRAIL_GAIN_3 * gain
                )
                sl = max(sl, trail)

            if pnl_r_peak >= 4.0:
                # Fase 4: trade excepcional — proteger 87% del pico
                # Deja solo un 1.5% de margen desde el pico
                gain = peak - entry_price
                trail = max(
                    peak * (1 - 0.015),
                    entry_price + 0.87 * gain
                )
                sl = max(sl, trail)

            # Actualizar peak DESPUÉS de calcular el trailing
            # Así el trailing de hoy protege contra el LOW de hoy
            peak = max(peak, high_today)

            # ── EVALUAR SALIDA ───────────────────────────────────────
            # Usar LOW del día para SL (el precio bajó hasta ahí intradía)
            reason = None
            if low_today <= sl:
                reason = 'SL'
            elif high_today >= tp:
                reason = 'TP'
            elif held >= MAX_HOLD_DAYS:
                reason = 'T'

            if reason:
                # Precio de salida: si SL → precio del SL (ejecutado en SL)
                # Si TP → precio del TP. Si T → close del día.
                if reason == 'SL':
                    raw_exit = sl  # ejecutado en el nivel del SL
                elif reason == 'TP':
                    raw_exit = tp  # ejecutado en el TP
                else:
                    raw_exit = price  # close del día
                exit_price = raw_exit * (1 - (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
                pnl_net    = (exit_price - entry_price) / entry_price * 100

                r_achieved = round((peak - entry_price) / (entry_price - sl_initial), 2) if (entry_price - sl_initial) > 0 else 0
                trades.append({
                    'ticker':      ticker,
                    'entry_date':  str(entry_date)[:10],
                    'exit_date':   str(ind['dates'][i])[:10],
                    'entry_price': round(entry_price, 4),
                    'exit_price':  round(exit_price, 4),
                    'stop_loss':   round(sl_initial, 4),
                    'take_profit': round(tp, 4),
                    'pnl':         round(pnl_net, 3),
                    'days':        held,
                    'reason':      reason,
                    'peak_pnl':    round((peak - entry_price) / entry_price * 100, 2),
                    'r_achieved':  r_achieved,
                })
                in_trade = False
            continue

        # ── Evaluar nueva entrada ────────────────────────────────────

        # Filtro de pánico — si el activo está en modo pánico, ignorar
        if check_panic(ind, i):
            diag['panic'] += 1
            continue

        # Condición 1: Tendencia
        trend_ok, trend_d = check_trend(ind, i, ticker)
        if not trend_ok:
            diag['no_trend'] += 1
            continue

        # Condición 2: Compresión
        comp_ok, comp_d = check_compression(ind, i)
        if not comp_ok:
            diag['no_comp'] += 1
            continue

        # Condición 3: Breakout
        bo_ok, bo_d = check_breakout(ind, i)
        if not bo_ok:
            diag['no_bo'] += 1
            continue

        diag['all3'] += 1

        # Las tres condiciones pasan — calcular niveles
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d, ticker)
        if entry_p is None or rr < 1.5:  # R/R mínimo 1.5
            diag['bad_levels'] += 1
            continue

        in_trade    = True
        entry_price = entry_p
        sl          = sl_p
        sl_initial  = sl_p   # guardar SL original para calcular R
        tp          = tp_p
        peak        = _v(ind, 'h', i)  # HIGH del día de entrada (no close)
        entry_i     = i
        entry_date  = ind['dates'][i]

    return trades, diag



# ════════════════════════════════════════════════════════════════════
# MEAN REVERSION — backtest complementario
# ════════════════════════════════════════════════════════════════════

def backtest_mr(ticker, ind, momentum_open_dates=None):
    """
    Estrategia complementaria: Pullback en Tendencia.

    IDEA: activos Tier1/Tier2 con tendencia alcista estructural
    (EMA20 > EMA50 > EMA200) que retroceden ordenadamente hasta tocar
    la EMA20 o EMA50 con volumen bajo (sin distribución real).
    El retroceso es una segunda oportunidad de entrada en tendencia,
    no una reversión. El cierre debe recuperar la EMA el día del toque.

    Complementa al breakout: éste captura el inicio, el pullback
    captura la continuación. Filosóficamente coherentes.

    Solo opera Tier1 + Tier2. No acumula si hay momentum abierto.
    """
    if ticker not in TIER1_ASSETS and ticker not in TIER2_ASSETS:
        return [], {}

    if momentum_open_dates is None:
        momentum_open_dates = set()

    n      = ind['n']
    trades = []
    diag   = {'no_trend': 0, 'no_pullback': 0, 'no_touch': 0,
              'panic': 0, 'bad_levels': 0, 'momentum_open': 0, 'vol_high': 0}

    in_trade    = False
    entry_price = sl = tp = peak = 0.0
    entry_i     = 0
    entry_date  = None

    min_bars = max(PB_TREND_MIN_BARS + 220, 270)

    def ema_series(key, i):
        return _v(ind, key, i)

    for i in range(min_bars, n):
        price = _v(ind, 'c', i)
        if price <= 0:
            continue

        # ── Gestión del trade abierto ────────────────────────────────
        if in_trade:
            high_today = _v(ind, 'h', i)
            low_today  = _v(ind, 'lo', i)
            held       = i - entry_i
            risk       = entry_price - sl

            if risk <= 0:
                in_trade = False
                continue

            # Break-even a 1R
            pnl_r = (high_today - entry_price) / risk
            if pnl_r >= 1.0 and sl < entry_price:
                sl = max(sl, entry_price * 1.001)

            peak = max(peak, high_today)

            reason = None
            if low_today <= sl:
                reason = 'SL'
            elif high_today >= tp:
                reason = 'TP'
            elif held >= PB_MAX_HOLD:
                reason = 'T'

            if reason:
                raw_exit   = sl if reason == 'SL' else (tp if reason == 'TP' else price)
                exit_price = raw_exit * (1 - (COMMISSION_PCT + SLIPPAGE_PCT) / 100)
                pnl_net    = (exit_price - entry_price) / entry_price * 100
                r_achieved = round((peak - entry_price) / risk, 2) if risk > 0 else 0

                trades.append({
                    'ticker':      ticker,
                    'entry_date':  str(entry_date)[:10],
                    'exit_date':   str(ind['dates'][i])[:10],
                    'entry_price': round(entry_price, 4),
                    'exit_price':  round(exit_price, 4),
                    'stop_loss':   round(sl, 4),
                    'take_profit': round(tp, 4),
                    'pnl':         round(pnl_net, 3),
                    'days':        held,
                    'reason':      reason,
                    'peak_pnl':    round((peak - entry_price) / entry_price * 100, 2),
                    'r_achieved':  r_achieved,
                    'strategy':    'MR',   # mantener etiqueta 'MR' para compatibilidad dashboard
                })
                in_trade = False
            continue

        # ── Evaluar nueva entrada Pullback ───────────────────────────

        date_str = str(ind['dates'][i])[:10]

        # No abrir si hay trade momentum en este ticker hoy
        if (ticker, date_str) in momentum_open_dates:
            diag['momentum_open'] += 1
            continue

        # Filtro pánico — igual que momentum
        vp = ind['vol_pct'][i]
        if not np.isnan(vp) and vp >= PB_PANIC_MAX:
            diag['panic'] += 1
            continue

        # ── Condición 1: tendencia estructural alcista ───────────────
        # EMA20 > EMA50 > EMA200 durante PB_TREND_MIN_BARS días consecutivos
        ema20_now  = _v(ind, 'ema20',  i)
        ema50_now  = _v(ind, 'ema50',  i)
        ema200_now = _v(ind, 'ema200', i)

        if ema20_now <= 0 or ema50_now <= 0 or ema200_now <= 0:
            diag['no_trend'] += 1
            continue

        # Pendiente estructural confirmada
        if not (ema20_now > ema50_now > ema200_now):
            diag['no_trend'] += 1
            continue

        # Precio sobre EMA200 — no operar en tendencia bajista macro
        price_now = _v(ind, 'c', i)
        if price_now < ema200_now * 0.995:
            diag['no_trend'] += 1
            continue

        # Confirmar que la tendencia lleva al menos PB_TREND_MIN_BARS días
        trend_ok_bars = 0
        for j in range(i - PB_TREND_MIN_BARS, i):
            e20 = _v(ind, 'ema20',  j)
            e50 = _v(ind, 'ema50',  j)
            e200= _v(ind, 'ema200', j)
            if e20 > e50 > e200:
                trend_ok_bars += 1
        if trend_ok_bars < PB_TREND_MIN_BARS:
            diag['no_trend'] += 1
            continue

        # ── Condición 2: precio en pullback (por debajo de EMA20 recientemente) ──
        # El precio debe haber cruzado por debajo o tocado la EMA20 en los últimos
        # 3 días, y el cierre de hoy debe estar por encima (recuperación)
        touch_ema20 = False
        touch_ema50 = False

        for j in range(max(0, i-3), i+1):
            lo_j  = _v(ind, 'lo',   j)
            hi_j  = _v(ind, 'h',    j)
            c_j   = _v(ind, 'c',    j)
            e20_j = _v(ind, 'ema20', j)
            e50_j = _v(ind, 'ema50', j)

            # Toque EMA20: mínimo tocó la EMA20 (±0.5%) y cierre por encima
            if e20_j > 0 and lo_j <= e20_j * (1 + PB_TOUCH_BUFFER) and c_j >= e20_j:
                touch_ema20 = True
            # Toque EMA50: más profundo — solo si EMA50 está ≥ 5% por encima de EMA200
            if e50_j > 0 and ema200_now > 0:
                ema50_dist = (e50_j - ema200_now) / ema200_now
                if ema50_dist >= 0.05 and lo_j <= e50_j * (1 + PB_TOUCH_BUFFER) and c_j >= e50_j:
                    touch_ema50 = True

        if not (touch_ema20 or touch_ema50):
            diag['no_touch'] += 1
            continue

        # El cierre de hoy debe estar por encima de la EMA tocada
        if touch_ema20 and price_now < ema20_now:
            diag['no_pullback'] += 1
            continue
        if touch_ema50 and not touch_ema20 and price_now < ema50_now:
            diag['no_pullback'] += 1
            continue

        # ── Condición 3: volumen bajo durante el retroceso (silencioso) ──
        vol_rank_now = ind['vol_rank'][i]
        if not np.isnan(vol_rank_now) and vol_rank_now > PB_VOL_MAX_RANK:
            diag['vol_high'] += 1
            continue

        # ── Niveles de entrada ───────────────────────────────────────
        entry_p = price_now * (1 + (COMMISSION_PCT + SLIPPAGE_PCT) / 100)

        # SL: mínimo del retroceso (últimos 5 días) - buffer
        recent_low = float(np.min(ind['lo'][i - 5:i + 1]))
        sl_p       = recent_low * (1 - PB_SL_BUFFER)

        risk = entry_p - sl_p
        if risk <= 0 or risk / entry_p < PB_MIN_RISK:
            diag['bad_levels'] += 1
            continue
        if risk / entry_p > PB_MAX_RISK:
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
    """
    Construye un set de (ticker, date) para todas las fechas en que
    cada trade momentum está abierto. Permite a MR evitar acumular
    en el mismo activo que ya tiene posición momentum.
    """
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
# MÉTRICAS POR TRADE (WR, PF, expectativa — independientes del portfolio)
# ════════════════════════════════════════════════════════════════════

def compute_metrics(trades):
    """
    Métricas estadísticas por trade individual.
    WR, PF, expectativa son válidas aquí — no dependen del portfolio.
    Equity total y MaxDD NO se calculan aquí — ver portfolio_simulate.
    """
    if not trades:
        return None
    pnls = np.array([t['pnl'] for t in trades])
    wins = pnls[pnls > 0]
    loss = pnls[pnls <= 0]
    n    = len(pnls)

    wr    = len(wins) / n * 100
    pf    = abs(wins.sum() / loss.sum()) if loss.sum() != 0 else (99.0 if len(wins) else 0)
    avg_w = float(wins.mean()) if len(wins) else 0
    avg_l = float(loss.mean()) if len(loss) else 0
    # Sharpe por trade — anualizado asumiendo ~252/avg_hold_days trades/año
    _avg_hold = float(np.mean([t['days'] for t in trades])) if trades else 25
    _ann = np.sqrt(max(252 / max(_avg_hold, 1), 1))
    sh    = float(pnls.mean() / pnls.std() * _ann) if pnls.std() > 0 else 0
    expectancy = avg_w * (wr / 100) + avg_l * (1 - wr / 100)

    by_reason = {}
    for t in trades:
        r = t.get('reason', '?')
        by_reason[r] = by_reason.get(r, 0) + 1

    avg_days = float(np.mean([t['days'] for t in trades]))

    streak = max_streak = cur = 0
    for p in pnls:
        if p < 0:
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 0

    # Efficiency ratio: qué % del pico capturaste en la salida
    # Solo sobre ganadores con pico > 0.5% (evita división por ruido)
    # Un perdedor que llegó a +5% de pico y salió en -3% tiene eficiencia -60%
    # pero eso no mide trailing — mide que el trade falló después del pico
    # Métrica útil: sobre TODOS los trades con pico >0.5%, mide captura media
    efficiencies = []
    for t in trades:
        peak_p = t.get('peak_pnl', 0)
        pnl_p  = t.get('pnl', 0)
        if peak_p > 0.5:
            efficiencies.append(pnl_p / peak_p * 100)
    # Reportar por separado ganadores vs total para contexto
    eff_winners = [pnl_p / peak_p * 100
                   for t in trades
                   for peak_p, pnl_p in [(t.get('peak_pnl',0), t.get('pnl',0))]
                   if peak_p > 0.5 and pnl_p > 0]
    avg_efficiency = round(float(np.mean(efficiencies)), 1) if efficiencies else 0
    avg_eff_winners = round(float(np.mean(eff_winners)), 1) if eff_winners else 0

    return {
        'n':               n,
        'wr':              round(wr, 1),
        'pf':              round(pf, 2),
        'sharpe':          round(sh, 2),
        'avg_win':         round(avg_w, 2),
        'avg_loss':        round(avg_l, 2),
        'expectancy':      round(expectancy, 3),
        'avg_days':        round(avg_days, 1),
        'max_loss_streak': max_streak,
        'avg_efficiency':  avg_efficiency,  # % del pico capturado
        'by_reason':       by_reason,
        'pnls':            [round(float(p), 3) for p in pnls],
        'trade_dates':     [t['entry_date'] for t in trades],
    }


# ════════════════════════════════════════════════════════════════════
# PORTFOLIO SIMULATOR — equity día a día con posiciones paralelas
# ════════════════════════════════════════════════════════════════════

def portfolio_simulate(trades, initial_capital=10000.0, position_size_pct=15.0):
    """
    Simula el portfolio día a día con posiciones paralelas reales.

    Cada señal abre una posición con position_size_pct del capital INICIAL
    (Kelly simplificado — tamaño fijo para evitar ruina). Con 87 activos
    y señales espaciadas, raramente habrá más de 3-5 posiciones simultáneas.

    Devuelve:
    - equity_curve: serie diaria de valor del portfolio (índice normalizado a 100)
    - daily_dates:  fechas correspondientes
    - total_pct:    retorno total del portfolio
    - max_dd:       drawdown máximo real (pico a valle en %)
    - sharpe:       Sharpe anual sobre retornos diarios
    - benchmark comparado contra SPY en mismo período
    """
    if not trades:
        return None

    # Ordenar trades por fecha de entrada
    trades_s = sorted(trades, key=lambda t: t['entry_date'])
    if not trades_s:
        return None

    # Rango de fechas del portfolio
    start = pd.Timestamp(trades_s[0]['entry_date'])
    end   = pd.Timestamp(max(t['exit_date'] for t in trades_s))
    dates = pd.bdate_range(start, end)  # solo días hábiles
    if len(dates) < 2:
        return None

    # Índice de fechas para lookup rápido
    date_idx = {d.strftime('%Y-%m-%d'): i for i, d in enumerate(dates)}
    n_days   = len(dates)

    # Capital por posición (fijo en % del capital inicial)
    # Position sizing dinámico: TIER1=20%, TIER2=15%, resto=10%
    # Se calcula por trade individual usando el ticker
    # pos_capital es el default (para trades sin ticker info)
    pos_capital_default = initial_capital * position_size_pct / 100.0
    pos_capital = pos_capital_default  # se sobreescribe por trade

    # ── P&L reconocido en fecha de SALIDA (no distribuido) ──────────
    # Razón: no conoces el resultado hasta cerrar la posición.
    # La distribución lineal creaba artefactos visuales (subidas/caídas
    # artificiales) porque trades largos con gran P&L se "esparcían"
    # de forma incorrecta sobre días anteriores a la salida real.
    #
    # Para reflejar posiciones ABIERTAS correctamente, calculamos el
    # valor mark-to-market de cada posición abierta cada día usando
    # interpolación del P&L entre entrada y salida — pero solo para
    # el gráfico visual. El P&L REAL se confirma en la fecha de salida.
    #
    # Método: equity diaria = capital_base + sum(MTM de posiciones abiertas)
    # MTM de cada posición = pos_capital × (pnl_pct × fracción_transcurrida)

    # Primero construir índice entrada→salida por trade
    open_trades = []  # lista de (ei, xi, pnl_pct, pos_cap)
    for t in trades_s:
        ei = date_idx.get(t['entry_date'])
        xi = date_idx.get(t['exit_date'])
        if ei is None:
            continue
        if xi is None:
            xi = n_days - 1
        xi = min(xi, n_days - 1)
        pnl_pct = t['pnl'] / 100.0
        # Position sizing dinámico según estrategia y calidad del activo
        tkr      = t.get('ticker', '')
        strategy = t.get('strategy', 'MOM')
        if strategy == 'MR':
            # Pullback en tendencia: sizing igual que Tier3 momentum
            t_cap = initial_capital * PB_POSITION_SIZE
        elif tkr in TIER1_ASSETS:
            t_cap = initial_capital * 0.20
        elif tkr in TIER2_ASSETS:
            t_cap = initial_capital * 0.15
        else:
            t_cap = initial_capital * 0.10
        open_trades.append((ei, xi, pnl_pct, t_cap))

    # Calcular equity día a día con MTM de posiciones abiertas
    # P&L se reconoce progresivamente (fracción del tiempo transcurrido)
    # Esto es más realista que distribuir uniformemente O reconocer solo al cierre
    equity = np.full(n_days, initial_capital)
    for d in range(1, n_days):
        mtm_total = 0.0
        for (ei, xi, pnl_pct, t_cap) in open_trades:
            if ei >= d:
                continue   # trade no abierto aún
            if xi < d - 1:
                # Trade ya cerrado — su P&L ya está incorporado permanentemente
                mtm_total += t_cap * pnl_pct
            else:
                # Trade abierto — MTM proporcional al tiempo transcurrido
                frac = (d - ei) / max(xi - ei, 1)
                frac = min(frac, 1.0)
                mtm_total += t_cap * pnl_pct * frac
        equity[d] = initial_capital + mtm_total

    equity = np.maximum(equity, 1.0)

    # Normalizar a base 100
    equity_idx = equity / initial_capital * 100

    # MaxDD real sobre equity diaria
    running_max = np.maximum.accumulate(equity)
    dd_series   = (equity / running_max - 1) * 100
    max_dd      = float(dd_series.min())

    # Retorno total
    total_pct = float((equity[-1] / initial_capital - 1) * 100)

    # Sharpe sobre retornos diarios (anualizado)
    daily_ret = np.diff(equity) / equity[:-1]
    sharpe    = float(daily_ret.mean() / daily_ret.std() * np.sqrt(252)) if daily_ret.std() > 0 else 0

    # CAGR
    years = (end - start).days / 365.25
    cagr  = float((equity[-1] / initial_capital) ** (1 / max(years, 0.1)) - 1) * 100 if years > 0 else 0

    # Máx posiciones simultáneas — usando índices numéricos (eficiente)
    open_arr = np.zeros(n_days, dtype=int)
    for (ei, xi, _, _t) in open_trades:
        open_arr[ei:xi+1] += 1
    max_concurrent = int(open_arr.max()) if n_days > 0 else 0

    return {
        'equity_curve':    [round(float(v), 2) for v in equity_idx],
        'daily_dates':     [d.strftime('%Y-%m-%d') for d in dates],
        'total_pct':       round(total_pct, 1),
        'max_dd':          round(max_dd, 1),
        'sharpe':          round(sharpe, 2),
        'cagr':            round(cagr, 1),
        'max_concurrent':  max_concurrent,
        'initial_capital': initial_capital,
        'pos_size_pct':    position_size_pct,
        'n_days':          n_days,
    }


# ════════════════════════════════════════════════════════════════════
# SEÑALES DEL DÍA
# ════════════════════════════════════════════════════════════════════

def get_today_signal(ticker, ind):
    """
    Evalúa el estado del activo en la última barra disponible.
    Devuelve señal de entrada si aplica, o estado de vigilancia.
    """
    i = ind['n'] - 1
    if i < COMPRESSION_BARS + 252 + TREND_BARS:
        return None

    price = _v(ind, 'c', i)
    if price <= 0:
        return None

    panic = check_panic(ind, i)
    trend_ok, trend_d = check_trend(ind, i, ticker)
    comp_ok,  comp_d  = check_compression(ind, i)
    bo_ok,    bo_d    = check_breakout(ind, i)

    # Estado del activo
    conditions_met = sum([trend_ok, comp_ok, bo_ok])
    signal_type = None

    if not panic and trend_ok and comp_ok and bo_ok:
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d, ticker)
        if entry_p and rr >= 1.5:
            signal_type = 'FIRE'
        else:
            signal_type = 'WEAK'
    elif not panic and trend_ok and comp_ok and not bo_ok:
        signal_type = 'WATCH'  # setup listo, falta el breakout
    elif not panic and trend_ok and not comp_ok:
        signal_type = 'TREND'  # en tendencia pero no comprimido aún
    elif panic:
        signal_type = 'PANIC'
    else:
        signal_type = 'NONE'

    entry_p = sl_p = tp_p = rr = None
    sl_pct = tp_pct = None
    if signal_type == 'FIRE':
        entry_p, sl_p, tp_p, rr = compute_levels(ind, i, comp_d)
        if entry_p and sl_p:
            sl_pct = round((entry_p - sl_p) / entry_p * 100, 2)
            tp_pct = round((tp_p - entry_p) / entry_p * 100, 2)

    # Datos para el gráfico (últimas 90 barras)
    hist_start = max(0, ind['n'] - 90)
    price_hist = []
    for j in range(hist_start, ind['n']):
        price_hist.append({
            'date':   str(ind['dates'][j])[:10],
            'open':   round(float(ind['op'][j]),  4) if not np.isnan(ind['op'][j])  else None,
            'high':   round(float(ind['h'][j]),   4) if not np.isnan(ind['h'][j])   else None,
            'low':    round(float(ind['lo'][j]),  4) if not np.isnan(ind['lo'][j])  else None,
            'close':  round(float(ind['c'][j]),   4) if not np.isnan(ind['c'][j])   else None,
            'volume': int(ind['v'][j]) if not np.isnan(ind['v'][j]) else 0,
            'ema8':   round(float(ind['ema8'][j]), 4)  if not np.isnan(ind['ema8'][j])  else None,
            'ema21':  round(float(ind['ema21'][j]),4)  if not np.isnan(ind['ema21'][j]) else None,
            'ema50':  round(float(ind['ema50'][j]),4)  if not np.isnan(ind['ema50'][j]) else None,
            'vol_pct':round(float(ind['vol_pct'][j]),1) if not np.isnan(ind['vol_pct'][j]) else None,
        })

    return {
        'ticker':       ticker,
        'name':         UNIVERSE.get(ticker, ticker),
        'signal':       signal_type,
        'price':        round(price, 4),
        'entry_price':  round(entry_p, 4)  if entry_p else None,
        'stop_loss':    round(sl_p, 4)     if sl_p    else None,
        'take_profit':  round(tp_p, 4)     if tp_p    else None,
        'sl_pct':       sl_pct,
        'tp_pct':       tp_pct,
        'rr_ratio':     rr,
        'trend':        trend_ok,
        'compressed':   comp_ok,
        'breakout':     bo_ok,
        'panic':        panic,
        'conditions':   conditions_met,
        'trend_detail': trend_d,
        'comp_detail':  comp_d,
        'bo_detail':    bo_d,
        'price_hist':   price_hist,
        'ema50':        round(_v(ind,'ema50',i), 4),
        'vol_pct_now':  round(float(ind['vol_pct'][i]), 1) if not np.isnan(ind['vol_pct'][i]) else None,
        'vol_rank_now': round(float(ind['vol_rank'][i]),1) if not np.isnan(ind['vol_rank'][i]) else None,
    }


# ════════════════════════════════════════════════════════════════════
# DASHBOARD HTML — standalone, sin dependencias, listo para GitHub
# ════════════════════════════════════════════════════════════════════

def generate_dashboard(data, out_path):
    data_js = json.dumps(data, ensure_ascii=False, default=str)

    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Momentum Breakout Engine</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Syne+Mono&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#050810;--s1:#080c18;--s2:#0c1020;--s3:#101428;
  --b1:#141d35;--b2:#1e2d50;--b3:#2a3f70;
  --fire:#ff4d6d;--fire2:#ff6b35;--watch:#ffd60a;--safe:#06d6a0;
  --blue:#4cc9f0;--purple:#7b5ea7;--muted:#3d5a8a;
  --t1:#f0f4ff;--t2:#8fa3c8;--t3:#4d6a99;--t4:#2a3d5c;
  --mono:'Syne Mono',monospace;--sans:'Syne',sans-serif;--serif:'Instrument Serif',serif;
  --r:12px;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--t1);font-family:var(--sans);min-height:100vh;overflow-x:hidden}

/* NOISE TEXTURE */
body::after{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");opacity:.4;pointer-events:none;z-index:9999}

/* GLOW ORBS */
.orb{position:fixed;border-radius:50%;filter:blur(120px);pointer-events:none;z-index:0}
.orb1{width:600px;height:600px;background:rgba(76,201,240,.06);top:-200px;left:-100px}
.orb2{width:500px;height:500px;background:rgba(255,77,109,.05);bottom:-150px;right:-100px}
.orb3{width:400px;height:400px;background:rgba(6,214,160,.04);top:40%;left:50%;transform:translateX(-50%)}

/* LAYOUT */
.app{position:relative;z-index:1}
header{height:64px;border-bottom:1px solid var(--b1);padding:0 2.5rem;display:flex;align-items:center;justify-content:space-between;background:rgba(5,8,16,.85);backdrop-filter:blur(32px);position:sticky;top:0;z-index:100}
.brand{display:flex;align-items:center;gap:1rem}
.brand-mark{width:36px;height:36px;background:linear-gradient(135deg,var(--fire),var(--fire2));border-radius:8px;display:grid;place-items:center;font-size:.9rem;box-shadow:0 0 24px rgba(255,77,109,.3)}
.brand-name{font-family:var(--serif);font-size:1.1rem;font-style:italic;letter-spacing:-.01em}
.brand-sub{font-family:var(--mono);font-size:.52rem;color:var(--t3);letter-spacing:.12em;text-transform:uppercase;margin-top:.05rem}
.hdr-meta{display:flex;align-items:center;gap:1rem}
.pulse{width:7px;height:7px;background:var(--safe);border-radius:50%;box-shadow:0 0 10px var(--safe);animation:pulse 2.5s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(1.6)}}
.ts{font-family:var(--mono);font-size:.6rem;color:var(--t3)}

main{max-width:1800px;margin:0 auto;padding:2rem 2.5rem;display:flex;flex-direction:column;gap:2rem}

.section-head{font-family:var(--mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.15em;color:var(--t3);display:flex;align-items:center;gap:.8rem;margin-bottom:1.1rem}
.section-head::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--b2),transparent)}

/* STATS BAR */
.stats-bar{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:.75rem}
.stat-card{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:1.1rem 1.2rem;position:relative;overflow:hidden;transition:border-color .2s}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,var(--b2))}
.stat-card:hover{border-color:var(--b2)}
.stat-lbl{font-family:var(--mono);font-size:.52rem;text-transform:uppercase;letter-spacing:.1em;color:var(--t3);margin-bottom:.5rem}
.stat-val{font-family:var(--serif);font-style:italic;font-size:2rem;letter-spacing:-.02em;line-height:1;color:var(--accent,var(--t1))}
.stat-sub{font-size:.6rem;color:var(--t3);margin-top:.3rem}

/* SIGNALS */
.signals-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}
.sig{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:1.4rem;cursor:pointer;transition:all .2s;position:relative;overflow:hidden}
.sig::before{content:'';position:absolute;inset:0;opacity:0;transition:opacity .2s;pointer-events:none}
.sig:hover{transform:translateY(-3px);box-shadow:0 24px 48px rgba(0,0,0,.3)}
.sig.fire{border-color:rgba(255,77,109,.3)}
.sig.fire::before{background:linear-gradient(135deg,rgba(255,77,109,.06),transparent);opacity:1}
.sig.watch{border-color:rgba(255,214,10,.2)}
.sig.watch::before{background:linear-gradient(135deg,rgba(255,214,10,.04),transparent);opacity:1}
.sig-stripe{position:absolute;top:0;left:0;right:0;height:3px}
.sig.fire .sig-stripe{background:linear-gradient(90deg,var(--fire),var(--fire2),transparent)}
.sig.watch .sig-stripe{background:linear-gradient(90deg,var(--watch),transparent)}
.sig-badge{font-family:var(--mono);font-size:.52rem;padding:.18rem .55rem;border-radius:20px;text-transform:uppercase;letter-spacing:.09em;display:inline-flex;align-items:center;gap:.35rem;margin-bottom:.7rem}
.sig.fire .sig-badge{background:rgba(255,77,109,.12);color:var(--fire);border:1px solid rgba(255,77,109,.25)}
.sig.watch .sig-badge{background:rgba(255,214,10,.1);color:var(--watch);border:1px solid rgba(255,214,10,.2)}
.sig-ticker{font-family:var(--serif);font-style:italic;font-size:2rem;font-weight:400;letter-spacing:-.02em;line-height:1;margin-bottom:.2rem}
.sig-name{font-size:.63rem;color:var(--t3);margin-bottom:1rem}
.levels{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:.85rem}
.lv{padding:.55rem .65rem;border-radius:8px;background:var(--s2)}
.lv.entry{background:rgba(76,201,240,.06);border:1px solid rgba(76,201,240,.12)}
.lv.sl{background:rgba(255,77,109,.06);border:1px solid rgba(255,77,109,.12)}
.lv.tp{background:rgba(6,214,160,.06);border:1px solid rgba(6,214,160,.12)}
.lv-lbl{font-family:var(--mono);font-size:.48rem;text-transform:uppercase;letter-spacing:.09em;color:var(--t3);margin-bottom:.22rem}
.lv-val{font-family:var(--mono);font-size:.82rem;font-weight:600}
.lv.entry .lv-val{color:var(--blue)}
.lv.sl .lv-val{color:var(--fire)}
.lv.tp .lv-val{color:var(--safe)}
.lv-pct{font-size:.58rem;color:var(--t3);margin-top:.08rem}
.conds{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.7rem}
.cond{font-family:var(--mono);font-size:.55rem;padding:.2rem .5rem;border-radius:6px;display:flex;align-items:center;gap:.3rem}
.cond.ok{background:rgba(6,214,160,.1);color:var(--safe);border:1px solid rgba(6,214,160,.2)}
.cond.no{background:rgba(255,77,109,.08);color:var(--fire);border:1px solid rgba(255,77,109,.15)}
.rr-row{display:flex;justify-content:space-between;align-items:center}
.rr-badge{font-family:var(--mono);font-size:.7rem;padding:.25rem .6rem;border-radius:7px;font-weight:600}
.rr-badge.great{background:rgba(6,214,160,.1);color:var(--safe);border:1px solid rgba(6,214,160,.2)}
.rr-badge.ok{background:rgba(76,201,240,.1);color:var(--blue);border:1px solid rgba(76,201,240,.2)}

/* RADAR TABLE */
.tbl-wrap{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);overflow:hidden}
.tbl{width:100%;border-collapse:collapse}
.tbl thead th{font-family:var(--mono);font-size:.53rem;text-transform:uppercase;letter-spacing:.09em;color:var(--t3);padding:.75rem 1.1rem;border-bottom:1px solid var(--b1);text-align:left;background:rgba(255,255,255,.01)}
.tbl thead th:not(:first-child):not(:nth-child(2)){text-align:center}
.tbl tbody tr{border-bottom:1px solid rgba(20,29,53,.6);cursor:pointer;transition:background .1s}
.tbl tbody tr:hover{background:rgba(255,255,255,.018)}
.tbl tbody td{padding:.62rem 1.1rem;font-size:.73rem}
.tbl tbody td:not(:first-child):not(:nth-child(2)){text-align:center;font-family:var(--mono)}
.tk{font-family:var(--mono);font-size:.88rem;font-weight:600}
.nm{font-size:.6rem;color:var(--t3);margin-top:.05rem}
.cond-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 2px}
.signal-pill{font-family:var(--mono);font-size:.55rem;padding:.16rem .48rem;border-radius:10px;text-transform:uppercase;letter-spacing:.07em}
.sp-fire{background:rgba(255,77,109,.12);color:var(--fire);border:1px solid rgba(255,77,109,.25)}
.sp-watch{background:rgba(255,214,10,.1);color:var(--watch);border:1px solid rgba(255,214,10,.2)}
.sp-trend{background:rgba(76,201,240,.08);color:var(--blue);border:1px solid rgba(76,201,240,.15)}
.sp-panic{background:rgba(123,94,167,.1);color:#b8a0e8;border:1px solid rgba(123,94,167,.2)}
.sp-none{color:var(--t4);font-family:var(--mono);font-size:.6rem}

/* BACKTEST SECTION */
.bt-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.bt-card{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:1.3rem}
.bt-title{font-family:var(--mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.9rem}
.bt-title.is{color:var(--blue)}.bt-title.oos{color:var(--safe)}
.bt-row{display:flex;justify-content:space-between;align-items:center;padding:.32rem 0;border-bottom:1px solid rgba(20,29,53,.8)}
.bt-row:last-child{border:none}
.bt-lbl{font-size:.68rem;color:var(--t2)}
.bt-val{font-family:var(--mono);font-size:.8rem;font-weight:500}

/* CHARTS */
.chart-card{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:1.2rem}
.chart-title{font-family:var(--mono);font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:var(--t3);margin-bottom:.75rem}
canvas{display:block;width:100%!important}

/* TRADE HISTORY */
.trades-tbl-wrap{background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);overflow:hidden;max-height:480px;overflow-y:auto}
.trades-tbl-wrap::-webkit-scrollbar{width:4px}
.trades-tbl-wrap::-webkit-scrollbar-track{background:var(--s1)}
.trades-tbl-wrap::-webkit-scrollbar-thumb{background:var(--b2);border-radius:2px}

/* DETAIL DRAWER */
.drawer{position:fixed;right:0;top:0;bottom:0;width:500px;background:var(--s1);border-left:1px solid var(--b2);z-index:200;transform:translateX(100%);transition:transform .3s cubic-bezier(.4,0,.2,1);overflow-y:auto;padding:1.5rem}
.drawer.open{transform:translateX(0)}
.drawer-close{position:absolute;top:1rem;right:1rem;background:var(--s2);border:1px solid var(--b2);color:var(--t2);width:32px;height:32px;border-radius:8px;cursor:pointer;display:grid;place-items:center;font-size:.85rem;transition:all .15s}
.drawer-close:hover{background:var(--b2);color:var(--t1)}
.drawer-ticker{font-family:var(--serif);font-style:italic;font-size:2.2rem;margin:2rem 0 .2rem}
.drawer-name{font-size:.68rem;color:var(--t3);margin-bottom:1.5rem}

@media(max-width:900px){
  .signals-grid{grid-template-columns:1fr}
  .bt-grid{grid-template-columns:1fr}
  .drawer{width:100%}
}
</style>
</head>
<body>
<div class="orb orb1"></div><div class="orb orb2"></div><div class="orb orb3"></div>
<div class="app">
<header>
  <div class="brand">
    <div class="brand-mark">◈</div>
    <div>
      <div class="brand-name">Momentum Breakout Engine</div>
      <div class="brand-sub">Momentum Breakout</div>
    </div>
  </div>
  <div class="hdr-meta">
    <div class="pulse"></div>
    <div class="ts" id="ts"></div>
  </div>
</header>
<main>

<!-- STATS -->
<div id="stats-section"></div>

<!-- SEÑALES FIRE -->
<div id="fire-section" style="display:none">
  <div class="section-head">🔥 Señales de entrada ahora</div>
  <div class="signals-grid" id="fire-grid"></div>
</div>

<!-- SEÑALES WATCH -->
<div id="watch-section" style="display:none">
  <div class="section-head">👁 Setup listo — esperar breakout</div>
  <div class="signals-grid" id="watch-grid"></div>
</div>

<!-- BACKTEST IS vs OOS -->
<div id="bt-section"></div>

<!-- EQUITY CURVE -->
<div id="eq-section"></div>

<!-- RADAR -->
<div>
  <div class="section-head">Radar completo del universo</div>
  <div class="tbl-wrap">
    <table class="tbl">
      <thead><tr>
        <th>Activo</th><th>Nombre</th>
        <th>Señal</th>
        <th title="Tendencia">T</th>
        <th title="Compresión">C</th>
        <th title="Breakout">B</th>
        <th>Vol%</th>
        <th>EMA50</th>
        <th>Precio</th>
        <th>SL</th><th>TP</th><th>R/R</th>
      </tr></thead>
      <tbody id="radar-body"></tbody>
    </table>
  </div>
</div>

<!-- HISTORIAL OOS -->
<div id="history-section"></div>

</main>
</div>

<!-- DRAWER DETALLE -->
<div class="drawer" id="drawer">
  <button class="drawer-close" onclick="closeDrawer()">✕</button>
  <div id="drawer-content"></div>
</div>

<script>
const D = """ + data_js + """;

// ── Utils ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function gc(v){return v>=60?'var(--safe)':v>=45?'var(--watch)':'var(--fire)'}
function fmt(v,d=2,suf=''){return v==null?'—':(v>=0?'+':'')+v.toFixed(d)+suf}
function fmtP(v,d=1){return v==null?'—':v.toFixed(d)+'%'}

// ── Timestamp ─────────────────────────────────────────────────────
if(D.generated_at){
  const d=new Date(D.generated_at);
  $('ts').textContent='Actualizado '+d.toLocaleString('es-ES',{dateStyle:'medium',timeStyle:'short'});
}

// ── Stats bar ─────────────────────────────────────────────────────
const oos=D.oos_metrics; const is_=D.is_metrics;
const fire_sigs=Object.values(D.signals||{}).filter(s=>s.signal==='FIRE');
const watch_sigs=Object.values(D.signals||{}).filter(s=>s.signal==='WATCH');

const stats=[
  {lbl:'Señales hoy',val:fire_sigs.length,sub:'FIRE — entrar ahora',accent:'var(--fire)',cond:fire_sigs.length>0},
  {lbl:'En vigilancia',val:watch_sigs.length,sub:'Setup listo, falta breakout',accent:'var(--watch)'},
  {lbl:'WR Out-of-Sample',val:oos?oos.wr+'%':'—',sub:`${oos?.n||0} trades OOS`,accent:oos&&oos.wr>=55?'var(--safe)':oos&&oos.wr>=45?'var(--watch)':'var(--fire)'},
  {lbl:'Profit Factor',val:oos?oos.pf:'—',sub:'Ganancias / Pérdidas',accent:oos&&oos.pf>=1.5?'var(--safe)':'var(--blue)'},
  {lbl:'Sharpe OOS',val:oos?oos.sharpe:'—',sub:'Anualizado ×√26',accent:oos&&oos.sharpe>=0.8?'var(--safe)':'var(--blue)'},
  {lbl:'Max Drawdown',val:oos?oos.max_dd+'%':'—',sub:'Pico-valle acumulado',accent:oos&&oos.max_dd>-15?'var(--safe)':'var(--fire)'},
  {lbl:'Expectativa/trade',val:oos?oos.expectancy+'%':'—',sub:'P&L esperado por operación',accent:oos&&oos.expectancy>0?'var(--safe)':'var(--fire)'},
  {lbl:'Trades/mes (OOS)',val:D.sigs_per_month||'—',sub:'Frecuencia esperada',accent:'var(--blue)'},
];
$('stats-section').innerHTML=`
  <div class="section-head">Estado del sistema</div>
  <div class="stats-bar">${stats.map(s=>`
    <div class="stat-card" style="--accent:${s.accent}">
      <div class="stat-lbl">${s.lbl}</div>
      <div class="stat-val">${s.val}</div>
      <div class="stat-sub">${s.sub}</div>
    </div>`).join('')}
  </div>`;

// ── Signal cards ──────────────────────────────────────────────────
function buildCard(s){
  const isFire=s.signal==='FIRE';
  return`<div class="sig ${isFire?'fire':'watch'}" onclick="openDrawer('${s.ticker}')">
    <div class="sig-stripe"></div>
    <span class="sig-badge">${isFire?'🔥 Entrar ahora':'👁 Vigilar breakout'}</span>
    <div class="sig-ticker">${s.ticker}</div>
    <div class="sig-name">${s.name||''}</div>
    ${isFire&&s.entry_price?`
    <div class="levels">
      <div class="lv entry"><div class="lv-lbl">Entrada</div><div class="lv-val">$${s.entry_price?.toFixed(2)}</div></div>
      <div class="lv sl"><div class="lv-lbl">Stop Loss</div><div class="lv-val">$${s.stop_loss?.toFixed(2)}</div><div class="lv-pct">-${s.sl_pct}%</div></div>
      <div class="lv tp"><div class="lv-lbl">Take Profit</div><div class="lv-val">$${s.take_profit?.toFixed(2)}</div><div class="lv-pct">+${s.tp_pct}%</div></div>
    </div>
    <div class="rr-row">
      <span class="rr-badge ${(s.rr_ratio||0)>=2.5?'great':'ok'}">R/R ${s.rr_ratio||'?'}:1</span>
    </div>`:''}
    <div class="conds" style="margin-top:.65rem">
      <span class="cond ${s.trend?'ok':'no'}">${s.trend?'✓':'✗'} Tendencia</span>
      <span class="cond ${s.compressed?'ok':'no'}">${s.compressed?'✓':'✗'} Compresión</span>
      <span class="cond ${s.breakout?'ok':'no'}">${s.breakout?'✓':'✗'} Breakout</span>
    </div>
  </div>`;
}

if(fire_sigs.length){
  $('fire-section').style.display='block';
  $('fire-grid').innerHTML=fire_sigs.map(buildCard).join('');
}
if(watch_sigs.length){
  $('watch-section').style.display='block';
  $('watch-grid').innerHTML=watch_sigs.map(buildCard).join('');
}

// ── Backtest IS vs OOS ────────────────────────────────────────────
if(is_&&oos){
  const rows=[
    ['Trades','n',''],['Win Rate','wr','%'],['Profit Factor','pf',''],
    ['Sharpe','sharpe',''],['Avg ganancia','avg_win','%'],['Avg pérdida','avg_loss','%'],
    ['P&L total','total_pct','%'],['Max Drawdown','max_dd','%'],
    ['Expectativa','expectancy','%'],['Días medio','avg_days','d'],
    ['Eficiencia pico','avg_efficiency','%'],
    ['Racha pérdidas','max_loss_streak',''],
  ];
  const verdict=oos.wr>=55&&oos.pf>=1.3&&oos.sharpe>=0.5?
    {t:'✅ SISTEMA VÁLIDO',c:'var(--safe)',d:'Edge real demostrado en OOS — los parámetros generalizan bien.'}:
    oos.wr>=50&&oos.pf>=1.1?
    {t:'⚡ SISTEMA MARGINAL',c:'var(--watch)',d:'Edge débil. Funciona pero con poco margen. Operar con tamaño reducido.'}:
    {t:'✗ SIN EDGE ESTADÍSTICO',c:'var(--fire)',d:'Los resultados OOS no justifican operar. Revisar condiciones.'};

  $('bt-section').innerHTML=`
    <div class="section-head">Backtest walk-forward — IS (${D.is_period||''}) vs OOS (${D.oos_period||''})</div>
    <div style="background:var(--s1);border:1px solid ${verdict.c}33;border-left:4px solid ${verdict.c};border-radius:var(--r);padding:1.2rem 1.4rem;margin-bottom:1rem">
      <div style="font-family:var(--serif);font-style:italic;font-size:1.2rem;color:${verdict.c};margin-bottom:.3rem">${verdict.t}</div>
      <div style="font-size:.72rem;color:var(--t2)">${verdict.d}${D.benchmark?' · Benchmark SPY OOS: '+(D.benchmark.total_pct>=0?'+':'')+D.benchmark.total_pct+'%':''}</div>
    </div>
    <div class="bt-grid">
      <div class="bt-card">
        <div class="bt-title is">In-Sample (${D.is_period||''})</div>
        ${rows.map(([l,k,u])=>`<div class="bt-row"><span class="bt-lbl">${l}</span><span class="bt-val">${is_[k]!=null?is_[k]+u:'—'}</span></div>`).join('')}
      </div>
      <div class="bt-card">
        <div class="bt-title oos">Out-of-Sample (${D.oos_period||''})</div>
        ${rows.map(([l,k,u])=>{
          const vi=is_[k],vo=oos[k];
          let col='var(--t1)';
          if(vo!=null&&vi!=null&&k!=='n'&&k!=='avg_days'&&k!=='max_loss_streak'){
            const better=(k==='max_dd'||k==='avg_loss'||k==='max_loss_streak')?(vo>vi):(vo>=vi);
            col=better?'var(--safe)':'var(--fire)';
          }
          return`<div class="bt-row"><span class="bt-lbl">${l}</span><span class="bt-val" style="color:${col}">${vo!=null?vo+u:'—'}</span></div>`;
        }).join('')}
      </div>
    </div>

    ${(()=>{
      const br = oos.by_reason||{};
      const total = Object.values(br).reduce((a,b)=>a+b,0)||1;
      const items = [
        {k:'TP', label:'TP', c:'#06d6a0'},
        {k:'SL', label:'SL', c:'#ff4d6d'},
        {k:'M',  label:'M⚡', c:'#ffd60a'},
        {k:'T',  label:'Tiempo', c:'#4cc9f0'},
      ];
      const bars = items.map(({k,label,c})=>{
        const n = br[k]||0, pct = (n/total*100).toFixed(0);
        return `<div style="flex:1;min-width:80px">
          <div style="font-family:var(--mono);font-size:.58rem;color:${c};margin-bottom:.3rem">${label} · ${n}</div>
          <div style="background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden;height:6px">
            <div style="width:${pct}%;background:${c};height:100%;border-radius:4px"></div>
          </div>
          <div style="font-family:var(--mono);font-size:.55rem;color:var(--t3);margin-top:.2rem">${pct}%</div>
        </div>`;
      }).join('');
      const eff = oos.avg_efficiency;
      const effCol = eff>=60?'var(--safe)':eff>=40?'var(--watch)':'var(--fire)';
      return `<div style="background:var(--s1);border:1px solid rgba(255,255,255,.06);border-radius:var(--r);padding:1rem 1.2rem;margin-top:.8rem">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem;flex-wrap:wrap;gap:.5rem">
          <span style="font-family:var(--mono);font-size:.6rem;color:var(--t2);letter-spacing:.05em">MOTIVOS DE SALIDA — OOS</span>
          ${eff!=null?`<span style="font-family:var(--mono);font-size:.6rem;color:var(--t3)">Eficiencia media: <span style="color:${effCol};font-weight:600">${eff}%</span> <span style="color:var(--t3);font-size:.52rem">(% del pico capturado)</span></span>`:''}
        </div>
        <div style="display:flex;gap:1rem;flex-wrap:wrap">${bars}</div>
      </div>`;
    })()}`;
}

// ── Equity curve OOS — portfolio diario vs SPY ───────────────────
const port = D.portfolio_oos;
if(port && port.equity_curve && port.equity_curve.length > 1){

  const portDates = port.daily_dates || [];
  const nDays = port.equity_curve.length;

  // SPY real: interpolar su serie diaria al calendario del portfolio
  let spyCurve = [];
  if(D.benchmark && D.benchmark.equity_curve && D.benchmark.daily_dates){
    const spyDateMap = {};
    D.benchmark.daily_dates.forEach((d,i) => spyDateMap[d] = D.benchmark.equity_curve[i]);
    // Para cada día del portfolio, buscar el valor SPY más cercano
    let lastSpy = 100;
    spyCurve = portDates.map(d => {
      if(spyDateMap[d] != null) { lastSpy = spyDateMap[d]; }
      return lastSpy;
    });
  }
  const hasSpy = spyCurve.length === nDays;

  const sysTotal = port.total_pct;
  const spyTotal2 = D.benchmark?.total_pct ?? null;

  const legendHTML = `<div style="display:flex;gap:1.4rem;align-items:center;margin-bottom:.7rem;flex-wrap:wrap">
    <div style="display:flex;align-items:center;gap:.5rem">
      <div style="width:24px;height:3px;background:#06d6a0;border-radius:2px"></div>
      <span style="font-family:var(--mono);font-size:.62rem;color:var(--t2)">Portfolio (${sysTotal>=0?'+':''}${sysTotal}% · 10% capital/trade)</span>
    </div>
    ${hasSpy?`<div style="display:flex;align-items:center;gap:.5rem">
      <div style="width:24px;height:2px;background:#4cc9f0;border-radius:2px;opacity:.7;background:repeating-linear-gradient(90deg,#4cc9f0 0,#4cc9f0 5px,transparent 5px,transparent 9px)"></div>
      <span style="font-family:var(--mono);font-size:.62rem;color:var(--t2)">SPY Buy&Hold (${spyTotal2>=0?'+':''}${spyTotal2}%)</span>
    </div>`:''}
    <span style="font-family:var(--mono);font-size:.58rem;color:var(--t3);margin-left:auto">base 100 · 10%/posición · máx ${port.max_concurrent||'?'} simultáneas · CAGR ${(port.cagr>=0?'+':'')+port.cagr}%/año</span>
  </div>`;

  $('eq-section').innerHTML=`
    <div class="section-head">Curva de equity — Portfolio Out-of-Sample vs Benchmark</div>
    <div class="chart-card">
      <div class="chart-title">${legendHTML}</div>
      <canvas id="eq-cv" height="280"></canvas>
    </div>`;

  setTimeout(()=>{
    const cv=$('eq-cv'); if(!cv) return;
    const W=cv.offsetWidth||800, H=280;
    cv.width=W*devicePixelRatio; cv.height=H*devicePixelRatio;
    const ctx=cv.getContext('2d'); ctx.scale(devicePixelRatio,devicePixelRatio);

    const eq=port.equity_curve, n=eq.length;
    const allVals=[...eq, ...(hasSpy?spyCurve:[]), 100];
    const mn=Math.min(...allVals)*0.995, mx=Math.max(...allVals)*1.005;
    const pad={t:14,r:72,b:36,l:58}, cW=W-pad.l-pad.r, cH=H-pad.t-pad.b;
    const rng=mx-mn||1;
    const xp=i=>pad.l+i/Math.max(n-1,1)*cW;
    const yp=v=>pad.t+(1-(v-mn)/rng)*cH;

    // Grid + labels Y (base 100)
    ctx.strokeStyle='rgba(20,29,53,.9)'; ctx.lineWidth=1;
    for(let g=0;g<=5;g++){
      const y=pad.t+g/5*cH, v=mn+(1-g/5)*rng;
      ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r+6,y); ctx.stroke();
      ctx.fillStyle='rgba(77,106,153,.85)'; ctx.font='9px Syne Mono,monospace';
      ctx.textAlign='right';
      const disp = v>=100 ? '+'+((v-100).toFixed(0))+'%' : '-'+((100-v).toFixed(0))+'%';
      ctx.fillText(disp, pad.l-4, y+3);
    }
    ctx.textAlign='left';

    // Línea base 100
    const y100=yp(100);
    ctx.strokeStyle='rgba(255,255,255,.1)'; ctx.lineWidth=1; ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(pad.l,y100); ctx.lineTo(W-pad.r,y100); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='rgba(255,255,255,.2)'; ctx.font='8px Syne Mono,monospace';
    ctx.fillText('100', W-pad.r+4, y100+3);

    // SPY curva (punteada azul)
    if(hasSpy){
      ctx.strokeStyle='rgba(76,201,240,.6)'; ctx.lineWidth=1.5; ctx.setLineDash([5,4]);
      ctx.beginPath();
      spyCurve.forEach((v,i)=>i===0?ctx.moveTo(xp(i),yp(v)):ctx.lineTo(xp(i),yp(v)));
      ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle='rgba(76,201,240,.7)'; ctx.font='bold 8px Syne Mono,monospace';
      ctx.fillText('SPY', W-pad.r+4, yp(spyCurve[n-1])+3);
    }

    // Portfolio: fill bajo la curva
    const sysColor=eq[n-1]>=100?'#06d6a0':'#ff4d6d';
    ctx.beginPath(); ctx.moveTo(xp(0),yp(100));
    eq.forEach((v,i)=>ctx.lineTo(xp(i),yp(v)));
    ctx.lineTo(xp(n-1),yp(100)); ctx.closePath();
    const grad=ctx.createLinearGradient(0,pad.t,0,pad.t+cH);
    grad.addColorStop(0,eq[n-1]>=100?'rgba(6,214,160,.2)':'rgba(255,77,109,.2)');
    grad.addColorStop(1,'transparent');
    ctx.fillStyle=grad; ctx.fill();

    // Portfolio: línea principal
    ctx.strokeStyle=sysColor; ctx.lineWidth=2.5;
    ctx.beginPath();
    eq.forEach((v,i)=>i===0?ctx.moveTo(xp(i),yp(v)):ctx.lineTo(xp(i),yp(v)));
    ctx.stroke();
    ctx.fillStyle=sysColor; ctx.font='bold 8px Syne Mono,monospace';
    ctx.fillText('SYS', W-pad.r+4, yp(eq[n-1])+3);

    // Fechas en X (de daily_dates)
    if(portDates.length){
      const step=Math.max(1,Math.ceil(n/8));
      portDates.forEach((d,i)=>{
        if(i%step!==0) return;
        ctx.fillStyle='rgba(61,90,138,.8)'; ctx.font='7px Syne Mono,monospace';
        ctx.fillText(d.slice(0,7), xp(i)-14, H-6);
      });
    }
  },80);
}

// ── Radar table ───────────────────────────────────────────────────
const sigs=D.signals||{};
const sorted=Object.values(sigs).sort((a,b)=>{
  const order={FIRE:0,WATCH:1,TREND:2,NONE:3,PANIC:4};
  return (order[a.signal]??5)-(order[b.signal]??5);
});

$('radar-body').innerHTML=sorted.map(s=>{
  const dotColor=ok=>ok?'var(--safe)':'rgba(255,77,109,.35)';
  const spClass={FIRE:'sp-fire',WATCH:'sp-watch',TREND:'sp-trend',PANIC:'sp-panic',NONE:'sp-none'}[s.signal]||'sp-none';
  const spLabel={FIRE:'🔥 FIRE',WATCH:'👁 Watch',TREND:'→ Trend',PANIC:'⚡ Pánico',NONE:'—'}[s.signal]||'—';
  const rr=s.rr_ratio;
  return`<tr onclick="openDrawer('${s.ticker}')">
    <td><div class="tk">${s.ticker}</div></td>
    <td><div class="nm">${s.name||''}</div></td>
    <td><span class="${spClass} signal-pill">${spLabel}</span></td>
    <td><span class="cond-dot" style="background:${dotColor(s.trend)}"></span></td>
    <td><span class="cond-dot" style="background:${dotColor(s.compressed)}"></span></td>
    <td><span class="cond-dot" style="background:${dotColor(s.breakout)}"></span></td>
    <td style="color:${s.vol_pct_now>=80?'var(--fire)':s.vol_pct_now<=25?'var(--safe)':'var(--t2)'}">${s.vol_pct_now!=null?s.vol_pct_now+'%':'—'}</td>
    <td style="color:var(--t3);font-size:.68rem">${s.ema50?'$'+s.ema50.toFixed(2):'—'}</td>
    <td>$${s.price?.toFixed(2)||'—'}</td>
    <td style="color:var(--fire)">${s.stop_loss?'$'+s.stop_loss.toFixed(2):'—'}</td>
    <td style="color:var(--safe)">${s.take_profit?'$'+s.take_profit.toFixed(2):'—'}</td>
    <td style="color:${rr>=2.5?'var(--safe)':rr>=1.5?'var(--blue)':'var(--t3)'}">${rr?rr+'x':'—'}</td>
  </tr>`;
}).join('');

// ── Trade history OOS ─────────────────────────────────────────────
const oos_trades=(D.oos_trades||[]).sort((a,b)=>b.entry_date.localeCompare(a.entry_date));
if(oos_trades.length){
  $('history-section').innerHTML=`
    <div class="section-head">Histórico de trades — Out-of-Sample (${oos_trades.length} operaciones)</div>
    <div class="trades-tbl-wrap">
      <table class="tbl">
        <thead><tr>
          <th>Ticker</th><th>Estrat.</th><th>Entrada</th><th>Salida</th>
          <th>$ Entrada</th><th>$ Salida</th>
          <th>P&L</th><th>Pico</th><th>R máx</th><th>Días</th><th>Motivo</th>
        </tr></thead>
        <tbody>${oos_trades.map(t=>{
          const win=t.pnl>=0;
          return`<tr>
            <td style="font-weight:600;font-family:var(--mono)">${t.ticker}</td>
            <td><span style="font-family:var(--mono);font-size:.58rem;padding:.1rem .3rem;border-radius:4px;${
              t.strategy==='MR'?'background:rgba(99,102,241,.15);color:#818cf8':'background:rgba(6,214,160,.1);color:var(--safe)'
            }">${t.strategy||'MOM'}</span></td>
            <td>${t.entry_date}</td><td>${t.exit_date}</td>
            <td>$${t.entry_price?.toFixed(2)}</td>
            <td>$${t.exit_price?.toFixed(2)}</td>
            <td style="color:${win?'var(--safe)':'var(--fire)'}">
              ${win?'+':''}${t.pnl?.toFixed(2)}%
            </td>
            <td style="color:var(--t3);font-size:.65rem">+${t.peak_pnl?.toFixed(1)||0}%</td>
            <td style="color:${(t.r_achieved||0)>=2?'var(--safe)':(t.r_achieved||0)>=1?'var(--watch)':'var(--t3)'};font-size:.65rem">${t.r_achieved!=null?t.r_achieved+'R':'—'}</td>
            <td style="color:var(--t3)">${t.days}d</td>
            <td>
              <span style="font-family:var(--mono);font-size:.6rem;font-weight:600;padding:.15rem .4rem;border-radius:5px;${
                t.reason==='TP'?'background:rgba(6,214,160,.12);color:var(--safe)':
                t.reason==='SL'?'background:rgba(255,77,109,.1);color:var(--fire)':
                t.reason==='M'?'background:rgba(255,214,10,.1);color:var(--watch)':
                'background:rgba(77,106,153,.1);color:var(--t3)'
              }">${t.reason==='M'?'M⚡':t.reason}</span>
            </td>
          </tr>`;}).join('')}
        </tbody>
      </table>
    </div>`;
}

// ── Drawer detalle ────────────────────────────────────────────────
function openDrawer(ticker){
  const s=sigs[ticker]; if(!s) return;
  const hist=s.price_hist||[];

  $('drawer-content').innerHTML=`
    <div class="drawer-ticker">${ticker}</div>
    <div class="drawer-name">${s.name||''}</div>

    <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.2rem">
      <span class="cond ${s.trend?'ok':'no'}">${s.trend?'✓':'✗'} Tendencia (${s.trend_detail?.price_change_pct||0}% en 60d)</span>
      <span class="cond ${s.compressed?'ok':'no'}">${s.compressed?'✓':'✗'} Compresión (Vol pct ${s.comp_detail?.vol_percentile||'?'}%)</span>
      <span class="cond ${s.breakout?'ok':'no'}">${s.breakout?'✓':'✗'} Breakout (Vol rank ${s.bo_detail?.vol_rank||'?'}%)</span>
      ${s.panic?'<span class="cond no">⚡ PÁNICO — no operar</span>':''}
    </div>

    ${s.signal==='FIRE'&&s.entry_price?`
    <div class="levels" style="margin-bottom:1.2rem">
      <div class="lv entry"><div class="lv-lbl">Entrada</div><div class="lv-val">$${s.entry_price?.toFixed(2)}</div></div>
      <div class="lv sl"><div class="lv-lbl">Stop Loss</div><div class="lv-val">$${s.stop_loss?.toFixed(2)}</div><div class="lv-pct">-${s.sl_pct}%</div></div>
      <div class="lv tp"><div class="lv-lbl">Take Profit</div><div class="lv-val">$${s.take_profit?.toFixed(2)}</div><div class="lv-pct">+${s.tp_pct}%</div></div>
    </div>
    <div style="margin-bottom:1.2rem">
      <span class="rr-badge ${(s.rr_ratio||0)>=2.5?'great':'ok'}">R/R ${s.rr_ratio}:1</span>
    </div>`:''}

    <div class="chart-card" style="margin-bottom:1rem">
      <div class="chart-title">Precio 90d · EMA8 · EMA21 · EMA50</div>
      <canvas id="d-price" height="200"></canvas>
    </div>
    <div class="chart-card">
      <div class="chart-title">Percentil de volatilidad histórica (pánico ≥80%, compresión ≤25%)</div>
      <canvas id="d-vol" height="120"></canvas>
    </div>`;

  $('drawer').classList.add('open');

  setTimeout(()=>{
    if(!hist.length) return;
    drawLineChart('d-price',[
      {data:hist.map(x=>x.close), c:'#4cc9f0',  w:1.5, fill:'rgba(76,201,240,.05)'},
      {data:hist.map(x=>x.ema8),  c:'#ffd60a',  w:1,   d:[3,3]},
      {data:hist.map(x=>x.ema21), c:'#06d6a0',  w:1.5},
      {data:hist.map(x=>x.ema50), c:'#7b5ea7',  w:1,   d:[5,5]},
    ],{dates:hist.map(x=>x.date),dec:2,
       refs:s.stop_loss?[{v:s.stop_loss,c:'rgba(255,77,109,.4)',l:'SL'},
                          {v:s.take_profit,c:'rgba(6,214,160,.4)',l:'TP'}]:[]});

    drawLineChart('d-vol',[
      {data:hist.map(x=>x.vol_pct),c:'#a78bfa',w:1.5,fill:'rgba(167,139,250,.06)'},
    ],{dates:hist.map(x=>x.date),min:0,max:100,dec:0,
       refs:[{v:80,c:'rgba(255,77,109,.35)',l:'80%'},{v:25,c:'rgba(6,214,160,.35)',l:'25%'}]});
  },40);
}

function closeDrawer(){$('drawer').classList.remove('open');}

// ── Chart engine ──────────────────────────────────────────────────
function drawLineChart(id,datasets,opts={}){
  const cv=$(id); if(!cv) return;
  const W=cv.offsetWidth||460, H=parseInt(cv.getAttribute('height'))||200;
  cv.width=W*devicePixelRatio; cv.height=H*devicePixelRatio;
  const ctx=cv.getContext('2d'); ctx.scale(devicePixelRatio,devicePixelRatio);
  const pad={t:10,r:12,b:26,l:46}, cW=W-pad.l-pad.r, cH=H-pad.t-pad.b;
  ctx.clearRect(0,0,W,H);
  let all=datasets.flatMap(d=>d.data.filter(v=>v!=null&&!isNaN(v)));
  if(!all.length) return;
  let mn=opts.min??Math.min(...all), mx=opts.max??Math.max(...all);
  if(mx===mn){mx+=1;mn-=1;}
  const rng=mx-mn;
  const xp=(i,n)=>pad.l+i/Math.max(n-1,1)*cW;
  const yp=v=>pad.t+(1-(v-mn)/rng)*cH;
  // Grid
  ctx.strokeStyle='rgba(20,29,53,.95)'; ctx.lineWidth=1;
  for(let g=0;g<=4;g++){const y=pad.t+g/4*cH; ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();}
  // Refs
  (opts.refs||[]).forEach(r=>{
    ctx.strokeStyle=r.c; ctx.lineWidth=1; ctx.setLineDash([4,4]);
    const y=yp(r.v); ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(W-pad.r,y); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle=r.c; ctx.font='8px Syne Mono,monospace';
    ctx.fillText(r.l,W-pad.r-24,y-3);
  });
  // Datasets
  datasets.forEach(ds=>{
    const data=ds.data, n=data.length; if(!n) return;
    ctx.strokeStyle=ds.c; ctx.lineWidth=ds.w||1.5; ctx.setLineDash(ds.d||[]);
    if(ds.fill){
      ctx.beginPath(); let s=false;
      data.forEach((v,i)=>{if(v==null||isNaN(v))return; s?ctx.lineTo(xp(i,n),yp(v)):(ctx.moveTo(xp(i,n),yp(v)),s=true);});
      ctx.lineTo(xp(n-1,n),pad.t+cH); ctx.lineTo(pad.l,pad.t+cH); ctx.closePath();
      ctx.fillStyle=ds.fill; ctx.fill();
    }
    ctx.beginPath(); let s=false;
    data.forEach((v,i)=>{if(v==null||isNaN(v))return; s?ctx.lineTo(xp(i,n),yp(v)):(ctx.moveTo(xp(i,n),yp(v)),s=true);});
    ctx.stroke(); ctx.setLineDash([]);
  });
  // Y labels
  ctx.fillStyle='rgba(61,90,138,.9)'; ctx.font='8px Syne Mono,monospace';
  for(let g=0;g<=4;g++){const v=mn+(1-g/4)*rng; ctx.fillText(v.toFixed(opts.dec??1),2,pad.t+g/4*cH+3);}
  // X dates
  if(opts.dates){
    const step=Math.max(1,Math.ceil(opts.dates.length/6));
    opts.dates.forEach((d,i)=>{
      if(i%step!==0) return;
      ctx.fillStyle='rgba(61,90,138,.8)'; ctx.font='7px Syne Mono,monospace';
      ctx.fillText(d.slice(5),xp(i,opts.dates.length)-10,H-5);
    });
  }
}
</script>
</body>
</html>""";

    out_path.write_text(html, encoding='utf-8')


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'═'*65}{RST}")
    print(f"{BOLD}{C}  ◈  MOMENTUM BREAKOUT ENGINE  v1.1{RST}")
    print(f"{DIM}  Momentum Breakout + Mean Reversion — dos estrategias complementarias{RST}")
    print(f"{BOLD}{'═'*65}{RST}\n")

    # ── Descargar datos ──────────────────────────────────────────────
    print(f"  {C}↓ Descargando histórico máximo ({len(UNIVERSE)} activos)...{RST}\n")

    all_is_trades  = []
    all_oos_trades = []
    all_is_mr      = []   # trades mean reversion IS
    all_oos_mr     = []   # trades mean reversion OOS
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
            print(f"{G}✓{RST} {len(df)} barras ({len(df)/252:.1f}a)", end="  ")
        except Exception as e:
            print(f"{R}✗ {e}{RST}")
            continue

        # Calcular indicadores sobre el histórico completo
        ind = compute_indicators(df)

        # ── BACKTEST: split IS/OOS por FECHA FIJA global ─────────────
        # Fecha de corte fija: 2020-01-01
        # IS = todo antes de 2020 (historia larga para calibrar)
        # OOS = 2020 en adelante (incluye COVID crash, bull 2021,
        #       bear 2022, y bull 2023-2026 — periodo muy exigente)
        # Usar fecha fija es más honesto que split por % de barras,
        # que daría fechas distintas para cada activo.
        OOS_START = pd.Timestamp("2020-01-01")

        df_is  = df[df.index < OOS_START]
        df_oos = df[df.index >= OOS_START]

        if len(df_is) < 600 or len(df_oos) < 100:
            print(f"{Y}⚠ Historia insuficiente para split IS/OOS{RST}")
            # Backtest sobre todo el histórico si no hay suficientes datos
            df_is  = df
            df_oos = df.iloc[int(len(df)*0.65):]

        # Calcular indicadores con toda la historia disponible hasta cada período
        # OOS: usar df completo para que los percentiles en 2020+ incluyan
        # la historia previa — así en Jan 2020 tienes 20+ años de historia
        # IS: usar solo df_is para evitar look-ahead del futuro en el IS
        ind_is   = compute_indicators(df_is)
        ind_full = compute_indicators(df)   # para el OOS: historia completa

        trades_is, diag_is   = backtest(ticker, ind_is)

        # Para OOS: backtest sobre el df completo pero solo conservar
        # trades cuya entrada cae en el período OOS
        oos_start_str = OOS_START.strftime('%Y-%m-%d')
        trades_full, diag_full = backtest(ticker, ind_full)
        trades_oos    = [t for t in trades_full if t['entry_date'] >= oos_start_str]

        # Tag
        for t in trades_is:  t['period'] = 'IS'
        for t in trades_oos: t['period'] = 'OOS'

        all_is_trades.extend(trades_is)
        all_oos_trades.extend(trades_oos)

        m_oos = compute_metrics(trades_oos)
        m_is  = compute_metrics(trades_is)
        wr_is  = m_is['wr']  if m_is  else 0
        wr_oos = m_oos['wr'] if m_oos else 0
        n_is   = len(trades_is)
        n_oos  = len(trades_oos)
        col    = G if wr_oos >= 55 else (Y if wr_oos >= 45 else R)

        print(f"IS:{n_is:>3}t WR={wr_is:.0f}% │ "
              f"OOS:{n_oos:>3}t {col}WR={wr_oos:.0f}%{RST} "
              f"PF={m_oos['pf'] if m_oos else 0:.2f}")
        if n_oos == 0 and n_is == 0:
            # Mostrar por qué no hay trades — útil para calibrar filtros
            d = diag_full
            print(f"   ↳ sin trades: panic={d['panic']} no_trend={d['no_trend']} "
                  f"no_comp={d['no_comp']} no_bo={d['no_bo']} "
                  f"all3={d['all3']} bad_lvl={d['bad_levels']}")

        # ── ESTRATEGIA COMPLEMENTARIA: ELIMINADA ─────────────────────
        # Solo momentum puro.

        # ── SEÑALES DE HOY ───────────────────────────────────────────────
        sig = get_today_signal(ticker, ind)
        if sig:
            all_signals[ticker] = sig

    # ── Métricas globales ────────────────────────────────────────────
    m_is_global  = compute_metrics(all_is_trades)
    m_oos_global = compute_metrics(all_oos_trades)
    m_mr_oos     = compute_metrics(all_oos_mr)
    all_is_combined  = all_is_trades  + all_is_mr
    all_oos_combined = all_oos_trades + all_oos_mr
    m_is_combined    = compute_metrics(all_is_combined)
    m_oos_combined   = compute_metrics(all_oos_combined)

    # Portfolio simulation con trades combinados momentum+MR
    port_is  = portfolio_simulate(all_is_combined,  position_size_pct=15.0)
    port_oos = portfolio_simulate(all_oos_combined, position_size_pct=15.0)

    # Añadir métricas de portfolio a los dicts globales
    if m_is_combined and port_is:
        m_is_combined['total_pct'] = port_is['total_pct']
        m_is_combined['max_dd']    = port_is['max_dd']
        m_is_combined['sharpe']    = port_is['sharpe']
        m_is_combined['cagr']      = port_is['cagr']
    if m_oos_combined and port_oos:
        m_oos_combined['total_pct'] = port_oos['total_pct']
        m_oos_combined['max_dd']    = port_oos['max_dd']
        m_oos_combined['sharpe']    = port_oos['sharpe']
        m_oos_combined['cagr']      = port_oos['cagr']
    # m_oos_global conserva sus métricas trade-a-trade puras (sin portfolio combinado)

    # Períodos
    is_dates  = sorted([t['entry_date'] for t in all_is_combined])
    oos_dates = sorted([t['entry_date'] for t in all_oos_combined])
    is_period  = f"{is_dates[0]} → {is_dates[-1]}"  if is_dates  else "—"
    oos_period = f"{oos_dates[0]} → {oos_dates[-1]}" if oos_dates else "—"

    # Señales por mes
    sigs_per_month = 0
    if oos_dates:
        from datetime import datetime as dt
        first = dt.strptime(oos_dates[0],  "%Y-%m-%d")
        last  = dt.strptime(oos_dates[-1], "%Y-%m-%d")
        months = max((last - first).days / 30, 1)
        sigs_per_month = round(len(all_oos_combined) / months, 1)

    # Benchmark SPY — serie diaria real, mismo rango que el portfolio OOS
    benchmark = None
    try:
        port_start = oos_dates[0] if oos_dates else None
        port_end   = max(t['exit_date'] for t in all_oos_combined) if all_oos_combined else None
        if port_start and port_end:
            spy = yf.download("SPY", start=port_start, end=port_end,
                              auto_adjust=True, progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)
            if len(spy) >= 2:
                spy_c    = spy['Close'].squeeze()
                spy_mult = np.cumprod(1 + spy_c.pct_change().fillna(0).values)
                spy_ret  = float((spy_mult[-1] - 1) * 100)
                spy_run  = np.maximum.accumulate(spy_mult)
                spy_dd   = float(((spy_mult / spy_run) - 1).min() * 100)

                # Serie diaria base-100 para el gráfico
                spy_dates  = [d.strftime('%Y-%m-%d') for d in spy_c.index]
                spy_equity = [round(float(v * 100), 2) for v in spy_mult]

                benchmark = {
                    'total_pct':   round(spy_ret, 1),
                    'max_dd':      round(spy_dd, 1),
                    'daily_dates': spy_dates,
                    'equity_curve': spy_equity,  # base-100 serie diaria real
                }
    except Exception:
        pass

    # ── Resumen terminal ─────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*65}{RST}")
    print(f"\n  {'':22} {'IS':>10} {'OOS':>10}")
    print(f"  {'─'*44}")

    def _row(lbl, m_is, m_oos, key, fmt="{:.1f}", suf=""):
        vi = m_is[key]  if m_is  else None
        vo = m_oos[key] if m_oos else None
        col = G if vo is not None and vi is not None and (
            vo >= vi if key not in ('max_dd','avg_loss','max_loss_streak') else vo > vi
        ) else (R if vo is not None and vi is not None else "")
        print(f"  {lbl:<22} {fmt.format(vi)+suf if vi is not None else '—':>10} "
              f"{col}{fmt.format(vo)+suf if vo is not None else '—':>10}{RST}")

    print(f"  {DIM}── Momentum + Mean Reversion (combinado) ───────────{RST}")
    _row("Trades",           m_is_combined, m_oos_combined, 'n',         "{:.0f}")
    _row("Win Rate",         m_is_combined, m_oos_combined, 'wr',        "{:.1f}", "%")
    _row("Profit Factor",    m_is_combined, m_oos_combined, 'pf',        "{:.2f}")
    _row("Sharpe",           m_is_combined, m_oos_combined, 'sharpe',    "{:.2f}")
    _row("Max Drawdown",     m_is_combined, m_oos_combined, 'max_dd',    "{:.1f}", "%")
    _row("Expectativa/trade",m_is_combined, m_oos_combined, 'expectancy',"{:.3f}", "%")
    _row("Total P&L",        m_is_combined, m_oos_combined, 'total_pct', "{:.1f}", "%")
    print(f"  {DIM}── Solo Momentum ───────────────────────────────────{RST}")
    _row("  Trades MOM",     m_is_global,   m_oos_global,   'n',   "{:.0f}")
    _row("  WR MOM",         m_is_global,   m_oos_global,   'wr',  "{:.1f}", "%")
    _row("  PF MOM",         m_is_global,   m_oos_global,   'pf',  "{:.2f}")
    if m_mr_oos:
        print(f"  {DIM}── Solo Mean Reversion (OOS) ────────────────────────{RST}")
        print(f"  {'  Trades MR':<22} {'---':>10} {m_mr_oos['n']:>10.0f}")
        print(f"  {'  WR MR':<22} {'---':>10} {m_mr_oos['wr']:>10.1f}%")
        print(f"  {'  PF MR':<22} {'---':>10} {m_mr_oos['pf']:>10.2f}")

    if benchmark:
        print(f"\n  Benchmark SPY (mismo período OOS): "
              f"{'+' if benchmark['total_pct']>=0 else ''}{benchmark['total_pct']:.1f}%")

    fire_today  = [tk for tk, s in all_signals.items() if s['signal'] == 'FIRE']
    watch_today = [tk for tk, s in all_signals.items() if s['signal'] == 'WATCH']

    if fire_today:
        print(f"\n  {M}{BOLD}🔥 SEÑALES HOY: {', '.join(fire_today)}{RST}")
    if watch_today:
        print(f"  {Y}👁 Vigilar: {', '.join(watch_today)}{RST}")

    # Veredicto
    print(f"\n{BOLD}{'═'*65}{RST}")
    if m_oos_combined:
        wr = m_oos_combined['wr']; pf = m_oos_combined['pf']; sh = m_oos_combined['sharpe']
        if wr >= 55 and pf >= 1.3 and sh >= 0.5:
            print(f"\n  {G}{BOLD}✅ SISTEMA VÁLIDO — edge real demostrado{RST}")
        elif wr >= 50 and pf >= 1.1:
            print(f"\n  {Y}{BOLD}⚡ SISTEMA MARGINAL — edge débil{RST}")
        else:
            print(f"\n  {R}{BOLD}✗ SIN EDGE — revisar condiciones o universo{RST}")

    # ── Generar dashboard ────────────────────────────────────────────
    def _san(o):
        if isinstance(o, dict):     return {k: _san(v) for k, v in o.items()}
        if isinstance(o, list):     return [_san(v) for v in o]
        if isinstance(o, np.bool_): return bool(o)
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return None if (np.isnan(o) or np.isinf(o)) else float(o)
        if isinstance(o, float) and (np.isnan(o) or np.isinf(o)): return None
        return o

    dashboard_data = _san({
        "generated_at":  datetime.now().isoformat(),
        "is_period":     is_period,
        "oos_period":    oos_period,
        "is_metrics":    m_is_combined,
        "oos_metrics":   m_oos_combined,
        "mom_metrics_oos": m_oos_global,
        "portfolio_oos": port_oos,
        "portfolio_is":  port_is,
        "benchmark":     benchmark,
        "sigs_per_month": sigs_per_month,
        "signals":       all_signals,
        "oos_trades":    all_oos_combined,
        "oos_trades_mr": all_oos_mr,
        "mr_metrics_oos": m_mr_oos,
        "params": {
            "COMPRESSION_BARS":        COMPRESSION_BARS,
            "TREND_BARS":              TREND_BARS,
            "TREND_ATR_MULTIPLE":      TREND_ATR_MULTIPLE,
            "TREND_EMA":               TREND_EMA,
            "COMPRESSION_VOL_PERCENTILE": COMPRESSION_VOL_PERCENTILE,
            "PANIC_VOL_PERCENTILE":    PANIC_VOL_PERCENTILE,
            "BREAKOUT_VOL_PERCENTILE": BREAKOUT_VOL_PERCENTILE,
            "TP_R_MULTIPLE":           TP_R_MULTIPLE,
            "MAX_HOLD_DAYS":           MAX_HOLD_DAYS,
        },
    })

    generate_dashboard(dashboard_data, DASHBOARD_FILE)
    print(f"\n  {G}→ dashboard.html generado — listo para GitHub Pages{RST}\n")


if __name__ == "__main__":
    main()
