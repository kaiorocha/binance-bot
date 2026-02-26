"""Binance trading bot entry point."""

import logging
import time

from binance.client import Client
from binance.exceptions import BinanceAPIException

import config
from strategy import calculate_rsi, get_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


def get_closing_prices(client: Client, symbol: str, interval: str, limit: int = 100) -> list:
    """Fetch historical closing prices from Binance."""
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return [float(k[4]) for k in klines]


def place_order(client: Client, symbol: str, side: str, quantity: float) -> dict:
    """Place a market order and return the order response."""
    return client.order_market(symbol=symbol, side=side, quantity=quantity)


def run(client: Client) -> None:
    """Main bot loop: fetch data, compute RSI, and act on signals."""
    logger.info(
        "Bot started  |  symbol=%s  interval=%s  rsi_period=%d",
        config.SYMBOL,
        config.INTERVAL,
        config.RSI_PERIOD,
    )

    while True:
        try:
            closes = get_closing_prices(client, config.SYMBOL, config.INTERVAL)
            rsi = calculate_rsi(closes, config.RSI_PERIOD)

            if rsi is None:
                logger.warning("Not enough data to compute RSI – waiting for next candle.")
            else:
                logger.info("RSI=%.2f", rsi)
                signal = get_signal(rsi, config.RSI_OVERSOLD, config.RSI_OVERBOUGHT)
                logger.info("Signal: %s", signal)

                if signal == "BUY":
                    order = place_order(client, config.SYMBOL, Client.SIDE_BUY, config.TRADE_QUANTITY)
                    logger.info("BUY order placed: %s", order)
                elif signal == "SELL":
                    order = place_order(client, config.SYMBOL, Client.SIDE_SELL, config.TRADE_QUANTITY)
                    logger.info("SELL order placed: %s", order)

        except BinanceAPIException as exc:
            logger.error("Binance API error: %s", exc)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected error: %s", exc)

        # Wait for the next candle
        interval_seconds = _interval_to_seconds(config.INTERVAL)
        logger.info("Sleeping %d seconds until next candle…", interval_seconds)
        time.sleep(interval_seconds)


def _interval_to_seconds(interval: str) -> int:
    """Convert a Binance candle interval string to seconds.

    Raises ValueError for unrecognised or malformed interval strings.
    """
    units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    if not interval or len(interval) < 2:
        raise ValueError(f"Invalid interval: {interval!r}")
    unit = interval[-1]
    if unit not in units:
        raise ValueError(f"Unknown interval unit {unit!r} in {interval!r}")
    try:
        value = int(interval[:-1])
    except ValueError:
        raise ValueError(f"Invalid interval value in {interval!r}")
    if value <= 0:
        raise ValueError(f"Interval value must be positive, got {interval!r}")
    return value * units[unit]


def main() -> None:
    """Create the Binance client and start the bot."""
    if not config.API_KEY or not config.API_SECRET:
        raise ValueError(
            "BINANCE_API_KEY and BINANCE_API_SECRET must be set in the .env file."
        )

    client = Client(
        config.API_KEY,
        config.API_SECRET,
        testnet=config.USE_TESTNET,
    )
    run(client)


if __name__ == "__main__":
    main()
