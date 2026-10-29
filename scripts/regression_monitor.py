#!/usr/bin/env python3
"""Run a safe, local regression and visual check for the TAIEX learning lab."""

from __future__ import annotations

import fcntl
import difflib
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE_URL = os.environ.get("TAIEX_LAB_URL", "http://127.0.0.1:8000").rstrip("/")
STATE_PATH = ROOT / "data" / "regression-monitor-state.json"
LOCK_PATH = ROOT / "data" / "regression-monitor.lock"
SOURCE_SNAPSHOT_PATH = ROOT / "data" / "regression-monitor-sources.json"
ARTIFACTS = ROOT / "artifacts" / "regression-monitor"
REFERENCE = ROOT / ".impeccable" / "mocks" / "sequence-first.png"
BEGIN = "<!-- regression-monitor:latest:start -->"
END = "<!-- regression-monitor:latest:end -->"
SOURCE_GLOBS = ("app/*.py", "web/index.html", "web/app.js", "web/styles.css", "tests/*.py", "scripts/*.py", "requirements.txt")
FINAL_STATE_GLOB = "final-test-*.json"


def final_state_paths() -> tuple[str, ...]:
    """Return holdout state path names without opening the protected files."""
    return tuple(str(path.relative_to(ROOT)) for path in sorted((ROOT / "data").glob(FINAL_STATE_GLOB)) if path.is_file())


def now() -> datetime:
    return datetime.now().astimezone()


