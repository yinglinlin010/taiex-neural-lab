"""Regression guards for synthetic time-series and locked-test boundaries."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.data import Series, build_samples, walk_forward_folds
import app.main as main_module
from app.main import app


def synthetic_series(n: int = 1800) -> Series:
    """Deterministic synthetic closes; no market data is used by these tests."""
    dates = [(date(2010, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    t = np.arange(n, dtype=np.float64)
    closes = 100.0 * np.exp(0.0003 * t + 0.02 * np.sin(t / 13.0))
    return Series(dates, closes, {"source": "synthetic test fixture"}, "synthetic")


@pytest.mark.parametrize("horizon", [1, 5, 20])
def test_sample_origin_entry_target_and_return_alignment(horizon: int):
    series = synthetic_series()
    samples = build_samples(series, ["return_1"], lookback=10, horizon=horizon, use_log_return=False)

    np.testing.assert_array_equal(samples["entry_indices"], samples["origins"] + 1)
    np.testing.assert_array_equal(samples["targets"], samples["entry_indices"] + horizon)
    np.testing.assert_allclose(
        samples["y"],
        series.closes[samples["targets"]] / series.closes[samples["entry_indices"]] - 1.0,
    )
    assert np.all(samples["origins"] < samples["entry_indices"])
    assert np.all(samples["entry_indices"] < samples["targets"])
    assert np.all(samples["targets"] < len(series.closes))


def test_walk_forward_labels_remain_before_locked_partition():
    samples = build_samples(synthetic_series(), ["return_1"], lookback=10, horizon=20, use_log_return=False)
    split = samples["split_index"]
    folds = walk_forward_folds(samples)

    assert len(folds) >= 2
    for train_idx, validation_idx in folds:
        assert len(train_idx) and len(validation_idx)
        assert np.all(samples["targets"][train_idx] < split)
        assert np.all(samples["targets"][validation_idx] < split)
        assert samples["targets"][train_idx].max() < samples["origins"][validation_idx].min()


def test_full_series_api_honors_end_cutoff(monkeypatch):
    series = synthetic_series(24)
    cutoff = series.dates[16]
    monkeypatch.setattr(main_module, "load_series", lambda symbol="TAIEX": series)

    response = TestClient(app).get(f"/api/data/series?full=true&end={cutoff}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["full"] is True
    assert payload["rangeEnd"] == cutoff
    assert [point["date"] for point in payload["points"]] == series.dates[:17]
    assert all(point["date"] <= cutoff for point in payload["points"])


def test_final_evaluation_rejects_tcn_before_loading_data(monkeypatch):
    monkeypatch.setattr(main_module, "load_series", lambda symbol="TAIEX": pytest.fail("data must not be loaded"))

    response = TestClient(app).post(
        "/api/final-evaluation",
        json={
            "modelTypes": ["tcn"],
            "features": ["return_1"],
            "lookback": 5,
            "horizon": 1,
            "epochs": 20,
        },
    )

    assert response.status_code == 422
    assert "TCN" in response.json()["detail"]
