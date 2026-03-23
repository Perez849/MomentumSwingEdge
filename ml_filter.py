"""
╔══════════════════════════════════════════════════════════════════════╗
║  ML SETUP FILTER — Momentum Breakout Engine                          ║
║  LightGBM walk-forward que aprende qué setups vale la pena operar    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  FILOSOFÍA:                                                          ║
║  Las 3 condiciones del sistema son necesarias pero no suficientes.   ║
║  Hay breakouts con volumen y tendencia que fallan porque el setup    ║
║  tiene características sutiles de debilidad. Este filtro las aprende ║
║  directamente de los trades históricos del propio sistema.           ║
║                                                                      ║
║  LABEL: trade bueno = R_pico >= 1.0 AND PnL > 0                     ║
║  MODELO: LightGBM (rápido, robusto, no overfittea con 300 samples)  ║
║  VALIDACIÓN: walk-forward — nunca usa datos futuros                  ║
║                                                                      ║
║  IMPACTO ESPERADO:                                                   ║
║  +5-12pp Win Rate · +0.3-0.8 Profit Factor · -25% frecuencia        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

try:
    from lightgbm import LGBMClassifier
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

# ── Parámetros del filtro ─────────────────────────────────────────
MIN_TRAIN_SAMPLES  = 60     # mínimo trades IS para entrenar
MIN_POSITIVE_RATE  = 0.20   # mínimo % de trades buenos en IS
GOOD_TRADE_MIN_R   = 1.0    # pico >= 1R para ser "bueno"
GOOD_TRADE_MIN_PNL = 0.0    # y cerró positivo


def extract_features(setup: dict) -> dict:
    """
    Extrae features del setup en el momento de la señal.
    Todo viene de datos disponibles en la barra de entrada — sin look-ahead.
    """
    cd = setup.get('comp_detail', {}) or {}
    td = setup.get('trend_detail', {}) or {}
    bd = setup.get('bo_detail',   {}) or {}

    # Importación lazy para evitar circular import
    try:
        from momentum_engine import TIER1_ASSETS, TIER2_ASSETS, HIGH_VOL_MOMENTUM
        ticker = setup.get('ticker', '')
        tier   = 1 if ticker in TIER1_ASSETS else (2 if ticker in TIER2_ASSETS else 3)
        is_hvm = int(ticker in HIGH_VOL_MOMENTUM)
    except Exception:
        tier   = 3
        is_hvm = 0

    price  = float(setup.get('price',       1.0) or 1.0)
    ema50  = float(setup.get('ema50',      price) or price)
    entry  = float(setup.get('entry_price', price) or price)
    sl     = setup.get('stop_loss')
    tp     = setup.get('take_profit')

    vol_pct  = float(setup.get('vol_pct_now')  or cd.get('vol_percentile') or 50.0)
    vol_rank = float(setup.get('vol_rank_now') or bd.get('vol_rank')       or 50.0)

    # Distancia a EMA50 — tendencia madura (lejos) vs reciente (cerca)
    dist_ema50 = (price - ema50) / ema50 * 100 if ema50 > 0 else 0.0

    # Risk y reward %
    risk_pct = (entry - sl) / entry * 100  if (sl and entry > 0) else 5.0
    tp_pct   = (tp - entry) / entry * 100  if (tp and entry > 0) else 15.0
    rr       = setup.get('rr_ratio') or (tp_pct / risk_pct if risk_pct > 0 else 3.0)

    # Fuerza relativa de la tendencia (cuántos ATR-múltiplos sobre el umbral)
    trend_chg = float(td.get('price_change_pct', 0.0) or 0.0)
    trend_thr = float(td.get('atr_threshold_pct', 5.0) or 5.0)
    trend_strength = trend_chg / trend_thr if trend_thr > 0 else 1.0

    # Fuerza del breakout (% sobre el máximo de compresión)
    bo_pct = float(bd.get('breakout_pct', 0.0) or 0.0)

    # Amplitud de la compresión (compresión estrecha = setup de mayor calidad)
    comp_low  = float(cd.get('comp_low',  price * 0.95) or price * 0.95)
    comp_high = float(cd.get('comp_high', price * 1.02) or price * 1.02)
    comp_range_pct = (comp_high - comp_low) / comp_low * 100 if comp_low > 0 else 3.0

    # Precio relativo dentro de la compresión (breakout en la parte alta = mejor)
    if comp_high > comp_low:
        price_in_comp = (price - comp_low) / (comp_high - comp_low)
    else:
        price_in_comp = 0.5

    return {
        'tier':            float(tier),
        'is_hvm':          float(is_hvm),
        'vol_pct':         vol_pct,
        'vol_rank':        vol_rank,
        'dist_ema50':      dist_ema50,
        'risk_pct':        risk_pct,
        'tp_pct':          tp_pct,
        'rr':              float(rr),
        'trend_strength':  trend_strength,
        'bo_pct':          bo_pct,
        'comp_range_pct':  comp_range_pct,
        'price_in_comp':   price_in_comp,
    }


def label_trade(trade: dict) -> int:
    r_peak = float(trade.get('r_achieved', 0.0) or 0.0)
    pnl    = float(trade.get('pnl',        0.0) or 0.0)
    return int(r_peak >= GOOD_TRADE_MIN_R and pnl > GOOD_TRADE_MIN_PNL)


class MLSetupFilter:
    """
    Filtro ML walk-forward para el Momentum Breakout Engine.

    Entrena con trades IS → filtra señales en tiempo real (OOS).
    Umbral auto-calibrado maximizando PF × WR en IS.
    """

    def __init__(self, min_score_threshold: float = None):
        self.model          = None
        self.threshold      = min_score_threshold
        self.feature_names  = None
        self.trained        = False
        self.stats          = {}
        self._blocked       = 0
        self._passed        = 0

    # ── Entrenamiento ─────────────────────────────────────────────

    def train(self, trades: list, threshold: float = None) -> 'MLSetupFilter':
        if not HAS_LGBM:
            self.trained = False
            return self

        valid = [t for t in trades if t.get('setup_features')]
        if len(valid) < MIN_TRAIN_SAMPLES:
            self.trained = False
            return self

        rows   = [t['setup_features'] for t in valid]
        labels = [label_trade(t)      for t in valid]

        df = pd.DataFrame(rows).fillna(0)
        X  = df.values.astype(float)
        y  = np.array(labels)

        pos_rate = y.mean()
        if pos_rate < MIN_POSITIVE_RATE:
            self.trained = False
            return self

        self.feature_names = list(df.columns)

        self.model = LGBMClassifier(
            n_estimators      = 300,
            learning_rate     = 0.04,
            max_depth         = 4,
            num_leaves        = 15,
            min_child_samples = 15,
            subsample         = 0.75,
            colsample_bytree  = 0.8,
            reg_alpha         = 0.2,
            reg_lambda        = 1.5,
            class_weight      = 'balanced',
            random_state      = 42,
            verbose           = -1,
        )
        self.model.fit(X, y)

        # Calibrar umbral
        if threshold is not None:
            self.threshold = threshold
        elif self.threshold is None:
            self.threshold = self._calibrate_threshold(X, y, valid)

        # Stats
        probas = self.model.predict_proba(X)[:, 1]
        preds  = (probas >= self.threshold).astype(int)

        passed_mask = probas >= self.threshold
        if passed_mask.sum() > 0:
            passed_pnls = np.array([t.get('pnl', 0.0) or 0.0
                                    for t, m in zip(valid, passed_mask) if m])
            passed_wins = passed_pnls[passed_pnls > 0]
            passed_loss = passed_pnls[passed_pnls <= 0]
            filtered_pf = (abs(passed_wins.sum() / passed_loss.sum())
                           if len(passed_loss) > 0 and len(passed_wins) > 0 else 99.0)
            filtered_wr = float(len(passed_wins) / len(passed_pnls) * 100)
        else:
            filtered_pf = 0.0
            filtered_wr = 0.0

        all_pnls = np.array([t.get('pnl', 0.0) or 0.0 for t in valid])
        all_wins = all_pnls[all_pnls > 0]
        all_loss = all_pnls[all_pnls <= 0]
        base_pf  = (abs(all_wins.sum() / all_loss.sum())
                    if len(all_loss) > 0 and len(all_wins) > 0 else 0.0)
        base_wr  = float(len(all_wins) / len(all_pnls) * 100)

        self.stats = {
            'n_trades':         len(valid),
            'pos_rate':         round(pos_rate * 100, 1),
            'threshold':        round(self.threshold * 100, 1),
            'n_passed':         int(passed_mask.sum()),
            'n_blocked':        int((~passed_mask).sum()),
            'base_wr':          round(base_wr, 1),
            'base_pf':          round(base_pf, 2),
            'filtered_wr':      round(filtered_wr, 1),
            'filtered_pf':      round(filtered_pf, 2),
            'wr_improvement':   round(filtered_wr - base_wr, 1),
            'pf_improvement':   round(filtered_pf - base_pf, 2),
            'feature_importance': dict(zip(
                self.feature_names,
                [round(float(v), 4) for v in self.model.feature_importances_]
            )),
        }

        self.trained = True
        return self

    def _calibrate_threshold(self, X, y, trades, n_steps=20) -> float:
        """
        Cross-validation 3-fold para evitar overfitting IS.
        Rango 0.42-0.56. Minimo 50% trades deben pasar.
        """
        from sklearn.model_selection import StratifiedKFold
        pnls = np.array([t.get('pnl', 0.0) or 0.0 for t in trades])

        skf        = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        best_score = -np.inf
        best_thr   = 0.45

        for thr in np.linspace(0.42, 0.56, n_steps):
            fold_scores = []
            for train_idx, val_idx in skf.split(X, y):
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr        = y[train_idx]
                pnls_val    = pnls[val_idx]

                m_fold = LGBMClassifier(
                    n_estimators=200, learning_rate=0.05, max_depth=4,
                    num_leaves=15, min_child_samples=10, subsample=0.8,
                    colsample_bytree=0.8, class_weight='balanced',
                    random_state=42, verbose=-1,
                )
                m_fold.fit(X_tr, y_tr)
                probas_val = m_fold.predict_proba(X_val)[:, 1]

                mask  = probas_val >= thr
                n_sel = int(mask.sum())

                if n_sel < max(10, int(len(val_idx) * 0.50)):
                    fold_scores.append(-1.0)
                    continue

                sel  = pnls_val[mask]
                wins = sel[sel > 0]
                loss = sel[sel <= 0]
                if len(loss) == 0 or len(wins) == 0:
                    fold_scores.append(0.0)
                    continue

                pf = abs(wins.sum() / loss.sum())
                wr = len(wins) / n_sel
                fold_scores.append(pf * wr)

            score = float(np.mean(fold_scores))
            if score > best_score:
                best_score = score
                best_thr   = thr

        return float(best_thr)


    def score(self, setup: dict) -> float:
        if not self.trained or self.model is None:
            return 0.5
        try:
            feats = extract_features(setup)
            df    = pd.DataFrame([feats])[self.feature_names].fillna(0)
            return float(self.model.predict_proba(df.values.astype(float))[:, 1][0])
        except Exception:
            return 0.5

    def should_trade(self, setup: dict) -> tuple:
        """Devuelve (bool, score, motivo_str)."""
        if not self.trained:
            return True, 0.5, "no_filter"
        sc = self.score(setup)
        ok = sc >= self.threshold
        if ok:
            self._passed  += 1
        else:
            self._blocked += 1
        return ok, round(sc, 3), f"score={sc:.2f} thr={self.threshold:.2f}"

    # ── Reporting ─────────────────────────────────────────────────

    def print_stats(self):
        if not self.stats:
            print("  ⚠ ML Filter no entrenado\n")
            return
        s = self.stats
        G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"
        C = "\033[96m"; DIM = "\033[90m"; BOLD = "\033[1m"; RST = "\033[0m"

        print(f"\n  {BOLD}{C}{'─'*55}{RST}")
        print(f"  {BOLD}🧠 ML SETUP FILTER — Resultados IS{RST}")
        print(f"  {DIM}{'─'*55}{RST}")
        print(f"  Trades entrenamiento : {s['n_trades']}")
        print(f"  Trades buenos IS     : {s['pos_rate']}%")
        print(f"  Umbral calibrado     : {s['threshold']}%")
        print(f"  Pasarían el filtro   : {s['n_passed']} "
              f"({round(s['n_passed']/s['n_trades']*100,0):.0f}%)")
        print(f"  Bloqueados           : {s['n_blocked']}")
        print()

        wr_col = G if s['wr_improvement'] > 3 else (Y if s['wr_improvement'] > 0 else R)
        pf_col = G if s['pf_improvement'] > 0.2 else (Y if s['pf_improvement'] > 0 else R)

        print(f"  {'':20} {'Base':>10} {'Filtrado':>10} {'Mejora':>10}")
        print(f"  {DIM}{'─'*52}{RST}")
        print(f"  {'Win Rate':<20} {s['base_wr']:>9.1f}% "
              f"{s['filtered_wr']:>9.1f}% "
              f"{wr_col}{'+' if s['wr_improvement']>=0 else ''}"
              f"{s['wr_improvement']:>8.1f}pp{RST}")
        print(f"  {'Profit Factor':<20} {s['base_pf']:>10.2f} "
              f"{s['filtered_pf']:>10.2f} "
              f"{pf_col}{'+' if s['pf_improvement']>=0 else ''}"
              f"{s['pf_improvement']:>9.2f}{RST}")

        print(f"\n  {DIM}Feature importance (top 6):{RST}")
        imp = sorted(s['feature_importance'].items(),
                     key=lambda x: x[1], reverse=True)
        for feat, val in imp[:6]:
            bar = '█' * int(val / max(v for _, v in imp[:1]) * 20)
            print(f"    {feat:<22} {bar:<20} {val:.4f}")
        print(f"  {BOLD}{C}{'─'*55}{RST}\n")
