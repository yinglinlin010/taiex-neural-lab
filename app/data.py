"""Taiwan market close series, causal features, and time-aware data splits."""

from __future__ import annotations

import csv
import http.cookiejar
import hashlib
import json
import math
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "taiex_close.csv"
META_PATH = DATA_DIR / "metadata.json"
# Keep evaluations from the previous UI/model protocol intact while starting a
# fresh one-time test gate for this redesigned experiment workflow.
FINAL_STATE_PATH = DATA_DIR / "final-test-state-sequence-v1.json"
SOURCE_URL = "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST"

FEATURES: dict[str, str] = {
    "return_1": "單日報酬",
    "return_5": "5 日累積報酬",
    "return_20": "20 日累積報酬",
    "volatility_5": "5 日波動度",
    "volatility_20": "20 日波動度",
}

# A curated large-cap watchlist. This is a stable learning universe, not a
# claim that these are the most actively traded stocks today.
POPULAR_STOCKS = [
    {"symbol": "2330.TW", "name": "台積電", "market": "TWSE"},
    {"symbol": "2317.TW", "name": "鴻海", "market": "TWSE"},
    {"symbol": "2454.TW", "name": "聯發科", "market": "TWSE"},
    {"symbol": "2308.TW", "name": "台達電", "market": "TWSE"},
    {"symbol": "2881.TW", "name": "富邦金", "market": "TWSE"},
    {"symbol": "2882.TW", "name": "國泰金", "market": "TWSE"},
    {"symbol": "2303.TW", "name": "聯電", "market": "TWSE"},
    {"symbol": "2382.TW", "name": "廣達", "market": "TWSE"},
    {"symbol": "3711.TW", "name": "日月光投控", "market": "TWSE"},
    {"symbol": "2603.TW", "name": "長榮", "market": "TWSE"},
]
TRADABLE_EQUITY_SYMBOLS = frozenset(item["symbol"] for item in POPULAR_STOCKS)
STOCK_DATA_DIR = DATA_DIR / "stocks"


def is_tradable_equity(symbol: str) -> bool:
    """Return whether a symbol is in the local individual-equity data universe."""
    return isinstance(symbol, str) and symbol in TRADABLE_EQUITY_SYMBOLS


def _symbol_file(symbol: str) -> Path:
    if symbol not in {item["symbol"] for item in POPULAR_STOCKS}:
        raise ValueError("目前只支援熱門清單中的台股標的。")
    return STOCK_DATA_DIR / f"{symbol.replace('.', '_')}_close.csv"


