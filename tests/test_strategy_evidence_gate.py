from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _evaluate(model, benchmarks, trades):
    source = (ROOT / "web" / "app.js").read_text()
    start = source.index("function evaluateStrategyEvidence(")
    end = source.index("function timeSeriesMomentumSignals(", start)
    script = f"""
      const vm=require('vm');
      vm.runInThisContext({json.dumps(source[start:end])});
      process.stdout.write(JSON.stringify(evaluateStrategyEvidence(
        {json.dumps(model)}, {json.dumps(benchmarks)}, {json.dumps(trades)}
      )));
    """
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True,
                            text=True, check=True)
    return json.loads(result.stdout)


def test_evidence_gate_requires_strictly_beat_every_after_cost_benchmark():
    benchmark_set = [{"name": "均線", "equity": 1.1}, {"name": "買入持有", "equity": 1.2}]
    assert _evaluate(1.21, benchmark_set, 30) == {
        "complete": True, "underperforming": [], "enoughTrades": True,
    }
    assert _evaluate(1.2, benchmark_set, 30)["underperforming"] == ["買入持有"]
    assert _evaluate(1.0, benchmark_set, 42)["underperforming"] == ["均線", "買入持有"]


@pytest.mark.parametrize("trades,expected", [(0, False), (29, False), (30, True), (30.5, False), (None, False)])
def test_evidence_gate_trade_count_boundary(trades, expected):
    result = _evaluate(1.5, [{"name": "cash", "equity": 1.0}], trades)
    assert result["enoughTrades"] is expected


@pytest.mark.parametrize("model,benchmarks", [
    (None, [{"name": "cash", "equity": 1}]),
    (1.2, []),
    (1.2, [{"name": "broken", "equity": None}]),
])
def test_evidence_gate_fails_closed_on_missing_or_non_finite_results(model, benchmarks):
    assert _evaluate(model, benchmarks, 100) == {
        "complete": False, "underperforming": [], "enoughTrades": False,
    }
