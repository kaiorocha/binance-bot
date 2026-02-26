"""Binance trading bot entry point."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException

import config
from strategy import (
    calculate_atr,
    calculate_ema,
    calculate_rsi,
    calculate_stop_loss,
    calculate_take_profit,
    get_signal,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Tracks a single open trade."""

    side: str            # "BUY" or "SELL"
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float


def get_closing_prices(client: Client, symbol: str, interval: str, limit: int = 100) -> list:
    """Fetch historical closing prices from Binance."""
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return [float(k[4]) for k in klines]


def get_ohlcv(
    client: Client, symbol: str, interval: str, limit: int = 100
) -> Tuple[List[float], List[float], List[float]]:
    """Fetch OHLCV klines and return (closes, highs, lows).

    All three lists are aligned by index so they can be passed directly to
    indicator functions such as ``calculate_atr``.
    """
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    return closes, highs, lows


def place_order(client: Client, symbol: str, side: str, quantity: float) -> dict:
    """Place a market order and return the order response."""
    return client.order_market(symbol=symbol, side=side, quantity=quantity)


def run(client: Client) -> None:
    """Main bot loop: fetch data, compute indicators, manage positions, act on signals."""
    logger.info(
        "Bot started  |  symbol=%s  interval=%s  rsi_period=%d  ema_slow=%d  "
        "atr_period=%d  atr_mult=%.1f  sl_pct=%.1f%%  tp_pct=%.1f%%  "
        "max_daily_loss=%.2f USDT",
        config.SYMBOL,
        config.INTERVAL,
        config.RSI_PERIOD,
        config.EMA_SLOW,
        config.ATR_PERIOD,
        config.ATR_MULTIPLIER,
        config.STOP_LOSS_PCT * 100,
        config.TAKE_PROFIT_PCT * 100,
        config.MAX_DAILY_LOSS_USDT,
    )

    position: Optional[Position] = None
    daily_loss: float = 0.0
    daily_pnl_date: str = ""

    while True:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != daily_pnl_date:
            if daily_pnl_date:
                logger.info("New UTC day – resetting daily loss counter (was %.2f USDT).", daily_loss)
            daily_loss = 0.0
            daily_pnl_date = today

        # ── Circuit-breaker ──────────────────────────────────────────────────
        if daily_loss >= config.MAX_DAILY_LOSS_USDT:
            logger.warning(
                "Daily loss limit of %.2f USDT reached (actual %.2f USDT). "
                "Bot paused for 1 hour.",
                config.MAX_DAILY_LOSS_USDT,
                daily_loss,
            )
            time.sleep(3600)
            continue

        try:
            closes, highs, lows = get_ohlcv(client, config.SYMBOL, config.INTERVAL)
            current_price = closes[-1]

            # ── Stop-loss / Take-profit monitoring ───────────────────────────
            if position is not None:
                sl_hit = (
                    position.side == "BUY" and current_price <= position.stop_loss
                ) or (
                    position.side == "SELL" and current_price >= position.stop_loss
                )
                tp_hit = (
                    position.side == "BUY" and current_price >= position.take_profit
                ) or (
                    position.side == "SELL" and current_price <= position.take_profit
                )

                if sl_hit or tp_hit:
                    close_side = Client.SIDE_SELL if position.side == "BUY" else Client.SIDE_BUY
                    reason = "stop-loss" if sl_hit else "take-profit"
                    pnl = (
                        (current_price - position.entry_price) * position.quantity
                        if position.side == "BUY"
                        else (position.entry_price - current_price) * position.quantity
                    )
                    logger.info(
                        "Closing position – reason=%s  price=%.4f  pnl=%.4f USDT",
                        reason,
                        current_price,
                        pnl,
                    )
                    order = place_order(client, config.SYMBOL, close_side, position.quantity)
                    logger.info("Close order placed: %s", order)
                    if pnl < 0:
                        daily_loss += abs(pnl)
                    position = None

            # ── Signal evaluation (only when flat) ───────────────────────────
            if position is None:
                rsi = calculate_rsi(closes, config.RSI_PERIOD)
                ema = calculate_ema(closes, config.EMA_SLOW)
                atr = calculate_atr(highs, lows, closes, config.ATR_PERIOD)

                if rsi is None:
                    logger.warning("Not enough data to compute RSI – waiting for next candle.")
                else:
                    ema_trend: Optional[bool] = None
                    if ema is not None:
                        ema_trend = current_price > ema

                    logger.info(
                        "price=%.4f  RSI=%.2f  EMA(%d)=%s  ATR=%s  trend=%s",
                        current_price,
                        rsi,
                        config.EMA_SLOW,
                        f"{ema:.4f}" if ema is not None else "n/a",
                        f"{atr:.4f}" if atr is not None else "n/a",
                        "bullish" if ema_trend is True else ("bearish" if ema_trend is False else "unknown"),
                    )

                    signal = get_signal(rsi, config.RSI_OVERSOLD, config.RSI_OVERBOUGHT, ema_trend)
                    logger.info("Signal: %s", signal)

                    if signal in ("BUY", "SELL"):
                        if atr is not None:
                            sl_price = calculate_stop_loss(
                                current_price, signal, atr, config.ATR_MULTIPLIER
                            )
                            tp_price = calculate_take_profit(
                                current_price, signal, atr, config.ATR_MULTIPLIER
                            )
                        else:
                            # Fallback: fixed-percentage levels
                            if signal == "BUY":
                                sl_price = current_price * (1.0 - config.STOP_LOSS_PCT)
                                tp_price = current_price * (1.0 + config.TAKE_PROFIT_PCT)
                            else:
                                sl_price = current_price * (1.0 + config.STOP_LOSS_PCT)
                                tp_price = current_price * (1.0 - config.TAKE_PROFIT_PCT)

                        binance_side = Client.SIDE_BUY if signal == "BUY" else Client.SIDE_SELL
                        order = place_order(client, config.SYMBOL, binance_side, config.TRADE_QUANTITY)
                        position = Position(
                            side=signal,
                            entry_price=current_price,
                            quantity=config.TRADE_QUANTITY,
                            stop_loss=sl_price,
                            take_profit=tp_price,
                        )
                        logger.info(
                            "%s order placed  entry=%.4f  SL=%.4f  TP=%.4f: %s",
                            signal,
                            current_price,
                            sl_price,
                            tp_price,
                            order,
                        )

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
