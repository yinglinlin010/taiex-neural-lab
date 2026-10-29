from __future__ import annotations

import json
import ast
import time
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from app.data import FEATURES, Series, build_samples, load_series, walk_forward_folds
import app.main as main_module
from app.main import app
from app.ml import TrainingConfig, _metrics, _model, numpy_mlp_trace, run_validation


def test_monitor_checks_interval_and_relu_widgets_on_their_actual_lesson_steps():
    monitor = Path(__file__).resolve().parents[1].joinpath("scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert "lessonIndex=10; renderLesson(); const visible=!document.querySelector('#predictionIntervalExample').hidden" in monitor
    assert "lessonIndex=13; renderLesson(); const input=document.querySelector('#reluInput')" in monitor
    assert "relu_widget_at_interval_step = guided_fixture" in monitor
    assert "document.querySelector('#predictionIntervalExample').hidden && document.querySelector('#reluExercise').hidden" in monitor
    assert "and interval_ui_ok and relu_widget_at_interval_step and chain_rule_step_ok" in monitor


def test_monitor_emits_the_residual_calibration_check_once():
    monitor = Path(__file__).resolve().parents[1].joinpath("scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert monitor.count('checks.append({"name": "殘差、逐折誤差與預測幅度校準圖"') == 1


def test_monitor_browser_script_splits_svg_history_points_on_whitespace():
    monitor_path = Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py"
    tree = ast.parse(monitor_path.read_text(encoding="utf-8"))
    browser_check = next(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "historyPoints:" in node.value
    )
    assert r".trim().split(/\s+/).length" in browser_check


def test_monitor_browser_navigation_does_not_wait_for_network_idle():
    monitor = Path(__file__).resolve().parents[1].joinpath("scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert 'page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=30000)' in monitor
    assert 'wait_until="networkidle"' not in monitor


def test_monitor_pytest_prefers_project_virtualenv_and_falls_back(tmp_path):
    from scripts.regression_monitor import pytest_interpreter

    project_python = tmp_path / ".venv" / "bin" / "python"
    project_python.parent.mkdir(parents=True)
    project_python.write_text("", encoding="utf-8")
    project_python.chmod(0o755)
    assert pytest_interpreter(tmp_path, "/system/python") == str(project_python)
    project_python.chmod(0o644)
    assert pytest_interpreter(tmp_path, "/system/python") == "/system/python"


def test_forward_pass_lesson_reports_relu_gradient_gate():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    html = (root / "web/index.html").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert "ReLU 的局部梯度是否能通過" in html
    assert "forward_pass_ui_ok = guided_fixture" in monitor
    assert "empty.includes('請輸入可計算的有限神經元值 z 與目標 y')" in monitor
    assert "negative.includes('實際上漲組 n=1：MAE 0.40 pp')" in monitor
    assert "changed.includes('更新後重新計算 L=1.0000')" in monitor
    assert "doubled.includes('更新後重新計算 L=4.8400')" in monitor
    assert "opposite.includes('等於基準')" not in monitor
    assert "changed.includes('更新後重新計算 L=0.0400')" not in monitor
    start = app.index("function calculateForwardPass(")
    end = app.index("\nfunction calculateMultiForwardPass", start)
    script = f"""
const byId = id => ({{forwardPassResult:{{textContent:''}},forwardInput:{{value:'2'}},forwardWeight:{{value:'0.5'}},forwardBias:{{value:'0.2'}}}})[id];
{app[start:end]}
let result=calculateForwardPass(2,0.5,0.2);
if (result.z!==1.2 || result.output!==1.2 || result.reluDerivative!==1) process.exit(1);
result=calculateForwardPass(-2,0.5,0.2);
if (result.z!==-0.8 || result.output!==0 || result.reluDerivative!==0) process.exit(2);
result=calculateForwardPass(-2,0.5,1);
if (result.z!==0 || result.reluDerivative!==0) process.exit(3);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def test_multi_input_lesson_explains_each_weight_gradient_from_its_input():
    import subprocess

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    html = (root / "web/index.html").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    lesson_start = app.index("kicker:'17 · 多輸入神經元'")
    lesson = app[lesson_start:app.index("kicker:'18 ·", lesson_start)]
    assert "每個權重梯度是 δ 乘上自己的輸入" in lesson
    assert "∂L/∂w₁=δx₁=−0.8" in lesson
    assert "∂L/∂w₂=δx₂=−0.4" in lesson
    assert "∂L/∂b=δ=−0.4" in lesson
    assert "敏感度例把 x₁ 加倍至 4" in lesson
    assert "x₁ 加倍為 4" in html
    assert 'id="multiForwardPassResult"' in html
    assert "initial.includes('∂L/∂w₁=-0.80')" in monitor
    assert "initial.includes('∂L/∂w₂=-0.40')" in monitor
    assert "initial.includes('∂L/∂b=-0.40')" in monitor
    assert "targetZero.includes('∂L/∂b=1.60')" in monitor
    assert "targetZero.includes('∂L/∂b=-0.40')" not in monitor
    script = r"""
const fs = require('fs');
const source = fs.readFileSync('web/app.js', 'utf8');
const start = source.indexOf('function calculateMultiForwardPass(');
const end = source.indexOf('\nfunction renderMultiForwardPassExercise', start);
eval(source.slice(start, end) + '\nglobalThis.calculateMultiForwardPassFixture = calculateMultiForwardPass;');
const calculate = globalThis.calculateMultiForwardPassFixture;
const initial = calculate(2, 0.5, 1, -0.4, 0.2, 1);
const doubledInput = calculate(4, 0.5, 1, -0.4, 0.2, 2);
const targetZero = calculate(2, 0.5, 1, -0.4, 0.2, 0);
const close = (actual, expected) => Math.abs(actual - expected) < 1e-12;
if (!close(initial.gradients.w1, -0.8) || !close(initial.gradients.w2, -0.4) || !close(initial.gradients.bias, -0.4) || !close(doubledInput.z, 1.8) || !close(doubledInput.delta, -0.4) || !close(doubledInput.gradients.w1, -1.6) || !close(doubledInput.gradients.w2, -0.4) || !close(targetZero.gradients.bias, 1.6)) process.exit(1);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def test_multi_input_forward_pass_displays_each_weighted_contribution():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert "negative.includes('z=-1.20')" in monitor
    assert "negative.includes('ReLU′(z)=0，所以本例局部梯度為零')" in monitor
    assert "negative.includes('z=0，總和為零時不定義占比')" not in monitor
    assert "LESSONS[11].title.includes('反向傳播')" in monitor
    assert "LESSONS[13].title.includes('觀察 ReLU 如何傳遞梯度')" in monitor
    assert "LESSONS[14].title.includes('方向一致性和幅度誤差')" in monitor
    start = app.index("function calculateMultiForwardPass(")
    end = app.index("\nfunction calculateGradientUpdate", start)
    script = f"""
const nodes = {{
  multiInputX1: {{value:'2'}}, multiInputW1: {{value:'0.5'}},
  multiInputX2: {{value:'1'}}, multiInputW2: {{value:'-0.4'}},
  multiInputBias: {{value:'0.2'}}, multiInputTarget: {{value:'1'}},
  multiForwardPassResult: {{textContent:''}}
}};
const byId = id => nodes[id];
{app[start:end]}
renderMultiForwardPassExercise();
const output = nodes.multiForwardPassResult.textContent;
if (!output.includes('w₁x₁=1.00') || !output.includes('w₂x₂=-0.40') || !output.includes('偏置 b=0.20') || !output.includes('z=0.80') || !output.includes('w₁x₁=125.0%') || !output.includes('w₂x₂=-50.0%') || !output.includes('b=25.0%')) process.exit(1);
nodes.multiInputX1.value='4';
renderMultiForwardPassExercise();
if (!nodes.multiForwardPassResult.textContent.includes('w₁x₁=2.00') || !nodes.multiForwardPassResult.textContent.includes('z=1.80')) process.exit(2);
nodes.multiInputX1.value='-2'; nodes.multiInputW1.value='0.5'; nodes.multiInputX2.value='1'; nodes.multiInputW2.value='0'; nodes.multiInputBias.value='1';
renderMultiForwardPassExercise();
if (!nodes.multiForwardPassResult.textContent.includes('總和為零時不定義占比')) process.exit(3);
nodes.multiInputW2.value='-0.4'; nodes.multiInputBias.value='0.2';
renderMultiForwardPassExercise();
if (!nodes.multiForwardPassResult.textContent.includes('z=-1.20') || !nodes.multiForwardPassResult.textContent.includes('ReLU′(z)=0，所以本例局部梯度為零') || !nodes.multiForwardPassResult.textContent.includes('∂L/∂w₁=0.00')) process.exit(4);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def test_gradient_update_lesson_labels_gradients_and_substitutes_parameters():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    start = app.index("function calculateMultiForwardPass(")
    end = app.index("\nfunction calculateBatchGradientUpdate", start)
    script = f"""
const vm = require('vm');
const nodes = {{
  multiInputX1: {{value:'2'}}, multiInputW1: {{value:'0.5'}},
  multiInputX2: {{value:'1'}}, multiInputW2: {{value:'-0.4'}},
  multiInputBias: {{value:'0.2'}}, multiInputTarget: {{value:'1'}},
  updateTarget: {{value:'1'}}, updateRate: {{value:'0.1'}},
  gradientUpdateResult: {{textContent:''}}
}};
const byId = id => nodes[id];
vm.runInThisContext({json.dumps(app[start:end])});
renderGradientUpdateExercise();
const initial = nodes.gradientUpdateResult.textContent;
if (!initial.includes('∂L/∂w₁=-0.8000') || !initial.includes('∂L/∂w₂=-0.4000') || !initial.includes('∂L/∂b=-0.4000')) process.exit(1);
    if (!initial.includes('w₁ 0.5−0.1×(-0.8000)=0.5800') || !initial.includes('一階損失預測 L+∇L·Δθ=-0.0560') || !initial.includes('更新後重新計算 L=0.0016') || !initial.includes('損失下降')) process.exit(2);
nodes.updateRate.value='0';
renderGradientUpdateExercise();
    if (!nodes.gradientUpdateResult.textContent.includes('更新後重新計算 L=0.0400') || !nodes.gradientUpdateResult.textContent.includes('損失不變')) process.exit(3);
nodes.updateRate.value='0.5';
renderGradientUpdateExercise();
    if (!nodes.gradientUpdateResult.textContent.includes('更新後重新計算 L=1.0000') || !nodes.gradientUpdateResult.textContent.includes('損失上升')) process.exit(4);
nodes.updateRate.value='';
renderGradientUpdateExercise();
if (!nodes.gradientUpdateResult.textContent.includes('請輸入有限數值；學習率需介於 0 與 1')) process.exit(5);
nodes.updateRate.value='2';
renderGradientUpdateExercise();
if (!nodes.gradientUpdateResult.textContent.includes('學習率需介於 0 與 1')) process.exit(6);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def test_finite_difference_lesson_checks_backprop_gradients_and_rejects_invalid_step():
    import json
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    html = (root / "web/index.html").read_text(encoding="utf-8")
    guide = (root / "docs/learning-guide.md").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert 'id="gradientCheckExercise"' in html and 'id="gradientCheckEpsilon"' in html
    assert "calculateFiniteDifferenceGradientCheck" in app and "有限差分核對={gradient_check_ui_ok}" in monitor
    assert "gradient_check_ui_ok = guided_fixture" in monitor and "lessonIndex=17; renderLesson(); const result=document.querySelector('#gradientCheckResult')" in monitor
    assert "gradientCheckEpsilon:'0.001'" in monitor
    assert "中心有限差分" in guide
    start = app.index("function calculateMultiForwardPass(")
    end = app.index("\nfunction calculateBatchGradientUpdate", start)
    script = f"""
const vm=require('vm');
const nodes={{multiInputX1:{{value:'2'}},multiInputW1:{{value:'0.5'}},multiInputX2:{{value:'1'}},multiInputW2:{{value:'-0.4'}},multiInputBias:{{value:'0.2'}},updateTarget:{{value:'1'}},gradientCheckEpsilon:{{value:'0.001'}},gradientCheckResult:{{textContent:''}}}};
const byId=id=>nodes[id];
vm.runInThisContext({json.dumps(app[start:end])});
const initial=calculateFiniteDifferenceGradientCheck(2,0.5,1,-0.4,0.2,1,0.001);
const changed=calculateFiniteDifferenceGradientCheck(2,0.5,1,-0.4,0.2,0,0.001);
if (!initial || initial.maxAbsoluteError>1e-10 || initial.analytic.some((x,i)=>Math.abs(x-initial.numeric[i])>1e-10)) process.exit(1);
if (!changed || Math.abs(changed.analytic[0]-3.2)>1e-12 || Math.abs(changed.numeric[0]-3.2)>1e-10) process.exit(2);
if (calculateFiniteDifferenceGradientCheck(2,.5,1,-.4,.2,1,0)!==null || calculateFiniteDifferenceGradientCheck('',.5,1,-.4,.2,1,.001)!==null) process.exit(3);
renderFiniteDifferenceGradientCheck();
if (!nodes.gradientCheckResult.textContent.includes('w₁ 解析=-0.800000、數值≈-0.800000') || !nodes.gradientCheckResult.textContent.includes('最大絕對差=')) process.exit(4);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def synthetic_series(n: int = 1200) -> Series:
    dates = [(date(2010, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    t = np.arange(n)
    closes = 1000 * np.exp(0.0002 * t + 0.015 * np.sin(t / 17) + 0.003 * np.sin(t / 3.7))
    return Series(dates, closes, {"source": "test fixture"}, "fixture")


def test_local_data_is_consistent_and_close_only():
    series = load_series()
    assert len(series.dates) >= 3889
    assert series.dates[0] == "2010-01-04"
    assert series.dates[-1] >= "2025-12-31"
    assert series.closes.min() > 0
    assert set(FEATURES) == {"return_1", "return_5", "return_20", "volatility_5", "volatility_20"}


def test_targets_use_future_close_but_features_stop_at_origin():
    original = synthetic_series()
    altered_closes = original.closes.copy()
    altered_closes[700:] *= 1.15
    altered = Series(original.dates, altered_closes, original.source, "altered")
    options = ["return_1", "volatility_5"]
    a = build_samples(original, options, lookback=10, horizon=5, use_log_return=False)
    b = build_samples(altered, options, lookback=10, horizon=5, use_log_return=False)
    index = int(np.flatnonzero(a["origins"] == 695)[0])
    np.testing.assert_allclose(a["x"][index], b["x"][index])
    assert a["y"][index] != b["y"][index]


def test_feature_warmup_and_lookback_align_without_invalid_origins():
    samples = build_samples(synthetic_series(), ["volatility_20"], lookback=20, horizon=1, use_log_return=False)
    assert samples["origins"][0] == 39
    assert np.isfinite(samples["x"]).all()


@pytest.mark.parametrize(
    ("feature", "lookback", "first_origin"),
    [("return_1", 20, 20), ("volatility_5", 10, 14), ("return_20", 10, 29)],
)
def test_single_feature_uses_its_actual_warmup_row(feature: str, lookback: int, first_origin: int):
    samples = build_samples(synthetic_series(), [feature], lookback=lookback, horizon=1, use_log_return=False)
    assert samples["origins"][0] == first_origin
    assert np.isfinite(samples["x"]).all()


@pytest.mark.parametrize("kind", ["mlp", "rnn", "lstm", "gru", "tcn"])
def test_all_networks_accept_same_sequence_and_backpropagate(kind: str):
    config = TrainingConfig(epochs=1, hidden_units=8, hidden_layers=2, dropout=0.1)
    network = _model(kind, n_features=3, lookback=12, config=config)
    x = torch.randn(4, 12, 3)
    output = network(x)
    assert output.shape == (4,)
    loss = output.square().mean()
    loss.backward()
    assert all(parameter.grad is not None for parameter in network.parameters() if parameter.requires_grad)


def test_tcn_cannot_use_future_suffix_for_earlier_output():
    config = TrainingConfig(epochs=1, hidden_units=8, hidden_layers=2, dropout=0.0)
    network = _model("tcn", n_features=2, lookback=12, config=config).eval()
    original = torch.randn(1, 12, 2)
    changed_future = original.clone()
    changed_future[:, 8:, :] += 1000
    with torch.no_grad():
        before = network.prefix_representation(original, 6)
        after = network.prefix_representation(changed_future, 6)
    torch.testing.assert_close(before, after)


def test_tcn_completes_walk_forward_validation_path():
    series = synthetic_series(1200)
    samples = build_samples(series, ["return_1"], lookback=10, horizon=1, use_log_return=False)
    result = run_validation(
        samples, ["tcn"], TrainingConfig(epochs=1, batch_size=256, dropout=0.0, seed=11),
        __import__("threading").Event(), lambda *_: None,
    )
    assert [item["key"] for item in result["comparisons"]] == ["historical_mean", "naive", "ridge", "forest", "tcn"]
    model = result["models"][0]
    assert model["key"] == "tcn" and len(model["folds"]) >= 2
    assert all(np.isfinite(row["predicted"]) and np.isfinite(row["actual"]) for fold in model["folds"] for row in fold["predictions"])


@pytest.mark.parametrize("horizon", [1, 5, 20])
def test_targets_align_with_next_close_execution(horizon: int):
    series = synthetic_series(1200)
    samples = build_samples(series, ["return_1"], lookback=10, horizon=horizon, use_log_return=False)
    origin = int(samples["origins"][0])
    entry = int(samples["entry_indices"][0])
    target = int(samples["targets"][0])
    assert entry == origin + 1
    assert target == entry + horizon
    assert samples["execution"] == "next_close"
    assert samples["y"][0] == pytest.approx(series.closes[target] / series.closes[entry] - 1)
    assert target < len(series.closes)


def test_walk_forward_targets_stay_within_validation_partition():
    samples = build_samples(synthetic_series(), ["return_1"], lookback=10, horizon=20, use_log_return=False)
    split = samples["split_index"]
    folds = walk_forward_folds(samples)
    for train_idx, val_idx in folds:
        assert samples["targets"][train_idx].max() < samples["origins"][val_idx].min()
        assert samples["targets"][val_idx].max() < split


def test_next_close_target_ignores_signal_close_move():
    series = synthetic_series(100)
    options = ["return_1"]
    original = build_samples(series, options, lookback=10, horizon=5, use_log_return=False)
    first_origin = int(original["origins"][0])
    changed = series.closes.copy()
    changed[first_origin] *= 4
    altered = Series(series.dates, changed, series.source, "changed-origin")
    revised = build_samples(altered, options, lookback=10, horizon=5, use_log_return=False)
    np.testing.assert_allclose(original["y"][0], revised["y"][0])


def test_fixed_rule_and_oof_replay_use_delayed_close_execution_and_full_path():
    # OOF buy signal after close[0], then remain exposed across the missing
    # forecast gap; sell signal after close[3], exit at close[4], including
    # the 133.1 -> 120 execution-day mark-to-market move.
    series = [{"close": value} for value in [100, 110, 121, 133.1, 120, 150]]
    intervals = [
        {"originIndex": 0, "entryIndex": 1, "targetIndex": 2, "signal": "buy_candidate"},
        {"originIndex": 3, "entryIndex": 4, "targetIndex": 5, "signal": "sell_candidate"},
    ]
    # Run the exact JS pure calculation implementation in an isolated Node VM.
    script = """
      const fs = require('fs'), vm = require('vm');
      const source = fs.readFileSync('web/app.js','utf8');
      const start = source.indexOf('function replayFixedSignals(');
      const end = source.indexOf('async function api(', start);
      const helpers = source.slice(start, end);
      vm.runInThisContext(helpers);
      const series = JSON.parse(process.env.SERIES);
      const intervals = JSON.parse(process.env.INTERVALS);
      const replay = replayOofSignals(series, intervals, 1, 5, 0.001425, 0.004425);
      const baseline = replayFixedSignals(series, new Map(), 1, 5, 0.001425, 0.004425);
      process.stdout.write(JSON.stringify({replay, baseline}));
    """
    import os, subprocess
    env = {**os.environ, "SERIES": json.dumps(series), "INTERVALS": json.dumps(intervals)}
    completed = subprocess.run(["node", "-e", script], env=env, capture_output=True, text=True, check=True)
    payload = json.loads(completed.stdout)
    result = payload["replay"]
    expected = (1 - 0.001425) * (120 / 110) * (1 - 0.004425)
    assert result["equity"] == pytest.approx(expected)
    assert result["completed"] == 1
    assert result["holdingDays"] == 3
    assert payload["baseline"]["equity"] == pytest.approx(1)


def test_strategy_window_excludes_locked_dates():
    script = """
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function replayFixedSignals('),end=source.indexOf('async function api(',start);
      vm.runInThisContext(source.slice(start,end));
      const series=[{date:'d0'},{date:'d1'},{date:'d2'},{date:'d3'},{date:'d4'},{date:'d5'}];
      const byDate=new Map(series.map((p,i)=>[p.date,i]));
      const rows=[{originIndex:0,targetIndex:2},{originIndex:2,targetIndex:4},{originIndex:4,targetIndex:5}];
      process.stdout.write(JSON.stringify(replayWindow(rows,byDate,'d1','d4',series.length)));
    """
    import subprocess
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(completed.stdout) == [
        {"originIndex": 0, "targetIndex": 2},
        {"originIndex": 2, "targetIndex": 4},
    ]


def test_walk_forward_target_dates_do_not_cross_fold_boundary():
    sample_data = build_samples(synthetic_series(), ["return_1"], lookback=10, horizon=20, use_log_return=False)
    folds = walk_forward_folds(sample_data)
    targets = sample_data["targets"]
    assert len(folds) >= 2
    for train_idx, val_idx in folds:
        assert targets[train_idx].max() < targets[val_idx].min()
        assert targets[val_idx].max() < sample_data["split_index"]


def test_numpy_trace_matches_torch_autograd():
    trace = numpy_mlp_trace()
    assert trace["gradientMaxAbsError"] < 1e-12
    assert abs(trace["prediction"] - trace["pytorchPrediction"]) < 1e-12


def test_neutral_forecast_direction_accuracy_gets_half_credit():
    metrics = _metrics(np.array([0.01, -0.02, 0.03, -0.01]), np.zeros(4))
    assert metrics["directionAccuracy"] == 0.5


def test_saved_validation_is_restored_by_digest_after_registry_reset(tmp_path, monkeypatch):
    series = synthetic_series()
    config = {"symbol": "TAIEX", "modelTypes": ["mlp"], "epochs": 1}
    result = {"validationSamples": 3, "models": [{"key": "mlp", "folds": []}]}
    monkeypatch.setattr(main_module, "ROOT", tmp_path)
    monkeypatch.setattr(main_module, "load_series", lambda symbol: series if symbol == "TAIEX" else None)
    monkeypatch.setattr(main_module, "validation_registry", {})
    (tmp_path / "data").mkdir()

    main_module._store_latest_validation(series.digest, config, result)

    expected_path = tmp_path / "data" / f"latest-validation-{series.digest[:16]}.json"
    assert expected_path.is_file()
    assert not (tmp_path / "data" / "latest-validation-sequence-v1.json").exists()

    # A new empty registry models a server restart; the API must restore from disk.
    response = TestClient(app).get("/api/validation/latest?symbol=TAIEX")

    assert response.status_code == 200
    assert response.json() == {"datasetHash": series.digest, "config": config, "result": result}


def test_legacy_default_validation_is_restored_only_for_matching_digest(tmp_path, monkeypatch):
    series = synthetic_series()
    config = {"symbol": "TAIEX", "modelTypes": ["mlp"], "epochs": 1}
    result = {"validationSamples": 3, "models": [{"key": "mlp", "folds": []}]}
    monkeypatch.setattr(main_module, "ROOT", tmp_path)
    monkeypatch.setattr(main_module, "load_series", lambda symbol: series if symbol == "TAIEX" else None)
    monkeypatch.setattr(main_module, "validation_registry", {})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    legacy = data_dir / "latest-validation-sequence-v1.json"
    legacy.write_text(json.dumps({"datasetHash": series.digest, "config": config, "result": result}), encoding="utf-8")

    response = TestClient(app).get("/api/validation/latest?symbol=TAIEX")
    assert response.status_code == 200
    assert response.json()["result"] == result

    legacy.write_text(json.dumps({"datasetHash": "stale-hash", "config": config, "result": result}), encoding="utf-8")
    response = TestClient(app).get("/api/validation/latest?symbol=TAIEX")
    assert response.status_code == 200
    assert response.json() is None


def test_public_api_and_async_validation_job(monkeypatch):
    # Keep the API smoke independent of persisted lock and validation state.
    monkeypatch.setattr(main_module, "_final_state_for_dataset", lambda digest, symbol: {"status": "available"})
    monkeypatch.setattr(main_module, "_store_latest_validation", lambda *args, **kwargs: None)
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200 and health.json()["service"] == "taiex-neural-lab"
    status = client.get("/api/data/status").json()
    assert status["fields"] == ["date", "close"]
    assert status["rows"] == len(load_series().dates)
    assert "finalTest" not in status
    lock_status = client.get("/api/data/lock-status").json()
    assert set(lock_status) <= {"status", "datasetHashMismatch"}
    assert lock_status.get("status") in {"available", "running", "spent"}
    trace = client.get("/api/learning/trace").json()
    assert trace["gradientMaxAbsError"] < 1e-12
    response = client.post("/api/experiments", json={
        "modelTypes": ["mlp", "rnn", "lstm", "gru"], "features": ["return_1"], "lookback": 5, "horizon": 1,
        "epochs": 1, "batchSize": 256, "hiddenUnits": 8, "hiddenLayers": 1,
        "dropout": 0, "seed": 7,
    })
    assert response.status_code == 200, response.text
    job_id = response.json()["jobId"]
    deadline = time.time() + 30
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in {"queued", "running"}:
            break
        time.sleep(0.1)
    assert job["status"] == "completed", job
    assert [model["key"] for model in job["result"]["models"]] == ["mlp", "rnn", "lstm", "gru"]
    assert [row["key"] for row in job["result"]["comparisons"]] == ["historical_mean", "naive", "ridge", "forest", "mlp", "rnn", "lstm", "gru"]
    for model in job["result"]["models"]:
        assert len(model["folds"]) >= 2
        assert model["zeroBaseline"]["mae"] > 0


def test_final_evaluation_rejects_multiple_models():
    client = TestClient(app)
    response = client.post("/api/final-evaluation", json={
        "modelTypes": ["mlp", "gru"], "features": ["return_1"], "lookback": 5, "horizon": 1,
    })
    assert response.status_code == 422
    response = client.post("/api/final-evaluation", json={
        "modelTypes": ["mlp"], "features": ["return_1"], "lookback": 5, "horizon": 1,
    })
    assert response.status_code == 409


def test_final_evaluation_refuses_tcn_before_any_final_state_change(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(main_module, "load_series", lambda symbol="TAIEX": pytest.fail("must reject before loading data"))
    monkeypatch.setattr(main_module, "_final_state_for_dataset", lambda digest, symbol: pytest.fail("must not inspect final state"))
    monkeypatch.setattr(main_module, "write_final_state", lambda state: pytest.fail("must not write final state"))
    monkeypatch.setattr(main_module, "_start_job", lambda payload, final=False: pytest.fail("final job must not start"))
    response = client.post("/api/final-evaluation", json={
        "modelTypes": ["tcn"], "features": ["return_1"], "lookback": 5, "horizon": 1, "epochs": 20,
    })
    assert response.status_code == 422
    assert "TCN" in response.json()["detail"]


def test_series_full_mode_returns_complete_local_path(monkeypatch):
    series = synthetic_series(12)
    monkeypatch.setattr(main_module, "load_series", lambda symbol="TAIEX": series)
    full = TestClient(app).get("/api/data/series?full=true")
    chart = TestClient(app).get("/api/data/series")
    assert full.status_code == chart.status_code == 200
    assert len(full.json()["points"]) == 12
    assert full.json()["full"] is True
    assert len(chart.json()["points"]) == 12


def test_series_full_mode_can_clip_to_training_validation_end(monkeypatch):
    series = synthetic_series(12)
    monkeypatch.setattr(main_module, "load_series", lambda symbol="TAIEX": series)
    response = TestClient(app).get("/api/data/series?full=true&end=2010-01-07")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rangeEnd"] == "2010-01-07"
    assert all(point["date"] <= "2010-01-07" for point in payload["points"])
    assert len(payload["points"]) == 7


def test_prediction_interval_lesson_calculation_and_input_bounds():
    script = """
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function calculatePredictionInterval(');
      const end=source.indexOf('function renderPredictionIntervalExample(',start);
      vm.runInThisContext(source.slice(start,end));
      process.stdout.write(JSON.stringify({
        standard:calculatePredictionInterval(0.6,0.4),
        changed:calculatePredictionInterval(0.6,0.7),
        blank:calculatePredictionInterval('',0.4),
        negative:calculatePredictionInterval(0.6,-0.1),
        overflow:calculatePredictionInterval(1e308,1e308)
      }));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    assert result["standard"] == {"lower": 0.2, "upper": 1}
    assert result["changed"] == {"lower": -0.1, "upper": 1.3}
    assert result["blank"] is None
    assert result["negative"] is None
    assert result["overflow"] is None


def test_prediction_interval_visualization_tracks_bounds_and_invalid_inputs():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    assert 'id="intervalViz" class="interval-viz" role="img"' in html
    assert "三個標記分別表示下界、中心預測與上界" in guide
    script = r"""
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function calculatePredictionInterval(');
      const end=source.indexOf('function calculateGradientStep(',start);
      const code=source.slice(start,end);
      const nodes={
        predictionIntervalResult:{textContent:''},intervalViz:{hidden:false,attrs:{},style:{values:{},setProperty(k,v){this.values[k]=v}},setAttribute(k,v){this.attrs[k]=v}},
        intervalCenter:{value:'0.6'},intervalSpread:{value:'0.4'},intervalLowerLabel:{textContent:''},intervalCenterLabel:{textContent:''},intervalUpperLabel:{textContent:''}
      };
      const context={byId:id=>nodes[id]}; vm.createContext(context); vm.runInContext(code,context);
      context.renderPredictionIntervalExample();
      const standard={message:nodes.predictionIntervalResult.textContent,aria:nodes.intervalViz.attrs['aria-label'],labels:[nodes.intervalLowerLabel.textContent,nodes.intervalCenterLabel.textContent,nodes.intervalUpperLabel.textContent],hidden:nodes.intervalViz.hidden,left:nodes.intervalViz.style.values['--interval-left'],right:nodes.intervalViz.style.values['--interval-right']};
      nodes.intervalCenter.value='-0.2';nodes.intervalSpread.value='0.7';context.renderPredictionIntervalExample();
      const down={aria:nodes.intervalViz.attrs['aria-label'],labels:[nodes.intervalLowerLabel.textContent,nodes.intervalCenterLabel.textContent,nodes.intervalUpperLabel.textContent]};
      nodes.intervalCenter.value='0.6';nodes.intervalSpread.value='0.7';context.renderPredictionIntervalExample();
      const wide={aria:nodes.intervalViz.attrs['aria-label'],labels:[nodes.intervalLowerLabel.textContent,nodes.intervalUpperLabel.textContent]};
      nodes.intervalSpread.value='-1';context.renderPredictionIntervalExample();
      const invalid={message:nodes.predictionIntervalResult.textContent,hidden:nodes.intervalViz.hidden};
      process.stdout.write(JSON.stringify({standard,down,wide,invalid}));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    assert result["standard"]["labels"] == ["下界 +0.20%", "中心 +0.60%", "上界 +1.00%"]
    assert "下界 +0.20" in result["standard"]["aria"] and "上界 +1.00" in result["standard"]["aria"]
    assert not result["standard"]["hidden"] and result["standard"]["left"] == "58.4%" and result["standard"]["right"] == "92%"
    assert result["down"]["labels"] == ["下界 -0.90%", "中心 -0.20%", "上界 +0.50%"]
    assert result["wide"]["labels"] == ["下界 -0.10%", "上界 +1.30%"]
    assert "下界 -0.90" in result["down"]["aria"]
    assert result["invalid"]["hidden"] and "非負誤差尺度" in result["invalid"]["message"]


def test_prediction_interval_lesson_explains_scale_and_total_width():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    assert "寬 0.8 個百分點" in app and "寬 1.4 個百分點" in app
    assert "中心不變、尺度增加，範圍變寬" in app
    assert "總寬 ${width.toFixed(2)} 個百分點" in app
    assert "總寬 0.8 個百分點" in guide and "總寬 1.4 個百分點" in guide
    assert "不代表機率密度、模型預測區間或覆蓋率保證" in guide


def test_monitor_selects_guided_tab_before_lesson_navigation_and_fixtures():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert '== str(page.evaluate("LESSONS.length"))' in monitor
    assert 'page.locator("#tabGuided").click()' in monitor
    assert "page.wait_for_function(\"document.querySelector('#tabGuided')?.getAttribute('aria-selected') === 'true' && document.querySelector('#learningGuided')?.hidden === false\")" in monitor
    assert "activeLearningTabId = 'tabGuided'; document.querySelector('#tabGuided').click()" not in monitor
    assert 'page.locator("#tabGuided").click()\n                    page.wait_for_function("document.querySelector(\'#tabGuided\')?.getAttribute(\'aria-selected\') === \'true\' && document.querySelector(\'#learningGuided\')?.hidden === false")\n                    page.locator("#lessonBack").click()' in monitor
    assert monitor.index('page.locator("#tabGuided").click()\n                    page.wait_for_function') > monitor.index('page.locator("#tabLab").click()')
    reset_then_advance = 'page.evaluate("() => { savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = \'tabGuided\'; lessonIndex = 0; activeLearningTabId = \'tabGuided\'; renderLesson(); }")\n                    # Advance exactly seven steps from lesson 1 to lesson 8.'
    assert reset_then_advance in monitor
    assert monitor.index(reset_then_advance) < monitor.index('for _ in range(7): page.locator("#lessonNext").click()')
    for marker in ("relu_interaction_ok =", "multi_forward_pass_ok =", "gradient_update_ui_ok =", "batch_gradient_ui_ok =", "interval_ui_ok =", "activation_ui_ok ="):
        block = monitor[monitor.index(marker):monitor.index("\n", monitor.index(marker))]
        assert "lessonIndex=" in block and "renderLesson();" in block
    gradient_fixture = monitor[monitor.index("gradient_update_ui_ok ="):monitor.index("\n", monitor.index("gradient_update_ui_ok ="))]
    assert gradient_fixture.index("multiInputX1').value='2'") < gradient_fixture.index("lessonIndex=17; renderLesson()")
    assert "損失下降" in gradient_fixture and "損失上升" in gradient_fixture
    interval_predicate = monitor[monitor.index("interval_ui_ok ="):monitor.index("\n", monitor.index("interval_ui_ok ="))]
    assert "initial.includes('0.20% 至 1.00%')" in interval_predicate
    assert "changed.includes('-0.10% 至 1.30%')" in interval_predicate
    assert "+0.20% 至 +1.00%" not in interval_predicate


def test_guided_learning_explains_saved_progress_and_restart():
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / "web/index.html").read_text()
    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert 'id="learningProgressHelp"' in html
    assert "導學進度會保存在這個瀏覽器" in html
    assert "「上一步」可複習" in html
    assert "最後一步的「重新開始」" in html
    assert "byId('lessonNext').textContent = lessonIndex === LESSONS.length - 1 ? '重新開始' : '下一步'" in app
    assert "const compatibleA=savedValidationSummary(" in monitor
    assert "const compatibleB=savedValidationSummary(" in monitor
    assert "savedComparisonCompatibility([compatibleA,compatibleB])" in monitor
    assert "const sharedSetup={features:['return_1','return_5'],lookback:5" in monitor


def test_guided_resume_notice_uses_saved_progress_and_monitor_reset_updates_snapshot():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "const hasSavedProgress = savedLearningProgress.lessonIndex > 0" in app
    assert "resumeNotice.hidden = lessonIndex === 0 || !hasSavedProgress" in app
    assert monitor.count("savedLearningProgress.lessonIndex = 0; lessonIndex = 0") == 1
    assert monitor.count("savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'") == 2
    assert monitor.count("saveLearningProgress = () => {}; savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'; lessonIndex = 0; activeLearningTabId = 'tabGuided'; renderLesson();") == 1
    assert "reset_notice_hidden = page.locator(\"#learningResumeNotice\").evaluate(\"element => element.hidden\")" in monitor
    assert '"已恢復上次進度" in lesson_resume_notice' in monitor
    assert "reset_notice_hidden or \"已恢復上次進度\" in lesson_resume_notice" not in monitor
    assert "learning_ok = learning_ok and lesson_ok and reset_notice_hidden and quiz_ok" in monitor


def test_guided_navigation_monitor_renders_controlled_start_before_next_back():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    reset = "saveLearningProgress = () => {}; savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'; lessonIndex = 0; activeLearningTabId = 'tabGuided'; renderLesson();"
    assert reset in monitor
    assert monitor.index(reset) < monitor.index('page.locator("#lessonNext").click()', monitor.index(reset))
    assert "起始={lesson_start.group(1) if lesson_start else 'unknown'}" in monitor
    assert "前進={lesson_next.group(1) if lesson_next else 'unknown'}" in monitor
    assert "返回={lesson_return.group(1) if lesson_return else 'unknown'}" in monitor
    assert "guided_visible_after_back = page.locator(\"#learningGuided\").evaluate(\"element => !element.hidden\")" in monitor


def test_later_guided_fixture_resets_saved_resume_snapshot_and_tab():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    reset = "savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'; lessonIndex = 0; activeLearningTabId = 'tabGuided'; renderLesson();"
    assert reset in monitor


def test_momentum_lesson_explains_velocity_after_gradient_reverses():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    lesson = app[app.index("{ kicker:'20 · 動量最佳化'"):app.index("{ kicker:'21 · 啟用函數比較'")]
    assert "第二步梯度改成 −2" in lesson
    assert "0.9×1.45−2=−0.695" in lesson
    assert "權重因此上升 0.0695" in lesson


def test_cross_asset_direction_and_magnitude_reading_order_is_visible():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    assert 'class="cross-asset-reading-tip"' in html
    for term in ("方向比例", "上漲", "下跌", "平均絕對幅度", "方向錯置"):
        assert term in html and term in guide


def test_direction_summary_reports_mae_by_actual_direction_and_keeps_misses():
    root = Path(__file__).resolve().parents[1]
    source = (root / "web/app.js").read_text(encoding="utf-8")
    start = source.index("function directionMixSummary(")
    end = source.index("function savedValidationSummary(", start)
    helper = source[start:end]
    script = f"""
      {helper}
      const summary = directionMixSummary([
        {{actual:.01,predicted:.02}}, {{actual:-.01,predicted:0}},
        {{actual:.03,predicted:.01}}, {{actual:.02,predicted:-.01}},
        {{actual:-.02,predicted:-.01}}, {{actual:null,predicted:.5}}
      ]);
      process.stdout.write(summary);
    """
    result = subprocess.run(["node", "-e", script], cwd=root, capture_output=True, text=True, check=True)
    assert "上漲 n=3、2.000 個百分點" in result.stdout
    assert "下跌 n=2、1.000 個百分點" in result.stdout
    assert "方向錯置 1 筆" in result.stdout
    assert "null" not in result.stdout
def test_mult_input_neuron_lesson_contract():
    """The final lesson exposes and calculates the two-input ReLU example."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "多輸入神經元" in app and "z=w₁x₁+w₂x₂+b" in app
    assert "multiForwardPassExercise" in html and "第 1 / 26 步" in html
    assert "第十七步" in guide and "z=w₁x₁+w₂x₂+b" in guide
    assert "LESSONS.length === 26" in monitor
    assert "!trace && currentModel() === 'mlp' && !isInput && !isOutput" in app
    assert "矩陣維度例子" in app and "W∈ℝ²ˣ³" in app
    assert "shape_note_ok" in monitor and "MLP 矩陣維度教學" in monitor
    assert "a∈ℝ³" in app and "W∈ℝ²ˣ³" in app and "Wa∈ℝ²" in app
    assert 'lessonIndex=7; renderLesson();' in monitor
    assert "tensorShapeLesson" in html and "renderTensorShapeExercise" in app
    assert "W 的形狀為 <strong>${neurons}×${inputs}</strong>" in app
    assert 'name="tensorShapeAnswer" value="neurons-first"' in html
    assert "checkTensorShape" in app and "每一列：一列代表一個神經元" in app
    assert "LESSONS.length === 26" in monitor and "multi_forward_pass_ok" in monitor
    assert "replay_pause_ok" in monitor and "page.locator(\"#playNetwork\").click()" in monitor
    assert "calculateGradientUpdate" in app and "gradientUpdateExercise" in html
    assert "(${result.before.gradients.w1.toFixed(4)})=${result.updated.w1.toFixed(4)}" in app
    assert "(${result.before.gradients.w2.toFixed(4)})=${result.updated.w2.toFixed(4)}" in app
    assert "(${result.before.gradients.bias.toFixed(4)})=${result.updated.bias.toFixed(4)}" in app
    assert "θ新=θ−η×梯度：w₁ ${values[1]}−${byId('updateRate').value}×(${result.before.gradients.w1.toFixed(4)})=${result.updated.w1.toFixed(4)}" in app
    assert "LESSONS.length === 26" in monitor and "gradient_update_ui_ok" in monitor
    assert "initial.includes('維持同四筆梯度，只改成 (1,3) 與 (2,4) 分批，權重路徑變為 2.0500 → 1.8000')" in monitor
    assert "initial.includes('梯度：∂L/∂w₁=-0.8000')" in monitor
    assert "多筆樣本先平均梯度" in app and "(−2+4+1+1)/4=1" in app
    assert "小批次如何更新權重" in guide
    assert "batchGradientExercise" in html and "calculateBatchGradientUpdate" in app
    assert "const batch = calculateBatchGradientUpdate(2,[-2,4,1,1],0.1)" in monitor
    assert "batch.average===1" in monitor and "Math.abs(batch.updated-1.9)<1e-12" in monitor
    assert "batchGradientFour" in html and "÷ ${gradients.length} = ${result.average.toFixed(4)}" in app
    assert "positiveCount" in app and "正負梯度互相抵銷一部分" in app and "樣本範圍 ${result.minGradient.toFixed(4)} 至 ${result.maxGradient.toFixed(4)}" in app
    assert "batch.positiveCount===3" in monitor
    assert "batch.negativeCount===1" in monitor
    assert "batch.zeroCount===0" in monitor
    assert "batch.total===4" in monitor
    assert "Math.abs(batch.summedUpdate-1.6)<1e-12" in monitor
    assert "第 19 / 26 步" in monitor
    assert "LESSONS[18].body.includes('(−2+4+1+1)/4=1')" in monitor
    assert "calculateBatchGradientUpdate(2,[-2,4,'',1],0.1)===null" in monitor
    assert "renderBatchGradientExercise();" in monitor
    assert "batch.influentialSample" in monitor
    assert "動量累積近期梯度方向" in app and "vₜ=βvₜ₋₁+gₜ" in app
    assert "momentumExercise" in html and "calculateMomentumUpdate" in app
    assert "calculateMomentumUpdate" in monitor and "momentumExercise" in monitor
    assert "momentumNextGradient" in html and "calculateMomentumSteps" in app
    assert "calculateMomentumSteps" in monitor and "momentumNextGradient" in monitor


def test_batch_gradient_lesson_exposes_direction_disagreement():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    start = app.index("function calculateBatchGradientUpdate(")
    end = app.index("function calculateMomentumUpdate(", start)
    renderer = app[start:end]
    script = renderer + """
const nodes={batchGradientResult:{textContent:''},batchWeight:{value:'2'},batchGradientOne:{value:'-2'},batchGradientTwo:{value:'4'},batchGradientThree:{value:'1'},batchGradientFour:{value:'1'},batchRate:{value:'0.1'}};
const byId=id=>nodes[id];
renderBatchGradientExercise();
const text=nodes.batchGradientResult.textContent;
nodes.batchGradientOne.value='-1'; nodes.batchGradientTwo.value='1'; nodes.batchGradientThree.value='0'; nodes.batchGradientFour.value='0'; renderBatchGradientExercise();
const zeroToNonzeroText=nodes.batchGradientResult.textContent;
nodes.batchGradientTwo.value='4'; renderBatchGradientExercise();
const reverseText=nodes.batchGradientResult.textContent;
process.stdout.write(JSON.stringify({result:calculateBatchGradientUpdate(2,[-2,4,1,1],0.1),doubled:calculateBatchGradientUpdate(2,[-2,4,1,1,-2,4,1,1],0.1),canceled:calculateBatchGradientUpdate(2,[-1,1,0,0],0.1),flipped:calculateBatchGradientUpdate(2,[-1,4,0,0],0.1),zero:calculateBatchGradientUpdate(2,[0,0,0,0],0.1),aligned:calculateBatchGradientUpdate(2,[1,1,1,1],0.1),text,zeroToNonzeroText,reverseText}));
"""
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert result["result"] == {"average": 1, "total": 4, "totalAbsolute": 8, "netToAbsoluteRatio": 0.5, "updated": 1.9, "summedUpdate": 1.6, "positiveCount": 3, "negativeCount": 1, "zeroCount": 0, "minGradient": -2, "maxGradient": 4, "variance": 4.5, "standardDeviation": 4.5 ** 0.5, "maxLeaveOneOutShift": 1, "influentialSample": 1, "influentialGradient": -2, "leaveOneOutMean": 2, "leaveOneOutDelta": 1, "influentialSampleChangesDirection": False}
    assert result["doubled"]["average"] == 1 and result["doubled"]["total"] == 8
    assert result["doubled"]["updated"] == 1.9 and result["doubled"]["summedUpdate"] == 1.2
    assert result["canceled"]["netToAbsoluteRatio"] == 0
    assert result["zero"]["netToAbsoluteRatio"] is None
    assert result["aligned"]["netToAbsoluteRatio"] == 1
    assert result["aligned"]["maxLeaveOneOutShift"] == 0
    assert result["canceled"]["maxLeaveOneOutShift"] == pytest.approx(1 / 3)
    assert result["canceled"]["influentialSample"] == 1
    assert result["canceled"]["leaveOneOutMean"] == pytest.approx(1 / 3)
    assert result["canceled"]["leaveOneOutDelta"] == pytest.approx(1 / 3)
    assert result["canceled"]["influentialSampleChangesDirection"] is True
    assert result["flipped"]["average"] == pytest.approx(0.75)
    assert result["flipped"]["leaveOneOutMean"] == pytest.approx(-1 / 3)
    assert result["flipped"]["influentialSampleChangesDirection"] is True
    assert "3 筆為正、1 筆為負、0 筆為零" in result["text"]
    assert "正負梯度互相抵銷一部分" in result["text"]
    assert "樣本範圍 -2.0000 至 4.0000" in result["text"]
    assert "母體變異數 4.5000、標準差 2.1213" in result["text"]
    assert "淨梯度占總絕對梯度比例 = 0.5000" in result["text"]
    assert "數值越低，正負梯度抵銷越多" in result["text"]
    assert "梯度有分散：標準差表示單筆梯度典型地偏離平均多少。" in result["text"]
    assert "若逐一拿掉一筆，平均梯度最多改變 1.0000；第 1 筆（梯度 -2）影響最大，拿掉後平均變成 2.0000（改變 +1.0000）" in result["text"]
    assert "這是目前批次的敏感度，不是模型品質指標。" in result["text"]
    assert "更新方向維持不變" in result["text"]
    assert "完整 batch 平均一次更新到 1.9000" in result["text"]
    assert "mini-batch、每批各更新一次，權重依序 1.9000 → 1.8000" in result["text"]
    assert "只改成 (1,3) 與 (2,4) 分批，權重路徑變為 2.0500 → 1.8000" in result["text"]
    assert "兩種 mini-batch 分組的終點同為 1.8000" in result["text"]
    assert "單次 full-batch 只更新一次，因此終點是 1.9000" in result["text"]
    assert "刻意固定梯度以隔離更新次數的影響" in result["text"]
    assert "真實訓練每次更新後會重新計算梯度" in result["text"]
    assert "零更新變成非零更新" in result["zeroToNonzeroText"]
    assert "梯度符號改變" in result["reverseText"]
    assert "= 1.9000" in result["text"]
    assert "四筆梯度全為 +1 時平均也是 1，新權重 1.9000" in result["text"]
    assert "平均更新相同，但樣本方向較一致" in result["text"]
    assert "總梯度 4.0000 會得到 w新=1.6000" in result["text"]
    assert "8 筆平均仍為 1.0000，新權重 1.9000" in result["text"]
    assert "未平均總梯度變成 8.0000，新權重 1.2000" in result["text"]

    aligned = script.replace("[-2,4,1,1]", "[1,1,1,1]")
    aligned = aligned.replace("batchGradientOne:{value:'-2'}", "batchGradientOne:{value:'1'}")
    aligned = aligned.replace("batchGradientTwo:{value:'4'}", "batchGradientTwo:{value:'1'}")
    aligned = aligned.replace("batchGradientThree:{value:'1'}", "batchGradientThree:{value:'1'}")
    aligned = aligned.replace("batchGradientFour:{value:'1'}", "batchGradientFour:{value:'1'}")
    aligned_result = json.loads(subprocess.check_output(["node", "-e", aligned], text=True))
    assert "梯度完全一致：每筆都等於平均值。" in aligned_result["text"]

    balanced = script.replace("[-2,4,1,1]", "[-1,1,0,0]")
    balanced = balanced.replace("batchGradientOne:{value:'-2'}", "batchGradientOne:{value:'-1'}")
    balanced = balanced.replace("batchGradientTwo:{value:'4'}", "batchGradientTwo:{value:'1'}")
    balanced = balanced.replace("batchGradientThree:{value:'1'}", "batchGradientThree:{value:'0'}")
    balanced = balanced.replace("batchGradientFour:{value:'1'}", "batchGradientFour:{value:'0'}")
    balanced_result = json.loads(subprocess.check_output(["node", "-e", balanced], text=True))
    assert balanced_result["result"]["average"] == 0
    assert "梯度有分散：標準差表示單筆梯度典型地偏離平均多少。" in balanced_result["text"]
    assert balanced_result["result"]["updated"] == 2
    assert "平均梯度為 0，正負梯度完全抵銷" in balanced_result["text"]
    assert balanced_result["result"]["variance"] == 0.5


def test_direction_magnitude_exercise_explains_signed_prediction_bias():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    start = app.index("function compareReturnMagnitude(")
    end = app.index("\nfunction renderMagnitudeErrorExercise", start)
    source = app[start:end]
    assert "signedErrorPp: p - a" in source
    assert "方向錯置" in app and "預測 − 實際" in (Path(__file__).resolve().parents[1] / "docs/learning-guide.md").read_text()
    script = f"{source}; process.stdout.write(JSON.stringify([compareReturnMagnitude(0.6,0.2),compareReturnMagnitude(0.1,0.3)]));"
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    values = json.loads(result.stdout)
    assert values[0]["signedErrorPp"] == pytest.approx(0.4)
    assert values[0]["errorPp"] == pytest.approx(0.4)
    assert values[1]["signedErrorPp"] == pytest.approx(-0.2)


def test_magnitude_exercise_groups_mae_by_actual_direction():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    start = app.index("function compareReturnMagnitude(")
    end = app.index("function renderMagnitudeErrorExercise", start)
    source = app[start:end]
    render_start = end
    render_end = app.index("function calculateForwardPass(", render_start)
    renderer = app[render_start:render_end]
    script = f"""
      const nodes={{magnitudePredicted:{{value:'0.6,-0.4,0.1'}},magnitudeActual:{{value:'0.2,-0.2,-0.1'}},magnitudeErrorResult:{{textContent:''}}}};
      const byId=id=>nodes[id]; {source} {renderer}
      renderMagnitudeErrorExercise(); const high=nodes.magnitudeErrorResult.textContent;
      nodes.magnitudePredicted.value='-0.2'; nodes.magnitudeActual.value='-0.2'; renderMagnitudeErrorExercise(); const tie=nodes.magnitudeErrorResult.textContent;
      nodes.magnitudePredicted.value='0'; nodes.magnitudeActual.value='0'; renderMagnitudeErrorExercise(); const empty=nodes.magnitudeErrorResult.textContent;
      nodes.magnitudePredicted.value=''; renderMagnitudeErrorExercise(); const invalid=nodes.magnitudeErrorResult.textContent;
      nodes.magnitudePredicted.value='0.2,0.1'; nodes.magnitudeActual.value='0.1'; renderMagnitudeErrorExercise(); const mismatched=nodes.magnitudeErrorResult.textContent;
      process.stdout.write(JSON.stringify({{high,tie,empty,invalid,mismatched}}));
    """
    result = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert "實際上漲組 n=1：MAE 0.40 pp，零報酬基準 0.20 pp，高於基準；平均絕對幅度預測／實際 0.60／0.20 pp；方向錯置 0 筆" in result["high"]
    assert "實際下跌組 n=2：MAE 0.20 pp，零報酬基準 0.15 pp，高於基準；平均絕對幅度預測／實際 0.25／0.15 pp；方向錯置 1 筆" in result["high"]
    assert "實際上漲組 n=0：沒有可比較樣本" in result["tie"]
    assert "實際下跌組 n=1：MAE 0.00 pp" in result["tie"]
    assert "實際上漲組 n=0：沒有可比較樣本" in result["empty"]
    assert "零報酬列不納入方向分組" in result["empty"]
    assert "數量相同且有限" in result["invalid"] and "數量相同且有限" in result["mismatched"]
    assert "實際上漲組" in app and "同期間基準比較" in (Path(__file__).resolve().parents[1] / "docs/learning-guide.md").read_text()
    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert '"有效 n" in page.locator(".learning-checklist").inner_text()' in monitor


def test_cross_asset_lesson_explains_direction_group_sample_counts():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    assert "各組有效樣本數" in html
    assert "小樣本方向組容易受少數觀測影響" in html
    assert "有效 n" in html
    assert "各自的有效樣本數（有效 n）" in guide


def test_magnitude_exercise_mean_does_not_overflow_finite_extreme_samples():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    start = app.index("function compareReturnMagnitude(")
    end = app.index("function calculateForwardPass(", start)
    source = app[start:end]
    script = f"""
      const nodes={{magnitudePredicted:{{value:'1e308,1e308'}},magnitudeActual:{{value:'1,1'}},magnitudeErrorResult:{{textContent:''}}}};
      const byId=id=>nodes[id]; {source}
      renderMagnitudeErrorExercise(); process.stdout.write(nodes.magnitudeErrorResult.textContent);
    """
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    assert "MAE 1e+308 pp" in result
    assert "零報酬基準 1.00 pp" in result
    assert "Infinity" not in result and "NaN" not in result


def test_gradient_update_compares_linearized_and_recomputed_loss():
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    start = app.index("function calculateMultiForwardPass(")
    end = app.index("function calculateFiniteDifferenceGradientCheck(", start)
    source = app[start:end]
    script = f"""
const nodes={{multiInputX1:{{value:'2'}},multiInputW1:{{value:'0.5'}},multiInputX2:{{value:'1'}},multiInputW2:{{value:'-0.4'}},multiInputBias:{{value:'0.2'}},updateTarget:{{value:'1'}},updateRate:{{value:'0.1'}},gradientUpdateResult:{{textContent:''}}}};
const byId=id=>nodes[id]; {source}
renderGradientUpdateExercise(); const small=nodes.gradientUpdateResult.textContent;
nodes.updateRate.value='1'; renderGradientUpdateExercise(); const large=nodes.gradientUpdateResult.textContent;
    nodes.updateRate.value='not-a-number'; renderGradientUpdateExercise(); const invalid=nodes.gradientUpdateResult.textContent;
process.stdout.write(JSON.stringify({{small,large,invalid}}));
"""
    result = json.loads(subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True).stdout)
    assert "一階損失預測 L+∇L·Δθ=-0.0560" in result["small"]
    assert "負值不可能是實際平方損失" in result["small"]
    assert "更新後重新計算 L=0.0016" in result["small"]
    assert "一階損失預測 L+∇L·Δθ=-0.9200" in result["large"]
    assert "更新後重新計算 L=4.8400" in result["large"]
    assert "計算結果須在數值範圍內" in result["invalid"]
    assert "學習率需介於 0 與 1" in result["invalid"]


def test_relu_zero_input_explains_the_selected_subgradient():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    start = app.index("function calculateReluGradient(")
    end = app.index("function compareReturnMagnitude(", start)
    source = app[start:end]
    script = f"""
      const nodes={{reluInput:{{value:'0'}},reluTarget:{{value:'3'}},reluResult:{{textContent:''}}}};
      const byId=id=>nodes[id]; {source}
      renderReluExercise(); const zero=nodes.reluResult.textContent;
      nodes.reluInput.value='-2'; renderReluExercise(); const inactive=nodes.reluResult.textContent;
      nodes.reluInput.value='2'; renderReluExercise(); const active=nodes.reluResult.textContent;
      process.stdout.write(JSON.stringify({{zero,inactive,active}}));
    """
    result = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert "L=(ŷ−y)² = 9" in result["zero"] and "ReLU′(z) = 0" in result["zero"]
    assert "dL/dz = 2(ŷ−y) × 0 = 0" in result["zero"]
    assert "ReLU′(z) = 0" in result["inactive"] and "dL/dz = 2(ŷ−y) × 0 = 0" in result["inactive"]
    assert "ReLU′(z) = 1" in result["active"] and "dL/dz = 2(ŷ−y) × 1 = -2" in result["active"]
    assert "z=0 不可微" in result["zero"] and "ReLU′(0)=0 的次梯度慣例" in result["zero"]
    assert "次梯度慣例" not in result["inactive"] and "次梯度慣例" not in result["active"]
    assert "零點互動" in (root / "docs/learning-guide.md").read_text()


def test_relu_lesson_compares_sigmoid_saturation_gradients():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    start = app.index("function calculateReluGradient(")
    end = app.index("function compareReturnMagnitude(", start)
    source = app[start:end]
    script = f"""
      const nodes={{reluInput:{{value:'2'}},reluTarget:{{value:'1'}},reluResult:{{textContent:''}}}};
      const byId=id=>nodes[id]; {source}
      renderReluExercise(); const moderate=nodes.reluResult.textContent;
      nodes.reluInput.value='8'; renderReluExercise(); const saturated=nodes.reluResult.textContent;
      process.stdout.write(JSON.stringify({{moderate,saturated}}));
    """
    result = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert "ReLU′(z) = 1" in result["moderate"]
    assert "Sigmoid′(z) = 1.050e-1" in result["moderate"]
    assert "輸入絕對值較大時，Sigmoid′(z) 會變小" in result["saturated"]
    assert "Sigmoid′(z) = 3.352e-4" in result["saturated"]
    assert "dL/dz = -2.248e-7" in result["saturated"]
    assert "比較 ReLU 與 Sigmoid 的局部梯度" in (root / "web/index.html").read_text()


def test_routine_monitor_does_not_start_training_smoke():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    start = monitor.index("def check_splits_and_train(")
    end = monitor.index("\ndef source_snapshot(", start)
    body = monitor[start:end]
    assert '"name": "FastAPI／PyTorch 真實資料訓練", "status": "SKIP"' in body
    assert 'client.post("/api/experiments"' not in body


def test_tensor_shape_learning_widget_acceptance():
    import json
    import os
    import subprocess
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text()
    feedback_start = source.index("function tensorShapeFeedbackForAnswer(")
    feedback_end = source.index("function renderMagnitudeExample()", feedback_start)
    feedback_function = source[feedback_start:feedback_end]
    feedback_script = f"{feedback_function}\nprocess.stdout.write(JSON.stringify(['input-first','neurons-first',null].map(tensorShapeFeedbackForAnswer)));"
    feedback_result = json.loads(subprocess.run(["node", "-e", feedback_script], capture_output=True, text=True,
                                                check=True, env={**os.environ, "NODE_NO_WARNINGS": "1"}).stdout)
    assert feedback_result[0]["correct"] is False and "一列代表一個神經元" in feedback_result[0]["text"]
    assert feedback_result[1]["correct"] is True and "W 是 2×3" in feedback_result[1]["text"]
    assert feedback_result[2]["correct"] is False and "請先選一個答案" in feedback_result[2]["text"]
    start = source.index("function renderTensorShapeExercise()")
    end = source.index("function renderMagnitudeExample()", start)
    function = source[start:end]
    script = f"""
      const values={{tensorInputCount:'3',tensorNeuronCount:'2'}};
      const result={{textContent:'',innerHTML:''}};
      const byId=(id)=>id==='tensorShapeResult'?result:{{value:values[id]}};
      {function}
      renderTensorShapeExercise(); const defaultText=result.innerHTML;
      values.tensorInputCount='5'; values.tensorNeuronCount='4'; renderTensorShapeExercise(); const changed=result.innerHTML;
      values.tensorInputCount='8'; values.tensorNeuronCount='2'; renderTensorShapeExercise(); const capped=result.innerHTML;
      values.tensorInputCount='1.5'; renderTensorShapeExercise(); const invalid=result.textContent;
      process.stdout.write(JSON.stringify({{defaultText,changed,capped,invalid}}));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True,
                               env={**os.environ, "NODE_NO_WARNINGS": "1"})
    result = json.loads(completed.stdout)
    assert "W 的形狀為 <strong>2×3</strong>" in result["defaultText"] and "輸出為 2 維" in result["defaultText"]
    assert "W 的形狀為 <strong>4×5</strong>" in result["changed"] and "輸出為 4 維" in result["changed"]
    assert 'aria-label="權重矩陣 4 列、5 欄"' in result["changed"]
    assert "列：神經元" in result["changed"] and "欄：輸入" in result["changed"]
    assert "最多顯示 6×6 格" in result["capped"] and "實際矩陣仍為 2×8" in result["capped"]
    assert result["invalid"] == "請輸入 1 到 64 的整數維度。"


def test_monitor_activates_mlp_and_learning_lab_for_matrix_checks():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert 'page.locator("#modelType").select_option("mlp")' in monitor
    assert 'page.locator("#math > summary").click()' in monitor
    assert 'page.locator("#tabLab").click()' in monitor
    assert 'page.evaluate("state.forwardTrace = null")' in monitor
    assert monitor.index('page.locator("#modelType").select_option("mlp")') < monitor.index('dimension_lesson_ok =')
    assert monitor.index('page.locator("#tabLab").click()') < monitor.index('tensor_shape_quiz_ok =')


def test_learning_progress_persists_safely_and_monitor_opens_disclosure():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "taiex-learning-progress-v1" in app
    assert "index < LESSONS.length ? index : 0" in app
    assert "validTabs.has(tabId) ? tabId : 'tabGuided'" in app
    assert "saveLearningProgress();" in app
    assert 'details class="guide-panel" id="math"' in html
    assert 'if not page.locator("#math").evaluate("element => element.open"):' in monitor
    disclosure = monitor.index('if not page.locator("#math").evaluate("element => element.open")')
    assert disclosure < monitor.index('page.locator("#tabGuided").click()', disclosure)
    assert 'id="learningResumeNotice"' in html
    assert "已恢復上次進度" in app


def test_monitor_checks_relative_lesson_navigation_from_saved_position():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert "int(lesson_next.group(1)) == min(int(lesson_start.group(1)) + 1, 22)" in monitor
    assert "lesson_return.group(1) == lesson_start.group(1)" in monitor
    assert 'lesson_start.group(1) == "1" or "已恢復上次進度" in lesson_resume_notice' in monitor
    assert 'lesson_start.group(1) == "1" and' not in monitor


def test_cross_asset_lesson_teaches_directional_magnitude_calibration():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "web/index.html").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "實際 0.60 · 預測 0.80 個百分點，差 0.20" in html
    assert "實際 1.00 · 預測 1.40 個百分點，差 0.40" in html
    assert "乙組高估較多" in html
    assert '"實際 0.60 · 預測 0.80 個百分點，差 0.20"' in monitor
    assert '"實際 1.00 · 預測 1.40 個百分點，差 0.40"' in monitor


def test_monitor_isolates_lesson_progress_and_uses_current_catalog_length():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    reset = "saveLearningProgress = () => {}; savedLearningProgress.lessonIndex = 0; lessonIndex = 0;"
    assert reset in monitor and 'page.locator("#tabGuided").click()' in monitor
    assert "第 11 / 26 步" in monitor
    assert "第 11 / 15 步" not in monitor


def test_monitor_validates_model_checkbox_values_not_just_count():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert "value:input.value, enabled:!input.disabled" in monitor
    assert 'expected_compare_models = {"mlp", "rnn", "lstm", "gru", "tcn"}' in monitor
    assert "observed_compare_models == expected_compare_models" in monitor
    assert "multi-model choices={sorted(observed_compare_models)}/{sorted(expected_compare_models)} enabled" in monitor



def test_guided_catalog_monitor_reports_each_failed_clause():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert "const lessonCatalogClauses = [" in monitor
    assert "window.__lessonCatalogChecks = lessonCatalogClauses.map((passed, index) => ({index: index + 1, passed}))" in monitor
    assert "失敗子句索引={lesson_catalog_failures}" in monitor
    assert "return lessonCatalogClauses.every(Boolean)" in monitor

def test_browser_monitor_exceptions_are_failures():
    """A missing browser run must not be reported as a successful monitor."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert '"瀏覽器渲染／視覺檢查", "status": "FAIL"' in monitor


def test_activation_function_lesson_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "Sigmoid、ReLU 與 Tanh" in app and "calculateActivationComparison" in app
    assert "activationExercise" in html and "第 1 / 26 步" in html
    assert "Sigmoid、ReLU 與 Tanh" in guide and "sigmoidGradient" in guide and "tanhGradient" in guide
    assert "activationTarget" in app and "平方損失梯度" in app
    assert "calculateActivationComparison(-2).relu === 0" in monitor and "activation_ui_ok" in monitor
    assert "Math.abs(activation.tanh-0.96402758)<1e-7" in monitor
    assert "sigmoidGradient/4.248354255e-18-1)<1e-9" in monitor
    assert "tanhGradient/1.699341702e-17-1)<1e-9" in monitor
    assert "對稱輸入 +|z| 與 −|z| 的 Sigmoid／Tanh 局部導數相同" in app
    assert "negativeSaturated.includes('Sigmoid=0.0003')" in monitor
    assert "平方損失梯度" in monitor and "activationTarget" in monitor


def test_activation_lesson_explains_largest_local_gradient():
    script = r"""
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function calculateActivationComparison(');
      const end=source.indexOf('function calculateGradientClipping(',start);
      const nodes={activationInput:{value:'2'},activationTarget:{value:'1'},activationResult:{textContent:''}};
      const context={byId:id=>nodes[id]};vm.createContext(context);vm.runInContext(source.slice(start,end),context);
      context.renderActivationExercise();const positive=nodes.activationResult.textContent;
      nodes.activationTarget.value='0';context.renderActivationExercise();const zeroTarget=nodes.activationResult.textContent;
      nodes.activationInput.value='-2';nodes.activationTarget.value='1';context.renderActivationExercise();const negative=nodes.activationResult.textContent;
      const negativeRelu=negative;
      nodes.activationInput.value='0';context.renderActivationExercise();const reluBoundary=nodes.activationResult.textContent;
      nodes.activationTarget.value='';context.renderActivationExercise();const invalid=nodes.activationResult.textContent;
      nodes.activationInput.value='2';nodes.activationTarget.value='2';context.renderActivationExercise();const unreachableHigh=nodes.activationResult.textContent;
      nodes.activationTarget.value='0';context.renderActivationExercise();const boundary=nodes.activationResult.textContent;
      nodes.activationTarget.value='-1';context.renderActivationExercise();const lowerBoundary=nodes.activationResult.textContent;
      nodes.activationInput.value='40';nodes.activationTarget.value='0';context.renderActivationExercise();const sigmoidSaturation=nodes.activationResult.textContent;
      nodes.activationTarget.value='1';context.renderActivationExercise();const sigmoidNearTarget=nodes.activationResult.textContent;
      nodes.activationInput.value='-40';context.renderActivationExercise();const negativeSigmoidSaturation=nodes.activationResult.textContent;
      nodes.activationInput.value='20';context.renderActivationExercise();const tanhSaturation=nodes.activationResult.textContent;
      nodes.activationInput.value='-20';context.renderActivationExercise();const tanhNegativeSaturation=nodes.activationResult.textContent;
      nodes.activationInput.value='370';context.renderActivationExercise();const tanhExtreme=nodes.activationResult.textContent;
      nodes.activationInput.value='2';nodes.activationTarget.value='1e200';context.renderActivationExercise();const overflow=nodes.activationResult.textContent;
      process.stdout.write(JSON.stringify({positive,negative,negativeRelu,reluBoundary,zeroTarget,invalid,unreachableHigh,boundary,lowerBoundary,sigmoidSaturation,sigmoidNearTarget,negativeSigmoidSaturation,tanhSaturation,tanhNegativeSaturation,tanhExtreme,overflow}));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    assert "平方損失 0.0142" in result["positive"]
    assert "平方損失 1.0000" in result["positive"]
    assert "平方損失 0.0013" in result["positive"]
    assert "平方損失梯度 -2.503e-2" in result["positive"]
    assert "梯度下降會提高 z" in result["positive"]
    assert "平方損失 0.7758" in result["zeroTarget"]
    assert "平方損失 4.0000" in result["zeroTarget"]
    assert "平方損失 0.9293" in result["zeroTarget"]
    assert "平方損失梯度 1.850e-1" in result["zeroTarget"]
    assert "梯度下降會降低 z" in result["zeroTarget"]
    assert "請輸入有限的神經元值 z 與目標 y" in result["invalid"]
    assert "平方損失梯度 -1.850e-1" in result["negative"]
    assert "ReLU 負區提示：目標雖在輸出範圍且損失非零，局部導數仍為零" in result["negativeRelu"]
    assert "只靠這個神經元的梯度更新無法離開負區" in result["negativeRelu"]
    assert "ReLU 負區提示" in result["reluBoundary"]
    assert "目標在輸出範圍" in result["positive"]
    assert "Sigmoid=0.8808" in result["unreachableHigh"] and "平方損失梯度 -2.350e-1、目標不在輸出範圍" in result["unreachableHigh"]
    assert "ReLU=2.0000" in result["unreachableHigh"] and "平方損失梯度 0.000e+0、目標在輸出範圍" in result["unreachableHigh"]
    assert "Tanh=0.9640" in result["unreachableHigh"] and "平方損失梯度 -1.464e-1、目標不在輸出範圍" in result["unreachableHigh"]
    assert "目標不在輸出範圍" in result["boundary"] and "目標在輸出範圍" in result["boundary"]
    assert "目標不在輸出範圍" in result["lowerBoundary"]
    assert "局部導數 4.248e-18" in result["sigmoidSaturation"]
    assert "平方損失梯度 8.497e-18" in result["sigmoidSaturation"]
    assert "Sigmoid=1.0000（平方損失 0.0000" in result["sigmoidNearTarget"]
    assert "平方損失梯度 -3.610e-35" in result["sigmoidNearTarget"]
    assert "對稱輸入 +|z| 與 −|z| 的 Sigmoid／Tanh 局部導數相同" in result["sigmoidSaturation"]
    assert "Sigmoid=0.0000" in result["negativeSigmoidSaturation"]
    assert "局部導數 4.248e-18" in result["negativeSigmoidSaturation"]
    assert "局部導數 1.699e-17" in result["tanhSaturation"]
    assert "平方損失梯度 -6.797e-17" in result["tanhNegativeSaturation"]
    assert "局部導數 1.680e-321" in result["tanhExtreme"]
    assert "請輸入有限的神經元值 z 與目標 y" in result["overflow"]


def test_saved_comparison_monitor_matches_compatibility_copy():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "目標協定、模型、訓練設定、預測期間" in app
    assert "['目標協定','模型','訓練設定','預測期間','報酬定義','驗證日期'].every(term=>compatibleGuard.includes(term))" in monitor
    assert "compatibleGuard.startsWith(" not in monitor
    assert "const compatibleA=savedValidationSummary(" in monitor
    assert "const compatibleB=savedValidationSummary(" in monitor
    assert "savedComparisonCompatibility([compatibleA,compatibleB])" in monitor
    assert "savedComparisonChecklist" in app and "saved-comparison-checklist" in app
    assert "${label}${ok ? '一致' : '缺少或不同'}" in app and "不可直接排名" in app
    assert "已保存摘要下方會逐項列出" in (root / "docs/learning-guide.md").read_text()


def test_missing_saved_comparison_summary_blocks_ranking_with_next_step():
    script = r"""
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function savedComparisonCompatibility(');
      const end=source.indexOf('function savedComparisonChecklist(',start);
      vm.runInThisContext(source.slice(start,end));
      const message=savedComparisonCompatibility([{available:true},{available:false}]);
      process.stdout.write(message);
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert completed.stdout.startswith("不可直接排名：目前缺少兩份可用的一般驗證摘要")
    assert "請先完成兩個標的一般 walk-forward 驗證" in completed.stdout


def test_momentum_direction_geometry_and_input_boundaries():
    script = r"""
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function calculateMomentumDirection(');
      const end=source.indexOf('function calculateActivationComparison(',start);
      vm.runInThisContext(source.slice(start,end));
      const nodes={momentumDirectionResult:{textContent:''},momentumVectorDimension:{value:'3'},momentumVectorV1:{value:'1'},momentumVectorV2:{value:'2'},momentumVectorV3:{value:'2'},momentumVectorG1:{value:'2'},momentumVectorG2:{value:'1'},momentumVectorG3:{value:'0'}};
      const byId=id=>nodes[id]; renderMomentumDirection(); const renderedThree=nodes.momentumDirectionResult.textContent; nodes.momentumVectorDimension.value='2'; renderMomentumDirection(); const renderedTwo=nodes.momentumDirectionResult.textContent; nodes.momentumVectorV1.value='0'; nodes.momentumVectorV2.value='0'; renderMomentumDirection();
      process.stdout.write(JSON.stringify({
        same:calculateMomentumDirection(.5,0,1,0),
        opposite:calculateMomentumDirection(.5,0,-1,0),
        perpendicular:calculateMomentumDirection(1,0,0,2),
        threeDimensional:calculateMomentumDirection(1,2,2,2,1,0),
        tiny:calculateMomentumDirection(1e-200,2e-200,2e-200,1e-200),
        ordinary:calculateMomentumDirection(1,2,2,1),
        zero:calculateMomentumDirection(0,0,1,0),
        empty:calculateMomentumDirection('',0,1,0),
        overflow:calculateMomentumDirection(1e308,0,1e308,0),
        renderedZero:nodes.momentumDirectionResult.textContent, rendered:renderedTwo, renderedThree
      }));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    assert result["same"]["cosine"] == 1 and "加強" in result["same"]["relation"]
    assert result["same"]["parallel"] == 0.5 and result["same"]["perpendicular"] == 0
    assert result["opposite"]["cosine"] == -1 and "抵銷" in result["opposite"]["relation"]
    assert result["opposite"]["parallel"] == -0.5 and result["opposite"]["perpendicular"] == 0
    assert result["perpendicular"]["cosine"] == 0 and "垂直" in result["perpendicular"]["relation"]
    assert result["perpendicular"]["parallel"] == 0 and result["perpendicular"]["perpendicular"] == 1
    assert result["threeDimensional"]["dimensions"] == 3 and abs(result["threeDimensional"]["cosine"] - 0.5962847940) < 1e-9
    assert result["threeDimensional"]["vNorm"] == pytest.approx(3)
    assert result["threeDimensional"]["gNorm"] == pytest.approx(5 ** 0.5)
    assert result["threeDimensional"]["angleDegrees"] == pytest.approx(53.4, abs=0.05)
    assert result["tiny"]["angleDegrees"] == pytest.approx(36.8698976458)
    assert result["tiny"]["cosine"] == pytest.approx(0.8)
    assert result["tiny"]["parallel"] == pytest.approx(1.7888543819998317e-200)
    assert result["ordinary"]["angleDegrees"] == pytest.approx(result["tiny"]["angleDegrees"])
    assert "夾角比較的是方向" in (Path(__file__).resolve().parents[1] / "web/index.html").read_text()
    assert result["same"]["angleDegrees"] == 0
    assert result["opposite"]["angleDegrees"] == 180
    assert result["perpendicular"]["angleDegrees"] == 90
    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert "Math.abs(three.gNorm-Math.sqrt(5))<1e-12" in monitor
    assert "tiny=calculateMomentumDirection(1e-200,2e-200,2e-200,1e-200)" in monitor
    assert "tiny.angleDegrees" in monitor and "tiny.cosine" in monitor
    assert "three.gNorm===3" not in monitor
    assert "分解核對：|v|²=9.0000，平行分量²＋垂直分量²=9.0000" in monitor
    assert "分解核對：|v|²=5.0000，平行分量²＋垂直分量²=5.0000" in monitor
    assert result["zero"]["cosine"] is None and "零向量" in result["zero"]["relation"]
    assert result["empty"] is None and result["overflow"] is None
    assert "沿梯度方向的速度分量=1.7889" in result["renderedThree"]
    assert "垂直分量大小=2.4083" in result["renderedThree"]
    assert "夾角=53.40°" in result["renderedThree"]
    assert "分解核對：|v|²=9.0000，平行分量²＋垂直分量²=9.0000" in result["renderedThree"]
    assert "維度=2" in result["rendered"]
    assert "夾角=36.87°" in result["rendered"]
    assert "方向餘弦=0.8000" in result["rendered"]
    assert "沿梯度方向的速度分量=1.7889" in result["rendered"]
    assert "垂直分量大小=1.3416" in result["rendered"]
    assert "分解核對：|v|²=5.0000，平行分量²＋垂直分量²=5.0000" in result["rendered"]
    assert "維度=3" in result["renderedThree"]
    assert "|v|=3.0000；|g|=2.2361" in result["renderedThree"]
    assert "方向餘弦=未定義" in result["renderedZero"]
    assert "分解核對：未定義（零向量沒有方向）" in result["renderedZero"]
    assert "分解核對：|v|²=5.0000，平行分量²＋垂直分量²=5.0000" not in result["renderedZero"]


def test_momentum_direction_preloads_non_degenerate_three_dimensional_example():
    source = Path("web/index.html").read_text()
    section = source.split('id="momentumExercise"', 1)[1].split("</section>", 1)[0]
    defaults = {
        field: re.search(rf'id="momentumVector{field}"[^>]*value="([^"]+)"', section)
        for field in ("V1", "V2", "V3", "G1", "G2", "G3")
    }
    assert all(match for match in defaults.values())
    values = [float(defaults[field].group(1)) for field in ("V1", "V2", "V3", "G1", "G2", "G3")]
    assert values == [1, 2, 2, 2, 1, 0]
    assert "value=\"3\" selected" in section
    assert re.search(r'<select id="momentumVectorDimension">.*value="2".*value="3" selected', section)
    monitor = Path("scripts/regression_monitor.py").read_text()
    assert "momentum_step_checks = guided_fixture" in monitor
    assert "第二十步動量子句={momentum_step_checks}" in monitor
    assert 'wait_until="domcontentloaded"' in monitor


def test_regression_monitor_dependencies_are_declared():
    requirements = Path("requirements.txt").read_text().lower()
    assert "playwright>=" in requirements
    assert "pillow>=" in requirements


def test_saved_comparison_checklist_lists_protocol_mismatches():
    script = """
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function savedComparisonChecklist(');
      const end=source.indexOf('async function renderSavedCrossAssetComparison(',start);
      vm.runInThisContext(source.slice(start,end));
      const base={available:true,execution:'next_close',horizon:1,returnType:'simple',model:'MLP',setupSignature:'{}',period:'2024-01-01 至 2024-02-01'};
      process.stdout.write(JSON.stringify({same:savedComparisonChecklist([base,{...base}]),different:savedComparisonChecklist([base,{...base,setupSignature:'different'}]),missing:savedComparisonChecklist([base,{...base,execution:null}])}));
    """
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    assert "訓練設定一致" in result["same"] and "可描述性並列" in result["same"]
    assert "訓練設定缺少或不同" in result["different"] and "不可直接排名" in result["different"]
    assert "目標協定缺少或不同" in result["missing"]


def test_validation_comparison_chart_uses_shared_horizontal_scale_and_handles_edge_values():
    script = r"""
      const fs=require('fs'),vm=require('vm'),source=fs.readFileSync('web/app.js','utf8');
      const start=source.indexOf('function renderComparison('),end=source.indexOf('function renderDiagnostics(',start);
      const state={};let svg={innerHTML:'',attrs:{},getBoundingClientRect:()=>({width:390}),setAttribute(k,v){this.attrs[k]=v;}};
      const byId=(id)=>id==='comparisonChart'?svg:null,pct=(v)=>`${(Number(v)*100).toFixed(2)}%`;
      vm.runInThisContext(source.slice(start,end));
      renderComparison([{key:'mean',name:'歷史平均',mae:.0195,rmse:.027},{key:'bad',name:'<script>',mae:0,rmse:null},{key:'extreme',name:'極端值',mae:1e6,rmse:2e6}]);
      process.stdout.write(JSON.stringify({attrs:svg.attrs,html:svg.innerHTML}));
    """
    result = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    chart = result["html"]
    assert result["attrs"]["viewBox"].startswith("0 0 390 ")
    assert "MAE 1.95%" in chart and "RMSE 2.70%" in chart
    assert "RMSE —" in chart and "<script>" not in chart and "&lt;script&gt;" in chart
    assert "rotate(" not in chart and "comparison-grid" in chart
    assert chart.count("comparison-track") == 6


def test_validation_completion_keeps_viewport_still():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    start = source.index("function renderValidation(")
    end = source.index("function renderForwardTrace(", start)
    completion = source[start:end]
    assert "scrollIntoView" not in completion
    assert "diagnosticsPanel').open = true" not in completion
    assert "Diagnostics remain collapsed" in completion
    assert completion.index("dataset.status = 'complete'") < completion.index("renderComparison(")


def test_training_animation_keeps_forward_detail_from_shifting_layout():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "web/app.js").read_text()
    styles = (root / "web/styles.css").read_text()
    html = (root / "web/index.html").read_text()
    start = source[source.index("async function startJob("):source.index("async function pollJob(")]
    progress = source[source.index("function updateProgress("):source.index("function stopNetworkTrainingMotion(")]
    stop = source[source.index("function stopNetworkTrainingMotion("):source.index("async function startJob(")]
    assert "resetNetworkMotion()" not in start
    assert "startNetworkTrainingMotion(0, Number(payload.epochs) || 0)" in start
    assert "training-motion" in stop and "classList.remove('training-motion')" in stop
    assert "networkMotionStatus" not in progress
    training_motion = source[source.index("function startNetworkTrainingMotion("):source.index("function stopNetworkTrainingMotion(")]
    assert "activateNetworkStage(next, networkMotion.step >= 0)" in training_motion
    assert "setTimeout(advance, 820 / networkMotion.speed)" in training_motion
    assert "networkMotion.trainingTimer" in stop and "clearTimeout(networkMotion.trainingTimer)" in stop
    assert ".network-panel .network-step-detail" in styles and "block-size:236px" in styles and "overflow:auto" in styles
    assert "訓練時網路節點會逐層跳動" in html
    assert "#network.training-motion .network-diagram-data .network-node.is-active" in styles
    assert "animation: training-neuron-hop 820ms ease-in-out infinite !important" in styles
    assert "animation: training-edge-flow 560ms linear infinite !important" in styles


def test_training_animation_cycles_and_remains_visible_with_reduced_motion_enabled():
    import subprocess

    root = Path(__file__).resolve().parents[1]
    source = (root / "web/app.js").read_text()
    start = source.index("function startNetworkTrainingMotion(")
    end = source.index("function stopNetworkTrainingMotion(", start)
    script = f"""
const vm = require('vm');
const code = {json.dumps(source[start:end])};
function fixture(reducedMotion) {{
  const calls = [], timers = new Map(); let nextTimer = 1;
  const network = {{classList:{{add(){{}}}}}};
  const diagram = {{dataset:{{layerCount:'3'}}}};
  const sandbox = {{networkMotion:{{step:-1,speed:1,training:false,trainingTimer:null}},
    byId:id=>id==='network'?network:diagram,
    matchMedia:()=>({{matches:reducedMotion}}),
    activateNetworkStage:(step,animate)=>{{sandbox.networkMotion.step=step;calls.push([step,animate]);}},
    setTimeout:(callback,delay)=>{{const id=nextTimer++;timers.set(id,{{callback,delay}});return id;}},
    clearTimeout:id=>timers.delete(id)}};
  vm.runInNewContext(code+';globalThis.startNetworkTrainingMotion=startNetworkTrainingMotion;',sandbox);
  return {{sandbox,calls,timers,start:sandbox.startNetworkTrainingMotion}};
}}
const normal=fixture(false); normal.start(2,10);
for(let i=0;i<3;i++){{const [id,timer]=normal.timers.entries().next().value;normal.timers.delete(id);timer.callback();}}
if(JSON.stringify(normal.calls)!==JSON.stringify([[0,false],[1,true],[2,true],[0,true]]))process.exit(1);
if(normal.sandbox.networkMotion.trainingEpoch!==2||normal.sandbox.networkMotion.trainingEpochs!==10)process.exit(2);
const reduced=fixture(true);reduced.start(1,5);
if(JSON.stringify(reduced.calls)!==JSON.stringify([[0,false]])||reduced.timers.size!==1||!reduced.sandbox.networkMotion.training)process.exit(3);
"""
    subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True)


def test_network_toolbar_step_and_replay_icons_cannot_be_flex_shrunk_or_clipped():
    from pathlib import Path

    styles = (Path(__file__).resolve().parents[1] / "web/styles.css").read_text()
    assert ".network-panel .playground-run-controls #stepNetwork,.network-panel .playground-run-controls #replayNetwork" in styles
    assert "flex:0 0 42px; min-width:42px; overflow:visible" in styles
    assert ".network-panel .playground-run-controls button svg { display:block; width:22px; height:22px; overflow:visible;" in styles



def test_tcn_nodes_and_edges_participate_in_training_stage_animation():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    tcn = source[source.index("if (tcn) {"):source.index("const xs = [plot.x0", source.index("if (tcn) {"))]
    assert 'class="network-node ${kind} tcn-node" data-layer="${layer}"' in tcn
    assert 'class="network-connection network-sample-path tcn-edge" data-layer="0"' in tcn
    assert 'class="network-connection network-sample-path tcn-edge" data-layer="1"' in tcn
    assert 'class="network-node node-output tcn-output-node" data-layer="3"' in tcn
    assert 'class="tcn-detail-title"' in tcn and '單一殘差區塊' in tcn
    assert 'class="tcn-residual-frame"' in tcn and 'class="tcn-block-flow"' in tcn
    assert "Temporal convolution network" in tcn and "class=\"tcn-footnote\"" in tcn
    assert 'class="tcn-lane"' in tcn and 'sequence processed in parallel' in tcn

def test_paper_account_timeline_only_maps_persisted_event_kinds():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "web/paper.js").read_text()
    assert "'history_warning'" not in source
    assert "'history_verified'" not in source
    assert "historyVerification === 'verified_with_saved_anchors'" in source
    assert "本次沿用帳戶保存的錨點核對歷史。" in source
    assert "historyVerification === 'verified'" in source
    assert "提交的歷史已與帳戶錨點核對。" in source
    for event_kind in ("buy", "sell", "started", "paused", "resumed", "rejected"):
        assert f"{event_kind}:" in source


def test_cross_asset_lesson_teaches_magnitude_in_both_directions():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "web/index.html").read_text()
    guide = (root / "docs/learning-guide.md").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    for example in (
        "實際 0.60 · 預測 0.80 個百分點，差 0.20",
        "實際 1.00 · 預測 1.40 個百分點，差 0.40",
        "實際 0.50 · 預測 0.70 個百分點，差 0.20",
        "實際 0.80 · 預測 1.20 個百分點，差 0.40",
    ):
        assert example in html
    assert "下跌幅度為 0.50／0.70" in guide
    assert "乙組上漲幅度為 1.00／1.40" in guide
    assert '"實際 0.80 · 預測 1.20 個百分點，差 0.40"' in monitor


def test_gradient_clipping_lesson_has_observable_bounded_update():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "function calculateGradientClipping(" in app
    assert "w新=1.9" in app and "梯度裁剪" in app
    assert "梯度 (3,4) 的範數是 5" in app and "變成 (0.6,0.8)" in app
    assert "L2 範數為" in (root / "docs/learning-guide.md").read_text()
    assert 'id="gradientClippingExercise"' in html
    assert "把上限改成 0、0.5、1 和 4" in html
    assert "更新權重為 2、1.95、1.9、1.6" in (root / "docs/learning-guide.md").read_text()
    assert "calculateGradientClipping(2,4,1,0.1)" in monitor
    assert "保留原梯度大小的 25.0%" in monitor and "保留原梯度大小的 100.0%" in monitor
    assert "clipping_ui_ok" in monitor and "第 22 / 26 步" in monitor
    assert 'id="vectorGradientOne"' in html and 'id="vectorGradientResult"' in html
    assert 'id="vectorGradientThreeOne"' in html and 'id="vectorGradientThreeResult"' in html
    assert "renderVectorGradientClipping" in monitor
    assert "calculateVectorGradientClipping3(2,-1,2,1)" in monitor
    assert 'id="vectorGradientFourOne"' in html and 'id="vectorGradientFourResult"' in html
    assert "calculateVectorGradientClippingN([1,2,2,4],2)" in monitor and "vector_four_ui_ok" in monitor
    assert "四維互動例子" in (root / "docs/learning-guide.md").read_text()
    assert 'id="learningSummary">26 步導學' in html
    assert 'f"{lesson_start.group(2)} 步導學"' in monitor
    start_n = app.index("function calculateVectorGradientClippingN(")
    end_n = app.index("function renderVectorGradientClipping4(", start_n)
    script_n = app[start_n:end_n] + "process.stdout.write(JSON.stringify([calculateVectorGradientClippingN([1,2,2,4],2),calculateVectorGradientClippingN([3,4,0,0],10),calculateVectorGradientClippingN([0,0,0,0],2),calculateVectorGradientClippingN([1,'',2,4],2),calculateVectorGradientClippingN([1,2,2,4],-1),calculateVectorGradientClippingN(Array(65).fill(1),2)]));"
    actual_n = json.loads(subprocess.check_output(["node", "-e", script_n], text=True))
    assert actual_n[0] == {"norm": 5, "scale": 0.4, "clipped": [0.4, 0.8, 0.8, 1.6], "clippedNorm": 2, "componentClipped": [1, 2, 2, 2], "componentClippedNorm": 13**0.5}
    # Global norm clipping preserves direction; coordinate-wise clipping does not.
    assert actual_n[0]["clipped"][0] / actual_n[0]["clipped"][1] == 0.5
    assert actual_n[0]["componentClipped"][0] / actual_n[0]["componentClipped"][1] == 0.5
    assert actual_n[0]["clipped"][0] / actual_n[0]["clipped"][3] == 0.25
    assert actual_n[0]["componentClipped"][0] / actual_n[0]["componentClipped"][3] == 0.5
    assert actual_n[1] == {"norm": 5, "scale": 1, "clipped": [3, 4, 0, 0], "clippedNorm": 5, "componentClipped": [3, 4, 0, 0], "componentClippedNorm": 5}
    assert actual_n[2] == {"norm": 0, "scale": 1, "clipped": [0, 0, 0, 0], "clippedNorm": 0, "componentClipped": [0, 0, 0, 0], "componentClippedNorm": 0}
    assert actual_n[3:] == [None, None, None]
    assert actual_n[0]["componentClipped"] == [1, 2, 2, 2]
    render_four_start = app.index("function renderVectorGradientClipping4()")
    render_four_end = app.index("function renderVectorGradientClipping()", render_four_start)
    render_four = app[render_four_start:render_four_end]
    render_script = "const nodes={vectorGradientFourOne:{value:'1'},vectorGradientFourTwo:{value:'2'},vectorGradientFourThree:{value:'2'},vectorGradientFourFour:{value:'4'},vectorGradientFourLimit:{value:'2'},vectorGradientFourResult:{textContent:''}}; function byId(id){return nodes[id];}\n" + app[app.index("function calculateVectorGradientClippingN("):render_four_start] + render_four + "renderVectorGradientClipping4(); process.stdout.write(nodes.vectorGradientFourResult.textContent);"
    rendered_four = subprocess.check_output(["node", "-e", render_script], text=True)
    assert "(0.4000, 0.8000, 0.8000, 1.6000)" in rendered_four
    assert "(1.0000, 2.0000, 2.0000, 2.0000)" in rendered_four and "範數 3.6056" in rendered_four
    assert "餘弦 1.0000、偏轉角 0.00°" in rendered_four and "餘弦 0.9430、偏轉角 19.44°" in rendered_four
    zero_render_script = render_script.replace("value:'1'", "value:'0'").replace("value:'2'", "value:'0'").replace("value:'4'", "value:'0'")
    rendered_zero = subprocess.check_output(["node", "-e", zero_render_script], text=True)
    assert "原始 L2 範數 0.0000" in rendered_zero and "沒有更新方向；裁剪不會產生新的梯度" in rendered_zero
    zero_limit_script = render_script.replace("vectorGradientFourLimit:{value:'2'}", "vectorGradientFourLimit:{value:'0'}")
    rendered_zero_limit = subprocess.check_output(["node", "-e", zero_limit_script], text=True)
    assert "上限為 0 時，範數裁剪會把梯度縮放為零，這一步不會更新權重。" in rendered_zero_limit
    assert "四維範數與拒絕條件={vector_four_math_ok}" in monitor
    start = app.index("function calculateGradientClipping(")
    end = app.index("function renderGradientClippingExercise(", start)
    script = app[start:end] + "process.stdout.write(JSON.stringify([calculateGradientClipping(2,4,1,0.1),calculateGradientClipping(2,0.5,1,0.1),calculateGradientClipping(2,0,1,0.1),calculateGradientClipping('',4,1,0.1),calculateGradientClipping(2,4,-1,0.1)]));"
    actual = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert actual[0] == {"clipped": 1, "updated": 1.9, "unclippedUpdated": 1.6, "unclippedStep": 0.4, "clippedStep": 0.1, "retainedFraction": 0.25}
    assert actual[1] == {"clipped": 0.5, "updated": 1.95, "unclippedUpdated": 1.95, "unclippedStep": 0.05, "clippedStep": 0.05, "retainedFraction": 1}
    assert actual[2]["retainedFraction"] == 1
    assert actual[3:] == [None, None]
    vector_start = app.index("function calculateVectorGradientClipping(")
    vector_end = app.index("function renderVectorGradientClipping(", vector_start)
    vector_script = app[vector_start:vector_end] + "process.stdout.write(JSON.stringify([calculateVectorGradientClipping(3,4,1),calculateVectorGradientClipping(0.3,0.4,1),calculateVectorGradientClipping(0,0,1),calculateVectorGradientClipping('',4,1),calculateVectorGradientClipping(3,4,-1)]));"
    vector_actual = json.loads(subprocess.check_output(["node", "-e", vector_script], text=True))
    assert vector_actual[0] == {"norm": 5, "scale": 0.2, "clippedOne": 0.6000000000000001, "clippedTwo": 0.8, "clippedNorm": 1, "componentClippedOne": 1, "componentClippedTwo": 1, "componentClippedNorm": 2**0.5}
    assert vector_actual[1] == {"norm": 0.5, "scale": 1, "clippedOne": 0.3, "clippedTwo": 0.4, "clippedNorm": 0.5, "componentClippedOne": 0.3, "componentClippedTwo": 0.4, "componentClippedNorm": 0.5}
    assert vector_actual[2]["clippedNorm"] == 0
    assert vector_actual[3:] == [None, None]


def test_gradient_clipping_lesson_renders_limit_sweep_and_lesson_monitor_uses_correct_loss():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    html = (root / "web/index.html").read_text()
    assert 'id="clippingSweepResult"' in html
    assert "momentumSteps.velocity3-(-0.3755)" in monitor
    assert "momentumSteps.weight3-1.71205" in monitor
    assert "oversized_step_loss_ok =" in monitor and "更新後 16" in monitor
    start = app.index("function calculateGradientClipping(")
    end = app.index("function calculateVectorGradientClipping(", start)
    nodes = "const nodes={clippingWeight:{value:'2'},clippingGradient:{value:'4'},clippingLimit:{value:'1'},clippingRate:{value:'0.1'},gradientClippingResult:{textContent:''},clippingSweepResult:{textContent:''}}; function byId(id){return nodes[id];}\n"
    rendered = subprocess.check_output(["node", "-e", nodes + app[start:end] + "renderGradientClippingExercise(); process.stdout.write(nodes.clippingSweepResult.textContent);"], text=True)
    for expected in (
        "上限 0 → 裁剪梯度 0.00、新權重 2.00",
        "上限 0.5 → 裁剪梯度 0.50、新權重 1.95",
        "上限 1 → 裁剪梯度 1.00、新權重 1.90",
        "上限 4 → 裁剪梯度 4.00、新權重 1.60",
    ):
        assert expected in rendered


def test_gradient_descent_trace_shows_recomputed_steps_and_rejects_invalid_inputs():
    import json
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    html = (root / "web/index.html").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "梯度下降軌跡" in app and 'id="gradientDescentTrace"' in html
    assert "權重位移 Δw=" in app
    assert "gradient_descent_trace_ok" in monitor and "多步梯度下降軌跡={gradient_descent_trace_ok}" in monitor and "第 23 / 26 步" in monitor
    assert "η=0.5（誤差倍率 0.00；一步到達最低點）→ 損失" in monitor and "η=1（誤差倍率 -1.00；邊界振盪）→ 損失" in monitor
    assert 'id="gradientDescentRateComparison"' in html
    assert "若更新後超出數值範圍，請縮小起始權重或學習率" in app
    start = app.index("function calculateGradientDescentTrace(")
    end = app.index("function renderGradientDescentTrace(", start)
    script = app[start:end] + "process.stdout.write(JSON.stringify([calculateGradientDescentTrace(3,0.25,4),calculateGradientDescentTrace(3,1,2),calculateGradientDescentTrace(3,'',4),calculateGradientDescentTrace(3,0.25,11),calculateGradientDescentTrace(3,0.5,2,2),calculateGradientDescentTrace(3,0.75,2,2),calculateGradientDescentTrace(3,0.5,2,6),calculateGradientDescentTrace(3,0.5,2,1),calculateGradientDescentTrace(3,0.49,2,1),calculateGradientDescentTrace(1e308,1,10,5)]));"
    rows, overshoot, empty_rate, too_many, oscillate, diverge, invalid_curvature, one_step_minimum, slow_convergence, overflow = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert overflow is None
    assert [row["weight"] for row in rows] == [3, 2, 1.5, 1.25, 1.125]
    assert [row["loss"] for row in rows] == [4, 1, 0.25, 0.0625, 0.015625]
    assert [row["weight"] for row in overshoot] == [3, -1, 3]
    assert [row["loss"] for row in overshoot] == [4, 4, 4]
    assert [row["weight"] for row in oscillate] == [3, -1, 3]
    assert [row["loss"] for row in oscillate] == [8, 8, 8]
    assert [row["weight"] for row in diverge] == [3, -3, 9]
    assert [row["loss"] for row in diverge] == [8, 32, 128]
    assert empty_rate is None and too_many is None
    assert invalid_curvature is None
    assert one_step_minimum[1]["weight"] == 1 and one_step_minimum[1]["loss"] == 0
    assert abs(slow_convergence[1]["weight"] - 1.04) < 1e-12 and abs(slow_convergence[1]["loss"] - 0.0016) < 1e-12
    render_start = app.index("function renderGradientDescentTrace(")
    render_end = app.index("function renderVectorGradientClipping(", render_start)
    render_script = "const nodes={traceCurvature:{value:'1'},traceStartWeight:{value:'3'},traceLearningRate:{value:'0.25'},traceStepCount:{value:'4'},gradientDescentTraceResult:{textContent:''},gradientDescentRateComparison:{textContent:''}}; const byId=id=>nodes[id];\n" + app[start:render_end] + "renderGradientDescentTrace(); process.stdout.write(JSON.stringify([nodes.gradientDescentTraceResult.textContent,nodes.gradientDescentRateComparison.textContent]));"
    output, comparison = json.loads(subprocess.check_output(["node", "-e", render_script], text=True))
    assert output.startswith("目前設定 ηc=0.25，有號誤差倍率=0.50（不越過最低點而收斂）。")
    assert "步驟 0：w=3.0000，距最低點 |w−1|=2.0000，梯度=4.0000，L=4.0000" in output
    assert "步驟 4：w=1.1250，距最低點 |w−1|=0.1250，有號誤差倍率=0.5000，梯度=0.2500，權重位移 Δw=-0.1250（下降），L=0.0156" in output
    assert "步驟 1：w=2.0000，距最低點 |w−1|=1.0000，有號誤差倍率=0.5000，梯度=2.0000，權重位移 Δw=-1.0000（下降），L=1.0000，ΔL=-3.0000（下降）" in output
    assert "步驟 1：w=2.0000，距最低點 |w−1|=1.0000，有號誤差倍率=0.5000，梯度=2.0000，權重位移 Δw=-1.0000（下降）" in output
    assert "η=0.25（誤差倍率 0.50；收斂）→ 損失 4.0000→1.0000→0.2500→0.0625→0.0156" in comparison
    assert "ΔL=-3.0000（下降）" in output
    assert "η=0.5（誤差倍率 0.00；一步到達最低點）→ 損失 4.0000→0.0000→0.0000→0.0000→0.0000" in comparison
    assert "η=1（誤差倍率 -1.00；邊界振盪）→ 損失 4.0000→4.0000→4.0000→4.0000→4.0000" in comparison
    alternating_script = render_script.replace("traceLearningRate:{value:'0.25'}", "traceLearningRate:{value:'0.75'}")
    alternating, _ = json.loads(subprocess.check_output(["node", "-e", alternating_script], text=True))
    assert alternating.startswith("目前設定 ηc=0.75，有號誤差倍率=-0.50（交替越過最低點並收斂）。")
    no_update_script = render_script.replace("traceLearningRate:{value:'0.25'}", "traceLearningRate:{value:'0'}")
    no_update, _ = json.loads(subprocess.check_output(["node", "-e", no_update_script], text=True))
    assert no_update.startswith("目前設定 ηc=0.00，有號誤差倍率=1.00（不更新）。")
    assert "每步下降→下降→下降→下降" in comparison
    assert "每步下降→不變→不變→不變" in comparison
    assert "每步不變→不變→不變→不變" in comparison
    oscillation_script = render_script.replace("traceCurvature:{value:'1'}", "traceCurvature:{value:'2'}").replace("traceLearningRate:{value:'0.25'}", "traceLearningRate:{value:'0.5'}").replace("traceStepCount:{value:'4'}", "traceStepCount:{value:'2'}")
    oscillation, _ = json.loads(subprocess.check_output(["node", "-e", oscillation_script], text=True))
    assert "步驟 1：w=-1.0000，距最低點 |w−1|=2.0000，有號誤差倍率=-1.0000" in oscillation
    curvature_script = render_script.replace("traceCurvature:{value:'1'}", "traceCurvature:{value:'2'}").replace("traceLearningRate:{value:'0.25'}", "traceLearningRate:{value:'0.5'}")
    _, curvature_comparison = json.loads(subprocess.check_output(["node", "-e", curvature_script], text=True))
    assert "固定 c=2" in curvature_comparison
    assert "η=0.25（誤差倍率 0.00；一步到達最低點）" in curvature_comparison
    assert "η=0.5（誤差倍率 -1.00；邊界振盪）" in curvature_comparison
    assert "η=1（誤差倍率 -3.00；發散（交替遠離最低點））" in curvature_comparison
    assert "0<ηc<1 時收斂" in comparison and "ηc=1 時一步到達最低點" in comparison and "ηc>1 會交替發散" in comparison
    overflow_script = render_script.replace("traceCurvature:{value:'1'}", "traceCurvature:{value:'5'}").replace("traceStartWeight:{value:'3'}", "traceStartWeight:{value:'1e308'}").replace("traceLearningRate:{value:'0.25'}", "traceLearningRate:{value:'1'}")
    overflow_output, overflow_comparison = json.loads(subprocess.check_output(["node", "-e", overflow_script], text=True))
    assert "若更新後超出數值範圍，請縮小起始權重或學習率" in overflow_output
    assert "完成有效輸入" in overflow_comparison
    invalid_script = render_script.replace("traceStepCount:{value:'4'}", "traceStepCount:{value:'11'}")
    _, invalid_comparison = json.loads(subprocess.check_output(["node", "-e", invalid_script], text=True))
    assert "完成有效輸入" in invalid_comparison


def test_idle_training_monitor_reports_the_actual_epoch_contract():
    from pathlib import Path
    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text()
    assert "Epoch 顯示與設定相符" in monitor
    assert "目前 {epoch_display}；設定" in monitor
    assert "Epoch 維持待命" not in monitor


def test_momentum_lesson_shows_previous_and_current_gradient_contributions():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text()
    monitor = (root / "scripts/regression_monitor.py").read_text()
    assert "第一步：βvₜ₋₁" in app
    assert "第二步沿用 vₜ" in app
    assert "vₜ₊₁ = ${beta} × ${result.velocity1.toFixed(4)}" in app
    assert "不保留動量（β=0）時，三步權重為" in app
    guide = (root / "docs/learning-guide.md").read_text()
    assert "1.9000 → 1.8500 → 2.0500` 與目前 β=0.9 的 `1.8550 → 1.6745 → 1.71205`" in guide
    assert "真實訓練更新權重後會重新計算梯度" in guide
    start = app.index("function calculateMomentumUpdate(")
    end = app.index("function calculateActivationComparison(", start)
    script = app[start:end] + "process.stdout.write(JSON.stringify(calculateMomentumUpdate(0.9,0.5,1,2,0.1)));"
    actual = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert actual == {"velocity": 1.45, "updated": 1.855}
    render_script = app[start:app.index("function calculateActivationComparison(", start)] + "\nconst nodes={momentumResult:{textContent:''},momentumBeta:{value:'0.9'},momentumPrevious:{value:'0.5'},momentumGradient:{value:'1'},momentumNextGradient:{value:'0.5'},momentumThirdGradient:{value:'-2'},momentumWeight:{value:'2'},momentumRate:{value:'0.1'}}; const byId=id=>nodes[id]; renderMomentumExercise(); process.stdout.write(nodes.momentumResult.textContent);"
    output = subprocess.check_output(["node", "-e", render_script], text=True)
    assert "第一步：βvₜ₋₁ = 0.9 × 0.5 = 0.4500" in output
    assert "vₜ = 1.4500，wₜ = 1.8550" in output
    assert "vₜ₊₁ = 0.9 × 1.4500 + 0.5000 = 1.8050，wₜ₊₁ = 1.6745" in output
    assert "不保留動量（β=0）時" in output
    assert "1.9000 → 1.8500 → 2.0500" in output
    assert "目前設定三步為 1.8550 → 1.6745 → 1.71205" in output
    assert "歷史速度反向（β=0.5、vₜ₋₁=−0.5、gₜ=1）" in output
    assert "保留貢獻 −0.2500 會抵銷部分本步梯度，合成速度 0.7500，權重變為 1.9250" in output
    negative_history_script = app[start:app.index("function calculateActivationComparison(", start)] + "\nconst nodes={momentumResult:{textContent:''},momentumBeta:{value:'0.5'},momentumPrevious:{value:'-0.5'},momentumGradient:{value:'1'},momentumNextGradient:{value:'0.5'},momentumThirdGradient:{value:'-2'},momentumWeight:{value:'2'},momentumRate:{value:'0.1'}}; const byId=id=>nodes[id]; renderMomentumExercise(); process.stdout.write(nodes.momentumResult.textContent);"
    negative_output = subprocess.check_output(["node", "-e", negative_history_script], text=True)
    assert "第一步：βvₜ₋₁ = 0.5 × -0.5 = -0.2500" in negative_output
    assert "vₜ = 0.7500，wₜ = 1.9250" in negative_output
    assert "權重變為 1.9250" in negative_output


def test_momentum_lesson_carries_velocity_across_two_steps():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text()
    start = app.index("function calculateMomentumUpdate(")
    end = app.index("function calculateActivationComparison(", start)
    script = app[start:end] + """
const nodes={momentumResult:{textContent:''},momentumBeta:{value:'0.9'},momentumPrevious:{value:'0.5'},momentumGradient:{value:'1'},momentumNextGradient:{value:'0.5'},momentumThirdGradient:{value:'-2'},momentumWeight:{value:'2'},momentumRate:{value:'0.1'}};
const byId=id=>nodes[id]; renderMomentumExercise();
process.stdout.write(JSON.stringify({steps:calculateMomentumSteps(0.9,0.5,1,0.5,-2,2,0.1),zero:calculateMomentumSteps(0,0.5,1,0.5,-2,2,0.1),invalid:calculateMomentumSteps(0.9,0.5,1,0.5,'',2,0.1),text:nodes.momentumResult.textContent}));
"""
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert result["steps"] == {"velocity1": 1.45, "weight1": 1.855, "velocity2": 1.805, "weight2": 1.6745, "velocity3": -0.37549999999999994, "weight3": 1.71205}
    assert abs(result["zero"]["weight3"] - 2.05) < 1e-12
    assert result["invalid"] is None
    assert "vₜ = 1.4500，wₜ = 1.8550" in result["text"]
    assert "vₜ₊₁ = 0.9 × 1.4500 + 0.5000 = 1.8050，wₜ₊₁ = 1.6745" in result["text"]
    assert "不保留動量（β=0）時" in result["text"]
    assert "1.9000 → 1.8500" in result["text"]
    assert "目前設定三步為 1.8550 → 1.6745 → 1.71205" in result["text"]
    assert "vₜ₊₂ = 0.9 × 1.8050 + -2.0000 = -0.3755，wₜ₊₂ = 1.71205" in result["text"]
    assert "第三步速度已反向（1.8050 → -0.3755），因此權重上升（1.67450 → 1.71205）" in result["text"]


def test_loss_pointer_uses_css_pixel_coordinates_before_scaling_svg_viewbox():
    app = (Path(__file__).parents[1] / "web" / "app.js").read_text()
    start = app.index("function renderLossChart(model)")
    end = app.index("function readRunHistory()", start)
    renderer = app[start:end]
    assert "(event.clientX-rect.left)/Math.max(1,rect.width)*W" in renderer
    assert "const plotX=Math.max(L,Math.min(W-R,localX))" in renderer
    assert "event.clientX;point.y=event.clientY;point.matrixTransform(svg.getScreenCTM().inverse())" not in renderer


def test_loss_pointer_clamps_axis_margins_to_nearest_plotted_epoch():
    app = (Path(__file__).parents[1] / "web" / "app.js").read_text()
    start = app.index("function renderLossChart(model)")
    end = app.index("function readRunHistory()", start)
    renderer = app[start:end]
    script = r"""
const handlers={};
const attrs={};
const makeNode=()=>({setAttribute(k,v){attrs[k]=v;},style:{},dataset:{}});
const nodes={lossChart:{innerHTML:'',dataset:{},setAttribute(){},closest:()=>({getBoundingClientRect:()=>({left:0,top:0,width:660,height:250})}),getBoundingClientRect:()=>({left:0,top:0,width:660,height:250})},lossCursor:makeNode(),lossTrainPoint:makeNode(),lossValidPoint:makeNode(),lossTooltip:{hidden:true,style:{},innerHTML:''},lossLegend:{innerHTML:''}};
const byId=id=>nodes[id];
const svg=nodes.lossChart;
""" + renderer + r"""
renderLossChart({meanTrainLoss:[.12,.06,.03,.02],meanValidationLoss:[.15,.08,.05,.04]});
const samples=[-50,66,354,642,700].map(clientX=>{svg.onpointermove({clientX,clientY:125});return {epoch:Number(svg.dataset.epoch),text:nodes.lossTooltip.innerHTML};});
process.stdout.write(JSON.stringify(samples));
"""
    output = subprocess.check_output(["node", "-e", script], text=True)
    samples = json.loads(output)
    assert [sample["epoch"] for sample in samples] == [0, 0, 2, 3, 3]
    assert all("Epoch " in sample["text"] and "Train" in sample["text"] and "Validation" in sample["text"] for sample in samples)


def test_loss_pointer_ignores_touch_move_so_page_scroll_does_not_open_tooltip():
    app = (Path(__file__).parents[1] / "web" / "app.js").read_text()
    start = app.index("function renderLossChart(model)")
    end = app.index("function readRunHistory()", start)
    renderer = app[start:end]
    script = r"""
const makeNode=()=>({setAttribute(){},style:{},dataset:{}});
const svg={innerHTML:'',dataset:{},setAttribute(){},closest:()=>({getBoundingClientRect:()=>({left:0,top:0,width:660,height:250})}),getBoundingClientRect:()=>({left:0,top:0,width:660,height:250})};
const nodes={lossChart:svg,lossCursor:makeNode(),lossTrainPoint:makeNode(),lossValidPoint:makeNode(),lossTooltip:{hidden:true,style:{},innerHTML:''},lossLegend:{innerHTML:''}};
const byId=id=>nodes[id];
""" + app[start:end] + r"""
renderLossChart({meanTrainLoss:[.12,.06,.03],meanValidationLoss:[.15,.08,.05]});
svg.onpointermove({pointerType:'mouse',clientX:354,clientY:120});
const mouse={epoch:svg.dataset.epoch,visible:!nodes.lossTooltip.hidden};
svg.dataset.epoch='0';nodes.lossTooltip.hidden=true;
svg.onpointermove({pointerType:'touch',clientX:642,clientY:120});
process.stdout.write(JSON.stringify({mouse,touch:{epoch:svg.dataset.epoch,visible:!nodes.lossTooltip.hidden}}));
"""
    result = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert result["mouse"] == {"epoch": "1", "visible": True}
    assert result["touch"] == {"epoch": "0", "visible": False}


def test_loss_hit_area_is_behind_interactive_curves_and_cursor():
    app = (Path(__file__).parents[1] / "web" / "app.js").read_text()
    start = app.index("function renderLossChart(model)")
    end = app.index("function readRunHistory()", start)
    renderer = app[start:end]
    hit_index = renderer.index('class="loss-hit-area"')
    assert hit_index < renderer.index('class="loss-train-line"')
    assert hit_index < renderer.index('id="lossCursor"')
    assert hit_index < renderer.index('id="lossTrainPoint"')


def test_loss_hover_monitor_waits_on_the_svg_hit_target():
    monitor = (Path(__file__).parents[1] / "scripts" / "regression_monitor.py").read_text()
    assert 'chart.locator(".loss-hit-area").hover(position={"x": 288, "y": 90}, timeout=5000)' in monitor
    assert "page.wait_for_function(\"() => { const tip=document.querySelector('#lossTooltip')" in monitor


def test_comparison_chart_compacts_narrow_labels_and_preserves_full_names():
    app = (Path(__file__).parents[1] / "web" / "app.js").read_text()
    start = app.index("function renderComparison(rows)")
    end = app.index("function renderDiagnostics(model)", start)
    script = app[start:end] + r'''
const svg={innerHTML:'',setAttribute(){},getBoundingClientRect(){return {width:390}}};
const hint={hidden:true,textContent:''};
const state={};
const pct=value=>(value*100).toFixed(2)+'%';
const byId=id=>id==='comparisonChart'?svg:hint;
renderComparison([{name:'Random Forest',mae:0.1,rmse:0.2},{name:'MLP',mae:0.1,rmse:0.2}]);
process.stdout.write(JSON.stringify({svg:svg.innerHTML,hintHidden:hint.hidden,hint:hint.textContent}));
'''
    output = subprocess.check_output(["node", "-e", script], text=True)
    rendered = json.loads(output)
    assert rendered["svg"].count("bar-label-rotated") == 2
    assert '<title>Random Forest</title>Random…' in rendered["svg"]
    assert rendered["hintHidden"] is False and "短標籤" in rendered["hint"]


def test_adam_two_step_rejects_squared_gradient_underflow():
    app = (Path(__file__).resolve().parents[1] / "web/app.js").read_text(encoding="utf-8")
    start = app.index("function calculateAdamTwoSteps(")
    end = app.index("\nfunction renderAdamTwoStepExercise", start)
    script = app[start:end] + r"""
const bad=calculateAdamTwoSteps(1e-200,-1e-200,0.1,0.9,0.999,1e-300);
const ordinary=calculateAdamTwoSteps(2,-1,0.1,0.9,0.999);
process.stdout.write(JSON.stringify({bad, ordinary:ordinary && ordinary.adamWeight2}));
"""
    result = json.loads(subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True).stdout)
    assert result["bad"] is None
    assert abs(result["ordinary"] - 0.873367) < 0.00001


def test_adam_first_step_shows_bias_correction_and_sgd_comparison():
    import json
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    html = (root / "web/index.html").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    guide = (root / "docs/learning-guide.md").read_text(encoding="utf-8")
    start = app.index("function calculateAdamFirstStep(")
    end = app.index("\nfunction renderGradientDescentTrace(", start)
    script = f"""
const vm=require('vm');
const nodes={{adamGradient:{{value:'2'}},adamRate:{{value:'0.1'}},adamBeta1:{{value:'0.9'}},adamBeta2:{{value:'0.999'}},adamStepResult:{{textContent:''}},adamGradient1:{{value:'2'}},adamGradient2:{{value:'-1'}},adamRate2:{{value:'0.1'}},adamBeta12:{{value:'0.9'}},adamBeta22:{{value:'0.999'}},adamEpsilon2:{{value:'0.00000001'}},adamTwoStepResult:{{textContent:''}}}};
const byId=id=>nodes[id];
vm.runInThisContext({json.dumps(app[start:end])});
renderAdamStepExercise(); const initial=nodes.adamStepResult.textContent;
nodes.adamGradient.value='-2'; renderAdamStepExercise(); const negative=nodes.adamStepResult.textContent;
nodes.adamGradient.value='4'; renderAdamStepExercise(); const largerGradient=nodes.adamStepResult.textContent;
nodes.adamBeta1.value='1'; renderAdamStepExercise(); const invalid=nodes.adamStepResult.textContent;
nodes.adamBeta1.value='0.9'; nodes.adamGradient.value=''; renderAdamStepExercise(); const blank=nodes.adamStepResult.textContent;
renderAdamTwoStepExercise(); const twoStep=nodes.adamTwoStepResult.textContent;
nodes.adamBeta22.value='0.9'; renderAdamTwoStepExercise(); const lowerBeta2=nodes.adamTwoStepResult.textContent;
nodes.adamBeta22.value='0.999'; renderAdamTwoStepExercise();
nodes.adamBeta22.value='0'; renderAdamTwoStepExercise(); const zeroBeta2=nodes.adamTwoStepResult.textContent;
nodes.adamBeta22.value='0.999'; renderAdamTwoStepExercise();
nodes.adamGradient2.value='2'; renderAdamTwoStepExercise(); const aligned=nodes.adamTwoStepResult.textContent;
nodes.adamGradient2.value='0'; renderAdamTwoStepExercise(); const zeroSecond=nodes.adamTwoStepResult.textContent;
nodes.adamGradient1.value='0.00001'; renderAdamTwoStepExercise(); const tinyZeroSecond=nodes.adamTwoStepResult.textContent;
nodes.adamGradient1.value='2';
nodes.adamGradient2.value='-1.8'; renderAdamTwoStepExercise(); const cancelled=nodes.adamTwoStepResult.textContent;
nodes.adamGradient2.value='-1.79999'; renderAdamTwoStepExercise(); const nearCancelled=nodes.adamTwoStepResult.textContent;
nodes.adamGradient1.value='0'; nodes.adamGradient2.value='0'; renderAdamTwoStepExercise(); const bothZero=nodes.adamTwoStepResult.textContent;
nodes.adamGradient1.value='2';
nodes.adamGradient2.value=''; renderAdamTwoStepExercise(); const twoStepBlank=nodes.adamTwoStepResult.textContent;
nodes.adamGradient2.value='-1'; nodes.adamEpsilon2.value='0.1'; renderAdamTwoStepExercise(); const epsilonChanged=nodes.adamTwoStepResult.textContent;
nodes.adamEpsilon2.value=''; renderAdamTwoStepExercise(); const epsilonBlank=nodes.adamTwoStepResult.textContent;
nodes.adamEpsilon2.value='0.00000001'; renderAdamTwoStepExercise();
process.stdout.write(JSON.stringify({{initial,negative,largerGradient,invalid,blank,twoStep,lowerBeta2,zeroBeta2,aligned,zeroSecond,tinyZeroSecond,cancelled,nearCancelled,bothZero,twoStepBlank,epsilonChanged,epsilonBlank,invalidMath:calculateAdamFirstStep(2,0.1,1,0.999)===null,blankMath:calculateAdamFirstStep('',0.1,0.9,0.999)===null,zeroGradient:calculateAdamFirstStep(0,0.1,0.9,0.999).adamWeight,twoStepMath:calculateAdamTwoSteps(2,-1,0.1,0.9,0.999),epsilonMath:calculateAdamTwoSteps(2,-1,0.1,0.9,0.999,0.1),blankTwoStepMath:calculateAdamTwoSteps('',-1,0.1,0.9,0.999)===null,blankEpsilonMath:calculateAdamTwoSteps(2,-1,0.1,0.9,0.999,'')===null}}));
"""
    result = json.loads(subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True).stdout)
    assert "m₁=0.2000、v₁=0.0040" in result["initial"]
    assert "m̂₁=2.0000、v̂₁=4.0000" in result["initial"]
    assert "SGD 位移=0.2000，w₁=0.8000" in result["initial"]
    assert "Adam 位移=0.1000，w₁=0.9000" in result["initial"]
    assert "Adam 位移=-0.1000，w₁=1.1000" in result["negative"]
    assert "SGD 位移=0.4000，w₁=0.6000" in result["largerGradient"]
    assert "Adam 位移=0.1000，w₁=0.9000" in result["largerGradient"]
    assert "0 ≤ β₁、β₂ < 1" in result["invalid"] and result["invalidMath"]
    assert "請輸入有限梯度" in result["blank"] and result["blankMath"]
    assert result["zeroGradient"] == 1
    assert "相加 m₂=0.0800；平方梯度歷史項 β₂v₁=0.003996" in result["twoStep"]
    assert "歷史項 β₁m₁=0.1800，當步項 (1−β₁)g₂=-0.1000，相加 m₂=0.0800" in result["twoStep"]
    assert "平方梯度歷史項 β₂v₁=0.003996，當步項 (1−β₂)g₂²=0.001000，相加 v₂=0.004996" in result["twoStep"]
    assert "m̂₂=0.4211、v̂₂=2.4992" in result["twoStep"]
    assert "g₂=-1.0000 與 Adam 校正動差 m̂₂=0.4211 方向相反" in result["twoStep"]
    assert "SGD 的 w₂=0.9000" in result["twoStep"]
    assert "Adam 的 w₁=0.9000 → w₂=0.8734" in result["twoStep"]
    assert "√v̂₂+ε=1.5809+1.0e-8=1.5809" in result["twoStep"]
    assert "ηm̂₂/(√v̂₂+ε)=0.0266" in result["twoStep"]
    assert "權重改變 −0.0266" in result["twoStep"]
    assert "β₂ 記憶對照（相同梯度）：β₂=0 時分母 1.0000、更新量 0.0421；目前 β₂=0.999 時分母 1.5809、更新量 0.0266" in result["twoStep"]
    assert "ε 對照（相同梯度與動差）：ε=0 時分母 1.5809、更新量 0.0266" in result["twoStep"]
    assert "目前 ε=1.0e-8 時分母 1.5809、更新量 0.0266" in result["twoStep"]
    assert "β₂=0 時分母 1.0000、更新量 0.0421" in result["zeroBeta2"]
    assert "目前 β₂=0.900 時分母 1.5560、更新量 0.0271" in result["lowerBeta2"]
    assert "m₂=0.3800" in result["aligned"]
    assert "平方梯度歷史項 β₂v₁=0.003996，當步項 (1−β₂)g₂²=0.004000，相加 v₂=0.007996" in result["aligned"]
    assert "方向相同" in result["aligned"]
    assert "g₂=0.0000 沒有方向" in result["zeroSecond"] and "仍保留先前累積方向" in result["zeroSecond"]
    assert "方向相反" not in result["zeroSecond"]
    assert "m̂₂=4.74e-6" in result["tinyZeroSecond"] and "m̂₂=0.0000" not in result["tinyZeroSecond"]
    assert "梯度同乘 10（固定 β、η、ε）" in result["twoStep"]
    assert "Adam 更新量 0.0266；SGD w₂=0.0000（原本 0.9000）" in result["twoStep"]
    assert "Adam 校正動差 m̂₂=0.0000" in result["cancelled"]
    assert "歷史與當步梯度恰好抵銷" in result["cancelled"]
    assert "第二步沒有更新方向" in result["cancelled"]
    assert "方向相反" not in result["cancelled"]
    assert "m̂₂=5.26e-6" in result["nearCancelled"]
    assert "方向相反" in result["nearCancelled"]
    assert "m̂₂=0.0000" not in result["nearCancelled"]
    assert "當步梯度 g₂ 與 Adam 校正動差 m̂₂ 都為零" in result["bothZero"]
    assert "請輸入兩個有限梯度" in result["twoStepBlank"] and result["blankTwoStepMath"]
    assert "ε=1.0e-1" in result["epsilonChanged"] and "w₂=0.8797" in result["epsilonChanged"]
    assert "√v̂₂+ε=1.5809+1.0e-1=1.6809" in result["epsilonChanged"]
    assert "ηm̂₂/(√v̂₂+ε)=0.0250" in result["epsilonChanged"]
    assert "權重改變 −0.0250" in result["epsilonChanged"]
    assert "0 < ε ≤ 1" in result["epsilonBlank"] and result["blankEpsilonMath"]
    assert abs(result["twoStepMath"]["adamWeight2"] - 0.873367) < 0.00001
    assert abs(result["epsilonMath"]["adamWeight2"] - 0.8797) < 0.0001
    assert 'id="adamStepExercise"' in html and 'id="adamStepResult"' in html
    assert "第一步 Adam 的偏差校正會抵銷梯度尺度" in html
    assert "純 SGD 的位移則隨梯度成比例變化" in html
    assert 'id="adamTwoStepExercise"' in html and 'id="adamTwoStepResult"' in html and 'id="adamEpsilon2"' in html
    assert "adam_step_ui_ok" in monitor and "adam_two_step_ui_ok" in monitor and "LESSONS.length === 26" in monitor
    assert "Adam 第一步的偏差校正" in guide
    assert "β₁ 控制有號梯度的歷史記憶；β₂ 控制平方梯度尺度的歷史記憶" in html


def test_weight_decay_comparison_matches_coupled_l2_for_sgd():
    import json
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    start = app.index("function calculateWeightDecayComparison(")
    end = app.index("\nfunction calculateL2CancellationExample", start)
    script = f"const vm=require('vm'); const nodes={{weightDecayGradient:{{value:'0.5'}},weightDecayWeight:{{value:'2'}},weightDecayRate:{{value:'0.1'}},weightDecayStrength:{{value:'0.1'}},weightDecayComparisonResult:{{textContent:''}},adamWeightDecayResult:{{textContent:''}}}}; global.byId=(id)=>nodes[id]; vm.runInThisContext({json.dumps(app[start:end])}); renderWeightDecayComparison(); const renderedDefault=nodes.weightDecayComparisonResult.textContent, adamDefault=nodes.adamWeightDecayResult.textContent; nodes.weightDecayGradient.value='-1'; nodes.weightDecayWeight.value='0.25'; nodes.weightDecayRate.value='0.2'; nodes.weightDecayStrength.value='0.4'; renderWeightDecayComparison(); const renderedChanged=nodes.weightDecayComparisonResult.textContent, adamChanged=nodes.adamWeightDecayResult.textContent; const cases=[[0.5,2,0.1,0.1],[-1,0.25,0.2,0.4],[0,3,0,2]], results=cases.map(x=>calculateWeightDecayComparison(...x)); nodes.weightDecayGradient.value=''; renderWeightDecayComparison(); const adamBlank=nodes.adamWeightDecayResult.textContent; process.stdout.write(JSON.stringify({{results,renderedDefault,renderedChanged,adamDefault,adamChanged,adamBlank,adamCases:[[0.5,2,0.1,0.1],[-1,0.25,0.2,0.4],[0,3,0,2]].map(x=>calculateAdamWeightDecayComparison(...x)),blank:calculateWeightDecayComparison('',2,0.1,0.1),invalid:calculateWeightDecayComparison(1,2,-0.1,0.1),overflow:calculateWeightDecayComparison(1e308,1e308,10,10)}}));"
    result = json.loads(subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True).stdout)
    assert all(abs(item["coupled"] - item["decoupled"]) < 1e-12 for item in result["results"])
    assert result["results"][0]["coupled"] == pytest.approx(1.93)
    assert result["results"][0]["gradientStep"] == pytest.approx(-0.05)
    assert result["results"][0]["decayStep"] == pytest.approx(-0.02)
    assert result["results"][1]["coupled"] == pytest.approx(0.43)
    assert result["results"][1]["difference"] == 0
    assert result["results"][0]["retentionFactor"] == pytest.approx(0.99)
    assert result["results"][1]["retentionFactor"] == pytest.approx(0.92)
    assert "梯度更新量 −ηg=-0.0500；衰減更新量 −ηλw=-0.0200" in result["renderedDefault"]
    assert "方向拆解：梯度更新減少權重，衰減更新減少權重" in result["renderedDefault"]
    assert "梯度更新量 −ηg=0.2000；衰減更新量 −ηλw=-0.0200" in result["renderedChanged"]
    assert "權重保留比例 1−ηλ=0.9200" in result["renderedChanged"]
    assert "耦合 L2 更新 w=0.4300；解耦權重衰減 w=0.4300；差=0.0000" in result["renderedChanged"]
    assert "方向拆解：梯度更新增加權重，衰減更新減少權重" in result["renderedChanged"]
    assert result["blank"] is None and result["invalid"] is None and result["overflow"] is None
    assert result["adamCases"][0]["coupled"] == pytest.approx(1.9)
    assert result["adamCases"][0]["decoupled"] == pytest.approx(1.88)
    assert result["adamCases"][1]["coupled"] == pytest.approx(0.45)
    assert result["adamCases"][1]["decoupled"] == pytest.approx(0.43)
    assert result["adamCases"][2]["coupled"] == pytest.approx(3)
    assert result["adamCases"][2]["decoupled"] == pytest.approx(3)
    assert "Adam 第一步（ε=10⁻⁸）：耦合 L2 w=1.9000；解耦權重衰減 w=1.8800" in result["adamDefault"]
    assert "耦合 L2 w=0.4500；解耦權重衰減 w=0.4300" in result["adamChanged"]
    assert "Adam 對照暫無結果" in result["adamBlank"]
    html = (root / "web/index.html").read_text(encoding="utf-8")
    assert 'id="weightDecayComparisonExercise"' in html
    assert "ε=10⁻⁸" in html and "同一組輸入也會即時計算 Adam 第一步" in html
    epsilon, eta, weight, gradient, penalty = 1e-8, 0.1, 2.0, 0.5, 0.1
    coupled_adam = weight - eta * (gradient + penalty * weight) / (abs(gradient + penalty * weight) + epsilon)
    decoupled_adam = weight - eta * gradient / (abs(gradient) + epsilon) - eta * penalty * weight
    assert f"w={coupled_adam:.4f}" == "w=1.9000"
    assert f"w={decoupled_adam:.4f}" == "w=1.8800"
    assert "weightDecayComparisonExercise" in app and "renderWeightDecayComparison" in app
    assert "if (lessonIndex === weightDecayLessonIndex) renderWeightDecayComparison();" in app
    assert "梯度更新量 −ηg=" in app and "衰減更新量 −ηλw=" in app
    assert "權重保留比例 1−ηλ=" in app and "Number.EPSILON" in app
    assert "function calculateAdamWeightDecayComparison(" in app and "renderAdamWeightDecayComparison();" in app
    assert 'id="adamWeightDecayResult"' in html
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert "weight_decay_checks = guided_fixture(" in monitor and "adamChanged" in monitor and "blankOk" in monitor
    assert "note.includes('同一組輸入也會即時計算 Adam 第一步')" in monitor
    assert "lessonIndex=LESSONS.findIndex(item=>item.title==='正則化梯度會把權重拉向零')" in monitor


def test_l2_regularization_lesson_calculates_data_and_penalty_gradients():
    import json
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "web/app.js").read_text(encoding="utf-8")
    html = (root / "web/index.html").read_text(encoding="utf-8")
    monitor = (root / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    guide = (root / "docs/learning-guide.md").read_text(encoding="utf-8")
    start = app.index("function classifyOpposingGradients(")
    end = app.index("\nfunction renderGradientDescentTrace", start)
    script = f"const vm=require('vm'); const nodes={{l2Weight:{{value:'2'}},l2Rate:{{value:'0.1'}},l2Lambda:{{value:'0.1'}},l2RegularizationResult:{{textContent:''}},l2CancellationSweepResult:{{textContent:''}},l2LossTradeoffExercise:{{textContent:''}}}}; global.byId=(id)=>nodes[id]; vm.runInThisContext({json.dumps(app[start:end])}); renderL2RegularizationExercise(); const renderedDefault=nodes.l2RegularizationResult.textContent, renderedSweep=nodes.l2CancellationSweepResult.textContent, renderedTradeoff=nodes.l2LossTradeoffExercise.textContent; nodes.l2Weight.value='0.5'; nodes.l2Lambda.value='0.5'; renderL2RegularizationExercise(); const renderedDataLeads=nodes.l2RegularizationResult.textContent; nodes.l2Lambda.value='1.5'; renderL2RegularizationExercise(); const renderedPenaltyLeads=nodes.l2RegularizationResult.textContent; nodes.l2Lambda.value='1'; renderL2RegularizationExercise(); const renderedCanceled=nodes.l2RegularizationResult.textContent; nodes.l2Weight.value='2'; nodes.l2Lambda.value='0.1'; nodes.l2Rate.value='2'; renderL2RegularizationExercise(); const renderedOvershoot=nodes.l2RegularizationResult.textContent; nodes.l2Rate.value='0.9090909090909091'; renderL2RegularizationExercise(); const renderedCritical=nodes.l2RegularizationResult.textContent; nodes.l2Rate.value='0.5'; renderL2RegularizationExercise(); const renderedStable=nodes.l2RegularizationResult.textContent; nodes.l2Weight.value='0'; nodes.l2Lambda.value='0'; nodes.l2Rate.value='0.1'; renderL2RegularizationExercise(); const renderedUnchangedPenalty=nodes.l2RegularizationResult.textContent; nodes.l2Weight.value='2'; renderL2RegularizationExercise(); const renderedNoPenalty=nodes.l2RegularizationResult.textContent; process.stdout.write(JSON.stringify({{renderedDefault,renderedSweep,renderedTradeoff,renderedDataLeads,renderedPenaltyLeads,renderedCanceled,renderedOvershoot,renderedCritical,renderedStable,renderedUnchangedPenalty,renderedNoPenalty,defaultCase:calculateL2Regularization(2,0.1,0.1), noPenalty:calculateL2Regularization(2,0.1,0), dataLeads:calculateL2Regularization(0.5,0.1,0.5), penaltyLeads:calculateL2Regularization(0.5,0.1,1.5), canceled:calculateL2Regularization(0.5,0.1,1), overshoot:calculateL2Regularization(2,2,0.1), critical:calculateL2Regularization(2,1/1.1,0.1), stable:calculateL2Regularization(2,0.5,0.1), tinyOpposing:classifyOpposingGradients(2e-13,-1e-13), tinyEqual:classifyOpposingGradients(2e-13,-2e-13), nearCancel:classifyOpposingGradients(2e-13,-2e-13*(1+5e-13)), cancellationExample:calculateL2CancellationExample(), invalidSweep:calculateL2CancellationExample(2.1), blank:calculateL2Regularization('',0.1,0.1), invalid:calculateL2Regularization(2,0.1,-1), overflow:calculateL2Regularization(1e154,0.1,1), overflowDirection:calculateL2Regularization(1e200,0.1,1)}}));"
    result = json.loads(subprocess.run(["node", "-e", script], cwd=root, check=True, capture_output=True, text=True).stdout)
    assert result["defaultCase"]["dataGradient"] == 2
    assert result["defaultCase"]["penaltyGradient"] == 0.4
    assert result["defaultCase"]["totalGradient"] == 2.4
    assert result["defaultCase"]["nextWeight"] == 1.76
    assert result["defaultCase"]["errorMultiplier"] == pytest.approx(0.78)
    assert [item["multiplier"] for item in result["defaultCase"]["stabilitySweep"]] == pytest.approx([0, -1, -2])
    assert [item["behavior"] for item in result["defaultCase"]["stabilitySweep"]] == ["一步到達最低點", "等距反向", "誤差放大"]
    assert "η=0.4545 → 倍率 0.0000（一步到達最低點）" in result["renderedDefault"]
    assert "η=0.9091 → 倍率 -1.0000（等距反向）" in result["renderedDefault"]
    assert "η=1.3636 → 倍率 -2.0000（誤差放大）" in result["renderedDefault"]
    assert result["defaultCase"]["distanceToOptimumBefore"] == pytest.approx(1.0909090909)
    assert result["defaultCase"]["distanceToOptimumAfter"] == pytest.approx(0.8509090909)
    assert result["defaultCase"]["penaltyAfter"] == pytest.approx(0.30976)
    assert result["defaultCase"]["penaltyChange"] == pytest.approx(-0.09024)
    assert round(result["defaultCase"]["totalAfter"], 4) == 0.8874
    assert round(result["defaultCase"]["dataLossChange"], 4) == -0.4224
    assert round(result["defaultCase"]["penaltyChange"], 4) == -0.0902
    assert result["noPenalty"]["nextWeight"] == 1.8
    assert "同向" in result["defaultCase"]["directionNote"]
    assert "λ=0" in result["noPenalty"]["directionNote"]
    assert result["noPenalty"]["optimumWeight"] == 1
    assert "λ=0 時沒有懲罰，最低點仍是資料目標偏好的 w=1" in result["renderedNoPenalty"]
    assert "資料項主導" in result["dataLeads"]["directionNote"]
    assert "懲罰項主導" in result["penaltyLeads"]["directionNote"]
    assert "正好抵銷" in result["canceled"]["directionNote"]
    assert "兩項梯度同向" in result["renderedDefault"]
    assert "距最低點 1.0909→0.8509（有號倍率 0.7800）" in result["renderedDefault"]
    assert "微小梯度比較：0.50 的相對差，資料項主導" in result["renderedDefault"]
    assert "掃描微小梯度的抵銷比例" in result["renderedSweep"]
    assert "總梯度 1.0e-13，0.50 的相對差，資料項主導" in result["renderedSweep"]
    assert "總梯度 0.0e+0，正好抵銷" in result["renderedSweep"]
    assert "近乎抵銷（懲罰/資料梯度比 1.0）" in result["renderedSweep"]
    assert "5.0e-13 的相對差，懲罰項主導" in result["renderedSweep"]
    assert "總梯度 -1.0e-13，0.33 的相對差，懲罰項主導" in result["renderedSweep"]
    assert "梯度下降的權重位移方向與總梯度相反" in result["renderedSweep"]
    assert "ΔLdata=-0.4224" in result["renderedDefault"]
    assert "ΔLpenalty=-0.0902" in result["renderedDefault"]
    assert "合計 ΔL=-0.5126" in result["renderedDefault"]
    assert "損失占比：資料 71.4%、懲罰 28.6%" in result["renderedDefault"]
    assert "梯度貢獻率：資料 83.3%、懲罰 16.7%" in result["renderedDefault"]
    assert "資料項主導合力方向" in result["renderedDataLeads"]
    assert "懲罰項主導合力方向" in result["renderedPenaltyLeads"]
    assert result["renderedTradeoff"] == "固定合成例 w=0.5、η=0.1、λ=0.1：ΔLdata=-0.0819，ΔLpenalty=0.00981。資料損失下降；懲罰上升，但資料項下降較多，所以總損失下降。比較兩項變化量的絕對值，可確認哪一項主導總損失。"
    assert result["renderedTradeoff"] == "固定合成例 w=0.5、η=0.1、λ=0.1：ΔLdata=-0.0819，ΔLpenalty=0.00981。資料損失下降；懲罰上升，但資料項下降較多，所以總損失下降。比較兩項變化量的絕對值，可確認哪一項主導總損失。"
    assert "相反且等大，正好抵銷" in result["renderedCanceled"]
    assert "梯度貢獻率：資料 未定義（總梯度為零）、懲罰 未定義（總梯度為零）" in result["renderedCanceled"]
    assert result["defaultCase"]["lossDirectionNote"] == "資料損失下降；懲罰下降；總損失下降。"
    assert result["overshoot"]["dataLossAfter"] > result["overshoot"]["dataLossBefore"]
    assert result["overshoot"]["totalAfter"] > result["overshoot"]["totalBefore"]
    assert "資料損失上升" in result["renderedOvershoot"] and "總損失上升" in result["renderedOvershoot"]
    assert "η 等於臨界值，誤差每步反號且大小不變" in result["renderedCritical"]
    assert result["critical"]["errorMultiplier"] == pytest.approx(-1)
    assert "有號倍率 -1.0000" in result["renderedCritical"]
    assert result["overshoot"]["errorMultiplier"] == pytest.approx(-3.4)
    assert "η 小於臨界值，這個二次目標的誤差會逐步縮小" in result["renderedStable"]
    assert result["critical"]["criticalRate"] == pytest.approx(1 / 1.1)
    assert result["critical"]["stabilityNote"].startswith("穩定性：η 等於臨界值")
    assert "臨界學習率 η*=1/(1+λ)=0.9091" in result["renderedDefault"]
    assert result["defaultCase"]["optimumWeight"] == pytest.approx(1 / 1.1)
    assert result["defaultCase"]["optimumDataLoss"] == pytest.approx(1 / 121)
    assert result["defaultCase"]["optimumPenalty"] == pytest.approx(10 / 121)
    assert result["defaultCase"]["optimumTotalLoss"] == pytest.approx(1 / 11)
    assert "總目標最低點 w*=1/(1+λ)=0.9091；λ>0 時懲罰會把最低點拉向零，低於資料單獨偏好的 1" in result["renderedDefault"]
    assert "最低點的損失分解：資料 0.0083、懲罰 0.0826、合計 0.0909" in result["renderedDefault"]
    assert "最低點" in html and "w*=1/(1+λ)" in html and "結果會列出最低點的資料損失、懲罰與合計" in html
    assert "λ=0 時仍是資料目標偏好的 w=1" in html
    assert "lambdaZero:noPenalty.includes" in monitor
    assert "合計 ΔL=+" in result["renderedOvershoot"]
    assert "資料損失下降；懲罰不變；總損失下降。" in result["renderedUnchangedPenalty"]
    mixed = json.loads(subprocess.run(["node", "-e", f"const vm=require('vm'); vm.runInThisContext({json.dumps(app[start:end])}); process.stdout.write(JSON.stringify(calculateL2Regularization(0.5,0.1,0.1)));"], cwd=root, check=True, capture_output=True, text=True).stdout)
    assert mixed["dataLossChange"] < 0 < mixed["penaltyChange"]
    assert mixed["totalAfter"] < mixed["totalBefore"]
    assert "資料損失下降；懲罰上升" in mixed["lossDirectionNote"]
    assert "資料項下降較多" in mixed["lossDirectionNote"]
    assert result["blank"] is None and result["invalid"] is None and result["overflow"] is None
    assert result["overflowDirection"] is None
    assert result["tinyOpposing"] == "data" and result["tinyEqual"] == "cancel"
    assert result["nearCancel"] == "penalty"
    assert "近乎抵銷（懲罰/資料梯度比 1.0）" in result["renderedSweep"]
    assert "5.0e-13 的相對差，懲罰項主導" in result["renderedSweep"]
    assert result["cancellationExample"]["relativeDifference"] == 0.5
    assert result["cancellationExample"]["classification"] == "data"
    assert result["invalidSweep"] is None
    assert "資料項主導" in result["renderedDefault"]
    assert 'id="l2RegularizationExercise"' in html and "第 1 / 26 步" in html
    assert "l2_regularization_ui_ok" in monitor and "LESSONS.length === 26" in monitor
    assert "λ>0 時懲罰會把最低點拉向零，低於資料單獨偏好的 1" in monitor
    assert "最低點的損失分解：資料 0.0083、懲罰 0.0826、合計 0.0909" in monitor
    assert "window.__l2LessonChecks=clauses" in monitor
    assert "l2_lesson_failures" in monitor and "失敗子句={l2_lesson_failures}" in monitor
    assert "先比較兩項損失占比" in html and "損失占比：資料 71.4%、懲罰 28.6%" in monitor
    assert "梯度貢獻率：資料 83.3%、懲罰 16.7%" in monitor
    assert "資料項主導合力方向" in monitor and "懲罰項主導合力方向" in monitor
    assert "l2CancellationSweepResult" in html and "掃描微小梯度的抵銷比例" in html
    assert 'id="l2LossTradeoffExercise"' in html and "比較兩項變化量的絕對值" in html
    assert "掃描反向懲罰梯度的比例" in guide and "總梯度 `1×10⁻¹³`" in guide
    assert "L2 正則化" in app and "λw²" in guide
    assert "臨界學習率 η*=1/(1+λ)" in app and "learningRateStability" in monitor
    assert "η*=1/(1+λ)" in guide and "二次目標" in guide


def test_guided_lesson_monitor_lengths_match_current_catalog():
    from pathlib import Path

    monitor = (Path(__file__).resolve().parents[1] / "scripts/regression_monitor.py").read_text(encoding="utf-8")
    assert "LESSONS.length===25" not in monitor
    assert monitor.count("LESSONS.length===26") == 4
