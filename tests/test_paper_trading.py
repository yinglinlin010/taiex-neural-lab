from __future__ import annotations

import pytest
import numpy as np
import sqlite3
import json
import re
from pathlib import Path
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.paper import advance_account, create_account, list_accounts, pause_account, resume_account, update_account_settings, update_mascot
import app.main as main_module
from app.data import Series, build_samples, is_tradable_equity
from app.main import app
from app.ml import TrainingConfig, fit_deployment_artifact, predict_with_artifact, pre_test_training_indices
from app.data import build_latest_feature_window


def bars(closes):
    return [f"2026-01-{day:02d}" for day in range(1, len(closes) + 1)], closes


def test_paper_capital_fields_accept_default_100000_whole_dollar_amount():
    html = (Path(__file__).resolve().parents[1] / "web" / "paper.html").read_text()
    capital_input = re.search(r'<input id="capital"[^>]*>', html)
    assert capital_input
    assert 'min="1"' in capital_input.group()
    assert 'step="1"' in capital_input.group()
    assert 100_000 >= 1 and (100_000 - 1) % 1 == 0

    script = (Path(__file__).resolve().parents[1] / "web" / "paper.js").read_text()
    assert "field('editCapital','模擬本金',account.initialCash,1,100000000,1)" in script


def test_list_accounts_does_not_create_database_on_read(tmp_path):
    path = tmp_path / "absent" / "paper.sqlite3"
    assert list_accounts(path) == []
    assert not path.exists()


def test_latest_feature_window_requires_full_warmup_and_is_causal():
    closes = np.linspace(100, 200, 50).tolist()
    with pytest.raises(ValueError, match="資料不足"):
        build_latest_feature_window(closes[:39], ["volatility_20"], 20)
    first = build_latest_feature_window(closes, ["return_1", "volatility_20"], 5)
    log_window = build_latest_feature_window(closes, ["return_1", "volatility_20"], 5, "log")
    changed_future = closes[:-1] + [9999]
    second = build_latest_feature_window(changed_future, ["return_1", "volatility_20"], 5)
    assert first.shape == (5, 2)
    assert not np.allclose(first, log_window)
    assert not np.array_equal(first, second)


def test_tradable_equity_guard_matches_local_stock_universe():
    assert is_tradable_equity("2330.TW")
    assert not is_tradable_equity("TAIEX")
    assert not is_tradable_equity("OTHER_INDEX")
    assert not is_tradable_equity(" 2330.TW ")
    assert not is_tradable_equity(2330)


def test_pre_test_training_indices_excludes_labels_on_and_after_split():
    from app.ml import pre_test_training_indices

    samples = {"targets": np.asarray([2, 4, 5, 6]), "split_index": 5}

    np.testing.assert_array_equal(pre_test_training_indices(samples), np.asarray([0, 1]))
    np.testing.assert_array_equal(
        pre_test_training_indices({"targets": np.asarray([], dtype=int), "split_index": 0}),
        np.asarray([], dtype=int),
    )


