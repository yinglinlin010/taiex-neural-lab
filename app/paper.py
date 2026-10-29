"""Persistent, close-only paper accounts for forward strategy observation.

Paper accounts never submit brokerage orders. Signals formed after a session close
are filled at the next available session close with explicit fee, tax and slippage.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Sequence
from datetime import date as calendar_date

from .strategies import time_series_momentum_signals
from .data import build_latest_feature_window
from .ml import predict_with_artifact

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "paper-trading.sqlite3"
MAX_CAPITAL = 100_000_000.0
MAX_LOOKBACK = 252


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
      CREATE TABLE IF NOT EXISTS paper_accounts (
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, initial_cash REAL NOT NULL,
        cash REAL NOT NULL, shares INTEGER NOT NULL DEFAULT 0, lookback INTEGER NOT NULL,
        max_exposure REAL NOT NULL,
        commission_rate REAL NOT NULL, sell_tax_rate REAL NOT NULL, slippage_rate REAL NOT NULL,
        last_date TEXT NOT NULL, last_close REAL NOT NULL, history_hash TEXT NOT NULL,
        pending_long INTEGER NOT NULL, pending_exposure REAL NOT NULL DEFAULT 0,
        paused INTEGER NOT NULL DEFAULT 0,
        strategy TEXT NOT NULL DEFAULT 'momentum', model_artifact TEXT,
        agent_provider TEXT, agent_auto_enabled INTEGER NOT NULL DEFAULT 0,
        buy_threshold REAL NOT NULL DEFAULT 0.002, sell_threshold REAL NOT NULL DEFAULT -0.002,
        feature_lookback INTEGER NOT NULL DEFAULT 20,
        nickname TEXT NOT NULL DEFAULT '', mascot_color TEXT NOT NULL DEFAULT 'teal',
        mascot_accessory TEXT NOT NULL DEFAULT 'dot', retired INTEGER NOT NULL DEFAULT 0,
        first_sync INTEGER NOT NULL DEFAULT 0, creation_key TEXT, creation_hash TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS paper_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL REFERENCES paper_accounts(id),
        date TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS paper_history (
        account_id TEXT NOT NULL REFERENCES paper_accounts(id), date TEXT NOT NULL, close REAL NOT NULL,
        PRIMARY KEY(account_id, date)
      );
    """)
    event_schema = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='paper_events'").fetchone()["sql"]
    if "unique(account_id,date,kind)" in (event_schema or "").lower().replace(" ", ""):
        connection.executescript("""
          BEGIN IMMEDIATE;
          CREATE TABLE paper_events_v2 (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL REFERENCES paper_accounts(id),
            date TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL
          );
          INSERT INTO paper_events_v2(seq,account_id,date,kind,payload)
            SELECT seq,account_id,date,kind,payload FROM paper_events ORDER BY seq;
          DROP TABLE paper_events;
          ALTER TABLE paper_events_v2 RENAME TO paper_events;
          COMMIT;
        """)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(paper_accounts)")}
    for name, declaration in (("strategy", "TEXT NOT NULL DEFAULT 'momentum'"), ("model_artifact", "TEXT"),
                              ("pending_exposure", "REAL NOT NULL DEFAULT 0"),
                              ("agent_provider", "TEXT"), ("agent_auto_enabled", "INTEGER NOT NULL DEFAULT 0"),
                              ("buy_threshold", "REAL NOT NULL DEFAULT 0.002"), ("sell_threshold", "REAL NOT NULL DEFAULT -0.002"),
                              ("feature_lookback", "INTEGER NOT NULL DEFAULT 20"),
                              ("nickname", "TEXT NOT NULL DEFAULT ''"), ("mascot_color", "TEXT NOT NULL DEFAULT 'teal'"),
                              ("mascot_accessory", "TEXT NOT NULL DEFAULT 'dot'"),
                              ("retired", "INTEGER NOT NULL DEFAULT 0"), ("first_sync", "INTEGER NOT NULL DEFAULT 0"),
                              ("creation_key", "TEXT"), ("creation_hash", "TEXT")):
        if name not in columns:
            connection.execute(f"ALTER TABLE paper_accounts ADD COLUMN {name} {declaration}")
    connection.execute("UPDATE paper_accounts SET pending_exposure=max_exposure WHERE pending_long=1 AND pending_exposure=0")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS paper_agent_decision_once ON paper_events(account_id,date) WHERE kind='agent_decision'")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS paper_accounts_creation_key ON paper_accounts(creation_key) WHERE creation_key IS NOT NULL")
    return connection


