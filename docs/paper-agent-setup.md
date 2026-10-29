# 訂閱代理紙上交易設定

本功能不向模型供應商送出 API key。Codex 或 Antigravity 以各自已登入的訂閱客戶端連到專案的本機 MCP 伺服器；MCP 只讀取本機帳戶與行情、更新 TWSE 日收盤資料，並提交受風控限制的紙上目標曝險。它不會連券商或建立真實委託。

## 安裝與啟動

在專案根目錄使用 Python 3.10 以上安裝依賴，並啟動本機網站。MCP 的行情更新工具透過本機網站既有的資料更新路由工作，因此排程時網站必須保持執行。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app
```

網站預設在 `http://127.0.0.1:8000`。可在環境變數 `PAPER_API_URL` 指定其他本機網址。

## 連接 Codex

專案已附上 `.codex/config.toml`，由專案根目錄啟動 Codex 時會連到本機 MCP 伺服器。Codex 使用自己的訂閱登入，不需要專案 API key。檢查工具是否載入：

```bash
codex mcp list
```

## 連接 Antigravity

專案已附上 `.agents/mcp_config.json` 本機設定。若專案位置不同，請把設定中的工作目錄與 Python 路徑改成目前位置：

```json
{
  "mcpServers": {
    "taiex-paper": {
      "command": "/ABSOLUTE/PATH/TO/taiex-neural-lab/.venv/bin/python",
      "args": ["-m", "app.paper_mcp", "--provider", "antigravity"],
      "cwd": "/ABSOLUTE/PATH/TO/taiex-neural-lab",
      "timeoutSeconds": 300
    }
  }
}
```

Antigravity 可使用工作區的 `.agents/mcp_config.json`。MCP 由 Antigravity 客戶端啟動，不透過第三方程式包裝 AGY 指令。

## 設定排程工作

在 Codex 與 Antigravity 各自的第一方客戶端建立本機排程。建議台灣時間週一至週五收盤後執行，兩個客戶端錯開至少 5 分鐘，避免同時更新行情。電腦、網站與客戶端需保持可執行狀態。

將以下任務說明貼入每個客戶端的排程：

> 使用 taiex-paper 工具執行一次紙上交易輪次。先呼叫 `refresh_agent_market_data`；若更新失敗或任一標的更新不完整，停止本輪且不要提交決策。接著呼叫 `list_agent_accounts`。逐帳戶呼叫 `advance_one_session`，再呼叫 `get_decision_context`。若 `decisionSubmitted` 為 true，略過該帳戶。只能根據回傳的收盤資料、報酬、波動、持倉、成本與曝險上限決策，不使用未提供的盤中或未來資料。選擇 0 至 `maxAllowedExposurePct` 之間的 `target_exposure_pct`；0 表示持有現金。呼叫 `submit_decision` 時使用回傳的 `asOf`，理由不超過 600 字。若資料、額度、工具或回覆格式有錯，停止該帳戶本輪，不重複提交、不猜測成交。不得聲稱已送出券商委託。

每輪最多推進一個交易日；若 TWSE 尚未公布新收盤價，帳戶不會跳過日期。需要清楚知道停用開關的效果：停用會拒絕未來的新代理決策，但已提交、等待下一收盤執行的目標仍會依紙上規則處理。

## MCP 工具

- `refresh_agent_market_data`：透過本機網站更新此代理帳戶所用標的的 TWSE 日線資料；任何標的更新失敗會讓本輪停止。
- `list_agent_accounts`：只列出指派給目前客戶端且已啟用自動決策的帳戶。
- `advance_one_session`：使用帳戶先前已留存的決策，最多模擬推進一個新收盤日。
- `get_decision_context`：提供帳戶最新已確認收盤日、近期收盤、報酬與波動資訊。
- `submit_decision`：接受 0 至帳戶曝險上限的目標曝險；同帳戶同日期不可覆寫決策。

若停用帳戶，待執行決策仍可能在下一個可用收盤日成交。若需讓帳戶退出，使用既有「停止策略並安排退場」功能；它會依原本規則在下一個新交易日收盤模擬平倉。