@pytest.mark.parametrize("horizon", [1, 5, 20])
def test_pre_test_training_indices_purges_horizon_labels_at_locked_boundary(horizon):
    from app.ml import pre_test_training_indices

    dates = [(date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(1000)]
    closes = np.linspace(100, 200, len(dates))
    samples = build_samples(Series(dates, closes, {}, "fixture"), ["return_1"], 5, horizon, False)

    train = pre_test_training_indices(samples)

    assert samples["targets"][train].max() == samples["split_index"] - 1
    assert np.all(samples["targets"][train] < samples["split_index"])


def test_deployment_artifact_inference_validates_shape_and_is_deterministic():
    dates = [(date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(900)]
    closes = 100 * np.exp(np.cumsum(np.sin(np.arange(len(dates))) * 0.002 + 0.0003))
    series = Series(dates=dates,
                    closes=closes, source={}, digest="fixture")
    from app.data import build_samples
    samples = build_samples(series, ["return_1", "return_5"], 5, 1, False)
    artifact = fit_deployment_artifact(samples, "mlp", TrainingConfig(epochs=1, batch_size=64, hidden_sizes=[4], hidden_layers=1))
    train_idx = pre_test_training_indices(samples)
    assert np.array_equal(samples["targets"][train_idx], samples["targets"][samples["targets"] < samples["split_index"]])
    assert samples["targets"][train_idx].max() < samples["split_index"]
    assert artifact["trainingThrough"] == dates[int(samples["targets"][train_idx].max())]
    assert artifact["testBoundary"] == dates[samples["split_index"]]
    window = build_latest_feature_window(closes, ["return_1", "return_5"], 5)
    assert predict_with_artifact(artifact, window) == pytest.approx(predict_with_artifact(artifact, window))
    with pytest.raises(ValueError, match="形狀"):
        predict_with_artifact(artifact, window[:-1])


def test_neural_paper_account_uses_frozen_artifact_each_new_session(tmp_path):
    from app.data import Series, build_samples
    from app.ml import TrainingConfig, fit_deployment_artifact
    closes = (100 * np.exp(np.cumsum(np.sin(np.arange(900)) * 0.001 + 0.0002))).tolist()
    dates = [f"{2000 + index // 365}-{(index % 365) // 28 + 1:02d}-{(index % 28) + 1:02d}" for index in range(900)]
    # ISO dates need valid days/months; use monotonic real calendar days.
    start = date(2000, 1, 1)
    dates = [(start + timedelta(days=index)).isoformat() for index in range(900)]
    sample = build_samples(Series(dates, np.asarray(closes), {}, "fixture"), ["return_1"], 5, 1, False)
    artifact = fit_deployment_artifact(sample, "mlp", TrainingConfig(epochs=1, batch_size=128, hidden_sizes=[4], hidden_layers=1))
    # Produce a legal long-lookback artifact with wide feature warmup coverage.
    sample = build_samples(Series(dates, np.asarray(closes), {}, "fixture"), ["volatility_20"], 60, 1, True)
    artifact = fit_deployment_artifact(sample, "mlp", TrainingConfig(epochs=1, batch_size=128, hidden_sizes=[4], hidden_layers=1))
    db = tmp_path / "paper.sqlite3"
    account = create_account("TEST", dates[:850], closes[:850], lookback=20, initial_cash=50000,
                             strategy="neural", model_artifact=artifact, buy_threshold=0.0,
                             sell_threshold=-0.0001, db_path=db)
    assert account["strategy"] == "neural"
    assert account["model"]["key"] == "mlp"
    updated = advance_account(account["id"], dates, closes, db_path=db)
    assert updated["advancedSessions"] == 50
    neural_closes = [event for event in updated["events"] if event["kind"] == "close" and "prediction" in event]
    assert len(neural_closes) == 50
    assert all(np.isfinite(event["prediction"]) and event["model"] == "mlp" for event in neural_closes)
    repeated = advance_account(account["id"], dates, closes, db_path=db)
    assert repeated["advancedSessions"] == 0


def test_neural_neutral_signal_holds_and_bearish_signal_exits_next_close(monkeypatch, tmp_path):
    import app.paper as paper_module
    predictions = iter([0.01, 0.0, -0.01, -0.01])  # initial buy, neutral hold, bearish exit
    monkeypatch.setattr(paper_module, "predict_with_artifact", lambda *_args: next(predictions))
    dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(40)]
    closes = [100.0 + index for index in range(40)]
    artifact = {"model": "mlp", "horizon": 1, "features": ["return_1"], "trainingThrough": dates[20],
                "returnType": "simple", "lookback": 5}
    db = tmp_path / "paper.sqlite3"
    account = create_account("TEST", dates[:30], closes[:30], strategy="neural", model_artifact=artifact,
                             lookback=5, buy_threshold=0.002, sell_threshold=-0.002,
                             initial_cash=100000, db_path=db)
    first = advance_account(account["id"], dates[:31], closes[:31], db_path=db)
    assert any(event["kind"] == "buy" and event["date"] == dates[30] for event in first["events"])
    assert first["pendingAction"] == "持有"
    second = advance_account(account["id"], dates[:32], closes[:32], db_path=db)
    assert not any(event["kind"] == "sell" for event in second["events"])
    third = advance_account(account["id"], dates[:33], closes[:33], db_path=db)
    sells = [event for event in third["events"] if event["kind"] == "sell"]
    assert len(sells) == 1 and sells[0]["date"] == dates[32]
    assert third["shares"] == 0


def test_neural_paper_api_requires_same_data_and_locked_boundary(monkeypatch, tmp_path):
    from app.data import Series
    import app.main as main
    closes = np.linspace(100, 110, 900)
    dates = [(date(2000, 1, 1) + timedelta(days=index)).isoformat() for index in range(900)]
    digest = "current-digest"
    series = Series(dates, closes, {}, digest)
    monkeypatch.setattr(main, "_paper_series", lambda _symbol: series)
    monkeypatch.setattr(main.paper_trading, "DEFAULT_DB", tmp_path / "paper.sqlite3")
    monkeypatch.setattr(main, "get_latest_validation", lambda _symbol: {
        "datasetHash": "stale-digest", "config": {"buyThreshold": 0.002, "sellThreshold": -0.002},
        "result": {"testBoundary": dates[800], "models": [{"key": "mlp"}]},
    })
    response = TestClient(app).post("/api/paper/accounts", json={"symbol": "2330.TW", "strategy": "neural", "model": "mlp"})
    assert response.status_code == 422
    assert "相符的最新驗證" in response.json()["detail"]


def test_neural_paper_api_rejects_validation_without_spent_locked_test(monkeypatch, tmp_path):
    from app.data import Series
    import app.main as main
    closes = np.linspace(100, 110, 900)
    dates = [(date(2000, 1, 1) + timedelta(days=index)).isoformat() for index in range(900)]
    series = Series(dates, closes, {}, "same-digest")
    monkeypatch.setattr(main, "_paper_series", lambda _symbol: series)
    monkeypatch.setattr(main.paper_trading, "DEFAULT_DB", tmp_path / "paper.sqlite3")
    monkeypatch.setattr(main, "get_latest_validation", lambda _symbol: {
        "datasetHash": "same-digest", "config": {"buyThreshold": 0.002, "sellThreshold": -0.002},
        "result": {"testBoundary": dates[720], "models": [{"key": "mlp"}]},
    })
    monkeypatch.setattr(main, "_final_state_for_dataset", lambda *_args: {"status": "available"})
    response = TestClient(app).post("/api/paper/accounts", json={"symbol": "2330.TW", "strategy": "neural", "model": "mlp"})
    assert response.status_code == 422
    assert "鎖定測試" in response.json()["detail"]


def test_paper_api_rejects_non_stock_symbols_before_loading_series(monkeypatch):
    monkeypatch.setattr(main_module, "_paper_series", lambda _symbol: pytest.fail("non-stock symbols must be rejected first"))

    response = TestClient(app).post("/api/paper/accounts", json={"symbol": "OTHER_INDEX"})

    assert response.status_code == 422
    assert "只支援本機個股清單" in response.json()["detail"]


def test_account_starts_at_latest_close_and_waits_for_next_session(tmp_path):
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=1000,
                             max_exposure_pct=20, db_path=tmp_path / "paper.sqlite3")

    assert account["lastDate"] == dates[-1]
    assert account["cash"] == 1000
    assert account["shares"] == 0
    assert account["pendingAction"] == "買進待下個收盤"
    assert account["events"][-1]["kind"] == "started"


