#!/usr/bin/env python3
"""Deterministic, network-free smoke check for the sample and fold pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

# Support both `python scripts/synthetic_regression.py` and `python -m ...`
# without requiring an installed package or reading any project data.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.data import Series, build_samples, walk_forward_folds


SEED = 20261023
N_DAYS = 2500


def synthetic_series(seed: int = SEED, n_days: int = N_DAYS) -> Series:
    """Create reproducible positive closes and calendar dates without I/O."""
    rng = np.random.default_rng(seed)
    daily_returns = 0.0002 + rng.normal(0.0, 0.008, size=n_days - 1)
    closes = np.empty(n_days, dtype=np.float64)
    closes[0] = 1000.0
    closes[1:] = closes[0] * np.exp(np.cumsum(daily_returns))
    dates = [(date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(n_days)]
    return Series(dates, closes, {"source": "synthetic", "seed": seed}, "synthetic")


def run_smoke(seed: int = SEED, n_days: int = N_DAYS) -> list[str]:
    series = synthetic_series(seed, n_days)
    samples = build_samples(
        series,
        ["return_1", "volatility_5"],
        lookback=10,
        horizon=1,
        use_log_return=True,
    )
    x = samples["x"].reshape(len(samples["x"]), -1).astype(np.float64)
    y = samples["y"].astype(np.float64)
    origins = samples["origins"]
    if len(y) == 0 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("sample generation returned empty or non-finite data")

    folds = walk_forward_folds(samples)
    fold_summaries: list[str] = []
    for number, (train_idx, val_idx) in enumerate(folds, start=1):
        # A tiny closed-form ridge model: feature scaling and coefficients use
        # only the training partition; the intercept is left unregularized.
        x_train, x_val = x[train_idx], x[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        mean = x_train.mean(axis=0)
        scale = x_train.std(axis=0)
        scale[scale < 1e-12] = 1.0
        z_train = (x_train - mean) / scale
        z_val = (x_val - mean) / scale
        design_train = np.column_stack((np.ones(len(z_train)), z_train))
        design_val = np.column_stack((np.ones(len(z_val)), z_val))
        penalty = np.eye(design_train.shape[1], dtype=np.float64) * 1e-6
        penalty[0, 0] = 0.0
        coefficients = np.linalg.solve(design_train.T @ design_train + penalty, design_train.T @ y_train)
        predictions = design_val @ coefficients
        if len(train_idx) < 250 or len(val_idx) < 20:
            raise ValueError(f"fold {number} is below minimum sample counts")
        if not np.isfinite(predictions).all():
            raise ValueError(f"fold {number} produced non-finite predictions")
        if np.max(samples["targets"][train_idx]) >= np.min(samples["targets"][val_idx]):
            raise ValueError(f"fold {number} training labels overlap validation targets")
        mse = float(np.mean((predictions - y_val) ** 2))
        if not np.isfinite(mse):
            raise ValueError(f"fold {number} produced non-finite MSE")
        fold_summaries.append(
            f"fold {number}: train={len(train_idx)}, validation={len(val_idx)}, MSE={mse:.3e}"
        )
    return [
        f"seed={seed}, synthetic_days={n_days}, samples={len(y)}, folds={len(folds)}",
        *fold_summaries,
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED, help=f"random seed (default: {SEED})")
    parser.add_argument("--days", type=int, default=N_DAYS, help=f"synthetic series length (default: {N_DAYS})")
    args = parser.parse_args(argv)
    try:
        summaries = run_smoke(args.seed, args.days)
    except Exception as exc:
        print(f"FAIL synthetic regression: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("PASS synthetic regression")
    for line in summaries:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
