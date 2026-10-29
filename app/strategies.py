"""Time-series momentum baseline strategies for pedagogical and research comparison.

This module provides pure, causal, and testable time-series momentum rules.
Signals at session t are computed strictly using close prices up to and including t.
Under the next-close execution contract, signal[t] is executed at close[t+1],
meaning the position entering the holding period between close[t+1] and close[t+2]
is determined by signal[t].

DISCLAIMER:
This strategy is an illustrative quantitative baseline rule designed for
academic, comparative, and educational experimentation inside taiex-neural-lab.
It is NOT investment advice and makes NO claim of alpha, excess return, or profitability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class TimeSeriesMomentumResult:
    """Structured result of time-series momentum signal generation.

    Attributes:
        signals: 1D array of shape (N,) containing decisions formed at session t close.
            Values are 1.0 (long), 0.0 (neutral/cash), and optionally -1.0 (short).
        executed_positions: 1D array of shape (N,) containing active positions after
            session t close execution. Follows the next-close execution contract:
            executed_positions[0] = 0.0, and executed_positions[t] = signals[t - 1] for t >= 1.
        momentum_values: 1D array of shape (N,) containing the continuous momentum metric
            (e.g., P[t] / P[t - lookback] - 1.0). For t < lookback or invalid sessions,
            the value is np.nan.
        signal_indices: 1D array of shape (N,) containing decision session indices [0, 1, ..., N-1].
        entry_indices: 1D array of shape (N,) containing execution session indices [1, 2, ..., N].
        lookback: The lookback window length used (default 20).
        dates: Optional list of date strings corresponding to each session.
        allow_short: Whether short positions (-1.0) were permitted.
        rule: The momentum calculation rule used ('return' or 'sma').
        metadata: Diagnostic and contract metadata formatted for API/UI integration.
    """

    signals: np.ndarray
    executed_positions: np.ndarray
    momentum_values: np.ndarray
    signal_indices: np.ndarray
    entry_indices: np.ndarray
    lookback: int
    dates: list[str] | None
    allow_short: bool
    rule: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the result into a JSON-serializable dictionary for API/UI consumption."""
        nan_to_none = lambda val: None if (isinstance(val, float) and (math.isnan(val) or math.isinf(val))) else val
        return {
            "lookback": self.lookback,
            "rule": self.rule,
            "allow_short": self.allow_short,
            "execution_contract": {
                "decision_session": "t (using closes up to t)",
                "execution_session": "t + 1 (executed at close of t + 1)",
                "holding_interval": "from close[t + 1] to close[t + 2]",
                "position_mapping": "executed_positions[t] = signals[t - 1] (for t >= 1, 0 otherwise)",
            },
            "signals": [nan_to_none(float(x)) for x in self.signals],
            "executed_positions": [nan_to_none(float(x)) for x in self.executed_positions],
            "momentum_values": [nan_to_none(float(x)) for x in self.momentum_values],
            "signal_indices": [int(x) for x in self.signal_indices],
            "entry_indices": [int(x) for x in self.entry_indices],
            "dates": self.dates,
            "summary": {
                "total_sessions": len(self.signals),
                "insufficient_lookback_sessions": int(np.sum(np.isnan(self.momentum_values))),
                "long_signals": int(np.sum(self.signals > 0)),
                "cash_signals": int(np.sum(self.signals == 0)),
                "short_signals": int(np.sum(self.signals < 0)),
            },
            "metadata": self.metadata,
        }