def test_new_session_fills_next_close_with_integer_shares_and_costs(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=1000,
                             commission_rate=0.001, slippage_bps=100,
                             max_exposure_pct=20, db_path=db)

    next_dates, next_closes = bars([100, 100, 110, 120])
    updated = advance_account(account["id"], next_dates, next_closes, db_path=db)
    buy = next(event for event in updated["events"] if event["kind"] == "buy")
    expected_fill = 120 * 1.01
    assert updated["advancedSessions"] == 1
    assert buy["fillPrice"] == pytest.approx(expected_fill)
    assert buy["shares"] == 1
    assert buy["commission"] == pytest.approx(expected_fill * 0.001)
    assert updated["cash"] >= 0
    assert updated["costAssumptions"]["maxExposurePct"] == 20


def test_small_exposure_rejects_order_without_negative_cash(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10,
                             max_exposure_pct=20, db_path=db)
    next_dates, next_closes = bars([100, 100, 110, 120, 130])
    updated = advance_account(account["id"], next_dates, next_closes, db_path=db)
    assert updated["cash"] == 10
    assert updated["shares"] == 0
    rejected = next(event for event in updated["events"] if event["kind"] == "rejected")
    assert rejected["policy"] == "本次委託未成交；若收盤訊號仍看多，下一日重試；訊號轉空手時明確取消。"
    rejected_dates = [event["date"] for event in updated["events"] if event["kind"] == "rejected"]
    assert rejected_dates == next_dates[3:]
    assert updated["historyVerification"] == "verified"


def test_account_can_advance_from_a_pruned_but_overlapping_history_window(tmp_path):
    db = tmp_path / "paper.sqlite3"
    full_dates, full_closes = bars([90, 95, 100, 100, 110, 120])
    account = create_account("TEST", full_dates[:5], full_closes[:5], lookback=2, db_path=db)

    # The source retained only the last lookback window before the account date.
    retained_dates = full_dates[2:]
    retained_closes = full_closes[2:]
    updated = advance_account(account["id"], retained_dates, retained_closes, db_path=db)
    assert updated["lastDate"] == full_dates[-1]
    assert updated["advancedSessions"] == 1


