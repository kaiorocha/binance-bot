"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


def _int_env(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _float_env(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def _bool_env(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


API_KEY: str = os.getenv("BINANCE_API_KEY", "")
API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")

SYMBOL: str = os.getenv("SYMBOL", "BTCUSDT")
INTERVAL: str = os.getenv("INTERVAL", "1h")

RSI_PERIOD: int = _int_env("RSI_PERIOD", 14)
RSI_OVERSOLD: float = _float_env("RSI_OVERSOLD", 30.0)
RSI_OVERBOUGHT: float = _float_env("RSI_OVERBOUGHT", 70.0)

TRADE_QUANTITY: float = _float_env("TRADE_QUANTITY", 0.001)

USE_TESTNET: bool = _bool_env("USE_TESTNET", False)

# ── Risk management ──────────────────────────────────────────────────────────

# Slow EMA period used as a trend filter: signals that trade against the trend
# are suppressed to HOLD, reducing whipsaw losses.
EMA_SLOW: int = _int_env("EMA_SLOW", 21)

# ATR (Average True Range) period for measuring recent volatility.
ATR_PERIOD: int = _int_env("ATR_PERIOD", 14)

# Stop-loss distance = ATR_MULTIPLIER × ATR.
# Take-profit distance = ATR_MULTIPLIER × ATR × 2 (2 : 1 reward / risk).
ATR_MULTIPLIER: float = _float_env("ATR_MULTIPLIER", 2.0)

# Fallback stop-loss / take-profit as a fraction of entry price, used when
# ATR is unavailable (e.g. insufficient historical data on first startup).
STOP_LOSS_PCT: float = _float_env("STOP_LOSS_PCT", 0.02)   # 2 %
TAKE_PROFIT_PCT: float = _float_env("TAKE_PROFIT_PCT", 0.04)  # 4 %

# Circuit-breaker: pause the bot for the remainder of the UTC day once
# realised losses exceed this amount (in the quote asset, e.g. USDT).
MAX_DAILY_LOSS_USDT: float = _float_env("MAX_DAILY_LOSS_USDT", 50.0)
