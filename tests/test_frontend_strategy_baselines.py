from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_time_series_momentum_baseline_is_causal_and_executes_next_close():
    source = (ROOT / "web" / "app.js").read_text()
    start = source.index("function timeSeriesMomentumSignals(")
    end = source.index("function firstLastIntervalDates(", start)
    replay_start = source.index("function replayFixedSignals(")
    replay_end = source.index("function replayOofSignals(", replay_start)
    helpers = source[start:end] + source[replay_start:replay_end]
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helpers)});
      const original = [100, 100, 110, 121, 100, 90].map(close => ({{close}}));
      const signals = timeSeriesMomentumSignals(original, 2);
      const changedFuture = original.map(row => ({{...row}}));
      changedFuture[4].close = 1000;
      changedFuture[5].close = 1;
      const futureSignals = timeSeriesMomentumSignals(changedFuture, 2);
      const replay = replayFixedSignals(original, signals, 3, 5, 0.001425, 0.004425);
      process.stdout.write(JSON.stringify({{
        keys: [...signals.keys()],
        decisions: [...signals.values()],
        causal: signals.get(3) === futureSignals.get(3),
        replay
      }}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    result = json.loads(completed.stdout)

    assert result["keys"] == [2, 3, 4, 5]
    assert result["decisions"] == [True, True, False, False]
    assert result["causal"] is True
    # Signal at origin index 2 first enters at close 3; it then exits at close 5.
    expected = (1 - 0.001425) * (100 / 121) * (90 / 100) * (1 - 0.004425)
    assert abs(result["replay"]["equity"] - expected) < 1e-12
    assert result["replay"]["trades"] == 2