def test_pruned_window_still_rejects_revision_inside_required_lookback(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([90, 95, 100, 100])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    retained_dates, retained_closes = dates[1:], [96, 100, 100]
    with pytest.raises(ValueError, match="回看窗收盤資料發生變更"):
        advance_account(account["id"], retained_dates, retained_closes, db_path=db)


def test_account_can_resume_after_source_prunes_its_lookback_window(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([90, 95, 100, 105, 110, 115, 120])
    account = create_account("TEST", dates[:5], closes[:5], lookback=2, db_path=db)
    advanced = advance_account(account["id"], dates, closes, db_path=db)
    assert advanced["lastDate"] == dates[-1]

    # Older rows can be pruned while the complete saved lookback remains present.
    pruned_dates = dates[4:] + ["2026-01-08", "2026-01-09", "2026-01-10"]
    pruned_closes = closes[4:] + [125, 130, 135]
    resumed = advance_account(account["id"], pruned_dates, pruned_closes, db_path=db)
    assert resumed["lastDate"] == pruned_dates[-1]
    assert resumed["advancedSessions"] == 3
    following_dates = pruned_dates[-3:] + ["2026-01-11"]
    following_closes = pruned_closes[-3:] + [140]
    following = advance_account(account["id"], following_dates, following_closes, db_path=db)
    assert following["lastDate"] == following_dates[-1]
    assert following["advancedSessions"] == 1


def test_pruned_sync_uses_saved_strategy_context_for_identical_signals(tmp_path):
    dates, closes = bars([100, 110, 90, 95, 120, 80])
    full = create_account("TEST", dates[:4], closes[:4], lookback=2,
                          initial_cash=10_000, db_path=tmp_path / "full.sqlite3")
    pruned = create_account("TEST", dates[:4], closes[:4], lookback=2,
                            initial_cash=10_000, db_path=tmp_path / "pruned.sqlite3")
    extra_history = create_account("TEST", dates[:4], closes[:4], lookback=2,
                                   initial_cash=10_000, db_path=tmp_path / "extra.sqlite3")

    full_state = advance_account(full["id"], dates, closes, db_path=tmp_path / "full.sqlite3")
    pruned_state = advance_account(pruned["id"], dates[1:], closes[1:], db_path=tmp_path / "pruned.sqlite3")
    extra_closes = [999, *closes[1:]]
    extra_state = advance_account(extra_history["id"], dates, extra_closes, db_path=tmp_path / "extra.sqlite3")
    assert pruned_state["historyVerification"] == "verified"
    assert pruned_state["cash"] == pytest.approx(full_state["cash"])
    assert pruned_state["shares"] == full_state["shares"]
    assert extra_state["cash"] == pytest.approx(full_state["cash"])
    assert extra_state["shares"] == full_state["shares"]
    assert [(event["date"], event["kind"]) for event in pruned_state["events"]
            if event["kind"] in ("buy", "sell")] == [
                (event["date"], event["kind"]) for event in full_state["events"]
                if event["kind"] in ("buy", "sell")]


def test_sync_continues_when_provider_prunes_older_saved_anchor(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 105])
    account = create_account("TEST", dates, closes, lookback=1, db_path=db)
    retained_dates = [dates[-1], "2026-01-04"]
    retained_closes = [closes[-1], 110]

    advanced = advance_account(account["id"], retained_dates, retained_closes, db_path=db)
    assert advanced["lastDate"] == retained_dates[-1]
    assert advanced["advancedSessions"] == 1
    assert advanced["historyVerification"] == "verified_with_saved_anchors"


def test_sync_can_use_stored_full_lookback_when_source_keeps_only_last_date(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([90, 95, 100, 105])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    retained_dates = [dates[-1], "2026-01-05", "2026-01-06"]
    retained_closes = [closes[-1], 110, 115]
    advanced = advance_account(account["id"], retained_dates, retained_closes, db_path=db)
    assert advanced["lastDate"] == retained_dates[-1]
    assert advanced["advancedSessions"] == 2
    assert advanced["historyVerification"] == "verified_with_saved_anchors"


def test_legacy_account_without_saved_history_fails_closed(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 105, 110])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    with sqlite3.connect(db) as connection:
        connection.execute("DELETE FROM paper_history WHERE account_id=?", (account["id"],))

    with pytest.raises(ValueError, match="缺少可驗證的策略錨點"):
        advance_account(account["id"], dates + ["2026-01-04"], closes + [115], db_path=db)

    unchanged = list_accounts(db)[0]
    assert unchanged["lastDate"] == dates[-1]
    assert unchanged["tradeCount"] == 0
    assert [event["kind"] for event in unchanged["events"]] == ["started"]


def test_modified_persisted_anchor_fails_closed_without_advancing(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 105, 110])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE paper_history SET close=close+1 WHERE account_id=? AND date=?",
                           (account["id"], dates[-2]))

    with pytest.raises(ValueError, match="儲存的策略錨點不一致"):
        advance_account(account["id"], dates + ["2026-01-04"], closes + [115], db_path=db)

    unchanged = list_accounts(db)[0]
    assert unchanged["lastDate"] == dates[-1]
    assert unchanged["tradeCount"] == 0


