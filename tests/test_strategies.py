"""Tests for time-series momentum baseline strategies.

All tests strictly use synthetic, deterministic price series. No real market data
or production datasets are loaded.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from app.strategies import (
    TimeSeriesMomentumResult,
    compute_next_close_strategy_returns,
    moving_average_momentum_signals,
    time_series_momentum_signals,
    validate_prices,
)


def make_synthetic_uptrend(n: int = 60, base: float = 100.0, step: float = 1.0) -> np.ndarray:
    """Generate a strictly monotonic increasing synthetic price series."""
    return base + np.arange(n, dtype=np.float64) * step


def make_synthetic_downtrend(n: int = 60, base: float = 100.0, step: float = 1.0) -> np.ndarray:
    """Generate a strictly monotonic decreasing synthetic price series."""
    return base - np.arange(n, dtype=np.float64) * step


def make_synthetic_oscillation(n: int = 100, base: float = 100.0, amp: float = 10.0, period: float = 20.0) -> np.ndarray:
    """Generate a deterministic sine-wave synthetic price series."""
    t = np.arange(n, dtype=np.float64)
    return base + amp * np.sin(2 * np.pi * t / period)


# ==============================================================================
# 1. Lookback and Signal Alignment Tests
# ==============================================================================


def test_insufficient_lookback_handling():
    """Sessions before the lookback window must yield NaN momentum and 0.0 signal."""
    prices = make_synthetic_uptrend(n=30)
    lookback = 20
    res = time_series_momentum_signals(prices, lookback=lookback)

    # For t in [0, 19], momentum is NaN and signal is 0.0
    for t in range(lookback):
        assert math.isnan(res.momentum_values[t]), f"Expected NaN at index {t}"
        assert res.signals[t] == 0.0, f"Expected 0.0 signal at index {t}"

    # At t = 20, first valid momentum: (prices[20] / prices[0]) - 1.0
    expected_mom = (prices[20] / prices[0]) - 1.0
    assert not math.isnan(res.momentum_values[20])
    assert pytest.approx(res.momentum_values[20]) == expected_mom
    assert res.signals[20] == 1.0


def test_series_shorter_than_lookback():
    """Series with fewer sessions than lookback should not crash and return neutral signals."""
    short_prices = [100.0, 101.0, 102.0, 103.0]
    res = time_series_momentum_signals(short_prices, lookback=20)

    assert len(res.signals) == 4
    assert np.all(res.signals == 0.0)
    assert np.all(np.isnan(res.momentum_values))
    assert np.all(res.executed_positions == 0.0)


def test_synthetic_monotonic_uptrend_and_downtrend():
    """Monotonic trend series produce consistent long or neutral/short signals."""
    up_prices = make_synthetic_uptrend(n=40)
    res_up = time_series_momentum_signals(up_prices, lookback=20)
    assert np.all(res_up.signals[20:] == 1.0)
    assert np.all(res_up.momentum_values[20:] > 0)

    down_prices = make_synthetic_downtrend(n=40, base=200.0)
    # Long-only (cash when negative momentum)
    res_down_cash = time_series_momentum_signals(down_prices, lookback=20, allow_short=False)
    assert np.all(res_down_cash.signals[20:] == 0.0)
    assert np.all(res_down_cash.momentum_values[20:] < 0)

    # Long-short enabled
    res_down_short = time_series_momentum_signals(down_prices, lookback=20, allow_short=True)
    assert np.all(res_down_short.signals[20:] == -1.0)


# ==============================================================================
# 2. Strict Causality: Future Prices Do Not Affect Prior Signals
# ==============================================================================


@pytest.mark.parametrize("cutoff", [15, 20, 25, 35, 45])
def test_future_price_changes_do_not_affect_past_signals(cutoff: int):
    """Mutating future prices (t > cutoff) must have zero effect on signals at or before cutoff."""
    prices_original = make_synthetic_oscillation(n=60, base=100.0, amp=15.0)
    res_original = time_series_momentum_signals(prices_original, lookback=20)

    # Create modified future scenarios: extreme spike, crash, oscillation reversal
    modified_scenarios = [
        prices_original.copy(),
        prices_original.copy(),
        prices_original.copy(),
    ]
    # Scenario A: Massive upward spike in the future
    modified_scenarios[0][cutoff + 1 :] = prices_original[cutoff + 1 :] * 10.0 + 500.0
    # Scenario B: Extreme crash in the future
    modified_scenarios[1][cutoff + 1 :] = 1.0
    # Scenario C: Inverted sign
    modified_scenarios[2][cutoff + 1 :] = 100.0 - (prices_original[cutoff + 1 :] - 100.0)

    for scenario_idx, modified_prices in enumerate(modified_scenarios):
        res_modified = time_series_momentum_signals(modified_prices, lookback=20)

        # Signals up to and including cutoff must be strictly identical
        np.testing.assert_array_equal(
            res_original.signals[: cutoff + 1],
            res_modified.signals[: cutoff + 1],
            err_msg=f"Causality leak detected in scenario {scenario_idx} up to cutoff {cutoff}",
        )

        # Momentum values up to and including cutoff must match
        for idx in range(cutoff + 1):
            orig_m = res_original.momentum_values[idx]
            mod_m = res_modified.momentum_values[idx]
            if math.isnan(orig_m):
                assert math.isnan(mod_m)
            else:
                assert pytest.approx(orig_m) == mod_m


# ==============================================================================
# 3. Next-Close Execution Contract Tests
# ==============================================================================


def test_next_close_delayed_execution_contract():
    """Verify executed_positions[t] == signals[t - 1] (delayed execution at t+1)."""
    # Create a step price series where momentum flips at a known session
    prices = np.full(50, 100.0, dtype=np.float64)
    # From index 25 onwards, price jumps to 120.0
    prices[25:] = 120.0

    res = time_series_momentum_signals(prices, lookback=10)

    # Before index 25, price is flat (100 vs 100) -> momentum == 0, signal == 0
    assert res.signals[24] == 0.0
    # At index 25, price is 120 vs price[15]=100 -> positive momentum, signal becomes 1.0
    assert res.signals[25] == 1.0

    # Under next-close execution:
    # At close of session 25, the order is entered.
    # The active position during session 25 is executed_positions[25], which was signal[24] = 0.0.
    assert res.executed_positions[25] == 0.0, "Position at t must reflect signal[t-1], not signal[t]"

    # At session 26, the active position is now 1.0 (from signal[25])
    assert res.executed_positions[26] == 1.0

    # Check overall mapping for all t >= 1
    np.testing.assert_array_equal(res.executed_positions[1:], res.signals[:-1])
    assert res.executed_positions[0] == 0.0
    np.testing.assert_array_equal(res.entry_indices, res.signal_indices + 1)


def test_strategy_returns_delayed_execution():
    """Strategy returns must use signal[t-1] across interval (t -> t+1)."""
    # Flat 100, then at t=10 jump to 110, at t=11 jump to 120
    prices = np.full(30, 100.0, dtype=np.float64)
    # Signal switches to 1 at index 5
    signals = np.zeros(30, dtype=np.float64)
    signals[5:] = 1.0

    # At t=6, close price is 100
    # At t=7, price rises to 150
    prices[7] = 150.0
    prices[8:] = 150.0

    returns = compute_next_close_strategy_returns(prices, signals)

    # Signal formed at t=5 executes at close t=6.
    # The holding return from t=6 to t=7 is (150 / 100 - 1) = 0.5.
    # Because position was entered at t=6 (signal[5]), return at t=7 should be 0.5.
    assert pytest.approx(returns[7]) == 0.5
    # Return at t=6 is 0 (price was flat 100 to 100)
    assert returns[6] == 0.0
    # Returns at t=0 and t=1 are always 0.0
    assert returns[0] == 0.0
    assert returns[1] == 0.0


# ==============================================================================
# 4. Input Validation & Edge Case Handling
# ==============================================================================


def test_validation_rejects_empty_or_invalid_dimensions():
    with pytest.raises(ValueError, match="長度不能為 0"):
        validate_prices([])

    with pytest.raises(ValueError, match="一維陣列"):
        validate_prices(np.ones((5, 2)))


def test_validation_non_positive_prices():
    """Strict mode raises ValueError on non-positive prices; safe mode marks NaN."""
    prices_with_zero = [100.0, 105.0, 0.0, 110.0]
    with pytest.raises(ValueError, match="非正價格"):
        time_series_momentum_signals(prices_with_zero, lookback=2, raise_on_invalid=True)

    prices_with_neg = [100.0, 105.0, -10.0, 110.0]
    with pytest.raises(ValueError, match="非正價格"):
        time_series_momentum_signals(prices_with_neg, lookback=2, raise_on_invalid=True)

    # Safe mode (raise_on_invalid=False) should not raise
    res_safe = time_series_momentum_signals(prices_with_zero, lookback=2, raise_on_invalid=False)
    assert len(res_safe.signals) == 4
    # The session with 0.0 price and the one depending on it should have NaN momentum and 0 signal
    assert math.isnan(res_safe.momentum_values[2])
    assert res_safe.signals[2] == 0.0


def test_validation_non_finite_prices():
    """Strict mode raises ValueError on NaN/inf; safe mode marks NaN."""
    prices_with_nan = [100.0, float("nan"), 105.0, 110.0]
    with pytest.raises(ValueError, match="無效數值"):
        time_series_momentum_signals(prices_with_nan, lookback=2, raise_on_invalid=True)

    prices_with_inf = [100.0, float("inf"), 105.0, 110.0]
    with pytest.raises(ValueError, match="無效數值"):
        time_series_momentum_signals(prices_with_inf, lookback=2, raise_on_invalid=True)

    # Safe mode
    res = time_series_momentum_signals(prices_with_nan, lookback=2, raise_on_invalid=False)
    assert len(res.signals) == 4
    assert res.signals[1] == 0.0
    assert math.isnan(res.momentum_values[1])


def test_invalid_parameters():
    prices = [100.0, 101.0, 102.0]
    with pytest.raises(ValueError, match="lookback.*必須為正整數"):
        time_series_momentum_signals(prices, lookback=0)

    with pytest.raises(ValueError, match="未知的動能規則"):
        time_series_momentum_signals(prices, lookback=2, rule="invalid_rule")

    with pytest.raises(ValueError, match="日期序列長度"):
        time_series_momentum_signals(prices, lookback=2, dates=["2020-01-01"])


# ==============================================================================
# 5. SMA Rule and Serialization
# ==============================================================================


def test_moving_average_momentum_signals_rule():
    """Verify SMA-based momentum rule matches average calculation."""
    # Prices: 10, 20, 30, 40, 50. Lookback=3.
    prices = [10.0, 20.0, 30.0, 40.0, 20.0]
    # At t=2 (30.0): window=[10, 20, 30], mean=20.0 -> price 30 > 20 -> signal 1.0
    # At t=3 (40.0): window=[20, 30, 40], mean=30.0 -> price 40 > 30 -> signal 1.0
    # At t=4 (20.0): window=[30, 40, 20], mean=30.0 -> price 20 < 30 -> signal 0.0
    res = moving_average_momentum_signals(prices, lookback=3)
    assert res.signals[0] == 0.0
    assert res.signals[1] == 0.0
    assert res.signals[2] == 1.0
    assert res.signals[3] == 1.0
    assert res.signals[4] == 0.0
    assert res.rule == "sma"


def test_result_to_dict_json_compatibility():
    """Verify result serialization contains no raw NaNs and is fully JSON ready."""
    prices = make_synthetic_uptrend(n=30)
    res = time_series_momentum_signals(prices, lookback=20)
    data = res.to_dict()

    assert data["lookback"] == 20
    assert "execution_contract" in data
    assert "summary" in data
    assert data["summary"]["total_sessions"] == 30
    assert data["summary"]["insufficient_lookback_sessions"] == 20
    assert data["summary"]["long_signals"] == 10

    # Ensure all NaN entries were converted to None for valid JSON serialization
    for val in data["momentum_values"][:20]:
        assert val is None, f"Expected None instead of NaN in JSON output, got {val}"
    for val in data["momentum_values"][20:]:
        assert isinstance(val, float)
