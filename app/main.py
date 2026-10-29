"""Local API for the TAIEX neural-network learning lab."""

from __future__ import annotations

import threading
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .data import (
    FEATURES,
    build_samples,
    build_latest_feature_window,
    data_status,
    is_tradable_equity,
    load_series,
    read_final_state,
    refresh_latest_month,
    refresh_stock_data,
    stock_universe,
    write_final_state,
)
from .ml import MODEL_NAMES, config_from_request, fit_deployment_artifact, numpy_mlp_trace, run_final_test, run_validation
from . import paper as paper_trading

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
app = FastAPI(title="序列觀測站｜神經網路股價預測學習實驗室", version="2.0.0")
app.mount("/assets", StaticFiles(directory=WEB), name="assets")

pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nn-experiment")
jobs: dict[str, dict[str, Any]] = {}
validation_registry: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()
refresh_in_progress = False


def _store_latest_validation(digest: str, config: dict[str, Any], result: dict[str, Any]) -> None:
    """Keep the latest completed validation available after a browser or server restart."""
    path = ROOT / "data" / f"latest-validation-{digest[:16]}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"datasetHash": digest, "config": config, "result": result}, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


class ExperimentRequest(BaseModel):
    symbol: str = "TAIEX"
    buyThreshold: float = Field(default=0.002, ge=0, le=0.2)
    sellThreshold: float = Field(default=-0.002, ge=-0.2, le=0)
    modelTypes: list[Literal["mlp", "rnn", "lstm", "gru", "tcn"]] = ["mlp", "rnn", "lstm", "gru", "tcn"]
    features: list[str] = ["return_1", "return_5", "return_20", "volatility_5", "volatility_20"]
    lookback: int = Field(default=20, ge=5, le=60)
    horizon: Literal[1, 5, 20] = 5
    returnType: Literal["simple", "log"] = "simple"
    epochs: int = Field(default=25, ge=1, le=100)
    batchSize: int = Field(default=64, ge=8, le=512)
    hiddenUnits: int = Field(default=32, ge=4, le=128)
    hiddenLayers: int = Field(default=2, ge=1, le=4)
    hiddenSizes: list[int] = Field(default_factory=lambda: [64, 32, 16], min_length=1, max_length=4)
    dropout: float = Field(default=0.1, ge=0, le=0.7)
    learningRate: float = Field(default=0.001, gt=0.000001, le=0.1)
    optimizer: Literal["adam", "sgd"] = "adam"
    loss: Literal["mse", "huber"] = "mse"
    seed: int = Field(default=42, ge=0, le=999999)


class FinalRequest(ExperimentRequest):
    modelTypes: list[Literal["mlp", "rnn", "lstm", "gru", "tcn"]] = ["mlp"]


class PaperAccountRequest(BaseModel):
    symbol: str
    strategy: Literal["momentum", "neural", "agent"] = "momentum"
    model: Optional[Literal["mlp", "rnn", "lstm", "gru", "tcn"]] = None
    agentProvider: Optional[Literal["codex", "antigravity"]] = None
    agentAutoEnabled: bool = False
    buyThreshold: float = Field(default=0.002, ge=0, le=0.2)
    sellThreshold: float = Field(default=-0.002, ge=-0.2, le=0)
    lookback: int = Field(default=20, ge=1, le=252)
    initialCash: float = Field(default=100000, ge=1, le=100000000)
    commissionBps: float = Field(default=14.25, ge=0, le=500)
    sellTaxBps: float = Field(default=30, ge=0, le=500)
    slippageBps: float = Field(default=10, ge=0, le=500)
    maxExposurePct: float = Field(default=20, ge=1, le=100)
    nickname: str = Field(default="", max_length=24)
    mascotColor: Literal["teal", "red", "blue", "cream"] = "teal"
    mascotAccessory: Literal["cap", "beret", "crown", "none", "dot", "leaf", "star"] = "cap"
    creationKey: Optional[str] = Field(default=None, min_length=16, max_length=80)


class MascotRequest(BaseModel):
    nickname: str = Field(default="", max_length=24)
    mascotColor: Literal["teal", "red", "blue", "cream"]
    mascotAccessory: Literal["cap", "beret", "crown", "none", "dot", "leaf", "star"]