def test_pruned_source_still_rejects_changes_in_available_overlap(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 105, 110, 115])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    retained_dates = dates[2:] + ["2026-01-05"]
    retained_closes = [111, 115, 120]
    with pytest.raises(ValueError, match="回看窗收盤資料發生變更"):
        advance_account(account["id"], retained_dates, retained_closes, db_path=db)


def test_float_serialization_noise_is_tolerated_but_price_revision_is_not(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 101, 102])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    tiny_noise = [100.0, 101.0, 102.0 + 5e-13, 103.0]
    accepted = advance_account(account["id"], dates + ["2026-01-04"], tiny_noise, db_path=db)
    assert accepted["lastDate"] == "2026-01-04"

    next_dates = dates + ["2026-01-04", "2026-01-05"]
    revised = [100.0, 101.0, 102.0001, 103.0, 104.0]
    with pytest.raises(ValueError, match="收盤價已變更|回看窗收盤資料發生變更"):
        advance_account(account["id"], next_dates, revised, db_path=db)


def test_daily_drawdown_is_marked_to_market_and_reaches_extreme_move(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=100_000,
                             max_exposure_pct=20, db_path=db)
    d4, p4 = bars([100, 100, 110, 120])
    held = advance_account(account["id"], d4, p4, db_path=db)
    d5, p5 = bars([100, 100, 110, 120, 60])
    drawdown = advance_account(account["id"], d5, p5, db_path=db)
    assert drawdown["maxDrawdownPct"] > 8
    assert drawdown["shares"] == held["shares"]
    assert drawdown["pendingAction"] == "賣出待下個收盤"
    latest_close = next(event for event in reversed(drawdown["events"]) if event["kind"] == "close")
    assert latest_close["peak"] >= latest_close["equity"]
    assert latest_close["maxDrawdown"] * 100 == pytest.approx(drawdown["maxDrawdownPct"])

    d6, p6 = bars([100, 100, 110, 120, 60, 200])
    recovered = advance_account(account["id"], d6, p6, db_path=db)
    assert recovered["maxDrawdownPct"] >= drawdown["maxDrawdownPct"]
    latest_recovered = next(event for event in reversed(recovered["events"]) if event["kind"] == "close")
    assert latest_recovered["maxDrawdown"] * 100 == pytest.approx(recovered["maxDrawdownPct"])


def test_legacy_close_events_reconstruct_peak_and_drawdown_on_first_sync(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10_000, db_path=db)
    d4, p4 = bars([100, 100, 110, 120])
    advance_account(account["id"], d4, p4, db_path=db)

    with sqlite3.connect(db) as connection:
        payload = connection.execute(
            "SELECT payload FROM paper_events WHERE account_id=? AND kind='close' ORDER BY seq DESC LIMIT 1",
            (account["id"],),
        ).fetchone()[0]
        old_payload = json.loads(payload)
        old_payload.pop("peak", None)
        old_payload.pop("maxDrawdown", None)
        connection.execute(
            "UPDATE paper_events SET payload=? WHERE account_id=? AND kind='close' AND date=?",
            (json.dumps(old_payload), account["id"], d4[-1]),
        )

    d5, p5 = bars([100, 100, 110, 120, 60])
    updated = advance_account(account["id"], d5, p5, db_path=db)
    latest = next(event for event in reversed(updated["events"]) if event["kind"] == "close")
    assert latest["peak"] >= old_payload["equity"]
    assert latest["maxDrawdown"] * 100 == pytest.approx(updated["maxDrawdownPct"])


