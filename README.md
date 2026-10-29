# 序列觀測站：神經網路股價預測學習實驗室

以臺灣加權股價指數（TAIEX）和固定大型股教學樣本為例，操作並檢查 MLP、RNN、LSTM、GRU、TCN 如何從歷史收盤資料預測未來報酬率。重點是看懂序列資料、訓練、反向傳播和時間序列評估；預測結果不代表投資建議或獲利能力。

## 快速開始

需要 Python 3.10 以上。第一次安裝 PyTorch 會下載較大的套件；模型預設在本機 CPU 執行。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app
```

開啟 <http://127.0.0.1:8000>。Windows PowerShell 啟動虛擬環境的指令是 `.venv\Scripts\Activate.ps1`。

## 操作順序

1. 選擇 TAIEX 或熱門個股實驗池的標的；個股第一次使用前按「更新個股資料」。
2. 查看時間軸、資料來源和最後 20% 的鎖定測試區。
3. 選預測期、簡單或對數報酬率、回看長度及輸入特徵。
4. 設定偏多／偏空候選門檻，選網路並設定 epoch、batch size、層數、隱藏單元、dropout、learning rate、optimizer、loss 和 seed。
5. 執行 walk-forward 驗證，比較逐折 MAE／RMSE 與基準方法；結果區會依逐筆預測顯示「偏多候選／觀望／偏空或退出候選」。
6. 展開「誤差診斷與逐折表現」，查看驗證殘差直方圖、常態參考曲線和每折 running MAE。這些圖使用 walk-forward 驗證預測，不讀取鎖定測試集。
7. 設定定案後，選一種模型凍結參數，按一次「執行一次鎖定測試」。正式鎖定測試至少訓練 20 個 Epoch；已揭露的測試期間不能重跑或再拿來調參。
8. 在「學習中心 → 數學拆解」看 NumPy 如何算 MLP 梯度，並確認與相同權重的 PyTorch autograd 相符。

「實驗歷程」會在目前瀏覽器保留最近 20 筆一般驗證摘要，可套用舊設定或匯出 JSON 封存。封存包含資料雜湊、實驗設定與逐折指標，不含逐筆預測、原始資料或鎖定測試結果。

## 紙上交易台

從「紙上交易台」建立個股模擬帳戶，預設使用 20 日時間序列動能（收盤高於回看期前收盤則做多，否則持現金）。新帳戶從目前本機資料的最後日期開始；之後訊號在收盤後形成，只會於新交易日資料同步時，以該日收盤加減設定滑價模擬執行。下單以整數股數計算，可設定手續費、賣出稅、滑價與單一標的曝險上限。SQLite 狀態儲存在 `data/paper-trading.sqlite3`，僅屬本機紙上帳本。同步時必須保留帳戶最後處理日及完整的策略回看錨點；缺少任何已保存錨點時會停止同步，避免使用不完整歷史產生模擬交易。舊版建立、沒有可驗證錨點的帳戶也會要求建立新紙上帳戶。

這是前瞻紙上模擬，不會讀取鎖定測試集、不會把舊驗證模型當成即時訊號，也不會連券商或送出委託。研究工作台仍由使用者手動更新資料；啟用的代理排程可透過本機網站更新其帳戶標的的 TWSE 日收盤資料。目前資料只有日收盤，且未計漲跌停、盤中成交、股利及公司行動，所以結果不能證明策略有獲利能力或可直接實盤。要停止帳戶，系統會排定在下一個新交易日收盤模擬平倉，不能回溯改寫已記錄的成交。

紙上帳戶也可選擇訂閱代理策略，將帳戶指派給已登入的 Codex 或 Google Antigravity 客戶端。代理透過本機 MCP 取得收盤資料並提交目標曝險；模擬引擎驗證帳戶曝險上限、整股、成本與去重後，才記錄下一收盤模擬成交。模型憑證不放在本專案，也不需要模型 API key。自動排程由對應的第一方客戶端執行；設定方式見 [`docs/paper-agent-setup.md`](docs/paper-agent-setup.md)。

改動資料或實驗參數後，舊驗證結果會視為過期。資料更新只能在沒有訓練工作執行時進行。

## 本機資料與限制

`data/taiex_close.csv` 是本機 TWSE 歷史快照整理出的 TAIEX 每日收盤指數。熱門股清單包含台積電、鴻海、聯發科、台達電、富邦金、國泰金、聯電、廣達、日月光投控和長榮；首次更新時透過 TWSE `STOCK_DAY` 月資料取得 2022 年以來的日收盤資料，每檔獨立保存於 `data/stocks/`。清單是固定大型股學習池，不是即時成交量排行榜。個股資料不含 OHLC 或成交量，且目前使用收盤價而非含股利調整價；公司行動可能造成報酬序列跳動，因此個股訊號僅作研究練習，不做策略績效宣稱。

來源：[TWSE 指數歷史資料頁](https://www.twse.com.tw/en/indices/taiex/mi-5min-hist.html)、[TWSE OpenAPI](https://openapi.twse.com.tw/)。課程環境中的歷史快照位於 `ai Quant Trading` 的原始資料封存；專題資料夾內保留的是標準化後的收盤序列和來源資訊，不會改動原封存。

### 評估規則

- 預測時點是交易日 t 收盤後；以收盤資料建構的簡化執行假設為下一交易日收盤 C_{t+1}，目標為持有 h 個交易日後 C_{t+h+1} 的報酬 (C_{t+h+1}/C_{t+1}-1)，或其對數報酬版本。這不是開盤或盤中撮合模擬。
- 前 80% 日期用於 expanding walk-forward 訓練和驗證；最後 20% 日期留作鎖定測試。
- 樣本依目標日期歸屬切分。訓練標籤不得跨入下一驗證折／測試區；回看特徵只使用預測時點及之前的資料。
- 每折標準化只 fit 該折訓練輸入，避免驗證或測試資料影響尺度。
- MAE、RMSE 以報酬率百分點顯示；不用 MAPE，因報酬率會接近零。
- 殘差圖以逐筆 walk-forward 預測計算；直方圖的常態曲線只作視覺參考，±2σ 比例與超額峰度是描述統計，不是正式常態性檢定。
- 逐折曲線為驗證折內截至該筆預測的 running MAE。折與折分開呈現，觀察時段差異，不將它解讀為投資績效。
- 策略研究卡把 OOF 門檻訊號延後到下一收盤執行，並逐日以收盤估值；同窗列出全現金、固定 20 日均線、20 日時間序列動能與買入持有基準。手續費與交易稅為簡化假設，未含滑價、漲跌停成交限制、股利或公司行動，不代表可實際複製的績效。
- TCN 使用固定兩個因果殘差卷積區塊，不提供可調深度；目前僅納入一般 walk-forward 比較，未納入鎖定測試協定。因果性與形狀/梯度有合成單元測試，不能據此推論模型優於其他架構。
- 本機 CPU、小型日資料和有限模型搜尋只適合教學。時期、指數編製、結構變化和資料範圍都會影響結果。

## 專題文件

- [`docs/learning-guide.md`](docs/learning-guide.md)：模型、特徵和公式說明。
- [`docs/learning-map.md`](docs/learning-map.md)：操作與學習路線。
- [`docs/report.md`](docs/report.md)：報告架構和實驗紀錄欄位；應以你實際執行結果填寫。
- [`docs/90-second-demo.md`](docs/90-second-demo.md)：簡短展示順序。
- [`docs/ai-conversation-summary.md`](docs/ai-conversation-summary.md)：專題選擇和實作決策紀錄。

## 本機 API

- `GET /api/health`：服務狀態和 PyTorch 版本。
- `GET /api/data/status`、`GET /api/data/series`：資料範圍、摘要和畫圖序列。
- `POST /api/data/refresh`：手動取得 TWSE 最新月份指數資料。
- `GET /api/stocks`：熱門股清單及各標的本機資料狀態。
- `POST /api/stocks/refresh`：取得清單內個股 TWSE 日收盤資料；可傳入 `{"symbols":["2330.TW"]}` 限定更新標的。
- `POST /api/experiments`：啟動 walk-forward 訓練工作。
- `GET /api/jobs/active`：頁面重新載入後接回執行中的工作。
- `GET /api/jobs/{job_id}`、`POST /api/jobs/{job_id}/cancel`：查看或取消工作。
- `GET /api/validation/latest?symbol=2330.TW`：依標的和資料雜湊恢復最近一次驗證結果與設定。
- `POST /api/final-evaluation`：對一種凍結設定啟動唯一最終測試。
- `GET /api/learning/trace`：取得 NumPy／PyTorch MLP 教學計算。
- `GET /paper`：開啟紙上交易台。
- `GET /api/paper/accounts`、`POST /api/paper/accounts`：查看或建立本機紙上帳戶。
- `POST /api/paper/accounts/{id}/advance`、`POST /api/paper/accounts/{id}/pause`：同步新交易日或停止策略並排定平倉。
- `POST /api/paper/accounts/{id}/agent-automation`：啟用或停用代理的新決策。

FastAPI 文件：<http://127.0.0.1:8000/docs>。

## 本機與隱私

資料、模型和實驗都在本機運行。手動更新時只向 TWSE 發出讀取請求；沒有帳戶、金鑰或外部服務憑證。最終測試狀態按標的保存；資料更新不會重置已揭露測試集的使用狀態。