@dataclass(frozen=True)
class Series:
    dates: list[str]
    closes: np.ndarray
    source: dict[str, Any]
    digest: str


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_series(symbol: str = "TAIEX") -> Series:
    path = CSV_PATH if symbol == "TAIEX" else _symbol_file(symbol)
    if not path.exists():
        raise ValueError(f"找不到 {symbol} 本機收盤資料；請先按『更新個股資料』取得 TWSE 日資料。")
    dates: list[str] = []
    closes: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["date", "close"]:
            raise ValueError("資料欄位必須是 date,close；此專題目前使用每日收盤資料。")
        for row in reader:
            try:
                datetime.strptime(row["date"], "%Y-%m-%d")
                close = float(row["close"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"資料列格式錯誤：{row}") from exc
            if not math.isfinite(close) or close <= 0:
                raise ValueError(f"收盤指數必須是正有限數值：{row}")
            dates.append(row["date"])
            closes.append(close)
    if len(dates) < 800:
        raise ValueError(f"{symbol} 目前只有 {len(dates)} 筆；至少需要 800 個交易日才能進行此專題的時間序列驗證。")
    if dates != sorted(set(dates)):
        raise ValueError("日期必須遞增且不能重複。")
    source: dict[str, Any] = {}
    meta_path = META_PATH if symbol == "TAIEX" else path.with_suffix(".json")
    if meta_path.exists():
        source = json.loads(meta_path.read_text(encoding="utf-8"))
    return Series(dates, np.asarray(closes, dtype=np.float64), source, _file_hash(path))


def data_status() -> dict[str, Any]:
    series = load_series()
    values = list(FEATURES.items())
    split = int(len(series.dates) * 0.8)
    return {
        "symbol": "TAIEX",
        "name": "臺灣加權股價指數",
        "rows": len(series.dates),
        "start": series.dates[0],
        "end": series.dates[-1],
        "source": series.source.get("source", "TWSE local archive"),
        "sourceUrl": series.source.get("sourceUrl", SOURCE_URL),
        "sha256": series.digest,
        "trainValidationEnd": series.dates[split - 1],
        "validationStart": series.dates[int(split * 0.5)],
        "lockedTestStart": series.dates[split],
        "fields": ["date", "close"],
        "featureNote": "本機 TAIEX 快照只含收盤指數；特徵由過去收盤價計算，不含 OHLC 與成交量。",
        "features": [{"key": key, "label": label} for key, label in values],
    }


def stock_universe() -> dict[str, Any]:
    stocks = []
    for item in POPULAR_STOCKS:
        path = _symbol_file(item["symbol"])
        meta_path = path.with_suffix(".json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        try:
            available = load_series(item["symbol"])
            rows, start, end = len(available.dates), available.dates[0], available.dates[-1]
        except ValueError:
            rows, start, end = 0, None, None
        stocks.append({**item, "available": bool(rows), "rows": rows, "start": start, "end": end,
                       "sha256": _file_hash(path) if path.exists() else None,
                       "source": meta.get("source", "TWSE 公開日資料")})
    snapshot_dates = [meta.get("retrievedAt", "")[:10] for stock in stocks
                      for meta_path in [_symbol_file(stock["symbol"]).with_suffix(".json")]
                      if meta_path.exists() and meta_path.is_file()]
    snapshot = max(snapshot_dates) if snapshot_dates else "尚未擷取"
    return {"stocks": stocks, "expectedCount": len(POPULAR_STOCKS), "universeNote": f"固定大型股教學樣本；資料快照截至 {snapshot}（非歷史市場母體或即時成交量排行榜）；逐檔標示本機資料範圍與雜湊。"}


def refresh_stock_data(symbols: list[str] | None = None) -> dict[str, Any]:
    """Download official TWSE daily stock data for the curated watchlist."""
    import time

    selected = {item["symbol"] for item in POPULAR_STOCKS} if symbols is None else set(symbols)
    allowed = {item["symbol"] for item in POPULAR_STOCKS}
    if not selected or not selected <= allowed:
        raise ValueError("更新標的必須是熱門股清單中的一種或多種股票。")

    class TwseRedirectHandler(urllib.request.HTTPRedirectHandler):
        # Some TWSE edge nodes respond with 308, which urllib on older Python
        # versions does not follow by default.
        def http_error_308(self, request, response, code, message, headers):
            return self.redirect_request(request, response, code, message, headers)

    opener = urllib.request.build_opener(TwseRedirectHandler())

    STOCK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    updated, errors = [], []
    for stock in POPULAR_STOCKS:
        if stock["symbol"] not in selected:
            continue
        symbol, code = stock["symbol"], stock["symbol"].split(".")[0]
        path = _symbol_file(symbol)
        try:
            history: dict[str, float] = {}
            if path.exists():
                with path.open(newline="", encoding="utf-8") as handle:
                    for row in csv.DictReader(handle):
                        history[row["date"]] = float(row["close"])
            if history:
                latest = max(history)
                first_year = max(2023, int(latest[:4]))
                first_month = max(1, int(latest[5:7]) - 1)
            else:
                # 2023 onward is still more than the 800-row training gate.
                first_year, first_month = 2023, 1
            current_year = date.today().year
            for year in range(first_year, current_year + 1):
                for month in range(first_month if year == first_year else 1, 13):
                    if (year, month) > (current_year, date.today().month):
                        break
                    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?" + urllib.parse.urlencode(
                        {"response": "json", "date": f"{year}{month:02d}01", "stockNo": code}
                    )
                    request = urllib.request.Request(url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; TAIEX Neural Network Learning Lab/1.0)",
                        "Accept": "application/json", "Referer": "https://www.twse.com.tw/",
                    })
                    payload = None
                    last_error: Exception | None = None
                    for attempt in range(4):
                        try:
                            with opener.open(request, timeout=20) as response:
                                payload = json.loads(response.read().decode("utf-8"))
                            last_error = None
                            break
                        except Exception as exc:
                            last_error = exc
                            time.sleep(1.2 * (attempt + 1))
                    if last_error:
                        raise RuntimeError(f"{year}-{month:02d} 取得失敗：{last_error}") from last_error
                    if payload and payload.get("stat") == "OK":
                        for row in payload.get("data", []):
                            try:
                                roc, mo, day_num = map(int, row[0].split("/"))
                                close = float(str(row[6]).replace(",", ""))
                                if close > 0:
                                    history[date(roc + 1911, mo, day_num).isoformat()] = close
                            except (ValueError, TypeError, IndexError):
                                continue
                    # Polite delay for TWSE rate-limiting policy (prevents HTTP 429)
                    time.sleep(2.5)
            if len(history) < 800:
                raise RuntimeError(f"僅取得 {len(history)} 筆，未達 800 筆；未寫入不完整資料。")
            rows = sorted(history.items())
            temporary = path.with_suffix(".tmp")
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle); writer.writerow(["date", "close"]); writer.writerows(rows)
            temporary.replace(path)
            digest = _file_hash(path)
            path.with_suffix(".json").write_text(json.dumps({
                "source": "TWSE STOCK_DAY monthly daily trading data", "sourceUrl": "https://www.twse.com.tw/exchangeReport/STOCK_DAY",
                "symbol": symbol, "retrievedAt": datetime.now(timezone.utc).isoformat(),
                "rows": len(rows), "from": rows[0][0], "to": rows[-1][0], "sha256": digest,
                "fields": ["date", "close"], "note": "使用 TWSE 日成交資料中的收盤價；不含 OHLC 與成交量。"
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            updated.append({"symbol": symbol, "rows": len(rows), "from": rows[0][0], "to": rows[-1][0], "sha256": digest})
        except Exception as exc:  # one unavailable symbol must not hide successful updates
            errors.append({"symbol": symbol, "message": str(exc)})
    return {"updated": updated, "count": len(updated), "errors": errors}


def read_final_state(digest: str | None = None, symbol: str = "TAIEX") -> dict[str, Any]:
    # Final-test exposure is locked by symbol, not just file hash. Refreshing a
    # dataset must not silently make an already inspected holdout look unused.
    path = DATA_DIR / f"final-test-{symbol.replace('.', '_')}-v1.json"
    candidates = [path]
    if symbol == "TAIEX":
        # Honor prior one-time test records across protocol/file migrations.
        # A changed CSV hash does not make an inspected holdout fresh again.
        candidates.extend([FINAL_STATE_PATH, DATA_DIR / "final-test-state.json"])
    states: list[tuple[Path, dict[str, Any]]] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            states.append((candidate, json.loads(candidate.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    spent = next(((candidate, state) for candidate, state in states if state.get("status") == "spent"), None)
    if spent:
        candidate, state = spent
        recorded_hash = state.get("datasetHash")
        return {
            **state,
            "datasetHashMismatch": bool(digest and recorded_hash and recorded_hash != digest),
            "legacyStateFile": candidate.name if candidate != path else None,
        }
    for candidate, state in states:
        if candidate == path and digest and state.get("datasetHash") and state.get("datasetHash") != digest:
            continue
        if candidate == FINAL_STATE_PATH and digest and state.get("datasetHash") and state.get("datasetHash") != digest:
            continue
        return state
    return {"status": "available"}


def write_final_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    symbol = str(state.get("symbol", "TAIEX"))
    path = DATA_DIR / f"final-test-{symbol.replace('.', '_')}-v1.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def refresh_latest_month() -> dict[str, Any]:
    """Fill any missing months and refresh the latest month from the TWSE endpoint."""
    current = load_series()
    existing = {d: float(v) for d, v in zip(current.dates, current.closes)}
    start_month = datetime.strptime(current.dates[-1], "%Y-%m-%d").date().replace(day=1)
    end_month = date.today().replace(day=1)
    months: list[date] = []
    month = start_month
    while month <= end_month:
        months.append(month)
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    source_url = "https://www.twse.com.tw/indicesReport/MI_5MINS_HIST"
    updated = 0
    try:
        for requested_month in months:
            url = f"{source_url}?date={requested_month:%Y%m}01&response=json"
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; TAIEX Neural Network Learning Lab/1.0)",
                    "Accept": "application/json",
                    "Referer": "https://www.twse.com.tw/zh/indices/taiex/mi-5min-hist.html",
                },
            )
            with opener.open(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("stat") != "OK":
                raise RuntimeError(f"TWSE 未回傳 {requested_month:%Y-%m} 的有效資料：{payload.get('stat', 'unknown status')}")
            for row in payload.get("data", []):
                try:
                    roc, mo, day_num = map(int, row[0].split("/"))
                    day = date(roc + 1911, mo, day_num).isoformat()
                    close = float(str(row[4]).replace(",", ""))
                except (ValueError, TypeError, IndexError):
                    continue
                if close > 0:
                    if day not in existing:
                        updated += 1
                    existing[day] = close
    except Exception as exc:
        raise RuntimeError(f"更新 {requested_month:%Y-%m} 期間失敗，原始資料未變更：{exc}") from exc
    if not existing:
        raise RuntimeError("TWSE 回應沒有可用的收盤指數資料。")
    rows = sorted(existing.items())
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "close"])
        writer.writerows(rows)
    tmp.replace(CSV_PATH)
    metadata = {
        "source": "TWSE local daily index snapshots with manual refresh from TWSE monthly history",
        "sourceUrl": source_url,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "from": rows[0][0],
        "to": rows[-1][0],
        "sha256": _file_hash(CSV_PATH),
        "fields": ["date", "close"],
        "note": "本機歷史快照不含 TAIEX 日 OHLC；最新更新亦只合併收盤指數。",
        "updatedRows": updated,
        "refreshedMonths": [f"{item:%Y-%m}" for item in months],
    }
    META_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"updatedRows": updated, "refreshedMonths": metadata["refreshedMonths"], "rows": len(rows), "through": rows[-1][0], "sha256": metadata["sha256"]}


def build_samples(
    series: Series,
    selected_features: list[str],
    lookback: int,
    horizon: int,
    use_log_return: bool,
) -> dict[str, Any]:
    if not selected_features or any(key not in FEATURES for key in selected_features):
        raise ValueError("至少選一個有效特徵。")
    if len(set(selected_features)) != len(selected_features):
        raise ValueError("特徵不能重複。")
    if lookback < 5 or lookback > 60:
        raise ValueError("觀察窗需介於 5 到 60 個交易日。")
    if horizon not in (1, 5, 20):
        raise ValueError("預測期只能是 1、5 或 20 個交易日。")
    closes = series.closes
    daily = np.full(len(closes), np.nan, dtype=np.float64)
    daily[1:] = closes[1:] / closes[:-1] - 1.0
    if use_log_return:
        daily[1:] = np.log(closes[1:] / closes[:-1])
    values: dict[str, np.ndarray] = {"return_1": daily}
    for window in (5, 20):
        arr = np.full(len(closes), np.nan, dtype=np.float64)
        arr[window:] = closes[window:] / closes[:-window] - 1.0
        if use_log_return:
            arr[window:] = np.log(closes[window:] / closes[:-window])
        values[f"return_{window}"] = arr
        vol = np.full(len(closes), np.nan, dtype=np.float64)
        for t in range(window, len(closes)):
            vol[t] = float(np.std(daily[t - window + 1 : t + 1], ddof=1))
        values[f"volatility_{window}"] = vol
    feature_matrix = np.column_stack([values[key] for key in selected_features])
    # Each feature's first valid row equals its rolling window; require the
    # entire lookback window to begin after the latest feature warm-up.
    # Feature suffixes describe return/volatility horizons, not uniformly
    # the first valid row: return_1 starts at row 1, while return_20 and
    # volatility_20 start at row 20. The full lookback must begin at or after
    # the latest selected feature's actual warm-up row.
    warmup_by_feature = {
        "return_1": 1,
        "return_5": 5,
        "return_20": 20,
        "volatility_5": 5,
        "volatility_20": 20,
    }
    latest_warmup = max(warmup_by_feature[key] for key in selected_features)
    start = max(lookback - 1, latest_warmup + lookback - 1)
    # The signal is available after close[t]. With close-only data, define the
    # target from the next close to the close horizon sessions after that.
    # This keeps the prediction target aligned with a next-close execution.
    origins = np.arange(start, len(closes) - horizon - 1, dtype=int)
    entry_indices = origins + 1
    targets = origins + horizon + 1
    x_list: list[np.ndarray] = []
    y_list: list[float] = []
    good_origins: list[int] = []
    good_targets: list[int] = []
    for origin, entry, target in zip(origins, entry_indices, targets):
        window = feature_matrix[origin - lookback + 1 : origin + 1]
        if window.shape[0] != lookback or not np.isfinite(window).all():
            continue
        raw_return = closes[target] / closes[entry] - 1.0
        target_return = math.log(closes[target] / closes[entry]) if use_log_return else raw_return
        x_list.append(window.astype(np.float32))
        y_list.append(target_return)
        good_origins.append(int(origin))
        good_targets.append(int(target))
    return {
        "x": np.asarray(x_list, dtype=np.float32),
        "y": np.asarray(y_list, dtype=np.float32),
        "origins": np.asarray(good_origins, dtype=int),
        "entry_indices": np.asarray(good_origins, dtype=int) + 1,
        "targets": np.asarray(good_targets, dtype=int),
        "dates": series.dates,
        "split_index": int(len(series.dates) * 0.8),
        "selected_features": selected_features,
        "lookback": lookback,
        "horizon": horizon,
        "execution": "next_close",
        "return_type": "log" if use_log_return else "simple",
    }


_FEATURE_WARMUP = {"return_1": 1, "return_5": 5, "return_20": 20, "volatility_5": 5, "volatility_20": 20}


def _causal_feature_matrix(closes: np.ndarray, selected_features: list[str], use_log_return: bool = False) -> np.ndarray:
    daily = np.full(len(closes), np.nan, dtype=np.float64)
    daily[1:] = np.log(closes[1:] / closes[:-1]) if use_log_return else closes[1:] / closes[:-1] - 1.0
    values: dict[str, np.ndarray] = {"return_1": daily}
    for window in (5, 20):
        returns = np.full(len(closes), np.nan, dtype=np.float64)
        returns[window:] = np.log(closes[window:] / closes[:-window]) if use_log_return else closes[window:] / closes[:-window] - 1.0
        values[f"return_{window}"] = returns
        volatility = np.full(len(closes), np.nan, dtype=np.float64)
        for index in range(window, len(closes)):
            volatility[index] = float(np.std(daily[index-window+1:index+1], ddof=1))
        values[f"volatility_{window}"] = volatility
    return np.column_stack([values[key] for key in selected_features])


def build_latest_feature_window(closes: list[float] | np.ndarray, selected_features: list[str], lookback: int,
                                return_type: str = "simple") -> np.ndarray:
    """Build the current close's causal feature window without requiring future labels."""
    values = np.asarray(closes, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("收盤價序列必須是非空的有限正數。")
    if not selected_features or any(key not in FEATURES for key in selected_features) or len(set(selected_features)) != len(selected_features):
        raise ValueError("模型特徵設定無效。")
    if not isinstance(lookback, int) or isinstance(lookback, bool) or not 5 <= lookback <= 60:
        raise ValueError("模型觀察窗需介於 5 到 60 個交易日。")
    if return_type not in {"simple", "log"}:
        raise ValueError("模型報酬類型設定無效。")
    feature_matrix = _causal_feature_matrix(values, selected_features, return_type == "log")
    start = max(lookback - 1, max(_FEATURE_WARMUP[key] for key in selected_features) + lookback - 1)
    if len(values) - 1 < start:
        raise ValueError("目前可用收盤資料不足以建立模型輸入視窗。")
    window = feature_matrix[len(values) - lookback:]
    if window.shape != (lookback, len(selected_features)) or not np.isfinite(window).all():
        raise ValueError("目前收盤資料無法建立完整模型特徵視窗。")
    return window.astype(np.float32)


def walk_forward_folds(samples: dict[str, Any], folds: int = 4) -> list[tuple[np.ndarray, np.ndarray]]:
    origins = samples["origins"]
    targets = samples["targets"]
    split = samples["split_index"]
    # Purge any label whose holding period would overlap the locked segment.
    pool = np.flatnonzero(targets < split)
    if len(pool) < 500:
        raise ValueError("訓練與驗證區資料不足；請縮短觀察窗或檢查資料。")
    first_validation = max(int(split * 0.50), int(targets[pool[0]] + 250))
    boundaries = np.linspace(first_validation, split, folds + 1, dtype=int)
    result = []
    for i in range(folds):
        val_start, val_end = int(boundaries[i]), int(boundaries[i + 1])
        # Purged walk-forward (López de Prado, 2018):
        # Validation samples have targets in [val_start, val_end) so targets < split is respected
        val_idx = np.flatnonzero((targets >= val_start) & (targets < val_end) & (targets < split))
        if len(val_idx) < 20:
            continue
        # Training labels must conclude before the earliest validation origin,
        # with Embargoing to prevent serial correlation leakage (López de Prado 2018):
        embargo = min(5, samples.get("horizon", 1)) if samples.get("horizon", 1) > 1 else 0
        min_val_origin = int(np.min(origins[val_idx]))
        train_idx = np.flatnonzero(targets <= min_val_origin - embargo)
        if len(train_idx) < 250:
            continue
        result.append((train_idx, val_idx))
    if len(result) < 2:
        raise ValueError("資料無法建立至少兩個有效的時間序列驗證折。")
    return result
