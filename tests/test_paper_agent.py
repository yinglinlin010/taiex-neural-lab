from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import app.main as main_module
import app.data as data_module
from app.data import Series
from app.paper import (
    advance_account,
    create_account,
    get_agent_context,
    list_accounts,
    list_agent_accounts,
    set_agent_automation,
    submit_agent_decision,
)
from app.main import app
from app.paper_mcp import PaperAgentTools


def make_history(size: int = 100):
    dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(size)]
    closes = [100.0 + index for index in range(size)]
    return dates, closes


def create_agent(db_path: Path, provider: str = "codex", **kwargs):
    dates, closes = make_history()
    symbol = kwargs.pop("symbol", "TEST")
    return create_account(symbol, dates, closes, lookback=20, db_path=db_path,
                          strategy="agent", agent_provider=provider,
                          agent_auto_enabled=True, **kwargs)


def test_agent_account_requires_supported_provider_and_starts_flat(tmp_path):
    dates, closes = make_history()
    with pytest.raises(ValueError, match="指定 Codex 或 Antigravity"):
        create_account("TEST", dates, closes, strategy="agent", db_path=tmp_path / "bad.sqlite3")
    account = create_agent(tmp_path / "paper.sqlite3")
    assert account["strategy"] == "agent"
    assert account["agentProvider"] == "codex"
    assert account["agentAutoEnabled"] is True
    assert account["pendingExposurePct"] == 0
    assert account["shares"] == 0


def test_agent_context_is_provider_scoped_and_uses_only_saved_closes(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path, "antigravity")
    context = get_agent_context(account["id"], "antigravity", path)
    assert context["asOf"] == account["lastDate"]
    assert context["decisionSubmitted"] is False
    assert context["market"]["recentCloses"][-1] == {"date": account["lastDate"], "close": account["lastClose"]}
    assert context["market"]["return1d"] == pytest.approx(account["lastClose"] / context["market"]["recentCloses"][-2]["close"] - 1)
    with pytest.raises(ValueError, match="未指派"):
        get_agent_context(account["id"], "codex", path)


@pytest.mark.parametrize("value", [-0.01, 20.01, float("nan"), float("inf"), True, "bad"])
def test_agent_decision_rejects_invalid_exposure_without_mutation(tmp_path, value):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    with pytest.raises(ValueError, match="曝險"):
        submit_agent_decision(account["id"], "codex", account["lastDate"], value, "測試理由", path)
    current = list_accounts(path)[0]
    assert current["pendingExposurePct"] == 0
    assert not any(event["kind"] == "agent_decision" for event in current["events"])


@pytest.mark.parametrize("rationale", ["", "x" * 601])
def test_agent_decision_rejects_empty_or_oversized_rationale(tmp_path, rationale):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    with pytest.raises(ValueError, match="決策理由"):
        submit_agent_decision(account["id"], "codex", account["lastDate"], 0, rationale, path)
    assert list_accounts(path)[0]["pendingExposurePct"] == 0


def test_agent_decisions_are_idempotent_and_cannot_be_rewritten(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    first = submit_agent_decision(account["id"], "codex", account["lastDate"], 12.5, "趨勢延續，採中低曝險。", path)
    retry = submit_agent_decision(account["id"], "codex", account["lastDate"], 12.5, "趨勢延續，採中低曝險。", path)
    assert first["accepted"] and not first["duplicate"]
    assert retry["accepted"] and retry["duplicate"]
    with pytest.raises(ValueError, match="未指派"):
        submit_agent_decision(account["id"], "antigravity", account["lastDate"], 5, "wrong provider", path)
    with pytest.raises(ValueError, match="不同決策"):
        submit_agent_decision(account["id"], "codex", account["lastDate"], 8, "改寫", path)
    current = list_accounts(path)[0]
    assert current["pendingExposurePct"] == 12.5
    assert sum(event["kind"] == "agent_decision" for event in current["events"]) == 1


def test_racing_agent_submissions_create_one_audited_decision(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)

    def submit():
        return submit_agent_decision(account["id"], "codex", account["lastDate"], 20,
                                     "最大允許曝險邊界測試。", path)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _index: submit(), range(6)))
    assert sum(not result["duplicate"] for result in results) == 1
    assert sum(result["duplicate"] for result in results) == 5
    assert list_accounts(path)[0]["pendingExposurePct"] == 20


