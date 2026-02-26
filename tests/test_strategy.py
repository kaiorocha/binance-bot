"""Unit tests for the RSI strategy."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from strategy import calculate_rsi, get_signal


class TestCalculateRsi:
    def test_returns_none_when_not_enough_data(self):
        closes = [100.0] * 10
        assert calculate_rsi(closes, period=14) is None

    def test_returns_100_when_no_losses(self):
        # Strictly increasing prices → no losses → RSI = 100
        closes = [float(i) for i in range(16)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi == 100.0

    def test_returns_0_when_no_gains(self):
        # Strictly decreasing prices → no gains → RS = 0 → RSI = 0
        closes = [float(100 - i) for i in range(16)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi == 0.0

    def test_rsi_within_valid_range(self):
        closes = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.15,
            43.61, 44.33, 44.83, 45.10, 45.15, 43.61, 44.33,
        ]
        rsi = calculate_rsi(closes, period=14)
        assert rsi is not None
        assert 0.0 <= rsi <= 100.0

    def test_more_data_points_update_smoothed_average(self):
        closes = [float(i % 10) for i in range(30)]
        rsi = calculate_rsi(closes, period=14)
        assert rsi is not None
        assert 0.0 <= rsi <= 100.0


class TestGetSignal:
    def test_buy_signal_when_oversold(self):
        assert get_signal(25.0) == "BUY"

    def test_sell_signal_when_overbought(self):
        assert get_signal(75.0) == "SELL"

    def test_hold_signal_when_neutral(self):
        assert get_signal(50.0) == "HOLD"

    def test_boundary_oversold(self):
        assert get_signal(30.0) == "BUY"

    def test_boundary_overbought(self):
        assert get_signal(70.0) == "SELL"

    def test_custom_thresholds(self):
        assert get_signal(20.0, oversold=25.0, overbought=75.0) == "BUY"
        assert get_signal(80.0, oversold=25.0, overbought=75.0) == "SELL"
        assert get_signal(50.0, oversold=25.0, overbought=75.0) == "HOLD"
