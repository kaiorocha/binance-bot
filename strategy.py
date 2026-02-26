"""RSI + EMA + ATR trading strategy with risk-management helpers."""

from typing import List, Optional, Tuple


def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate the Relative Strength Index (RSI) for a list of closing prices.

    Returns None if there are not enough data points.
    """
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Subsequent values use smoothed averages
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = change if change > 0 else 0.0
        loss = abs(change) if change < 0 else 0.0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_ema(closes: List[float], period: int) -> Optional[float]:
    """Calculate the Exponential Moving Average (EMA) for a list of closing prices.

    Uses a simple moving average as the seed value for the first *period* candles,
    then applies the standard EMA smoothing formula.

    Returns None if there are not enough data points.
    """
    if len(closes) < period:
        return None

    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period  # seed with SMA
    for price in closes[period:]:
        ema = price * k + ema * (1.0 - k)
    return ema


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Optional[float]:
    """Calculate the Average True Range (ATR).

    ATR measures market volatility and is used to set dynamic stop-loss levels.
    Returns None if there are not enough data points.
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None

    true_ranges: List[float] = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # Wilder's smoothed average
    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def get_signal(
    rsi: float,
    oversold: float = 30.0,
    overbought: float = 70.0,
    ema_trend: Optional[bool] = None,
) -> str:
    """Return a trading signal based on RSI value with an optional EMA trend filter.

    Args:
        rsi:       Current RSI value.
        oversold:  RSI threshold below which the market is considered oversold.
        overbought: RSI threshold above which the market is considered overbought.
        ema_trend: When provided, acts as a trend filter:
                   - True  → price is above the slow EMA (bullish bias); SELL signals
                             that contradict the trend are suppressed to HOLD.
                   - False → price is below the slow EMA (bearish bias); BUY signals
                             that contradict the trend are suppressed to HOLD.
                   - None  → no filter applied (backward-compatible default).

    Returns:
        "BUY"  – oversold AND trend not bearish.
        "SELL" – overbought AND trend not bullish.
        "HOLD" – all other cases.
    """
    if rsi <= oversold:
        # Suppress buy signal when price is in a confirmed downtrend
        if ema_trend is False:
            return "HOLD"
        return "BUY"
    if rsi >= overbought:
        # Suppress sell signal when price is in a confirmed uptrend
        if ema_trend is True:
            return "HOLD"
        return "SELL"
    return "HOLD"


def calculate_stop_loss(
    entry_price: float,
    side: str,
    atr: float,
    atr_multiplier: float = 2.0,
) -> float:
    """Calculate an ATR-based stop-loss price.

    Args:
        entry_price:    The price at which the position was opened.
        side:           "BUY" for long positions, "SELL" for short positions.
        atr:            Current ATR value.
        atr_multiplier: Distance from entry expressed as a multiple of ATR.

    Returns:
        The stop-loss price level.
    """
    distance = atr * atr_multiplier
    if side == "BUY":
        return entry_price - distance
    return entry_price + distance


def calculate_take_profit(
    entry_price: float,
    side: str,
    atr: float,
    atr_multiplier: float = 2.0,
    reward_ratio: float = 2.0,
) -> float:
    """Calculate an ATR-based take-profit price targeting a 2:1 reward/risk ratio.

    Args:
        entry_price:    The price at which the position was opened.
        side:           "BUY" for long positions, "SELL" for short positions.
        atr:            Current ATR value.
        atr_multiplier: Stop-loss distance expressed as a multiple of ATR.
        reward_ratio:   Take-profit distance as a multiple of the stop-loss distance.

    Returns:
        The take-profit price level.
    """
    distance = atr * atr_multiplier * reward_ratio
    if side == "BUY":
        return entry_price + distance
    return entry_price - distance