def test_repeated_sync_is_idempotent_and_history_revisions_fail_closed(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    same = advance_account(account["id"], dates, closes, db_path=db)
    assert same["advancedSessions"] == 0
    assert same["lastDate"] == dates[-1]

    revised_dates, revised_closes = bars([100, 101, 110, 120])
    with pytest.raises(ValueError, match="回看窗收盤資料發生變更"):
        advance_account(account["id"], revised_dates, revised_closes, db_path=db)
    with pytest.raises(ValueError, match="必須保留帳戶最後交易日"):
        advance_account(account["id"], dates[:2], closes[:2], db_path=db)
    assert list_accounts(db)[0]["lastDate"] == dates[-1]


def test_exit_signal_sells_next_session_after_costs(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10_000,
                             max_exposure_pct=20, commission_rate=0.001,
                             sell_tax_rate=0.003, slippage_bps=10, db_path=db)
    d4, p4 = bars([100, 100, 110, 120])
    held = advance_account(account["id"], d4, p4, db_path=db)
    assert held["shares"] > 0
    d5, p5 = bars([100, 100, 110, 120, 90])
    pending_exit = advance_account(account["id"], d5, p5, db_path=db)
    assert pending_exit["shares"] == held["shares"]
    d6, p6 = bars([100, 100, 110, 120, 90, 80])
    closed = advance_account(account["id"], d6, p6, db_path=db)
    sells = [event for event in closed["events"] if event["kind"] == "sell"]
    assert len(sells) == 1
    assert sells[0]["date"] == d6[-1]
    assert sells[0]["sellTax"] > 0
    assert closed["shares"] == 0
    assert closed["cash"] < held["cash"] + held["shares"] * held["lastClose"]


def test_signal_reversal_is_executed_one_close_later_without_same_close_reentry(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10_000, db_path=db)
    dates, closes = bars([100, 100, 110, 120])
    advance_account(account["id"], dates, closes, db_path=db)
    dates, closes = bars([100, 100, 110, 120, 90])
    advance_account(account["id"], dates, closes, db_path=db)
    dates, closes = bars([100, 100, 110, 120, 90, 200])
    exited = advance_account(account["id"], dates, closes, db_path=db)
    assert exited["shares"] == 0
    assert exited["pendingAction"] == "買進待下個收盤"
    dates, closes = bars([100, 100, 110, 120, 90, 200, 210])
    reentered = advance_account(account["id"], dates, closes, db_path=db)
    sales = [event for event in reentered["events"] if event["kind"] == "sell"]
    buys = [event for event in reentered["events"] if event["kind"] == "buy"]
    assert [event["date"] for event in sales] == ["2026-01-06"]
    assert [event["date"] for event in buys] == ["2026-01-04", "2026-01-07"]
    assert reentered["shares"] > 0
    assert reentered["retired"] is False


def test_pause_schedules_close_only_exit_and_stops_reentry(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10_000,
                             db_path=db)
    d4, p4 = bars([100, 100, 110, 120])
    held = advance_account(account["id"], d4, p4, db_path=db)
    assert held["shares"] > 0
    paused = pause_account(account["id"], db_path=db)
    assert paused["paused"] is True
    with pytest.raises(ValueError, match="仍有持倉"):
        resume_account(account["id"], db_path=db)
    d5, p5 = bars([100, 100, 110, 120, 130])
    closed = advance_account(account["id"], d5, p5, db_path=db)
    assert closed["shares"] == 0
    assert closed["paused"] is True
    assert closed["pendingAction"] == "已停止"
    assert closed["retired"] is True
    assert closed["events"][-1]["kind"] == "retired"
    with pytest.raises(ValueError, match="已退場"):
        resume_account(account["id"], db_path=db)
    d6, p6 = bars([100, 100, 110, 120, 130, 140])
    with pytest.raises(ValueError, match="已退場"):
        advance_account(account["id"], d6, p6, db_path=db)
    assert list_accounts(db)[0]["id"] == account["id"]
    assert list_accounts(db)[0]["retired"] is True


def test_empty_account_retires_immediately_and_migrates_legacy_schema(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 101, 102])
    account = create_account("TEST", dates, closes, lookback=2, db_path=db)
    connection = sqlite3.connect(db)
    connection.executescript("""
      ALTER TABLE paper_events RENAME TO paper_events_modern;
      CREATE TABLE paper_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL REFERENCES paper_accounts(id),
        date TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
        UNIQUE(account_id, date, kind)
      );
      INSERT INTO paper_events SELECT * FROM paper_events_modern;
      DROP TABLE paper_events_modern;
    """)
    connection.close()

    retired = pause_account(account["id"], db_path=db)
    assert retired["retired"] is True
    kinds = [event["kind"] for event in retired["events"]]
    assert kinds.count("paused") == 1
    assert kinds.count("retired") == 1
    with pytest.raises(ValueError, match="已退場"):
        resume_account(account["id"], db_path=db)


