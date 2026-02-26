"""Unit tests for the new risk-management indicators and helpers."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from strategy import (
    calculate_ema,
    calculate_atr,
    get_signal,
    calculate_stop_loss,
    calculate_take_profit,
)


# ─────────────────────────────────────── EMA ──────────────────────────────────

class TestCalculateEma:
    def test_returns_none_when_not_enough_data(self):
        assert calculate_ema([100.0] * 9, period=10) is None

    def test_returns_price_when_single_candle_equals_period(self):
        # With a flat series the EMA equals that constant price
        price = 200.0
        ema = calculate_ema([price] * 10, period=10)
        assert ema == pytest.approx(price)

    def test_ema_tracks_rising_prices_above_initial_value(self):
        # Rising series → EMA should be greater than the initial SMA seed
        closes = [float(i) for i in range(1, 21)]  # 1 … 20
        ema = calculate_ema(closes, period=10)
        assert ema is not None
        assert ema > sum(closes[:10]) / 10  # above seed SMA

    def test_ema_within_range_of_input_prices(self):
        closes = [44.34, 44.09, 44.15, 43.61, 44.33,
                  44.83, 45.10, 45.15, 46.20, 45.80,
                  45.50, 46.10, 46.50, 45.90, 46.30]
        ema = calculate_ema(closes, period=10)
        assert ema is not None
        assert min(closes) <= ema <= max(closes)

    def test_exact_period_boundary(self):
        # Exactly `period` data points → no smoothing step, equals SMA
        closes = [10.0, 20.0, 30.0]
        ema = calculate_ema(closes, period=3)
        assert ema == pytest.approx(20.0)


# ─────────────────────────────────────── ATR ──────────────────────────────────

class TestCalculateAtr:
    def _flat_ohlcv(self, price: float, n: int):
        """Return highs, lows, closes for a flat market."""
        highs = [price + 1.0] * n
        lows = [price - 1.0] * n
        closes = [price] * n
        return highs, lows, closes

    def test_returns_none_when_not_enough_data(self):
        highs, lows, closes = self._flat_ohlcv(100.0, 10)
        assert calculate_atr(highs, lows, closes, period=14) is None

    def test_returns_float_with_sufficient_data(self):
        highs, lows, closes = self._flat_ohlcv(100.0, 30)
        atr = calculate_atr(highs, lows, closes, period=14)
        assert atr is not None
        assert atr > 0

    def test_flat_market_atr_equals_candle_range(self):
        # With highs = price + 1, lows = price - 1, each candle's true range = 2
        highs, lows, closes = self._flat_ohlcv(100.0, 30)
        atr = calculate_atr(highs, lows, closes, period=14)
        assert atr == pytest.approx(2.0)

    def test_atr_is_positive(self):
        import random
        random.seed(42)
        n = 50
        closes = [100.0 + random.gauss(0, 5) for _ in range(n)]
        highs = [c + abs(random.gauss(0, 2)) for c in closes]
        lows = [c - abs(random.gauss(0, 2)) for c in closes]
        atr = calculate_atr(highs, lows, closes, period=14)
        assert atr is not None
        assert atr > 0


# ─────────────────────────────────── get_signal (EMA filter) ──────────────────

class TestGetSignalEmaFilter:
    def test_buy_suppressed_in_downtrend(self):
        # RSI oversold but price is below EMA → HOLD (no counter-trend buy)
        assert get_signal(25.0, ema_trend=False) == "HOLD"

    def test_buy_allowed_in_uptrend(self):
        assert get_signal(25.0, ema_trend=True) == "BUY"

    def test_sell_suppressed_in_uptrend(self):
        # RSI overbought but price is above EMA → HOLD (no counter-trend sell)
        assert get_signal(75.0, ema_trend=True) == "HOLD"

    def test_sell_allowed_in_downtrend(self):
        assert get_signal(75.0, ema_trend=False) == "SELL"

    def test_hold_unaffected_by_trend(self):
        assert get_signal(50.0, ema_trend=True) == "HOLD"
        assert get_signal(50.0, ema_trend=False) == "HOLD"

    def test_none_trend_preserves_original_behaviour(self):
        assert get_signal(25.0, ema_trend=None) == "BUY"
        assert get_signal(75.0, ema_trend=None) == "SELL"
        assert get_signal(50.0, ema_trend=None) == "HOLD"


# ─────────────────────────────── stop-loss / take-profit ─────────────────────

class TestCalculateStopLoss:
    def test_buy_stop_loss_below_entry(self):
        sl = calculate_stop_loss(entry_price=100.0, side="BUY", atr=5.0, atr_multiplier=2.0)
        assert sl == pytest.approx(90.0)

    def test_sell_stop_loss_above_entry(self):
        sl = calculate_stop_loss(entry_price=100.0, side="SELL", atr=5.0, atr_multiplier=2.0)
        assert sl == pytest.approx(110.0)

    def test_default_multiplier(self):
        sl = calculate_stop_loss(entry_price=200.0, side="BUY", atr=10.0)
        assert sl == pytest.approx(180.0)


class TestCalculateTakeProfit:
    def test_buy_take_profit_above_entry(self):
        tp = calculate_take_profit(entry_price=100.0, side="BUY", atr=5.0, atr_multiplier=2.0)
        assert tp == pytest.approx(120.0)

    def test_sell_take_profit_below_entry(self):
        tp = calculate_take_profit(entry_price=100.0, side="SELL", atr=5.0, atr_multiplier=2.0)
        assert tp == pytest.approx(80.0)

    def test_reward_risk_ratio(self):
        atr = 4.0
        mult = 1.5
        entry = 50.0
        sl = calculate_stop_loss(entry, "BUY", atr, mult)
        tp = calculate_take_profit(entry, "BUY", atr, mult)
        risk = entry - sl
        reward = tp - entry
        assert reward == pytest.approx(risk * 2.0)