def validate_prices(
    prices: Sequence[float] | np.ndarray,
    raise_on_invalid: bool = True,
) -> np.ndarray:
    """Validate and sanitize an input price sequence.

    Args:
        prices: Sequence or 1D numpy array of close prices.
        raise_on_invalid: If True, raises ValueError when missing (NaN), non-finite,
            or non-positive prices (<= 0) are encountered. If False, invalid entries
            are marked as NaN without raising.

    Returns:
        1D float64 numpy array of validated prices.

    Raises:
        ValueError: If prices is empty, contains non-numeric values, or fails positivity/finite checks
            when raise_on_invalid is True.
    """
    if prices is None:
        raise ValueError("價格序列不能為 None。")

    try:
        arr = np.asarray(prices, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"價格序列必須為數值型態：{exc}") from exc

    if arr.ndim != 1:
        raise ValueError(f"價格序列必須為一維陣列，目前維度為 {arr.ndim}。")

    if len(arr) == 0:
        raise ValueError("價格序列長度不能為 0。")

    invalid_finite = ~np.isfinite(arr)
    if np.any(invalid_finite):
        if raise_on_invalid:
            bad_idx = int(np.where(invalid_finite)[0][0])
            raise ValueError(f"收盤價在索引 {bad_idx} 包含無效數值 (NaN 或非有限值)：{arr[bad_idx]}")
        arr = arr.copy()
        arr[invalid_finite] = np.nan

    non_positive = arr <= 0
    if np.any(non_positive & ~np.isnan(arr)):
        if raise_on_invalid:
            bad_idx = int(np.where(non_positive & ~np.isnan(arr))[0][0])
            raise ValueError(f"收盤價必須為正數 (P > 0)，在索引 {bad_idx} 發現非正價格：{arr[bad_idx]}")
        arr = arr.copy()
        arr[non_positive] = np.nan

    return arr


def time_series_momentum_signals(
    prices: Sequence[float] | np.ndarray,
    lookback: int = 20,
    dates: Sequence[str] | None = None,
    allow_short: bool = False,
    rule: str = "return",
    raise_on_invalid: bool = True,
) -> TimeSeriesMomentumResult:
    """Compute pure 20-session time-series momentum signals with next-close execution contract.

    This function is strictly causal: signal[t] depends ONLY on prices[0:t+1]. Future prices
    (prices[t+1:]) have zero impact on signal[t].

    Timing and Execution Contract:
    - Signal formation at session t: close[t] is observed. Momentum is computed over
      the past `lookback` sessions.
    - Execution at session t+1: The trade enters or rebalances at close[t+1].
    - Holding interval: The position determined by signal[t] is held between close[t+1]
      and close[t+2].
    - `executed_positions`: Represented as executed_positions[t] = signals[t-1] for t >= 1,
      and 0.0 for t = 0.

    Handling of Edge Cases:
    - Insufficient lookback (t < lookback): momentum_value is np.nan, signal is 0.0 (neutral/cash).
    - Missing / NaN values or non-positive prices (<= 0):
      If raise_on_invalid=True, raises ValueError with descriptive diagnostics.
      If raise_on_invalid=False, sets momentum_value to np.nan and signal to 0.0 for any window
      containing invalid values.

    Args:
        prices: Sequence of close prices.
        lookback: Number of sessions for the momentum window (default 20). Must be >= 1.
        dates: Optional sequence of session dates (strings), matching the length of prices.
        allow_short: If True, produces -1.0 for negative momentum; if False, defaults to 0.0 (cash).
        rule: Momentum metric:
            - 'return': Price ratio momentum, P[t] / P[t - lookback] - 1.0.
            - 'sma': Distance to simple moving average, P[t] / SMA(lookback) - 1.0.
        raise_on_invalid: Whether to raise ValueError on invalid prices.

    Returns:
        TimeSeriesMomentumResult instance containing signals, executed positions,
        momentum values, and index contracts.
    """
    if lookback < 1:
        raise ValueError(f"回看觀察窗 (lookback) 必須為正整數 (>= 1)，傳入值：{lookback}")

    if rule not in ("return", "sma"):
        raise ValueError(f"未知的動能規則：'{rule}'，僅支援 'return' 或 'sma'。")

    clean_prices = validate_prices(prices, raise_on_invalid=raise_on_invalid)
    n = len(clean_prices)

    if dates is not None:
        dates_list = list(dates)
        if len(dates_list) != n:
            raise ValueError(f"日期序列長度 ({len(dates_list)}) 與價格序列長度 ({n}) 不符。")
    else:
        dates_list = None

    signals = np.zeros(n, dtype=np.float64)
    momentum_values = np.full(n, np.nan, dtype=np.float64)
    signal_indices = np.arange(n, dtype=np.int64)
    entry_indices = np.arange(1, n + 1, dtype=np.int64)

    # Pure causal signal computation loop
    for t in range(n):
        if rule == "return":
            if t < lookback:
                continue
            past_price = clean_prices[t - lookback]
            curr_price = clean_prices[t]
            if not np.isfinite(past_price) or not np.isfinite(curr_price) or past_price <= 0 or curr_price <= 0:
                continue
            mom = (curr_price / past_price) - 1.0
            momentum_values[t] = mom
            if mom > 0.0:
                signals[t] = 1.0
            elif mom < 0.0:
                signals[t] = -1.0 if allow_short else 0.0
            else:
                signals[t] = 0.0

        elif rule == "sma":
            if t < lookback - 1:
                continue
            window = clean_prices[t - lookback + 1 : t + 1]
            if len(window) != lookback or not np.all(np.isfinite(window)) or np.any(window <= 0):
                continue
            sma = float(np.mean(window))
            curr_price = clean_prices[t]
            mom = (curr_price / sma) - 1.0
            momentum_values[t] = mom
            if curr_price > sma:
                signals[t] = 1.0
            elif curr_price < sma:
                signals[t] = -1.0 if allow_short else 0.0
            else:
                signals[t] = 0.0

    # Next-close execution contract:
    # Order generated at t executes at close[t+1].
    # Therefore, the executed position held at close[t] is signals[t-1] for t >= 1, and 0 for t = 0.
    executed_positions = np.zeros(n, dtype=np.float64)
    if n > 1:
        executed_positions[1:] = signals[:-1]

    metadata = {
        "strategy": "time_series_momentum",
        "lookback": lookback,
        "rule": rule,
        "allow_short": allow_short,
        "disclaimer": (
            "此規則僅為量化研究與基準比較用之純函式，無任何獲利保證、投資建議或 Alpha 宣稱。"
        ),
    }

    return TimeSeriesMomentumResult(
        signals=signals,
        executed_positions=executed_positions,
        momentum_values=momentum_values,
        signal_indices=signal_indices,
        entry_indices=entry_indices,
        lookback=lookback,
        dates=dates_list,
        allow_short=allow_short,
        rule=rule,
        metadata=metadata,
    )


