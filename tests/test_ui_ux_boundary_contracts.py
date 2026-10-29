from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _extract_helpers(source: str, functions: list[tuple[str, str]]) -> str:
    extracted = []
    for name, next_name in functions:
        start = source.index(f"function {name}(")
        end = source.index(f"function {next_name}(", start)
        extracted.append(source[start:end])
    return "\n".join(extracted)


def test_magnitude_reference_boundary_and_extreme_values():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [("calculateMagnitudeReference", "renderTensorShapeExercise")])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const zeroReturn = calculateMagnitudeReference(100, 0, 'simple');
      const positiveReturn = calculateMagnitudeReference(100, 5, 'simple');
      const negativeReturn = calculateMagnitudeReference(100, -5, 'simple');
      const simpleDrop100 = calculateMagnitudeReference(100, -100, 'simple');
      const simpleDrop101 = calculateMagnitudeReference(100, -101, 'simple');
      const logDrop101 = calculateMagnitudeReference(100, -101, 'log');
      const hugeReturn = calculateMagnitudeReference(100, 1000, 'simple');
      const zeroPrice = calculateMagnitudeReference(0, 5, 'simple');
      const negativePrice = calculateMagnitudeReference(-10, 5, 'simple');
      const nanPrice = calculateMagnitudeReference('NaN', 5, 'simple');
      const emptyPrice = calculateMagnitudeReference('  ', 5, 'simple');
      const overflowLog = calculateMagnitudeReference(100, 1000000, 'log');

      process.stdout.write(JSON.stringify({{
        zeroReturn,
        positiveReturn,
        negativeReturn,
        simpleDrop100,
        simpleDrop101,
        logDrop101,
        hugeReturn,
        zeroPrice,
        negativePrice,
        nanPrice,
        emptyPrice,
        overflowLog
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # 零報酬邊界：方向為持平，幅度為 0
    assert res["zeroReturn"]["direction"] == "持平"
    assert res["zeroReturn"]["magnitude"] == 0
    assert res["zeroReturn"]["value"] == 100

    # 正負報酬方向
    assert res["positiveReturn"]["direction"] == "上漲"
    assert res["positiveReturn"]["value"] == 105
    assert res["negativeReturn"]["direction"] == "下跌"
    assert res["negativeReturn"]["value"] == 95

    # 簡單報酬邊界：-100% 及低於 -100% 嚴格拒絕（報酬不可低於 -100%）
    assert res["simpleDrop100"] is None
    assert res["simpleDrop101"] is None

    # 對數報酬邊界：連續複利下 -101% 為合法下跌
    assert res["logDrop101"]["direction"] == "下跌"
    assert res["logDrop101"]["magnitude"] == 101
    assert abs(res["logDrop101"]["value"] - (100 * 2.718281828459045 ** (-1.01))) < 1e-4

    # 大數正報酬邊界：+1000% 點位放大 11 倍
    assert res["hugeReturn"]["value"] == 1100

    # 非法價格邊界拒絕
    assert res["zeroPrice"] is None
    assert res["negativePrice"] is None
    assert res["nanPrice"] is None
    assert res["emptyPrice"] is None
    assert res["overflowLog"] is None


def test_prediction_interval_boundary_and_extreme_spreads():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [("calculatePredictionInterval", "renderPredictionIntervalExample")])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const zeroSpread = calculatePredictionInterval(1.5, 0);
      const normal = calculatePredictionInterval(1.5, 0.5);
      const negativeCenter = calculatePredictionInterval(-2.5, 0.5);
      const negativeSpread = calculatePredictionInterval(1.5, -0.01);
      const emptyCenter = calculatePredictionInterval(' ', 0.5);
      const nanSpread = calculatePredictionInterval(1.5, 'abc');
      const precision = calculatePredictionInterval(0.123456789012, 0.000000000001);

      process.stdout.write(JSON.stringify({{
        zeroSpread,
        normal,
        negativeCenter,
        negativeSpread,
        emptyCenter,
        nanSpread,
        precision
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # 零誤差尺度：上下界與中心相同
    assert res["zeroSpread"] == {"lower": 1.5, "upper": 1.5}

    # 一般區間
    assert res["normal"] == {"lower": 1.0, "upper": 2.0}

    # 負報酬預測中心
    assert res["negativeCenter"] == {"lower": -3.0, "upper": -2.0}

    # 負誤差尺度或無效輸入嚴格拒絕
    assert res["negativeSpread"] is None
    assert res["emptyCenter"] is None
    assert res["nanSpread"] is None

    # 高精度小數點截斷保持 12 位
    assert res["precision"]["lower"] == 0.123456789011
    assert res["precision"]["upper"] == 0.123456789013


def test_prediction_interval_renderer_explains_scale_to_width_relationship():
    source = (ROOT / "web" / "app.js").read_text()
    renderer = _extract_helpers(source, [("calculatePredictionInterval", "renderPredictionIntervalExample"), ("renderPredictionIntervalExample", "calculateGradientStep")])
    html = (ROOT / "web" / "index.html").read_text()
    assert 'id="intervalWidthReading"' in html
    script = f"""
      const vm = require('vm');
      const nodes = {{
        predictionIntervalResult: {{textContent: ''}}, intervalCenter: {{value: '0.6'}},
        intervalSpread: {{value: '0.4'}}, intervalWidthReading: {{textContent: ''}},
        intervalViz: null
      }};
      global.byId = (id) => nodes[id] || null;
      vm.runInThisContext({json.dumps(renderer)});
      renderPredictionIntervalExample();
      const first = nodes.intervalWidthReading.textContent;
      nodes.intervalSpread.value = '0.8';
      renderPredictionIntervalExample();
      process.stdout.write(JSON.stringify({{first, second: nodes.intervalWidthReading.textContent}}));
    """
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"})
    result = json.loads(completed.stdout)
    assert "尺度 0.40 個百分點 → 寬度 0.80 個百分點" in result["first"]
    assert "尺度加倍時寬度也加倍，中心不變" in result["first"]
    assert "尺度 0.80 個百分點 → 寬度 1.60 個百分點" in result["second"]


def test_activation_comparison_asymptotic_and_zero_limits():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [("calculateActivationComparison", "renderActivationExercise")])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const atZero = calculateActivationComparison(0);
      const largePositive = calculateActivationComparison(50);
      const largeNegative = calculateActivationComparison(-50);
      const invalid = calculateActivationComparison('');
      const nanInput = calculateActivationComparison('abc');

      process.stdout.write(JSON.stringify({{
        atZero,
        largePositive,
        largeNegative,
        invalid,
        nanInput
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # z = 0 原點邊界
    assert res["atZero"]["sigmoid"] == 0.5
    assert res["atZero"]["sigmoidGradient"] == 0.25
    assert res["atZero"]["relu"] == 0
    assert res["atZero"]["reluGradient"] == 0
    assert res["atZero"]["tanh"] == 0
    assert res["atZero"]["tanhGradient"] == 1.0

    # z = +50 正漸近極限
    assert res["largePositive"]["sigmoid"] == 1.0
    assert res["largePositive"]["sigmoidGradient"] < 1e-15
    assert res["largePositive"]["relu"] == 50.0
    assert res["largePositive"]["reluGradient"] == 1.0
    assert res["largePositive"]["tanh"] == 1.0
    assert res["largePositive"]["tanhGradient"] < 1e-15

    # z = -50 負漸近極限
    assert res["largeNegative"]["sigmoid"] < 1e-15
    assert res["largeNegative"]["relu"] == 0.0
    assert res["largeNegative"]["reluGradient"] == 0.0
    assert res["largeNegative"]["tanh"] == -1.0
    assert res["largeNegative"]["tanhGradient"] < 1e-15

    # 無效輸入防呆
    assert res["invalid"] is None
    assert res["nanInput"] is None


def test_gradient_step_and_quadratic_loss_boundary_conditions():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [
        ("calculateGradientStep", "calculateQuadraticLoss"),
        ("calculateQuadraticLoss", "renderGradientExercise")
    ])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const zeroRate = calculateGradientStep(2.0, 1.5, 0);
      const maxRate = calculateGradientStep(2.0, 1.5, 10);
      const overRate = calculateGradientStep(2.0, 1.5, 10.001);
      const negativeRate = calculateGradientStep(2.0, 1.5, -0.01);
      const zeroGrad = calculateGradientStep(2.0, 0, 0.1);
      const exactTargetLoss = calculateQuadraticLoss(1.0, 1.0);
      const normalLoss = calculateQuadraticLoss(3.0, 1.0);

      process.stdout.write(JSON.stringify({{
        zeroRate,
        maxRate,
        overRate,
        negativeRate,
        zeroGrad,
        exactTargetLoss,
        normalLoss
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    assert res["zeroRate"] == 2.0  # 步長為 0，權重完全不變
    assert res["maxRate"] == -13.0  # 2 - 10 * 1.5 = -13
    assert res["overRate"] is None  # 超過上限 10 拒絕
    assert res["negativeRate"] is None  # 負學習率拒絕
    assert res["zeroGrad"] == 2.0  # 梯度為 0 權重不變
    assert res["exactTargetLoss"] == 0.0  # 權重等於目標時損失為 0
    assert res["normalLoss"] == 4.0  # (3 - 1)^2 = 4


def test_batch_gradient_cancellation_and_spread_bounds():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [("calculateBatchGradientUpdate", "renderBatchGradientExercise")])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const balanced = calculateBatchGradientUpdate(2.0, [-2, 2, -1, 1], 0.1);
      const allZero = calculateBatchGradientUpdate(2.0, [0, 0, 0, 0], 0.1);
      const rateOne = calculateBatchGradientUpdate(2.0, [1, 1, 1, 1], 1.0);
      const rateOver = calculateBatchGradientUpdate(2.0, [1, 1, 1, 1], 1.01);
      const rateNegative = calculateBatchGradientUpdate(2.0, [1, 1, 1, 1], -0.01);
      const shortList = calculateBatchGradientUpdate(2.0, [1, 1, 1], 0.1);
      const longList = calculateBatchGradientUpdate(2.0, [1, 1, 1, 1, 1], 0.1);

      process.stdout.write(JSON.stringify({{
        balanced,
        allZero,
        rateOne,
        rateOver,
        rateNegative,
        shortList,
        longList
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # 完整對稱抵銷：平均為 0，權重保持 2.0
    assert res["balanced"]["average"] == 0.0
    assert res["balanced"]["total"] == 0.0
    assert res["balanced"]["updated"] == 2.0
    assert res["balanced"]["positiveCount"] == 2
    assert res["balanced"]["negativeCount"] == 2
    assert res["balanced"]["zeroCount"] == 0
    assert res["balanced"]["minGradient"] == -2
    assert res["balanced"]["maxGradient"] == 2

    # 全零梯度
    assert res["allZero"]["average"] == 0.0
    assert res["allZero"]["zeroCount"] == 4

    # 學習率邊界
    assert res["rateOne"]["updated"] == 1.0  # 2 - 1 * 1 = 1
    assert res["rateOver"] is None
    assert res["rateNegative"] is None

    # 樣本數必須嚴格等於 4
    assert res["shortList"] is None
    assert res["longList"] is None


def test_momentum_update_extreme_beta_and_opposing_velocity():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [("calculateMomentumUpdate", "renderMomentumExercise")])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const noBeta = calculateMomentumUpdate(0, 5.0, 1.0, 2.0, 0.1);
      const fullBeta = calculateMomentumUpdate(1.0, 5.0, 1.0, 2.0, 0.1);
      const cancelVelocity = calculateMomentumUpdate(0.5, -2.0, 1.0, 2.0, 0.1);
      const invalidBeta = calculateMomentumUpdate(1.01, 1.0, 1.0, 2.0, 0.1);
      const negativeBeta = calculateMomentumUpdate(-0.1, 1.0, 1.0, 2.0, 0.1);
      const invalidRate = calculateMomentumUpdate(0.9, 1.0, 1.0, 2.0, 1.01);

      process.stdout.write(JSON.stringify({{
        noBeta,
        fullBeta,
        cancelVelocity,
        invalidBeta,
        negativeBeta,
        invalidRate
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # beta = 0：無前一步速度保留，v = g = 1.0，w = 2.0 - 0.1 * 1.0 = 1.9
    assert res["noBeta"]["velocity"] == 1.0
    assert res["noBeta"]["updated"] == 1.9

    # beta = 1：100% 保留速度，v = 5.0 + 1.0 = 6.0，w = 2.0 - 0.1 * 6.0 = 1.4
    assert res["fullBeta"]["velocity"] == 6.0
    assert res["fullBeta"]["updated"] == 1.4

    # 反向動量剛好抵銷本步梯度：0.5 * (-2) + 1 = 0，權重完全不變
    assert res["cancelVelocity"]["velocity"] == 0.0
    assert res["cancelVelocity"]["updated"] == 2.0

    # 邊界檢驗防呆
    assert res["invalidBeta"] is None
    assert res["negativeBeta"] is None
    assert res["invalidRate"] is None


def test_vector_gradient_clipping_bounds_and_zero_limits():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [
        ("calculateVectorGradientClipping", "calculateVectorGradientClipping3"),
        ("calculateVectorGradientClippingN", "renderVectorGradientClipping4")
    ])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const zeroVector = calculateVectorGradientClippingN([0, 0, 0, 0], 2.0);
      const exactNorm = calculateVectorGradientClippingN([1, 1, 1, 1], 2.0);
      const clippedNorm = calculateVectorGradientClippingN([3, 0, 4, 0], 2.0);
      const zeroLimit = calculateVectorGradientClippingN([1, 2, 2, 4], 0);
      const negativeLimit = calculateVectorGradientClippingN([1, 2, 2, 4], -1);
      const emptyComponents = calculateVectorGradientClippingN([], 2.0);
      const oversized = calculateVectorGradientClippingN(Array(65).fill(1), 2.0);

      process.stdout.write(JSON.stringify({{
        zeroVector,
        exactNorm,
        clippedNorm,
        zeroLimit,
        negativeLimit,
        emptyComponents,
        oversized
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # 零向量：norm = 0，scale = 1，不發生除以零
    assert res["zeroVector"]["norm"] == 0
    assert res["zeroVector"]["scale"] == 1
    assert res["zeroVector"]["clipped"] == [0, 0, 0, 0]

    # 剛好等於上限：norm = sqrt(4) = 2.0 == limit，scale = 1
    assert abs(res["exactNorm"]["norm"] - 2.0) < 1e-12
    assert res["exactNorm"]["scale"] == 1

    # 超出上限：norm = sqrt(3^2 + 4^2) = 5.0 > 2.0，scale = 2.0 / 5.0 = 0.4
    assert res["clippedNorm"]["norm"] == 5.0
    assert res["clippedNorm"]["scale"] == 0.4
    assert res["clippedNorm"]["clipped"] == pytest.approx([1.2, 0.0, 1.6, 0.0])
    assert abs(res["clippedNorm"]["clippedNorm"] - 2.0) < 1e-12
    # 分量裁剪獨立夾取至 [-2, 2]
    assert res["clippedNorm"]["componentClipped"] == [2.0, 0.0, 2.0, 0.0]

    # limit = 0：全部裁剪為 0
    assert res["zeroLimit"]["clippedNorm"] == 0.0
    assert res["zeroLimit"]["componentClippedNorm"] == 0.0

    # 非法 limit 與維度邊界防呆
    assert res["negativeLimit"] is None
    assert res["emptyComponents"] is None
    assert res["oversized"] is None


def test_return_magnitude_comparison_and_zero_baseline_ties():
    source = (ROOT / "web" / "app.js").read_text()
    helpers = _extract_helpers(source, [
        ("compareReturnMagnitude", "compareMagnitudeToZeroBaseline"),
        ("compareMagnitudeToZeroBaseline", "renderMagnitudeErrorExercise")
    ])
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      
      const exactMatch = compareMagnitudeToZeroBaseline(0.5, 0.5);
      const oppositeSameMagnitude = compareMagnitudeToZeroBaseline(0.2, -0.2);
      const zeroPredActual = compareMagnitudeToZeroBaseline(0, -0.2);
      const bothZero = compareMagnitudeToZeroBaseline(0, 0);
      const overEstimate = compareMagnitudeToZeroBaseline(0.8, 0.3);
      const underEstimate = compareMagnitudeToZeroBaseline(0.1, 0.4);

      process.stdout.write(JSON.stringify({{
        exactMatch,
        oppositeSameMagnitude,
        zeroPredActual,
        bothZero,
        overEstimate,
        underEstimate
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    res = json.loads(completed.stdout)

    # 完全吻合：超越零基準
    assert res["exactMatch"]["sameDirection"] is True
    assert res["exactMatch"]["signedErrorPp"] == 0.0
    assert res["exactMatch"]["errorPp"] == 0.0
    assert res["exactMatch"]["magnitudeBias"] == "預測絕對幅度相同"
    assert res["exactMatch"]["beatsZeroBaseline"] is True

    # 方向相反但絕對幅度相同（+0.2% vs -0.2%）：
    # 預測誤差為 |0.2 - (-0.2)| = 0.4pp，而零基準誤差僅 |-0.2| = 0.2pp。
    # 故方向錯誤時其誤差比零基準更差（0.4pp > 0.2pp），不勝也不平零基準
    assert res["oppositeSameMagnitude"]["sameDirection"] is False
    assert abs(res["oppositeSameMagnitude"]["signedErrorPp"] - 0.4) < 1e-12
    assert abs(res["oppositeSameMagnitude"]["errorPp"] - 0.4) < 1e-12
    assert res["oppositeSameMagnitude"]["magnitudeBias"] == "預測絕對幅度相同"
    assert res["oppositeSameMagnitude"]["beatsZeroBaseline"] is False
    assert res["oppositeSameMagnitude"]["tiesZeroBaseline"] is False

    # 預測恰為 0：誤差與零基準完全一致（平局）
    assert res["zeroPredActual"]["tiesZeroBaseline"] is True

    # 兩者皆為 0
    assert res["bothZero"]["sameDirection"] is True
    assert res["bothZero"]["signedErrorPp"] == 0.0
    assert res["bothZero"]["tiesZeroBaseline"] is True

    # 高估與低估幅度偏差
    assert res["overEstimate"]["magnitudeBias"] == "預測絕對幅度較大"
    assert res["underEstimate"]["magnitudeBias"] == "預測絕對幅度較小"


def test_paper_agent_consent_checkbox_stays_compact_in_drawer():
    css = (ROOT / "web" / "paper.css").read_text()
    # Drawer controls are generally full width. This more specific checkbox
    # rule prevents the flex label from squeezing its copy into a vertical rail.
    assert '.drawer-content input:not([type=radio]),.drawer-content select{width:100%' in css
    selector = '.drawer-content .agent-auto-choice>input[type="checkbox"]{'
    assert selector in css
    checkbox_rule = css.split(selector, 1)[1].split("}", 1)[0]
    assert "flex:0 0 18px" in checkbox_rule
    assert "width:18px" in checkbox_rule
    assert '.drawer-content .agent-auto-choice>span{flex:1 1 auto;min-width:0' in css