class PaperSettingsRequest(BaseModel):
    lookback: int = Field(ge=1, le=252)
    initialCash: float = Field(ge=1, le=100_000_000)
    commissionBps: float = Field(ge=0, le=500)
    sellTaxBps: float = Field(ge=0, le=500)
    slippageBps: float = Field(ge=0, le=500)
    maxExposurePct: float = Field(ge=1, le=100)


class PaperAgentAutomationRequest(BaseModel):
    enabled: bool


class StockRefreshRequest(BaseModel):
    symbols: Optional[list[str]] = Field(default=None, min_length=1, max_length=10)


def _check_request(payload: ExperimentRequest, final: bool = False) -> None:
    if not payload.modelTypes:
        raise HTTPException(status_code=422, detail="至少選一種模型。")
    if len(set(payload.modelTypes)) != len(payload.modelTypes):
        raise HTTPException(status_code=422, detail="模型不能重複選取。")
    if final and len(payload.modelTypes) != 1:
        raise HTTPException(status_code=422, detail="最終鎖定測試只能選一種凍結模型設定。")
    if final and payload.modelTypes[0] == "tcn":
        raise HTTPException(status_code=422, detail="TCN 尚未納入既有鎖定測試協定；目前可使用一般 walk-forward 驗證。")
    if not payload.features:
        raise HTTPException(status_code=422, detail="至少選一個輸入特徵。")
    if any(key not in FEATURES for key in payload.features):
        raise HTTPException(status_code=422, detail="含有不支援的輸入特徵。")
    if any(size < 4 or size > 128 for size in payload.hiddenSizes):
        raise HTTPException(status_code=422, detail="隱藏層寬度需介於 4 到 128。")
    if payload.symbol != "TAIEX" and payload.symbol not in {item["symbol"] for item in stock_universe()["stocks"]}:
        raise HTTPException(status_code=422, detail="不支援的台股標的。")
    if payload.sellThreshold >= payload.buyThreshold:
        raise HTTPException(status_code=422, detail="賣出門檻必須低於買進門檻。")
    if final and payload.epochs < 20:
        raise HTTPException(status_code=422, detail="正式鎖定測試至少需訓練 20 個 Epoch；短訓練可用於驗證流程，不得消耗最終測試。")


def _final_state_for_dataset(digest: str, symbol: str = "TAIEX") -> dict[str, Any]:
    state = read_final_state(digest, symbol)
    if state.get("status") == "running":
        with jobs_lock:
            job = jobs.get(state.get("jobId", ""))
        if not job or job.get("status") not in {"queued", "running"}:
            state = {"status": "available", "datasetHash": digest, "symbol": symbol, "note": "上次最終測試在完成前中斷，沒有揭露測試分數。"}
            write_final_state(state)
    return state