def test_pre_sync_settings_can_change_once_then_freeze(tmp_path):
    db = tmp_path / "paper.sqlite3"
    dates, closes = bars([100, 101, 104])
    account = create_account("TEST", dates, closes, lookback=2, initial_cash=10000, db_path=db)
    edited = update_account_settings(
        account["id"], lookback=1, initial_cash=25000, commission_rate=0.002,
        sell_tax_rate=0.004, slippage_bps=20, max_exposure_pct=35, db_path=db,
    )
    assert edited["firstSync"] is False
    assert edited["initialCash"] == 25000
    assert edited["cash"] == 25000
    assert edited["lookback"] == 1
    assert edited["costAssumptions"]["maxExposurePct"] == 35
    next_dates, next_closes = bars([100, 101, 104, 108])
    synced = advance_account(account["id"], next_dates, next_closes, db_path=db)
    assert synced["firstSync"] is True
    with pytest.raises(ValueError, match="已凍結"):
        update_account_settings(
            account["id"], lookback=1, initial_cash=30000, commission_rate=0.002,
            sell_tax_rate=0.004, slippage_bps=20, max_exposure_pct=35, db_path=db,
        )


def test_mascot_identity_persists_and_is_editable_after_retirement(tmp_path):
    dates, closes = bars([100, 100, 110])
    account = create_account("TEST", dates, closes, lookback=2, db_path=tmp_path / "paper.sqlite3",
                             nickname="小雲", mascot_color="blue", mascot_accessory="beret")
    assert account["nickname"] == "小雲" and account["mascotColor"] == "blue"
    assert account["mascotAccessory"] == "beret"
    edited = update_mascot(account["id"], nickname="新名字", mascot_color="red", mascot_accessory="crown",
                           db_path=tmp_path / "paper.sqlite3")
    assert edited["nickname"] == "新名字" and edited["mascotColor"] == "red"
    assert edited["mascotAccessory"] == "crown"
    retired = pause_account(account["id"], db_path=tmp_path / "paper.sqlite3")
    assert retired["retired"] is True
    edited_after_exit = update_mascot(account["id"], nickname="紀念", mascot_color="cream", mascot_accessory="none",
                                      db_path=tmp_path / "paper.sqlite3")
    assert edited_after_exit["retired"] is True and edited_after_exit["nickname"] == "紀念"
    with pytest.raises(ValueError, match="外觀設定無效"):
        update_mascot(account["id"], nickname="紀念", mascot_color="cream", mascot_accessory="helmet",
                      db_path=tmp_path / "paper.sqlite3")


def test_creation_key_retries_return_same_account(tmp_path):
    dates, closes = bars([100, 100, 110])
    db = tmp_path / "paper.sqlite3"
    kwargs = {"lookback": 2, "db_path": db, "creation_key": "retry-key-123456789"}
    first = create_account("TEST", dates, closes, **kwargs)
    retry = create_account("TEST", dates, closes, **kwargs)
    assert retry["id"] == first["id"]
    assert retry["nickname"] == first["nickname"]
    assert len(list_accounts(db)) == 1
    with pytest.raises(ValueError, match="不同設定"):
        create_account("TEST", dates, closes, nickname="duplicate", **kwargs)


def test_room_sync_continues_after_one_account_data_failure(tmp_path, monkeypatch):
    import app.main as main
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(25)]
    closes = np.linspace(100, 130, len(dates))
    series = Series(dates, closes, {"fields": ["date", "close"]}, "synthetic")
    db = tmp_path / "paper.sqlite3"
    monkeypatch.setattr(main.paper_trading, "DEFAULT_DB", db)
    first = create_account("OK", dates[:-1], closes[:-1].tolist(), lookback=20, db_path=db)
    second = create_account("FAIL", dates[:-1], closes[:-1].tolist(), lookback=20, db_path=db)
    def load(symbol):
        if symbol == "FAIL":
            raise ValueError("fixture has no current data")
        return series
    monkeypatch.setattr(main, "_paper_series", load)
    response = TestClient(app).post("/api/paper/sync-all")
    assert response.status_code == 200
    outcomes = {item["id"]: item for item in response.json()["outcomes"]}
    assert outcomes[first["id"]]["ok"] is True
    assert outcomes[first["id"]]["advancedSessions"] == 1
    assert outcomes[second["id"]]["ok"] is False
    assert "fixture" in outcomes[second["id"]]["error"]