def _validate_inputs(dates: Sequence[str], closes: Sequence[float], lookback: int,
                     initial_cash: float, commission_rate: float, sell_tax_rate: float,
                     slippage_bps: float, max_exposure_pct: float = 20) -> tuple[list[str], list[float], float, float, float, float, float]:
    if len(dates) != len(closes):
        raise ValueError("日期與收盤價長度不一致。")
    if not isinstance(lookback, int) or isinstance(lookback, bool) or not 1 <= lookback <= MAX_LOOKBACK:
        raise ValueError(f"lookback 必須介於 1 到 {MAX_LOOKBACK}。")
    raw_numbers = (initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct)
    if any(isinstance(value, bool) for value in raw_numbers):
        raise ValueError("本金、費率、滑價與曝險上限必須是數值，不能使用布林值。")
    try:
        initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct = map(float, raw_numbers)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("本金、費率、滑價與曝險上限必須是有限數值。") from exc
    if not math.isfinite(initial_cash) or not 1 <= initial_cash <= MAX_CAPITAL:
        raise ValueError(f"模擬本金必須介於 1 到 {MAX_CAPITAL:,.0f}。")
    for name, rate in (("commission_rate", commission_rate), ("sell_tax_rate", sell_tax_rate)):
        if not math.isfinite(rate) or not 0 <= rate <= 0.05:
            raise ValueError(f"{name} 必須介於 0 到 0.05。")
    if not math.isfinite(slippage_bps) or not 0 <= slippage_bps <= 500:
        raise ValueError("滑價必須介於 0 到 500 個基點。")
    if not math.isfinite(max_exposure_pct) or not 1 <= max_exposure_pct <= 100:
        raise ValueError("單一標的曝險上限必須介於 1% 到 100%。")
    if len(dates) <= lookback:
        raise ValueError(f"至少需要 {lookback + 1} 個交易日才能產生第一個訊號。")
    normalized_dates = list(dates)
    try:
        if any(not isinstance(day, str) or calendar_date.fromisoformat(day).isoformat() != day for day in normalized_dates):
            raise ValueError("交易日期格式必須為有效的 YYYY-MM-DD。")
    except ValueError as exc:
        raise ValueError("交易日期格式必須為有效的 YYYY-MM-DD。") from exc
    if any(a >= b for a, b in zip(normalized_dates, normalized_dates[1:])):
        raise ValueError("交易日期必須嚴格遞增且不可重複。")
    try:
        normalized_closes = [float(value) for value in closes]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("收盤價必須是有限正數。") from exc
    if any(not math.isfinite(value) or value <= 0 for value in normalized_closes):
        raise ValueError("收盤價必須是有限正數。")
    return normalized_dates, normalized_closes, initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct


def _history_hash(dates: Sequence[str], closes: Sequence[float], through: int, lookback: int) -> str:
    digest = hashlib.sha256()
    start = max(0, through - lookback)
    for day, close in zip(dates[start:through + 1], closes[start:through + 1]):
        digest.update(f"{day},{close:.12g}\n".encode())
    return digest.hexdigest()


def _neural_history_length(artifact: dict[str, Any]) -> int:
    warmup = max({"return_1": 1, "return_5": 5, "return_20": 20,
                  "volatility_5": 5, "volatility_20": 20}[key] for key in artifact["features"])
    return int(artifact["lookback"]) + warmup


def _prices_match(left: float, right: float) -> bool:
    """Allow only sub-picounit float serialization noise in persisted prices."""
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)


def _snapshot(row: sqlite3.Row, events: Sequence[sqlite3.Row] = ()) -> dict[str, Any]:
    equity = float(row["cash"]) + int(row["shares"]) * float(row["last_close"])
    trades = [event for event in events if event["kind"] in ("buy", "sell")]
    latest_close = next((event for event in reversed(events) if event["kind"] == "close"), None)
    latest_close_payload = json.loads(latest_close["payload"]) if latest_close else {}
    if "maxDrawdown" in latest_close_payload:
        max_drawdown_pct = float(latest_close_payload["maxDrawdown"]) * 100
    else:
        max_drawdown_pct = max((float(json.loads(event["payload"]).get("drawdown", 0)) * 100
                                for event in events if event["kind"] == "close"), default=0)
    return {
        "id": row["id"], "symbol": row["symbol"], "lookback": row["lookback"],
        "nickname": row["nickname"], "mascotColor": row["mascot_color"],
        "mascotAccessory": row["mascot_accessory"], "retired": bool(row["retired"]),
        "firstSync": bool(row["first_sync"]),
        "strategy": row["strategy"],
        "agentProvider": row["agent_provider"],
        "agentAutoEnabled": bool(row["agent_auto_enabled"]),
        "pendingExposurePct": float(row["pending_exposure"] or 0) * 100,
        "model": ({"key": json.loads(row["model_artifact"]).get("model"),
                   "horizon": json.loads(row["model_artifact"]).get("horizon"),
                   "features": json.loads(row["model_artifact"]).get("features"),
                   "trainingThrough": json.loads(row["model_artifact"]).get("trainingThrough"),
                   "buyThreshold": row["buy_threshold"], "sellThreshold": row["sell_threshold"]}
                  if row["model_artifact"] else None),
        "initialCash": row["initial_cash"], "cash": row["cash"], "shares": row["shares"],
        "lastDate": row["last_date"], "lastClose": row["last_close"], "equity": equity,
        "pnl": equity - row["initial_cash"], "returnPct": (equity / row["initial_cash"] - 1) * 100,
        "pendingAction": ("已停止 · 待下個收盤平倉" if row["shares"] else "已停止") if row["paused"] else
                         ("買進待下個收盤" if row["pending_long"] and not row["shares"] else
                          "賣出待下個收盤" if not row["pending_long"] and row["shares"] else
                          "持有" if row["shares"] else "觀望／現金"),
        "paused": bool(row["paused"]), "tradeCount": len(trades),
        "costAssumptions": {"commissionBps": row["commission_rate"] * 10000,
                            "sellTaxBps": row["sell_tax_rate"] * 10000,
                            "slippageBps": row["slippage_rate"] * 10000,
                            "maxExposurePct": row["max_exposure"] * 100},
        "maxDrawdownPct": max_drawdown_pct,
    }


