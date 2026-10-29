"""MCP tools for Codex and Antigravity subscription clients.

The local client owns model authentication. This process exposes only paper
account context and validated simulated decisions over stdio.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

from . import paper
from .data import Series, load_series


class PaperAgentTools:
    def __init__(self, provider: str, db_path: str | Path | None = None,
                 series_loader: Callable[[str], Series] = load_series):
        if provider not in {"codex", "antigravity"}:
            raise ValueError("provider 必須是 codex 或 antigravity。")
        self.provider = provider
        self.db_path = db_path
        self.series_loader = series_loader

    def refresh_market_data(self, api_url: str | None = None) -> dict[str, Any]:
        accounts = paper.list_agent_accounts(self.provider, self.db_path)
        symbols = sorted({account["symbol"] for account in accounts})
        if not symbols:
            return {"updated": [], "message": "目前沒有啟用中的代理帳戶，不需更新行情。"}
        base_url = (api_url or os.environ.get("PAPER_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        request = Request(
            f"{base_url}/api/stocks/refresh",
            data=json.dumps({"symbols": symbols}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"更新行情失敗；本次不得提交交易決策：{exc}") from exc
        failed_symbols = {item.get("symbol") for item in payload.get("errors", [])}
        updated_symbols = {item.get("symbol") for item in payload.get("updated", [])}
        if failed_symbols.intersection(symbols) or not set(symbols).issubset(updated_symbols):
            raise RuntimeError(f"部分帳戶標的行情未成功更新；本次不得提交決策。回應：{payload}")
        return payload

    def list_accounts(self) -> list[dict[str, Any]]:
        return [{key: account[key] for key in ("id", "symbol", "nickname", "lastDate", "lastClose",
                                                "shares", "pendingAction", "pendingExposurePct")}
                for account in paper.list_agent_accounts(self.provider, self.db_path)]

    def advance_one_session(self, account_id: str) -> dict[str, Any]:
        context = paper.get_agent_context(account_id, self.provider, self.db_path)
        if not context["account"]["id"]:
            raise ValueError("帳戶識別碼無效。")
        accounts = {item["id"]: item for item in paper.list_agent_accounts(self.provider, self.db_path)}
        if account_id not in accounts:
            raise ValueError("帳戶未啟用此代理的自動決策，或已停止。")
        series = self.series_loader(accounts[account_id]["symbol"])
        updated = paper.advance_account(account_id, series.dates, series.closes.tolist(),
                                        db_path=self.db_path, max_sessions=1)
        return {
            "advancedSessions": updated["advancedSessions"],
            "lastDate": updated["lastDate"],
            "dataThrough": series.dates[-1],
            "decisionSubmitted": any(event["kind"] == "agent_decision" and event["date"] == updated["lastDate"]
                                      for event in updated["events"]),
        }

    def get_decision_context(self, account_id: str) -> dict[str, Any]:
        context = paper.get_agent_context(account_id, self.provider, self.db_path)
        if not context["account"]["id"]:
            raise ValueError("帳戶識別碼無效。")
        if account_id not in {item["id"] for item in paper.list_agent_accounts(self.provider, self.db_path)}:
            raise ValueError("帳戶未啟用此代理的自動決策，或已停止。")
        return context

    def submit_decision(self, account_id: str, as_of: str, target_exposure_pct: float,
                        rationale: str) -> dict[str, Any]:
        return paper.submit_agent_decision(account_id, self.provider, as_of, target_exposure_pct,
                                           rationale, self.db_path)


def create_mcp_server(provider: str, db_path: str | Path | None = None,
                      series_loader: Callable[[str], Series] = load_series) -> FastMCP:
    tools = PaperAgentTools(provider, db_path, series_loader)
    server = FastMCP(
        name=f"taiex-paper-{provider}",
        instructions=("只可操作已指派給本代理且已啟用自動決策的本機紙上帳戶。先呼叫 "
                     "list_agent_accounts，再對每個帳戶呼叫 advance_one_session、get_decision_context，"
                     "最後以 target_exposure_pct 與簡短繁體中文理由提交一次決策。不得聲稱送出券商委託。"),
    )

    @server.tool()
    def list_agent_accounts() -> list[dict[str, Any]]:
        """List active paper accounts assigned to this provider and enabled for automatic decisions."""
        return tools.list_accounts()

    @server.tool()
    def refresh_agent_market_data() -> dict[str, Any]:
        """Refresh TWSE daily closes for this provider's enabled paper accounts; requires the local app on port 8000."""
        return tools.refresh_market_data()

    @server.tool()
    def advance_one_session(account_id: str) -> dict[str, Any]:
        """Advance one available close session using only the previously recorded decision."""
        return tools.advance_one_session(account_id)

    @server.tool()
    def get_decision_context(account_id: str) -> dict[str, Any]:
        """Read the account state and price history through its latest confirmed close."""
        return tools.get_decision_context(account_id)

    @server.tool()
    def submit_decision(account_id: str, as_of: str, target_exposure_pct: float,
                        rationale: str) -> dict[str, Any]:
        """Submit a long-only target exposure for the next available close; zero means cash."""
        return tools.submit_decision(account_id, as_of, target_exposure_pct, rationale)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local MCP server for paper trading agents")
    parser.add_argument("--provider", choices=("codex", "antigravity"), required=True)
    args = parser.parse_args()
    db_path = os.environ.get("PAPER_TRADING_DB")
    create_mcp_server(args.provider, db_path).run(transport="stdio")


if __name__ == "__main__":
    main()
