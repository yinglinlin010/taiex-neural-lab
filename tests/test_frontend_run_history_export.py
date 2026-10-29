from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _archive(rows):
    source = (ROOT / "web" / "app.js").read_text()
    start = source.index("function isValidRunHistoryRecord(")
    end = source.index("function exportRunHistory(", start)
    script = f"""
      const vm = require('vm');
      vm.runInThisContext('const MAX_RUN_HISTORY=20;\\n' + {json.dumps(source[start:end])});
      const rows = JSON.parse(process.env.RUN_ROWS);
      process.stdout.write(JSON.stringify(buildRunHistoryArchive(rows, '2026-10-25T00:00:00.000Z')));
    """
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "RUN_ROWS": json.dumps(rows)},
    )
    return json.loads(result.stdout)


def test_archive_empty_and_non_array_input_has_stable_schema():
    empty = _archive([])
    invalid = _archive({"runs": []})

    assert empty["schemaVersion"] == 1
    assert empty["runCount"] == 0
    assert empty["runs"] == []
    assert invalid["runCount"] == 0


def test_archive_filters_malformed_records_and_normalizes_non_finite_metrics():
    archive = _archive([
        None,
        {"id": "missing-config", "models": []},
        {"createdAt": "2026-10-25", "config": {}, "models": [{"key": "rnn"}]},
        {"id": "missing-model", "createdAt": "2026-10-25", "config": {}, "models": []},
        {"id": "invalid-date", "createdAt": "not-a-date", "config": {}, "models": [{"key": "rnn"}]},
        {
            "id": "run-1",
            "createdAt": "2026-10-24T12:00:00Z",
            "datasetHash": "abc123",
            "samples": None,
            "config": {"symbol": "TAIEX", "horizon": 5, "lookback": 20, "modelTypes": ["rnn", "gru"],
                       "features": ["return_1", {"private": True}],
                       "hiddenSizes": [32, "NaN", None], "lockedTest": {"score": 0.99}, "unexpected": "drop"},
            "models": [None, {"key": "gru", "mae": "NaN", "rmse": 0.02, "r2": None,
                              "folds": [None, {"fold": 1, "from": "2026-01-01", "to": "2026-02-01", "mae": 0.01}]}],
            "lockedTest": {"private": "must not be exported"},
        },
    ])

    assert archive["runCount"] == 1
    run = archive["runs"][0]
    assert run["config"] == {"symbol": "TAIEX", "horizon": 5, "lookback": 20, "modelTypes": ["rnn", "gru"],
                             "features": ["return_1"], "hiddenSizes": [32]}
    assert run["samples"] is None
    assert "lockedTest" not in run
    assert len(run["models"]) == 1
    assert run["models"][0]["mae"] is None
    assert run["models"][0]["rmse"] == 0.02
    assert run["models"][0]["r2"] is None
    assert run["models"][0]["folds"] == [
        {"fold": 1, "from": "2026-01-01", "to": "2026-02-01", "mae": 0.01, "rmse": None}
    ]
    assert "鎖定測試結果" in archive["note"]


def test_archive_caps_to_the_documented_twenty_runs():
    rows = [{"id": str(i), "createdAt": "2026-10-25T00:00:00Z", "config": {},
             "models": [{"key": "rnn"}]} for i in range(25)]
    archive = _archive(rows)

    assert archive["runCount"] == 20
    assert len(archive["runs"]) == 20
    assert archive["runs"][0]["id"] == "0"
    assert archive["runs"][-1]["id"] == "19"


def test_download_filename_date_uses_local_calendar_date():
    source = (ROOT / "web" / "app.js").read_text()
    start = source.index("function localDateStamp(")
    end = source.index("function renderRunHistory(", start)
    script = f"""
      const vm = require('vm');
      vm.runInThisContext({json.dumps(source[start:end])});
      process.stdout.write(localDateStamp(new Date('2025-12-31T16:30:00.000Z')));
    """
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "TZ": "Asia/Taipei"},
    )
    assert completed.stdout == "2026-01-01"


def test_history_table_renders_untrusted_model_names_as_text():
    source = (ROOT / "web" / "app.js").read_text()
    helpers_start = source.index("function isValidRunHistoryRecord(")
    render_start = source.index("function renderRunHistory(")
    end = source.index("function recordValidationRun(", render_start)
    malicious_name = "</strong><img src=x onerror=alert(1)>"
    script = f"""
      const vm = require('vm');
      class FakeNode {{
        constructor() {{ this.children=[]; this.dataset={{}}; }}
        replaceChildren(...children) {{ this.children=children; }}
        insertRow() {{ const row=new FakeNode(); this.children.push(row); return row; }}
        insertCell() {{ const cell=new FakeNode(); this.children.push(cell); return cell; }}
        append(...children) {{ this.children.push(...children); }}
        set innerHTML(value) {{ this.rawHTML=value; this.children=[]; }}
      }}
      const source={json.dumps(source[helpers_start:render_start] + source[render_start:end])};
      const setup=`const MAX_RUN_HISTORY=20; const MODEL_LABELS={{}};\n`+
        `const elements={{runHistoryRows:new FakeNode(),exportRunHistory:new FakeNode()}};\n`+
        `const document={{createElement:()=>new FakeNode()}};\n`+
        `const RUN_HISTORY_KEY='history'; const localStorage={{getItem:()=>process.env.RUN_ROWS}};\n`+
        `const byId=(id)=>elements[id];\n`+
        ``;
      const context={{FakeNode,process,Date,JSON,Object,Number,Array,String}};
      vm.runInNewContext(setup + source + 'renderRunHistory(); process.stdout.write(JSON.stringify({{html:Object.hasOwn(elements.runHistoryRows,"rawHTML"), name:elements.runHistoryRows.children[0].children[1].children[0].textContent, rowIndex:elements.runHistoryRows.children[0].children[5].children[0].dataset.runIndex, rowCount:elements.runHistoryRows.children.length}}));', context);
    """
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "RUN_ROWS": json.dumps([None, {"id": "x", "createdAt": "2026-10-25", "config": {},
                                                         "models": [{"key": "rnn", "name": malicious_name}]}])},
    )
    result = json.loads(completed.stdout)
    assert result == {"html": False, "name": malicious_name, "rowIndex": "0", "rowCount": 1}


def test_history_read_fails_closed_when_storage_is_blocked_or_corrupt():
    source = (ROOT / "web" / "app.js").read_text()
    start = source.index("function isValidRunHistoryRecord(")
    end = source.index("function renderRunHistory(", start)
    script = f"""
      const vm = require('vm');
      const source = {json.dumps(source[start:end])};
      const values = [new Error('blocked'), '{{broken json', '{{"runs":[]}}', '[{{"id":"ok","createdAt":"2026-10-25","config":{{}},"models":[{{"key":"rnn"}}]}}]'];
      const context = {{
        RUN_HISTORY_KEY: 'history',
        localStorage: {{getItem: () => {{ const value=values.shift(); if(value instanceof Error) throw value; return value; }}}},
        JSON, Array
      }};
      process.stdout.write(JSON.stringify(vm.runInNewContext(source + '\\n[readRunHistory(),readRunHistory(),readRunHistory(),readRunHistory()]', context)));
    """
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=os.environ,
    )
    assert json.loads(completed.stdout) == [[], [], [], [{"id": "ok", "createdAt": "2026-10-25", "config": {}, "models": [{"key": "rnn"}]}]]
