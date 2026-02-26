# binance-bot

A simple RSI-based trading bot for the [Binance](https://www.binance.com) exchange, written in Python.

## How it works

The bot fetches candlestick (OHLCV) data for a configured trading pair, computes the
[Relative Strength Index (RSI)](https://en.wikipedia.org/wiki/Relative_strength_index), and
places market orders based on the following rules:

| RSI value | Action |
|-----------|--------|
| ≤ oversold threshold (default 30) | **BUY** |
| ≥ overbought threshold (default 70) | **SELL** |
| Between thresholds | **HOLD** (no order) |

After each evaluation the bot sleeps until the next candle closes.

## Requirements

- Python 3.9+
- A [Binance](https://www.binance.com) account with API access
  (or a [Testnet](https://testnet.binance.vision/) account for safe testing)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

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

> **Warning:** Never commit your `.env` file. It is listed in `.gitignore`.

## Usage

```bash
python bot.py
```

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project structure

```
binance-bot/
├── bot.py           # Main entry point and bot loop
├── config.py        # Configuration (loaded from .env)
├── strategy.py      # RSI calculation and signal logic
├── tests/
│   ├── test_bot.py       # Tests for bot helper functions
│   └── test_strategy.py  # Tests for strategy logic
├── requirements.txt
├── .env.example
└── .gitignore
```

## Disclaimer

This bot is provided for educational purposes only. Cryptocurrency trading carries significant
financial risk. Always test with the Testnet before using real funds, and never invest more than
you can afford to lose.