def test_agent_decision_applies_at_next_close_and_advance_processes_one_session(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    dates, closes = make_history(103)
    submit_agent_decision(account["id"], "codex", account["lastDate"], 10, "先以低曝險觀察趨勢。", path)
    updated = advance_account(account["id"], dates, closes, db_path=path)
    assert updated["advancedSessions"] == 1
    assert updated["lastDate"] == dates[-3]
    assert updated["shares"] > 0
    buy = next(event for event in updated["events"] if event["kind"] == "buy")
    assert buy["date"] == dates[-3]
    assert buy["targetExposurePct"] == 10
    assert updated["shares"] * updated["lastClose"] / updated["equity"] <= 0.11


def test_agent_without_decision_holds_cash_and_does_not_backfill_all_dates(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    dates, closes = make_history(103)
    updated = advance_account(account["id"], dates, closes, db_path=path)
    assert updated["advancedSessions"] == 1
    assert updated["lastDate"] == dates[-3]
    assert updated["shares"] == 0
    assert not any(event["kind"] == "buy" for event in updated["events"])


def test_agent_cash_decision_sells_next_session_with_costs(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    dates, closes = make_history(102)
    submit_agent_decision(account["id"], "codex", account["lastDate"], 15, "趨勢條件成立。", path)
    held = advance_account(account["id"], dates, closes, db_path=path)
    assert held["shares"] > 0
    submit_agent_decision(held["id"], "codex", held["lastDate"], 0, "波動升高，退回現金。", path)
    dates, closes = make_history(103)
    flat = advance_account(account["id"], dates, closes, db_path=path)
    sells = [event for event in flat["events"] if event["kind"] == "sell"]
    assert flat["shares"] == 0
    assert sells[-1]["targetExposurePct"] == 0
    assert sells[-1]["commission"] > 0
    assert sells[-1]["sellTax"] > 0


def test_agent_toggle_blocks_new_decisions_and_migrates_old_schema(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    disabled = set_agent_automation(account["id"], False, path)
    assert disabled["agentAutoEnabled"] is False
    assert list_agent_accounts("codex", path) == []
    with pytest.raises(ValueError, match="未啟用"):
        submit_agent_decision(account["id"], "codex", account["lastDate"], 5, "停用狀態", path)

    legacy = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(legacy)
    connection.execute("CREATE TABLE paper_accounts (id TEXT PRIMARY KEY, symbol TEXT NOT NULL, initial_cash REAL NOT NULL, cash REAL NOT NULL, shares INTEGER NOT NULL DEFAULT 0, lookback INTEGER NOT NULL, max_exposure REAL NOT NULL, commission_rate REAL NOT NULL, sell_tax_rate REAL NOT NULL, slippage_rate REAL NOT NULL, last_date TEXT NOT NULL, last_close REAL NOT NULL, history_hash TEXT NOT NULL, pending_long INTEGER NOT NULL, paused INTEGER NOT NULL DEFAULT 0, nickname TEXT NOT NULL DEFAULT '', mascot_color TEXT NOT NULL DEFAULT 'teal', mascot_accessory TEXT NOT NULL DEFAULT 'dot', retired INTEGER NOT NULL DEFAULT 0, first_sync INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    connection.execute("INSERT INTO paper_accounts(id,symbol,initial_cash,cash,shares,lookback,max_exposure,commission_rate,sell_tax_rate,slippage_rate,last_date,last_close,history_hash,pending_long) VALUES ('old','TEST',1000,1000,0,20,0.2,0,0,0,'2026-01-01',100,'hash',1)")
    connection.commit()
    connection.close()
    migrated = list_accounts(legacy)[0]
    assert migrated["strategy"] == "momentum"
    assert migrated["agentProvider"] is None
    assert migrated["pendingExposurePct"] == 20


def test_agent_creation_api_persists_provider_and_auto_setting(tmp_path, monkeypatch):
    dates, closes = make_history()
    series = Series(dates, __import__("numpy").array(closes), {"fields": ["date", "close"]}, "synthetic")
    monkeypatch.setattr(main_module, "load_series", lambda _symbol: series)
    monkeypatch.setattr(main_module, "is_tradable_equity", lambda symbol: symbol == "TEST")
    monkeypatch.setattr(main_module.paper_trading, "DEFAULT_DB", tmp_path / "api-paper.sqlite3")
    client = TestClient(app)
    response = client.post("/api/paper/accounts", json={
        "symbol": "TEST", "strategy": "agent", "agentProvider": "codex", "agentAutoEnabled": True,
        "initialCash": 100000, "maxExposurePct": 20,
    })
    assert response.status_code == 200
    account = response.json()["account"]
    assert account["agentProvider"] == "codex" and account["agentAutoEnabled"] is True
    toggled = client.post(f"/api/paper/accounts/{account['id']}/agent-automation", json={"enabled": False})
    assert toggled.status_code == 200
    assert toggled.json()["account"]["agentAutoEnabled"] is False


def test_mcp_tool_advances_once_using_fixture_market_data(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    dates, closes = make_history(103)
    submit_agent_decision(account["id"], "codex", account["lastDate"], 10, "依現有收盤訊號採保守曝險。", path)
    tools = PaperAgentTools("codex", path, lambda _symbol: Series(dates, __import__("numpy").array(closes), {}, "fixture"))
    result = tools.advance_one_session(account["id"])
    assert result["advancedSessions"] == 1
    assert result["lastDate"] == dates[-3]
    assert result["decisionSubmitted"] is False
    assert list_accounts(path)[0]["shares"] > 0


def test_agent_market_refresh_fails_closed_on_partial_or_unavailable_update(tmp_path, monkeypatch):
    path = tmp_path / "paper.sqlite3"
    create_agent(path, symbol="2330.TW")
    tools = PaperAgentTools("codex", path)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"updated": [], "errors": [{"symbol": "2330.TW", "message": "timeout"}]}).encode()

    monkeypatch.setattr("app.paper_mcp.urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError, match="不得提交決策"):
        tools.refresh_market_data("http://localhost:8000")

    monkeypatch.setattr("app.paper_mcp.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")))
    with pytest.raises(RuntimeError, match="更新行情失敗"):
        tools.refresh_market_data("http://localhost:8000")


def test_stock_refresh_rejects_unknown_or_empty_symbol_sets_before_io(tmp_path, monkeypatch):
    target = tmp_path / "stocks"
    monkeypatch.setattr(data_module, "STOCK_DATA_DIR", target)
    with pytest.raises(ValueError, match="更新標的"):
        data_module.refresh_stock_data(["UNKNOWN"])
    with pytest.raises(ValueError, match="更新標的"):
        data_module.refresh_stock_data([])
    assert not target.exists()


def test_stock_refresh_endpoint_accepts_ui_empty_object_and_optional_symbol_list(monkeypatch):
    calls = []

    def fake_refresh(symbols=None):
        calls.append(symbols)
        return {"updated": [], "count": 0, "errors": []}

    monkeypatch.setattr(main_module, "refresh_stock_data", fake_refresh)
    client = TestClient(app)

    all_stocks = client.post("/api/stocks/refresh", json={})
    one_stock = client.post("/api/stocks/refresh", json={"symbols": ["2330.TW"]})
    empty_symbols = client.post("/api/stocks/refresh", json={"symbols": []})

    assert all_stocks.status_code == 200
    assert one_stock.status_code == 200
    assert empty_symbols.status_code == 422
    assert calls == [None, ["2330.TW"]]


def test_mcp_stdio_exposes_scoped_tools_and_account_list(tmp_path):
    path = tmp_path / "paper.sqlite3"
    account = create_agent(path)
    env = {**os.environ, "PAPER_TRADING_DB": str(path)}
    params = StdioServerParameters(
        command=str(Path(sys.executable)),
        args=["-m", "app.paper_mcp", "--provider", "codex"],
        env=env,
        cwd=str(Path(__file__).resolve().parents[1]),
    )

    async def run_client():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed_tools = await session.list_tools()
                names = {tool.name for tool in listed_tools.tools}
                assert names == {"list_agent_accounts", "refresh_agent_market_data", "advance_one_session",
                                 "get_decision_context", "submit_decision"}
                result = await session.call_tool("list_agent_accounts", {})
                payload = result.structuredContent["result"]
                assert payload[0]["id"] == account["id"]
                context_result = await session.call_tool("get_decision_context", {"account_id": account["id"]})
                context = context_result.structuredContent.get("result", context_result.structuredContent)
                assert context["asOf"] == account["lastDate"]
                rejected = await session.call_tool("submit_decision", {
                    "account_id": account["id"], "as_of": account["lastDate"],
                    "target_exposure_pct": 100, "rationale": "must fail closed",
                })
                assert rejected.isError is True
                submitted = await session.call_tool("submit_decision", {
                    "account_id": account["id"], "as_of": account["lastDate"],
                    "target_exposure_pct": 15, "rationale": "採用有限曝險觀察日線趨勢。",
                })
                assert submitted.isError is False
                submitted_payload = submitted.structuredContent.get("result", submitted.structuredContent)
                assert submitted_payload["accepted"] is True

    asyncio.run(run_client())
    assert list_accounts(path)[0]["pendingExposurePct"] == 15