def moving_average_momentum_signals(
    prices: Sequence[float] | np.ndarray,
    lookback: int = 20,
    dates: Sequence[str] | None = None,
    allow_short: bool = False,
    raise_on_invalid: bool = True,
) -> TimeSeriesMomentumResult:
    """Convenience wrapper for 20-session Simple Moving Average (SMA) momentum."""
    return time_series_momentum_signals(
        prices=prices,
        lookback=lookback,
        dates=dates,
        allow_short=allow_short,
        rule="sma",
        raise_on_invalid=raise_on_invalid,
    )


def compute_next_close_strategy_returns(
    prices: Sequence[float] | np.ndarray,
    signals: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Compute realized daily returns under the next-close execution contract.

    Execution contract:
    - Signal generated at close[t-1] executes at close[t].
    - Across interval (t -> t+1), the position held is signals[t-1].
    - The realized return earned from close[t] to close[t+1] is:
      realized_return[t+1] = signals[t-1] * (prices[t+1] / prices[t] - 1.0).

    Args:
        prices: Sequence of close prices.
        signals: Sequence of signals generated at each session.

    Returns:
        1D float64 array of realized returns for each session [0, ..., N-1].
        For t in {0, 1}, return is 0.0 because the earliest possible execution of signals[0]
        happens at close[1], earning return across (1 -> 2).
    """
    p = np.asarray(prices, dtype=np.float64)
    s = np.asarray(signals, dtype=np.float64)
    if len(p) != len(s):
        raise ValueError(f"價格長度 ({len(p)}) 與訊號長度 ({len(s)}) 必須一致。")

    n = len(p)
    realized_returns = np.zeros(n, dtype=np.float64)
    if n <= 2:
        return realized_returns

    # For session t (where t >= 2):
    # Position held during (t-1 -> t) is s[t-2] (generated at t-2, entered at close[t-1]).
    price_return = (p[2:] / p[1:-1]) - 1.0
    realized_returns[2:] = s[:-2] * price_return
    return realized_returns
