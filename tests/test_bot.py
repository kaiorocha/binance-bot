"""Unit tests for bot helper functions."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from bot import get_closing_prices, get_ohlcv, _interval_to_seconds


class TestGetClosingPrices:
    def test_extracts_close_prices(self):
        # Kline format: [open_time, open, high, low, close, ...]
        mock_klines = [
            [0, "1.0", "2.0", "0.5", "1.5", "100"],
            [1, "1.5", "2.5", "1.0", "2.0", "200"],
        ]
        client = MagicMock()
        client.get_klines.return_value = mock_klines

        closes = get_closing_prices(client, "BTCUSDT", "1h")

        assert closes == [1.5, 2.0]
        client.get_klines.assert_called_once_with(symbol="BTCUSDT", interval="1h", limit=100)


class TestGetOhlcv:
    def test_returns_closes_highs_lows(self):
        # Kline format: [open_time, open, high, low, close, ...]
        mock_klines = [
            [0, "1.0", "2.0", "0.5", "1.5", "100"],
            [1, "1.5", "2.5", "1.0", "2.0", "200"],
        ]
        client = MagicMock()
        client.get_klines.return_value = mock_klines

        closes, highs, lows = get_ohlcv(client, "BTCUSDT", "1h")

        assert closes == [1.5, 2.0]
        assert highs == [2.0, 2.5]
        assert lows == [0.5, 1.0]
        client.get_klines.assert_called_once_with(symbol="BTCUSDT", interval="1h", limit=100)

    def test_lists_are_same_length(self):
        mock_klines = [
            [i, str(i), str(i + 0.5), str(i - 0.5), str(i + 0.1), "100"]
            for i in range(10)
        ]
        client = MagicMock()
        client.get_klines.return_value = mock_klines

        closes, highs, lows = get_ohlcv(client, "BTCUSDT", "1h")

        assert len(closes) == len(highs) == len(lows) == 10


class TestIntervalToSeconds:
    @pytest.mark.parametrize("interval,expected", [
        ("1m", 60),
        ("5m", 300),
        ("15m", 900),
        ("1h", 3600),
        ("4h", 14400),
        ("1d", 86400),
        ("1w", 604800),
    ])
    def test_converts_correctly(self, interval, expected):
        assert _interval_to_seconds(interval) == expected

    @pytest.mark.parametrize("bad_interval", ["", "x", "1x", "0m", "-1h", "abc"])
    def test_raises_on_invalid_interval(self, bad_interval):
        with pytest.raises(ValueError):
            _interval_to_seconds(bad_interval)

