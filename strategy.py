"""RSI-based trading strategy."""

from typing import List, Optional


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


def get_signal(rsi: float, oversold: float = 30.0, overbought: float = 70.0) -> str:
    """Return a trading signal based on RSI value.

    Returns:
        "BUY"  – RSI is below the oversold threshold.
        "SELL" – RSI is above the overbought threshold.
        "HOLD" – RSI is between the thresholds.
    """
    if rsi <= oversold:
        return "BUY"
    if rsi >= overbought:
        return "SELL"
    return "HOLD"