def _account_payload(row: sqlite3.Row, events: Sequence[sqlite3.Row]) -> dict[str, Any]:
    result = _snapshot(row, events)
    result["events"] = [{"date": event["date"], "kind": event["kind"], **json.loads(event["payload"])} for event in events]
    return result


def list_accounts(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(db_path or DEFAULT_DB)
    if not path.exists():
        return []
    connection = _connect(path)
    try:
        rows = connection.execute("SELECT * FROM paper_accounts ORDER BY created_at DESC, id DESC").fetchall()
        result = []
        for row in rows:
            events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (row["id"],)).fetchall()
            result.append(_account_payload(row, events))
        return result
    finally:
        connection.close()


def list_agent_accounts(provider: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    if provider not in {"codex", "antigravity"}:
        raise ValueError("代理只能是 codex 或 antigravity。")
    return [account for account in list_accounts(db_path)
            if account["strategy"] == "agent" and account["agentProvider"] == provider
            and account["agentAutoEnabled"] and not account["paused"] and not account["retired"]]


def get_agent_context(account_id: str, provider: str, db_path: str | Path | None = None) -> dict[str, Any]:
    if provider not in {"codex", "antigravity"}:
        raise ValueError("代理只能是 codex 或 antigravity。")
    connection = _connect(db_path or DEFAULT_DB)
    try:
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["strategy"] != "agent" or row["agent_provider"] != provider:
            raise ValueError("此帳戶未指派給目前的代理。")
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        decision = next((event for event in reversed(events)
                         if event["kind"] == "agent_decision" and event["date"] == row["last_date"]), None)
        history = connection.execute("SELECT date,close FROM paper_history WHERE account_id=? ORDER BY date", (account_id,)).fetchall()
        closes = [float(item["close"]) for item in history]
        if not closes or history[-1]["date"] != row["last_date"] or not _prices_match(closes[-1], float(row["last_close"])):
            raise ValueError("目前帳戶行情錨點不完整；停止代理決策以避免使用錯誤資料。")

        def trailing_return(period: int) -> float | None:
            if len(closes) <= period:
                return None
            return closes[-1] / closes[-period - 1] - 1

        returns = [(right / left) - 1 for left, right in zip(closes[-6:], closes[-5:]) if left]
        volatility_5 = (sum((value - sum(returns) / len(returns)) ** 2 for value in returns) / (len(returns) - 1)) ** 0.5 if len(returns) >= 2 else None
        snapshot = _account_payload(row, events)
        return {
            "provider": provider,
            "account": {key: snapshot[key] for key in (
                "id", "symbol", "nickname", "cash", "shares", "equity", "returnPct",
                "pendingAction", "pendingExposurePct", "costAssumptions", "lastDate", "lastClose",
            )},
            "asOf": row["last_date"],
            "decisionSubmitted": decision is not None,
            "maxAllowedExposurePct": float(row["max_exposure"]) * 100,
            "market": {
                "close": closes[-1],
                "return1d": trailing_return(1),
                "return5d": trailing_return(5),
                "return20d": trailing_return(20),
                "volatility5d": volatility_5,
                "recentCloses": [{"date": item["date"], "close": float(item["close"])} for item in history[-21:]],
            },
        }
    finally:
        connection.close()


def submit_agent_decision(account_id: str, provider: str, as_of: str, target_exposure_pct: float,
                          rationale: str, db_path: str | Path | None = None) -> dict[str, Any]:
    if provider not in {"codex", "antigravity"}:
        raise ValueError("代理只能是 codex 或 antigravity。")
    if isinstance(target_exposure_pct, bool):
        raise ValueError("目標曝險必須是有限數值。")
    try:
        target_exposure_pct = float(target_exposure_pct)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("目標曝險必須是有限數值。") from exc
    if not math.isfinite(target_exposure_pct):
        raise ValueError("目標曝險必須是有限數值。")
    rationale = str(rationale).strip()
    if not rationale or len(rationale) > 600:
        raise ValueError("決策理由需為 1 到 600 個字元。")
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["strategy"] != "agent" or row["agent_provider"] != provider:
            raise ValueError("此帳戶未指派給目前的代理。")
        if not row["agent_auto_enabled"] or row["paused"] or row["retired"]:
            raise ValueError("此代理帳戶未啟用或已停止，不能提交決策。")
        if as_of != row["last_date"]:
            raise ValueError("決策日期必須等於帳戶最新已確認收盤日。")
        if not 0 <= target_exposure_pct <= float(row["max_exposure"]) * 100:
            raise ValueError("目標曝險必須介於 0 與帳戶曝險上限之間。")
        existing = connection.execute(
            "SELECT payload FROM paper_events WHERE account_id=? AND date=? AND kind='agent_decision'",
            (account_id, as_of),
        ).fetchone()
        if existing:
            saved = json.loads(existing["payload"])
            if saved.get("targetExposurePct") == target_exposure_pct and saved.get("rationale") == rationale:
                connection.commit()
                return {"accepted": True, "duplicate": True, "date": as_of, **saved}
            raise ValueError("此帳戶與交易日已提交過不同決策；請勿覆寫歷史決策。")
        payload = {"provider": provider, "targetExposurePct": target_exposure_pct, "rationale": rationale,
                   "execution": "next_available_close", "maxExposurePct": float(row["max_exposure"]) * 100}
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, as_of, "agent_decision", json.dumps(payload, ensure_ascii=False)))
        connection.execute("UPDATE paper_accounts SET pending_long=?,pending_exposure=? WHERE id=?",
                           (int(target_exposure_pct > 0), target_exposure_pct / 100, account_id))
        connection.commit()
        return {"accepted": True, "duplicate": False, "date": as_of, **payload}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def set_agent_automation(account_id: str, enabled: bool, db_path: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(enabled, bool):
        raise ValueError("自動決策設定必須是布林值。")
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["strategy"] != "agent":
            raise ValueError("只有 AI 代理帳戶可以設定自動決策。")
        if row["retired"] or (enabled and row["paused"]):
            raise ValueError("已退場或停止的帳戶不能啟用自動決策。")
        connection.execute("UPDATE paper_accounts SET agent_auto_enabled=? WHERE id=?", (int(enabled), account_id))
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, row["last_date"], "agent_automation", json.dumps({"enabled": enabled})))
        connection.commit()
        updated = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        return _account_payload(updated, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_account(symbol: str, dates: Sequence[str], closes: Sequence[float], *,
                   lookback: int = 20, initial_cash: float = 100_000,
                   commission_rate: float = 0.001425, sell_tax_rate: float = 0.003,
                   slippage_bps: float = 10, max_exposure_pct: float = 20,
                   db_path: str | Path | None = None, strategy: str = "momentum",
                   model_artifact: dict[str, Any] | None = None,
                   buy_threshold: float = 0.002, sell_threshold: float = -0.002,
                   nickname: str = "", mascot_color: str = "teal", mascot_accessory: str = "cap",
                   creation_key: str | None = None, agent_provider: str | None = None,
                   agent_auto_enabled: bool = False) -> dict[str, Any]:
    db_path = db_path or DEFAULT_DB
    dates, closes, initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct = _validate_inputs(
        dates, closes, lookback, initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct
    )
    if strategy not in {"momentum", "neural", "agent"} or (strategy == "neural") != (model_artifact is not None):
        raise ValueError("紙上策略或神經網路模型設定無效。")
    if strategy == "agent":
        if agent_provider not in {"codex", "antigravity"} or model_artifact is not None:
            raise ValueError("AI 代理帳戶必須指定 Codex 或 Antigravity，且不能附帶神經網路權重。")
        if not isinstance(agent_auto_enabled, bool):
            raise ValueError("AI 代理自動決策設定必須是布林值。")
    elif agent_provider is not None or agent_auto_enabled:
        raise ValueError("只有 AI 代理策略可以設定模型代理或自動決策。")
    nickname = str(nickname).strip()[:24]
    if mascot_color not in {"teal", "red", "blue", "cream"} or mascot_accessory not in {"cap", "beret", "crown", "dot", "leaf", "star", "none"}:
        raise ValueError("吉祥物外觀設定無效。")
    if strategy == "neural":
        if model_artifact["returnType"] not in {"simple", "log"} or not math.isfinite(buy_threshold) or not math.isfinite(sell_threshold) or buy_threshold < 0 or sell_threshold > 0 or sell_threshold >= buy_threshold:
            raise ValueError("神經網路紙上策略門檻設定無效。")
        feature_lookback = int(model_artifact["lookback"])
        prediction = predict_with_artifact(model_artifact, build_latest_feature_window(closes, model_artifact["features"], feature_lookback, model_artifact["returnType"]))
        predicted_return = math.expm1(prediction) if model_artifact["returnType"] == "log" else prediction
        pending_long = predicted_return > buy_threshold
        history_length = max(lookback, _neural_history_length(model_artifact))
    elif strategy == "momentum":
        result = time_series_momentum_signals(closes, lookback=lookback, dates=dates)
        pending_long = bool(result.signals[-1] == 1)
        feature_lookback = lookback
        history_length = lookback
    else:
        pending_long = False
        feature_lookback = lookback
        history_length = max(lookback, 60)
    pending_exposure = max_exposure_pct / 100 if pending_long else 0.0
    request_hash = hashlib.sha256(json.dumps({"symbol": symbol, "strategy": strategy, "lookback": lookback,
        "initialCash": initial_cash, "commissionRate": commission_rate, "sellTaxRate": sell_tax_rate,
        "slippageBps": slippage_bps, "maxExposurePct": max_exposure_pct, "buyThreshold": buy_threshold,
        "sellThreshold": sell_threshold, "modelArtifact": model_artifact, "nickname": nickname,
        "mascotColor": mascot_color, "mascotAccessory": mascot_accessory, "agentProvider": agent_provider,
        "agentAutoEnabled": agent_auto_enabled}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    account_id = uuid.uuid4().hex
    history_hash = _history_hash(dates, closes, len(dates) - 1, history_length)
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if creation_key:
            existing = connection.execute("SELECT * FROM paper_accounts WHERE creation_key=?", (creation_key,)).fetchone()
            if existing:
                if existing["creation_hash"] != request_hash:
                    raise ValueError("此建立識別碼已用於不同設定；請重新開啟呼叫流程。")
                events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (existing["id"],)).fetchall()
                connection.commit()
                return _account_payload(existing, events)
        connection.execute("""INSERT INTO paper_accounts
          (id,symbol,initial_cash,cash,shares,lookback,max_exposure,commission_rate,sell_tax_rate,slippage_rate,
           last_date,last_close,history_hash,pending_long,pending_exposure,strategy,model_artifact,agent_provider,agent_auto_enabled,
           buy_threshold,sell_threshold,feature_lookback,nickname,mascot_color,mascot_accessory,creation_key,creation_hash)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (account_id, symbol, initial_cash, initial_cash, 0, lookback, max_exposure_pct / 100, commission_rate,
           sell_tax_rate, slippage_bps / 10000, dates[-1], closes[-1], history_hash,
           int(pending_long), pending_exposure, strategy, json.dumps(model_artifact) if model_artifact else None,
           agent_provider, int(agent_auto_enabled),
           buy_threshold, sell_threshold, feature_lookback, nickname, mascot_color, mascot_accessory, creation_key, request_hash))
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, dates[-1], "started", json.dumps({"signal": "long" if pending_long else "cash", "execution": "next_close",
                             "strategy": strategy, "prediction": predicted_return if strategy == "neural" else None,
                             "agentProvider": agent_provider,
                             "model": model_artifact.get("model") if model_artifact else None})))
        saved_lookback = max(history_length, MAX_LOOKBACK)
        for day, close in zip(dates[-saved_lookback - 1:], closes[-saved_lookback - 1:]):
            connection.execute("INSERT INTO paper_history(account_id,date,close) VALUES (?,?,?)",
                               (account_id, day, close))
        connection.commit()
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        output = _account_payload(row, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return output


def advance_account(account_id: str, dates: Sequence[str], closes: Sequence[float], *,
                    db_path: str | Path | None = None,
                    max_sessions: int | None = None) -> dict[str, Any]:
    db_path = db_path or DEFAULT_DB
    if len(dates) != len(closes) or not dates:
        raise ValueError("目前沒有可用的日期與收盤價序列。")
    dates, closes, *_ = _validate_inputs(dates, closes, 1, 1, 0, 0, 0)
    connection = _connect(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["retired"]:
            raise ValueError("此角色已退場，不能再同步。")
        if row["symbol"] == "":
            raise ValueError("目前資料不足以驗證帳戶策略。")
        try:
            last_index = dates.index(row["last_date"])
        except ValueError as exc:
            raise ValueError("同步資料必須保留帳戶最後交易日，才能驗證歷史錨點；請調整保留範圍後再同步。") from exc
        if not _prices_match(closes[last_index], float(row["last_close"])):
            raise ValueError("帳戶最後交易日的收盤價已變更；已停止同步，請建立新帳戶檢查。")
        anchors = connection.execute(
            "SELECT date,close FROM paper_history WHERE account_id=? ORDER BY date ASC", (account_id,)
        ).fetchall()
        if not anchors:
            raise ValueError("此帳戶缺少可驗證的策略錨點（可能由舊版建立）；請建立新紙上帳戶後再同步。")
        anchor_dates = [anchor["date"] for anchor in anchors]
        anchor_closes = [float(anchor["close"]) for anchor in anchors]
        artifact = json.loads(row["model_artifact"]) if row["strategy"] == "neural" else None
        history_length = max(row["lookback"], _neural_history_length(artifact) if artifact else
                             60 if row["strategy"] == "agent" else row["lookback"])
        if _history_hash(anchor_dates, anchor_closes, len(anchor_dates) - 1, history_length) != row["history_hash"]:
            raise ValueError("帳戶內儲存的策略錨點不一致；已停止同步，請檢查帳戶資料。")
        supplied = dict(zip(dates[:last_index + 1], closes[:last_index + 1]))
        required_anchors = anchors[-history_length - 1:]
        overlap = [anchor for anchor in required_anchors if anchor["date"] in supplied]
        for anchor in overlap:
            if not _prices_match(supplied[anchor["date"]], float(anchor["close"])):
                raise ValueError("帳戶已處理的回看窗收盤資料發生變更；已停止同步，請建立新帳戶檢查。")
        # Saved anchors are the verified strategy context. Rolling data providers
        # may prune older rows, so compare every available overlap and retain the
        # stored values for any pruned dates. The account's last date was checked
        # above and must remain present in the submitted history.
        history_verification = "verified_with_saved_anchors" if len(overlap) < len(required_anchors) else "verified"
        base_history = list(zip(anchor_dates, anchor_closes))
        new_history = list(zip(dates[last_index + 1:], closes[last_index + 1:]))
        if max_sessions is not None and (not isinstance(max_sessions, int) or isinstance(max_sessions, bool) or max_sessions < 1):
            raise ValueError("max_sessions 必須是正整數。")
        if row["strategy"] == "agent":
            new_history = new_history[:max_sessions or 1]
        elif max_sessions is not None:
            new_history = new_history[:max_sessions]
        strategy_history = base_history + new_history
        strategy_dates = [item[0] for item in strategy_history]
        strategy_closes = [item[1] for item in strategy_history]
        if row["strategy"] == "neural":
            artifact = json.loads(row["model_artifact"])
            # Continue the frozen model's causal feature stream on each new close.
            neural_signals = []
            neural_predictions = []
            for idx in range(len(base_history), len(strategy_closes)):
                window = build_latest_feature_window(strategy_closes[:idx + 1], artifact["features"], artifact["lookback"], artifact["returnType"])
                raw_prediction = predict_with_artifact(artifact, window)
                predicted_return = math.expm1(raw_prediction) if artifact["returnType"] == "log" else raw_prediction
                neural_predictions.append(predicted_return)
                neural_signals.append(1 if predicted_return > row["buy_threshold"] else 0 if predicted_return < row["sell_threshold"] else -1)
            signals = None
        elif row["strategy"] == "momentum":
            signals = time_series_momentum_signals(strategy_closes, lookback=row["lookback"], dates=strategy_dates).signals
        else:
            signals = None
        cash, shares = float(row["cash"]), int(row["shares"])
        pending_long, paused = bool(row["pending_long"]), bool(row["paused"])
        pending_exposure = float(row["pending_exposure"] or 0)
        latest_close = connection.execute(
            "SELECT payload FROM paper_events WHERE account_id=? AND kind='close' ORDER BY seq DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        peak, max_drawdown = float(row["initial_cash"]), 0.0
        if latest_close:
            latest_payload = json.loads(latest_close["payload"])
            if "peak" in latest_payload:
                peak = max(peak, float(latest_payload["peak"]))
            else:
                prior_equity = float(latest_payload.get("equity", row["initial_cash"]))
                prior_drawdown = float(latest_payload.get("drawdown", 0))
                if math.isfinite(prior_drawdown) and 0 <= prior_drawdown < 1:
                    peak = max(peak, prior_equity / (1 - prior_drawdown))
            if "maxDrawdown" in latest_payload:
                max_drawdown = float(latest_payload["maxDrawdown"])
            else:
                prior_closes = connection.execute(
                    "SELECT payload FROM paper_events WHERE account_id=? AND kind='close'", (account_id,)
                ).fetchall()
                max_drawdown = max((float(json.loads(event["payload"]).get("drawdown", 0))
                                    for event in prior_closes), default=0)
        advanced = 0
        for new_offset, (day, close) in enumerate(new_history):
            prior_day = row["last_date"] if new_offset == 0 else strategy_dates[len(base_history) + new_offset - 1]
            has_agent_decision = row["strategy"] == "agent" and connection.execute(
                "SELECT 1 FROM paper_events WHERE account_id=? AND date=? AND kind='agent_decision' LIMIT 1",
                (account_id, prior_day),
            ).fetchone() is not None
            # An agent decision is a one-session target. Without a fresh decision,
            # hold the existing position instead of silently rebalancing it.
            should_execute = row["strategy"] != "agent" or has_agent_decision or paused
            execution_target = 0.0 if paused else pending_exposure
            if row["strategy"] != "agent":
                if pending_long and shares == 0 and not paused:
                    fill_price = close * (1 + row["slippage_rate"])
                    equity_before_fill = cash + shares * close
                    budget = min(cash, equity_before_fill * row["max_exposure"])
                    bought = math.floor(budget / (fill_price * (1 + row["commission_rate"])))
                    if bought > 0:
                        gross = bought * fill_price
                        fee = gross * row["commission_rate"]
                        cash -= gross + fee
                        shares += bought
                        payload = {"shares": bought, "referenceClose": close, "fillPrice": fill_price,
                                   "gross": gross, "commission": fee, "slippageBps": row["slippage_rate"] * 10000}
                        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                           (account_id, day, "buy", json.dumps(payload)))
                    else:
                        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                           (account_id, day, "rejected", json.dumps({"reason": "依曝險上限與整股規則無法買進一股。", "referenceClose": close,
                                            "policy": "本次委託未成交；若收盤訊號仍看多，下一日重試；訊號轉空手時明確取消。"})))
                elif not pending_long and shares > 0:
                    fill_price = close * (1 - row["slippage_rate"])
                    gross = shares * fill_price
                    fee, tax = gross * row["commission_rate"], gross * row["sell_tax_rate"]
                    cash += gross - fee - tax
                    payload = {"shares": shares, "referenceClose": close, "fillPrice": fill_price,
                               "gross": gross, "commission": fee, "sellTax": tax,
                               "slippageBps": row["slippage_rate"] * 10000}
                    connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                       (account_id, day, "sell", json.dumps(payload)))
                    shares = 0
            elif should_execute:
                equity_before_fill = cash + shares * close
                target_shares = math.floor(max(0.0, equity_before_fill * execution_target) / close)
                delta = target_shares - shares
                if delta > 0:
                    fill_price = close * (1 + row["slippage_rate"])
                    affordable = math.floor(cash / (fill_price * (1 + row["commission_rate"])))
                    bought = min(delta, affordable)
                    if bought > 0:
                        gross = bought * fill_price
                        fee = gross * row["commission_rate"]
                        cash -= gross + fee
                        shares += bought
                        payload = {"shares": bought, "referenceClose": close, "fillPrice": fill_price,
                                   "gross": gross, "commission": fee, "slippageBps": row["slippage_rate"] * 10000,
                                   "targetExposurePct": execution_target * 100}
                        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                           (account_id, day, "buy", json.dumps(payload)))
                    else:
                        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                           (account_id, day, "rejected", json.dumps({"reason": "依曝險上限與整股規則無法買進一股。", "referenceClose": close,
                                            "policy": "本次委託未成交；若訊號仍有效，下一個新收盤日再處理。"})))
                elif delta < 0:
                    sold = -delta
                    fill_price = close * (1 - row["slippage_rate"])
                    gross = sold * fill_price
                    fee, tax = gross * row["commission_rate"], gross * row["sell_tax_rate"]
                    cash += gross - fee - tax
                    shares -= sold
                    payload = {"shares": sold, "referenceClose": close, "fillPrice": fill_price,
                               "gross": gross, "commission": fee, "sellTax": tax,
                               "slippageBps": row["slippage_rate"] * 10000,
                               "targetExposurePct": execution_target * 100}
                    connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                       (account_id, day, "sell", json.dumps(payload)))
            if paused:
                pending_long, pending_exposure = False, 0.0
            elif row["strategy"] != "agent":
                if row["strategy"] == "neural":
                    signal = neural_signals[new_offset]
                    if signal != -1:
                        pending_long = signal == 1
                else:
                    pending_long = bool(signals[len(base_history) + new_offset] == 1)
                pending_exposure = row["max_exposure"] if pending_long else 0.0
            equity = cash + shares * close
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak if peak else 0
            max_drawdown = max(max_drawdown, drawdown)
            connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                               (account_id, day, "close", json.dumps({"close": close, "signal": "long" if pending_long else "cash", "equity": equity,
                                "peak": peak, "drawdown": drawdown, "maxDrawdown": max_drawdown})))
            if row["strategy"] == "neural":
                connection.execute("UPDATE paper_events SET payload=? WHERE account_id=? AND date=? AND kind='close'",
                                   (json.dumps({"close": close, "signal": "long" if pending_long else "cash", "equity": equity,
                                    "peak": peak, "drawdown": drawdown, "maxDrawdown": max_drawdown,
                                    "prediction": neural_predictions[new_offset], "predictionHorizon": json.loads(row["model_artifact"])["horizon"],
                                    "model": json.loads(row["model_artifact"])["model"]}), account_id, day))
            advanced += 1
        if advanced:
            retired = bool(paused and shares == 0)
            rolling_history = strategy_history[-history_length - 1:]
            connection.execute("DELETE FROM paper_history WHERE account_id=?", (account_id,))
            connection.executemany("INSERT INTO paper_history(account_id,date,close) VALUES (?,?,?)",
                                   [(account_id, day, close) for day, close in rolling_history])
            connection.execute("""UPDATE paper_accounts SET cash=?,shares=?,last_date=?,last_close=?,
              history_hash=?,pending_long=?,pending_exposure=?,first_sync=1,retired=? WHERE id=?""",
              (cash, shares, strategy_dates[-1], strategy_closes[-1], _history_hash(strategy_dates, strategy_closes,
                                                                   len(strategy_closes) - 1, history_length),
               int(pending_long), pending_exposure, int(retired), account_id))
            if retired:
                connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                                   (account_id, strategy_dates[-1], "retired", json.dumps({"note": "最後平倉完成，吉祥物退場；帳戶與交易歷史保留。"})))
        connection.commit()
        refreshed = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        result = _account_payload(refreshed, events)
        result["advancedSessions"] = advanced
        result["historyVerification"] = history_verification
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def pause_account(account_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["paused"]:
            raise ValueError("此紙上交易帳戶已停止。")
        if row["retired"]:
            raise ValueError("此角色已退場。")
        retired = int(row["shares"] == 0)
        connection.execute("UPDATE paper_accounts SET paused=1,pending_long=0,pending_exposure=0,agent_auto_enabled=0,retired=? WHERE id=?", (retired, account_id))
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, row["last_date"], "paused", json.dumps({"note": "下個新交易日收盤模擬平倉；停止產生新進場訊號。"})))
        if retired:
            connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                               (account_id, row["last_date"], "retired", json.dumps({"note": "帳戶已無持倉，吉祥物退場；歷史保留。"})))
        connection.commit()
        updated = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        return _account_payload(updated, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def resume_account(account_id: str, db_path: str | Path | None = None) -> dict[str, Any]:
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["retired"]:
            raise ValueError("此角色已退場，帳戶僅供查閱。")
        if not row["paused"]:
            raise ValueError("此紙上交易帳戶目前正在運作。")
        if row["shares"] > 0:
            raise ValueError("帳戶仍有持倉；請先同步至預定平倉完成，再重新啟動策略。")
        connection.execute("UPDATE paper_accounts SET paused=0,pending_long=0,pending_exposure=0 WHERE id=?", (account_id,))
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, row["last_date"], "resumed", json.dumps({"note": "策略已重新啟動；依下一個新收盤日產生訊號。"})))
        connection.commit()
        updated = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        return _account_payload(updated, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_mascot(account_id: str, *, nickname: str, mascot_color: str, mascot_accessory: str,
                  db_path: str | Path | None = None) -> dict[str, Any]:
    nickname = str(nickname).strip()[:24]
    if mascot_color not in {"teal", "red", "blue", "cream"} or mascot_accessory not in {"cap", "beret", "crown", "dot", "leaf", "star", "none"}:
        raise ValueError("吉祥物外觀設定無效。")
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        connection.execute("UPDATE paper_accounts SET nickname=?,mascot_color=?,mascot_accessory=? WHERE id=?",
                           (nickname, mascot_color, mascot_accessory, account_id))
        connection.commit()
        updated = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        return _account_payload(updated, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_account_settings(account_id: str, *, lookback: int, initial_cash: float, commission_rate: float,
                            sell_tax_rate: float, slippage_bps: float, max_exposure_pct: float,
                            db_path: str | Path | None = None) -> dict[str, Any]:
    connection = _connect(db_path or DEFAULT_DB)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise KeyError("找不到紙上交易帳戶。")
        if row["first_sync"] or row["retired"] or row["paused"]:
            raise ValueError("帳戶首次同步後或退場後，策略與交易條件已凍結。")
        anchors = connection.execute("SELECT date,close FROM paper_history WHERE account_id=? ORDER BY date", (account_id,)).fetchall()
        anchor_dates = [item["date"] for item in anchors]
        anchor_closes = [float(item["close"]) for item in anchors]
        dates, closes, initial_cash, commission_rate, sell_tax_rate, slippage_bps, max_exposure_pct = _validate_inputs(
            anchor_dates, anchor_closes, lookback, initial_cash, commission_rate, sell_tax_rate, slippage_bps,
            max_exposure_pct,
        )
        artifact = json.loads(row["model_artifact"]) if row["model_artifact"] else None
        if artifact:
            feature_window = build_latest_feature_window(closes, artifact["features"], artifact["lookback"], artifact["returnType"])
            raw_prediction = predict_with_artifact(artifact, feature_window)
            predicted_return = math.expm1(raw_prediction) if artifact["returnType"] == "log" else raw_prediction
            pending_long = predicted_return > row["buy_threshold"]
            history_length = max(lookback, _neural_history_length(artifact))
        elif row["strategy"] == "momentum":
            pending_long = bool(time_series_momentum_signals(closes, lookback=lookback, dates=dates).signals[-1] == 1)
            history_length = lookback
        else:
            pending_long = False
            history_length = max(lookback, 60)
        pending_exposure = max_exposure_pct / 100 if pending_long else 0.0
        connection.execute("""UPDATE paper_accounts SET lookback=?,initial_cash=?,cash=?,commission_rate=?,sell_tax_rate=?,
          slippage_rate=?,max_exposure=?,pending_long=?,pending_exposure=?,history_hash=? WHERE id=?""",
          (lookback, initial_cash, initial_cash, commission_rate, sell_tax_rate, slippage_bps / 10000,
           max_exposure_pct / 100, int(pending_long), pending_exposure,
           _history_hash(dates, closes, len(dates) - 1, history_length), account_id))
        connection.execute("INSERT INTO paper_events(account_id,date,kind,payload) VALUES (?,?,?,?)",
                           (account_id, row["last_date"], "settings_updated", json.dumps({"note": "首次同步前已更新模擬條件。"})))
        connection.commit()
        updated = connection.execute("SELECT * FROM paper_accounts WHERE id=?", (account_id,)).fetchone()
        events = connection.execute("SELECT * FROM paper_events WHERE account_id=? ORDER BY seq", (account_id,)).fetchall()
        return _account_payload(updated, events)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
