# binance-bot

A production-grade RSI + EMA trend-filter trading bot for the [Binance](https://www.binance.com)
exchange, written in Python.  The bot combines two proven technical indicators, enforces
ATR-based stop-loss and take-profit levels on every trade, and includes a daily loss
circuit-breaker to protect your capital during adverse market conditions.

---

## Table of contents

1. [How it works](#how-it-works)
2. [Strategy explained](#strategy-explained)
3. [Risk management](#risk-management)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Running tests](#running-tests)
9. [Project structure](#project-structure)
10. [FAQ](#faq)
11. [Disclaimer](#disclaimer)

---

## How it works

Each time a new candle closes the bot:

1. Fetches the latest OHLCV (Open / High / Low / Close / Volume) candles from Binance.
2. Computes three indicators: **RSI**, **EMA (slow)**, and **ATR**.
3. If a position is already open, checks whether the **stop-loss** or **take-profit** price
   has been reached and closes the position if so.
4. If no position is open and all entry conditions are met, places a **market order** and
   immediately records the ATR-based stop-loss and take-profit levels.
5. Sleeps until the next candle closes, then repeats.

---

## Strategy explained

### Indicators

| Indicator | Purpose |
|-----------|---------|
| **RSI** (Relative Strength Index) | Identifies potential reversal points by measuring momentum – values below the oversold threshold hint at a bottom; values above the overbought threshold hint at a top. |
| **EMA** (Exponential Moving Average) | Defines the prevailing trend. When price is **above** the slow EMA the market is in an uptrend; below the EMA it is in a downtrend. |
| **ATR** (Average True Range) | Quantifies recent volatility so that stop-loss and take-profit distances adapt to the actual market environment rather than using fixed percentages. |

### Entry rules

| Direction | Condition |
|-----------|-----------|
| **BUY (long)** | RSI ≤ `RSI_OVERSOLD` **AND** price is **above** the slow EMA |
| **SELL (short)** | RSI ≥ `RSI_OVERBOUGHT` **AND** price is **below** the slow EMA |
| **HOLD** | All other cases (including signals that contradict the prevailing EMA trend) |

> **Why the EMA filter matters** – RSI alone can remain oversold for weeks in a strong
> downtrend (and overbought for weeks in a strong uptrend).  Requiring the signal to align
> with the EMA trend eliminates a large category of whipsaw losses at the cost of taking
> fewer trades.

---

## Risk management

### ATR-based stop-loss & take-profit

Every order is placed with pre-calculated exit levels:

```
Stop-loss  distance = ATR × ATR_MULTIPLIER           (default: ATR × 2)
Take-profit distance = ATR × ATR_MULTIPLIER × 2      (default: ATR × 4, giving a 2 : 1 reward/risk)
```

A reward-to-risk ratio of at least **2 : 1** means the strategy can be profitable even if
fewer than half of all trades are winners.

When ATR is unavailable (insufficient historical data on first start) the bot falls back to
fixed-percentage levels controlled by `STOP_LOSS_PCT` and `TAKE_PROFIT_PCT`.

### Position tracking

The bot maintains **at most one open position at a time**.  While a position is open all new
entry signals are ignored, preventing pyramiding into a losing trade.

### Daily loss circuit-breaker

If the total **realised loss** for the current UTC day exceeds `MAX_DAILY_LOSS_USDT`, the
bot pauses for one hour and then re-evaluates.  This cap prevents a sequence of back-to-back
losing trades from causing catastrophic account damage on a single bad day.

The daily counter resets automatically at UTC midnight.

---

## Requirements

- Python 3.9 or later
- A [Binance](https://www.binance.com) account with Spot trading API access  
  (or a [Testnet](https://testnet.binance.vision/) account for safe testing)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/kaiorocha/binance-bot.git
cd binance-bot

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

### All configuration variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINANCE_API_KEY` | Your Binance API key | *(required)* |
| `BINANCE_API_SECRET` | Your Binance API secret | *(required)* |
| `SYMBOL` | Trading pair | `BTCUSDT` |
| `INTERVAL` | Candle interval (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`) | `1h` |
| `RSI_PERIOD` | RSI look-back period | `14` |
| `RSI_OVERSOLD` | RSI buy threshold | `30` |
| `RSI_OVERBOUGHT` | RSI sell threshold | `70` |
| `TRADE_QUANTITY` | Order size in base asset units | `0.001` |
| `USE_TESTNET` | Use Binance Testnet (`true`/`false`) | `false` |
| `EMA_SLOW` | Slow EMA period for trend filter | `21` |
| `ATR_PERIOD` | ATR look-back period | `14` |
| `ATR_MULTIPLIER` | Stop-loss distance in ATR multiples | `2.0` |
| `STOP_LOSS_PCT` | Fallback stop-loss as a fraction of entry price | `0.02` (2 %) |
| `TAKE_PROFIT_PCT` | Fallback take-profit as a fraction of entry price | `0.04` (4 %) |
| `MAX_DAILY_LOSS_USDT` | Circuit-breaker daily loss cap (quote asset) | `50.0` |

> **Security:** Never commit your `.env` file. It is already listed in `.gitignore`.

### Recommended settings by time-frame

| Time-frame | `INTERVAL` | `RSI_PERIOD` | `EMA_SLOW` | `ATR_PERIOD` | Notes |
|-----------|------------|-------------|------------|-------------|-------|
| Scalping  | `5m`       | 14           | 21         | 14          | Many signals; tight risk controls required |
| Swing     | `1h`       | 14           | 21         | 14          | Balanced default |
| Position  | `4h`/`1d`  | 14           | 50         | 20          | Fewer, higher-quality signals |

---

## Usage

```bash
python bot.py
```

The bot logs every decision to stdout in a structured format:

```
2024-01-15 10:00:02  INFO      Bot started  |  symbol=BTCUSDT  interval=1h  ...
2024-01-15 11:00:01  INFO      price=42350.0000  RSI=28.34  EMA(21)=41900.0000  ATR=850.0000  trend=bullish
2024-01-15 11:00:01  INFO      Signal: BUY
2024-01-15 11:00:01  INFO      BUY order placed  entry=42350.0000  SL=40650.0000  TP=45750.0000: {...}
2024-01-15 12:00:01  INFO      Closing position – reason=take-profit  price=45780.0000  pnl=3.43 USDT
```

---

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

The test suite covers:

- RSI calculation (edge cases, boundary values, smoothed averages)
- EMA calculation (seeding, convergence, boundary)
- ATR calculation (flat market, random series, insufficient data)
- `get_signal` with and without the EMA trend filter
- `calculate_stop_loss` and `calculate_take_profit` (long & short, reward/risk ratio)
- `get_ohlcv` helper (field extraction, list alignment)
- `_interval_to_seconds` (valid and invalid inputs)

---

## Project structure

```
binance-bot/
├── bot.py           # Entry point: main loop, position tracking, circuit-breaker
├── config.py        # Configuration loaded from .env
├── strategy.py      # Indicators (RSI, EMA, ATR) and signal + risk helpers
├── tests/
│   ├── test_bot.py            # Tests for bot helper functions
│   ├── test_strategy.py       # Tests for RSI and core signal logic
│   └── test_risk_management.py # Tests for EMA, ATR, stop-loss, take-profit
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## FAQ

**Can I run this with real money straight away?**  
No.  Always validate with the Binance Testnet (`USE_TESTNET=true`) until you are confident
in the bot's behaviour with your chosen settings.  Start with a very small `TRADE_QUANTITY`
when you first move to live trading.

**Does the bot support short-selling?**  
The SELL signal places a sell-side market order.  On Spot accounts this will only succeed if
you actually hold the base asset.  For true short-selling you need a Futures/Margin account.

**How do I stop the bot?**  
Press `Ctrl+C` in the terminal.  Any open position will remain open on Binance and must be
managed manually.

**Why is the EMA filter suppressing all my signals?**  
If the market is trending strongly, RSI signals that contradict the trend are intentionally
filtered out.  This is by design.  You can widen `RSI_OVERSOLD` / `RSI_OVERBOUGHT` thresholds
or decrease `EMA_SLOW` to get more signals.

---

## Disclaimer

This software is provided for **educational purposes only**.  Cryptocurrency trading carries
significant financial risk.  Past performance of any strategy is not indicative of future
results.  Never invest more than you can afford to lose, and always test thoroughly on the
Testnet before using real funds.  The authors accept no responsibility for financial losses
incurred through the use of this software.

