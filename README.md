# ◈ Momentum Breakout Engine

> Swing trading sistemático de alta convicción — una idea, bien ejecutada.

**[→ Ver Dashboard en vivo](https://TU_USUARIO.github.io/momentum-engine/dashboard.html)**

---

## La idea

Un activo en tendencia que comprime su volatilidad y luego rompe al alza con volumen tiene compradores reales detrás. Eso es todo.

Sin puntos arbitrarios. Sin 19 parámetros optimizados. Sin filtro SPY para activos descorrelacionados.

## Tres condiciones binarias — todas obligatorias

| Condición | Descripción | Por qué funciona |
|-----------|-------------|-----------------|
| **Tendencia** | Subida > 1.5× ATR normalizado en 60 días + precio sobre EMA50 | Solo operar a favor de la tendencia establecida |
| **Compresión** | Volatilidad realizada en percentil ≤ 25 de su propia historia | El precio acumula energía antes de moverse |
| **Breakout** | Rompe el máximo de la compresión con volumen en percentil ≥ 70 | Confirma que hay compradores reales, no ruido |

**Filtro de régimen:** por activo, no por SPY. Si la volatilidad realizada está en percentil ≥ 80 de su historia → pánico → no operar. Cada activo se compara contra sí mismo, haciendo el sistema universal para activos descorrelacionados.

## Gestión del trade

- **SL:** mínimo de la compresión − 0.3% (soporte estructural real)
- **TP:** entrada + 2.5 × riesgo (R/R mínimo 2.5:1)
- **Trailing:** EMA8 una vez que el trade supera 1R de beneficio
- **Tiempo máximo:** 20 días hábiles

## Universo (87 activos)

| Categoría | Activos | Por qué |
|-----------|---------|---------|
| **ETFs europeos** (20) | Metales, semis, defensa, energía, EM, apalancados | Acceso desde broker europeo |
| **ETFs sectoriales USA** (18) | XLK, XLE, SOXX, ITA, IBB, COPX, URA... | Máxima liquidez, historia 10+ años, tendencias sectoriales largas |
| **Mega-cap tecnología** | NVDA, META, MSFT, AMZN, AVGO, AMD | Tendencias de años, compresiones perfectas, volumen masivo |
| **Ciberseguridad** | CRWD, PANW, FTNT, ZS | Sector con momentum estructural más fuerte de la década |
| **Defensa directa** | LMT, RTX, NOC, HII | Más historia que los ETFs de defensa |
| **Materias primas** | CCJ, WPM, NEM, AEM, PAAS, FSLR | Ciclos largos, perfectos para breakout de compresión |
| **Momentum consumo** | LULU, DECK, BKNG, RCL | Tendencias de 2-4 años muy claras |
| **Industriales** | TDG, SAIA, ISRG, AXON | Momentum silencioso, pocas noticias que distorsionen |

Activos con historial corto (<5 años) permanecen en el universo y se activarán automáticamente cuando acumulen historia suficiente para el percentil.

## Instalación y uso

```bash
pip install -r requirements.txt
python momentum_engine.py
```

La primera ejecución tarda ~15-20 minutos (descarga histórico máximo de cada activo y calcula percentiles barra a barra). Las siguientes son más rápidas con caché de yfinance.

Al terminar genera `dashboard.html` — ábrelo en el navegador o súbelo a GitHub Pages.

## Dashboard

El dashboard HTML es standalone — sin servidor, sin dependencias externas. Incluye:

- Estado del sistema (métricas OOS en tiempo real)
- Señales FIRE del día con entrada, SL, TP y R/R
- Señales WATCH — setup listo, falta breakout
- Tabla radar del universo completo con estado de cada condición
- Histórico completo de trades OOS verificables
- Curva de equity Out-of-Sample
- Gráfico de precio + EMAs + percentil de volatilidad por activo

## Backtest

El backtest es walk-forward honesto con split 65% IS / 35% OOS. Los parámetros no se optimizan — son fijos con lógica económica real. Lo que ves en OOS es lo que el sistema hubiera hecho en real.

Costes incluidos: 0.10% comisión + 0.05% slippage por operación.

## Parámetros

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| `COMPRESSION_BARS` | 10 | Ventana de la pausa pre-breakout |
| `TREND_BARS` | 60 | ~3 meses para confirmar tendencia |
| `TREND_ATR_MULTIPLE` | 1.5× | Relativo a la volatilidad del activo |
| `COMPRESSION_VOL_PERCENTILE` | 25 | Cuartil inferior de volatilidad histórica |
| `PANIC_VOL_PERCENTILE` | 80 | Percentil 80 = régimen de riesgo |
| `BREAKOUT_VOL_PERCENTILE` | 70 | Volumen superior al 70% histórico |
| `TP_R_MULTIPLE` | 2.5× | R/R mínimo de 2.5:1 |
| `MAX_HOLD_DAYS` | 20 | Salida por tiempo si no resuelve |

---

*Este repositorio es educativo. No es asesoramiento financiero.*