def _start_job(payload: ExperimentRequest, final: bool = False) -> dict[str, Any]:
    _check_request(payload, final)
    try:
        series = load_series(payload.symbol)
        sample_data = build_samples(
            series, payload.features, payload.lookback, payload.horizon, payload.returnType == "log"
        )
        if final:
            train_n = int((sample_data["targets"] < sample_data["split_index"]).sum())
            test_mask = (sample_data["origins"] >= sample_data["split_index"]) & (sample_data["targets"] > sample_data["split_index"])
            test_n = int(test_mask.sum())
            if train_n < 250 or test_n < 50:
                raise ValueError("依目前選擇建立的鎖定測試樣本不足。")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job_id = uuid.uuid4().hex[:12]
    cancel = threading.Event()
    record: dict[str, Any] = {
        "id": job_id,
        "kind": "final" if final else "validation",
        "status": "queued",
        "progress": 0,
        "message": "工作已排入本機 CPU 訓練佇列",
        "cancel": cancel,
        "result": None,
        "error": None,
        "datasetHash": series.digest,
        "config": payload.model_dump(),
    }
    with jobs_lock:
        if refresh_in_progress or any(job["status"] in {"queued", "running"} for job in jobs.values()):
            raise HTTPException(status_code=409, detail="目前已有資料更新或訓練工作執行中，請等待完成或取消。")
        while len(jobs) >= 40:
            oldest_finished = next((key for key, item in jobs.items() if item["status"] not in {"queued", "running"}), None)
            if oldest_finished is None:
                break
            del jobs[oldest_finished]
        jobs[job_id] = record
    if final:
        write_final_state({
            "status": "running", "jobId": job_id, "datasetHash": series.digest, "symbol": payload.symbol,
            "model": payload.modelTypes[0], "config": payload.model_dump(),
        })

    def progress(percent: int, message: str) -> None:
        with jobs_lock:
            record["progress"] = max(record["progress"], min(percent, 99))
            record["message"] = message

    def execute() -> None:
        with jobs_lock:
            record["status"] = "running"
        try:
            config = config_from_request(payload.model_dump())
            if final:
                result = run_final_test(sample_data, payload.modelTypes[0], config, cancel, progress)
                write_final_state({
                    "status": "spent", "jobId": job_id, "datasetHash": series.digest, "symbol": payload.symbol,
                    "model": payload.modelTypes[0], "completedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                    "config": payload.model_dump(), "result": result,
                })
            else:
                result = run_validation(sample_data, payload.modelTypes, config, cancel, progress)
                result["returnType"] = payload.returnType
                result["execution"] = sample_data["execution"]
                result["targetDefinition"] = "close[t+1] to close[t+horizon+1]"
                result["signalSettings"] = {"buyThreshold": payload.buyThreshold, "sellThreshold": payload.sellThreshold}
                for model in result.get("models", []):
                    for fold in model.get("folds", []):
                        for row in fold.get("predictions", []):
                            predicted = __import__("math").expm1(row["predicted"]) if payload.returnType == "log" else row["predicted"]
                            row["signal"] = "buy_candidate" if predicted > payload.buyThreshold else "sell_candidate" if predicted < payload.sellThreshold else "hold"
                with jobs_lock:
                    validation_registry[f"{payload.symbol}:{series.digest}"] = {
                        "config": payload.model_dump(),
                        "validatedModels": list(payload.modelTypes),
                        "result": result,
                    }
                try:
                    _store_latest_validation(series.digest, payload.model_dump(), result)
                except OSError:
                    pass
            with jobs_lock:
                record["status"] = "completed"
                record["progress"] = 100
                record["message"] = "完成"
                record["result"] = result
        except InterruptedError as exc:
            with jobs_lock:
                record["status"] = "cancelled"
                record["message"] = str(exc)
            if final:
                write_final_state({"status": "available", "datasetHash": series.digest, "symbol": payload.symbol, "note": "測試未完成，沒有揭露最終測試分數。"})
        except Exception as exc:  # Keep the local server alive and expose the actual failure.
            with jobs_lock:
                record["status"] = "failed"
                record["error"] = str(exc)
                record["message"] = "工作失敗"
            if final:
                write_final_state({"status": "failed", "datasetHash": series.digest, "symbol": payload.symbol, "error": str(exc)})

    pool.submit(execute)
    return {"jobId": job_id, "status": "queued", "kind": record["kind"]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/paper")
def paper_dashboard() -> FileResponse:
    return FileResponse(WEB / "paper.html")


def _paper_series(symbol: str):
    try:
        return load_series(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/paper/accounts")
def get_paper_accounts() -> dict[str, Any]:
    accounts = paper_trading.list_accounts()
    return {"accounts": [account for account in accounts if not account["retired"]],
            "retiredAccounts": [account for account in accounts if account["retired"]]}


@app.post("/api/paper/accounts")
def start_paper_account(payload: PaperAccountRequest) -> dict[str, Any]:
    if not is_tradable_equity(payload.symbol):
        raise HTTPException(status_code=422, detail="紙上帳戶目前只支援本機個股清單內的股票；指數和其他代號不可作為一股成交。")
    if payload.strategy == "agent" and payload.model is not None:
        raise HTTPException(status_code=422, detail="AI 代理帳戶不使用研究工作台的凍結模型權重。")
    series = _paper_series(payload.symbol)
    try:
        artifact = None
        if payload.strategy == "neural":
            if not payload.model:
                raise ValueError("神經網路策略必須選擇模型。")
            latest = get_latest_validation(payload.symbol)
            if not latest or latest.get("datasetHash") != series.digest:
                raise ValueError("此標的沒有與目前資料版本相符的最新驗證結果；請先完成模型驗證。")
            config_data, result = latest["config"], latest["result"]
            lock_state = _final_state_for_dataset(series.digest, payload.symbol)
            if lock_state.get("status") != "spent" or lock_state.get("model") != payload.model:
                raise ValueError("請先對此資料版本與所選模型完成鎖定測試，再建立神經網路紙上帳戶。")
            locked_config = lock_state.get("config", {})
            compared_keys = ("symbol", "features", "lookback", "horizon", "returnType", "buyThreshold", "sellThreshold", "epochs", "batchSize",
                             "hiddenUnits", "hiddenLayers", "hiddenSizes", "dropout", "learningRate", "optimizer", "loss", "seed")
            if any(locked_config.get(key) != config_data.get(key) for key in compared_keys):
                raise ValueError("最新驗證設定與已完成的鎖定測試不一致；請重新驗證並執行鎖定測試。")
            split_boundary = result.get("testBoundary")
            if not split_boundary or series.dates[-1] < split_boundary or series.digest != latest.get("datasetHash"):
                raise ValueError("目前資料尚未到鎖定測試邊界；請先完成獨立測試，之後再啟動前瞻紙上模擬。")
            validated = {item.get("key") for item in result.get("models", [])}
            if payload.model not in validated:
                raise ValueError("所選模型不在最新驗證結果中。")
            if (payload.buyThreshold, payload.sellThreshold) != (config_data.get("buyThreshold"), config_data.get("sellThreshold")):
                raise ValueError("紙上帳戶的進出場門檻必須沿用最新驗證設定。")
            model_config = config_from_request(locked_config)
            sample_data = build_samples(series, locked_config["features"], locked_config["lookback"], locked_config["horizon"], locked_config["returnType"] == "log")
            if series.dates[int(sample_data["split_index"])] != split_boundary:
                raise ValueError("最新驗證的鎖定邊界與目前資料切分不一致；請重新執行模型驗證。")
            artifact = fit_deployment_artifact(sample_data, payload.model, model_config)
            artifact["datasetHash"] = series.digest
        account = paper_trading.create_account(
            payload.symbol, series.dates, series.closes.tolist(), lookback=payload.lookback,
            initial_cash=payload.initialCash, commission_rate=payload.commissionBps / 10000,
            sell_tax_rate=payload.sellTaxBps / 10000, slippage_bps=payload.slippageBps,
            max_exposure_pct=payload.maxExposurePct,
            strategy=payload.strategy, model_artifact=artifact,
            buy_threshold=payload.buyThreshold, sell_threshold=payload.sellThreshold,
            nickname=payload.nickname, mascot_color=payload.mascotColor,
            mascot_accessory=payload.mascotAccessory, creation_key=payload.creationKey,
            agent_provider=payload.agentProvider, agent_auto_enabled=payload.agentAutoEnabled,
        )
        return {"account": account, "data": {"lastDate": series.dates[-1], "digest": series.digest,
                                               "fields": series.source.get("fields", ["date", "close"])}}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/paper/accounts/{account_id}/advance")
def advance_paper_account(account_id: str) -> dict[str, Any]:
    accounts = {account["id"]: account for account in paper_trading.list_accounts()}
    account = accounts.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="找不到紙上交易帳戶。")
    series = _paper_series(account["symbol"])
    try:
        return {"account": paper_trading.advance_account(account_id, series.dates, series.closes.tolist()),
                "data": {"lastDate": series.dates[-1], "digest": series.digest,
                         "fields": series.source.get("fields", ["date", "close"])}}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/paper/sync-all")
def sync_all_paper_accounts() -> dict[str, Any]:
    outcomes = []
    for account in paper_trading.list_accounts():
        if account["retired"]:
            continue
        try:
            series = _paper_series(account["symbol"])
            updated = paper_trading.advance_account(account["id"], series.dates, series.closes.tolist())
            outcomes.append({"id": account["id"], "ok": True, "advancedSessions": updated["advancedSessions"],
                             "lastDate": updated["lastDate"], "retired": updated["retired"]})
        except Exception as exc:
            outcomes.append({"id": account["id"], "ok": False, "error": str(exc)})
    return {"outcomes": outcomes}


@app.post("/api/paper/accounts/{account_id}/mascot")
def edit_paper_mascot(account_id: str, payload: MascotRequest) -> dict[str, Any]:
    try:
        return {"account": paper_trading.update_mascot(account_id, nickname=payload.nickname,
                                                        mascot_color=payload.mascotColor,
                                                        mascot_accessory=payload.mascotAccessory)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/paper/accounts/{account_id}/settings")
def edit_paper_settings(account_id: str, payload: PaperSettingsRequest) -> dict[str, Any]:
    try:
        return {"account": paper_trading.update_account_settings(
            account_id, lookback=payload.lookback, initial_cash=payload.initialCash,
            commission_rate=payload.commissionBps / 10000, sell_tax_rate=payload.sellTaxBps / 10000,
            slippage_bps=payload.slippageBps, max_exposure_pct=payload.maxExposurePct,
        )}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/paper/accounts/{account_id}/pause")
def pause_paper_account(account_id: str) -> dict[str, Any]:
    try:
        return {"account": paper_trading.pause_account(account_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/paper/accounts/{account_id}/resume")
def resume_paper_account(account_id: str) -> dict[str, Any]:
    try:
        return {"account": paper_trading.resume_account(account_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/paper/accounts/{account_id}/agent-automation")
def set_paper_agent_automation(account_id: str, payload: PaperAgentAutomationRequest) -> dict[str, Any]:
    try:
        return {"account": paper_trading.set_agent_automation(account_id, payload.enabled)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "taiex-neural-lab", "device": "cpu", "torch": __import__("torch").__version__}


@app.get("/api/data/status")
def get_data_status(symbol: str = "TAIEX") -> dict[str, Any]:
    try:
        if symbol == "TAIEX":
            status = data_status()
        else:
            series = load_series(symbol)
            split = int(len(series.dates) * 0.8)
            stock = next(item for item in stock_universe()["stocks"] if item["symbol"] == symbol)
            status = {"symbol": symbol, "name": stock["name"], "rows": len(series.dates), "start": series.dates[0], "end": series.dates[-1],
                      "source": series.source.get("source", "TWSE local archive"), "sourceUrl": series.source.get("sourceUrl"),
                      "sha256": series.digest, "trainValidationEnd": series.dates[split-1],
                      "validationStart": series.dates[int(split*0.5)], "lockedTestStart": series.dates[split],
                      "fields": ["date", "close"], "featureNote": f"{symbol} 日收盤資料；特徵由歷史收盤價計算，不含 OHLC 或成交量。",
                      "features": [{"key": key, "label": label} for key,label in FEATURES.items()]}
        return status
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/data/lock-status")
def get_lock_status(symbol: str = "TAIEX") -> dict[str, Any]:
    """Return only whether the one-time evaluation is available; never expose its result."""
    try:
        digest = load_series(symbol).digest
        state = _final_state_for_dataset(digest, symbol)
        return {"status": state.get("status", "available"), "datasetHashMismatch": bool(state.get("datasetHashMismatch"))}
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/data/series")
def get_series(symbol: str = "TAIEX", full: bool = False, end: Optional[str] = None) -> dict[str, Any]:
    series = load_series(symbol)
    if full:
        indices = range(len(series.dates)) if end is None else (i for i, day in enumerate(series.dates) if day <= end)
        points = [{"date": series.dates[i], "close": float(series.closes[i])} for i in indices]
        if not points:
            raise HTTPException(status_code=422, detail="指定日期以前沒有可用資料。")
        return {"points": points, "sha256": series.digest, "symbol": symbol, "full": True, "rangeEnd": points[-1]["date"]}
    # A chart-friendly decimation that keeps the exact start and end dates.
    stride = max(1, len(series.dates) // 700)
    points = [{"date": series.dates[i], "close": float(series.closes[i])} for i in range(0, len(series.dates), stride)]
    if points[-1]["date"] != series.dates[-1]:
        points.append({"date": series.dates[-1], "close": float(series.closes[-1])})
    return {"points": points, "sha256": series.digest, "symbol": symbol}


@app.get("/api/stocks")
def get_stocks() -> dict[str, Any]:
    return stock_universe()


@app.post("/api/stocks/refresh")
def refresh_stocks(payload: Optional[StockRefreshRequest] = None) -> dict[str, Any]:
    global refresh_in_progress
    with jobs_lock:
        if refresh_in_progress or any(job["status"] in {"queued", "running"} for job in jobs.values()):
            raise HTTPException(status_code=409, detail="訓練工作執行中，完成或取消後再更新資料。")
        refresh_in_progress = True
    try:
        return refresh_stock_data(payload.symbols if payload else None)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        with jobs_lock:
            refresh_in_progress = False


@app.post("/api/data/refresh")
def refresh_data() -> dict[str, Any]:
    global refresh_in_progress
    with jobs_lock:
        if refresh_in_progress or any(job["status"] in {"queued", "running"} for job in jobs.values()):
            raise HTTPException(status_code=409, detail="訓練工作執行中，完成或取消後再更新資料。")
        refresh_in_progress = True
    try:
        return refresh_latest_month()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        with jobs_lock:
            refresh_in_progress = False


@app.get("/api/learning/trace")
def learning_trace() -> dict[str, Any]:
    return numpy_mlp_trace()


@app.post("/api/experiments")
def create_experiment(payload: ExperimentRequest) -> dict[str, Any]:
    return _start_job(payload)


@app.get("/api/jobs/active")
def get_active_job() -> Any:
    """Let a reloaded page reconnect to the single in-memory training job."""
    with jobs_lock:
        active = next((job for job in jobs.values() if job["status"] in {"queued", "running"}), None)
        return {k: v for k, v in active.items() if k != "cancel"} if active else None


@app.get("/api/validation/latest")
def get_latest_validation(symbol: str = "TAIEX") -> Any:
    """Return the last validation for the current dataset so the UI can restore it."""
    series = load_series(symbol)
    with jobs_lock:
        record = validation_registry.get(f"{symbol}:{series.digest}")
        if record and record.get("result"):
            return {"datasetHash": series.digest, "config": record["config"], "result": record["result"]}
    try:
        saved_path = ROOT / "data" / f"latest-validation-{series.digest[:16]}.json"
        if not saved_path.exists() and symbol == "TAIEX":
            # Older builds stored the default index under a fixed name. Accept it
            # only when its embedded hash still matches the current local series.
            saved_path = ROOT / "data" / "latest-validation-sequence-v1.json"
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        return saved if saved.get("datasetHash") == series.digest and saved.get("config", {}).get("symbol", "TAIEX") == symbol else None
    except (OSError, ValueError, AttributeError):
        return None


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        record = jobs.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="找不到這個實驗工作。")
        return {k: v for k, v in record.items() if k != "cancel"}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        record = jobs.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="找不到這個實驗工作。")
        if record["status"] not in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="這個工作已結束，不能取消。")
        record["cancel"].set()
    return {"jobId": job_id, "status": "cancelling"}


@app.post("/api/final-evaluation")
def final_evaluation(payload: FinalRequest) -> dict[str, Any]:
    _check_request(payload, True)
    series = load_series(payload.symbol)
    state = _final_state_for_dataset(series.digest, payload.symbol)
    if state.get("status") in {"running", "spent"}:
        raise HTTPException(status_code=409, detail="這份資料的鎖定測試已啟動或已完成，不能再次用於選模。")
    with jobs_lock:
        validation = validation_registry.get(f"{payload.symbol}:{series.digest}")
        if not validation:
            try:
                saved_path = ROOT / "data" / f"latest-validation-{series.digest[:16]}.json"
                saved = json.loads(saved_path.read_text(encoding="utf-8"))
                if saved.get("datasetHash") == series.digest:
                    validation = {
                        "config": saved["config"],
                        "validatedModels": saved["config"]["modelTypes"],
                        "result": saved["result"],
                    }
                    validation_registry[f"{payload.symbol}:{series.digest}"] = validation
            except (OSError, ValueError, KeyError, TypeError):
                validation = None
    if not validation or payload.modelTypes[0] not in validation["validatedModels"]:
        raise HTTPException(status_code=409, detail="先用目前這份資料完成 walk-forward 驗證，再選其中一種模型做鎖定測試。")
    requested = payload.model_dump()
    validated = validation["config"]
    validation_config = {key: value for key, value in requested.items() if key not in {"modelTypes", "buyThreshold", "sellThreshold"}}
    if any(validation_config[key] != validated[key] for key in validation_config):
        raise HTTPException(status_code=409, detail="資料、特徵或訓練參數與已驗證設定不同；請先重新執行驗證。")
    return _start_job(payload, final=True)

