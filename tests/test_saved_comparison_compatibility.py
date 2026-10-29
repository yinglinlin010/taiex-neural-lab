from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_saved_cross_asset_comparison_fails_closed_on_incompatible_protocols():
    source = (ROOT / "web" / "app.js").read_text()
    assert "record.result.execution || null" in source
    assert "compatibility.className = 'saved-comparison-compatibility'" in source
    assert "compatibility.setAttribute('role', 'status')" in source
    assert "compatibility.textContent = savedComparisonCompatibility(records)" in source
    start = source.index("function savedComparisonCompatibility(")
    end = source.index("async function renderSavedCrossAssetComparison(", start)
    helper = source[start:end]
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(helper)});
      const base = {{available:true,execution:'next_close',horizon:1,returnType:'simple',period:'2024-01-01 至 2024-02-01',model:'GRU',setupSignature:'same'}};
      const legacy = {{...base,execution:null}};
      const horizonMismatch = {{...base,horizon:5}};
      const setupMismatch = {{...base,setupSignature:'different'}};
      const featuresMismatch = {{...base,setupSignature:'different features'}};
      const compatible = savedComparisonCompatibility([base,{{...base}}]);
      const legacyStatus = savedComparisonCompatibility([legacy,base]);
      const horizonStatus = savedComparisonCompatibility([base,horizonMismatch]);
      const setupStatus = savedComparisonCompatibility([base,setupMismatch]);
      const missing = savedComparisonCompatibility([base,{{available:false}}]);
      process.stdout.write(JSON.stringify({{compatible,legacyStatus,horizonStatus,setupStatus,featuresStatus:savedComparisonCompatibility([base,featuresMismatch]),missing}}));
    """
    completed = subprocess.run(
        ["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
        env={**os.environ, "NODE_NO_WARNINGS": "1"},
    )
    result = json.loads(completed.stdout)

    assert result["compatible"].startswith("目標協定、模型、訓練設定")
    assert "不可直接排名" in result["legacyStatus"]
    assert "未保存 next-close 目標協定" in result["legacyStatus"]
    assert "不可直接排名" in result["horizonStatus"]
    assert "預測期間不同或未保存" in result["horizonStatus"]
    assert "不可直接排名" in result["setupStatus"]
    assert "訓練設定不同或未保存" in result["setupStatus"]
    assert "含特徵與回看日數" in result["featuresStatus"]
    assert "缺少兩份可用" in result["missing"]
