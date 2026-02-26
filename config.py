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