def iso_time() -> str:
    return now().isoformat(timespec="seconds")


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def check_http() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    checks: list[dict[str, Any]] = []
    status_data = None
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
            ok = response.status == 200 and "序列觀測站" in html
            checks.append({"name": "首頁 HTTP", "status": "PASS" if ok else "FAIL", "detail": f"HTTP {response.status}; app title {'found' if '序列觀測站' in html else 'missing'}"})
            css_match = re.search(r'href="([^"]*styles\.css[^"]*)"', html)
            js_match = re.search(r'src="([^"]*app\.js[^"]*)"', html)
        for label, match in (("CSS 靜態資產", css_match), ("JavaScript 靜態資產", js_match)):
            if not match:
                checks.append({"name": label, "status": "FAIL", "detail": "首頁沒有引用對應資產"})
                continue
            try:
                with urllib.request.urlopen(BASE_URL + match.group(1), timeout=15) as response:
                    ok = response.status == 200 and len(response.read()) > 100
                checks.append({"name": label, "status": "PASS" if ok else "FAIL", "detail": f"HTTP {response.status}"})
            except Exception as exc:  # noqa: BLE001 - report the concrete endpoint failure
                checks.append({"name": label, "status": "FAIL", "detail": str(exc)})
    except Exception as exc:  # noqa: BLE001 - an unavailable preview is a monitor finding
        checks.append({"name": "首頁 HTTP", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
        return checks, None

    for path, label in (("/api/health", "FastAPI 健康端點"), ("/api/data/status", "資料狀態端點"), ("/api/data/series", "時間序列端點"), ("/api/learning/trace", "數學教學端點"), ("/api/jobs/active", "訓練工作狀態端點")):
        try:
            code, payload = request_json(path)
            ok = code == 200 and payload is not None
            if path == "/api/health":
                ok = ok and payload.get("ok") is True and payload.get("service") == "taiex-neural-lab" and bool(payload.get("torch"))
                detail = f"HTTP {code}; service={payload.get('service')}; PyTorch={payload.get('torch')}"
            elif path == "/api/data/status":
                status_data = payload
                ok = ok and status_data.get("fields") == ["date", "close"] and status_data.get("rows", 0) >= 300 and bool(status_data.get("sha256"))
                ok = ok and "finalTest" not in payload
                detail = f"HTTP {code}; rows={payload.get('rows')}; {payload.get('start')}…{payload.get('end')}; fields={payload.get('fields')}"
            elif path == "/api/data/series":
                points = payload.get("points", [])
                ok = ok and len(points) >= 2 and points[0].get("date") <= points[-1].get("date") and all(float(p.get("close", 0)) > 0 for p in points)
                if status_data:
                    ok = ok and payload.get("sha256") == status_data.get("sha256") and points[0]["date"] == status_data["start"] and points[-1]["date"] == status_data["end"]
                detail = f"HTTP {code}; chart points={len(points)}; endpoints match data metadata"
            elif path == "/api/learning/trace":
                err = float(payload.get("gradientMaxAbsError", math.inf))
                pred_error = abs(float(payload.get("prediction", math.inf)) - float(payload.get("pytorchPrediction", -math.inf)))
                residual = float(payload.get("prediction", math.nan)) - float(payload.get("target", math.nan))
                loss = float(payload.get("loss", math.nan))
                delta = float(payload.get("outputDelta", math.nan))
                mse_convention_ok = math.isfinite(residual) and abs(loss - residual**2) < 1e-12 and abs(delta - 2 * residual) < 1e-12
                ok = ok and err < 1e-10 and pred_error < 1e-10 and loss >= 0 and mse_convention_ok
                detail = f"HTTP {code}; NumPy/PyTorch gradient max error={err:.3g}; prediction delta={pred_error:.3g}; MSE loss/2e convention={mse_convention_ok}"
            else:
                ok = code == 200
                detail = f"HTTP {code}; {'active job present' if payload else 'idle'}"
            checks.append({"name": label, "status": "PASS" if ok else "FAIL", "detail": detail})
            if path == "/api/jobs/active":
                checks.append({"name": "PyTorch 訓練資源狀態", "status": "WARN" if payload else "PASS", "detail": "服務正執行使用者工作，為避免競爭跳過排程訓練" if payload else "閒置，可以執行隔離的訓練 smoke check"})
                if payload:
                    checks[-2]["active_job"] = True
        except Exception as exc:  # noqa: BLE001
            checks.append({"name": label, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        stock_code, stock_payload = request_json("/api/stocks")
        stocks = stock_payload.get("stocks", []) if stock_payload else []
        verified = []
        for stock in stocks:
            if not stock.get("available"):
                continue
            symbol = stock.get("symbol", "")
            status_code, stock_status = request_json(f"/api/data/status?symbol={symbol}")
            series_code, stock_series = request_json(f"/api/data/series?symbol={symbol}")
            points = (stock_series or {}).get("points", [])
            stock_ok = (status_code == 200 and series_code == 200 and stock_status.get("symbol") == symbol and
                        stock_status.get("name") == stock.get("name") and stock_status.get("rows", 0) >= 300 and
                        stock_status.get("fields") == ["date", "close"] and stock_status.get("sha256") == stock_series.get("sha256") and
                        len(points) >= 2 and points[0].get("date") == stock_status.get("start") and
                        points[-1].get("date") == stock_status.get("end") and
                        all(math.isfinite(float(point.get("close", math.nan))) and float(point["close"]) > 0 for point in points))
            if stock_ok:
                verified.append(symbol)
        available = [stock for stock in stocks if stock.get("available")]
        expected_count = stock_payload.get("expectedCount", len(stocks)) if stock_payload else 0
        coverage_ok = stock_code == 200 and len(stocks) >= 1 and len(verified) == len(available) and expected_count == len(stocks)
        checks.append({"name": "熱門個股本機資料覆蓋", "status": "PASS" if coverage_ok else "FAIL", "detail": f"API 宣告名冊={len(stocks)}/{expected_count} 檔；可用本機標的={len(available)} 檔；通過狀態／序列一致性={len(verified)} 檔；未下載或更新資料"})
    except Exception as exc:  # noqa: BLE001 - preserve a concrete stock-data check result
        checks.append({"name": "熱門個股本機資料覆蓋", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    return checks, status_data


def check_splits_and_train(active_job: bool) -> list[dict[str, Any]]:
    from app.data import build_samples, load_series, walk_forward_folds
    import app.main as main_module
    import numpy as np
    import time
    from fastapi.testclient import TestClient

    checks: list[dict[str, Any]] = []
    try:
        reload_source = (ROOT / "app" / "__main__.py").read_text(encoding="utf-8")
        reload_ok = all(token in reload_source for token in ("reload_dirs=", "ROOT / \"app\"", "ROOT / \"web\"", "reload_excludes=", "*.csv", "*.json", "*.md", "*.tmp"))
    except OSError:
        reload_ok = False
    checks.append({"name": "Uvicorn 重載監聽範圍", "status": "PASS" if reload_ok else "FAIL", "detail": "只監聽 app/web，並排除資料、文件與狀態檔" if reload_ok else "app/__main__.py 的 reload_dirs/reload_excludes 已偏離安全範圍"})
    try:
        series = load_series()
        samples = build_samples(series, ["return_1", "volatility_20"], lookback=20, horizon=1, use_log_return=False)
        origins, targets = samples["origins"], samples["targets"]
        first_expected_origin = 39
        data_ok = (bool(len(targets)) and int(origins[0]) == first_expected_origin and
                   np.isfinite(samples["x"]).all() and np.isfinite(samples["y"]).all() and
                   np.all(samples["entry_indices"] == origins + 1) and
                   np.all(targets == samples["entry_indices"] + samples["horizon"]))
        split = samples["split_index"]
        data_ok = data_ok and int(targets[-1]) == len(series.dates) - 1
        checks.append({"name": "特徵暖機與樣本切片", "status": "PASS" if data_ok else "FAIL", "detail": f"首個合法 origin={int(origins[0]) if len(origins) else 'none'}（預期 39）；樣本={len(targets)}；lookback=20，horizon=1；輸入有限，entry=origin+1、target=entry+horizon"})

        folds = walk_forward_folds(samples)
        fold_ok = len(folds) >= 2
        target_dates = np.asarray(samples["targets"])
        split_details = []
        for train_idx, val_idx in folds:
            chronology_ok = target_dates[train_idx].max() < target_dates[val_idx].min() and target_dates[val_idx].max() < split
            fold_ok = fold_ok and chronology_ok
            split_details.append(f"train≤{series.dates[int(target_dates[train_idx].max())]} < val≤{series.dates[int(target_dates[val_idx].max())]}")
        heldout_candidate_count = int(np.count_nonzero(target_dates >= split))
        fold_ok = fold_ok and heldout_candidate_count > 0
        checks.append({"name": "Walk-forward／鎖定測試邊界", "status": "PASS" if fold_ok else "FAIL", "detail": f"驗證折={len(folds)}，皆按時間遞增且 target < 邊界索引 {split}；邊界後可用樣本={heldout_candidate_count}（僅切分中繼資料，未讀取或評估其觀測值）"})

        checks.append({"name": "FastAPI／PyTorch 真實資料訓練", "status": "SKIP", "detail": "例行維護不啟動訓練 smoke；本輪只檢查切片與 walk-forward 邊界"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "資料切片／PyTorch 訓練", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    return checks


def source_snapshot() -> dict[str, str]:
    files = sorted({path for pattern in SOURCE_GLOBS for path in ROOT.glob(pattern) if path.is_file()})
    return {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in files}


def hash_sources(snapshot: dict[str, str]) -> dict[str, str]:
    return {path: hashlib.sha256(content.encode("utf-8")).hexdigest() for path, content in snapshot.items()}


def changed_sources(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def write_source_diff(changed: list[str], before: dict[str, str], after: dict[str, str]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    target = ARTIFACTS / "source-diff-latest.md"
    sections = ["# Source changes since the previous monitor run", ""]
    if not changed:
        sections.append("No tracked application, web, test, script, or requirements source changes were detected.")
    elif not before:
        sections.append("No previous text snapshot exists yet. This run establishes the baseline; the next run can produce exact unified diffs.")
    else:
        rendered = 0
        for path in changed:
            diff = list(difflib.unified_diff(
                before.get(path, "").splitlines(), after.get(path, "").splitlines(),
                fromfile=f"previous/{path}" if path in before else "/dev/null",
                tofile=f"current/{path}" if path in after else "/dev/null",
                lineterm="",
            ))
            if diff:
                rendered += 1
                sections.extend([f"## `{path}`", "", "```diff", *diff, "```", ""])
        if rendered == 0:
            sections.append("Changed paths were detected from the previous SHA-256 state, but the saved text snapshot already matches the current files. The exact historical diff is unavailable; this run refreshes the snapshot baseline.")
    content = "\n".join(sections).rstrip() + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, prefix=".source-diff-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return target


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def browser_check(previous_geometry: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    checks: list[dict[str, Any]] = []
    geometry: dict[str, Any] = {}
    visual_notes: list[str] = []
    layout_drifts: list[str] = []
    asset_strip_checks: dict[str, bool] = {}
    try:
        from PIL import Image, ImageChops, ImageStat
        from playwright.sync_api import sync_playwright

        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        launch_args: dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if Path(chrome).exists():
            launch_args["executable_path"] = chrome
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_args)
            for name, viewport in (("desktop", {"width": 1504, "height": 1046}), ("mobile", {"width": 390, "height": 844})):
                page = browser.new_page(viewport=viewport, device_scale_factor=1)
                page_errors: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                # The app can keep polling/event connections open; DOM readiness is
                # sufficient before the explicit API/UI waits below.
                response = page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(900)
                if name == "desktop":
                    stock_available = page.locator("#symbolSelect option[value='2330.TW']").count() == 1
                    asset_strip_count = page.locator("#stockCards .stock-card").count()
                    stock_coverage_note = page.locator("#stockUniverseNote").inner_text()
                    stock_coverage_visible = "10/10 檔本機資料可用" in stock_coverage_note
                    index_selected_ok = page.locator("#stockCards [data-symbol='TAIEX']").get_attribute("aria-pressed") == "true"
                    desktop_strip_one_row = page.evaluate("""() => {
                      const cards=[...document.querySelectorAll('#stockCards .stock-card')];
                      return cards.length===11 && cards.every(card=>Math.abs(card.getBoundingClientRect().y-cards[0].getBoundingClientRect().y)<2);
                    }""")
                    stock_selected_ok = False
                    stock_button_selected_ok = False
                    taiex_return_ok = False
                    index_button_selected_after_return = False
                    if stock_available:
                        page.locator("#symbolSelect").select_option("2330.TW")
                        page.wait_for_function("document.querySelector('#historyChart')?.getAttribute('aria-label')?.includes('台積電')", timeout=8000)
                        stock_selected_ok = page.locator("#periodStart").inner_text() == "2022-01-03" and "台積電" in page.locator("#historyChart").get_attribute("aria-label")
                        stock_button_selected_ok = page.locator("#stockCards [data-symbol='2330.TW']").get_attribute("aria-pressed") == "true"
                        page.locator("#symbolSelect").select_option("TAIEX")
                        page.wait_for_function("document.querySelector('#historyChart')?.getAttribute('aria-label')?.includes('TAIEX')", timeout=8000)
                        taiex_return_ok = page.locator("#periodStart").inner_text() == "2010-01-04"
                        index_button_selected_after_return = page.locator("#stockCards [data-symbol='TAIEX']").get_attribute("aria-pressed") == "true"
                        # Leave the viewport in the baseline state used by the desktop capture.
                        page.wait_for_function("document.querySelector('#historyChart .price-path')?.getAttribute('points')?.trim().length > 0", timeout=8000)
                        page.wait_for_timeout(150)
                    stock_ui_ok = stock_available and stock_selected_ok and taiex_return_ok and not page_errors
                    checks.append({"name": "熱門個股介面切換與資料同步", "status": "PASS" if stock_ui_ok else "FAIL", "detail": f"台積電選項可用={stock_available}; 載入個股日期／標籤={stock_selected_ok}; 切回 TAIEX={taiex_return_ok}; JS errors={page_errors or 'none'}"})
                    asset_strip_checks["desktop"] = asset_strip_count == 11 and index_selected_ok and desktop_strip_one_row and stock_button_selected_ok and index_button_selected_after_return and stock_coverage_visible
                    page.screenshot(path=str(ARTIFACTS / f"latest-{name}.png"), full_page=False)
                dom = page.evaluate(r"""() => {
                  const selectors = ['.sidebar','.control-strip','.stock-universe-panel','#stockCards','#timeline','#historyChart','#network','#networkDiagram','#results','.loss-panel','.metrics-panel','.action-bar','#runValidation','#cancelJob'];
                  const boxes = {};
                  for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el) { const r = el.getBoundingClientRect(); boxes[selector] = {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),visible:r.width>0&&r.height>0}; }
                  }
                  const cancel = document.querySelector('#cancelJob');
                  const cancelRect = cancel?.getBoundingClientRect();
                  const cancelStyle = cancel ? getComputedStyle(cancel) : null;
                  return {
                    title: document.title,
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    scrollHeight: document.documentElement.scrollHeight,
                    clientHeight: document.documentElement.clientHeight,
                    boxes,
                    historyPoints: (() => { const path = document.querySelector('#historyChart .price-path'); return path ? path.getAttribute('points').trim().split(/\s+/).length : 0; })(),
                    networkConnections: document.querySelectorAll('#networkDiagram .network-connection').length,
                    modelCompareChoices: [...document.querySelectorAll('.model-compare input')].map(input => ({value:input.value, enabled:!input.disabled})),
                    learningTabs: document.querySelectorAll('.learning-tab').length,
                    trainButton: !!document.querySelector('#runValidation'),
                    cancel: cancel ? {display:cancelStyle.display,width:Math.round(cancelRect.width),height:Math.round(cancelRect.height),visible:cancelStyle.display!=='none'&&cancelRect.width>0&&cancelRect.height>0} : null,
                    chartLabels: !!document.querySelector('#phaseKey') && !!document.querySelector('#trainDates'),
                    chartRailGap: (() => { const chart=document.querySelector('#historyChart')?.getBoundingClientRect(),rail=document.querySelector('.timeline-panel .phase-rail')?.getBoundingClientRect();return chart&&rail?Math.round(rail.top-chart.bottom):null; })(),
                    openConsole: document.querySelectorAll('img').length,
                  };
                }""")
                if name == "desktop":
                    geometry = dom["boxes"]
                    ref_note = ""
                    if REFERENCE.exists():
                        ref_size = Image.open(REFERENCE).size
                        shot = Image.open(ARTIFACTS / "latest-desktop.png").convert("RGB")
                        ref = Image.open(REFERENCE).convert("RGB")
                        if ref.size != shot.size:
                            ref_note = f"reference size {ref.size}, captured {shot.size}; resized reference for informational pixel delta"
                            ref = ref.resize(shot.size)
                        delta = ImageStat.Stat(ImageChops.difference(ref, shot)).mean
                        mean_delta = sum(delta) / (3 * 255)
                        ref_note += f"mean absolute RGB pixel delta={mean_delta:.4f} (informational; screenshots contain different real data/state)"
                    else:
                        ref_note = "sequence-first.png missing"
                        visual_notes.append(ref_note)
                    required_ok = response is not None and response.status == 200 and dom["historyPoints"] >= 2 and dom["networkConnections"] > 0 and dom["trainButton"] and dom["chartLabels"] and page.locator("#topTrain").count() == 1
                    checks.append({"name": "桌面瀏覽器渲染與圖表結構", "status": "PASS" if required_ok and not page_errors else "FAIL", "detail": f"1504×1046; history points={dom['historyPoints']}; network links={dom['networkConnections']}; JS errors={page_errors or 'none'}; {ref_note}; screenshot=artifacts/regression-monitor/latest-desktop.png"})
                    initial_network_model = page.locator("#modelType").input_value()
                    page.locator("#modelType").select_option("mlp")
                    initial_step_pending = page.locator("#networkDiagram").get_attribute("data-motion-step") is None
                    page.locator("#stepNetwork").click()
                    step_zero = initial_step_pending and page.locator("#networkDiagram").get_attribute("data-motion-step") == "0"
                    input_stage = page.locator("#networkDiagram .network-node[data-layer='0'].is-active").count() > 0
                    page.locator("#stepNetwork").click()
                    step_one = page.locator("#networkDiagram").get_attribute("data-motion-step") == "1"
                    layer_reveal = (
                        input_stage
                        and page.locator("#networkDiagram .network-node[data-layer='0'].is-reached").count() == 0
                        and page.locator("#networkDiagram .network-node[data-layer='1'].is-active").count() > 0
                        and page.locator("#networkDiagram .network-connection[data-layer='0'].is-traversed").count() > 0
                        and page.locator("#networkDiagram .network-connection[data-layer='1'].is-traversed").count() == 0
                    )
                    page.locator("#playNetwork").click()
                    page.wait_for_function("Number(document.querySelector('#networkDiagram').dataset.motionStep) >= 2", timeout=2500)
                    auto_advanced = int(page.locator("#networkDiagram").get_attribute("data-motion-step") or -1) >= 2
                    page.locator("#pauseNetwork").click()
                    pause_stable = "已暫停" in page.locator("#networkMotionStatus").inner_text() and page.locator("#networkDiagram .is-flowing").count() == 0
                    paused_step = int(page.locator("#networkDiagram").get_attribute("data-motion-step") or -1)
                    page.locator("#playNetwork").click()
                    page.wait_for_function("step => Number(document.querySelector('#networkDiagram').dataset.motionStep) > step", arg=paused_step, timeout=2500)
                    resume_advanced = int(page.locator("#networkDiagram").get_attribute("data-motion-step") or -1) > paused_step
                    page.locator("#replayNetwork").click()
                    replay_restarted = page.locator("#networkDiagram").get_attribute("data-motion-step") == "0" and "第 1 /" in page.locator("#networkMotionStatus").inner_text() and page.locator("#playNetwork span").inner_text() == "從輸入播放" and page.locator("#networkDiagram .network-node[data-layer='0'].is-active").count() > 0
                    # Replay intentionally returns to the input stage and stays paused.
                    # Start playback before waiting for a pausable state.
                    page.locator("#playNetwork").click()
                    page.wait_for_function("!document.querySelector('#pauseNetwork').disabled", timeout=2500)
                    page.locator("#pauseNetwork").click()
                    replay_pause_ok = "已暫停" in page.locator("#networkMotionStatus").inner_text()
                    page.emulate_media(reduced_motion="no-preference")
                    page.evaluate("resetNetworkMotion()")
                    page.locator("#replayNetwork").click()
                    # Replay deliberately stops at the input stage; start playback before waiting for progress.
                    page.locator("#playNetwork").click()
                    page.wait_for_function("document.querySelector('#networkDiagram').dataset.motionStep !== '0'", timeout=2500)
                    page.wait_for_function("!document.querySelector('#pauseNetwork').disabled", timeout=2500)
                    page.locator("#pauseNetwork").click()
                    pause_cycle_ok = "已暫停" in page.locator("#networkMotionStatus").inner_text()
                    checks.append({"name": "動畫重播後暫停時序", "status": "PASS" if pause_cycle_ok else "FAIL", "detail": f"重播後等待進入播放再暫停={pause_cycle_ok}"})
                    page.emulate_media(reduced_motion="reduce")
                    page.evaluate("resetNetworkMotion()")
                    page.locator("#stepNetwork").click()
                    reduced_motion_ok = page.locator("#networkDiagram").get_attribute("data-motion-step") == "0" and page.locator("#networkDiagram .is-active").evaluate_all("els=>els.length>0 && els.every(el=>getComputedStyle(el).animationName==='none')") and page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
                    mlp_equation = page.locator("#networkStageEquation").inner_text()
                    mlp_equation_compact = "".join(mlp_equation.split())
                    equation_ok = all(token in mlp_equation_compact for token in ["z⁽", "=W⁽", "⁾a⁽", "+b⁽", "=ReLU(z⁽"])
                    page.locator("#modelType").select_option("mlp")
                    # Existing browser state may contain a saved validation trace. The
                    # architecture preview contract specifically covers the no-trace state.
                    page.evaluate("state.forwardTrace = null")
                    page.evaluate("activateNetworkStage(1, false)")
                    shape_note = page.locator("#networkStepDetail").inner_text()
                    shape_note_ok = all(token in shape_note for token in ["矩陣維度例子", "a∈ℝ³", "W∈ℝ²ˣ³", "Wa∈ℝ²", "結果為 2 維"])
                    recurrent_equations = {"rnn": "hₜ = tanh(Wₓxₜ + Wₕhₜ₋₁ + b)", "lstm": "cₜ = fₜ⊙cₜ₋₁ + iₜ⊙c̃ₜ", "gru": "hₜ = (1−zₜ)⊙hₜ₋₁ + zₜ⊙h̃ₜ"}
                    for model, fragment in recurrent_equations.items():
                        page.locator("#modelType").select_option(model)
                        page.evaluate("activateNetworkStage(1, false)")
                        equation_ok = equation_ok and fragment in page.locator("#networkStageEquation").inner_text()
                    page.locator("#modelType").select_option(initial_network_model)
                    page.evaluate("resetNetworkMotion()")
                    motion_ok = step_zero and step_one and layer_reveal and auto_advanced and pause_stable and resume_advanced and replay_restarted and replay_pause_ok and reduced_motion_ok and equation_ok and shape_note_ok and not page_errors
                    checks.append({"name": "神經網路前向傳播動畫（手動／自動／暫停／重播）", "status": "PASS" if motion_ok else "FAIL", "detail": f"逐層步進={step_zero and step_one}；節點與連線逐層點亮={layer_reveal}；層公式={equation_ok}；MLP 矩陣維度教學={shape_note_ok}；自動前進={auto_advanced}；暫停穩定={pause_stable}；續播前進={resume_advanced}；重播回輸入={replay_restarted}；減少動態效果保留階段狀態={reduced_motion_ok}"})
                    epoch_display = page.locator("#toolbarEpoch").inner_text().strip()
                    epoch_matches_config = epoch_display == page.locator("#epochs").input_value().zfill(3)
                    training_motion_idle = page.locator("#network").get_attribute("class").find("is-training") < 0 and epoch_matches_config
                    checks.append({"name": "例行瀏覽器檢查不啟動訓練", "status": "PASS" if training_motion_idle else "FAIL", "detail": f"未進入訓練狀態且 Epoch 顯示與設定相符={training_motion_idle}（目前 {epoch_display}；設定 {page.locator('#epochs').input_value().zfill(3)}）"})
                    checks.append({"name": "鎖定測試圖表隔離", "status": "PASS", "detail": "routine browser checks do not inspect holdout chart or prediction rows"})
                    provenance_ok = page.evaluate("""() => {
                      if (!state.validation || !state.validationConfig) return false;
                      const savedConfig=state.validationConfig, savedSymbol=document.querySelector('#symbolSelect').value;
                      state.validationConfig={...savedConfig,symbol:'2330.TW'};
                      document.querySelector('#symbolSelect').value='2317.TW';
                      renderSignals(state.validation);
                      const text=document.querySelector('#signalProvenance').textContent;
                      const visible=!document.querySelector('#signalProvenance').hidden;
                      state.validationConfig=savedConfig;
                      document.querySelector('#symbolSelect').value=savedSymbol;
                      renderSignals(state.validation);
                      return visible && text.includes('台積電（2330.TW）') && text.includes('目前選擇 2317.TW') && text.includes('上次驗證結果');
                    }""")
                    checks.append({"name": "舊驗證訊號標示來源標的與過期狀態", "status": "PASS" if provenance_ok else "FAIL", "detail": f"切換標的時清楚列出原驗證標的與舊結果提示={provenance_ok}"})
                    original_model = page.locator("#modelType").input_value()
                    original_layers = page.locator("#hiddenLayers").input_value()
                    page.locator("#modelType").select_option("mlp")
                    mlp_controls_ok = page.locator("#recurrentLayersField").evaluate("element => element.hidden") and not page.locator(".mlp-sizes").evaluate("element => element.hidden")
                    page.locator("#modelType").select_option("gru")
                    page.locator("#advancedMenu > summary").click()
                    page.locator("#hiddenLayers").fill("1")
                    single_layer_text = page.locator("#layerSummary").inner_text()
                    recurrent_controls_ok = not page.locator("#recurrentLayersField").evaluate("element => element.hidden") and page.locator(".mlp-sizes").evaluate("element => element.hidden") and "Dropout 0" in single_layer_text
                    page.locator("#hiddenLayers").fill(original_layers)
                    page.locator("#modelType").select_option(original_model)
                    page.keyboard.press("Escape")
                    page.locator("#modelType").select_option("tcn")
                    tcn_controls_ok = page.locator("#recurrentLayersField").evaluate("element => element.hidden") and page.locator(".mlp-sizes").evaluate("element => element.hidden") and page.locator(".layer-stepper").evaluate("element => element.hidden") and "kernel 3" in page.locator("#layerSummary").inner_text()
                    page.evaluate("activateNetworkStage(1, false)")
                    tcn_equation_text = page.locator("#networkStageEquation").inner_text()
                    tcn_equation_ok = "因果卷積" in tcn_equation_text and "只讀最後時間位置" in tcn_equation_text
                    page.locator("#modelType").select_option(original_model)
                    page.locator("#modelType").select_option("mlp")
                    page.evaluate("activateNetworkStage(1, false)")
                    dimension_lesson_ok = all(token in page.locator("#networkStepDetail").inner_text() for token in ["矩陣維度例子", "a∈ℝ³", "W∈ℝ²ˣ³", "Wa∈ℝ²", "結果為 2 維"])
                    page.locator("#modelType").select_option(original_model)
                    expected_compare_models = {"mlp", "rnn", "lstm", "gru", "tcn"}
                    observed_compare_models = {choice["value"] for choice in dom["modelCompareChoices"] if choice["enabled"]}
                    multi_model_ok = len(dom["modelCompareChoices"]) == 5 and observed_compare_models == expected_compare_models
                    # The learning center is inside a collapsed <details> panel.
                    page.locator("#math > summary").click()
                    # Reset the in-memory snapshot used by renderLesson's resume notice too.
                    # The monitor must not inherit a learner's persisted lesson state.
                    page.evaluate("() => { saveLearningProgress = () => {}; savedLearningProgress.lessonIndex = 0; lessonIndex = 0; }")
                    page.locator("#tabGuided").click()
                    page.evaluate("renderLesson()")
                    page.locator("#tabLab").click()
                    page.locator('label.quiz-choice:has(input[name="tensorShapeAnswer"][value="input-first"])').click()
                    page.locator("#checkTensorShape").click()
                    tensor_wrong = "再看每一列" in page.locator("#tensorShapeFeedback").inner_text()
                    page.locator('label.quiz-choice:has(input[name="tensorShapeAnswer"][value="neurons-first"])').click()
                    page.locator("#checkTensorShape").click()
                    tensor_right = "W 有 2 列、3 欄" in page.locator("#tensorShapeFeedback").inner_text()
                    tensor_shape_quiz_ok = tensor_wrong and tensor_right
                    checks.append({"name": "模型選擇與專屬控制項", "status": "PASS" if mlp_controls_ok and recurrent_controls_ok and multi_model_ok and tcn_controls_ok and tcn_equation_ok and dimension_lesson_ok and tensor_shape_quiz_ok else "FAIL", "detail": f"multi-model choices={sorted(observed_compare_models)}/{sorted(expected_compare_models)} enabled; MLP/RNN-GRU/TNC controls correct={mlp_controls_ok and recurrent_controls_ok and tcn_controls_ok}; causal equation={tcn_equation_ok}; untrained MLP dimension example={dimension_lesson_ok}; tensor-shape quiz wrong/right feedback={tensor_shape_quiz_ok}"})
                    page.locator("#settingsShortcut").click()
                    popover_box = page.locator("#advancedMenu .advanced-popover").bounding_box()
                    sidebar_box = page.locator(".sidebar").bounding_box()
                    popover_geometry = page.evaluate("""() => {
                      const box = document.querySelector('#advancedMenu .advanced-popover').getBoundingClientRect();
                      const side = document.querySelector('.sidebar').getBoundingClientRect();
                      return {left:box.left,right:box.right,top:box.top,bottom:box.bottom,sidebarRight:side.right,viewport:innerWidth};
                    }""")
                    popover_visible = popover_box and sidebar_box and popover_geometry["left"] >= popover_geometry["sidebarRight"] - 1 and popover_geometry["right"] <= popover_geometry["viewport"] + 1
                    checks.append({"name": "進階設定面板不被固定側欄遮擋", "status": "PASS" if popover_visible else "FAIL", "detail": f"面板 x={popover_geometry['left']:.0f}–{popover_geometry['right']:.0f}px；側欄右緣={popover_geometry['sidebarRight']:.0f}px；視窗={popover_geometry['viewport']}px"})
                    page.keyboard.press("Escape")
                    page.locator("#settingsShortcut").click()
                    # Close by clicking the fixed sidebar brand, which remains visible even from a scrolled results section.
                    page.locator(".brand").click()
                    outside_closed = not page.locator("#advancedMenu").evaluate("element => element.open")
                    page.locator("#settingsShortcut").click()
                    page.keyboard.press("Escape")
                    escape_closed = not page.locator("#advancedMenu").evaluate("element => element.open")
                    interaction_ok = outside_closed and escape_closed
                    checks.append({"name": "進階設定關閉互動", "status": "PASS" if interaction_ok else "FAIL", "detail": f"點擊圖表外部收合={outside_closed}；Escape 收合={escape_closed}"})
                    api_error = page.evaluate("""async () => {
                      try {
                        await api('/api/experiments', {method:'POST', body:JSON.stringify({modelTypes:['mlp'],features:['return_1'],lookback:4,horizon:1,epochs:1})});
                        return {status:200,message:'invalid request unexpectedly accepted'};
                      } catch (error) { return {status:error.status,message:error.message}; }
                    }""")
                    api_error_ok = api_error.get("status") == 422 and bool(api_error.get("message")) and "[object Object]" not in api_error["message"]
                    checks.append({"name": "422 API 錯誤可讀性", "status": "PASS" if api_error_ok else "FAIL", "detail": f"invalid lookback returned HTTP {api_error.get('status')}; message={api_error.get('message')}"})
                    direction_mix = page.evaluate("""() => directionMixSummary([
                      {actual:.01,predicted:.02},{actual:-.01,predicted:0},{actual:0,predicted:-.01},{actual:.03,predicted:.01},
                      {actual:null,predicted:.50},{actual:.50,predicted:null}
                    ])""")
                    direction_mix_ok = all(term in direction_mix for term in ["實際上漲 2（50.0%）", "下跌 1（25.0%）", "持平 1（25.0%）", "預測上漲 2（50.0%）", "下跌 1（25.0%）", "中性 1（25.0%）"])
                    magnitude_ok = "上漲實際 2.000／預測 1.500 個百分點" in direction_mix and "下跌實際 1.000／預測 1.000 個百分點" in direction_mix
                    directional_error = page.evaluate("directionMixSummary([{actual:.01,predicted:.02},{actual:-.01,predicted:0},{actual:.03,predicted:.01},{actual:.02,predicted:-.01},{actual:-.02,predicted:-.01},{actual:null,predicted:.5}])")
                    directional_error_ok = "上漲 n=3、2.000 個百分點" in directional_error and "下跌 n=2、1.000 個百分點" in directional_error and "方向錯置 1 筆" in directional_error
                    direction_empty = page.evaluate("directionMixSummary([])") == ""
                    direction_skew = page.evaluate("directionMixSummary([{actual:.01,predicted:.01},{actual:.02,predicted:-.01},{actual:.03,predicted:0}])")
                    skew_ok = "實際資料有 100.0% 集中於單一方向" in direction_skew
                    checks.append({"name": "驗證方向比例與預測幅度", "status": "PASS" if direction_mix_ok and magnitude_ok and directional_error_ok and direction_empty and skew_ok else "FAIL", "detail": f"合成方向比例及 null 配對排除={direction_mix_ok}；實際／預測絕對幅度並列={magnitude_ok}；按實際方向分組 MAE 與方向錯置={directional_error_ok}；空逐筆資料摘要為空={direction_empty}；70% 以上實際方向集中提醒={skew_ok}"})
                    learning_ok = dom.get("learningTabs") == 4
                    if not page.locator("#math").evaluate("element => element.open"):
                        page.locator("#math > summary").click()
                    page.locator("#tabGuided").click()
                    tab_keyboard = page.evaluate("""() => {
                      const tabs=[...document.querySelectorAll('.learning-tab')];
                      const oneTabStop=tabs.filter(tab=>tab.tabIndex===0).length===1 && tabs.find(tab=>tab.tabIndex===0)?.getAttribute('aria-selected')==='true';
                      return {oneTabStop, ids:tabs.map(tab=>tab.id)};
                    }""")
                    page.locator("#tabGuided").focus()
                    page.keyboard.press("ArrowRight")
                    tab_right_ok = page.evaluate("document.activeElement.id==='tabQuiz' && document.querySelector('#tabQuiz').getAttribute('aria-selected')==='true' && document.querySelector('#learningQuiz').hidden===false && [...document.querySelectorAll('.learning-tab')].filter(tab=>tab.tabIndex===0).length===1")
                    page.keyboard.press("ArrowLeft")
                    tab_left_ok = page.evaluate("document.activeElement.id==='tabGuided' && document.querySelector('#tabGuided').getAttribute('aria-selected')==='true' && document.querySelector('#learningGuided').hidden===false")
                    tab_keyboard_ok = tab_keyboard.get("oneTabStop") and tab_right_ok and tab_left_ok
                    checks.append({"name": "學習中心鍵盤分頁操作", "status": "PASS" if tab_keyboard_ok else "FAIL", "detail": f"單一 Tab 停駐點={tab_keyboard.get('oneTabStop')}; 右鍵切換={tab_right_ok}; 左鍵返回={tab_left_ok}"})
                    # Browser storage may retain a learner's last lesson. Reset only
                    # this monitor page's in-memory state, without persisting it.
                    # Keep the loaded resume snapshot and visible lesson consistent.
                    page.locator("#tabGuided").click()
                    page.wait_for_function("document.querySelector('#tabGuided')?.getAttribute('aria-selected') === 'true' && document.querySelector('#learningGuided')?.hidden === false")
                    page.evaluate("() => { saveLearningProgress = () => {}; savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'; lessonIndex = 0; activeLearningTabId = 'tabGuided'; renderLesson(); }")
                    reset_notice_hidden = page.locator("#learningResumeNotice").evaluate("element => element.hidden")
                    lesson_before = page.locator("#lessonProgress").inner_text()
                    lesson_start = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*步", lesson_before)
                    page.locator("#lessonNext").click()
                    page.wait_for_function("document.querySelector('#learningGuided')?.hidden === false && document.querySelector('#lessonProgress')?.textContent.includes('2 /')")
                    lesson_after = page.locator("#lessonProgress").inner_text()
                    lesson_next = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*步", lesson_after)
                    page.locator("#tabGuided").click()
                    page.wait_for_function("document.querySelector('#tabGuided')?.getAttribute('aria-selected') === 'true' && document.querySelector('#learningGuided')?.hidden === false")
                    page.locator("#lessonBack").click()
                    lesson_return = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*步", page.locator("#lessonProgress").inner_text())
                    lesson_resume_notice = page.locator("#learningResumeNotice").inner_text()
                    lesson_catalog_ok = page.evaluate("""() => {
                      // The result is editable UI state; normalize its fixture before
                      // asserting rendered copy so prior browser interactions cannot leak in.
                      for (const [id, value] of Object.entries({batchWeight:'2',batchGradientOne:'-2',batchGradientTwo:'4',batchGradientThree:'1',batchGradientFour:'1',batchRate:'0.1'})) document.getElementById(id).value=value;
                      renderBatchGradientExercise();
                      const momentum = calculateMomentumUpdate(0.9,0.5,1,2,0.1); const momentumSteps=calculateMomentumSteps(0.9,0.5,1,0.5,-2,2,0.1);
                      const batch = calculateBatchGradientUpdate(2,[-2,4,1,1],0.1); const alignedBatch=calculateBatchGradientUpdate(2,[1,1,1,1],0.1); const balancedBatch=calculateBatchGradientUpdate(2,[-1,1,0,0],0.1);
                      const gradient = calculateGradientUpdate(2,0.5,1,-0.4,0.2,1,0.1);
                      const forward = calculateForwardPass(2,0.5,0.2);
                      const multi = calculateMultiForwardPass(2,0.5,1,-0.4,0.2,1);
                      const interval = calculatePredictionInterval(0.6,0.4);
                      const activation = calculateActivationComparison(2); const clipped = calculateGradientClipping(2,4,1,0.1);
                      const refs = [calculateMagnitudeReference(20000,0.6,'simple'), calculateMagnitudeReference(20000,-0.6,'simple'), calculateMagnitudeReference(20000,0.6,'log')];
                      const widerInterval = calculatePredictionInterval(0.6,0.7);
                      const lessonCatalogClauses = [
                        LESSONS.length === 26,
                        LESSONS[19].title.includes('動量累積近期梯度方向'),
                        LESSONS[19].body.includes('vₜ=βvₜ₋₁+gₜ'),
                        LESSONS[19].body.includes('1.45'),
                        LESSONS[19].takeaway.includes('訓練資料和驗證結果'),
                        momentum.velocity === 1.45,
                        momentumSteps.velocity1===1.45,
                        momentumSteps.weight1===1.855,
                        momentumSteps.velocity2===1.805,
                        momentumSteps.weight2===1.6745,
                        Math.abs(momentumSteps.velocity3-(-0.3755))<1e-12,
                        Math.abs(momentumSteps.weight3-1.71205)<1e-12,
                        calculateMomentumSteps(0.9,0.5,1,0.5,'',2,0.1)===null,
                        calculateMomentumSteps(1.1,0.5,1,0.5,-2,2,0.1)===null,
                        document.querySelector('#momentumNextGradient'),
                        LESSONS[20].title.includes('Sigmoid、ReLU 與 Tanh'),
                        activation.sigmoid > 0.8,
                        activation.relu === 2,
                        activation.reluGradient === 1,
                        Math.abs(activation.tanh-0.96402758)<1e-7,
                        Math.abs(activation.tanhGradient-0.07065082)<1e-7,
                        Math.abs(calculateActivationComparison(40,0).sigmoidGradient/4.248354255e-18-1)<1e-9,
                        Math.abs(calculateActivationComparison(20,0).tanhGradient/1.699341702e-17-1)<1e-9,
                        calculateActivationComparison(2,1e200)===null,
                        calculateActivationComparison(-2).relu === 0,
                        calculateActivationComparison('')===null,
                        document.querySelector('#activationExercise'),
                        LESSONS[21].title.includes('梯度裁剪'),
                        LESSONS[21].body.includes('w新=1.9'),
                        LESSONS[21].body.includes('梯度 (3,4) 的範數是 5'),
                        LESSONS[21].body.includes('變成 (0.6,0.8)'),
                        clipped.clipped===1,
                        Math.abs(clipped.updated-1.9)<1e-12,
                        Math.abs(clipped.unclippedUpdated-1.6)<1e-12,
                        Math.abs(calculateGradientClipping(2,0.5,1,0.1).unclippedUpdated-1.95)<1e-12,
                        calculateGradientClipping('',4,1,0.1)===null,
                        calculateGradientClipping(2,4,-1,0.1)===null,
                        document.querySelector('#gradientClippingExercise'),
                        Math.abs(momentum.updated-1.855)<1e-12,
                        calculateMomentumUpdate('',0.5,1,2,0.1)===null,
                        calculateMomentumUpdate(1.1,0.5,1,2,0.1)===null,
                        document.querySelector('#momentumExercise'),
                        LESSONS[18].title.includes('多筆樣本先平均梯度'),
                        LESSONS[18].body.includes('(−2+4+1+1)/4=1'),
                        batch.average===1,
                        Math.abs(batch.updated-1.9)<1e-12,
                        batch.total===4,
                        Math.abs(batch.summedUpdate-1.6)<1e-12,
                        batch.positiveCount===3,
                        batch.negativeCount===1,
                        batch.zeroCount===0,
                        Math.abs(batch.variance-4.5)<1e-12,
                        Math.abs(batch.standardDeviation-Math.sqrt(4.5))<1e-12,
                        Math.abs(batch.maxLeaveOneOutShift-1)<1e-12,
                        batch.influentialSampleChangesDirection===false,
                        balancedBatch.influentialSampleChangesDirection===true,
                        Math.abs(balancedBatch.maxLeaveOneOutShift-1/3)<1e-12,
                        Math.abs(calculateBatchGradientUpdate(2,[1,1,1,1],0.1).maxLeaveOneOutShift)<1e-12,
                        balancedBatch.average===0,
                        balancedBatch.updated===2,
                        balancedBatch.minGradient===-1,
                        balancedBatch.maxGradient===1,
                        Math.abs(balancedBatch.variance-0.5)<1e-12,
                        calculateBatchGradientUpdate('',[-2,4,1,1],0.1)===null,
                        calculateBatchGradientUpdate(2,[-2,4,1,1],2)===null,
                        calculateBatchGradientUpdate(2,[-2,4,'',1],0.1)===null,
                        document.querySelector('#batchGradientExercise'),
                        document.querySelector('#batchGradientResult').textContent.includes(`若逐一拿掉一筆，平均梯度最多改變 ${batch.maxLeaveOneOutShift.toFixed(4)}；第 ${batch.influentialSample} 筆（梯度 ${batch.influentialGradient}）影響最大`),
                        document.querySelector('#batchGradientResult').textContent.includes('拿掉影響最大的一筆後，批次平均梯度的更新方向維持不變。'),
                        LESSONS[18].takeaway.includes('平均梯度'),
                        LESSONS[7].title.includes('預測報酬換成參考點位'),
                        LESSONS[7].body.includes('20,000 × exp(0.01)'),
                        LESSONS[7].takeaway.includes('不是下一日可成交價格'),
                        LESSONS[8].title.includes('學習率'),
                        LESSONS[8].body.includes('1.95'),
                        LESSONS[8].body.includes('1.75'),
                        LESSONS[8].takeaway.includes('不代表訓練收斂'),
                        LESSONS[9].title.includes('正負號表示方向'),
                        LESSONS[9].body.includes('+0.6%'),
                        LESSONS[9].takeaway.includes('逐筆 OOF'),
                        LESSONS[10].title.includes('單一預測值'),
                        LESSONS[11].title.includes('反向傳播'),
                        LESSONS[11].body.includes('−8'),
                        LESSONS[11].takeaway.includes('合成算例'),
                        LESSONS[13].title.includes('觀察 ReLU 如何傳遞梯度'),
                        LESSONS[14].title.includes('方向一致性和幅度誤差'),
                        LESSONS[15].kicker.includes('單一神經元前向傳播'),
                        LESSONS[15].body.includes('z=wx+b'),
                        LESSONS[16].kicker.includes('多輸入神經元'),
                        LESSONS[16].body.includes('z=w₁x₁+w₂x₂+b'),
                        LESSONS[17].title.includes('梯度做一次'),
                        document.querySelector('#gradientUpdateExercise'),
                        Math.abs(gradient.before.loss-0.04)<1e-12,
                        Math.abs(gradient.after.loss-0.0016)<1e-12,
                        calculateGradientUpdate(2,0.5,1,-0.4,0.2,1,2)===null,
                        document.querySelector('#reluTarget'),
                        document.querySelector('#magnitudeErrorExercise'),
                        forward.z===1.2,
                        forward.output===1.2,
                        calculateForwardPass(-2,0.5,0.2).z===-0.8,
                        calculateForwardPass(-2,0.5,0.2).output===0,
                        calculateForwardPass('',0.5,0.2)===null,
                        calculateForwardPass(1e308,1e308,0)===null,
                        document.querySelector('#forwardPassExercise'),
                        multi.z===0.8,
                        multi.output===0.8,
                        Math.abs(multi.gradients.w1+0.8)<1e-12,
                        calculateMultiForwardPass(-2,0.5,1,-0.4,0.2,1).z===-1.2,
                        calculateMultiForwardPass(-2,0.5,1,-0.4,0.2,1).gradients.bias===0,
                        calculateMultiForwardPass('',0.5,1,-0.4,0.2,1)===null,
                        calculateMultiForwardPass(1e308,1e308,1,1,0,1)===null,
                        document.querySelector('#multiInputTarget'),
                        document.querySelector('#multiForwardPassExercise'),
                        document.querySelector('#magnitudeExample'),
                        refs[0].value===20120,
                        refs[1].value===19880,
                        Math.abs(refs[2].value-20120.36)<0.01,
                        calculateMagnitudeReference('',0.6,'simple')===null,
                        document.querySelector('#predictionIntervalExample'),
                        document.querySelector('#intervalCenter'),
                        document.querySelector('#intervalSpread'),
                        document.querySelector('#predictionIntervalResult'),
                        Math.abs(interval.lower-0.2)<1e-12,
                        interval.upper===1,
                        Math.abs(widerInterval.lower+0.1)<1e-12,
                        widerInterval.upper===1.3,
                        calculatePredictionInterval('',0.4)===null,
                        calculatePredictionInterval(0.6,-0.1)===null];
                      window.__lessonCatalogChecks = lessonCatalogClauses.map((passed, index) => ({index: index + 1, passed}));
                      return lessonCatalogClauses.every(Boolean);
                    }""")
                    lesson_catalog_failures = page.evaluate("""() => (window.__lessonCatalogChecks || []).filter(check => !check.passed).map(check => check.index)""")
                    l2_lesson_failures = page.evaluate("""() => Object.entries(window.__l2LessonChecks || {}).filter(([, passed]) => !passed).map(([name]) => name)""")
                    guided_visible_after_back = page.locator("#learningGuided").evaluate("element => !element.hidden")
                    lesson_ok = bool(lesson_start and lesson_next and lesson_return and guided_visible_after_back and
                                     int(lesson_next.group(1)) == min(int(lesson_start.group(1)) + 1, 22) and
                                     lesson_start.group(2) == lesson_next.group(2) == lesson_return.group(2) == str(page.evaluate("LESSONS.length")) and
                                     lesson_return.group(1) == lesson_start.group(1) and lesson_catalog_ok and
                                     (lesson_start.group(1) == "1" or "已恢復上次進度" in lesson_resume_notice) and
                                     f"{lesson_start.group(2)} 步導學" in page.locator("#learningSummary").inner_text())
                    # Later browser fixtures set lessonIndex directly. Restore the
                    # navigation starting point before checking lesson 8 visibility.
                    page.evaluate("() => { savedLearningProgress.lessonIndex = 0; savedLearningProgress.tabId = 'tabGuided'; lessonIndex = 0; activeLearningTabId = 'tabGuided'; renderLesson(); }")
                    # Advance exactly seven steps from lesson 1 to lesson 8.
                    for _ in range(7): page.locator("#lessonNext").click()
                    lesson_eighth = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*步", page.locator("#lessonProgress").inner_text())
                    lesson_eighth_visible = bool(lesson_eighth and lesson_eighth.group(1) == "8" and
                                                 page.locator("#returnConversionExercise").is_visible())
                    page.locator("#conversionPrice").fill("20000")
                    page.locator("#conversionReturn").fill("1")
                    simple_conversion_ok = "20,200.00 點" in page.locator("#conversionResult").inner_text() and "20,201.00 點" in page.locator("#conversionResult").inner_text()
                    page.locator("#conversionType").select_option("log")
                    log_conversion_ok = "20,201.00 點" in page.locator("#conversionResult").inner_text() and "20,200.00 點" in page.locator("#conversionResult").inner_text()
                    page.locator("#conversionReturn").fill("-101")
                    log_below_minus_100_ok = "對數報酬換算：7,284.38 點" in page.locator("#conversionResult").inner_text() and "簡單報酬定義無效" in page.locator("#conversionResult").inner_text()
                    page.locator("#conversionType").select_option("simple")
                    simple_below_minus_100_ok = "簡單報酬不可低於 −100%" in page.locator("#conversionResult").inner_text()
                    page.locator("#lessonNext").click()
                    learning_rate_step_ok = page.locator("#lessonProgress").inner_text().startswith("第 9 / 26 步") and "學習率" in page.locator("#lessonTitle").inner_text() and "1.95" in page.locator("#lessonBody").inner_text() and page.locator("#gradientExercise").is_visible() and "1.95" in page.locator("#gradientResult").inner_text() and "權重下降" in page.locator("#gradientResult").inner_text() and "平方損失下降" in page.locator("#gradientResult").inner_text() and "更新前損失 1" in page.locator("#gradientResult").inner_text() and not page.locator("#returnConversionExercise").is_visible()
                    page.locator("#gradientRate").fill("10")
                    oversized_step_loss_ok = "平方損失上升" in page.locator("#gradientResult").inner_text() and "更新後 16" in page.locator("#gradientResult").inner_text()
                    page.locator("#gradientRate").fill("0.1")
                    page.locator("#gradientValue").fill("-0.5")
                    negative_gradient_direction_ok = "權重上升" in page.locator("#gradientResult").inner_text() and "2.05" in page.locator("#gradientResult").inner_text()
                    page.locator("#gradientValue").fill("0")
                    zero_gradient_direction_ok = "權重不變" in page.locator("#gradientResult").inner_text() and "2" in page.locator("#gradientResult").inner_text()
                    page.locator("#gradientWeight").fill("")
                    empty_gradient_input_ok = "請填妥" in page.locator("#gradientResult").inner_text()
                    def guided_fixture(script):
                        guided_tab = page.locator("#tabGuided")
                        if guided_tab.get_attribute("aria-selected") != "true":
                            guided_tab.click()
                        page.wait_for_function("document.querySelector('#tabGuided')?.getAttribute('aria-selected') === 'true' && document.querySelector('#learningGuided')?.hidden === false")
                        return page.evaluate(script)
                    magnitude_step_ok = guided_fixture("() => { lessonIndex=9; renderLesson(); return document.querySelector('#lessonProgress').textContent.startsWith('第 10 / 26 步') && document.querySelector('#lessonTitle').textContent.includes('正負號表示方向') && document.querySelector('#lessonBody').textContent.includes('+0.6%') && document.querySelector('#lessonBody').textContent.includes('0.4 個百分點') && document.querySelector('#lessonTakeaway').textContent.includes('逐筆 OOF'); }")
                    magnitude_ui_ok = guided_fixture("() => { lessonIndex=9; renderLesson(); const visible=!document.querySelector('#magnitudeExample').hidden; const out=document.querySelector('#magnitudeResult'); const up=out.textContent; document.querySelector('#magnitudeReturn').value='-0.6'; renderMagnitudeExample(); const down=out.textContent; document.querySelector('#magnitudeType').value='log'; document.querySelector('#magnitudeReturn').value='0.6'; renderMagnitudeExample(); const log=out.textContent; document.querySelector('#magnitudePrice').value=''; renderMagnitudeExample(); return visible && up.includes('上漲') && up.includes('0.60%') && up.includes('20,120.00 點') && down.includes('下跌') && down.includes('19,880.00 點') && log.includes('20,120.36 點') && out.textContent.includes('請輸入大於 0'); }")
                    forward_pass_ui_ok = guided_fixture("() => { lessonIndex=15; renderLesson(); const box=document.querySelector('#forwardPassExercise'), out=document.querySelector('#forwardPassResult'); const positive=out.textContent; document.querySelector('#forwardInput').value='-2'; renderForwardPassExercise(); const inactive=out.textContent; document.querySelector('#forwardBias').value='1'; renderForwardPassExercise(); const boundary=out.textContent; return !box.hidden && document.querySelector('#lessonProgress').textContent==='第 16 / 26 步' && positive.includes('z = wx + b = 1.20') && positive.includes('ReLU′(z) = 1') && positive.includes('局部梯度可通過') && inactive.includes('z = wx + b = -0.80') && inactive.includes('ReLU′(z) = 0') && inactive.includes('此處局部梯度為零') && boundary.includes('z = wx + b = 0.00') && boundary.includes('ReLU′(z) = 0'); }")
                    chain_rule_step_ok = guided_fixture("() => { lessonIndex=11; renderLesson(); const body=document.querySelector('#lessonBody').textContent; return document.querySelector('#lessonProgress').textContent==='第 12 / 26 步' && document.querySelector('#lessonTitle').textContent.includes('反向傳播') && body.includes('dL/dw') && body.includes('−8') && body.includes('1.8') && body.includes('0.16') && document.querySelector('#lessonTakeaway').textContent.includes('合成算例'); }")
                    relu_gradient_step_ok = guided_fixture("() => { lessonIndex=12; renderLesson(); const body=document.querySelector('#lessonBody').textContent; const takeaway=document.querySelector('#lessonTakeaway').textContent; return document.querySelector('#lessonProgress').textContent==='第 13 / 26 步' && document.querySelector('#lessonTitle').textContent.includes('ReLU') && body.includes('z=2') && body.includes('dL/dz=2') && body.includes('z=−2') && body.includes('dL/dz=2(0−1)×0=0') && takeaway.includes('不可微') && takeaway.includes('不是整體模型品質'); }")
                    relu_interaction_ok = guided_fixture("() => { lessonIndex=13; renderLesson(); const input=document.querySelector('#reluInput'), target=document.querySelector('#reluTarget'), output=document.querySelector('#reluResult'); const visible=!document.querySelector('#reluExercise').hidden; const positive=output.textContent; target.value='3'; renderReluExercise(); const changedTarget=output.textContent; input.value='-2'; renderReluExercise(); const negative=output.textContent; input.value='0'; renderReluExercise(); const zero=output.textContent; input.value=''; renderReluExercise(); const empty=output.textContent; input.value='2'; target.value='1e308'; renderReluExercise(); const overflow=output.textContent; input.value='8'; target.value='1'; renderReluExercise(); const saturated=output.textContent; return saturated.includes('Sigmoid′(z) = 3.352e-4') && saturated.includes('輸入絕對值較大時') && visible && document.querySelector('#lessonProgress').textContent==='第 14 / 26 步' && positive.includes('ŷ = max(0,z) = 2') && positive.includes('L=(ŷ−y)² = 1') && positive.includes('ReLU′(z) = 1') && positive.includes('Sigmoid′(z) = 1.050e-1') && positive.includes('dL/dz = 2(ŷ−y) × 1 = 2') && changedTarget.includes('L=(ŷ−y)² = 1') && changedTarget.includes('dL/dz = 2(ŷ−y) × 1 = -2') && negative.includes('ŷ = max(0,z) = 0') && negative.includes('dL/dz = 2(ŷ−y) × 0 = 0') && zero.includes('dL/dz = 2(ŷ−y) × 0 = 0') && zero.includes('z=0 不可微') && zero.includes('ReLU′(0)=0 的次梯度慣例') && empty.includes('請輸入可計算的有限神經元值 z 與目標 y') && overflow.includes('請輸入可計算的有限神經元值 z 與目標 y'); }")
                    magnitude_error_lesson_ok = guided_fixture("() => { lessonIndex=14; renderLesson(); const result=document.querySelector('#magnitudeErrorResult'); const visible=!document.querySelector('#magnitudeErrorExercise').hidden; const initial=result.textContent; document.querySelector('#magnitudePredicted').value='-0.2,0.1'; document.querySelector('#magnitudeActual').value='0.2,-0.1'; renderMagnitudeErrorExercise(); const negative=result.textContent; document.querySelector('#magnitudePredicted').value='0'; document.querySelector('#magnitudeActual').value='0'; renderMagnitudeErrorExercise(); const emptyGroup=result.textContent; document.querySelector('#magnitudePredicted').value=''; renderMagnitudeErrorExercise(); const invalid=result.textContent; return visible && document.querySelector('#lessonProgress').textContent==='第 15 / 26 步' && LESSONS.length===26 && initial.includes('實際上漲組 n=1：MAE 0.40 pp') && initial.includes('實際下跌組 n=2：MAE 0.20 pp') && initial.includes('方向錯置 1 筆') && initial.includes('平均絕對幅度預測／實際 0.60／0.20 pp') && initial.includes('平均絕對幅度預測／實際 0.25／0.15 pp') && negative.includes('實際上漲組 n=1：MAE 0.40 pp') && negative.includes('方向錯置 1 筆') && emptyGroup.includes('實際上漲組 n=0：沒有可比較樣本') && invalid.includes('數量相同且有限'); }")
                    multi_forward_pass_ok = guided_fixture("() => { lessonIndex=16; renderLesson(); const output=document.querySelector('#multiForwardPassResult'); const visible=!document.querySelector('#multiForwardPassExercise').hidden; const initial=output.textContent; document.querySelector('#multiInputTarget').value='0'; renderMultiForwardPassExercise(); const targetZero=output.textContent; document.querySelector('#multiInputX1').value='-2'; document.querySelector('#multiInputTarget').value='1'; renderMultiForwardPassExercise(); const negative=output.textContent; document.querySelector('#multiInputX1').value=''; renderMultiForwardPassExercise(); const empty=output.textContent; return visible && document.querySelector('#lessonProgress').textContent==='第 17 / 26 步' && initial.includes('z=0.80') && initial.includes('ŷ = ReLU(z) = 0.80') && initial.includes('有號占比') && initial.includes('w₁x₁=125.0%') && initial.includes('w₂x₂=-50.0%') && initial.includes('∂L/∂w₁=-0.80') && initial.includes('∂L/∂w₂=-0.40') && initial.includes('∂L/∂b=-0.40') && targetZero.includes('∂L/∂b=1.60') && negative.includes('z=-1.20') && negative.includes('ŷ = ReLU(z) = 0.00') && negative.includes('有號占比') && negative.includes('ReLU′(z)=0，所以本例局部梯度為零') && negative.includes('∂L/∂w₁=0.00') && negative.includes('∂L/∂w₂=0.00') && negative.includes('∂L/∂b=0.00') && empty.includes('有限的 x₁、w₁、x₂、w₂、b 與目標 y'); }")
                    gradient_update_ui_ok = guided_fixture("() => { document.querySelector('#multiInputX1').value='2'; document.querySelector('#multiInputW1').value='0.5'; document.querySelector('#multiInputX2').value='1'; document.querySelector('#multiInputW2').value='-0.4'; document.querySelector('#multiInputBias').value='0.2'; document.querySelector('#multiInputTarget').value='1'; document.querySelector('#updateTarget').value='1'; document.querySelector('#updateRate').value='0.1'; lessonIndex=17; renderLesson(); const result=document.querySelector('#gradientUpdateResult'); const visible=!document.querySelector('#gradientUpdateExercise').hidden; const initial=result.textContent; document.querySelector('#updateRate').value='0.5'; renderGradientUpdateExercise(); const changed=result.textContent; document.querySelector('#updateRate').value='1'; renderGradientUpdateExercise(); const doubled=result.textContent; document.querySelector('#updateRate').value='2'; renderGradientUpdateExercise(); const rejected=result.textContent; document.querySelector('#updateRate').value=''; renderGradientUpdateExercise(); const blank=result.textContent; return visible && document.querySelector('#lessonProgress').textContent==='第 18 / 26 步' && initial.includes('梯度：∂L/∂w₁=-0.8000') && initial.includes('∂L/∂w₂=-0.4000') && initial.includes('∂L/∂b=-0.4000') && initial.includes('更新前 L=0.0400') && initial.includes('w₁ 0.5−0.1×(-0.8000)=0.5800') && initial.includes('w₂ -0.4−0.1×(-0.4000)=-0.3600') && initial.includes('b 0.2−0.1×(-0.4000)=0.2400') && initial.includes('一階損失預測 L+∇L·Δθ=-0.0560') && initial.includes('更新後重新計算 L=0.0016') && initial.includes('損失下降') && changed.includes('一階損失預測 L+∇L·Δθ=-0.4400') && changed.includes('更新後重新計算 L=1.0000') && changed.includes('損失上升') && doubled.includes('一階損失預測 L+∇L·Δθ=-0.9200') && doubled.includes('更新後重新計算 L=4.8400') && rejected.includes('學習率需介於 0 與 1') && blank.includes('請輸入有限數值；學習率需介於 0 與 1'); }")
                    gradient_check_ui_ok = guided_fixture("() => { for (const [id,value] of Object.entries({multiInputX1:'2',multiInputW1:'0.5',multiInputX2:'1',multiInputW2:'-0.4',multiInputBias:'0.2',updateTarget:'1',gradientCheckEpsilon:'0.001'})) document.querySelector('#'+id).value=value; lessonIndex=17; renderLesson(); const result=document.querySelector('#gradientCheckResult'), box=document.querySelector('#gradientCheckExercise'); const initial=result.textContent; document.querySelector('#updateTarget').value='0'; renderFiniteDifferenceGradientCheck(); const changed=result.textContent; document.querySelector('#gradientCheckEpsilon').value='0'; renderFiniteDifferenceGradientCheck(); const rejected=result.textContent; return !box.hidden && initial.includes('w₁ 解析=-0.800000、數值≈-0.800000') && initial.includes('最大絕對差=') && changed.includes('w₁ 解析=3.200000') && rejected.includes('ε 需介於 0.00000001 與 0.1'); }")
                    batch_gradient_ui_ok = guided_fixture("() => { lessonIndex=18; renderLesson(); const box=document.querySelector('#batchGradientExercise'), out=document.querySelector('#batchGradientResult'); const initial=out.textContent; document.querySelector('#batchGradientOne').value='-1'; document.querySelector('#batchGradientTwo').value='1'; document.querySelector('#batchGradientThree').value='0'; document.querySelector('#batchGradientFour').value='0'; renderBatchGradientExercise(); const canceled=out.textContent; document.querySelector('#batchGradientOne').value='0'; document.querySelector('#batchGradientTwo').value='0'; renderBatchGradientExercise(); const zero=out.textContent; document.querySelector('#batchGradientFour').value=''; renderBatchGradientExercise(); const empty=out.textContent; return LESSONS.length===26 && document.querySelector('#lessonProgress').textContent==='第 19 / 26 步' && !box.hidden && initial.includes('1 筆為負') && initial.includes('3 筆為正') && initial.includes('÷ 4 = 1.0000') && initial.includes('淨梯度占總絕對梯度比例 = 0.5000') && initial.includes('正負梯度互相抵銷一部分') && initial.includes('批次更新一次') && initial.includes('= 1.9000') && initial.includes('完整 batch 平均一次更新到 1.9000') && initial.includes('mini-batch、每批各更新一次，權重依序 1.9000 → 1.8000') && initial.includes('維持同四筆梯度，只改成 (1,3) 與 (2,4) 分批，權重路徑變為 2.0500 → 1.8000') && initial.includes('兩種 mini-batch 分組的終點同為 1.8000') && initial.includes('單次 full-batch 只更新一次，因此終點是 1.9000') && canceled.includes('比例 = 0.0000') && canceled.includes('正負方向完全抵銷') && zero.includes('比例 = 未定義（全部梯度為零）') && empty.includes('請輸入權重、四個有限梯度'); }")
                    momentum_step_checks = guided_fixture("() => { lessonIndex=19; renderLesson(); const box=document.querySelector('#momentumExercise'), out=document.querySelector('#momentumResult'); const initial=out.textContent; document.querySelector('#momentumNextGradient').value=''; renderMomentumExercise(); const empty=out.textContent; document.querySelector('#momentumNextGradient').value='0.5'; renderMomentumExercise(); const direction=document.querySelector('#momentumDirectionResult').textContent; document.querySelector('#momentumVectorDimension').value='2'; renderMomentumDirection(); const direction2d=document.querySelector('#momentumDirectionResult').textContent; return {visible:!box.hidden,step:document.querySelector('#lessonProgress').textContent==='第 20 / 26 步',first:initial.includes('vₜ = 1.4500，wₜ = 1.8550'),second:initial.includes('vₜ₊₁ = 0.9 × 1.4500 + 0.5000 = 1.8050，wₜ₊₁ = 1.6745'),third:initial.includes('vₜ₊₂ = 0.9 × 1.8050 + -2.0000 = -0.3755，wₜ₊₂ = 1.71205'),reversal:initial.includes('第三步速度已反向') && initial.includes('權重上升'),trace:initial.includes('目前設定三步為 1.8550 → 1.6745 → 1.71205'),blank:empty.includes('請輸入七個有限數值'),direction3d:direction.includes('維度=3') && direction.includes('夾角=53.40°') && direction.includes('大致同向') && direction.includes('分解核對：|v|²=9.0000，平行分量²＋垂直分量²=9.0000'),direction2d:direction2d.includes('維度=2') && direction2d.includes('夾角=36.87°') && direction2d.includes('大致同向') && direction2d.includes('分解核對：|v|²=5.0000，平行分量²＋垂直分量²=5.0000'),scaleNote:document.querySelector('#momentumExercise').textContent.includes('把任一非零向量放大或縮小正倍數，角度不變')}; }")
                    momentum_steps_ui_ok = all(momentum_step_checks.values())
                    momentum_direction_math_ok = page.evaluate("() => { const same=calculateMomentumDirection(0.5,0,1,0), opposite=calculateMomentumDirection(0.5,0,-1,0), orthogonal=calculateMomentumDirection(1,0,0,2), three=calculateMomentumDirection(1,2,2,2,1,0), ordinary=calculateMomentumDirection(1,2,2,1), tiny=calculateMomentumDirection(1e-200,2e-200,2e-200,1e-200), zero=calculateMomentumDirection(0,0,1,0), invalid=calculateMomentumDirection('',0,1,0); return same.cosine===1 && same.angleDegrees===0 && same.parallel===0.5 && same.perpendicular===0 && opposite.cosine===-1 && opposite.angleDegrees===180 && opposite.parallel===-0.5 && orthogonal.cosine===0 && orthogonal.angleDegrees===90 && orthogonal.parallel===0 && orthogonal.perpendicular===1 && three.vNorm===3 && Math.abs(three.gNorm-Math.sqrt(5))<1e-12 && Math.abs(three.cosine-0.5962847940)<1e-9 && Math.abs(three.angleDegrees-53.40)<0.01 && tiny && Math.abs(tiny.cosine-0.8)<1e-12 && Math.abs(tiny.angleDegrees-36.8698976458)<1e-9 && Math.abs(tiny.angleDegrees-ordinary.angleDegrees)<1e-9 && zero.cosine===null && zero.angleDegrees===null && zero.relation.includes('零向量') && invalid===null; }")
                    interval_ui_ok = guided_fixture("() => { lessonIndex=10; renderLesson(); const visible=!document.querySelector('#predictionIntervalExample').hidden; const initial=document.querySelector('#predictionIntervalResult').textContent; document.querySelector('#intervalSpread').value='0.7'; renderPredictionIntervalExample(); const changed=document.querySelector('#predictionIntervalResult').textContent; document.querySelector('#intervalSpread').value='-1'; renderPredictionIntervalExample(); const rejected=document.querySelector('#predictionIntervalResult').textContent.includes('非負誤差尺度'); return visible && initial.includes('0.20% 至 1.00%') && changed.includes('-0.10% 至 1.30%') && rejected && document.querySelector('#lessonProgress').textContent==='第 11 / 26 步' && document.querySelector('#lessonTakeaway').textContent.includes('不是本模型估出的區間'); }")
                    # The widgets are intentionally bound to different lessons.
                    # Assert the interval step hides the ReLU calculator to catch stale indices.
                    relu_widget_at_interval_step = guided_fixture("() => { lessonIndex=10; renderLesson(); return !document.querySelector('#predictionIntervalExample').hidden && document.querySelector('#reluExercise').hidden; }")
                    activation_ui_ok = guided_fixture("() => { lessonIndex=20; renderLesson(); const section=document.querySelector('#activationExercise'); const input=document.querySelector('#activationInput'); const target=document.querySelector('#activationTarget'); const output=document.querySelector('#activationResult'); const initial=output.textContent; target.value='0'; renderActivationExercise(); const zeroTarget=output.textContent; input.value='8'; target.value='1'; renderActivationExercise(); const saturated=output.textContent; input.value='-8'; renderActivationExercise(); const negativeSaturated=output.textContent; input.value=''; renderActivationExercise(); const invalid=output.textContent; target.value='2'; input.value='2'; renderActivationExercise(); const highTarget=output.textContent; return !section.hidden && initial.includes('平方損失 0.0142') && initial.includes('Sigmoid=0.8808') && initial.includes('平方損失 1.0000') && initial.includes('平方損失 0.0013') && initial.includes('平方損失梯度 -2.503e-2') && initial.includes('目標在輸出範圍') && zeroTarget.includes('平方損失 0.7758') && zeroTarget.includes('平方損失梯度 1.850e-1') && saturated.includes('平方損失梯度 -2.248e-7') && saturated.includes('對稱輸入 +|z| 與 −|z| 的 Sigmoid／Tanh 局部導數相同') && negativeSaturated.includes('Sigmoid=0.0003') && invalid.includes('請輸入有限') && highTarget.includes('Sigmoid=0.8808') && highTarget.includes('目標不在輸出範圍') && highTarget.includes('ReLU=2.0000') && document.querySelector('#lessonProgress').textContent==='第 21 / 26 步'; }")
                    relu_dead_zone_ui_ok = guided_fixture("() => { lessonIndex=20; renderLesson(); const input=document.querySelector('#activationInput'), target=document.querySelector('#activationTarget'), output=document.querySelector('#activationResult'); input.value='-2'; target.value='1'; renderActivationExercise(); const negative=output.textContent; input.value='0'; renderActivationExercise(); const boundary=output.textContent; return negative.includes('ReLU 負區提示：目標雖在輸出範圍且損失非零，局部導數仍為零') && negative.includes('只靠這個神經元的梯度更新無法離開負區') && boundary.includes('ReLU 負區提示'); }")
                    clipping_ui_ok = guided_fixture("() => { lessonIndex=21; renderLesson(); const box=document.querySelector('#gradientClippingExercise'), input=document.querySelector('#clippingGradient'), output=document.querySelector('#gradientClippingResult'), sweep=document.querySelector('#clippingSweepResult'); const initial=output.textContent, sweepInitial=sweep.textContent; input.value='0.5'; renderGradientClippingExercise(); const within=output.textContent; input.value='0'; renderGradientClippingExercise(); const zero=output.textContent; input.value=''; renderGradientClippingExercise(); return !box.hidden && sweepInitial.includes('上限 0 → 裁剪梯度 0.00、新權重 2.00') && sweepInitial.includes('上限 0.5 → 裁剪梯度 0.50、新權重 1.95') && sweepInitial.includes('上限 1 → 裁剪梯度 1.00、新權重 1.90') && sweepInitial.includes('上限 4 → 裁剪梯度 4.00、新權重 1.60') && initial.includes('步幅為 0.4000') && initial.includes('權重更新為 1.6000') && initial.includes('裁剪為 1.0000') && initial.includes('保留原梯度大小的 25.0%') && initial.includes('步幅為 0.1000') && initial.includes('權重更新為 1.9000') && within.includes('保留原梯度大小的 100.0%') && within.includes('步幅為 0.0500') && within.includes('權重更新為 1.9500') && zero.includes('保留原梯度大小的 100.0%') && output.textContent.includes('請輸入四個有限數值') && document.querySelector('#lessonProgress').textContent==='第 22 / 26 步' && document.querySelector('#lessonTakeaway').textContent.includes('不保證損失下降'); }")
                    gradient_descent_trace_ok = guided_fixture("() => { lessonIndex=22; renderLesson(); const box=document.querySelector('#gradientDescentTrace'), output=document.querySelector('#gradientDescentTraceResult'), comparison=document.querySelector('#gradientDescentRateComparison'), rate=document.querySelector('#traceLearningRate'), curvature=document.querySelector('#traceCurvature'), start=document.querySelector('#traceStartWeight'); const initial=output.textContent, rates=comparison.textContent; rate.value='0.75'; renderGradientDescentTrace(); const selectedAlternating=output.textContent; rate.value='1'; renderGradientDescentTrace(); const overshoot=output.textContent; curvature.value='2'; rate.value='0.5'; renderGradientDescentTrace(); const oscillation=output.textContent, curvedRates=comparison.textContent; rate.value='0.75'; renderGradientDescentTrace(); const divergence=output.textContent; curvature.value='6'; renderGradientDescentTrace(); const invalid=comparison.textContent; curvature.value='5'; start.value='1e308'; renderGradientDescentTrace(); const overflow=output.textContent; return !box.hidden && document.querySelector('#lessonProgress').textContent==='第 23 / 26 步' && initial.includes('目前設定 ηc=0.25，有號誤差倍率=0.50（不越過最低點而收斂）') && selectedAlternating.includes('目前設定 ηc=0.75，有號誤差倍率=-0.50（交替越過最低點並收斂）') && initial.includes('L=1(w−1)²') && initial.includes('步驟 4：w=1.1250，距最低點 |w−1|=0.1250，有號誤差倍率=0.5000') && initial.includes('步驟 1：w=2.0000，距最低點 |w−1|=1.0000，有號誤差倍率=0.5000') && rates.includes('η=0.5（誤差倍率 0.00；一步到達最低點）→ 損失 4.0000→0.0000→0.0000→0.0000→0.0000') && rates.includes('η=1（誤差倍率 -1.00；邊界振盪）→ 損失 4.0000→4.0000→4.0000→4.0000→4.0000') && overshoot.includes('步驟 1：w=-1.0000') && oscillation.includes('步驟 1：w=-1.0000') && oscillation.includes('步驟 2：w=3.0000') && oscillation.includes('有號誤差倍率=-1.0000') && curvedRates.includes('η=0.25（誤差倍率 0.00；一步到達最低點）') && curvedRates.includes('η=0.5（誤差倍率 -1.00；邊界振盪）') && curvedRates.includes('η=1（誤差倍率 -3.00；發散（交替遠離最低點））') && divergence.includes('步驟 1：w=-3.0000') && divergence.includes('步驟 2：w=9.0000') && invalid.includes('完成有效輸入') && overflow.includes('若更新後超出數值範圍'); }")
                    adam_step_ui_ok = guided_fixture("() => { lessonIndex=23; renderLesson(); const box=document.querySelector('#adamStepExercise'), out=document.querySelector('#adamStepResult'), initial=out.textContent; document.querySelector('#adamGradient').value='-2'; renderAdamStepExercise(); const negative=out.textContent; document.querySelector('#adamBeta1').value='1'; renderAdamStepExercise(); const invalid=out.textContent; document.querySelector('#adamBeta1').value='0.9'; document.querySelector('#adamGradient').value=''; renderAdamStepExercise(); const blank=out.textContent; return !box.hidden && LESSONS.length===26 && document.querySelector('#lessonProgress').textContent==='第 24 / 26 步' && initial.includes('m₁=0.2000、v₁=0.0040') && initial.includes('m̂₁=2.0000、v̂₁=4.0000') && initial.includes('SGD 位移=0.2000，w₁=0.8000') && initial.includes('Adam 位移=0.1000，w₁=0.9000') && negative.includes('Adam 位移=-0.1000，w₁=1.1000') && invalid.includes('0 ≤ β₁、β₂ < 1') && blank.includes('請輸入有限梯度'); }")
                    adam_two_step_ui_ok = guided_fixture("() => { lessonIndex=24; renderLesson(); const box=document.querySelector('#adamTwoStepExercise'), out=document.querySelector('#adamTwoStepResult'), initial=out.textContent; document.querySelector('#adamBeta22').value='0.9'; renderAdamTwoStepExercise(); const lowerBeta2=out.textContent; document.querySelector('#adamBeta22').value='0.999'; document.querySelector('#adamGradient2').value='2'; renderAdamTwoStepExercise(); const aligned=out.textContent; document.querySelector('#adamGradient2').value='0'; renderAdamTwoStepExercise(); const zero=out.textContent; document.querySelector('#adamGradient1').value='0.00001'; renderAdamTwoStepExercise(); const tinyZero=out.textContent; document.querySelector('#adamGradient1').value='2'; document.querySelector('#adamGradient2').value='-1.8'; renderAdamTwoStepExercise(); const cancelled=out.textContent; document.querySelector('#adamGradient2').value='-1.79999'; renderAdamTwoStepExercise(); const nearCancelled=out.textContent; document.querySelector('#adamGradient1').value='0'; document.querySelector('#adamGradient2').value='0'; renderAdamTwoStepExercise(); const bothZero=out.textContent; document.querySelector('#adamGradient1').value='2'; document.querySelector('#adamGradient2').value=''; renderAdamTwoStepExercise(); const invalid=out.textContent; document.querySelector('#adamGradient2').value='-1'; document.querySelector('#adamEpsilon2').value='0.1'; renderAdamTwoStepExercise(); const epsilon=out.textContent; document.querySelector('#adamGradient1').value='1e-200'; document.querySelector('#adamGradient2').value='-1e-200'; document.querySelector('#adamEpsilon2').value='1e-300'; renderAdamTwoStepExercise(); const underflow=out.textContent; return !box.hidden && LESSONS.length===26 && document.querySelector('#lessonProgress').textContent==='第 25 / 26 步' && initial.includes('歷史項 β₁m₁=0.1800，當步項 (1−β₁)g₂=-0.1000，相加 m₂=0.0800') && initial.includes('m̂₂=0.4211、v̂₂=2.4992') && initial.includes('方向相反') && initial.includes('β₂ 記憶對照（相同梯度）：β₂=0 時分母 1.0000、更新量 0.0421；目前 β₂=0.999 時分母 1.5809、更新量 0.0266') && initial.includes('梯度同乘 10（固定 β、η、ε）：Adam 更新量 0.0266；SGD w₂=0.0000（原本 0.9000）') && lowerBeta2.includes('目前 β₂=0.900 時分母 1.5560、更新量 0.0271') && zero.includes('g₂=0.0000 沒有方向') && zero.includes('仍保留先前累積方向') && !zero.includes('方向相反') && tinyZero.includes('m̂₂=4.74e-6') && !tinyZero.includes('m̂₂=0.0000') && cancelled.includes('m̂₂=0.0000') && cancelled.includes('歷史與當步梯度恰好抵銷') && cancelled.includes('第二步沒有更新方向') && !cancelled.includes('方向相反') && nearCancelled.includes('m̂₂=5.26e-6') && nearCancelled.includes('方向相反') && !nearCancelled.includes('m̂₂=0.0000') && bothZero.includes('當步梯度 g₂ 與 Adam 校正動差 m̂₂ 都為零') && initial.includes('√v̂₂+ε=1.5809+1.0e-8=1.5809') && initial.includes('ηm̂₂/(√v̂₂+ε)=0.0266') && initial.includes('權重改變 −0.0266') && initial.includes('w₂=0.8734') && initial.includes('SGD 的 w₂=0.9000') && aligned.includes('m₂=0.3800') && aligned.includes('方向相同') && invalid.includes('請輸入兩個有限梯度') && epsilon.includes('√v̂₂+ε=1.5809+1.0e-1=1.6809') && epsilon.includes('ηm̂₂/(√v̂₂+ε)=0.0250') && epsilon.includes('權重改變 −0.0250') && epsilon.includes('w₂=0.8797') && underflow.includes('低於數值範圍') && calculateAdamTwoSteps(1e-200,-1e-200,0.1,0.9,0.999,1e-300)===null && calculateAdamTwoSteps(2,-1,0.1,0.9,0.999)!==null && calculateAdamTwoSteps('',-1,0.1,0.9,0.999)===null && calculateAdamTwoSteps(2,-1,0.1,0.9,0.999,'')===null; }")
                    l2_regularization_ui_ok = guided_fixture("() => { lessonIndex=LESSONS.findIndex(item=>item.title==='正則化梯度會把權重拉向零'); renderLesson(); const box=document.querySelector('#l2RegularizationExercise'), out=document.querySelector('#l2RegularizationResult'), initial=out.textContent, sweep=document.querySelector('#l2CancellationSweepResult').textContent; document.querySelector('#l2Rate').value='0.5'; renderL2RegularizationExercise(); const stable=out.textContent; document.querySelector('#l2Rate').value=(1/1.1).toString(); renderL2RegularizationExercise(); const critical=out.textContent; document.querySelector('#l2Rate').value='2'; renderL2RegularizationExercise(); const divergent=out.textContent; document.querySelector('#l2Rate').value='0.1'; document.querySelector('#l2Lambda').value='0'; renderL2RegularizationExercise(); const noPenalty=out.textContent; document.querySelector('#l2Weight').value='0.5'; document.querySelector('#l2Lambda').value='0.5'; renderL2RegularizationExercise(); const dataLeads=out.textContent; document.querySelector('#l2Lambda').value='1.5'; renderL2RegularizationExercise(); const penaltyLeads=out.textContent; document.querySelector('#l2Lambda').value='1'; renderL2RegularizationExercise(); const canceled=out.textContent; document.querySelector('#l2Weight').value='2'; document.querySelector('#l2Lambda').value='0.1'; renderL2RegularizationExercise(); document.querySelector('#l2Weight').value=''; renderL2RegularizationExercise(); const blank=out.textContent; const tiny=calculateL2CancellationExample(); const clauses={learningRateStability:stable.includes('η 小於臨界值，這個二次目標的誤差會逐步縮小') && critical.includes('η 等於臨界值，誤差每步反號且大小不變') && divergent.includes('η 大於臨界值，這個二次目標的誤差會逐步放大') && initial.includes('臨界學習率 η*=1/(1+λ)=0.9091') && initial.includes('η=0.4545 → 倍率 0.0000（一步到達最低點）') && initial.includes('η=0.9091 → 倍率 -1.0000（等距反向）') && initial.includes('η=1.3636 → 倍率 -2.0000（誤差放大）'), visible:!box.hidden && document.querySelector('#lessonProgress').textContent==='第 26 / 26 步', regularizedOptimum:initial.includes('總目標最低點 w*=1/(1+λ)=0.9091；λ>0 時懲罰會把最低點拉向零，低於資料單獨偏好的 1') && initial.includes('最低點的損失分解：資料 0.0083、懲罰 0.0826、合計 0.0909'), defaultLossAndGradient:initial.includes('距最低點 1.0909→0.8509（有號倍率 0.7800）') && initial.includes('損失占比：資料 71.4%、懲罰 28.6%') && initial.includes('梯度貢獻率：資料 83.3%、懲罰 16.7%') && initial.includes('資料梯度 2(w−1)=2.0000') && initial.includes('懲罰梯度 2λw=0.4000') && initial.includes('ΔLdata=-0.4224') && initial.includes('ΔLpenalty=-0.0902') && initial.includes('合計 ΔL=-0.5126') && initial.includes('總梯度=2.4000') && initial.includes('兩項梯度同向'), ratioSweep:sweep.includes('總梯度 1.0e-13，0.50 的相對差，資料項主導') && sweep.includes('總梯度 0.0e+0，正好抵銷') && sweep.includes('近乎抵銷（懲罰/資料梯度比 1.0）') && sweep.includes('5.0e-13 的相對差，懲罰項主導') && sweep.includes('總梯度 -1.0e-13，0.33 的相對差，懲罰項主導') && sweep.includes('梯度下降的權重位移方向與總梯度相反'), lambdaZero:noPenalty.includes('λ=0，更新只由資料梯度決定') && noPenalty.includes('總目標最低點 w*=1/(1+λ)=1.0000；λ=0 時沒有懲罰，最低點仍是資料目標偏好的 w=1') && noPenalty.includes('最低點的損失分解：資料 0.0000、懲罰 0.0000、合計 0.0000') && noPenalty.includes('更新後 w=1.8000'), dominance:dataLeads.includes('資料項主導合力方向') && penaltyLeads.includes('懲罰項主導合力方向'), exactCancellation:canceled.includes('相反且等大，正好抵銷') && canceled.includes('梯度貢獻率：資料 未定義（總梯度為零）、懲罰 未定義（總梯度為零）'), invalidInput:blank.includes('請輸入有限權重'), numericGuards:tiny.relativeDifference===0.5 && classifyOpposingGradients(2e-13,-1e-13)==='data' && classifyOpposingGradients(2e-13,-2e-13)==='cancel' && calculateL2Regularization(1e154,0.1,1)===null}; window.__l2LessonChecks=clauses; return Object.values(clauses).every(Boolean); }")
                    vector_clipping_ui_ok = guided_fixture("() => { lessonIndex=21; renderLesson(); const input=document.querySelector('#vectorGradientResult'); const initial=input.textContent; document.querySelector('#vectorGradientOne').value='0.3'; document.querySelector('#vectorGradientTwo').value='0.4'; renderVectorGradientClipping(); const within=input.textContent; document.querySelector('#vectorGradientOne').value=''; renderVectorGradientClipping(); const empty=input.textContent; const three=document.querySelector('#vectorGradientThreeResult'); const threeInitial=three.textContent; document.querySelector('#vectorGradientThreeOne').value=''; renderVectorGradientClipping3(); const threeEmpty=three.textContent; return initial.includes('範數 5.0000') && initial.includes('縮放比例 0.2000') && initial.includes('(0.6000, 0.8000)') && initial.includes('新範數 1.0000') && within.includes('範數 0.5000') && within.includes('縮放比例 1.0000') && within.includes('(0.3000, 0.4000)') && empty.includes('請輸入兩個有限') && threeInitial.includes('範數 3.0000') && threeInitial.includes('縮放比例 0.3333') && threeInitial.includes('(0.6667, -0.3333, 0.6667)') && threeInitial.includes('新範數 1.0000') && threeEmpty.includes('請輸入三個有限'); }")
                    vector_three_math_ok = page.evaluate("() => { const x=calculateVectorGradientClipping3(2,-1,2,1); const ratio=x.clipped[0]/x.clipped[2]; return Math.abs(x.norm-3)<1e-12 && Math.abs(x.scale-1/3)<1e-12 && Math.abs(x.clipped[0]-2/3)<1e-12 && Math.abs(x.clipped[1]+1/3)<1e-12 && Math.abs(x.clipped[2]-2/3)<1e-12 && Math.abs(x.clippedNorm-1)<1e-12 && ratio===1 && calculateVectorGradientClipping3('',-1,2,1)===null && calculateVectorGradientClipping3(2,-1,2,-1)===null }")
                    weight_decay_checks = guided_fixture("() => { const guidedTab=document.querySelector('#tabGuided'); if(guidedTab.getAttribute('aria-selected')!=='true') guidedTab.click(); lessonIndex=LESSONS.findIndex(item=>item.title==='正則化梯度會把權重拉向零'); renderLesson(); const box=document.querySelector('#weightDecayComparisonExercise'), out=document.querySelector('#weightDecayComparisonResult'), adam=document.querySelector('#adamWeightDecayResult'), note=box.querySelector('small').textContent, initial=out.textContent, initialAdam=adam.textContent; document.querySelector('#weightDecayGradient').value='-1'; document.querySelector('#weightDecayWeight').value='0.25'; document.querySelector('#weightDecayRate').value='0.2'; document.querySelector('#weightDecayStrength').value='0.4'; renderWeightDecayComparison(); const changed=out.textContent, changedAdam=adam.textContent; document.querySelector('#weightDecayGradient').value=''; renderWeightDecayComparison(); const blank=out.textContent, blankAdam=adam.textContent; const visible=lessonIndex>=0 && !box.hidden; const noteOk=note.includes('同一組輸入也會即時計算 Adam 第一步') && note.includes('ε=10⁻⁸'); const sgdDefault=initial.includes('權重保留比例 1−ηλ=0.9900') && initial.includes('梯度更新量 −ηg=-0.0500；衰減更新量 −ηλw=-0.0200') && initial.includes('耦合 L2 更新 w=1.9300；解耦權重衰減 w=1.9300；差=0.0000'); const sgdChanged=changed.includes('權重保留比例 1−ηλ=0.9200') && changed.includes('梯度更新量 −ηg=0.2000；衰減更新量 −ηλw=-0.0200') && changed.includes('耦合 L2 更新 w=0.4300；解耦權重衰減 w=0.4300；差=0.0000'); const adamDefault=initialAdam.includes('耦合 L2 w=1.9000；解耦權重衰減 w=1.8800；差=-0.0200'); const adamChanged=changedAdam.includes('耦合 L2 w=0.4500；解耦權重衰減 w=0.4300；差=-0.0200'); const blankOk=blank.includes('請輸入有限數值') && blankAdam.includes('Adam 對照暫無結果'); return {visible,noteOk,sgdDefault,sgdChanged,adamDefault,adamChanged,blankOk}; }")
                    vector_four_math_ok = page.evaluate("() => { const x=calculateVectorGradientClippingN([1,2,2,4],2), zero=calculateVectorGradientClippingN([0,0,0,0],2); return Math.abs(x.norm-5)<1e-12 && x.scale===0.4 && JSON.stringify(x.clipped)==='[0.4,0.8,0.8,1.6]' && Math.abs(x.clippedNorm-2)<1e-12 && JSON.stringify(x.componentClipped)==='[1,2,2,2]' && Math.abs(x.componentClippedNorm-Math.sqrt(13))<1e-12 && zero.norm===0 && zero.scale===1 && JSON.stringify(zero.clipped)==='[0,0,0,0]' && calculateVectorGradientClippingN([1,'',2,4],2)===null && calculateVectorGradientClippingN([1,2,2,4],-1)===null && calculateVectorGradientClippingN(Array(65).fill(1),2)===null }")
                    vector_four_ui_ok = guided_fixture("() => { lessonIndex=21; renderLesson(); const output=document.querySelector('#vectorGradientFourResult'), initial=output.textContent; document.querySelector('#vectorGradientFourOne').value=''; renderVectorGradientClipping4(); const invalid=output.textContent; ['vectorGradientFourOne','vectorGradientFourTwo','vectorGradientFourThree','vectorGradientFourFour'].forEach(id=>document.querySelector('#'+id).value='0'); renderVectorGradientClipping4(); const zero=output.textContent; return initial.includes('範數 5.0000') && initial.includes('縮放比例 0.4000') && initial.includes('(0.4000, 0.8000, 0.8000, 1.6000)') && initial.includes('新範數 2.0000') && initial.includes('餘弦 1.0000、偏轉角 0.00°') && initial.includes('餘弦 0.9430、偏轉角 19.44°') && initial.includes('(1.0000, 2.0000, 2.0000, 2.0000)') && initial.includes('範數 3.6056') && invalid.includes('請輸入四個有限') && zero.includes('原始 L2 範數 0.0000') && zero.includes('沒有更新方向；裁剪不會產生新的梯度'); }")
                    conversion_ok = lesson_eighth_visible and learning_rate_step_ok and magnitude_ui_ok and forward_pass_ui_ok and oversized_step_loss_ok and negative_gradient_direction_ok and zero_gradient_direction_ok and empty_gradient_input_ok and magnitude_step_ok and interval_ui_ok and relu_widget_at_interval_step and chain_rule_step_ok and relu_gradient_step_ok and relu_interaction_ok and magnitude_error_lesson_ok and multi_forward_pass_ok and gradient_update_ui_ok and gradient_check_ui_ok and batch_gradient_ui_ok and momentum_steps_ui_ok and momentum_direction_math_ok and simple_conversion_ok and log_conversion_ok and log_below_minus_100_ok and simple_below_minus_100_ok and activation_ui_ok and relu_dead_zone_ui_ok and clipping_ui_ok and gradient_descent_trace_ok and adam_step_ui_ok and adam_two_step_ui_ok and l2_regularization_ui_ok and vector_clipping_ui_ok and vector_three_math_ok and vector_four_ui_ok and vector_four_math_ok and all(weight_decay_checks.values())
                    checks.append({"name": "報酬與區間互動教學", "status": "PASS" if conversion_ok else "FAIL", "detail": f"所在步驟={lesson_eighth.group(1) if lesson_eighth else 'unknown'}; 學習率={learning_rate_step_ok}; 預測幅度={magnitude_step_ok}; 可調算例={magnitude_ui_ok}; 單一神經元梯度閘門={forward_pass_ui_ok}; 區間預設／修改／錯誤輸入={interval_ui_ok}; 區間步驟/ReLU 隱藏狀態={relu_widget_at_interval_step}; 鏈鎖律步驟={chain_rule_step_ok}; ReLU 梯度說明={relu_gradient_step_ok}; ReLU 輸入互動={relu_interaction_ok}; 第十五步方向／幅度={magnitude_error_lesson_ok}; 第十七步多輸入前向傳播={multi_forward_pass_ok}; 第十八步梯度更新={gradient_update_ui_ok}; 有限差分核對={gradient_check_ui_ok}; 第十九步批次梯度互動={batch_gradient_ui_ok}; 第二十步動量子句={momentum_step_checks}; 方向餘弦邊界={momentum_direction_math_ok}; 大學習率損失上升={oversized_step_loss_ok}; 負梯度權重上升={negative_gradient_direction_ok}; 零梯度權重不變={zero_gradient_direction_ok}; 空梯度輸入拒絕={empty_gradient_input_ok}; 第八步與練習可見={lesson_eighth_visible}; 簡單報酬={simple_conversion_ok}; 對數報酬={log_conversion_ok}; 對數 −101%={log_below_minus_100_ok}; 簡單 −101%={simple_below_minus_100_ok}; Sigmoid／ReLU 比較={activation_ui_ok}; ReLU 負區零梯度={relu_dead_zone_ui_ok}; 梯度裁剪互動={clipping_ui_ok}; 多步梯度下降軌跡={gradient_descent_trace_ok}; Adam 首步偏差校正={adam_step_ui_ok}; Adam 反向梯度動差記憶={adam_two_step_ui_ok}; L2 正則化互動={l2_regularization_ui_ok}（失敗子句={l2_lesson_failures}）; 二維向量={vector_clipping_ui_ok}; 三維範數={vector_three_math_ok}; 四維範數與拒絕條件={vector_four_math_ok}; 四維畫面={vector_four_ui_ok}; 純 SGD 權重衰減={weight_decay_checks}"})
                    page.locator("#tabGuided").click()
                    page.locator("#lessonBack").click()
                    page.locator("#tabQuiz").click()
                    page.locator('#quizChoices input[value="1"]').check()
                    page.locator("#quizNext").click()
                    quiz_ok = "答對了" in page.locator("#quizFeedback").inner_text()
                    page.locator("#tabGuided").click()
                    page.locator("#tabLab").click()
                    page.locator('input[name="crossAssetAnswer"][value="better"]').check()
                    page.locator("#checkCrossAsset").click()
                    cross_asset_wrong = "沒有比較預測與實際誤差" in page.locator("#crossAssetFeedback").inner_text()
                    page.locator('input[name="crossAssetAnswer"][value="insufficient"]').check()
                    page.locator("#checkCrossAsset").click()
                    cross_asset_right = "答對了" in page.locator("#crossAssetFeedback").inner_text()
                    cross_asset_visible = (page.locator("#crossAssetLesson").is_visible() and
                                           page.locator(".learning-data-note").is_visible() and
                                           "合成教學資料" in page.locator(".learning-data-note").inner_text() and
                                           "實際 0.60 · 預測 0.80 個百分點，差 0.20" in page.locator("#crossAssetLesson").inner_text() and
                                           "實際 1.00 · 預測 1.40 個百分點，差 0.40" in page.locator("#crossAssetLesson").inner_text() and
                                           "實際 0.50 · 預測 0.70 個百分點，差 0.20" in page.locator("#crossAssetLesson").inner_text() and
                                           "實際 0.80 · 預測 1.20 個百分點，差 0.40" in page.locator("#crossAssetLesson").inner_text() and
                                           "乙組高估較多" in page.locator("#crossAssetLesson").inner_text() and
                                           "OOF 誤差" in page.locator(".learning-checklist").inner_text() and
                                           "有效 n" in page.locator(".learning-checklist").inner_text() and
                                           "預測幅度校準" in page.locator(".learning-checklist").inner_text())
                    saved_compare = page.evaluate("""() => {
                      const record={config:{symbol:'2330.TW',horizon:1,lookback:5,returnType:'simple'},result:{models:[{key:'mlp',mae:.01,folds:[{from:'2024-01-01',to:'2024-02-01',predictions:[{actual:.01,predicted:.02},{actual:'',predicted:.02},{actual:.03,predicted:null},{actual:'bad',predicted:.01}]}]}],comparisons:[{key:'naive',name:'naive',mae:.012}]}};
                      const line=savedValidationSummary(record,'Fixture');
                      const missing=savedValidationSummary(null,'Missing');
                      const modelBetter=savedValidationSummary({result:{models:[{key:'mlp',mae:.01,folds:[]}],comparisons:[{key:'naive',name:'naive',mae:.008}]}},'Model better');
                      const tinyDelta=savedValidationSummary({result:{models:[{key:'mlp',mae:.01,folds:[]}],comparisons:[{key:'naive',mae:.010000001}]}},'Tiny delta');
                      const noBaseline=savedValidationSummary({result:{models:[{key:'mlp',mae:.01,folds:[]}],comparisons:[]}},'No baseline');
                      const nullBaseline=savedValidationSummary({result:{models:[{key:'mlp',mae:.01,folds:[]}],comparisons:[{key:'naive',name:'naive',mae:null}]}},'Null baseline');
                      const nullModel=savedValidationSummary({result:{models:[{key:'mlp',mae:null,folds:[]}],comparisons:[{key:'naive',name:'naive',mae:.008}]}},'Null model');
                      const target=document.createElement('div'); renderSavedComparisonLines(target,[{...line,label:'<img src=x onerror=alert(1)>'}]);
                      const escapedMarkup=target.querySelector('img')===null&&target.querySelector('.saved-comparison-title').textContent==='<img src=x onerror=alert(1)>';
                      const legacyGuard=savedComparisonCompatibility([line,{...line,label:'Peer'}]);
                      const sharedSetup={features:['return_1','return_5'],lookback:5,epochs:10,batchSize:16,hiddenUnits:8,hiddenLayers:1,dropout:0,learningRate:0.01,optimizer:'adam',loss:'mse',seed:7};
                      const compatibleA=savedValidationSummary({config:{symbol:'2330.TW',...sharedSetup,horizon:1,returnType:'simple'},result:{execution:'next_close',horizon:1,returnType:'simple',models:[{key:'mlp',mae:.01,folds:[{from:'2024-01-01',to:'2024-02-01',predictions:[{actual:.01,predicted:.02}]}]}],comparisons:[{key:'naive',name:'naive',mae:.012}]}},'Fixture A'); const compatibleB=savedValidationSummary({config:{symbol:'2317.TW',...sharedSetup,horizon:1,returnType:'simple'},result:{execution:'next_close',horizon:1,returnType:'simple',models:[{key:'mlp',mae:.011,folds:[{from:'2024-01-01',to:'2024-02-01',predictions:[{actual:.01,predicted:.02}]}]}],comparisons:[{key:'naive',name:'naive',mae:.013}]}},'Fixture B'); const compatibleGuard=savedComparisonCompatibility([compatibleA,compatibleB]);
                      const featureMismatch=savedComparisonCompatibility([{...line,execution:'next_close'},{...line,label:'Peer',execution:'next_close',setupSignature:'different features'}]);
                      const statusVisible=target.querySelector('.saved-comparison-compatibility')?.textContent.includes('不可直接排名');
                      const compatibleHasAllTerms=['目標協定','模型','訓練設定','預測期間','報酬定義','驗證日期'].every(term=>compatibleGuard.includes(term));
                      return line.mae==='1.000%'&&line.baseline==='naive · 1.200%'&&line.delta==='-0.200 個百分點 · 本次驗證誤差較小'&&line.samples===1&&line.model==='MLP'&&line.period==='2024-01-01 至 2024-02-01'&&line.direction.includes('平均絕對幅度（各自方向內）')&&modelBetter.delta==='+0.200 個百分點 · 本次驗證誤差較大'&&tinyDelta.delta==='−<0.001 個百分點 · 本次驗證誤差較小'&&!noBaseline.delta.includes('OOF MAE 差')&&noBaseline.baseline==='未保存有效簡單基準'&&nullBaseline.baseline==='未保存有效簡單基準'&&nullModel.mae==='不可用'&&!nullModel.delta.includes('誤差較小')&&!missing.available&&missing.message.includes('沒有已保存')&&escapedMarkup&&legacyGuard.includes('不可直接排名')&&legacyGuard.includes('至少一份紀錄未保存 next-close 目標協定')&&compatibleHasAllTerms&&featureMismatch.includes('含特徵與回看日數')&&statusVisible;
                    }""")
                    checks.append({"name": "跨標的方向與幅度讀圖練習", "status": "PASS" if cross_asset_wrong and cross_asset_right and cross_asset_visible and saved_compare else "FAIL", "detail": f"錯答提示={cross_asset_wrong}; 正答即時回饋={cross_asset_right}; 合成限制與比較清單可見={cross_asset_visible}; 已保存摘要 fixture={saved_compare}"})
                    page.locator('input[name="weightedBiasAnswer"][value="unweighted"]').check()
                    page.locator("#checkWeightedBias").click()
                    weighted_bias_wrong = "不能把兩組偏差直接平均" in page.locator("#weightedBiasFeedback").inner_text()
                    page.locator('input[name="weightedBiasAnswer"][value="weighted"]').check()
                    page.locator("#checkWeightedBias").click()
                    weighted_bias_right = "−0.125 個百分點" in page.locator("#weightedBiasFeedback").inner_text() and "略偏高估" in page.locator("#weightedBiasFeedback").inner_text()
                    weighted_bias_visible = "合成算例的統計閱讀練習" in page.locator("#weightedBiasLesson").inner_text()
                    checks.append({"name": "加權校準偏差學習任務", "status": "PASS" if weighted_bias_wrong and weighted_bias_right and weighted_bias_visible else "FAIL", "detail": f"不加權答錯提示={weighted_bias_wrong}; 加權答案與方向解析={weighted_bias_right}; 合成資料限制可見={weighted_bias_visible}"})
                    page.locator('input[name="partitionAnswer"][value="score"]').check()
                    page.locator("#checkPartition").click()
                    partition_wrong = "沒有模型輸出與實際值的比較" in page.locator("#partitionFeedback").inner_text()
                    page.locator('input[name="partitionAnswer"][value="boundary"]').check()
                    page.locator("#checkPartition").click()
                    partition_right = "切分日期只描述資料邊界" in page.locator("#partitionFeedback").inner_text()
                    partition_visible = "不會讀取或執行鎖定測試資料" in page.locator("#partitionLesson").inner_text()
                    checks.append({"name": "資料邊界與模型成績區分練習", "status": "PASS" if partition_wrong and partition_right and partition_visible else "FAIL", "detail": f"錯答解釋={partition_wrong}; 正答解釋={partition_right}; 鎖定資料限制可見={partition_visible}"})
                    page.locator('[data-focus="#lookback"]').click()
                    mission_ok = page.locator("#advancedMenu").evaluate("element => element.open")
                    original_note = page.locator("#experimentNote").input_value()
                    page.locator("#experimentNote").fill("monitor smoke note")
                    page.locator("#saveReflection").click()
                    note_ok = "已儲存" in page.locator("#reflectionStatus").inner_text()
                    page.evaluate("value => { if (value) localStorage.setItem('sequence-lab-learning-notes-v1', value); else localStorage.removeItem('sequence-lab-learning-notes-v1'); }", original_note)
                    page.locator("#tabMath").click()
                    page.wait_for_selector(".trace-step", timeout=10000)
                    math_text = page.locator("#traceContent").inner_text()
                    math_ok = (page.locator(".trace-step").count() == 4 and "L=(ŷ−y)²" in math_text and
                               "係數 2" in math_text and "½(ŷ−y)²" in math_text and "梯度相差 2 倍" in math_text)
                    learning_ok = learning_ok and lesson_ok and reset_notice_hidden and quiz_ok and mission_ok and note_ok and math_ok
                    checks.append({"name": "多模式學習互動", "status": "PASS" if learning_ok else "FAIL", "detail": f"四種方式={dom.get('learningTabs')}; 導學前進/返回={lesson_ok}（起始={lesson_start.group(1) if lesson_start else 'unknown'}; 前進={lesson_next.group(1) if lesson_next else 'unknown'}; 返回={lesson_return.group(1) if lesson_return else 'unknown'}; 導學頁面可見={guided_visible_after_back}; 課程目錄={lesson_catalog_ok}（失敗子句索引={lesson_catalog_failures}）; 摘要步數={f'{lesson_start.group(2)} 步導學' in page.locator('#learningSummary').inner_text() if lesson_start else False}; 恢復提示={lesson_resume_notice}; 重置提示隱藏={reset_notice_hidden}）; 即時測驗回饋={quiz_ok}; 任務導向設定={mission_ok}; 本機觀察筆記={note_ok}; 數學 trace 四步={math_ok}"})
                    page.evaluate("document.querySelector('#diagnosticsPanel').open = true")
                    page.evaluate("() => renderDiagnostics({folds:[{fold:1,predictions:[{residual:null,predicted:0,actual:null,date:'2020-01-01'},{residual:.01,predicted:.02,actual:.01,date:'2020-01-02'}]}]})")
                    null_residual_summary = page.locator('#residualSummary').inner_text()
                    null_residual_ok = '1 筆 out-of-fold 殘差' in null_residual_summary and '均值 1.000 pp' in null_residual_summary
                    page.evaluate("() => renderDiagnostics({folds:[{fold:1,predictions:[{residual:null,predicted:null,actual:0,date:'2020-01-01'},{residual:null,predicted:0,actual:null,date:'2020-01-02'}]}]})")
                    empty_residual_ok = '沒有可用的有限 out-of-fold 殘差' in page.locator('#residualSummary').inner_text() and page.locator('#residualChart .diagnostics-empty').text_content().find('沒有可用的有限殘差資料') >= 0
                    page.evaluate("() => renderDiagnostics({folds:[{fold:1,predictions:[{date:'2024-01-01',residual:null,predicted:.02,actual:.01},{date:'2024-01-02',predicted:.5},{date:'2024-01-03',residual:.004,predicted:.8,actual:.3}]}]})")
                    fold_null_summary = page.locator('#foldErrorLegend').inner_text()
                    fold_null_ok = 'n=2' in fold_null_summary and '排除 1 筆缺值' in fold_null_summary and page.locator('#foldErrorChart .fold-error-line').count() == 1 and 'NaN' not in page.locator('#foldErrorChart').inner_html()
                    page.evaluate("() => renderDiagnostics({folds:[{fold:1,predictions:[{residual:.01,predicted:.02,actual:.01,date:'2020-01-01'}]}]})")
                    page.evaluate("""() => {
                      const folds = Array.from({length:4}, (_, f) => ({fold:f+1, predictions:Array.from({length:80}, (_,i) => {
                        const actual = Math.sin((i+f*7)/4)*0.01;
                        const predicted = actual + Math.cos((i+f)/5)*0.003 + (i===65 ? 0.035 : 0);
                        return {date:`202${f+1}-01-${String(i%28+1).padStart(2,'0')}`,actual,predicted,residual:predicted-actual};
                      })}));
                      renderDiagnostics({folds});
                    }""")
                    diagnostic_residual_summary = page.locator('#residualSummary').inner_text()
                    calibration_points = page.locator("#calibrationChart .calibration-point").count()
                    calibration_summary = page.locator("#calibrationSummary").inner_text()
                    example=page.locator(".calibration-example")
                    example.locator("summary").click()
                    example_open=example.evaluate("el=>el.open") and example.locator("circle[data-example]").count()==2 and "合成教學資料" in example.inner_text() and "(3 × −0.5 + 1 × 1.0) ÷ 4 = −0.125" in example.inner_text()
                    example.locator("summary").click()
                    page.evaluate("() => renderCalibration([{predicted:-.001,actual:-.002},{predicted:.001,actual:.002}])")
                    calibration_axis=page.locator("#calibrationChart .chart-axis").all_text_contents()
                    calibration_summary_text=page.locator("#calibrationSummary").inner_text()
                    small_sample_ok=page.locator("#calibrationChart .calibration-point").count()==1 and "NaN" not in page.locator("#calibrationChart").inner_html() and "2 筆" in calibration_summary_text and sum(label.strip()=="0.00" for label in calibration_axis)>=2 and "整體平均偏差接近零" in calibration_summary_text
                    page.evaluate("() => renderCalibration([{predicted:.01,actual:.005},{predicted:.01,actual:.005}])")
                    overprediction_summary=page.locator("#calibrationSummary").inner_text()
                    bias_direction_ok="整體高估" in overprediction_summary and "-0.500 個百分點" in overprediction_summary
                    page.evaluate("() => renderCalibration([{predicted:.01,actual:.005},{predicted:null,actual:.02},{predicted:.03,actual:null},{predicted:.01,actual:.005}])")
                    null_pair_summary=page.locator("#calibrationSummary").inner_text()
                    null_pairs_ok=page.locator("#calibrationChart .calibration-point").count()==1 and "2 筆 out-of-fold 預測" in null_pair_summary and "排除 2 筆缺少實際值或預測值的配對" in null_pair_summary and "NaN" not in page.locator("#calibrationChart").inner_html()
                    guide_text=Path(__file__).resolve().parents[1].joinpath("docs/learning-guide.md").read_text(encoding="utf-8")
                    calibration_guide_ok=all(term in guide_text for term in ["算一遍有號偏差", "0.5% − 1.0% = −0.5 個百分點", "+0.5 個百分點", "(3 × −0.5 + 1 × 1.0) ÷ 4 = −0.125", "跟著兩組樣本數先算各組偏差", "不能當作模型表現或交易訊號", "絕對幅度差、MAE", "先讀漲跌方向，再看幅度", "+0.4%", "−0.2%", "方向準確率"])
                    direction_guide_ok=all(term in guide_text for term in ["方向準確率如何計算", "零預測", "中性", "0.5 分", "實際報酬為零時", "+0.3%", "−0.1%", "漲跌比例", "至少 70%", "不是交易或選模門檻"])
                    direction_magnitude_guide_ok=all(term in guide_text for term in ["方向摘要會並列實際與預測上漲、下跌樣本各自的平均絕對報酬幅度", "1.5 個百分點", "缺少實際值或預測值的列不納入"])
                    magnitude_guide_ok=all(term in guide_text for term in ["從報酬率換算為指數點數", "20,000 × (1 + 0.01) = 20,200 點", "20,000 × exp(0.01) ≈ 20,201 點", "對數報酬可以低於 −100%", "另一種定義無效", "不是可成交價格"])
                    learning_rate_guide_ok=all(term in guide_text for term in ["固定合成目標權重 1", "L=(W−1)²", "損失從 1 降至 0.9025", "η` 改為 10", "損失升至 16", "不能由此推論訓練穩定"])
                    interval_guide_ok=all(term in guide_text for term in ["單一預測值與預測區間", "中心預測 +0.6%", "+0.2% 至 +1.0%", "不是模型估計", "覆蓋率與區間寬度"])
                    loss_guide_ok=all(term in guide_text for term in ["讀取訓練與驗證 Loss", "對數刻度", "左右方向鍵", "各折、MAE、基準"])
                    direction_ui_ok="方向準確率依預測與實際報酬率的正負號計算" in page.locator("button[aria-label='評估指標說明']").get_attribute("title") and "同向 1 分、反向 0 分、零預測 0.5 分" in guide_text and "實際" in page.locator("#directionMix").inner_text() and "預測" in page.locator("#directionMix").inner_text()
                    diagnostic_ok = null_residual_ok and fold_null_ok and empty_residual_ok and page.locator("#residualChart .residual-bar").count() >= 8 and page.locator("#residualChart .residual-normal").count() == 1 and page.locator("#foldErrorChart .fold-error-line").count() == 4 and page.locator("#foldErrorLegend span").count() == 4 and "超額峰度" in diagnostic_residual_summary and 1 <= calibration_points <= 8 and "分組加權幅度差" in calibration_summary and page.locator("#calibrationChart .calibration-reference").count() == 1 and example_open and small_sample_ok and bias_direction_ok and null_pairs_ok and calibration_guide_ok and direction_guide_ok and direction_magnitude_guide_ok and direction_ui_ok and loss_guide_ok and magnitude_guide_ok and learning_rate_guide_ok and interval_guide_ok
                    checks.append({"name": "殘差、逐折誤差與預測幅度校準圖", "status": "PASS" if diagnostic_ok else "FAIL", "detail": f"有效殘差排除 null={null_residual_ok}; 逐折缺值排除與有效 n={fold_null_ok}; 空殘差提示={empty_residual_ok}; 直方圖 bins={page.locator('#residualChart .residual-bar').count()}; 常態參考曲線={page.locator('#residualChart .residual-normal').count()}; 逐折曲線={page.locator('#foldErrorChart .fold-error-line').count()}; 折別圖例={page.locator('#foldErrorLegend span').count()}; 峰度摘要={'顯示' if '超額峰度' in diagnostic_residual_summary else '缺少'}; 校準分組={calibration_points}; 加權幅度差={'顯示' if '分組加權幅度差' in calibration_summary else '缺少'}; 高估／低估方向={bias_direction_ok}; null 配對排除與計數={null_pairs_ok}; 合成例子展開={example_open}; 近零／負值小樣本={small_sample_ok}; 教學檢查 calibration={calibration_guide_ok}, direction={direction_guide_ok}, direction_magnitude={direction_magnitude_guide_ok}, magnitude={magnitude_guide_ok}; UI direction={direction_ui_ok}; Loss guide={loss_guide_ok}"})
                    page.evaluate("""() => { renderLossChart({meanTrainLoss:[.12,.06,.03,.02],meanValidationLoss:[.15,.08,.05,.04]}); document.querySelector('#results').dataset.status='complete'; }""")
                    chart = page.locator("#lossChart")
                    chart.scroll_into_view_if_needed()
                    # Hover the actual SVG hit target so Playwright waits for a
                    # stable target and dispatches the same pointer path as a
                    # user. Wait for the rendered tooltip before reading it.
                    chart.locator(".loss-hit-area").hover(position={"x": 288, "y": 90}, timeout=5000)
                    page.wait_for_function("() => { const tip=document.querySelector('#lossTooltip'); return tip && !tip.hidden && /Epoch \\d+/.test(tip.innerText); }", timeout=5000)
                    # Capture pointer output before keyboard navigation mutates the same tooltip.
                    hover_text = page.locator("#lossTooltip").inner_text()
                    hover_ok = "Epoch" in hover_text and "Train" in hover_text and "Validation" in hover_text
                    pointer_epoch = re.search(r"Epoch\s+(\d+)", hover_text)
                    page.locator("#lossChart").focus()
                    page.keyboard.press("ArrowRight")
                    keyboard_text = page.locator("#lossTooltip").inner_text()
                    loss_hover_ok = hover_ok and pointer_epoch is not None and "Epoch 2" in keyboard_text
                    checks.append({"name": "Loss 曲線游標與鍵盤 Tooltip", "status": "PASS" if loss_hover_ok else "FAIL", "detail": f"游標值={hover_text.replace(chr(10), '; ') or '未顯示'}（獨立通過={hover_ok}, epoch={pointer_epoch.group(1) if pointer_epoch else 'unknown'}）；左右鍵值={keyboard_text.replace(chr(10), '; ') or '未顯示'}"})
                    page.evaluate("""() => {
                      const start=Math.max(40,state.series.findIndex(point=>point.date>=state.status.validationStart));
                      const samples=[
                        {originDate:state.series[start].date,date:state.series[start+1].date,predicted:.012,actual:.006},
                        {originDate:state.series[start+1].date,date:state.series[start+2].date,predicted:-.012,actual:-.004},
                        {originDate:state.series[start+2].date,date:state.series[start+3].date,predicted:0,actual:.002},
                      ];
                      document.querySelector('#buyThreshold').value='0.2';
                      document.querySelector('#sellThreshold').value='-0.2';
                      state.validationConfig={horizon:1,returnType:'simple'};
                      state.validation={horizon:1,returnType:'simple',models:[{folds:[{predictions:samples}]}]};
                      renderSignals(state.validation);
                    }""")
                    signal_summary=page.locator("#signalSummary").inner_text()
                    signal_chart_ok=page.locator("#historyChart .signal-marker-buy").count()==1 and page.locator("#historyChart .signal-marker-sell").count()==1 and "驗證期策略比較" in signal_summary and "買入持有淨報酬" in signal_summary and "20 日均線" in signal_summary and "全現金" in signal_summary and "次日收盤執行" in signal_summary and "0.585%" in signal_summary
                    checks.append({"name":"買賣標記與含摩擦成本策略回放","status":"PASS" if signal_chart_ok else "FAIL","detail":f"圖上買／賣標記={page.locator('#historyChart .signal-marker-buy').count()}/{page.locator('#historyChart .signal-marker-sell').count()}；摘要顯示模型與買入持有、MDD、完整往返成本 0.585%={signal_chart_ok}"})
                    checks.append({"name": "鎖定測試確認防呆", "status": "SKIP", "detail": "maintenance monitor does not open or click the one-time final-test confirmation UI; final-test execution remains outside routine browser checks"})
                    page.evaluate("""() => recordValidationRun({validationSamples:120,models:[{key:'mlp',name:'MLP',mae:.012,rmse:.018,r2:.21,spearman:.14,directionAccuracy:.52,folds:[]}]},buildConfig())""")
                    page.locator("#runHistoryPanel > summary").click()
                    history_ok=page.locator("#runHistoryRows tr").count()==1 and "套用設定" in (page.locator("#runHistoryRows").text_content() or "")
                    expected_model=page.evaluate("readRunHistory()[0].config.modelType")
                    page.locator("#runHistoryRows .history-apply").click()
                    page.wait_for_function("([model]) => { const menu=document.querySelector('#advancedMenu'); const select=document.querySelector('#modelType'); return Boolean(menu?.open && select?.value===model); }", arg=[expected_model], timeout=5000)
                    history_ok=history_ok and page.locator("#advancedMenu").evaluate("el=>el.open") and page.locator("#modelType").input_value()==expected_model
                    page.route("**/api/experiments", lambda route: route.fulfill(status=409,content_type="application/json",body='{"detail":"monitor intercepted"}'))
                    top_posts=[]
                    def intercept_top_training(route):
                        top_posts.append(route.request.post_data_json or {})
                        route.abort()
                    page.route("**/api/experiments", intercept_top_training)
                    page.locator("#topTrain").click()
                    page.wait_for_timeout(120)
                    expected_config=page.evaluate("buildConfig()")
                    top_flow_ok=(len(top_posts)==1 and top_posts[0].get("modelTypes") == expected_config.get("modelTypes") and
                                 top_posts[0].get("features") == expected_config.get("features") and top_posts[0].get("lookback") == expected_config.get("lookback") and
                                 page.locator("#jobError").inner_text().strip() != "")
                    page.unroute("**/api/experiments", intercept_top_training)
                    checks.append({"name": "頂部參數到訓練入口與歷程保存", "status": "PASS" if history_ok and top_flow_ok else "FAIL", "detail": f"本機實驗列出並套用設定={history_ok}；頂部訓練按鈕送出目前設定（API 被巡檢攔截，未啟動訓練）={top_flow_ok}"})
                else:
                    page.evaluate("setBusy(true)")
                    cancel = page.locator("#cancelJob").evaluate("el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {display:s.display,width:Math.round(r.width),height:Math.round(r.height),visible:s.display!=='none'&&r.width>0&&r.height>0&&!el.disabled}}")
                    top_train = page.locator("#topTrain").bounding_box()
                    mobile_ok = response is not None and response.status == 200 and dom["scrollWidth"] <= dom["clientWidth"] + 1 and bool(cancel.get("visible")) and cancel.get("height", 0) >= 44 and top_train and top_train["height"] >= 44 and (dom.get("chartRailGap") or -1) >= 6
                    page.evaluate("setBusy(false)")
                    checks.append({"name": "手機版排版與訓練／取消操作", "status": "PASS" if mobile_ok and not page_errors else "FAIL", "detail": f"390×844; horizontal overflow={max(0, dom['scrollWidth']-dom['clientWidth'])}px; phase rail/chart gap={dom.get('chartRailGap')}px; top train height={round(top_train['height']) if top_train else 0}px; active cancel visible={cancel.get('visible')}, {cancel.get('width')}×{cancel.get('height')}px; JS errors={page_errors or 'none'}; screenshot=artifacts/regression-monitor/latest-mobile.png"})
                    page.evaluate("() => { const panel=document.querySelector('#diagnosticsPanel'); panel.open=true; panel.dataset.status='ready'; }")
                    mobile_example=page.locator(".calibration-example")
                    mobile_example.locator("summary").click()
                    calibration_box=mobile_example.bounding_box()
                    calibration_svg_box=page.locator("#calibrationExample").bounding_box()
                    mobile_calibration_ok=mobile_example.evaluate("el=>el.open") and calibration_svg_box and calibration_svg_box["width"]>0 and calibration_box and calibration_box["x"]>=0 and calibration_box["x"]+calibration_box["width"]<=dom["clientWidth"]+1 and page.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1")
                    checks.append({"name":"手機版校準圖教學示例", "status":"PASS" if mobile_calibration_ok and not page_errors else "FAIL", "detail":f"390px 下示例可展開、SVG 顯示且卡片不溢出={mobile_calibration_ok}; JS errors={page_errors or 'none'}"})
                    page.evaluate("""() => renderComparison([
                      ['historical_mean','歷史平均'],['naive','預測零報酬'],['ridge','Ridge'],['forest','Random Forest'],
                      ['mlp','MLP'],['rnn','RNN'],['lstm','LSTM'],['gru','GRU']
                    ].map(([key,name],i)=>({key,name,mae:0.003+i*0.0001,rmse:0.004+i*0.0001})))""")
                    adaptive_ok = page.locator("#comparisonChart .bar-label-rotated").count() == 8 and page.locator("#comparisonChart .bar-label").count() == 8 and not page.locator("#comparisonCompactHint").is_hidden() and "短標籤" in page.locator("#comparisonCompactHint").inner_text()
                    checks.append({"name": "窄螢幕多模型 X 軸標籤", "status": "PASS" if adaptive_ok else "FAIL", "detail": f"390px viewport rotated/short labels={page.locator('#comparisonChart .bar-label-rotated').count()}/8"})
                    mobile_asset_strip = page.evaluate("""() => {
                      const strip=document.querySelector('#stockCards');
                      const cards=[...document.querySelectorAll('#stockCards .stock-card')];
                      return Boolean(strip && cards.length===11 && strip.scrollWidth>strip.clientWidth && cards.every(card=>card.getBoundingClientRect().height>=44) && document.documentElement.scrollWidth<=document.documentElement.clientWidth+1);
                    }""")
                    asset_strip_checks["mobile"] = mobile_asset_strip
                    checks.append({"name": "標的切換帶桌面與手機操作", "status": "PASS" if asset_strip_checks.get("desktop") and mobile_asset_strip else "FAIL", "detail": f"桌面 11 項單列、10/10 本機覆蓋數可見且 TAIEX／台積電選取狀態同步={asset_strip_checks.get('desktop')}; 手機可橫向瀏覽 11 項、點擊區≥44px 且頁面無水平溢位={mobile_asset_strip}"})
                    page.locator("#math > summary").click()
                    # The return-conversion exercise belongs to lesson 8; keep the
                    # mobile layout check anchored to that exercise as lessons grow.
                    page.evaluate("() => { lessonIndex=7; renderLesson(); }")
                    page.locator("#returnConversionExercise").scroll_into_view_if_needed()
                    conversion_mobile = page.evaluate("""() => {
                      const exercise=document.querySelector('#returnConversionExercise');
                      const fields=[...document.querySelectorAll('#conversionPrice,#conversionReturn,#conversionType')];
                      const rects=fields.map(el=>el.getBoundingClientRect());
                      const result=document.querySelector('#conversionResult').getBoundingClientRect();
                      const dock=document.querySelector('.action-bar').getBoundingClientRect();
                      return exercise.getBoundingClientRect().width>0 && fields.every((el,i)=>getComputedStyle(el).minHeight.replace('px','')>=44 && (i===0 || rects[i].top>rects[i-1].top+20)) &&
                        result.bottom<=dock.top+1 && document.documentElement.scrollWidth<=document.documentElement.clientWidth+1;
                    }""")
                    page.screenshot(path=str(ARTIFACTS / "latest-mobile-conversion.png"), full_page=False)
                    checks.append({"name": "手機版報酬換算練習", "status": "PASS" if conversion_mobile else "FAIL", "detail": f"390px 欄位單列且觸控高度≥44px、結果不被固定訓練列遮住、頁面無水平溢位={conversion_mobile}; screenshot=artifacts/regression-monitor/latest-mobile-conversion.png"})
                if page_errors:
                    visual_notes.extend(f"{name} JavaScript error: {error}" for error in page_errors)
                page.close()
            browser.close()
        for selector, box in geometry.items():
            old = previous_geometry.get(selector)
            if old and box.get("visible") and old.get("visible"):
                drift = max(abs(box[key] - old[key]) for key in ("x", "y", "width", "height"))
                if drift > 4:
                    layout_drifts.append(f"{selector} bounding-box drift from prior monitor run: {drift}px")
        visual_detail = "; ".join([note for note in visual_notes if "pixel delta" in note] + layout_drifts)
        checks.append({"name": "視覺設計稿比對", "status": "WARN" if (not REFERENCE.exists() or layout_drifts) else "PASS", "detail": visual_detail or "已擷取桌面與手機畫面；元件幾何數據與前次快照一致"})
    except Exception as exc:  # noqa: BLE001
        stack = traceback.format_exc().strip()
        checks.append({"name": "瀏覽器渲染／視覺檢查", "status": "FAIL", "detail": f"未能完成 Playwright 瀏覽器檢查：{type(exc).__name__}: {exc}; traceback={stack}"})
    return checks, geometry, visual_notes


def pytest_interpreter(root: Path = ROOT, fallback: str = sys.executable) -> str:
    """Prefer the project's environment so scheduled runs use declared dependencies."""
    candidates = (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe")
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return fallback


def run_pytest() -> dict[str, Any]:
    interpreter = pytest_interpreter()
    command = [interpreter, "-m", "pytest", "-q"]
    try:
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=100)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        detail = lines[-1] if lines else f"exit code {result.returncode}"
        return {"status": "PASS" if result.returncode == 0 else "FAIL", "detail": detail, "command": f"{interpreter} -m pytest -q"}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "detail": "單元回歸超過 100 秒逾時", "command": f"{interpreter} -m pytest -q"}


def render_block(report: dict[str, Any], changed: list[str], state: str, diff_path: Path) -> str:
    checks = report["checks"]
    counts = {status: sum(item["status"] == status for item in checks) for status in ("PASS", "WARN", "FAIL")}
    issues = [item for item in checks if item["status"] in {"FAIL", "WARN"}]
    if report["pytest"]["status"] == "FAIL":
        issues.append({"name": "pytest 完整回歸", "status": "FAIL", "detail": report["pytest"]["detail"]})
    lines = [BEGIN, f"## 自動回歸監測（{report['time']}）", "", f"整體：**{report['overall']}**（PASS {counts['PASS']}／WARN {counts['WARN']}／FAIL {counts['FAIL']}）。每 30 分鐘本機執行；不更新外部資料、不執行鎖定測試。", "", "### 新問題與待辦"]
    if issues:
        for item in issues:
            action = "修復並重跑" if item["status"] == "FAIL" else "追蹤／確認"
            lines.append(f"- **{item['status']}｜{action}：{item['name']}**：{item['detail']}")
    else:
        lines += ["- 無新增失敗或待辦。"]
    if changed:
        lines += ["", "### 來源檔變更", f"- {', '.join(f'`{p}`' for p in changed)}", f"- 差異／快照紀錄：`{diff_path.relative_to(ROOT)}`。"]
    elif state == "initialized":
        lines += ["", "### 來源檔變更", "- 已建立來源快照；下輪起會比較 app/web/tests/scripts/requirements 的實際文字差異。"]
    else:
        lines += ["", "### 來源檔變更", "- 無來源檔變更。"]
    train = next((item for item in checks if "真實資料訓練" in item["name"]), None)
    browser = next((item for item in checks if "桌面瀏覽器" in item["name"]), None)
    mobile = next((item for item in checks if "手機版" in item["name"]), None)
    visual = next((item for item in checks if item["name"] == "視覺設計稿比對"), None)
    lines += ["", "### 本輪摘要", f"- pytest：**{report['pytest']['status']}**，{report['pytest']['detail']}。API／非同步驗證測試使用隔離儲存，不會覆寫本機驗證結果。"]
    lines += [f"- 訓練 smoke check：**{train['status']}**，{train['detail']}" if train else "- 訓練 smoke check：未執行。"]
    lines += [f"- 瀏覽器：桌面 {browser['status'] if browser else '未執行'}；手機 {mobile['status'] if mobile else '未執行'}。截圖：`artifacts/regression-monitor/latest-desktop.png`、`artifacts/regression-monitor/latest-mobile.png`。" ]
    lines += [f"- 設計稿：{visual['status'] if visual else '未執行'}；{visual['detail'] if visual else ''} 像素差異僅供參考，資料與頁面狀態不同。"]
    lines += [f"- 完整逐項結果：`artifacts/regression-monitor/latest-checks.json`。", "", END]
    return "\n".join(lines)


def replace_block(path: Path, block: str, heading: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else heading + "\n"
    pattern = re.compile(re.escape(BEGIN) + r"[\s\S]*?" + re.escape(END))
    if pattern.search(old):
        new = pattern.sub(block, old)
    else:
        new = old.rstrip() + "\n\n" + block + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> int:
    ROOT.joinpath("data").mkdir(exist_ok=True)
    LOCK_PATH.touch(exist_ok=True)
    with LOCK_PATH.open("r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another regression monitor run is already active; skipped.")
            return 0

        try:
            previous = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
        except (OSError, json.JSONDecodeError):
            previous = {}
        # Hash paths only; never open one-time holdout files during routine maintenance.
        final_states_before = final_state_paths()
        try:
            previous_snapshot = json.loads(SOURCE_SNAPSHOT_PATH.read_text(encoding="utf-8")) if SOURCE_SNAPSHOT_PATH.exists() else {}
        except (OSError, json.JSONDecodeError):
            previous_snapshot = {}
        before_hashes = previous.get("sourceHashes", {})
        current_snapshot = source_snapshot()
        current_hashes = hash_sources(current_snapshot)
        changed = changed_sources(before_hashes, current_hashes) if before_hashes else []
        diff_path = write_source_diff(changed, previous_snapshot, current_snapshot)

        checks, status_data = check_http()
        active_job = any(item.get("active_job") for item in checks)
        try:
            checks.extend(check_splits_and_train(active_job))
        except Exception as exc:  # noqa: BLE001 - continue and write a useful failure report
            checks.append({"name": "資料切片／PyTorch 訓練監測器", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
        visual_checks, geometry, _ = browser_check(previous.get("geometry", {}))
        checks.extend(visual_checks)
        pytest_result = run_pytest()
        checks.append({"name": "程式回歸測試", "status": pytest_result["status"], "detail": pytest_result["detail"]})
        final_states_after = final_state_paths()
        final_state_unchanged = final_states_before == final_states_after
        checks.append({"name": "鎖定測試資料隔離", "status": "PASS" if final_state_unchanged else "FAIL",
                       "detail": "monitor blocks final-state writes and does not render holdout observations" if final_state_unchanged else "holdout state path set changed during monitor"})
        failures = sum(item["status"] == "FAIL" for item in checks)
        warnings = sum(item["status"] == "WARN" for item in checks)
        overall = "FAIL" if failures or pytest_result["status"] == "FAIL" else ("WARN" if warnings else "PASS")
        prior_hashes = previous.get("sourceHashes")
        source_state = "initialized" if prior_hashes is None else "steady"
        if prior_hashes is not None and changed and failures:
            overall = "FAIL"
        report = {"time": iso_time(), "overall": overall, "checks": checks, "pytest": pytest_result, "dataset": status_data,
                  "changedSources": changed, "sourceDiff": str(diff_path.relative_to(ROOT)),
                  "screenshots": ["artifacts/regression-monitor/latest-desktop.png", "artifacts/regression-monitor/latest-mobile.png"]}
        save_json_atomic(ARTIFACTS / "latest-checks.json", report)
        block = render_block(report, changed, source_state, diff_path)
        targets = [
            (ROOT / "scratchpad.md", "# Scratchpad：自動回歸監測"),
            (ROOT / "CODEX.md", "# Codex 任務指南：序列觀測站 (taiex-neural-lab)"),
            (ROOT / "docs" / "codex-bug-report.md", "# 序列觀測站 (taiex-neural-lab) 實測問題報告與修復指南"),
            (ROOT / ".cursor" / "ralph" / "scratchpad.md", "# 🤖 協同開發任務清單 (for Codex)"),
        ]
        for path, heading in targets:
            replace_block(path, block, heading)

        save_json_atomic(STATE_PATH, {"lastRun": report["time"], "sourceHashes": current_hashes, "geometry": geometry, "overall": overall})
        save_json_atomic(SOURCE_SNAPSHOT_PATH, current_snapshot)
        print(f"{report['time']} {overall}: {len(checks)} checks, pytest {pytest_result['status']}; changed source files={len(changed)}")
        for item in checks:
            print(f"{item['status']}: {item['name']} — {item['detail']}")
        print(f"Report updated: scratchpad.md, CODEX.md, docs/codex-bug-report.md, .cursor/ralph/scratchpad.md")
        return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