@pytest.mark.parametrize("kwargs", [
    {"initial_cash": 0}, {"initial_cash": float("inf")},
    {"lookback": 0}, {"lookback": 253}, {"slippage_bps": 501},
    {"max_exposure_pct": 0}, {"max_exposure_pct": 100.1},
    {"initial_cash": "cash"}, {"max_exposure_pct": True},
])
def test_account_rejects_extreme_or_invalid_settings(tmp_path, kwargs):
    dates, closes = bars([100, 100, 110])
    options = {"lookback": 2, "db_path": tmp_path / "paper.sqlite3", **kwargs}
    with pytest.raises(ValueError):
        create_account("TEST", dates, closes, **options)


def test_account_rejects_unsorted_duplicate_dates_and_invalid_prices(tmp_path):
    with pytest.raises(ValueError, match="嚴格遞增"):
        create_account("TEST", ["2026-01-02", "2026-01-01", "2026-01-03"],
                       [100, 101, 102], lookback=2, db_path=tmp_path / "a.sqlite3")
    with pytest.raises(ValueError, match="有限正數"):
        create_account("TEST", ["2026-01-01", "2026-01-02", "2026-01-03"],
                       [100, float("nan"), 102], lookback=2, db_path=tmp_path / "b.sqlite3")
    with pytest.raises(ValueError, match="有效的 YYYY-MM-DD"):
        create_account("TEST", ["2026-02-30", "2026-03-01", "2026-03-02"],
                       [100, 101, 102], lookback=2, db_path=tmp_path / "c.sqlite3")


def test_paper_api_creates_and_advances_synthetic_account_only(tmp_path, monkeypatch):
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(25)]
    closes = np.linspace(100, 130, len(dates))
    series = Series(dates, closes, {"fields": ["date", "close"]}, "synthetic")
    monkeypatch.setattr(main_module, "load_series", lambda _symbol: series)
    monkeypatch.setattr(main_module, "is_tradable_equity", lambda symbol: symbol == "TEST")
    real_db = main_module.paper_trading.DEFAULT_DB
    real_accounts_before = main_module.paper_trading.list_accounts(real_db)
    monkeypatch.setattr(main_module.paper_trading, "DEFAULT_DB", tmp_path / "api-paper.sqlite3")
    client = TestClient(app)

    page = client.get("/paper")
    assert page.status_code == 200 and "紙上交易室" in page.text
    assert 'id="callDialog"' in page.text and 'id="roomSeats"' in page.text
    create_payload = {"symbol": "TEST", "lookback": 20, "initialCash": 100000,
                      "creationKey": "api-retry-key-123456789"}
    created = client.post("/api/paper/accounts", json=create_payload)
    assert created.status_code == 200
    assert created.json()["account"]["initialCash"] == 100000
    account_id = created.json()["account"]["id"]
    assert created.json()["account"]["lastDate"] == dates[-1]
    retried = client.post("/api/paper/accounts", json=create_payload)
    assert retried.status_code == 200 and retried.json()["account"]["id"] == account_id
    listed = client.get("/api/paper/accounts")
    assert listed.status_code == 200 and listed.json()["accounts"][0]["id"] == account_id
    advanced = client.post(f"/api/paper/accounts/{account_id}/advance")
    assert advanced.status_code == 200
    assert advanced.json()["account"]["advancedSessions"] == 0
    paused = client.post(f"/api/paper/accounts/{account_id}/pause")
    assert paused.status_code == 200 and paused.json()["account"]["paused"] is True
    assert paused.json()["account"]["retired"] is True
    listed = client.get("/api/paper/accounts").json()
    assert listed["accounts"] == [] and listed["retiredAccounts"][0]["id"] == account_id
    assert client.post(f"/api/paper/accounts/{account_id}/resume").status_code == 422
    invalid = client.post("/api/paper/accounts", json={"symbol": "TEST", "lookback": 0})
    assert invalid.status_code == 422
    missing_symbol = client.post("/api/paper/accounts", json={"lookback": 20, "initialCash": 50000})
    assert missing_symbol.status_code == 422
    non_tradable_index = client.post("/api/paper/accounts", json={"symbol": "TAIEX"})
    assert non_tradable_index.status_code == 422
    assert main_module.paper_trading.list_accounts(real_db) == real_accounts_before
