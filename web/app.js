const byId = (id) => document.getElementById(id);
const MODEL_LABELS = { mlp: 'MLP', rnn: 'RNN', lstm: 'LSTM', gru: 'GRU', tcn: 'TCN' };
const MODEL_COLORS = { mlp: '#18a6a0', rnn: '#ee9f42', lstm: '#4c9cc5', gru: '#8c78b6', tcn: '#d2698b' };
const FEATURE_LABELS = {
  return_1: '單日報酬率', return_5: '5 日累積報酬', return_20: '20 日累積報酬',
  volatility_5: '波動度（5 日）', volatility_20: '波動度（20 日）',
};
const CONFIG_STORAGE_KEY = 'sequence-lab-config-v1';
const RUN_HISTORY_KEY = 'sequence-lab-run-history-v1';
const MAX_RUN_HISTORY = 20;
let crossAssetRenderRequest = 0;
const CONFIG_FIELDS = ['symbolSelect','buyThreshold','sellThreshold','modelType','horizon','returnType','lookback','epochs','batchSize','seed','learningRate','dropout','loss','optimizer','hiddenLayers','hiddenSize1','hiddenSize2','hiddenSize3','hiddenSize4'];
const state = { status: null, series: [], fullSeries: [], stocks: [], stockUniverseNote: '', comparisonRows: [], activeJobId: null, submitting: false, pollTimer: null, validation: null, validationConfig: null, forwardTrace: null, finalState: { status: 'available' }, finalUsed: false };
const networkMotion = { step: -1, timer: null, trainingTimer: null, playing: false, observer: null, speed: 1, neuron: 0, selectedNode: null, training: false, trainingEpoch: 0, trainingEpochs: 0 };

function movingAverageSignals(series, window = 20) {
  const signals = new Map();
  for (let i = window - 1; i < series.length; i++) {
    const average = series.slice(i - window + 1, i + 1).reduce((sum, point) => sum + Number(point.close), 0) / window;
    signals.set(i, Number(series[i].close) > average);
  }
  return signals;
}
function evaluateStrategyEvidence(modelEquity, benchmarks, completedTrades) {
  if (!Number.isFinite(modelEquity) || !Array.isArray(benchmarks) || benchmarks.length === 0
      || benchmarks.some((benchmark) => !benchmark || !Number.isFinite(benchmark.equity))) {
    return { complete: false, underperforming: [], enoughTrades: false };
  }
  return {
    complete: true,
    underperforming: benchmarks.filter((benchmark) => modelEquity <= benchmark.equity).map((benchmark) => benchmark.name),
    enoughTrades: Number.isInteger(completedTrades) && completedTrades >= 30,
  };
}
function timeSeriesMomentumSignals(series, lookback = 20) {
  const signals = new Map();
  for (let i = lookback; i < series.length; i++) {
    const current = Number(series[i].close), past = Number(series[i - lookback].close);
    if (!Number.isFinite(current) || !Number.isFinite(past) || current <= 0 || past <= 0) continue;
    signals.set(i, current > past);
  }
  return signals;
}
function firstLastIntervalDates(intervals) {
  if (!intervals.length) return { start: null, end: null };
  return { start: intervals[0].entryIndex, end: intervals.at(-1).targetIndex };
}
function replayFixedSignals(series, signals, start, end, fee, sellCost) {
  let equity = 1, invested = false, trades = 0;
  if (start == null || end == null || end <= start) return { equity, trades };
  for (let i = start; i <= end; i++) {
    const wantsLong = signals.get(i - 1);
    const entered = wantsLong === true && !invested;
    const exited = wantsLong === false && invested;
    if (i > start && (invested || exited) && !entered) equity *= Number(series[i].close) / Number(series[i - 1].close);
    if (entered) { equity *= 1 - fee; invested = true; trades++; }
    else if (exited) { equity *= 1 - sellCost; invested = false; trades++; }
  }
  if (invested) equity *= 1 - sellCost;
  return { equity, trades };
}
function replayOofSignals(series, intervals, start, end, fee, sellCost) {
  let equity = 1, invested = false, entryIndex = null, completed = 0, holdingDays = 0, wins = 0, tradeStartEquity = 1;
  const curve = [1], tradeReturns = [];
  if (start == null || end == null || end <= start) return { equity, curve, tradeReturns, completed, holdingDays, wins };
  const byOrigin = new Map(intervals.map(row => [row.originIndex, row]));
  for (let i = start; i <= end; i++) {
    const prediction = byOrigin.get(i - 1);
    let exited = false, entered = false;
    if (prediction?.signal === 'sell_candidate' && invested) {
      holdingDays += i - entryIndex; completed++; exited = true;
      invested = false; entryIndex = null;
    } else if (prediction?.signal === 'buy_candidate' && !invested) {
      tradeStartEquity = equity; equity *= 1 - fee; invested = true; entryIndex = i; entered = true;
    }
    if (i > start && (invested || exited) && !entered) equity *= Number(series[i].close) / Number(series[i - 1].close);
    if (exited) {
      equity *= 1 - sellCost;
      const tradeReturn = equity / tradeStartEquity - 1;
      tradeReturns.push(tradeReturn); if (tradeReturn > 0) wins++;
    }
    curve.push(equity);
  }
  if (invested) {
    equity *= 1 - sellCost; holdingDays += end - entryIndex; completed++;
    const tradeReturn = equity / tradeStartEquity - 1; tradeReturns.push(tradeReturn); if (tradeReturn > 0) wins++;
    curve.push(equity);
  }
  return { equity, curve, tradeReturns, completed, holdingDays, wins };
}
function replayWindow(intervals, byDate, validationStart, validationEnd, seriesLength) {
  const startBound = byDate.get(validationStart || '') ?? 0;
  const endBound = byDate.get(validationEnd || '') ?? (seriesLength - 1);
  return intervals.filter(row => row.targetIndex >= startBound && row.targetIndex <= endBound);
}
function isValidRunHistoryRecord(run) {
  return !!run && typeof run === 'object' && !Array.isArray(run)
    && typeof run.id === 'string' && run.id.length > 0
    && typeof run.createdAt === 'string' && Number.isFinite(Date.parse(run.createdAt))
    && !!run.config && typeof run.config === 'object' && !Array.isArray(run.config)
    && Array.isArray(run.models) && run.models.some((model) => model && typeof model === 'object'
      && !Array.isArray(model) && typeof model.key === 'string' && model.key.length > 0);
}
function buildRunHistoryArchive(rows, exportedAt = new Date().toISOString()) {
  const finiteOrNull = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
  const copyConfig = (config) => {
    const copied = {};
    for (const key of ['symbol','returnType','optimizer','loss','modelType']) {
      if (typeof config[key] === 'string') copied[key] = config[key];
    }
    for (const key of ['buyThreshold','sellThreshold','lookback','horizon','epochs','batchSize','hiddenUnits','hiddenLayers','dropout','learningRate','seed']) {
      if (Object.hasOwn(config, key)) copied[key] = finiteOrNull(config[key]);
    }
    for (const key of ['modelTypes','features','compareModels']) {
      if (Array.isArray(config[key])) copied[key] = config[key].filter((value) => typeof value === 'string');
    }
    if (Array.isArray(config.hiddenSizes)) copied.hiddenSizes = config.hiddenSizes.map(finiteOrNull).filter((value) => value !== null);
    return copied;
  };
  const validRuns = Array.isArray(rows) ? rows.filter(isValidRunHistoryRecord) : [];
  return {
    schemaVersion: 1,
    exportedAt,
    source: '序列觀測站 · 本機瀏覽器實驗歷程',
    note: '封存內容為瀏覽器保存的驗證摘要與設定，不含逐筆預測、原始資料或鎖定測試結果。',
    runCount: Math.min(validRuns.length, MAX_RUN_HISTORY),
    runs: validRuns.slice(0, MAX_RUN_HISTORY).map((run) => ({
      id: typeof run.id === 'string' ? run.id : null,
      createdAt: typeof run.createdAt === 'string' ? run.createdAt : null,
      datasetHash: typeof run.datasetHash === 'string' ? run.datasetHash : null,
      samples: finiteOrNull(run.samples),
      config: copyConfig(run.config),
      models: run.models.filter((model) => model && typeof model === 'object' && !Array.isArray(model)).map((model) => ({
        key: typeof model.key === 'string' ? model.key : null,
        name: typeof model.name === 'string' ? model.name : null,
        mae: finiteOrNull(model.mae),
        rmse: finiteOrNull(model.rmse),
        r2: finiteOrNull(model.r2),
        spearman: finiteOrNull(model.spearman),
        directionAccuracy: finiteOrNull(model.directionAccuracy),
        folds: Array.isArray(model.folds) ? model.folds.filter((fold) => fold && typeof fold === 'object' && !Array.isArray(fold)).map((fold) => ({
          fold: finiteOrNull(fold.fold),
          from: typeof fold.from === 'string' ? fold.from : null,
          to: typeof fold.to === 'string' ? fold.to : null,
          mae: finiteOrNull(fold.mae),
          rmse: finiteOrNull(fold.rmse),
        })) : [],
      })),
    })),
  };
}
function exportRunHistory() {
  const archive = buildRunHistoryArchive(readRunHistory());
  if (!archive.runCount) { toast('目前沒有可匯出的實驗歷程。'); return; }
  let url = null;
  try {
    const blob = new Blob([`${JSON.stringify(archive, null, 2)}\n`], { type: 'application/json;charset=utf-8' });
    url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sequence-lab-run-history-${localDateStamp()}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 5000);
    toast(`已準備 ${archive.runCount} 筆實驗摘要下載；若未出現檔案，請檢查瀏覽器下載狀態。`);
  } catch (_) {
    if (url) URL.revokeObjectURL(url);
    toast('瀏覽器無法準備實驗歷程下載，請重試或檢查下載設定。');
  }
}
function localDateStamp(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = payload.detail;
    if (Array.isArray(message)) message = message.map((item) => item?.msg || JSON.stringify(item)).join('； ');
    else if (message && typeof message === 'object') message = JSON.stringify(message);
    const error = new Error(message || `服務回應 ${response.status}`); error.status = response.status; throw error;
  }
  return payload;
}
function toast(message) { const n = byId('toast'); n.textContent = message; n.classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => n.classList.remove('show'), 3200); }
function err(message = '') { const n = byId('jobError'); n.textContent = message; n.hidden = !message; }
function formatInt(value) { return Number(value).toLocaleString('en-US'); }
function pct(value, digits = 2) { return `${(Number(value) * 100).toFixed(digits)}%`; }
function directionMixSummary(rows) {
  const numericValue = (value) => value === null || value === undefined || value === '' ? NaN : Number(value);
  const paired = rows.map((row) => ({ actual: numericValue(row.actual), predicted: numericValue(row.predicted) }))
    .filter((row) => Number.isFinite(row.actual) && Number.isFinite(row.predicted));
  const actual = paired.map((row) => row.actual);
  const predicted = paired.map((row) => row.predicted);
  const counts = (values) => ({ up: values.filter((value) => value > 0).length, down: values.filter((value) => value < 0).length, flat: values.filter((value) => value === 0).length });
  const format = (label, values, tally, zeroLabel) => `${label}上漲 ${tally.up}（${(tally.up/values.length*100).toFixed(1)}%）、下跌 ${tally.down}（${(tally.down/values.length*100).toFixed(1)}%）、${zeroLabel} ${tally.flat}（${(tally.flat/values.length*100).toFixed(1)}%）`;
  if (!paired.length) return '';
  const actualCounts = counts(actual), predictedCounts = counts(predicted);
  const majority = Math.max(actualCounts.up, actualCounts.down, actualCounts.flat) / actual.length;
  const meanMagnitude = (values) => values.length ? (values.reduce((sum, value) => sum + Math.abs(value), 0) / values.length * 100).toFixed(3) : '無樣本';
  const predictedUpMagnitude = meanMagnitude(predicted.filter((value) => value > 0));
  const predictedDownMagnitude = meanMagnitude(predicted.filter((value) => value < 0));
  const actualUpMagnitude = meanMagnitude(actual.filter((value) => value > 0));
  const actualDownMagnitude = meanMagnitude(actual.filter((value) => value < 0));
  const directionErrors = (sign) => paired.filter((row) => sign(row.actual)).map((row) => Math.abs(row.predicted - row.actual) * 100);
  const upErrors = directionErrors((value) => value > 0), downErrors = directionErrors((value) => value < 0);
  const meanError = (values) => values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(3) : '無樣本';
  const directionMismatches = paired.filter((row) => (row.actual > 0 && row.predicted < 0) || (row.actual < 0 && row.predicted > 0)).length;
  return `驗證資料方向分布：${format('實際', actual, actualCounts, '持平')}；${format('預測', predicted, predictedCounts, '中性')}。平均絕對幅度（各自方向內）：上漲實際 ${actualUpMagnitude}／預測 ${predictedUpMagnitude} 個百分點；下跌實際 ${actualDownMagnitude}／預測 ${predictedDownMagnitude} 個百分點。依實際方向分組的幅度 MAE（方向錯置仍計入）：上漲 n=${upErrors.length}、${meanError(upErrors)} 個百分點；下跌 n=${downErrors.length}、${meanError(downErrors)} 個百分點；上漲／下跌方向錯置 ${directionMismatches} 筆。${majority >= 0.7 ? `實際資料有 ${(majority*100).toFixed(1)}% 集中於單一方向，單看方向分數容易受比例影響。` : ''}零預測列為中性；分布與幅度只供解讀驗證輸出，不代表預測能力。`;
}
function savedValidationSummary(record, label) {
  const model = record?.result?.models?.[0];
  if (!model) return { label, available: false, message: '沒有已保存的一般驗證結果。完成一般 walk-forward 驗證後，這裡會顯示只讀摘要。' };
  const folds = model.folds || [], dated = folds.filter((fold) => fold.from && fold.to);
  const period = dated.length ? `${dated[0].from} 至 ${dated[dated.length - 1].to}` : '驗證期間不可用';
  const validMae = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) && Number(value) >= 0;
  const modelMae = validMae(model.mae) ? Number(model.mae) : NaN;
  const mae = Number.isFinite(modelMae) ? `${(modelMae * 100).toFixed(3)}%` : '不可用';
  const rows = folds.flatMap((fold) => fold.predictions || []);
  const direction = directionMixSummary(rows);
  const baseline = (record.result.comparisons || []).find((item) => ['naive','historical_mean'].includes(item.key));
  const baselineMae = validMae(baseline?.mae) ? Number(baseline.mae) : NaN;
  const hasBaseline = baseline && Number.isFinite(baselineMae) && Number.isFinite(modelMae);
  const delta = hasBaseline ? (modelMae - baselineMae) * 100 : NaN;
  const deltaDirection = delta > 0 ? '本次驗證誤差較大' : delta < 0 ? '本次驗證誤差較小' : '本次驗證相同';
  const deltaLabel = hasBaseline
    ? delta === 0 ? `0.000 個百分點 · ${deltaDirection}`
      : Math.abs(delta) < 0.0005 ? `${delta < 0 ? '−' : '+'}<0.001 個百分點 · ${deltaDirection}`
        : `${delta > 0 ? '+' : ''}${delta.toFixed(3)} 個百分點 · ${deltaDirection}`
    : '不可用 · 缺少有效模型或基準 MAE';
  const validValue = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const samples = rows.filter((row) => validValue(row.actual) && validValue(row.predicted)).length;
  const config = record.config || {};
  const horizon = record.result.horizon ?? config.horizon ?? null;
  const returnType = record.result.returnType ?? config.returnType ?? null;
  const setupKeys = ['features','lookback','epochs','batchSize','hiddenUnits','hiddenLayers','hiddenSizes','dropout','learningRate','optimizer','loss','seed'];
  const setup = Object.fromEntries(setupKeys.filter((key) => config[key] !== undefined).map((key) => [key, config[key]]));
  return {
    label, available: true, model: MODEL_LABELS[model.key] || model.key || '模型',
    mae, baseline: hasBaseline ? `${baseline.name || baseline.key} · ${(baselineMae * 100).toFixed(3)}%` : '未保存有效簡單基準',
    delta: deltaLabel, period, folds: folds.length, samples,
    execution: record.result.execution || null, horizon, returnType, setupSignature: JSON.stringify(setup),
    setup: [horizon ? `${horizon} 日目標` : null, config.lookback ? `回看 ${config.lookback} 日` : null, returnType === 'log' ? '對數報酬' : returnType === 'simple' ? '簡單報酬' : null].filter(Boolean).join(' · ') || '設定資訊未保存',
    direction: direction || '沒有完整逐筆 OOF 配對，無法摘要方向分布',
  };
}
function savedComparisonCompatibility(records) {
  if (records.length !== 2 || records.some((record) => !record.available)) return '不可直接排名：目前缺少兩份可用的一般驗證摘要，無法判定跨標的比較條件；請先完成兩個標的一般 walk-forward 驗證。';
  const [a, b] = records, issues = [];
  if (a.execution !== 'next_close' || b.execution !== 'next_close') issues.push('至少一份紀錄未保存 next-close 目標協定');
  if (a.horizon == null || b.horizon == null || a.horizon !== b.horizon) issues.push('預測期間不同或未保存');
  if (!a.returnType || !b.returnType || a.returnType !== b.returnType) issues.push('報酬定義不同或未保存');
  if (!a.period || a.period === '驗證期間不可用' || a.period !== b.period) issues.push('驗證日期區間不同或未保存');
  if (!a.model || a.model !== b.model) issues.push('模型種類不同或未保存');
  if (!a.setupSignature || !b.setupSignature || a.setupSignature !== b.setupSignature) issues.push('訓練設定不同或未保存（含特徵與回看日數）');
  return issues.length
    ? `不可直接排名：${issues.join('；')}。各卡只描述該標的自己的驗證結果；請以相同目標協定、模型、訓練設定與日期區間重跑一般驗證。`
    : '目標協定、模型、訓練設定、預測期間、報酬定義與驗證日期區間一致；可作描述性並列，仍須看各自基準，不代表模型品質。';
}
function savedComparisonChecklist(records) {
  if (records.length !== 2 || records.some((record) => !record.available)) return '比較前需有兩份已保存的一般驗證摘要。';
  const [a, b] = records;
  const checks = [
    ['目標協定', a.execution === 'next_close' && b.execution === 'next_close'],
    ['預測期間', a.horizon != null && a.horizon === b.horizon],
    ['報酬定義', !!a.returnType && a.returnType === b.returnType],
    ['模型', !!a.model && a.model === b.model],
    ['訓練設定', !!a.setupSignature && a.setupSignature === b.setupSignature],
    ['驗證日期區間', !!a.period && a.period !== '驗證期間不可用' && a.period === b.period],
  ];
  const ready = checks.every(([, ok]) => ok);
  return `可比條件逐項檢查：${checks.map(([label, ok]) => `${label}${ok ? '一致' : '缺少或不同'}`).join('；')}。${ready ? '可描述性並列，仍須對照各自基準。' : '目前只適合分別閱讀各自摘要；不可直接排名。'}`;
}
async function renderSavedCrossAssetComparison(symbol = byId('symbolSelect')?.value || 'TAIEX') {
  const panel = byId('crossAssetSavedComparison');
  if (!panel) return;
  const selectedSymbol = byId('symbolSelect')?.value;
  if (selectedSymbol && selectedSymbol !== symbol) return renderSavedCrossAssetComparison(selectedSymbol);
  const requestId = ++crossAssetRenderRequest;
  if (symbol === 'TAIEX') { panel.textContent = '目前選取 TAIEX；選取一檔個股後會與 TAIEX 的已保存一般驗證摘要並列。'; return; }
  panel.textContent = '正在讀取已保存的一般驗證摘要…';
  const items = [{symbol, label:seriesDisplayName(symbol)}, {symbol:'TAIEX', label:'TAIEX'}];
  const records = await Promise.all(items.map(async (item) => {
    try { return savedValidationSummary(await api(`/api/validation/latest?symbol=${encodeURIComponent(item.symbol)}`), item.label); }
    catch (_) { return { label: item.label, available: false, message: '目前無法讀取已保存的一般驗證結果。' }; }
  }));
  if (requestId !== crossAssetRenderRequest) return;
  const currentSymbol = byId('symbolSelect')?.value;
  if (currentSymbol && currentSymbol !== symbol) return renderSavedCrossAssetComparison(currentSymbol);
  renderSavedComparisonLines(panel, records);
}
function renderSavedComparisonLines(panel, records) {
  panel.replaceChildren();
  const heading = document.createElement('strong'); heading.textContent = '已保存的一般驗證摘要'; panel.append(heading);
  const intro = document.createElement('p'); intro.className = 'comparison-intro'; intro.textContent = '先逐一讀取每個標的的誤差與資料範圍，再判斷它們是否能公平比較。'; panel.append(intro);
  const list = document.createElement('ul');
  records.forEach((record) => {
    const item = document.createElement('li'); item.className = 'saved-comparison-card';
    const title = document.createElement('strong'); title.className = 'saved-comparison-title'; title.textContent = record.label; item.append(title);
    if (!record.available) { const message = document.createElement('p'); message.textContent = record.message; item.append(message); list.append(item); return; }
    const meta = document.createElement('small'); meta.className = 'saved-comparison-meta'; meta.textContent = `${record.model} · ${record.setup} · ${record.folds} 折 · ${record.samples.toLocaleString('zh-TW')} 筆 OOF`; item.append(meta);
    const metrics = document.createElement('dl'); metrics.className = 'saved-comparison-metrics';
    for (const [label, value] of [['模型 MAE', record.mae], ['簡單基準 MAE', record.baseline], ['模型 − 基準', record.delta], ['驗證期間', record.period]]) {
      const pair = document.createElement('div'); const term = document.createElement('dt'); term.textContent = label; const detail = document.createElement('dd'); detail.textContent = value; pair.append(term, detail); metrics.append(pair);
    }
    item.append(metrics);
    const direction = document.createElement('p'); direction.className = 'saved-comparison-direction'; direction.textContent = record.direction; item.append(direction);
    list.append(item);
  });
  panel.append(list);
  const compatibility = document.createElement('p'); compatibility.className = 'saved-comparison-compatibility'; compatibility.setAttribute('role', 'status'); compatibility.textContent = savedComparisonCompatibility(records); panel.append(compatibility);
  const checklist = document.createElement('p'); checklist.className = 'saved-comparison-checklist'; checklist.textContent = savedComparisonChecklist(records); panel.append(checklist);
  const note = document.createElement('small'); note.className = 'comparison-caution'; note.textContent = 'MAE 越低代表該標的、該期間的驗證誤差越小。期間或基準不同時不能直接排名；這些摘要不構成模型品質結論。'; panel.append(note);
}
function selectedFeatures() { return [...document.querySelectorAll('#featureChoices input:checked')].map((n) => n.value); }
function renderPlaygroundOutput() {
  const kind = currentModel(), isCurrent = !!state.validation && currentConfigMatches();
  const currentRows = isCurrent ? state.validation.models?.find(model => model.key === kind)?.folds?.flatMap(fold => fold.predictions || []) || [] : [];
  const trace = state.forwardTrace && kind === 'mlp' && isCurrent ? state.forwardTrace : null;
  const row = trace ? { predicted:trace.prediction, actual:trace.actual, returnType:trace.returnType } : currentRows.at(-1);
  const asSimple = (value, type) => type === 'log' ? Math.expm1(Number(value)) : Number(value);
  const marker = byId('playgroundReturnMarker'), gauge = byId('playgroundReturnGauge');
  const predictionPercent = row && Number.isFinite(Number(row.predicted)) ? asSimple(row.predicted, row.returnType || byId('returnType').value) * 100 : null;
  if (marker && gauge) {
    if (predictionPercent === null) marker.setAttribute('hidden', '');
    else {
      const extent = Math.max(1, Math.ceil(Math.abs(predictionPercent) * 2) / 2);
      marker.removeAttribute('hidden');
      marker.setAttribute('cx', String(Math.max(20, Math.min(200, 110 + predictionPercent / extent * 90))));
      byId('playgroundGaugeMin').textContent = `−${extent.toFixed(1)}%`;
      byId('playgroundGaugeMax').textContent = `+${extent.toFixed(1)}%`;
      marker.setAttribute('aria-label', `預測報酬 ${predictionPercent >= 0 ? '+' : ''}${predictionPercent.toFixed(4)}%`);
      gauge.setAttribute('aria-label', `驗證預測報酬 ${predictionPercent >= 0 ? '+' : ''}${predictionPercent.toFixed(4)}%；刻度範圍正負 ${extent.toFixed(1)}%`);
    }
  }
  byId('playgroundOutputValue').textContent = row && Number.isFinite(Number(row.predicted)) ? pct(asSimple(row.predicted, row.returnType || byId('returnType').value), 4) : '—';
  byId('playgroundOutputActual').textContent = row && Number.isFinite(Number(row.actual)) ? `實際值：${pct(asSimple(row.actual, row.returnType || byId('returnType').value), 4)}` : '實際值：—';
  const outputModel = isCurrent ? state.validation.models?.find(model => model.key === kind) : null;
  byId('playgroundOutputMae').textContent = outputModel && Number.isFinite(Number(outputModel.mae)) ? pct(outputModel.mae) : '—';
  byId('playgroundOutputCaption').textContent = trace ? '驗證折單筆實際輸出' : row ? '最近一筆 OOF 驗證預測' : '尚未產生預測';
  byId('playgroundOutputNote').textContent = row ? '數值來自目前驗證結果；非未來市場保證。' : state.validation ? '目前設定已變更；重新訓練後才會更新輸出。' : '完成驗證訓練後，這裡會呈現真實預測及誤差。';
}
function selectedModels() { return [...new Set([currentModel(), ...[...document.querySelectorAll('.model-compare input:checked')].map((n) => n.value)])]; }
function hiddenSizes() { return [1, 2, 3, 4].map((i) => byId(`hiddenSize${i}`)).filter((input) => !input.disabled).map((input) => Number(input.value)).filter((n) => n > 0); }
function currentModel() { return byId('modelType').value; }
function saveDraftConfig() {
  try {
    const values = Object.fromEntries(CONFIG_FIELDS.map((id) => [id, byId(id).value]));
    values.buyThreshold = Number(byId('buyThreshold').value) / 100;
    values.sellThreshold = Number(byId('sellThreshold').value) / 100;
    values.features = selectedFeatures();
    values.hiddenSizes = hiddenSizes();
    values.compareModels = [...document.querySelectorAll('.model-compare input:checked')].map((n) => n.value);
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(values));
  } catch (_) {}
}
function restoreDraftConfig(config = null) {
  let saved = config;
  if (!saved) { try { saved = JSON.parse(localStorage.getItem(CONFIG_STORAGE_KEY) || 'null'); } catch (_) { saved = null; } }
  if (!saved || typeof saved !== 'object') return false;
  saved = { ...saved };
  if (Array.isArray(saved.modelTypes)) saved.modelType = saved.modelTypes[0];
  if (Array.isArray(saved.hiddenSizes)) saved.hiddenSizes.forEach((value, index) => { saved[`hiddenSize${index + 1}`] = value; });
  for (const id of CONFIG_FIELDS) if (saved[id] !== undefined && byId(id)) {
    const value = id === 'buyThreshold' || id === 'sellThreshold' ? Number(saved[id]) * 100 : saved[id];
    byId(id).value = String(value);
  }
  if (Array.isArray(saved.features)) {
    document.querySelectorAll('#featureChoices input').forEach((input) => { input.checked = saved.features.includes(input.value); });
  }
  if (Array.isArray(saved.compareModels)) document.querySelectorAll('.model-compare input').forEach((input) => { input.checked = saved.compareModels.includes(input.value); });
  if (Array.isArray(saved.hiddenSizes) && currentModel() === 'mlp') setPlaygroundLayerCount(saved.hiddenSizes.length, false);
  byId('lookbackValue').textContent = byId('lookback').value;
  return true;
}
function buildConfig() {
  const sizes = hiddenSizes();
  const layers = currentModel() === 'mlp' ? sizes.length : Number(byId('hiddenLayers').value);
  return {
    symbol: byId('symbolSelect')?.value || 'TAIEX', buyThreshold: Number(byId('buyThreshold')?.value || 0.2)/100, sellThreshold: Number(byId('sellThreshold')?.value || -0.2)/100,
    modelTypes: selectedModels(), features: selectedFeatures(), lookback: Number(byId('lookback').value),
    horizon: Number(byId('horizon').value), returnType: byId('returnType').value,
    epochs: Number(byId('epochs').value), batchSize: Number(byId('batchSize').value),
    hiddenUnits: sizes[0] || 32, hiddenLayers: layers, hiddenSizes: sizes,
    dropout: Number(byId('dropout').value), learningRate: Number(byId('learningRate').value),
    optimizer: byId('optimizer').value, loss: byId('loss').value, seed: Number(byId('seed').value),
  };
}

function renderStatus(status) {
  state.status = status;
  if (byId('symbolSelect')) byId('symbolSelect').value = status.symbol || 'TAIEX';
  byId('periodStart').textContent = status.start;
  byId('periodEnd').textContent = status.end;
  const selectedName=seriesDisplayName(status.symbol);
  byId('historyChart')?.setAttribute('aria-label',`${selectedName} 收盤價時間序列與訓練、驗證、測試區間。使用左右方向鍵瀏覽資料點。`);
  const axis=document.querySelector('.chart-frame .axis-right');if(axis)axis.textContent=selectedName;
  byId('dataNote').textContent = `${status.featureNote} 資料來源：${status.source}。期間 ${status.start} 至 ${status.end}，共 ${formatInt(status.rows)} 個交易日。`;
  byId('dataHash').textContent = `資料 SHA-256　${status.sha256}`;
  byId('featureNote').textContent = '由歷史收盤指數計算；不含 OHLC 或成交量。';
  const trainEnd = status.validationStart || status.trainValidationEnd;
  byId('trainDates').textContent = `${status.start} — ${trainEnd}`;
  byId('validationDates').textContent = `${trainEnd} — ${status.trainValidationEnd}`;
  byId('testDates').textContent = `${status.lockedTestStart} — ${status.end}`;
  renderStocks({stocks:state.stocks,universeNote:state.stockUniverseNote});
  renderChart();
}

function seriesDisplayName(symbol = state.status?.symbol || 'TAIEX') {
  return symbol === 'TAIEX' ? 'TAIEX' : (state.stocks.find(stock => stock.symbol === symbol)?.name || symbol);
}

function renderStocks(payload) {
  state.stocks = payload.stocks || state.stocks;
  state.stockUniverseNote = payload.universeNote || state.stockUniverseNote;
  const availableCount = state.stocks.filter(stock => stock.available).length;
  byId('stockUniverseNote').textContent = `${state.stockUniverseNote}（${availableCount}/${state.stocks.length} 檔本機資料可用）　·　標的列可橫向瀏覽`;
  const select = byId('symbolSelect'), current = select.value || 'TAIEX';
  select.innerHTML = `<option value="TAIEX">TAIEX · 加權指數</option>` + state.stocks.map(stock => `<option value="${stock.symbol}" ${stock.available?'':'disabled'}>${stock.symbol} · ${stock.name}${stock.available?'':'（請先更新）'}</option>`).join('');
  select.value = current;
  const index = {symbol:'TAIEX',name:'加權指數',available:true,rows:state.status?.rows,end:state.status?.end};
  const options = [index, ...state.stocks];
  byId('stockCards').innerHTML = options.map(stock => {
    const selected = stock.symbol === current;
    const count = Number.isFinite(Number(stock.rows)) ? `${formatInt(stock.rows)} 筆` : '載入中';
    const label = `${stock.name}，${stock.symbol}，${count}${stock.end ? `，資料至 ${stock.end}` : ''}${selected ? '，目前標的' : ''}`;
    const period = stock.start && stock.end ? `${stock.start} 至 ${stock.end}` : '尚無可用本機資料';
    const source = stock.source ? (stock.source.includes('TWSE') ? 'TWSE' : stock.source) : '本機資料';
    return `<button class="stock-card ${selected?'selected':''}" data-symbol="${stock.symbol}" type="button" aria-pressed="${selected}" aria-label="${label}" title="${label}；${period} · ${source}"><span class="stock-card-main"><strong>${stock.name}</strong><b>${selected?'目前':''}</b></span><span class="stock-card-meta"><code>${stock.symbol}</code><small>${count}</small></span><span class="stock-card-period">${period}</span><span class="stock-card-source">${source}</span></button>`;
  }).join('');
}

function renderSignals(result) {
  const model = result.models?.[0], rows = (model?.folds || []).flatMap(fold => fold.predictions || []).sort((a,b)=>a.date.localeCompare(b.date));
  if (!rows.length) { byId('signalPanel').hidden = true; return; }
  byId('signalPanel').hidden = false;
  const sourceSymbol = state.validationConfig?.symbol || byId('symbolSelect')?.value || 'TAIEX';
  const selectedSymbol = byId('symbolSelect')?.value || 'TAIEX';
  const sourceAsset = sourceSymbol === 'TAIEX' ? '加權指數' : state.stocks.find(stock => stock.symbol === sourceSymbol)?.name || sourceSymbol;
  const provenance = byId('signalProvenance');
  if (provenance) {
    const stale = !!state.validationConfig && !currentConfigMatches();
    provenance.textContent = `結果來源：${sourceAsset}（${sourceSymbol}）${stale ? ` · 目前選擇 ${selectedSymbol}，或實驗設定已變更；以下是上次驗證結果` : ''}`;
    provenance.hidden = false;
    provenance.classList.toggle('is-stale', stale);
  }
  const buy = Number(byId('buyThreshold').value)/100, sell = Number(byId('sellThreshold').value)/100;
  const returnType = result.returnType || state.validationConfig?.returnType || 'simple';
  const asSimpleReturn = value => returnType === 'log' ? Math.expm1(Number(value)) : Number(value);
  const labels = {buy_candidate:'偏多候選',hold:'觀望',sell_candidate:'偏空／退出候選'}, counts = {buy_candidate:0,hold:0,sell_candidate:0};
  rows.forEach(row => { row.simplePredicted = asSimpleReturn(row.predicted); row.simpleActual = asSimpleReturn(row.actual); row.signal = row.simplePredicted > buy ? 'buy_candidate' : row.simplePredicted < sell ? 'sell_candidate' : 'hold'; counts[row.signal]++; });
  const horizon = Math.max(1, Number(result.horizon || state.validationConfig?.horizon || 1));
  const replaySeries = state.fullSeries.length ? state.fullSeries : state.series;
  const byDate = new Map(replaySeries.map((point,index)=>[point.date,index]));
  const candidates=[];
  const validationStartIndex = byDate.get(state.status?.validationStart || '') ?? 0;
  const validationEndIndex = byDate.get(state.status?.trainValidationEnd || '') ?? (replaySeries.length - 1);
  for (const row of [...rows].sort((a,b)=>(byDate.get(a.originDate || '') ?? Infinity)-(byDate.get(b.originDate || '') ?? Infinity))) {
    const origin=byDate.get(row.originDate || ''), target=byDate.get(row.date);
    if (origin == null || target == null || target <= origin || target < validationStartIndex || target > validationEndIndex) continue;
    candidates.push({...row,originIndex:origin,entryIndex:origin+1,targetIndex:target});
  }
  const intervals=[]; let lastTarget=-1;
  for (const row of candidates) if (row.originIndex >= lastTarget) { intervals.push(row); lastTarget=row.targetIndex; }
  const fee=0.001425, sellCost=0.001425+0.003;
  const drawdown = curve => { let peak=1, worst=0; for(const value of curve){peak=Math.max(peak,value);worst=Math.max(worst,(peak-value)/peak);} return worst; };
  const intervalDates = firstLastIntervalDates(intervals);
  const replay = replayOofSignals(replaySeries, intervals, intervalDates.start, intervalDates.end, fee, sellCost);
  let { equity, curve, tradeReturns, completed, holdingDays, wins } = replay;
  const baselineSignals = movingAverageSignals(replaySeries, 20);
  const baseline = replayFixedSignals(replaySeries, baselineSignals, intervalDates.start, intervalDates.end, fee, sellCost);
  const momentumSignals = timeSeriesMomentumSignals(replaySeries, 20);
  const momentumBaseline = replayFixedSignals(replaySeries, momentumSignals, intervalDates.start, intervalDates.end, fee, sellCost);
  const cash = { equity: 1 };
  const winRate = completed > 0 ? `${(wins / completed * 100).toFixed(1)}%` : '—';
  const grossGain = tradeReturns.filter(r => r > 0).reduce((a,b)=>a+b, 0);
  const grossLoss = Math.abs(tradeReturns.filter(r => r < 0).reduce((a,b)=>a+b, 0));
  const profitFactor = grossLoss > 1e-6 ? (grossGain / grossLoss).toFixed(2) : (grossGain > 0 ? '∞' : '1.00');
  const firstEntry = intervalDates.start, finalTarget = intervalDates.end;
  const replaySessions = firstEntry != null && finalTarget != null ? Math.max(1, finalTarget - firstEntry + 1) : 0;
  const exposure = replaySessions ? Math.min(1, holdingDays / replaySessions) : 0;
  let buyHold=firstEntry != null && finalTarget > firstEntry ? 1-fee : 1; const holdCurve=[1,buyHold];
  if (firstEntry != null && finalTarget > firstEntry) for(let i=firstEntry+1;i<=finalTarget;i++){const gross=Number(replaySeries[i].close)/Number(replaySeries[i-1].close);buyHold*=Math.max(0,gross);holdCurve.push(buyHold);}
  if(intervals.length){buyHold*=1-sellCost;holdCurve.push(buyHold);}
  const resultLabel = value => `${((value-1)*100).toFixed(2)}%`;
  const smallSampleNote = completed < 30
    ? `目前只有 ${completed} 筆已完成交易；勝率與盈虧比樣本偏少，僅描述此驗證區間，不適合推論穩定表現。`
    : '交易筆數是描述統計；結果仍受驗證期間與簡化收盤成交假設限制。';
  const evidence = evaluateStrategyEvidence(equity, [
    { name: '20 日均線', equity: baseline.equity },
    { name: '20 日時間序列動能', equity: momentumBaseline.equity },
    { name: '買入持有', equity: buyHold },
  ], completed);
  const modelLagsBaselines = !evidence.complete || evidence.underperforming.length > 0;
  const laggingText = evidence.underperforming.join('、');
  const sampleGate = evidence.enoughTrades ? `${completed} 筆已完成交易` : `僅 ${completed} 筆已完成交易，少於 30 筆觀察線`;
  const strategyGate = `<aside class="strategy-gate" aria-label="策略交易准入檢查"><div class="strategy-gate-heading"><span class="gate-stop">尚未通過</span><strong>模型訊號不應直接拿去實盤</strong></div><p>${modelLagsBaselines ? `目前驗證窗模型規則淨報酬 ${resultLabel(equity)}，${evidence.complete ? `未超過同窗、含成本基準：${laggingText}。` : '策略或基準資料不足，無法判定相對表現。'}` : `目前驗證窗模型規則淨報酬 ${resultLabel(equity)}，高於所列基準；這仍只是同一驗證窗比較，不能證明未來優勢。`}${sampleGate}，最大回撤 ${(drawdown(curve)*100).toFixed(2)}%。</p><p><strong>執行條件仍缺：</strong>本機資料只有收盤價，沒有 OHLC、成交量、即時報價、撮合或券商回報。先用個股跑前瞻紙上帳戶，逐日驗證成本與持倉。</p><a href="/paper">前往紙上交易台 →</a></aside>`;
  byId('signalSummary').innerHTML = `<div class="signal-counts"><span class="buy-signal">▲ 偏多候選 <strong>${counts.buy_candidate}</strong></span><span>● 觀望 <strong>${counts.hold}</strong></span><span class="sell-signal">▼ 偏空／退出候選 <strong>${counts.sell_candidate}</strong></span><small>共 ${rows.length} 筆 walk-forward 預測；依訊號日收盤後判斷下一段 ${horizon} 個交易日。圖上標記只顯示驗證期。</small></div>${strategyGate}<div class="strategy-results"><div class="strategy-title"><strong>驗證期策略比較</strong><span>次日收盤執行 · 每日收盤估值 · 折間維持持倉 · 往返成本 0.585%</span></div><div class="strategy-grid"><div><small>模型規則淨報酬</small><strong>${resultLabel(equity)}</strong></div><div><small>固定 20 日均線規則</small><strong>${resultLabel(baseline.equity)}</strong></div><div><small>20 日時間序列動能</small><strong>${resultLabel(momentumBaseline.equity)}</strong></div><div><small>買入持有淨報酬</small><strong>${resultLabel(buyHold)}</strong></div><div><small>不交易／全現金</small><strong>${resultLabel(cash.equity)}</strong></div><div><small>模型最大回撤</small><strong>${(drawdown(curve)*100).toFixed(2)}%</strong></div><div><small>模型成交／均持</small><strong>${completed} 筆 · ${completed?(holdingDays/completed).toFixed(1):'0.0'} 日</strong></div></div><p class="strategy-metadata">比較區間 ${firstEntry == null ? '—' : `${replaySeries[firstEntry].date} 至 ${replaySeries[finalTarget].date}`} · 市場曝險 ${(exposure*100).toFixed(1)}% · 預估成本含買進 0.1425%、賣出證交稅 0.3% 及賣出手續費 0.1425%。</p><p>訊號於收盤後計算，下一交易日收盤執行；每日以收盤價估值，折間缺少 OOF 訊號時維持持倉狀態。20 日均線規則依收盤是否高於均線持有；時間序列動能依當日收盤相對 20 個交易日前收盤決定方向。所有策略涵蓋同一日期區間與成本。不交易基準全程持現金。僅為收盤價簡化研究比較，不等於真實撮合。</p><p class="strategy-sample-note">${smallSampleNote}</p><span class="signal-disclaimer">研究用模型輸出，非實盤獲利保證或投資建議</span></div>`;
  const closeByDate = new Map(state.series.map(point => [point.date, Number(point.close)]));
  byId('signalRows').innerHTML = rows.slice(-100).reverse().map(row => {
    const originClose = closeByDate.get(row.originDate || '');
    const impliedClose = Number.isFinite(originClose) ? originClose * (1 + row.simplePredicted) : null;
    return `<tr><td>${row.originDate || row.date}</td><td>${row.date}</td><td>${pct(row.simplePredicted)}</td><td>${impliedClose == null ? '—' : impliedClose.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td><td><span class="signal-pill ${row.signal}">${labels[row.signal]}</span></td><td>${pct(row.simpleActual)}</td></tr>`;
  }).join('');
  renderChart();
}

function renderChart() {
  const svg = byId('historyChart');
  if (!svg || state.series.length < 2 || !state.status) return;
  const W = 1000, H = 350, L = 48, R = 18, T = 12, B = 26;
  const values = state.series.map((p) => p.close), min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  byId('phaseKey')?.toggleAttribute('hidden', !byId('showSplit').checked);
  document.querySelector('.timeline-panel .phase-rail')?.toggleAttribute('hidden', !byId('showSplit').checked);
  const innerW = W - L - R, innerH = H - T - B;
  const xAt = (i) => L + i / (values.length - 1) * innerW;
  const yAt = (v) => T + (max - v) / span * innerH;
  const indexFor = (date) => Math.max(0, state.series.findIndex((p) => p.date >= date));
  const validationAt = xAt(indexFor(state.status.validationStart || state.status.trainValidationEnd));
  const testAt = xAt(indexFor(state.status.lockedTestStart));
  const grid = [0, 1, 2, 3, 4].map((i) => {
    const y = T + innerH * i / 4, val = max - span * i / 4;
    return `<line class="chart-grid" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/><text class="chart-axis" x="${L - 9}" y="${y + 4}" text-anchor="end">${Math.round(val).toLocaleString()}</text>`;
  }).join('');
  const ticks = [];
  const firstYear = Number(state.series[0].date.slice(0, 4)), lastYear = Number(state.series.at(-1).date.slice(0, 4));
  const tickStep = Math.ceil((lastYear - firstYear) / 6);
  for (let year = firstYear; year <= lastYear; year += tickStep) {
    const idx = state.series.findIndex((p) => Number(p.date.slice(0, 4)) >= year);
    if (idx >= 0) ticks.push({ x: xAt(idx), label: String(year) });
  }
  if (!ticks.length || ticks.at(-1).label !== String(lastYear)) ticks.push({ x: xAt(values.length - 1), label: String(lastYear) });
  const timeGrid = ticks.map(({ x }) => `<line class="chart-grid chart-grid-vertical" x1="${x}" x2="${x}" y1="${T}" y2="${T + innerH}"/>`).join('');
  const xs = state.series.map((p, i) => `${xAt(i).toFixed(2)},${yAt(p.close).toFixed(2)}`).join(' ');
  const bands = byId('showSplit').checked ? `<rect class="band-train" x="${L}" y="${T}" width="${Math.max(0, validationAt - L)}" height="${innerH}"/><rect class="band-validation" x="${validationAt}" y="${T}" width="${Math.max(0, testAt - validationAt)}" height="${innerH}"/><rect class="band-test" x="${testAt}" y="${T}" width="${W - R - testAt}" height="${innerH}"/>` : '';
  const splitLines = byId('showSplit').checked ? `<line class="split-line train-boundary" x1="${validationAt}" y1="${T}" x2="${validationAt}" y2="${T + innerH}"/><line class="split-line test-boundary" x1="${testAt}" y1="${T}" x2="${testAt}" y2="${T + innerH}"/>` : '';
  const signalRows=(state.validation?.models?.[0]?.folds||[]).flatMap(fold=>fold.predictions||[]);
  const thresholdBuy=Number(byId('buyThreshold')?.value||0.2)/100, thresholdSell=Number(byId('sellThreshold')?.value||-0.2)/100;
  const logReturn=state.validation?.returnType==='log';
  const signalMarks=signalRows.map(row=>{const index=state.series.findIndex(point=>point.date===row.date);if(index<0)return'';const prediction=logReturn?Math.expm1(Number(row.predicted)):Number(row.predicted);if(prediction>thresholdBuy)return `<path class="signal-marker signal-marker-buy" d="M ${xAt(index)} ${yAt(values[index])-12} l -6 9 h 12 z"><title>${row.originDate||row.date} 收盤後：買進候選，預測 ${pct(prediction)}</title></path>`;if(prediction<thresholdSell)return `<path class="signal-marker signal-marker-sell" d="M ${xAt(index)} ${yAt(values[index])+12} l -6 -9 h 12 z"><title>${row.originDate||row.date} 收盤後：偏空／退出候選，預測 ${pct(prediction)}</title></path>`;return'';}).join('');
  svg.innerHTML = `${grid}${bands}${timeGrid}${splitLines}<polyline class="price-path" points="${xs}"/>${signalMarks}<circle class="chart-point" cx="${xAt(values.length - 1)}" cy="${yAt(values.at(-1))}" r="4"/>${ticks.map(({ x, label }, i) => `<text class="chart-axis" x="${x}" y="${H - 8}" text-anchor="${i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : 'middle'}">${label}</text>`).join('')}`;
  const marker = svg.querySelector('.chart-point');
  let activeIndex = values.length - 1;
  const showPoint = (index, event = null, announce = false) => {
    activeIndex = Math.max(0, Math.min(values.length - 1, index));
    const point = state.series[activeIndex]; if (!point) return;
    const tip = byId('chartTooltip'), rect = svg.getBoundingClientRect();
    tip.hidden = false;
    tip.textContent = `${point.date}　收盤指數 ${point.close.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
    const localX = event ? event.clientX - rect.left : (xAt(activeIndex) / W) * rect.width;
    const localY = event ? event.clientY - rect.top : (yAt(point.close) / H) * rect.height;
    tip.style.left = `${Math.max(6, Math.min(rect.width - 230, localX + 10))}px`;
    tip.style.top = `${Math.max(4, localY - 30)}px`;
    marker.setAttribute('cx', xAt(activeIndex)); marker.setAttribute('cy', yAt(point.close));
    if (announce) byId('chartReadout').textContent = `${point.date}，${seriesDisplayName()} 收盤價 ${point.close.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  };
  svg.onpointermove = (event) => {
    if (event.pointerType === 'touch') return;
    const rect = svg.getBoundingClientRect(), localX = ((event.clientX - rect.left) / rect.width) * W;
    const index = Math.max(0, Math.min(values.length - 1, Math.round((localX - L) / innerW * (values.length - 1))));
    showPoint(index, event);
  };
  svg.onpointerup = (event) => {
    if (event.pointerType !== 'touch') return;
    const rect = svg.getBoundingClientRect(), localX = ((event.clientX - rect.left) / rect.width) * W;
    showPoint(Math.round((localX - L) / innerW * (values.length - 1)), event, true);
  };
  svg.onkeydown = (event) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? values.length - 1 : activeIndex + (event.key === 'ArrowRight' ? 1 : -1);
    showPoint(next, null, true);
  };
  svg.onmouseleave = () => { byId('chartTooltip').hidden = true; };
  svg.onpointerleave = (event) => { if (event.pointerType !== 'touch') byId('chartTooltip').hidden = true; };
  const first = state.series[0], last = state.series.at(-1);
  const change = ((last.close / first.close) - 1) * 100;
  byId('historySummary').textContent = `${seriesDisplayName()} 收盤價由 ${first.date} 的 ${first.close.toLocaleString('en-US', { maximumFractionDigits: 2 })}，變為 ${last.date} 的 ${last.close.toLocaleString('en-US', { maximumFractionDigits: 2 })}，期間變化 ${change.toFixed(1)}%。圖中標示訓練、驗證與最後 20% 鎖定測試區間。使用方向鍵可逐筆瀏覽 ${values.length.toLocaleString('zh-TW')} 個資料點。`;
}

function networkTraceCurrent() { return !!state.forwardTrace && currentModel() === 'mlp' && currentConfigMatches(); }
function renderNetworkStage() {
  const strip = byId('networkSteps'), detail = byId('networkStepDetail');
  if (!strip || !detail) return;
  const total = Number(byId('networkDiagram')?.dataset.layerCount || 0), stage = Math.max(0, Math.min(networkMotion.step, total - 1));
  const trace = networkTraceCurrent() ? state.forwardTrace : null;
  const linears = trace ? (trace.layers || []).filter(item => item.type === 'Linear') : [];
  const relus = trace ? (trace.layers || []).filter(item => item.type === 'ReLU') : [];
  const isInput = stage === 0, isOutput = stage === total - 1;
  const li = isInput ? 0 : isOutput ? Math.max(0, linears.length - 1) : stage - 1;
  const linear = linears[li], matrix = trace?.weights?.[li]?.values || [], storedBias = trace?.biases?.[li]?.values || [];
  const input = !trace ? [] : isInput ? trace.input : li === 0 ? trace.input : (relus[li - 1]?.values || []);
  const z = linear?.values || [], bias = z.map((value, index) => Number.isFinite(storedBias[index]) ? storedBias[index] : value - (matrix[index] || []).reduce((sum, weight, j) => sum + weight * (input[j] || 0), 0));
  const activation = isOutput ? z : (relus[li]?.values || []);
  const title = isInput ? '輸入張量 X' : isOutput ? '報酬率輸出' : '隱藏層 ' + stage;
  const drawnNeurons = [...(byId('networkDiagram')?.querySelectorAll(`.network-node[data-layer="${stage}"]`) || [])].map(node => Number(node.dataset.neuron) + 1);
  const drawnWidth = drawnNeurons.length ? Math.max(...drawnNeurons) : 0;
  const nodeCount = isInput ? (trace?.input?.length || drawnWidth) : isOutput ? 1 : (activation?.length || z.length || drawnWidth);
  const selected = Math.max(0, Math.min(networkMotion.neuron, Math.max(0, nodeCount - 1)));
  networkMotion.neuron = selected;
  const availableValues = isInput ? trace?.input || [] : activation;
  const selectedValue = availableValues[selected];
  const inWeights = matrix[selected] || [];
  const contributions = inWeights.map((weight, index) => ({ weight, value: input[index] || 0, product: weight * (input[index] || 0) }));
  const selectedBias = bias[selected] || 0;
  const selectedZ = z[selected];
  const equationTerms = contributions.slice(0, 6).map((item, index) => `<span class="term"><b>${item.weight >= 0 ? '+' : '−'}${Math.abs(item.weight).toFixed(3)}</b> × <i>${item.value.toFixed(3)}</i><small>${item.product >= 0 ? '+' : '−'}${Math.abs(item.product).toFixed(3)}</small></span>`).join('');
  const shapeNote = !trace && currentModel() === 'mlp' && !isInput && !isOutput
    ? '<div class="inspector-empty"><strong>矩陣維度例子</strong><span>若本層接收 3 維向量 a∈ℝ³、含 2 個神經元，則權重矩陣 W∈ℝ²ˣ³；相乘 Wa∈ℝ²，結果為 2 維。每個神經元各有一個偏置 b，再各自套用 ReLU。這是維度示意，非本次訓練參數。</span></div>'
    : '';
  detail.innerHTML = '<header><div><small>' + (isInput ? '輸入層' : isOutput ? '回歸輸出' : '隱藏層 ' + stage) + '</small><h3>' + (isInput ? '選取輸入神經元' : isOutput ? '模型預測' : '神經元 ' + (selected + 1)) + '</h3></div><span class="detail-step">' + String(stage + 1).padStart(2, '0') + ' / ' + total + '</span></header>' + (trace && !isInput ? '<div class="neuron-inspector"><div class="inspector-equation">' + equationTerms + (contributions.length > 6 ? '<span class="term-more">… 共 ' + contributions.length + ' 項輸入</span>' : '') + '<strong>+ b ' + (selectedBias >= 0 ? '' : '− ') + Math.abs(selectedBias).toFixed(3) + '</strong></div><div class="inspector-output"><span>加權和 z</span><b>' + Number(selectedZ).toFixed(6) + '</b><span>activation a</span><b>' + Number(selectedValue).toFixed(6) + '</b></div></div>' : '<div class="inspector-empty"><strong>' + (trace ? '輸入值' : '尚未訓練') + '</strong><span>' + (trace ? '此層顯示模型實際讀入的標準化特徵值。' : '完成 MLP 驗證訓練後，點選圖中的神經元即可查看真實權重、偏置與 activation。') + '</span></div>') + shapeNote + '<p class="inspector-note">' + (trace ? trace.originDate + ' → ' + trace.sampleDate + ' · 驗證第 ' + trace.fold + ' 折。權重、輸入與偏置均取自本次 PyTorch 前向計算。' : '目前是架構預覽，不顯示虛構權重或數值。') + '</p>';
  byId('networkDiagram')?.querySelectorAll('.network-node').forEach(node => {
    const active = Number(node.dataset.layer) === stage && Number(node.dataset.neuron) === selected;
    node.classList.toggle('is-selected-neuron', active);
    node.setAttribute('aria-pressed', String(active));
  });
  byId('networkDiagram')?.querySelectorAll('.network-connection').forEach(line => {
    const edgeLayer = Number(line.dataset.layer);
    const selectedEdge = isInput
      ? edgeLayer === stage && Number(line.dataset.sourceNeuron) === selected
      : edgeLayer === stage - 1 && Number(line.dataset.targetNeuron) === selected;
    line.classList.toggle('is-selected-edge', selectedEdge);
  });
  byId('networkMotionStatus').textContent = networkMotion.playing ? '訊號正在逐層傳遞' : networkStageText(stage);
  const equation = byId('networkStageEquation');
  if (equation) equation.textContent = networkStageEquation(stage);
  strip.innerHTML = Array.from({ length: total }, (_, index) => '<button class="network-step ' + (index < stage ? 'is-complete' : '') + ' ' + (index === stage ? 'is-current' : '') + '" type="button" role="listitem" data-step="' + index + '" aria-current="' + (index === stage ? 'step' : 'false') + '"><small>' + String(index + 1).padStart(2, '0') + '</small><strong>' + (index === 0 ? '輸入 X' : index === total - 1 ? '預測 ŷ' : '隱藏層 ' + index) + '</strong><span>' + (index === 0 ? '特徵張量' : index === total - 1 ? '報酬率回歸' : 'W a + b → ReLU') + '</span></button>').join('');
}

function renderArchitecture() {
  if (!networkMotion.training) resetNetworkMotion();
  const kind = currentModel(), features = selectedFeatures(), sizes = hiddenSizes();
  const recurrent = ['rnn', 'lstm', 'gru'].includes(kind);
  const tcn = kind === 'tcn';
  const widths = tcn ? [16, 16] : recurrent ? Array(Number(byId('hiddenLayers').value)).fill(Number(byId('hiddenSize1').value)) : sizes;
  byId('playgroundLayerCount').textContent = String(widths.length);
  byId('addLayer').disabled = widths.length >= 4;
  byId('removeLayer').disabled = widths.length <= 1;
  byId('recurrentLayersField').hidden = !recurrent;
  document.querySelector('.mlp-sizes').hidden = recurrent || tcn;
  byId('addLayer').hidden = tcn;
  byId('removeLayer').hidden = tcn;
  byId('playgroundLayerCount').closest('.layer-stepper').hidden = tcn;
  const availableInputs = byId('featureChoices').querySelectorAll('.feature-option').length;
  const activeInputs = features.length;
  const inputDimensions = recurrent ? activeInputs : Number(byId('lookback').value) * activeInputs;
  const shownInputs = Math.min(10, Math.max(1, inputDimensions));
  const plot = { x0: 70, x1: 930, y0: 86, y1: 374 };
  if (tcn) {
    const times = [200, 300, 400, 500, 600, 700, 800, 900];
    const diagram = byId('networkDiagram');
    diagram.setAttribute('viewBox','0 0 1000 550');
    const row = (label, points, layer, kind) => `<text class="tcn-time-label" x="146" y="${points[0][1]+4}" text-anchor="end">${label}</text><polyline class="tcn-lane" points="${points.map(point => point.join(',')).join(' ')}"/>${points.map(([px,py],index)=>`<g class="network-node ${kind} tcn-node" data-layer="${layer}" data-neuron="${index}" style="--tcn-delay:${index*65}ms"><circle cx="${px}" cy="${py}" r="11"/><text x="${px}" y="${py+4}" text-anchor="middle">${index+1}</text></g>`).join('')}`;
    const inputPoints = times.map(x=>[x,126]), blockOne = times.map(x=>[x,218]), blockTwo = times.map(x=>[x,310]);
    const residualBlock = (title,y,d,layer) => `<g class="tcn-residual" data-layer="${layer}"><rect class="tcn-residual-frame" x="188" y="${y}" width="712" height="62" rx="10"/><text class="tcn-residual-title" x="208" y="${y+24}">${title}</text><text class="tcn-residual-meta" x="208" y="${y+43}">k=3 · d=${d}</text><path class="tcn-block-flow" d="M340 ${y+32}h50m126 0h50m126 0h50m126 0h28"/><rect class="tcn-op" x="390" y="${y+12}" width="126" height="40" rx="7"/><text x="453" y="${y+36}" text-anchor="middle">因果卷積</text><rect class="tcn-op" x="566" y="${y+12}" width="126" height="40" rx="7"/><text x="629" y="${y+36}" text-anchor="middle">GELU</text><rect class="tcn-op" x="742" y="${y+12}" width="126" height="40" rx="7"/><text x="805" y="${y+36}" text-anchor="middle">Dropout</text></g>`;
    diagram.innerHTML = `<text class="tcn-title" x="500" y="34" text-anchor="middle">Temporal convolution network</text><text class="tcn-key" x="500" y="57" text-anchor="middle">causal, dilated convolutions · sequence processed in parallel</text>${row('輸入序列 · x',inputPoints,0,'node-input')}<path class="network-connection network-sample-path tcn-edge" data-layer="0" d="M 900 126 C 942 126 942 218 900 218"/>${row('殘差區塊 · d=1',blockOne,1,'node-hidden')}<path class="network-connection network-sample-path tcn-edge" data-layer="1" d="M 900 218 C 942 218 942 310 900 310"/>${row('殘差區塊 · d=2',blockTwo,2,'node-hidden')}<path class="network-connection network-sample-path tcn-output-link" data-layer="2" d="M 912 310 H 958"/><g class="network-node node-output tcn-output-node" data-layer="3" data-neuron="0"><circle cx="970" cy="310" r="13"/><text class="tcn-output-label" x="970" y="338" text-anchor="middle">ŷ</text></g><text class="tcn-detail-title" x="188" y="372">單一殘差區塊</text><text class="tcn-detail-subtitle" x="900" y="372" text-anchor="end">輸入捷徑 + 卷積轉換</text>${residualBlock('殘差區塊 1',384,1,1)}${residualBlock('殘差區塊 2',456,2,2)}<text class="tcn-footnote" x="544" y="538" text-anchor="middle">每個區塊都保留捷徑路徑；dilation 逐層擴大可讀取的歷史範圍。</text>`;
    diagram.dataset.layerCount='4';
    byId('featureCount').textContent = `${features.length} / ${availableInputs} 項`;
    byId('layerSummary').textContent = '2 個因果卷積區塊 · 16 通道 · kernel 3 · dilation 1/2';
    byId('inputEquation').textContent = `X ∈ ℝ${byId('lookback').value}×${features.length}`;
    byId('toolbarEpoch').textContent = String(byId('epochs').value).padStart(3,'0');
    byId('toolbarLearningRate').textContent = Number(byId('learningRate').value).toPrecision(2);
    byId('toolbarActivation').textContent = 'GELU / causal conv';
    byId('toolbarRegularization').textContent = `Dropout ${Number(byId('dropout').value).toFixed(2)}`;
    renderPlaygroundOutput();
    const h=Number(byId('horizon').value);
    byId('targetEquation').textContent=byId('returnType').value==='log'?`ln(Cₜ₊${h+1}/Cₜ₊₁)`:`Cₜ₊${h+1}/Cₜ₊₁ − 1`;
    byId('lossEquation').textContent=byId('loss').value==='huber'?'Huber（ŷ, y）':'MSE（ŷ, y）';
    byId('network').setAttribute('aria-label','因果時間卷積網路（TCN）架構：膨脹因果卷積與殘差捷徑');
    const label=document.querySelector('.playground-color-key');
    if(label)label.innerHTML='<span><i class="weight-neutral"></i>因果卷積路徑</span><small>每個時間點只連到自己與左側的歷史時間點；殘差捷徑跨越卷積區塊。</small>';
    renderNetworkStage();
    return;
  }
  const xs = [plot.x0, ...widths.map((_, i) => plot.x0 + (i + 1) * (plot.x1 - plot.x0) / (widths.length + 1)), plot.x1];
  // Draw a sparse, labeled sample of each hidden layer; the model keeps its full configured width.
  const layerCounts = [shownInputs, ...widths.map((n) => Math.min(8, Math.max(5, Math.ceil(Math.sqrt(n))))), 1];
  const pointSets = layerCounts.map((count, layer) => Array.from({ length: count }, (_, i) => ({ x: xs[layer], y: count === 1 ? 159 : plot.y0 + i * (plot.y1 - plot.y0) / (count - 1) })));
  const edgeData = pointSets.slice(0, -1).flatMap((layer, i) => layer.flatMap((a, nodeIndex) => pointSets[i + 1].map((b, targetIndex) => {
    const sourceWidth = i === 0 ? inputDimensions : widths[i - 1];
    const targetWidth = i + 1 === pointSets.length - 1 ? 1 : widths[i];
    return { layer:i, sourceNeuron:layer.length <= 1 ? 0 : Math.round(nodeIndex * (sourceWidth - 1) / (layer.length - 1)), targetNeuron:pointSets[i + 1].length <= 1 ? 0 : Math.round(targetIndex * (targetWidth - 1) / (pointSets[i + 1].length - 1)), x1:a.x + 17, y1:a.y, x2:b.x - 17, y2:b.y, cx:(a.x+b.x)/2, samplePath:((nodeIndex * pointSets[i + 1].length + targetIndex) % 5 === 0) ? ' network-sample-path' : '', flowDelay:((nodeIndex * pointSets[i + 1].length + targetIndex) % 8) * 32 };
  })));
  const edgePath = (edge) => `M ${edge.x1} ${edge.y1} C ${edge.cx} ${edge.y1}, ${edge.cx} ${edge.y2}, ${edge.x2} ${edge.y2}`;
  const hitLines = edgeData.map(edge => `<path class="network-edge-hit" data-layer="${edge.layer}" data-source-neuron="${edge.sourceNeuron}" data-target-neuron="${edge.targetNeuron}" d="${edgePath(edge)}"/>`).join('');
  const lines = edgeData.map(edge => `<path class="network-connection${edge.samplePath}" data-layer="${edge.layer}" data-source-neuron="${edge.sourceNeuron}" data-target-neuron="${edge.targetNeuron}" style="--flow-delay:${edge.flowDelay}ms" d="${edgePath(edge)}"/>`).join('');
  const hitNodes = pointSets.flatMap((layer, layerIndex) => layer.map((p, nodeIndex) => {
    const actualWidth = layerIndex === 0 ? inputDimensions : layerIndex === layerCounts.length - 1 ? 1 : widths[layerIndex - 1];
    const neuron = layer.length <= 1 ? 0 : Math.round(nodeIndex * (actualWidth - 1) / (layer.length - 1));
    return `<circle class="network-node-hit" data-layer="${layerIndex}" data-neuron="${neuron}" aria-hidden="true" cx="${p.x}" cy="${p.y}" r="28"/>`;
  })).join('');
  const nodes = pointSets.flatMap((layer, layerIndex) => layer.map((p, nodeIndex) => {
    const count = layerCounts[layerIndex], actualWidth = layerIndex === 0 ? inputDimensions : layerIndex === layerCounts.length - 1 ? 1 : widths[layerIndex - 1];
    const neuron = count <= 1 ? 0 : Math.round(nodeIndex * (actualWidth - 1) / (count - 1));
    const trainingDelay = (layerIndex * 190 + nodeIndex * 75) % 1500;
    return `<rect class="network-node ${layerIndex === 0 ? 'node-input' : layerIndex === pointSets.length - 1 ? 'node-output' : 'node-hidden'}" data-layer="${layerIndex}" data-node="${nodeIndex}" data-neuron="${neuron}" tabindex="0" role="button" aria-label="第 ${layerIndex + 1} 層神經元 ${neuron + 1}" aria-pressed="false" style="--row-index:${nodeIndex};--training-delay:${trainingDelay}ms;" x="${p.x - 12}" y="${p.y - 12}" width="24" height="24" rx="4"/>`;
  })).join('');
  const labels = pointSets.map((layer, i) => {
    const drawn = layerCounts[i], x = xs[i], title = i === 0 ? `${inputDimensions} inputs · ${drawn} shown` : i === pointSets.length - 1 ? 'ŷ' : `${widths[i - 1]} neurons · ${drawn} shown`;
    return `<text class="network-label" x="${x}" y="38" text-anchor="middle">${title}</text>`;
  }).join('');
  const inputText = pointSets[0].map((point, i) => {
    const originalIndex = shownInputs <= 1 ? 0 : Math.round(i * (inputDimensions - 1) / (shownInputs - 1));
    return `<text class="network-input-label" x="${plot.x0 - 28}" y="${point.y + 4}" text-anchor="end">x${originalIndex + 1}</text>`;
  }).join('');
  byId('networkDiagram').setAttribute('viewBox', '0 0 1000 450');
  byId('networkDiagram').innerHTML = `<path class="network-bracket" d="M42 68h-9v324h9"/><text class="network-dimension" x="22" y="226" text-anchor="middle" transform="rotate(-90 22 226)">${inputDimensions} inputs</text>${labels}${hitLines}${hitNodes}${lines}${inputText}${nodes}`;
  byId('networkDiagram').dataset.layerCount = String(pointSets.length);
  document.querySelectorAll('#featureChoices .feature-option').forEach((opt, idx) => {
    const checked = opt.querySelector('input')?.checked;
    opt.classList.toggle('is-active-feature', !!checked);
    opt.style.setProperty('--row-index', idx);
  });
  byId('featureCount').textContent = `${features.length} / ${availableInputs} 項`;
  const dropout = Number(byId('dropout').value);
  byId('layerSummary').textContent = tcn
    ? '2 個因果卷積區塊 · 16 通道 · kernel 3 · dilation 1/2'
    : recurrent
    ? `${widths.length} 層 · 狀態維度 ${widths[0] || 0} · Dropout ${widths.length > 1 ? dropout : 0}`
    : `${widths.length} 層 · ReLU · Dropout ${dropout}`;
  byId('inputEquation').textContent = `X ∈ ℝ${byId('lookback').value}×${features.length}`;
  byId('toolbarEpoch').textContent = String(byId('epochs').value).padStart(3, '0');
  byId('toolbarLearningRate').textContent = Number(byId('learningRate').value).toPrecision(2);
  byId('toolbarActivation').textContent = kind === 'mlp' ? 'ReLU' : tcn ? 'GELU / causal conv' : 'Tanh / gates';
  byId('toolbarRegularization').textContent = Number(byId('dropout').value) ? `Dropout ${Number(byId('dropout').value).toFixed(2).replace(/0+$/, '').replace(/\.$/, '')}` : 'None';
  renderPlaygroundOutput();
  const h = Number(byId('horizon').value);
  byId('targetEquation').textContent = byId('returnType').value === 'log' ? `ln(Cₜ₊${h+1}/Cₜ₊₁)` : `Cₜ₊${h+1}/Cₜ₊₁ − 1`;
  byId('lossEquation').textContent = byId('loss').value === 'huber' ? 'Huber（ŷ, y）' : 'MSE（ŷ, y）';
  byId('lookbackValue').textContent = byId('lookback').value;
  const label = { mlp: '多層感知器', rnn: '循環神經網路', lstm: '長短期記憶', gru: '閘控循環單元', tcn: '因果時間卷積網路' }[kind];
  document.querySelector('.status-pill').textContent = state.validation ? (currentConfigMatches() ? '驗證完成' : '設定已變更') : '尚未訓練';
  byId('network').setAttribute('aria-label', `${label} 模型架構`);
  const traceIsCurrent = state.forwardTrace && kind === 'mlp' && currentConfigMatches();
  const colorKey = document.querySelector('.playground-color-key');
  if (colorKey) colorKey.innerHTML = traceIsCurrent
    ? '<span><i class="weight-positive"></i>正權重</span><span><i class="weight-negative"></i>負權重</span><small>每層顯示 4 個代表神經元；顏色與粗細依驗證樣本的實際權重</small>'
    : '<span><i class="weight-neutral"></i>網路連接</span><small>各層以代表神經元抽樣顯示；此為架構預覽，不呈現假權重</small>';
  if (tcn && colorKey) colorKey.innerHTML = '<span><i class="weight-neutral"></i>因果卷積通道</span><small>固定兩個殘差區塊；每個位置只聚合當下及過去輸入</small>';
  applyNetworkWeights();
  byId('networkTrace')?.classList.toggle('is-stale', !!state.validation && !currentConfigMatches());
  const motionNote = document.querySelector('.network-motion-note');
  if (motionNote) motionNote.textContent = traceIsCurrent
    ? `逐層查看第一驗證折樣本的實際計算；節點顏色依 activation 值映射。`
    : '架構預覽。完成 MLP 訓練後，可檢視第一個驗證樣本的實際前向數值。';
  renderNetworkStage();
}
function setPlaygroundLayerCount(count, persist = true) {
  const next = Math.max(1, Math.min(4, count));
  if (currentModel() === 'mlp') {
    [1, 2, 3, 4].forEach((index) => { byId(`hiddenSize${index}`).disabled = index > next; });
  } else {
    byId('hiddenLayers').value = String(next);
  }
  renderArchitecture();
  if (persist) { invalidateIfEdited(); saveDraftConfig(); }
}
function resetNetworkMotion() {
  clearTimeout(networkMotion.timer); networkMotion.timer = null; networkMotion.step = -1; networkMotion.playing = false; networkMotion.training = false;
  clearTimeout(networkMotion.trainingTimer); networkMotion.trainingTimer = null;
  const diagram = byId('networkDiagram');
  diagram?.querySelectorAll('.network-node').forEach((node) => node.classList.remove('is-active', 'is-reached'));
  diagram?.querySelectorAll('.network-connection').forEach((line) => line.classList.remove('is-flowing', 'is-traversed'));
  document.querySelectorAll('#featureChoices .feature-option.is-broadcasting').forEach((option) => option.classList.remove('is-broadcasting'));
  if (diagram) delete diagram.dataset.motionStep;
  const status = byId('networkMotionStatus');
  if (status) status.textContent = '點節點看計算，點連線看權重';
  if (byId('playNetwork')) { byId('playNetwork').disabled = false; byId('playNetwork').querySelector('span').textContent = '播放'; }
  if (byId('pauseNetwork')) byId('pauseNetwork').disabled = true;
  if (byId('stepNetwork')) byId('stepNetwork').disabled = false;
}
function networkStageText(step) {
  const diagram = byId('networkDiagram'), total = Number(diagram?.dataset.layerCount || 0), kind = currentModel();
  const trace = state.forwardTrace, traced = trace && kind === 'mlp' && currentConfigMatches();
  if (step === 0) return `第 1 / ${total} 層｜輸入 ${byId('lookback').value} 個交易日 × ${selectedFeatures().length} 項特徵`;
  if (step === total - 1) return `第 ${total} / ${total} 層｜輸出未來 ${byId('horizon').value} 日報酬率 ŷ（漲跌幅）`;
  if (traced) return `第 ${step + 1} / ${total} 層｜已訓練 MLP 的第 ${step} 個隱藏層 activation`;
  const names = { mlp: '加權總和 → ReLU', rnn: '循環狀態更新', lstm: '輸入、遺忘與輸出閘門', gru: '更新閘門與重設閘門', tcn: '因果卷積擷取過去時間片段' };
  return `第 ${step + 1} / ${total} 層｜${names[kind]} · ${kind === 'tcn' ? '16 個通道' : `${byId('hiddenSize1').value} 維狀態`}`;
}
function networkStageEquation(step) {
  const diagram = byId('networkDiagram'), total = Number(diagram?.dataset.layerCount || 0), kind = currentModel();
  if (step === 0) return `輸入 x：${byId('lookback').value} 日 × ${selectedFeatures().length} 項特徵；隱藏層：z⁽¹⁾ = W⁽¹⁾a⁽⁰⁾ + b⁽¹⁾；a⁽¹⁾ = ReLU(z⁽¹⁾)`;
  if (step === total - 1) return `輸出 ŷ：最後一層將隱藏表示轉成未來 ${byId('horizon').value} 日報酬率`;
  if (kind === 'mlp') return `第 ${step + 1} 層：z⁽${step}⁾ = W⁽${step}⁾a⁽${step - 1}⁾ + b⁽${step}⁾；a⁽${step}⁾ = ReLU(z⁽${step}⁾)`;
  if (kind === 'lstm') return 'LSTM：iₜ,fₜ,oₜ = σ(閘門輸入)；cₜ = fₜ⊙cₜ₋₁ + iₜ⊙c̃ₜ；hₜ = oₜ⊙tanh(cₜ)';
  if (kind === 'gru') return 'GRU：zₜ,rₜ = σ(閘門輸入)；h̃ₜ = tanh(Wₓxₜ + Wₕ(rₜ⊙hₜ₋₁))；hₜ = (1−zₜ)⊙hₜ₋₁ + zₜ⊙h̃ₜ';
  if (kind === 'tcn') return 'TCN：左側補零的因果卷積；兩個殘差區塊 (kernel=3, dilation=1→2)，輸出只讀最後時間位置。';
  return 'RNN：hₜ = tanh(Wₓxₜ + Wₕhₜ₋₁ + b)';
}
function activateNetworkStage(step, animate = false) {
  const diagram = byId('networkDiagram'), total = Number(diagram?.dataset.layerCount || 0);
  if (!diagram || !total) return;
  networkMotion.step = Math.max(0, Math.min(step, total - 1));
  diagram.dataset.motionStep = String(networkMotion.step);
  diagram.querySelectorAll('.network-node').forEach((node) => {
    const layer = Number(node.dataset.layer);
    node.classList.toggle('is-reached', layer > 0 && layer < networkMotion.step);
    node.classList.toggle('is-active', layer === networkMotion.step);
    node.style.fillOpacity = '';
    node.removeAttribute('aria-label');
    node.querySelector('title')?.remove();
    const trace = state.forwardTrace;
    if (!trace || currentModel() !== 'mlp' || !currentConfigMatches() || layer !== networkMotion.step) return;
    const hidden = (trace.layers || []).filter((item) => item.type === 'ReLU');
    const activations = layer === 0 ? trace.input : layer === total - 1 ? [trace.prediction] : hidden[layer - 1]?.values;
    const value = activations?.[Number(node.dataset.neuron)];
    if (value == null) return;
    const max = Math.max(1e-9, ...activations.map((item) => Math.abs(item)));
    node.style.fillOpacity = String(0.25 + 0.75 * Math.min(1, Math.abs(value) / max));
    const tip = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    tip.textContent = `神經元 ${Number(node.dataset.neuron) + 1}：${Number(value).toFixed(5)}`;
    node.append(tip);
  });
  document.querySelectorAll('#featureChoices .feature-option').forEach((option) => {
    option.classList.toggle('is-broadcasting', networkMotion.step === 0 && !!option.querySelector('input')?.checked);
  });
  diagram.querySelectorAll('.network-connection').forEach((line) => {
    const layer = Number(line.dataset.layer);
    line.classList.toggle('is-traversed', layer < networkMotion.step);
    line.classList.toggle('is-flowing', animate && layer === networkMotion.step - 1 && line.classList.contains('network-sample-path'));
  });
  byId('networkMotionStatus').textContent = networkStageText(networkMotion.step);
  const equation = byId('networkStageEquation');
  if (equation) equation.textContent = networkStageEquation(networkMotion.step);
  renderNetworkStage();
}
function applyNetworkWeights() {
  const trace = state.forwardTrace, validTrace = trace && currentModel() === 'mlp' && currentConfigMatches();
  byId('networkDiagram')?.querySelectorAll('.network-connection').forEach((line) => {
    line.style.stroke = ''; line.style.strokeWidth = ''; line.style.opacity = '';
    line.querySelector('title')?.remove();
    if (!validTrace) return;
    const matrix = trace.weights?.[Number(line.dataset.layer)]?.values;
    const weight = matrix?.[Number(line.dataset.targetNeuron)]?.[Number(line.dataset.sourceNeuron)];
    if (!Number.isFinite(weight)) return;
    const max = Math.max(1e-9, ...matrix.flat().map((value) => Math.abs(value)));
    line.style.stroke = weight >= 0 ? '#2683c6' : '#e58b2b';
    line.style.strokeWidth = String(0.55 + 1.2 * Math.abs(weight) / max);
    line.style.opacity = String(0.22 + 0.72 * Math.abs(weight) / max);
    const tip = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    tip.textContent = `權重 ${weight >= 0 ? '+' : ''}${weight.toFixed(5)}`; line.append(tip);
  });
}
function playNetworkMotion() {
  const total = Number(byId('networkDiagram').dataset.layerCount || 0);
  if (!total) return;
  if (networkMotion.step >= total - 1) resetNetworkMotion();
  if (networkMotion.step < 0) activateNetworkStage(0, false);
  networkMotion.playing = true;
  byId('playNetwork').querySelector('span').textContent = '播放中';
  byId('pauseNetwork').disabled = false; byId('stepNetwork').disabled = true;
  const advance = () => {
    if (!networkMotion.playing) return;
    if (networkMotion.step >= total - 1) {
      networkMotion.playing = false; byId('playNetwork').querySelector('span').textContent = '重播';
      byId('pauseNetwork').disabled = true; byId('stepNetwork').disabled = false;
      byId('networkMotionStatus').textContent = '前向傳播完成｜模型輸出下一期報酬率預測'; return;
    }
    activateNetworkStage(networkMotion.step + 1, networkMotion.step >= 0);
    const delay = (matchMedia('(prefers-reduced-motion: reduce)').matches ? 90 : 820) / networkMotion.speed;
    networkMotion.timer = setTimeout(advance, delay);
  };
  advance();
}
function pauseNetworkMotion() {
  clearTimeout(networkMotion.timer); networkMotion.timer = null; networkMotion.playing = false;
  byId('networkDiagram').querySelectorAll('.is-flowing').forEach((line) => { line.classList.remove('is-flowing'); line.classList.add('is-traversed'); });
  byId('playNetwork').querySelector('span').textContent = '繼續';
  byId('pauseNetwork').disabled = true; byId('stepNetwork').disabled = false;
  byId('networkMotionStatus').textContent = networkMotion.step >= 0 ? `已暫停｜${networkStageText(networkMotion.step)}` : '動畫已暫停';
}
function stepNetworkMotion() {
  if (networkMotion.playing) pauseNetworkMotion();
  const total = Number(byId('networkDiagram').dataset.layerCount || 0);
  if (networkMotion.step >= total - 1) resetNetworkMotion();
  activateNetworkStage(networkMotion.step + 1, false);
  byId('playNetwork').querySelector('span').textContent = '繼續';
}
function initNetworkMotion() {
  byId('playNetwork').addEventListener('click', playNetworkMotion);
  byId('pauseNetwork').addEventListener('click', pauseNetworkMotion);
  byId('stepNetwork').addEventListener('click', stepNetworkMotion);
  byId('replayNetwork').addEventListener('click', () => { resetNetworkMotion(); activateNetworkStage(0, false); byId('playNetwork').querySelector('span').textContent = '從輸入播放'; });
  byId('networkSpeed').addEventListener('change', (event) => { networkMotion.speed = Number(event.currentTarget.value) || 1; });
  byId('networkSteps').addEventListener('click', (event) => {
    const button = event.target.closest('.network-step');
    if (!button) return;
    if (networkMotion.playing) pauseNetworkMotion();
    activateNetworkStage(Number(button.dataset.step), false);
    byId('playNetwork').querySelector('span').textContent = '從此步播放';
  });
  const diagram = byId('networkDiagram');
  const paintedEdge = (edge) => [...diagram.querySelectorAll('.network-connection')].find(line => line.dataset.layer === edge.dataset.layer && line.dataset.sourceNeuron === edge.dataset.sourceNeuron && line.dataset.targetNeuron === edge.dataset.targetNeuron);
  diagram.addEventListener('click', (event) => {
    const line = event.target.closest('.network-edge-hit');
    if (line) {
      const trace = networkTraceCurrent();
      const weight = trace ? state.forwardTrace.weights?.[Number(line.dataset.layer)]?.values?.[Number(line.dataset.targetNeuron)]?.[Number(line.dataset.sourceNeuron)] : null;
      paintedEdge(line)?.classList.add('is-hovered-edge');
      byId('networkMotionStatus').textContent = Number.isFinite(weight)
        ? `權重 w${Number(line.dataset.targetNeuron) + 1},${Number(line.dataset.sourceNeuron) + 1} = ${weight >= 0 ? '+' : ''}${weight.toFixed(5)}；${weight >= 0 ? '同向影響' : '反向影響'}`
        : '目前是架構預覽；完成 MLP 驗證訓練後，這裡會顯示本次學得的真實權重。';
      return;
    }
    const node = event.target.closest('.network-node,.network-node-hit');
    if (!node) return;
    if (networkMotion.playing) pauseNetworkMotion();
    networkMotion.neuron = Number(node.dataset.neuron);
    activateNetworkStage(Number(node.dataset.layer), false);
  });
  diagram.addEventListener('pointerover', (event) => {
    const line = event.target.closest('.network-edge-hit');
    if (!line || line.contains(event.relatedTarget)) return;
    const trace = networkTraceCurrent();
    const weight = trace ? state.forwardTrace.weights?.[Number(line.dataset.layer)]?.values?.[Number(line.dataset.targetNeuron)]?.[Number(line.dataset.sourceNeuron)] : null;
    paintedEdge(line)?.classList.add('is-hovered-edge');
    if (Number.isFinite(weight)) byId('networkMotionStatus').textContent = `連線權重 ${weight >= 0 ? '+' : ''}${weight.toFixed(5)}；正值同向，負值反向影響。`;
  });
  diagram.addEventListener('pointerout', (event) => {
    const line = event.target.closest('.network-edge-hit');
    if (!line || line.contains(event.relatedTarget)) return;
    paintedEdge(line)?.classList.remove('is-hovered-edge');
    if (event.pointerType !== 'touch') byId('networkMotionStatus').textContent = '點節點看計算，點連線看權重';
  });
  diagram.addEventListener('keydown', (event) => {
    if (event.target.closest('.network-node') && ['Enter', ' '].includes(event.key)) { event.preventDefault(); event.target.closest('.network-node').dispatchEvent(new MouseEvent('click', { bubbles: true })); return; }
    if (event.key === 'ArrowRight') { event.preventDefault(); if (networkMotion.step >= Number(diagram.dataset.layerCount || 0) - 1) networkMotion.step = -1; stepNetworkMotion(); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); if (networkMotion.playing) pauseNetworkMotion(); networkMotion.step = Math.max(0, networkMotion.step - 1); activateNetworkStage(networkMotion.step, false); }
    else if (event.key === ' ') { event.preventDefault(); networkMotion.playing ? pauseNetworkMotion() : playNetworkMotion(); }
  });
  if ('IntersectionObserver' in window) {
    networkMotion.observer?.disconnect();
    networkMotion.observer = new IntersectionObserver(([entry]) => { if (!entry.isIntersecting && networkMotion.playing) pauseNetworkMotion(); }, { threshold: 0.05 });
    networkMotion.observer.observe(byId('network'));
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden && networkMotion.playing) pauseNetworkMotion(); });
}
function currentConfigMatches() {
  if (!state.validation || !state.validationConfig) return false;
  const current = buildConfig(), previous = { ...state.validationConfig };
  delete current.buyThreshold; delete current.sellThreshold;
  delete previous.buyThreshold; delete previous.sellThreshold;
  return JSON.stringify(current) === JSON.stringify(previous);
}
function invalidateIfEdited() {
  err();
  renderArchitecture();
  const stale = !!state.validation && !currentConfigMatches();
  byId('networkTrace')?.classList.toggle('is-stale', stale);
  let traceStaleNote = byId('networkTrace')?.querySelector('.trace-stale-note');
  if (stale && !traceStaleNote) {
    traceStaleNote = document.createElement('p'); traceStaleNote.className = 'trace-stale-note';
    traceStaleNote.textContent = '目前參數已變更；以下數值屬於上一次訓練，重新訓練後才會更新。'; byId('networkTrace')?.append(traceStaleNote);
  } else if (!stale) traceStaleNote?.remove();
  const hasDiagnosticData = state.validation?.models?.some((model) => model.folds?.some((fold) => (fold.predictions || []).length > 0));
  byId('diagnosticsStatus').textContent = stale
    ? '設定已變更；診斷仍對應舊驗證結果，重新訓練後更新。'
    : state.validation && hasDiagnosticData ? '目前驗證集 out-of-fold 預測'
      : state.validation ? '舊的已存結果沒有逐筆預測；重新訓練後可產生診斷圖'
        : '完成訓練後可查看 out-of-fold 預測診斷';
  byId('results').dataset.status = stale ? 'stale' : state.validation ? 'complete' : 'empty';
  byId('validationStale').hidden = !stale;
  if (stale) {
    byId('runFinal').disabled = true;
    byId('finalStatus').textContent = '設定已變更，請重新訓練；舊驗證分數不再適用。';
  } else if (state.validation) {
    const enoughTraining = Number(buildConfig().epochs) >= 20;
    byId('runFinal').disabled = state.finalUsed || !enoughTraining || !currentConfigMatches();
    byId('finalStatus').textContent = state.finalUsed
      ? '鎖定測試已使用；這段測試資料不可重跑。'
      : !enoughTraining ? '目前訓練少於 20 Epoch，可供開發驗證；不得消耗正式鎖定測試。'
        : `${state.validation.models?.[0]?.name || '模型'} 已完成驗證 · ${formatInt(state.validation.validationSamples)} 筆；設定凍結後可執行一次鎖定測試。`;
  }
}
function setBusy(busy, message = '') {
  byId('runValidation').disabled = busy;
  byId('topTrain').disabled = busy;
  if (byId('footerTrain')) byId('footerTrain').disabled = busy;
  if (byId('footerCancel')) { byId('footerCancel').hidden = !busy; byId('footerCancel').disabled = !busy; }
  if (byId('footerReset')) byId('footerReset').disabled = busy;
  byId('refreshData').disabled = busy;
  if (byId('staleTrain')) byId('staleTrain').disabled = busy;
  byId('runFinal').disabled = busy || state.finalUsed || !currentConfigMatches();
  byId('cancelJob').disabled = !busy;
  for (const id of ['playNetwork', 'stepNetwork', 'replayNetwork', 'networkSpeed']) {
    const control = byId(id);
    if (control) control.disabled = busy;
  }
  if (busy && byId('pauseNetwork')) byId('pauseNetwork').disabled = true;
  if (message) byId('jobMessage').textContent = message;
  if (!busy) {
    byId('progressFill').style.width = '0%'; byId('jobPercent').textContent = '0%';
    byId('jobMessage').textContent = '設定完成後可開始訓練'; byId('jobMessage').title = '設定完成後可開始訓練';
    byId('jobMessage').setAttribute('aria-label', '設定完成後可開始訓練');
  }
}
function updateProgress(job) {
  const percent = Math.max(0, Math.min(100, Number(job.progress) || 0));
  const isRunning = ['queued', 'running'].includes(job.status);
  const epochMatch = String(job.message || '').match(/epoch\s+(\d+)\s*\/\s*(\d+)/i);
  const epoch = Number(job.currentEpoch ?? job.epoch ?? job.metrics?.epoch ?? epochMatch?.[1] ?? 0);
  const epochs = Number(job.totalEpochs ?? job.epochs ?? epochMatch?.[2] ?? buildConfig().epochs);
  const foldMatch = String(job.message || '').match(/(?:fold|折)\s*(\d+)\s*\/\s*(\d+)/i);
  const fold = Number(job.currentFold ?? job.fold ?? foldMatch?.[1] ?? 0);
  const folds = Number(job.totalFolds ?? job.folds ?? foldMatch?.[2] ?? 0);
  const phase = job.status === 'queued' ? '等待工作佇列' : job.status === 'completed' ? '驗證完成 · 結果已更新'
    : job.status === 'cancelled' ? '訓練已取消' : job.status === 'failed' ? '訓練失敗 · 查看錯誤訊息'
      : fold && folds ? `第 ${fold}/${folds} 折 · 第 ${epoch || 0}/${epochs} 回合`
        : epoch ? `模型訓練中 · 第 ${epoch}/${epochs} 回合`
          : `模型訓練中 · ${percent}%`;
  // Keep the footer label stable in width; detailed phase remains available via title/ARIA.
  byId('jobMessage').textContent = isRunning ? phase : phase;
  byId('jobMessage').title = phase;
  byId('jobMessage').setAttribute('aria-label', phase);
  byId('jobPercent').textContent = `${percent}%`;
  byId('progressFill').style.width = `${percent}%`;
  if (isRunning) {
    startNetworkTrainingMotion(epoch, epochs);
    byId('toolbarEpoch').textContent = `${epoch || '…'}/${epochs || buildConfig().epochs}`;
  } else if (networkMotion.training) {
    stopNetworkTrainingMotion();
  }
}
function startNetworkTrainingMotion(epoch = 0, epochs = 0) {
  const diagram = byId('networkDiagram');
  const total = Number(diagram?.dataset.layerCount || 0);
  if (!total) return;
  networkMotion.trainingEpoch = Number.isFinite(epoch) ? epoch : 0;
  networkMotion.trainingEpochs = Number.isFinite(epochs) ? epochs : 0;
  networkMotion.training = true;
  byId('network')?.classList.add('training-motion');
  if (networkMotion.trainingTimer) return;
  const advance = () => {
    networkMotion.trainingTimer = null;
    if (!networkMotion.training) return;
    const next = networkMotion.step < 0 || networkMotion.step >= total - 1 ? 0 : networkMotion.step + 1;
    activateNetworkStage(next, networkMotion.step >= 0);
    networkMotion.trainingTimer = setTimeout(advance, 820 / networkMotion.speed);
  };
  advance();
}
function stopNetworkTrainingMotion() {
  networkMotion.training = false;
  networkMotion.playing = false;
  clearTimeout(networkMotion.timer); networkMotion.timer = null;
  clearTimeout(networkMotion.trainingTimer); networkMotion.trainingTimer = null;
  byId('network')?.classList.remove('training-motion');
  byId('toolbarEpoch').textContent = String(buildConfig().epochs).padStart(3, '0');
  // Preserve the selected network stage. Training progress remains in the fixed footer.
}
async function startJob(final = false) {
  err();
  if (state.activeJobId || state.submitting) return;
  const invalidControl = [...document.querySelectorAll('#advancedMenu input, #advancedMenu select')].find((control) => !control.checkValidity());
  if (invalidControl) { invalidControl.reportValidity(); invalidControl.focus(); return err('請先修正標示的參數，再開始訓練。'); }
  const payload = buildConfig();
  if (!payload.features.length) return err('請至少選一個輸入特徵。');
  if (!final && !payload.modelTypes.length) return err('請選擇神經網路架構。');
  if (final && !currentConfigMatches()) return err('設定已變更，請先重新訓練並完成驗證。');
  if (final) payload.modelTypes = [currentModel()];
  state.submitting = true;
  if (networkMotion.playing) pauseNetworkMotion();
  clearTimeout(networkMotion.timer); networkMotion.timer = null;
  startNetworkTrainingMotion(0, Number(payload.epochs) || 0);
  byId('toolbarEpoch').textContent = `0/${payload.epochs}`;
  setBusy(true, final ? '正在送出鎖定測試工作…' : '正在送出訓練工作…');
  try {
    const response = await api(final ? '/api/final-evaluation' : '/api/experiments', { method: 'POST', body: JSON.stringify(payload) });
    state.submitting = false;
    state.activeJobId = response.jobId;
    if (final) { state.finalUsed = true; byId('finalStatus').textContent = '鎖定測試執行中…'; }
    setBusy(true, final ? '正在執行鎖定測試…' : '模型訓練與 expanding walk-forward 驗證中…');
    await pollJob(response.jobId, JSON.stringify(payload), final);
  } catch (error) {
    state.submitting = false;
    if (final) state.finalUsed = false;
    if (!final && error.status === 409) {
      try {
        const active = await api('/api/jobs/active');
        if (active) { updateJobFromExisting(active); return; }
      } catch (_) {}
    }
    stopNetworkTrainingMotion(); err(error.message); setBusy(false);
  }
}
async function pollJob(id, configKey, final) {
  clearTimeout(state.pollTimer);
  try {
    const job = await api(`/api/jobs/${id}`); updateProgress(job);
    if (['queued', 'running'].includes(job.status)) { state.pollTimer = setTimeout(() => pollJob(id, configKey, final), 900); return; }
    state.activeJobId = null; setBusy(false);
    if (job.status === 'completed') {
      if (final) { state.finalUsed = true; renderFinal(job.result, false, job.config); await refreshLockStatus(); toast('鎖定測試完成，測試集不再用於調整設定。'); }
      else { state.validation = job.result; state.validationConfig = JSON.parse(configKey); renderValidation(job.result); recordValidationRun(job.result, state.validationConfig); toast('訓練與時間序列驗證完成。'); }
      byId('progressFill').style.width = '100%'; byId('jobPercent').textContent = '100%';
      byId('jobMessage').textContent = '驗證完成 · 結果已更新'; byId('jobMessage').title = '驗證完成 · 結果已更新';
    } else {
      if (final) { state.finalUsed = false; await refreshLockStatus(); }
      if (job.status === 'failed') err(job.error || '模型工作失敗，請檢查設定後重試。');
      else toast('訓練工作已取消。');
    }
  } catch (error) {
    if (error.status === 404) {
      state.activeJobId = null; stopNetworkTrainingMotion(); setBusy(false); err('本機服務已重新啟動，這次工作中斷了。確認設定後可重新訓練。'); return;
    }
    byId('jobMessage').textContent = '連線暫時中斷，正在重新連線查看訓練狀態…';
    state.pollTimer = setTimeout(() => pollJob(id, configKey, final), 1800);
  }
}
async function cancelJob() {
  if (!state.activeJobId) return;
  byId('cancelJob').disabled = true;
  if (byId('footerCancel')) byId('footerCancel').disabled = true;
  try {
    await api(`/api/jobs/${state.activeJobId}/cancel`, { method: 'POST', body: '{}' });
    byId('jobMessage').textContent = '正在停止模型工作…';
  } catch (error) {
    err(error.message); byId('cancelJob').disabled = false;
    if (byId('footerCancel')) byId('footerCancel').disabled = false;
  }
}

function renderValidation(result) {
  const model = result.models[0]; if (!model) return;
  state.validation = result;
  // Reveal the result panels before measuring their SVG widths.
  byId('results').dataset.status = 'complete';
  renderForwardTrace(result.forwardTrace);
  renderPlaygroundOutput();
  document.querySelector('.status-pill').textContent = '驗證完成';
  byId('lossEmpty').hidden = true; byId('comparisonEmpty').hidden = true;
  byId('metricMae').textContent = pct(model.mae);
  byId('metricRmse').textContent = pct(model.rmse);
  byId('metricR2').textContent = Number(model.r2).toFixed(3);
  byId('metricSpearman').textContent = Number(model.spearman).toFixed(3);
  byId('metricDirection').textContent = pct(model.directionAccuracy, 1);
  const directionRows = (model.folds || []).flatMap((fold) => fold.predictions || []);
  const directionSummary = directionMixSummary(directionRows);
  if (directionSummary) {
    byId('directionMix').textContent = directionSummary;
  } else {
    byId('directionMix').textContent = '這份舊結果沒有逐筆驗證預測，無法計算漲跌比例；重新訓練後可查看。';
  }
  renderLossChart(model); renderComparison(result.comparisons || []); renderDiagnostics(model); renderSignals(result);
  const diagnosticSelect = byId('diagnosticsModel');
  diagnosticSelect.innerHTML = result.models.map((item) => `<option value="${item.key}">${item.name}</option>`).join('');
  byId('diagnosticsModelField').hidden = result.models.length < 2;
  diagnosticSelect.value = model.key;
  diagnosticSelect.onchange = () => renderDiagnostics(result.models.find((item) => item.key === diagnosticSelect.value) || result.models[0]);
  const hasFoldPredictions = model.folds?.some((fold) => (fold.predictions || []).length > 0);
  byId('diagnosticsStatus').textContent = hasFoldPredictions
    ? '目前驗證集 out-of-fold 預測'
    : '舊的已存結果沒有逐筆預測；重新訓練後可產生診斷圖';
  // Keep the user's viewport steady. Diagnostics remain collapsed until opened.
  byId('finalStatus').textContent = `${model.name} 已完成驗證 · ${formatInt(result.validationSamples)} 筆；可執行一次鎖定測試。`;
  byId('runFinal').disabled = state.finalUsed || !currentConfigMatches();
  byId('jobMessage').textContent = `${model.name} 驗證完成 · ${result.folds} 個時間折`;
  byId('validationStale').hidden = true;
}
function renderForwardTrace(trace) {
  const panel = byId('networkTrace');
  if (!panel) return;
  state.forwardTrace = trace || null;
  applyNetworkWeights();
  renderNetworkStage();
  if (!trace || trace.model !== 'mlp') {
    panel.hidden = false;
    panel.innerHTML = '<strong>逐層數值檢視</strong><p>目前結果沒有 MLP 前向計算軌跡。選擇 MLP 並重新訓練後，這裡會顯示真實驗證樣本的輸入、隱藏層 activation 與輸出。</p>';
    return;
  }
  const hidden = (trace.layers || []).filter((layer) => layer.type === 'ReLU');
  const values = (items, limit = 6) => items.slice(0, limit).map((value, index) => `<span><small>${index + 1}</small>${Number(value).toFixed(3)}</span>`).join('');
  const predictionValue = trace.returnType === 'log' ? Math.expm1(trace.prediction) : trace.prediction;
  const actualValue = trace.actual == null ? null : trace.returnType === 'log' ? Math.expm1(trace.actual) : trace.actual;
  panel.innerHTML = `<div class="trace-heading"><div><strong>單筆前向計算</strong><span>${trace.originDate} → ${trace.sampleDate} · walk-forward 第 ${trace.fold} 折驗證樣本</span></div><span class="trace-proof">PyTorch 實際權重</span></div><p class="trace-caption">輸入為只用訓練折標準化的模型張量；節點明度呈現 activation，連線顏色代表權重正負、粗細代表相對大小。以下數列是實際計算值。</p><div class="trace-columns"><section><h3>輸入向量 <small>${trace.inputShape.join(' × ')} · 顯示前 6 維</small></h3><div class="trace-values">${values(trace.input, 6)}</div></section>${hidden.map((layer, index) => `<section><h3>隱藏層 ${index + 1} · ReLU <small>${layer.values.length} 個節點 · 顯示前 6 個</small></h3><div class="trace-values">${values(layer.values, 6)}</div></section>`).join('')}<section class="trace-output"><h3>模型輸出 <small>回歸預測</small></h3><div class="trace-prediction"><span>預測報酬</span><strong>${pct(predictionValue, 4)}</strong><span>實際報酬</span><b>${actualValue == null ? '—' : pct(actualValue, 4)}</b></div></section></div>`;
}
function renderLossChart(model) {
  const svg = byId('lossChart'), train = model.meanTrainLoss || [], valid = model.meanValidationLoss || [];
  if (!train.length) return;
  const W = 660, H = 250, L = 66, R = 18, T = 20, B = 38, values = [...train, ...valid].filter((v) => v > 0);
  const logs = values.map((v) => Math.log10(v)), dataMin = Math.min(...logs), dataMax = Math.max(...logs);
  const range = Math.max(dataMax - dataMin, 0.12), min = dataMin - range * .08, max = dataMax + range * .08;
  const y = (v) => T + (max - Math.log10(Math.max(v, 1e-12))) / (max - min) * (H - T - B);
  const x = (i, n) => L + i / Math.max(1, n - 1) * (W - L - R);
  const ticks = 4, tickLogs = Array.from({length:ticks}, (_,i)=>max-(max-min)*i/(ticks-1));
  const grid = tickLogs.map((logValue,i)=>{const yy=T+(H-T-B)*i/(ticks-1), v=10**logValue; return `<line class="chart-grid" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/><text class="chart-axis" x="${L-9}" y="${yy+4}" text-anchor="end">${v.toExponential(1)}</text>`}).join('');
  const points = (curve) => curve.map((v,i)=>`${x(i,curve.length)},${y(v)}`).join(' ');
  const count=Math.min(train.length,valid.length),cursorX=(i)=>x(i,count);
  svg.innerHTML = `${grid}<rect class="loss-hit-area" x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}"/><polyline class="loss-train-line" points="${points(train)}"/><polyline class="loss-valid-line" points="${points(valid)}"/><line id="lossCursor" class="loss-cursor" x1="${L}" x2="${L}" y1="${T}" y2="${H-B}"/><circle id="lossTrainPoint" class="loss-point train-point" cx="${L}" cy="${y(train[0])}" r="4"/><circle id="lossValidPoint" class="loss-point valid-point" cx="${L}" cy="${y(valid[0])}" r="4"/><text class="chart-axis" x="${L}" y="${H-8}">1</text><text class="chart-axis" x="${W-R}" y="${H-8}" text-anchor="end">${train.length} Epoch</text>`;
  const wrap=svg.closest('.loss-chart-wrap'),tooltip=byId('lossTooltip');
  const showAt=(index,event)=>{
    const i=Math.max(0,Math.min(count-1,index)),cx=cursorX(i),cursor=byId('lossCursor');
    svg.dataset.epoch=String(i);
    cursor.setAttribute('x1',cx);cursor.setAttribute('x2',cx);
    byId('lossTrainPoint').setAttribute('cx',cx);byId('lossTrainPoint').setAttribute('cy',y(train[i]));
    byId('lossValidPoint').setAttribute('cx',cx);byId('lossValidPoint').setAttribute('cy',y(valid[i]));
    tooltip.innerHTML=`<strong>Epoch ${i+1}</strong><span><i class="train-dot"></i>Train　${Number(train[i]).toExponential(4)}</span><span><i class="valid-dot"></i>Validation　${Number(valid[i]).toExponential(4)}</span>`;
    tooltip.hidden=false;
    const rect=wrap.getBoundingClientRect(), svgRect=svg.getBoundingClientRect();
    const screenX=svgRect.left+(cx/W)*svgRect.width;
    tooltip.style.left=`${Math.max(6,Math.min(rect.width-166,screenX-rect.left+10))}px`;
    tooltip.style.top=`${Math.max(4,Math.min(rect.height-72,(event?.clientY ?? svgRect.top+T/H*svgRect.height)-rect.top-24))}px`;
  };
  svg.onpointermove=(event)=>{if(event.pointerType==='touch')return;const rect=svg.getBoundingClientRect();const localX=(event.clientX-rect.left)/Math.max(1,rect.width)*W;const plotX=Math.max(L,Math.min(W-R,localX));const i=Math.round((plotX-L)/Math.max(1,W-L-R)*(count-1));showAt(i,event);};
  svg.onpointerleave=()=>{tooltip.hidden=true;};
  svg.onfocus=()=>showAt(0);
  svg.onkeydown=(event)=>{if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();const current=Number(svg.dataset.epoch||0)+(event.key==='ArrowRight'?1:-1);const next=Math.max(0,Math.min(count-1,current));svg.dataset.epoch=String(next);showAt(next);}else if(event.key==='Escape')tooltip.hidden=true;};
  svg.setAttribute('aria-describedby','lossTooltip');
  byId('lossLegend').innerHTML = '<span><i class="legend-train-line"></i>訓練損失（Train）</span><span><i class="legend-valid-line"></i>驗證損失（Validation）</span>';
}
function readRunHistory(){
  // Browser storage can be disabled or throw in private/restricted contexts; history stays optional.
  try{const value=JSON.parse(localStorage.getItem(RUN_HISTORY_KEY)||'[]');return Array.isArray(value)?value.filter(isValidRunHistoryRecord):[];}catch(_){return[];}
}
function renderRunHistory(){
  const rows=readRunHistory().filter(isValidRunHistoryRecord),body=byId('runHistoryRows');if(!body)return;
  const emptyState=byId('runHistoryEmpty');if(emptyState)emptyState.hidden=rows.length>0;
  const exportButton=byId('exportRunHistory');if(exportButton)exportButton.disabled=buildRunHistoryArchive(rows).runCount===0;
  body.replaceChildren();
  rows.forEach((run,index)=>{
    const config=run.config&&typeof run.config==='object'&&!Array.isArray(run.config)?run.config:{};
    const models=Array.isArray(run.models)?run.models.filter(item=>item&&typeof item==='object'&&!Array.isArray(item)):[];
    const m=models[0]||{},modelNames=models.map(item=>item.name||MODEL_LABELS[item.key]||item.key).filter(value=>typeof value==='string').join('、');
    const stamp=new Date(run.createdAt),tr=document.createElement('tr');body.append(tr);
    const timeCell=tr.insertCell();timeCell.textContent=Number.isNaN(stamp.getTime())?'時間未知':stamp.toLocaleString('zh-TW',{hour12:false});
    const configCell=tr.insertCell(),modelName=document.createElement('strong'),detail=document.createElement('small');
    modelName.textContent=modelNames||'—';detail.textContent=`${config.horizon||'—'} 日 · 回看 ${config.lookback||'—'} 日 · ${run.samples||'—'} 筆`;configCell.append(modelName,detail);
    for(const value of [m.mae==null?'—':pct(m.mae),m.rmse==null?'—':pct(m.rmse),m.r2==null?'—':Number(m.r2).toFixed(3)]){const cell=tr.insertCell();cell.textContent=value;}
    const actionCell=tr.insertCell(),button=document.createElement('button');button.className='history-apply';button.type='button';button.dataset.runIndex=String(index);button.textContent='套用設定';actionCell.append(button);
  });
}
function recordValidationRun(result,config){
  const savedConfig={...config,modelType:config.modelTypes?.[0],compareModels:config.modelTypes?.slice(1)||[]};
  const record={id:`${Date.now()}-${Math.random().toString(36).slice(2,7)}`,createdAt:new Date().toISOString(),config:savedConfig,samples:result.validationSamples,datasetHash:state.status?.sha256||null,models:(result.models||[]).map(m=>({key:m.key,name:m.name,mae:m.mae,rmse:m.rmse,r2:m.r2,spearman:m.spearman,directionAccuracy:m.directionAccuracy,folds:m.folds?.map(f=>({fold:f.fold,from:f.from,to:f.to,mae:f.mae,rmse:f.rmse}))||[]}))};
  try{const rows=[record,...readRunHistory()].slice(0,MAX_RUN_HISTORY);localStorage.setItem(RUN_HISTORY_KEY,JSON.stringify(rows));renderRunHistory();}catch(_){toast('訓練完成；瀏覽器儲存空間不足，未能新增實驗歷程。');}
}
function openFinalConfirmation(){
  if(!currentConfigMatches()||state.finalUsed||state.activeJobId)return;
  const dialog=byId('finalConfirmDialog'),config=buildConfig();
  byId('finalConfirmModel').textContent=MODEL_LABELS[config.modelType]||config.modelType;
  byId('finalConfirmTarget').textContent=`${config.horizon} 日後報酬率 · ${config.returnType==='log'?'對數':'簡單'}報酬`;
  byId('finalConfirmValidation').textContent=`${state.validation?.folds||'—'} 個時間折 · ${formatInt(state.validation?.validationSamples||0)} 筆驗證資料`;
  dialog.showModal();
}
function renderComparison(rows) {
  state.comparisonRows = rows || [];
  const svg = byId('comparisonChart'); if (!svg || !rows.length) return;
  const W = Math.max(360, Math.round(svg.getBoundingClientRect().width || 760));
  const L = Math.min(164, Math.max(126, Math.round(W * 0.22))), R = 54, T = 14, rowH = 40, axisH = 28;
  const H = T + rows.length * rowH + axisH, plotW = W - L - R;
  const compactLabels = W <= 420;
  const compactHint = byId('comparisonCompactHint');
  if (compactHint) {
    compactHint.hidden = !compactLabels;
    compactHint.textContent = compactLabels ? '窄螢幕使用短標籤；完整模型名稱可由圖中標籤提示讀取。' : '';
  }
  const isMetric = (value) => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const values = rows.flatMap((row) => [row.mae, row.rmse]).filter(isMetric).map((value) => Math.max(0, Number(value)));
  const max = Math.max(...values, 0.0001) * 1.12;
  const x = (value) => L + (isMetric(value) ? Math.max(0, Number(value)) : 0) / max * plotW;
  const safeText = (value) => String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('aria-label', `驗證集模型誤差比較，共 ${rows.length} 個模型；共用橫軸，單位為百分比`);
  const ticks = 4;
  const grid = Array.from({length:ticks + 1}, (_, i) => {
    const tx = L + plotW * i / ticks, value = max * i / ticks;
    return `<line class="chart-grid comparison-grid" x1="${tx}" x2="${tx}" y1="${T - 4}" y2="${T + rows.length * rowH - 3}"/><text class="chart-axis" x="${tx}" y="${H - 5}" text-anchor="middle">${(value * 100).toFixed(1)}%</text>`;
  }).join('');
  const bars = rows.map((row, i) => {
    const y = T + i * rowH, label = safeText(row.name || row.key || '模型');
    const maeX = x(row.mae), rmseX = x(row.rmse);
    const maeWidth = Math.max(0, maeX - L), rmseWidth = Math.max(0, rmseX - L);
    const maeLabel = isMetric(row.mae) ? pct(Math.max(0, Number(row.mae))) : '—';
    const rmseLabel = isMetric(row.rmse) ? pct(Math.max(0, Number(row.rmse))) : '—';
    const visibleLabel = compactLabels && label.length > 8 ? `${label.slice(0, 7).trimEnd()}…` : label;
    return `<text class="bar-label comparison-model-label${compactLabels ? ' bar-label-rotated' : ''}" x="${L - 12}" y="${y + 22}" text-anchor="end"><title>${label}</title>${visibleLabel}</text><rect class="bar-mae comparison-track" tabindex="0" role="img" aria-label="${label} MAE ${maeLabel}" x="${L}" y="${y + 4}" width="${maeWidth}" height="12" rx="3"><title>${label} · MAE ${maeLabel}</title></rect><text class="comparison-value" x="${Math.min(maeX + 7, W - R + 2)}" y="${y + 14}">${maeLabel}</text><rect class="bar-rmse comparison-track" tabindex="0" role="img" aria-label="${label} RMSE ${rmseLabel}" x="${L}" y="${y + 21}" width="${rmseWidth}" height="12" rx="3"><title>${label} · RMSE ${rmseLabel}</title></rect><text class="comparison-value" x="${Math.min(rmseX + 7, W - R + 2)}" y="${y + 31}">${rmseLabel}</text>`;
  }).join('');
  svg.innerHTML = `${grid}${bars}`;
}
function renderDiagnostics(model) {
  const folds = model.folds || [];
  const predictions = folds.flatMap((fold) => (fold.predictions || []).map((row) => ({...row, fold:fold.fold}))).sort((a,b)=>a.date.localeCompare(b.date));
  byId('diagnosticsPanel').dataset.status = predictions.length >= 2 ? 'ready' : 'legacy';
  const directionSummary = directionMixSummary(predictions);
  if (byId('directionMix')) byId('directionMix').textContent = directionSummary || '這份驗證結果沒有完整的實際／預測配對，無法比較方向分布。';
  const residualSvg = byId('residualChart'), foldSvg = byId('foldErrorChart');
  if (predictions.length < 2) {
    residualSvg.innerHTML = '<text class="diagnostics-empty" x="310" y="130">這份已存結果沒有逐筆殘差；請重新訓練以產生診斷資料。</text>';
    foldSvg.innerHTML = '<text class="diagnostics-empty" x="310" y="130">這份已存結果沒有逐折預測資料；請重新訓練以產生診斷資料。</text>';
    renderCalibration([]);
    byId('residualSummary').textContent = '逐筆診斷資料僅從本次新增的訓練結果開始保存。';
    byId('foldErrorLegend').replaceChildren(); return;
  }
  const residuals = predictions.map((row)=>{
    const residual=row.residual!==null&&row.residual!==undefined&&row.residual!==''?row.residual:(row.predicted===null||row.predicted===undefined||row.predicted===''||row.actual===null||row.actual===undefined||row.actual===''?NaN:Number(row.predicted)-Number(row.actual));
    return residual===null||residual===undefined||residual===''?NaN:Number(residual)*100;
  }).filter(Number.isFinite);
  if(!residuals.length){
    residualSvg.innerHTML='<text class="diagnostics-empty" x="310" y="130">沒有可用的有限殘差資料</text>';
    foldSvg.innerHTML='<text class="diagnostics-empty" x="310" y="130">沒有可用的有限殘差資料</text>';
    byId('residualSummary').textContent='沒有可用的有限 out-of-fold 殘差；缺值不會當成零報酬。';
    byId('foldErrorLegend').replaceChildren(); renderCalibration(predictions); return;
  }
  const mean = residuals.reduce((sum,value)=>sum+value,0)/residuals.length;
  const variance = residuals.reduce((sum,value)=>sum+(value-mean)**2,0)/Math.max(1,residuals.length-1);
  const sigma = Math.sqrt(variance), minimum = Math.min(...residuals), maximum = Math.max(...residuals);
  const binCount = Math.max(8,Math.min(32,Math.ceil(Math.sqrt(residuals.length))));
  const binWidth = (maximum-minimum || Math.max(sigma,0.01)*6)/binCount;
  const lo = minimum === maximum ? minimum-binWidth*binCount/2 : minimum;
  const hi = minimum === maximum ? maximum+binWidth*binCount/2 : maximum;
  const width = (hi-lo)/binCount, counts=Array(binCount).fill(0);
  for(const value of residuals) counts[Math.min(binCount-1,Math.floor((value-lo)/width))]++;
  const density=counts.map((count)=>count/(residuals.length*width));
  const gaussian=(x)=>sigma>0?Math.exp(-0.5*((x-mean)/sigma)**2)/(sigma*Math.sqrt(2*Math.PI)):0;
  const peak=Math.max(...density,gaussian(mean))*1.16;
  const W=620,H=260,L=47,R=15,T=14,B=40,plotW=W-L-R,plotH=H-T-B;
  const x=(value)=>L+(value-lo)/(hi-lo)*plotW, y=(value)=>T+plotH-(value/peak)*plotH;
  const grid=[0,1,2,3].map((i)=>{const yy=T+plotH*i/3,v=peak*(1-i/3);return `<line class="chart-grid" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/><text class="chart-axis" x="${L-6}" y="${yy+3}" text-anchor="end">${v.toFixed(1)}</text>`}).join('');
  const bars=counts.map((count,i)=>{const x0=x(lo+i*width),x1=x(lo+(i+1)*width),height=T+plotH-y(density[i]);return `<rect class="residual-bar" x="${x0+1}" y="${y(density[i])}" width="${Math.max(1,x1-x0-2)}" height="${height}" rx="1"><title>${(lo+(i+.5)*width).toFixed(3)} pp · ${count} 筆</title></rect>`}).join('');
  const normalPoints=Array.from({length:81},(_,i)=>{const value=lo+(hi-lo)*i/80;return `${x(value).toFixed(2)},${y(gaussian(value)).toFixed(2)}`}).join(' ');
  const xTicks=[lo,(lo+hi)/2,hi].map((v)=>`<text class="chart-axis" x="${x(v)}" y="${H-14}" text-anchor="middle">${v.toFixed(2)}</text>`).join('');
  residualSvg.innerHTML=`${grid}<line class="residual-zero" x1="${x(0)}" x2="${x(0)}" y1="${T}" y2="${T+plotH}"/><g>${bars}</g><polyline class="residual-normal" points="${normalPoints}"/><text class="chart-axis" x="${L}" y="${H-2}">殘差（百分點）</text>${xTicks}`;
  const outside=residuals.filter((value)=>sigma>0&&Math.abs(value-mean)>2*sigma).length/residuals.length*100;
  const fourth=residuals.reduce((sum,value)=>sum+((value-mean)/(sigma||1))**4,0)/residuals.length;
  const excessKurtosis=fourth-3;
  byId('residualSummary').textContent=`${residuals.length.toLocaleString()} 筆 out-of-fold 殘差 · 均值 ${mean.toFixed(3)} pp · 標準差 ${sigma.toFixed(3)} pp · ±2σ 外 ${outside.toFixed(1)}%（常態參考 4.6%）· 超額峰度 ${excessKurtosis.toFixed(2)}。此為描述統計，殘差有時間相依性。`;

  const colors=['#168f8b','#e39a3d','#527db2','#9273ad','#c66c59','#53a17b'];
  const foldResidual=(row)=>{
    const residual=row.residual!==null&&row.residual!==undefined&&row.residual!==''?row.residual:(row.predicted===null||row.predicted===undefined||row.predicted===''||row.actual===null||row.actual===undefined||row.actual===''?NaN:Number(row.predicted)-Number(row.actual));
    return residual===null||residual===undefined||residual===''?NaN:Number(residual);
  };
  const series=folds.map((fold,index)=>({fold,index,points:(fold.predictions||[]).map((row)=>({row,residual:foldResidual(row)})).filter((point)=>Number.isFinite(point.residual))})).filter((item)=>item.points.length);
  if(!series.length){foldSvg.innerHTML='<text class="diagnostics-empty" x="310" y="130">沒有可用的有限殘差資料</text>';byId('foldErrorLegend').replaceChildren();renderCalibration(predictions);return;}
  const maxMae=Math.max(...series.flatMap((item)=>item.points.map((_,i)=>item.points.slice(0,i+1).reduce((sum,point)=>sum+Math.abs(point.residual),0)/(i+1)*100)),0.01)*1.12;
  const FX=(i,n)=>L+i/Math.max(1,n-1)*plotW, FY=(value)=>T+plotH-value/maxMae*plotH;
  const fgrid=[0,1,2,3].map((i)=>{const yy=T+plotH*i/3,v=maxMae*(1-i/3);return `<line class="chart-grid" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/><text class="chart-axis" x="${L-6}" y="${yy+3}" text-anchor="end">${v.toFixed(2)}</text>`}).join('');
  const lines=series.map(({fold,index,points})=>{let cumulative=0;const stride=Math.max(1,Math.floor(points.length/120));const coords=[];for(let i=0;i<points.length;i++){cumulative+=Math.abs(points[i].residual);if(i%stride===0||i===points.length-1)coords.push(`${FX(i,points.length).toFixed(2)},${FY(cumulative/(i+1)*100).toFixed(2)}`);}return `<polyline class="fold-error-line" stroke="${colors[index%colors.length]}" points="${coords.join(' ')}"><title>第 ${fold.fold} 折 ${points[0].row.date} 至 ${points.at(-1).row.date} · 有效殘差 ${points.length} 筆</title></polyline>`}).join('');
  foldSvg.innerHTML=`${fgrid}${lines}<text class="chart-axis" x="${L}" y="${H-14}">0%</text><text class="chart-axis" x="${W-R}" y="${H-14}" text-anchor="end">100%</text><text class="chart-axis" x="${L}" y="${H-2}">該折內驗證預測進度</text>`;
  byId('foldErrorLegend').innerHTML=series.map(({fold,index,points})=>`<span><i style="background:${colors[index%colors.length]}"></i>第 ${fold.fold} 折 · ${points[0].row.date}—${points.at(-1).row.date} · n=${points.length}${points.length<(fold.predictions||[]).length?`（排除 ${(fold.predictions||[]).length-points.length} 筆缺值）`:''}</span>`).join('');
  renderCalibration(predictions);
}
function renderCalibration(predictions) {
  const svg=byId('calibrationChart'),summary=byId('calibrationSummary');
  const numericValue=(value)=>value===null||value===undefined||value===''?NaN:Number(value);
  const rows=predictions.map((row)=>({predicted:numericValue(row.predicted)*100,actual:numericValue(row.actual)*100})).filter((row)=>Number.isFinite(row.predicted)&&Number.isFinite(row.actual));
  const excluded=predictions.length-rows.length;
  if(rows.length<2){svg.innerHTML='<text class="diagnostics-empty" x="310" y="130">需要至少 2 筆逐筆驗證預測才能分組</text>';summary.textContent=`有效配對 ${rows.length} 筆；${excluded?`排除 ${excluded} 筆缺少實際值或預測值的配對。`:''}舊結果沒有足夠的 out-of-fold 逐筆預測；重新訓練後會產生幅度校準圖。`;return;}
  rows.sort((a,b)=>a.predicted-b.predicted);
  const binCount=Math.max(1,Math.min(8,Math.floor(rows.length/20))),bins=[];
  for(let i=0;i<binCount;i++){
    const start=Math.floor(i*rows.length/binCount),end=Math.floor((i+1)*rows.length/binCount),sample=rows.slice(start,end);
    bins.push({count:sample.length,predicted:sample.reduce((sum,row)=>sum+row.predicted,0)/sample.length,actual:sample.reduce((sum,row)=>sum+row.actual,0)/sample.length,from:sample[0].predicted,to:sample.at(-1).predicted});
  }
  const extentValues=bins.flatMap((bin)=>[bin.predicted,bin.actual]),lo=Math.min(...extentValues),hi=Math.max(...extentValues);
  // Keep the origin visible when all predictions cluster near zero, while retaining sensible padding for small samples.
  const span=hi-lo,scale=Math.max(Math.abs(lo),Math.abs(hi),.15),pad=Math.max(span*.12,scale*.08,.05);
  const min=Math.min(lo-pad,0),max=Math.max(hi+pad,0);
  const W=620,H=260,L=57,R=18,T=14,B=43,plotW=W-L-R,plotH=H-T-B;
  const X=(value)=>L+(value-min)/(max-min)*plotW,Y=(value)=>T+plotH-(value-min)/(max-min)*plotH;
  const ticks=[min,(min+max)/2,max],grid=ticks.map((value)=>`<line class="calibration-grid" x1="${L}" x2="${W-R}" y1="${Y(value)}" y2="${Y(value)}"/><line class="calibration-grid" x1="${X(value)}" x2="${X(value)}" y1="${T}" y2="${T+plotH}"/><text class="chart-axis" x="${L-7}" y="${Y(value)+3}" text-anchor="end">${value.toFixed(2)}</text><text class="chart-axis" x="${X(value)}" y="${H-25}" text-anchor="middle">${value.toFixed(2)}</text>`).join('');
  const points=bins.map((bin,index)=>{const radius=Math.min(10,5+Math.sqrt(bin.count)/4);return `<circle class="calibration-point" cx="${X(bin.predicted)}" cy="${Y(bin.actual)}" r="${radius}"><title>第 ${index+1} 組 · n=${bin.count} · 預測平均 ${bin.predicted.toFixed(3)} pp · 實際平均 ${bin.actual.toFixed(3)} pp · 預測範圍 ${bin.from.toFixed(3)} 至 ${bin.to.toFixed(3)} pp</title></circle>`;}).join('');
  const weightedGap=bins.reduce((sum,bin)=>sum+Math.abs(bin.actual-bin.predicted)*bin.count,0)/rows.length;
  const weightedBias=bins.reduce((sum,bin)=>sum+(bin.actual-bin.predicted)*bin.count,0)/rows.length;
  svg.innerHTML=`${grid}<line class="calibration-reference" x1="${X(min)}" y1="${Y(min)}" x2="${X(max)}" y2="${Y(max)}"><title>理想校準：平均預測等於平均實際</title></line>${points}<text class="chart-axis" x="${L+plotW/2}" y="${H-5}" text-anchor="middle">分組平均預測報酬（百分點）</text><text class="chart-axis" transform="translate(13 ${T+plotH/2}) rotate(-90)" text-anchor="middle">平均實際報酬（百分點）</text>`;
  svg.setAttribute('aria-label',`驗證集預測幅度校準圖；${rows.length} 筆 out-of-fold 預測分成 ${binCount} 組；點越靠近理想校準線代表組平均幅度越接近。`);
  const concentration=span<.1?`預測與實際分組集中於零附近（範圍 ${lo.toFixed(3)} 至 ${hi.toFixed(3)} 個百分點）；座標軸保留零點以避免放大微小差異。`:'';
  const biasText=Math.abs(weightedBias)<.0005?'整體平均偏差接近零':weightedBias>0?'實際幅度平均高於預測（整體低估）':'實際幅度平均低於預測（整體高估）';
  summary.textContent=`${rows.length.toLocaleString()} 筆 out-of-fold 預測 · ${binCount} 組（每組約 ${Math.floor(rows.length/binCount)} 筆）· 分組加權幅度差 ${weightedGap.toFixed(3)} 個百分點 · ${biasText} ${weightedBias>=0?'+':''}${weightedBias.toFixed(3)} 個百分點。${excluded?`另排除 ${excluded} 筆缺少實際值或預測值的配對。`:''}${concentration}樣本內描述統計；不同市場時段與預測期間可能有差異。`;
}
function renderLockState() {
  const status = state.finalState || {};
  if (status.status === 'spent') { state.finalUsed = true; byId('finalStatus').textContent = status.datasetHashMismatch ? '舊資料版本的鎖定測試已揭露；為保護測試集，不重新開放。' : '鎖定測試已使用；請勿再用此區間調整模型。'; byId('runFinal').disabled = true; if (status.result) renderFinal(status.result, true, status.config, Boolean(status.datasetHashMismatch)); }
  else if (status.status === 'running') { state.finalUsed = true; byId('finalStatus').textContent = '鎖定測試進行中…'; byId('runFinal').disabled = true; }
  else { state.finalUsed = false; byId('finalStatus').textContent = '尚未使用 · 只在選定模型後執行一次'; }
}
function renderFinal(result, restored = false, config = null, datasetMismatch = false) {
  const box = byId('finalOutcome'); box.hidden = false;
  const r2 = Number.isFinite(Number(result.metrics.r2)) ? Number(result.metrics.r2).toFixed(3) : '—';
  const modelMae = Number(result.metrics?.mae);
  const baselineMae = Number(result.zeroBaseline?.mae);
  const comparable = result.metrics?.mae != null && result.zeroBaseline?.mae != null && Number.isFinite(modelMae) && Number.isFinite(baselineMae) && baselineMae > 0;
  const beatsBaseline = comparable && modelMae < baselineMae;
  const verdict = !comparable ? '無法與零報酬基準比較' : beatsBaseline ? '本次 MAE 優於零報酬基準' : '本次模型未優於零報酬基準';
  const gap = comparable ? Math.abs((modelMae / baselineMae - 1) * 100) : null;
  const shortRun = Number(config?.epochs || 0) > 0 && Number(config.epochs) < 20;
  const trainingNote = config ? `<small>設定：${config.modelTypes?.join('／') || result.name} · ${config.epochs} Epoch · 回看 ${config.lookback} 日 · ${config.features?.length || 0} 個特徵</small>` : '';
  const validityNote = `${shortRun ? `<aside class="final-verdict final-test-warning"><span>!</span><strong>開發用短訓練，不列為正式成果</strong><small>這次只有 ${config.epochs} Epoch，模型 MAE 為 ${pct(result.metrics.mae)}，零報酬基準 MAE 為 ${pct(result.zeroBaseline.mae)}。此鎖定區間已揭露，保留紀錄但不可重跑後宣稱為獨立測試。</small></aside>` : ''}${datasetMismatch ? `<aside class="final-verdict final-test-warning"><span>!</span><strong>這是舊資料版本的歷史測試紀錄</strong><small>該測試集曾經揭露，資料檔版本現已不同；目前畫面保留舊紀錄供稽核，測試按鈕維持鎖定，不能把此分數當成目前資料版本的正式結果。</small></aside>` : ''}`;
  box.classList.toggle('is-better', beatsBaseline);
  box.classList.toggle('is-worse', comparable && !beatsBaseline);
  box.setAttribute('role', 'status');
  box.setAttribute('aria-live', 'polite');
  box.innerHTML = `${validityNote}<div class="final-verdict"><span aria-hidden="true">${beatsBaseline ? '✓' : comparable ? '!' : 'i'}</span><strong>${verdict}</strong><small>${comparable ? `依 MAE 與基準比較，${beatsBaseline ? '降低' : '高出'} ${gap.toFixed(1)}%。此比較不代表可交易獲利。` : '基準數值不足，請檢查此份測試紀錄。'}</small></div><strong>${result.name} · ${restored ? '已存檔的鎖定測試' : '鎖定測試結果'}</strong><span>模型 MAE ${pct(result.metrics.mae)}　RMSE ${pct(result.metrics.rmse)}　R² ${r2}　方向準確率 ${pct(result.metrics.directionAccuracy,1)}</span><small>${result.testRange.from} — ${result.testRange.to} · ${formatInt(result.testSamples)} 筆；零報酬基準 MAE ${pct(result.zeroBaseline.mae)}</small>${trainingNote}<div class="final-prediction-heading">測試集報酬率：實際值與預測值</div><div class="final-prediction-legend"><span><i class="actual-key"></i>實際報酬</span><span><i class="predicted-key"></i>預測報酬</span></div><svg id="finalPredictionChart" viewBox="0 0 760 190" role="img" aria-label="鎖定測試集實際報酬率與模型預測報酬率時間序列"></svg><details class="prediction-table"><summary>查看圖中抽樣資料</summary><div class="prediction-table-scroll"><table><thead><tr><th>日期</th><th>實際報酬</th><th>預測報酬</th></tr></thead><tbody>${(result.predictions||[]).map(p=>`<tr><td>${p.date}</td><td>${pct(p.actual)}</td><td>${pct(p.predicted)}</td></tr>`).join('')}</tbody></table></details>`;
  renderFinalPredictionChart(result.predictions || [], result.horizon || 1);
  byId('finalStatus').textContent = '鎖定測試已使用；分數只供最終報告。'; byId('runFinal').disabled = true;
}
function renderFinalPredictionChart(points, horizon) {
  const svg=byId('finalPredictionChart');
  if(!svg||!points.length){if(svg)svg.innerHTML='<text x="380" y="100" text-anchor="middle" class="chart-axis">此測試結果沒有可繪製的預測抽樣</text>';return;}
  const W=760,H=190,L=52,R=14,T=12,B=28, values=points.flatMap(p=>[Number(p.actual),Number(p.predicted)]).filter(Number.isFinite);
  const lo=Math.min(0,...values),hi=Math.max(0,...values),span=hi-lo||1, x=i=>L+i/Math.max(1,points.length-1)*(W-L-R), y=v=>T+(hi-v)/span*(H-T-B);
  const grid=[0,1,2,3].map(i=>{const value=hi-(hi-lo)*i/3,yy=y(value);return `<line class="chart-grid" x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}"/><text class="chart-axis" x="${L-7}" y="${yy+4}" text-anchor="end">${(value*100).toFixed(1)}%</text>`}).join('');
  const line=(key,cls)=>`<polyline class="${cls}" points="${points.map((p,i)=>`${x(i)},${y(Number(p[key]))}`).join(' ')}"/>`;
  const ticks=[0,Math.floor((points.length-1)/2),points.length-1].map(i=>`<text class="chart-axis" x="${x(i)}" y="${H-7}" text-anchor="${i===0?'start':i===points.length-1?'end':'middle'}">${points[i].date}</text>`).join('');
  const title=`鎖定測試集 ${horizon} 日報酬率的實際值與預測值，共 ${points.length} 個時間抽樣點`;
  svg.setAttribute('aria-label',title);svg.innerHTML=`<title>${title}</title>${grid}${line('actual','final-actual-line')}${line('predicted','final-predicted-line')}${ticks}`;
}
async function refreshLockStatus() { try { const status = await api(`/api/data/lock-status?symbol=${encodeURIComponent(state.status?.symbol || 'TAIEX')}`); state.finalState = status; renderLockState(); } catch (_) {} }

const LESSONS = [
  { kicker:'01 · 從資料開始', title:'模型讀取的是報酬，不是股價點位', body:'收盤價會隨市場長期上升，直接預測價格容易讓模型只學到尺度與趨勢。本實驗把目標定為下一期報酬率，並只使用截至預測時點可取得的歷史特徵。', takeaway:'先問清楚：模型的輸入是什麼？它要預測哪一個時間點？' },
  { kicker:'02 · 把時間變成張量', title:'回看區間決定模型一次看到多少過去', body:'若選 20 日回看、5 個特徵，單筆輸入就是 X ∈ ℝ²⁰ˣ⁵。每列是一個交易日，每欄是一種特徵；目標是觀測窗之後的報酬率。', takeaway:'序列順序有意義，因此切分資料時不能隨機打散日期。' },
  { kicker:'03 · 前向傳播', title:'每一層把輸入轉成新的表示', body:'神經元先計算 z = Wx + b，再套用非線性函數。MLP 將整段觀察窗攤平處理；RNN、LSTM、GRU 則依時間步更新隱藏狀態。', takeaway:'模型架構不同，改變的是資訊如何沿著時間與層傳遞。' },
  { kicker:'04 · 誤差與學習', title:'損失函數把預測誤差變成可優化的數值', body:'MSE 對大誤差給予較大平方懲罰。反向傳播用鏈鎖律計算每個權重對損失的偏導數，最佳化器再沿梯度方向調整權重。', takeaway:'訓練損失下降只代表模型更貼近訓練資料，不保證能預測未來。' },
  { kicker:'05 · 時間序列驗證', title:'用未參與訓練的未來資料檢查泛化', body:'前段資料用於逐步訓練與驗證，最後一段保留為鎖定測試。MAE、RMSE 要和零報酬、歷史平均等簡單基準一起看。', takeaway:'測試結果揭露後就不能再拿同一段資料反覆調參。' },
  { kicker:'06 · 預測幅度校準', title:'分組比較預測幅度和實際幅度', body:'把 walk-forward 驗證預測依預測值排序，再分成樣本數相近的組。每點的 x 是該組平均預測報酬，y 是平均實際報酬；離虛線越遠，該組的幅度偏差越大。', takeaway:'校準圖是驗證資料的描述統計；分組吻合不代表下一段期間會準，也不能單獨證明模型有用。' },
  { kicker:'07 · 方向與幅度', title:'方向答對，不等於幅度估得準', body:'合成例子：實際報酬 +0.2%，預測 +1.0%。兩者同為正值，所以方向相同；但預測比實際高 0.8 個百分點。反過來，預測 −0.1%、實際 +0.1% 是方向相反，幅度差只有 0.2 個百分點。', takeaway:'分開讀方向指標與 MAE／校準；這些合成數字只示範概念，不是模型輸出或品質證據。' },
  { kicker:'08 · 報酬換算', title:'把預測報酬換成參考點位', body:'教學例子：訊號日收盤為 20,000 點，預測 +1% 簡單報酬，換算為 20,000 × (1 + 0.01) = 20,200 點。若 +1% 是對數報酬，則先取指數：20,000 × exp(0.01) ≈ 20,201 點。', takeaway:'這是用訊號日收盤值做的算術換算，不是模型直接預測點位，也不是下一日可成交價格；數值只供學習。' },
  { kicker:'09 · 學習率', title:'學習率控制每次更新權重的步幅', body:'梯度指出損失上升最快的方向；梯度下降用 W ← W − η∇W 更新權重。η 是學習率：太大可能跨過較低損失區域，太小則每次只移動一點。合成例子中，若 W=2、梯度=0.5，η=0.1 時新權重為 1.95；η=0.5 時為 1.75。', takeaway:'學習率例子只示範更新算式；單次權重變化不代表訓練收斂或預測變好。' },
  { kicker:'10 · 讀懂預測幅度', title:'正負號表示方向，數值大小表示預測幅度', body:'合成例子：模型預測下一期報酬 +0.6%，表示方向為上漲，預測幅度為 0.6%；若一般驗證中的實際報酬是 +0.2%，方向答對，但幅度高估 0.4 個百分點。負值則表示預測下跌。', takeaway:'這組合成數字只示範如何讀報酬預測；實際成效仍須用逐筆 OOF 預測、MAE 與簡單基準檢查。' },
  { kicker:'11 · 區間與不確定性', title:'單一預測值不會告訴你誤差範圍', body:'合成教學例子：中心預測 +0.6%，誤差尺度 0.4 個百分點時範圍是 +0.2% 到 +1.0%，寬 0.8 個百分點；尺度改為 0.7 時範圍變成 −0.1% 到 +1.3%，寬 1.4 個百分點。中心不變、尺度增加，範圍變寬。這是算術示意，沒有機率或覆蓋率含義。', takeaway:'這不是本模型估出的區間；要談區間覆蓋率，須先用一般驗證資料定義方法、逐筆檢查覆蓋，再確認不同期間是否穩定。' },
  { kicker:'12 · 鏈鎖律', title:'反向傳播把局部變化串成梯度', body:'合成單一權重例子：ŷ=2w+1、目標 y=5、損失 L=(ŷ−y)²。當 w=1，ŷ=3、誤差 e=−2；鏈鎖律給出 dL/dw = 2(ŷ−y) × dŷ/dw = 2×(−2)×2 = −8。用學習率 η=0.1 更新，w新=1−0.1×(−8)=1.8，預測變成 4.6，損失由 4 降至 0.16。', takeaway:'這是合成算例，用來看懂鏈鎖律如何傳遞梯度；單一步更新不證明真實模型會收斂或預測更準。' },
  { kicker:'13 · 啟用函數與梯度', title:'ReLU 會讓負值方向的梯度停止傳遞', body:'看合成神經元 ŷ=ReLU(z)、損失 L=(ŷ−1)²。當 z=2，ReLU′(z)=1，因此 dL/dz=2(ŷ−1)×1=2；當 z=−2，ŷ=0 且 ReLU′(z)=0，所以 dL/dz=2(0−1)×0=0。鏈鎖律中的啟用函數導數決定梯度是否能往前一層傳。', takeaway:'這是遠離 z=0 的合成算例；ReLU 在零點不可微，實作會採用特定次梯度慣例。梯度為零只描述這個神經元和這筆輸入，不是整體模型品質結論。' },
  { kicker:'14 · ReLU 梯度互動', title:'改變神經元輸入，觀察 ReLU 如何傳遞梯度', body:'用下一個合成例子調整 z，逐步核對啟用函數輸出和損失梯度。', takeaway:'只展示單一合成神經元的局部微分，不代表訓練中的實際梯度或預測品質。' },
  { kicker:'15 · 方向與幅度誤差', title:'把方向一致性和幅度誤差分開核對', body:'合成例子：預測 +0.6%、實際 +0.2%，方向一致，但預測幅度高估 0.4 個百分點；零報酬基準誤差為 0.2 個百分點，所以這筆預測誤差較大。改成預測 0%、實際 +0.1%，方向都視為持平／中性，絕對誤差同為 0.1 個百分點。', takeaway:'此互動只演示單筆計算；模型表現仍需同一驗證協定下的逐筆 OOF、MAE 與同期間基準。零報酬視為持平方向。' },
  { kicker:'16 · 單一神經元前向傳播', title:'從輸入一路算到 ReLU 輸出', body:'調整 x、權重 w 與偏置 b，先計算 z=wx+b，再得到 ŷ=ReLU(z)。預設 x=2、w=0.5、b=0.2，故 z=1.2、輸出 ŷ=1.2。', takeaway:'這個可調算例展示一個神經元的前向計算，不連接訓練模型，也不代表預測品質。' },
  { kicker:'17 · 多輸入神經元', title:'多個輸入各自乘上權重後再相加', body:'單一神經元可接收多個輸入：z=w₁x₁+w₂x₂+b。預設 x₁=2、w₁=0.5、x₂=1、w₂=−0.4、b=0.2，得到 z=0.8，ReLU 輸出 ŷ=0.8。反向傳播時，令 δ=∂L/∂z；每個權重梯度是 δ 乘上自己的輸入，偏置梯度則是 δ。', takeaway:'預設目標 y=1 時 δ=−0.4，因此 ∂L/∂w₁=δx₁=−0.8、∂L/∂w₂=δx₂=−0.4、∂L/∂b=δ=−0.4。敏感度例把 x₁ 加倍至 4，其他輸入與權重不變，並把合成目標調至 y=2 以固定 δ=−0.4；此時 z=1.8、∂L/∂w₁=−1.6，而 ∂L/∂w₂ 仍是 −0.4。' },
  { kicker:'18 · 反向傳播更新', title:'用梯度做一次可檢查的參數更新', body:'在第 17 步的合成神經元上設定目標 y 與學習率 η，先用 L=(ŷ−y)² 求出兩個權重和偏置的梯度，再做 θ新=θ−η∇θ。比較更新前後的損失，理解單一步可能降低也可能提高損失。', takeaway:'此互動只演示一筆資料的一次 SGD 更新；不連接模型訓練，也不代表訓練收斂或預測品質。' },
  { kicker:'19 · 小批次梯度', title:'多筆樣本先平均梯度，再更新一次', body:'四筆合成樣本對同一權重的梯度為 −2、4、1、1。平均梯度 (−2+4+1+1)/4=1；若權重為 2、學習率 η=0.1，批次只更新一次至 1.9。正負梯度會部分抵銷；平均值相同的批次，也可能有不同的樣本方向。', takeaway:'平均梯度決定這次更新方向，但不會顯示每筆樣本的完整差異；下方可調互動只示範合成算術，不連接實際訓練。' },
  { kicker:'20 · 動量最佳化', title:'動量累積近期梯度方向', body:'合成例子使用 vₜ=βvₜ₋₁+gₜ、wₜ=wₜ₋₁−ηvₜ。若 β=0.9、前一步速度 vₜ₋₁=0.5、本步梯度 gₜ=1、η=0.1，則 vₜ=1.45，權重更新量為 −0.145。若第二步梯度改成 −2，方向反轉但速度仍為 0.9×1.45−2=−0.695，權重因此上升 0.0695；保留的歷史速度抵銷了一部分反向梯度。', takeaway:'動量會把過去更新方向帶入目前步驟；這個算例只說明公式，實際效果須以訓練資料和驗證結果評估。' },
  { kicker:'21 · 啟用函數比較', title:'Sigmoid、ReLU 與 Tanh 會塑造不同的輸出與梯度', body:'調整合成神經元輸入 z，比較 sigmoid(z)=1/(1+e⁻ᶻ)、ReLU(z)=max(0,z) 與 tanh(z)。Sigmoid 輸出介於 0 與 1；ReLU 保留正值並截掉負值；Tanh 輸出介於 −1 與 1。', takeaway:'三種函數會改變訊號與梯度傳遞方式；此互動是局部數學示例，不代表哪種架構在市場資料上較好。' },
  { kicker:'22 · 梯度裁剪', title:'梯度裁剪限制單次更新的步幅', body:'合成單一權重例子：w=2、梯度 g=4、學習率 η=0.1。未裁剪時 w新=2−0.1×4=1.6；若裁剪上限為 1，梯度改為 1，w新=1.9。多參數時可按整個梯度向量的範數同比縮放：梯度 (3,4) 的範數是 5，上限為 1 時變成 (0.6,0.8)，方向不變、總長度降為 1。', takeaway:'裁剪會限制梯度大小，但不保證損失下降或預測變好；向量例子只說明範數縮放，不連接實際模型訓練。' },
  { kicker:'23 · 梯度下降軌跡', title:'曲率與學習率共同決定更新穩定性', body:'使用合成損失 L(w)=c(w−1)²，其梯度為 2c(w−1)。每一步先計算梯度，再以 w新=w−ηg 更新；比較不同曲率與學習率，觀察收斂、振盪和發散。', takeaway:'這條一維二次損失只用來練習梯度下降算術；曲率會放大梯度，穩定範圍也會改變。真實神經網路損失面更複雜，單一合成軌跡不代表訓練成效。' },
  { kicker:'24 · Adam 首步', title:'Adam 用偏差校正讀取梯度的一階與二階動差', body:'Adam 以指數移動平均累積梯度 mₜ 與平方梯度 vₜ，再用偏差校正得到 m̂ₜ、v̂ₜ。第一步若 m₀=v₀=0，未校正平均會偏向零；校正後在單筆合成梯度上可直接看見正確尺度。', takeaway:'此互動只比較一個合成更新步驟，不連接 PyTorch 訓練，也不代表 Adam 一定比 SGD 收斂更快或預測更準。' },
  { kicker:'25 · Adam 動差記憶', title:'梯度反向時，Adam 如何保留前一步動差', body:'使用兩個方向相反的合成梯度，觀察 Adam 如何把前一步的一階與二階動差帶入下一步，並在 t=2 做偏差校正；同時比較直接使用當步梯度的 SGD。', takeaway:'固定梯度序列用來隔離更新公式。真實訓練會重新計算梯度，這個算例不連接訓練，也不代表市場預測品質。' },
  { kicker:'26 · L2 正則化', title:'正則化梯度會把權重拉向零', body:'資料損失和正則化懲罰會一起影響更新。調整權重、學習率與 λ，分開追蹤資料梯度 2(w−1)、L2 懲罰梯度 2λw，以及兩者相加後的新權重；兩項梯度相反時，觀察誰主導合力。', takeaway:'這是一個單一權重、平方資料損失加 λw² 的合成例子；它只解釋公式，不連接訓練，也不代表預測會改善。' },
];
const QUIZ = [
  { q:'預測某日報酬率時，哪些資料可以放進輸入？', choices:['預測日收盤後才知道的最高價','只使用預測時點以前已知的資料','把整段資料隨機打散後挑最近樣本'], answer:1, why:'輸入必須在預測當下已經可取得。未來資訊會造成資料洩漏，讓評估分數失真。' },
  { q:'把日期隨機打散再切訓練集與測試集，主要問題是什麼？', choices:['會破壞時間順序，較晚時期可能洩漏到訓練','一定會讓樣本數變少','會自動把價格改成報酬率'], answer:0, why:'金融時間序列需要按時間先後評估。未來資料進入訓練會高估模型的泛化能力。' },
  { q:'MSE 損失函數如何處理預測誤差？', choices:['計算誤差絕對值的平均','計算誤差平方的平均','只計算預測方向對不對'], answer:1, why:'MSE 是平方誤差的平均，因此大誤差會受到更重的懲罰。' },
  { q:'反向傳播在神經網路裡的作用是什麼？', choices:['用鏈鎖律計算損失對參數的梯度','打亂時間序列順序','替模型挑選最佳測試集'], answer:0, why:'梯度告訴最佳化器各權重改變時，損失會如何變化。' },
  { q:'鎖定測試分數看過之後，最嚴謹的下一步是什麼？', choices:['繼續用同一測試集挑超參數','把測試資料加進訓練並沿用原分數','保留結果，不再用這段測試集反覆選模'], answer:2, why:'看過測試結果後，測試集已提供了回饋，不再是完全未見資料。' },
  { q:'兩檔股票的 OOF MAE 分別是 0.8% 與 1.2%，可以直接說前者預測較好嗎？', choices:['可以，MAE 較小就代表模型較好','不一定；報酬波動尺度與驗證期間可能不同，需和各自基準及期間一起看','可以，只要兩檔都使用神經網路'], answer:1, why:'不同標的的報酬尺度可能不同。先比較各自相對簡單基準的誤差差，再確認期間與報酬定義；仍是描述性驗證結果。' },
];
const LEARNING_PROGRESS_KEY = 'taiex-learning-progress-v1';
function loadLearningProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(LEARNING_PROGRESS_KEY) || 'null');
    const index = Number(saved?.lessonIndex);
    const tabId = saved?.tabId;
    const validTabs = new Set(['tabGuided', 'tabQuiz', 'tabLab', 'tabMath']);
    return {lessonIndex: Number.isInteger(index) && index >= 0 && index < LESSONS.length ? index : 0,
      tabId: validTabs.has(tabId) ? tabId : 'tabGuided'};
  } catch (_) { return {lessonIndex: 0, tabId: 'tabGuided'}; }
}
function saveLearningProgress() {
  try { localStorage.setItem(LEARNING_PROGRESS_KEY, JSON.stringify({lessonIndex, tabId: activeLearningTabId})); } catch (_) {}
}
const savedLearningProgress = loadLearningProgress();
let lessonIndex = savedLearningProgress.lessonIndex, activeLearningTabId = savedLearningProgress.tabId;
let quizIndex = 0, quizScore = 0, quizAnswered = false, quizFinished = false, traceLoaded = false;
function renderLesson() {
  const lesson = LESSONS[lessonIndex];
  byId('learningSummary').textContent = `${LESSONS.length} 步導學 · 作答即時解析 · 實驗任務與筆記 · 數學運算`;
  const resumeNotice = byId('learningResumeNotice');
  if (resumeNotice) {
    const hasSavedProgress = savedLearningProgress.lessonIndex > 0;
    resumeNotice.hidden = lessonIndex === 0 || !hasSavedProgress;
    resumeNotice.textContent = resumeNotice.hidden ? '' : `已恢復上次進度：第 ${lessonIndex + 1} 步「${lesson.title}」。可繼續下一步，或用「上一步」複習。`;
  }
  byId('lessonKicker').textContent = lesson.kicker; byId('lessonTitle').textContent = lesson.title;
  byId('lessonBody').textContent = lesson.body; byId('lessonTakeaway').textContent = lesson.takeaway;
  byId('lessonProgress').textContent = `第 ${lessonIndex + 1} / ${LESSONS.length} 步`;
  byId('lessonProgressFill').style.width = `${(lessonIndex + 1) / LESSONS.length * 100}%`;
  byId('lessonBack').disabled = lessonIndex === 0;
  byId('lessonNext').textContent = lessonIndex === LESSONS.length - 1 ? '重新開始' : '下一步';
  const conversion = byId('returnConversionExercise');
  if (conversion) conversion.hidden = lessonIndex !== 7;
  if (lessonIndex === 7) renderReturnConversion();
  const gradient = byId('gradientExercise');
  if (gradient) gradient.hidden = lessonIndex !== 8;
  if (lessonIndex === 8) renderGradientExercise();
  const interval = byId('predictionIntervalExample');
  if (interval) interval.hidden = lessonIndex !== 10;
  const magnitude = byId('magnitudeExample');
  if (magnitude) magnitude.hidden = lessonIndex !== 9;
  if (lessonIndex === 10) renderPredictionIntervalExample();
  const relu = byId('reluExercise');
  if (relu) relu.hidden = lessonIndex !== 13;
  if (lessonIndex === 13) renderReluExercise();
  const magnitudeError = byId('magnitudeErrorExercise');
  if (magnitudeError) magnitudeError.hidden = lessonIndex !== 14;
  if (lessonIndex === 14) renderMagnitudeErrorExercise();
  const forwardPass = byId('forwardPassExercise');
  if (forwardPass) forwardPass.hidden = lessonIndex !== 15;
  if (lessonIndex === 15) renderForwardPassExercise();
  const multiForwardPass = byId('multiForwardPassExercise');
  if (multiForwardPass) multiForwardPass.hidden = lessonIndex !== 16;
  if (lessonIndex === 16) renderMultiForwardPassExercise();
  const updateExercise = byId('gradientUpdateExercise');
  if (updateExercise) updateExercise.hidden = lessonIndex !== 17;
  if (lessonIndex === 17) renderGradientUpdateExercise();
  const gradientCheckExercise = byId('gradientCheckExercise');
  if (gradientCheckExercise) gradientCheckExercise.hidden = lessonIndex !== 17;
  if (lessonIndex === 17) renderFiniteDifferenceGradientCheck();
  const batchGradientExercise = byId('batchGradientExercise');
  if (batchGradientExercise) batchGradientExercise.hidden = lessonIndex !== 18;
  if (lessonIndex === 18) renderBatchGradientExercise();
  const momentumExercise = byId('momentumExercise');
  if (momentumExercise) momentumExercise.hidden = lessonIndex !== 19;
  if (lessonIndex === 19) renderMomentumExercise();
  const momentumDirection = byId('momentumDirectionResult');
  if (momentumDirection && lessonIndex === 19) renderMomentumDirection();
  const activationExercise = byId('activationExercise');
  if (activationExercise) activationExercise.hidden = lessonIndex !== 20;
  if (lessonIndex === 20) renderActivationExercise();
  const clippingExercise = byId('gradientClippingExercise');
  if (clippingExercise) clippingExercise.hidden = lessonIndex !== 21;
  if (lessonIndex === 21) renderGradientClippingExercise();
  if (lessonIndex === 21) { renderVectorGradientClipping(); renderVectorGradientClipping3(); renderVectorGradientClipping4(); }
  const gradientDescentTrace = byId('gradientDescentTrace');
  if (gradientDescentTrace) gradientDescentTrace.hidden = lessonIndex !== 22;
  if (lessonIndex === 22) renderGradientDescentTrace();
  const adamStepExercise = byId('adamStepExercise');
  if (adamStepExercise) adamStepExercise.hidden = lessonIndex !== 23;
  if (lessonIndex === 23) renderAdamStepExercise();
  const adamTwoStepExercise = byId('adamTwoStepExercise');
  if (adamTwoStepExercise) adamTwoStepExercise.hidden = lessonIndex !== 24;
  if (lessonIndex === 24) renderAdamTwoStepExercise();
  const l2RegularizationExercise = byId('l2RegularizationExercise');
  if (l2RegularizationExercise) l2RegularizationExercise.hidden = lessonIndex !== 25;
  if (lessonIndex === 25) renderL2RegularizationExercise();
  const weightDecayExercise = byId('weightDecayComparisonExercise');
  const weightDecayLessonIndex = LESSONS.findIndex((item) => item.title === '正則化梯度會把權重拉向零');
  if (weightDecayExercise) weightDecayExercise.hidden = lessonIndex !== weightDecayLessonIndex;
  if (lessonIndex === weightDecayLessonIndex) renderWeightDecayComparison();
  if (lessonIndex === 9) renderMagnitudeExample();
  saveLearningProgress();
}
function calculateMagnitudeReference(price, returnPercent, type) {
  if ([price, returnPercent].some((value) => String(value).trim() === '')) return null;
  const base = Number(price), rate = Number(returnPercent), ratio = rate / 100;
  if (!Number.isFinite(base) || base <= 0 || !Number.isFinite(rate) || (type === 'simple' && ratio <= -1)) return null;
  const value = base * (type === 'log' ? Math.exp(ratio) : 1 + ratio);
  return Number.isFinite(value) ? { direction: rate > 0 ? '上漲' : rate < 0 ? '下跌' : '持平', magnitude: Math.abs(rate), value } : null;
}
function renderTensorShapeExercise() {
  const output = byId('tensorShapeResult');
  if (!output) return;
  const inputs = Number(byId('tensorInputCount').value), neurons = Number(byId('tensorNeuronCount').value);
  const valid = [byId('tensorInputCount').value, byId('tensorNeuronCount').value].every((value) => String(value).trim() !== '') &&
    Number.isInteger(inputs) && Number.isInteger(neurons) && inputs >= 1 && neurons >= 1 && inputs <= 64 && neurons <= 64;
  if (!valid) {
    output.textContent = '請輸入 1 到 64 的整數維度。';
    return;
  }
  const shownRows = Math.min(neurons, 6), shownColumns = Math.min(inputs, 6);
  const cells = Array.from({length: shownRows}, () => `<span class="tensor-cell" aria-hidden="true"></span>`).join('');
  const rows = Array.from({length: shownRows}, () => `<div class="tensor-row">${cells}</div>`).join('');
  const omitted = neurons > shownRows || inputs > shownColumns ? `<small>圖示最多顯示 6×6 格；實際矩陣仍為 ${neurons}×${inputs}。</small>` : '';
  output.innerHTML = `<span>W 的形狀為 <strong>${neurons}×${inputs}</strong>（${neurons} 列、${inputs} 欄）；輸入向量 ${inputs} 維相乘後，輸出為 ${neurons} 維。</span><div class="tensor-matrix-wrap"><span class="tensor-axis tensor-axis-rows">列：神經元</span><div class="tensor-matrix" role="img" aria-label="權重矩陣 ${neurons} 列、${inputs} 欄">${rows}</div><span class="tensor-axis tensor-axis-columns">欄：輸入</span></div>${omitted}`;
}
function tensorShapeFeedbackForAnswer(answer) {
  if (answer === 'neurons-first') return { correct: true, text: '答對了。W 有 2 列、3 欄，所以 W 是 2×3；乘上 3 維輸入後得到 2 維輸出。' };
  if (answer === 'input-first') return { correct: false, text: '再看每一列：一列代表一個神經元，每欄對應一項輸入，因此是 2×3。' };
  return { correct: false, text: '請先選一個答案，再檢查。' };
}
function renderMagnitudeExample() {
  const output = byId('magnitudeResult');
  if (!output) return;
  const price = byId('magnitudePrice').value, rate = byId('magnitudeReturn').value, type = byId('magnitudeType').value;
  const result = calculateMagnitudeReference(price, rate, type);
  if (!result) { output.textContent = '請輸入大於 0 的點位與有限報酬；簡單報酬不可低於 −100%。'; return; }
  const fmt = (value) => value.toLocaleString('zh-TW', {minimumFractionDigits:2, maximumFractionDigits:2});
  output.textContent = `預測方向：${result.direction}；預測幅度：${result.magnitude.toFixed(2)}%。參考點位：${fmt(result.value)} 點。`;
}
function calculatePredictionInterval(center, spread) {
  if ([center, spread].some((value) => String(value).trim() === '')) return null;
  const c = Number(center), s = Number(spread);
  if (![c, s].every(Number.isFinite) || s < 0 || !Number.isFinite(c - s) || !Number.isFinite(c + s)) return null;
  return { lower: Number((c - s).toFixed(12)), upper: Number((c + s).toFixed(12)) };
}
function renderPredictionIntervalExample() {
  const output = byId('predictionIntervalResult');
  if (!output) return;
  const center = byId('intervalCenter')?.value;
  const spread = byId('intervalSpread')?.value;
  const interval = calculatePredictionInterval(center, spread);
  const viz = byId('intervalViz');
  const width = interval ? Number((interval.upper - interval.lower).toFixed(12)) : null;
  if (!interval) {
    output.textContent = '請輸入有限的中心預測及非負誤差尺度。';
    if (viz) { viz.hidden = true; viz.setAttribute('aria-label', '輸入有效的中心預測與非負誤差尺度後顯示合成示意區間'); }
    return;
  }
  if (viz) {
    viz.hidden = false;
    const extent = Math.max(Math.abs(interval.lower), Math.abs(interval.upper), Math.abs(Number(center)), 0.5);
    const position = value => `${50 + (value / extent) * 42}%`;
    viz.style.setProperty('--interval-left', position(interval.lower));
    viz.style.setProperty('--interval-right', position(interval.upper));
    viz.style.setProperty('--interval-center', position(Number(center)));
    const fmt = value => `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
    byId('intervalLowerLabel').textContent = `下界 ${fmt(interval.lower)}`;
    byId('intervalCenterLabel').textContent = `中心 ${fmt(Number(center))}`;
    byId('intervalUpperLabel').textContent = `上界 ${fmt(interval.upper)}`;
    viz.setAttribute('aria-label', `合成示意區間：下界 ${fmt(interval.lower)}，中心 ${fmt(Number(center))}，上界 ${fmt(interval.upper)}`);
  }
  output.textContent = `示意範圍：${interval.lower.toFixed(2)}% 至 ${interval.upper.toFixed(2)}%（中心 ${Number(center).toFixed(2)}%，上下各 ${Number(spread).toFixed(2)} 個百分點；總寬 ${width.toFixed(2)} 個百分點）`;
  const widthReading = byId('intervalWidthReading');
  if (widthReading) widthReading.textContent = `尺度 ${Number(spread).toFixed(2)} 個百分點 → 寬度 ${width.toFixed(2)} 個百分點；尺度加倍時寬度也加倍，中心不變。`;
}
function calculateGradientStep(weight, gradient, rate) {
  if ([weight, gradient, rate].some((value) => String(value).trim() === '')) return null;
  const w = Number(weight), g = Number(gradient), eta = Number(rate);
  if (![w, g, eta].every(Number.isFinite) || eta < 0 || eta > 10) return null;
  const next = w - eta * g;
  return Number.isFinite(next) ? next : null;
}
function calculateQuadraticLoss(weight, target = 1) {
  if ([weight, target].some((value) => String(value).trim() === '')) return null;
  const w = Number(weight), t = Number(target);
  if (![w, t].every(Number.isFinite)) return null;
  const loss = (w - t) ** 2;
  return Number.isFinite(loss) ? loss : null;
}
function renderGradientExercise() {
  const result = byId('gradientResult');
  if (!result) return;
  const weight = byId('gradientWeight').value, gradient = byId('gradientValue').value, rate = byId('gradientRate').value;
  const next = calculateGradientStep(weight, gradient, rate);
  result.textContent = next === null
    ? '請填妥三個有限數值；學習率需介於 0 到 10。'
    : (() => {
      const before = calculateQuadraticLoss(weight), after = calculateQuadraticLoss(next);
      const comparison = before === null || after === null ? '損失無法計算。' : after < before ? '這個合成例子中，平方損失下降。' : after > before ? '這個合成例子中，平方損失上升；步幅可能太大。' : '這個合成例子中，平方損失不變。';
      return `W新 = ${weight} − ${rate} × ${gradient} = ${next.toLocaleString('zh-TW', {maximumFractionDigits: 6})}。${Number(gradient) > 0 ? '梯度為正，這一步讓權重下降。' : Number(gradient) < 0 ? '梯度為負，這一步讓權重上升。' : '梯度為零，這一步權重不變。'} 假設合成目標 W=1、L=(W−1)²，更新前損失 ${before}，更新後 ${after}。${comparison}`;
    })();
}
function calculateReluGradient(input, target) {
  if ([input, target].some((value) => String(value).trim() === '')) return null;
  const z = Number(input), y = Number(target);
  if (!Number.isFinite(z) || !Number.isFinite(y)) return null;
  const output = Math.max(0, z);
  const derivative = z > 0 ? 1 : z < 0 ? 0 : 0; // ReLU'(0) uses the common zero subgradient.
  const error = output - y;
  const loss = error ** 2;
  const gradient = 2 * error * derivative;
  const sigmoid = z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z));
  const sigmoidDerivative = sigmoid * (1 - sigmoid);
  const sigmoidGradient = 2 * (sigmoid - y) * sigmoidDerivative;
  return [loss, gradient, sigmoid, sigmoidDerivative, sigmoidGradient].every(Number.isFinite)
    ? { z, output, loss, derivative, gradient, atKink: z === 0, sigmoid, sigmoidDerivative, sigmoidGradient }
    : null;
}
function renderReluExercise() {
  const result = byId('reluResult');
  if (!result) return;
  const value = calculateReluGradient(byId('reluInput').value, byId('reluTarget').value);
  result.textContent = value === null ? '請輸入可計算的有限神經元值 z 與目標 y。' : `ŷ = max(0,z) = ${value.output}；L=(ŷ−y)² = ${value.loss}；ReLU′(z) = ${value.derivative}；dL/dz = 2(ŷ−y) × ${value.derivative} = ${value.gradient}。Sigmoid(z) = ${value.sigmoid.toFixed(4)}；Sigmoid′(z) = ${value.sigmoidDerivative.toExponential(3)}；同一損失下 dL/dz = ${value.sigmoidGradient.toExponential(3)}。${Math.abs(value.z) >= 4 ? '輸入絕對值較大時，Sigmoid′(z) 會變小，梯度也可能變得很小。' : ''}${value.atKink ? '此處 z=0 不可微；本互動採用 ReLU′(0)=0 的次梯度慣例，因此局部梯度為 0。' : ''}`;
}
function compareReturnMagnitude(predicted, actual) {
  if ([predicted, actual].some((value) => String(value).trim() === '')) return null;
  const p = Number(predicted), a = Number(actual);
  if (![p, a].every(Number.isFinite)) return null;
  const direction = (value) => value > 0 ? 1 : value < 0 ? -1 : 0;
  const sameDirection = direction(p) === direction(a);
  return { sameDirection, errorPp: Math.abs(p - a), signedErrorPp: p - a, predicted: p, actual: a };
}
function compareMagnitudeToZeroBaseline(predicted, actual) {
  const comparison = compareReturnMagnitude(predicted, actual);
  if (!comparison) return null;
  const zeroBaselineErrorPp = Math.abs(comparison.actual);
  const difference = Math.abs(comparison.predicted - comparison.actual) - Math.abs(comparison.actual);
  const tolerance = 1e-12 * Math.max(1, Math.abs(comparison.predicted), Math.abs(comparison.actual));
  const errorVsZeroBaselinePp = Math.abs(difference) <= tolerance ? 0 : difference;
  return {
    ...comparison,
    magnitudeBias: Math.abs(comparison.predicted) > Math.abs(comparison.actual)
      ? '預測絕對幅度較大'
      : Math.abs(comparison.predicted) < Math.abs(comparison.actual)
        ? '預測絕對幅度較小'
        : '預測絕對幅度相同',
    zeroBaselineErrorPp,
    errorVsZeroBaselinePp,
    beatsZeroBaseline: errorVsZeroBaselinePp < -tolerance,
    tiesZeroBaseline: Math.abs(errorVsZeroBaselinePp) <= tolerance
  };
}
function renderMagnitudeErrorExercise() {
  const output = byId('magnitudeErrorResult');
  if (!output) return;
  const parse = (id) => {
    const raw = byId(id).value.split(',').map((item) => item.trim());
    if (!raw.length || raw.some((item) => item === '' || !Number.isFinite(Number(item)))) return null;
    return raw.map(Number);
  };
  const predicted = parse('magnitudePredicted'), actual = parse('magnitudeActual');
  if (!predicted || !actual || predicted.length !== actual.length) {
    output.textContent = '請輸入數量相同且有限的預測與實際報酬，使用逗號分隔。';
    return;
  }
  const groups = { up: [], down: [] };
  actual.forEach((value, i) => {
    if (value > 0) groups.up.push([predicted[i], value]);
    if (value < 0) groups.down.push([predicted[i], value]);
  });
  const summarize = (rows) => rows.length ? {
    n: rows.length,
    // Scale each pair before taking its difference so a representable mean
    // does not overflow merely because the unscaled total exceeds Number.MAX_VALUE.
    mae: rows.reduce((sum, [p, a]) => sum + Math.abs(p / rows.length - a / rows.length), 0),
    baseline: rows.reduce((sum, [, a]) => sum + Math.abs(a / rows.length), 0),
    predictedMagnitude: rows.reduce((sum, [p]) => sum + Math.abs(p / rows.length), 0),
    actualMagnitude: rows.reduce((sum, [, a]) => sum + Math.abs(a / rows.length), 0),
    wrong: rows.filter(([p, a]) => Math.sign(p) !== Math.sign(a)).length
  } : null;
  const describe = (label, rows) => {
    const s = summarize(rows);
    return s ? `${label} n=${s.n}：MAE ${s.mae.toFixed(2)} pp，零報酬基準 ${s.baseline.toFixed(2)} pp，${s.mae < s.baseline ? '低於' : s.mae > s.baseline ? '高於' : '等於'}基準；平均絕對幅度預測／實際 ${s.predictedMagnitude.toFixed(2)}／${s.actualMagnitude.toFixed(2)} pp；方向錯置 ${s.wrong} 筆` : `${label} n=0：沒有可比較樣本`;
  };
  output.textContent = `${describe('實際上漲組', groups.up)}。${describe('實際下跌組', groups.down)}。零報酬列不納入方向分組。`;
}
function calculateForwardPass(input, weight, bias) {
  const values = [input, weight, bias].map((value) => {
    if (String(value).trim() === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  });
  if (values.some((value) => value === null)) return null;
  const z = values[0] * values[1] + values[2];
  if (!Number.isFinite(z)) return null;
  const output = Math.max(0, z);
  return { z, output, reluDerivative: z > 0 ? 1 : 0 };
}
function renderForwardPassExercise() {
  const output = byId('forwardPassResult');
  if (!output) return;
  const result = calculateForwardPass(byId('forwardInput').value, byId('forwardWeight').value, byId('forwardBias').value);
  output.textContent = result === null ? '請輸入有限的 x、w 與 b。' : `z = wx + b = ${result.z.toFixed(2)}；ŷ = ReLU(z) = ${result.output.toFixed(2)}；ReLU′(z) = ${result.reluDerivative}，${result.reluDerivative ? '局部梯度可通過' : '此處局部梯度為零'}。`;
}
function calculateMultiForwardPass(x1, w1, x2, w2, bias, target = 1) {
  const values = [x1, w1, x2, w2, bias].map((value) => {
    if (value == null || String(value).trim() === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  });
  if (target == null || String(target).trim() === '') return null;
  const numericTarget = Number(target);
  if (!Number.isFinite(numericTarget)) return null;
  if (values.some((value) => value === null)) return null;
  const z = values[0] * values[1] + values[2] * values[3] + values[4];
  if (!Number.isFinite(z)) return null;
  const output = Math.max(0, z);
  const error = output - numericTarget;
  const loss = error ** 2;
  const reluDerivative = z > 0 ? 1 : 0;
  const delta = 2 * error * reluDerivative;
  const gradients = { w1: delta * values[0], w2: delta * values[2], bias: delta };
  if (![loss, delta, ...Object.values(gradients)].every(Number.isFinite)) return null;
  const contributionShares = z === 0 ? null : {
    x1: (values[0] * values[1]) / z,
    x2: (values[2] * values[3]) / z,
    bias: values[4] / z
  };
  if (contributionShares && !Object.values(contributionShares).every(Number.isFinite)) return null;
  return {
    z, output, target: numericTarget, loss, delta, gradients,
    contributions: { x1: values[0] * values[1], x2: values[2] * values[3], bias: values[4] },
    contributionShares
  };
}
function renderMultiForwardPassExercise() {
  const output = byId('multiForwardPassResult');
  if (!output) return;
  const values = ['multiInputX1','multiInputW1','multiInputX2','multiInputW2','multiInputBias'].map((id) => byId(id).value);
  const result = calculateMultiForwardPass(...values, byId('multiInputTarget').value);
  output.textContent = result === null ? '請輸入有限的 x₁、w₁、x₂、w₂、b 與目標 y。' : `加權貢獻：w₁x₁=${result.contributions.x1.toFixed(2)}、w₂x₂=${result.contributions.x2.toFixed(2)}、偏置 b=${result.contributions.bias.toFixed(2)}；相加得 z=${result.z.toFixed(2)}。${result.contributionShares ? `以 z 為 100% 的有號占比：w₁x₁=${(result.contributionShares.x1 * 100).toFixed(1)}%、w₂x₂=${(result.contributionShares.x2 * 100).toFixed(1)}%、b=${(result.contributionShares.bias * 100).toFixed(1)}%。` : 'z=0，總和為零時不定義占比；請看各項正負貢獻。'}ŷ = ReLU(z) = ${result.output.toFixed(2)}；目標 y = ${result.target.toFixed(2)}；L=(ŷ−y)² = ${result.loss.toFixed(2)}。反向傳播 δ=2(ŷ−y)ReLU′(z)=${result.delta.toFixed(2)}，∂L/∂w₁=${result.gradients.w1.toFixed(2)}、∂L/∂w₂=${result.gradients.w2.toFixed(2)}、∂L/∂b=${result.gradients.bias.toFixed(2)}。${result.z <= 0 ? '因 z≤0，ReLU′(z)=0，所以本例局部梯度為零。' : ''}`;
}
function calculateGradientUpdate(x1, w1, x2, w2, bias, target, rate) {
  if (rate == null || String(rate).trim() === '') return null;
  const forward = calculateMultiForwardPass(x1, w1, x2, w2, bias, target);
  const eta = Number(rate);
  if (!forward || !Number.isFinite(eta) || eta < 0 || eta > 1) return null;
  const updated = { w1: Number(w1) - eta * forward.gradients.w1, w2: Number(w2) - eta * forward.gradients.w2, bias: Number(bias) - eta * forward.gradients.bias };
  if (!Object.values(updated).every(Number.isFinite)) return null;
  const after = calculateMultiForwardPass(x1, updated.w1, x2, updated.w2, updated.bias, target);
  if (!after) return null;
  const gradientDotStep = Object.values(forward.gradients).reduce((sum, gradient, index) => {
    const key = ['w1', 'w2', 'bias'][index];
    return sum + gradient * (updated[key] - Number({w1, w2, bias}[key]));
  }, 0);
  const linearizedLoss = forward.loss + gradientDotStep;
  return Number.isFinite(linearizedLoss) ? { before: forward, updated, after, linearizedLoss, approximationGap: after.loss - linearizedLoss } : null;
}
function renderGradientUpdateExercise() {
  const output = byId('gradientUpdateResult');
  if (!output) return;
  const values = ['multiInputX1','multiInputW1','multiInputX2','multiInputW2','multiInputBias'].map(id => byId(id).value);
  const result = calculateGradientUpdate(...values, byId('updateTarget').value, byId('updateRate').value);
  const lossTrend = result && result.after.loss < result.before.loss ? '損失下降' : result && result.after.loss > result.before.loss ? '損失上升' : '損失不變';
  output.textContent = result ? `更新前 L=${result.before.loss.toFixed(4)}；梯度：∂L/∂w₁=${result.before.gradients.w1.toFixed(4)}、∂L/∂w₂=${result.before.gradients.w2.toFixed(4)}、∂L/∂b=${result.before.gradients.bias.toFixed(4)}；θ新=θ−η×梯度：w₁ ${values[1]}−${byId('updateRate').value}×(${result.before.gradients.w1.toFixed(4)})=${result.updated.w1.toFixed(4)}；w₂ ${values[3]}−${byId('updateRate').value}×(${result.before.gradients.w2.toFixed(4)})=${result.updated.w2.toFixed(4)}；b ${values[4]}−${byId('updateRate').value}×(${result.before.gradients.bias.toFixed(4)})=${result.updated.bias.toFixed(4)}；一階損失預測 L+∇L·Δθ=${result.linearizedLoss.toFixed(4)}（局部線性近似${result.linearizedLoss < 0 ? '，負值不可能是實際平方損失' : ''}）；更新後重新計算 L=${result.after.loss.toFixed(4)}（${lossTrend}），與一階預測差 ${result.approximationGap.toFixed(4)}。` : '請輸入有限數值；學習率需介於 0 與 1，且計算結果須在數值範圍內。';
}
function calculateFiniteDifferenceGradientCheck(x1, w1, x2, w2, bias, target, epsilon) {
  const raw = [x1, w1, x2, w2, bias, target, epsilon];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [a, u, b, v, c, y, step] = raw.map(Number);
  if (![a, u, b, v, c, y, step].every(Number.isFinite) || step < 1e-8 || step > 0.1) return null;
  const forward = calculateMultiForwardPass(a, u, b, v, c, y);
  if (!forward) return null;
  const parameters = [u, v, c];
  const analytic = [forward.gradients.w1, forward.gradients.w2, forward.gradients.bias];
  const lossAt = (index, offset) => {
    const shifted = [...parameters];
    shifted[index] += offset;
    const z = Math.max(0, a * shifted[0] + b * shifted[1] + shifted[2]);
    return (z - y) ** 2;
  };
  const numeric = parameters.map((_, index) => (lossAt(index, step) - lossAt(index, -step)) / (2 * step));
  const absoluteErrors = numeric.map((value, index) => Math.abs(value - analytic[index]));
  if (![...numeric, ...absoluteErrors].every(Number.isFinite)) return null;
  return { z: forward.z, loss: forward.loss, analytic, numeric, absoluteErrors, maxAbsoluteError: Math.max(...absoluteErrors), epsilon: step };
}
function renderFiniteDifferenceGradientCheck() {
  const output = byId('gradientCheckResult');
  if (!output) return;
  const values = ['multiInputX1','multiInputW1','multiInputX2','multiInputW2','multiInputBias','updateTarget','gradientCheckEpsilon'].map(id => byId(id).value);
  const result = calculateFiniteDifferenceGradientCheck(...values);
  const names = ['w₁','w₂','b'];
  output.textContent = result
    ? `沿用上方神經元，z=${result.z.toFixed(4)}、L=${result.loss.toFixed(4)}。中心差分 [L(θ+ε)−L(θ−ε)]/(2ε)，ε=${result.epsilon}：${names.map((name, index) => `${name} 解析=${result.analytic[index].toFixed(6)}、數值≈${result.numeric[index].toFixed(6)}、差=${result.absoluteErrors[index].toExponential(2)}`).join('；')}。最大絕對差=${result.maxAbsoluteError.toExponential(2)}。若 z 接近 ReLU 的 0 邊界，有限差分可能跨過折點，需另外解讀。`
    : '請輸入有限的神經元參數與目標；ε 需介於 0.00000001 與 0.1。';
}
function calculateBatchGradientUpdate(weight, gradients, rate) {
  if (!Array.isArray(gradients) || ![2, 4, 8].includes(gradients.length) || [weight, rate, ...gradients].some(value => value == null || String(value).trim() === '')) return null;
  const [w, eta, ...values] = [weight, rate, ...gradients].map(Number);
  if (![w, eta, ...values].every(Number.isFinite) || eta < 0 || eta > 1) return null;
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  const total = values.reduce((sum, value) => sum + value, 0);
  const totalAbsolute = values.reduce((sum, value) => sum + Math.abs(value), 0);
  const netToAbsoluteRatio = totalAbsolute === 0 ? null : Math.abs(total) / totalAbsolute;
  const updated = w - eta * average;
  const summedUpdate = w - eta * total;
  const positiveCount = values.filter(value => value > 0).length;
  const negativeCount = values.filter(value => value < 0).length;
  const zeroCount = values.length - positiveCount - negativeCount;
  const variance = values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length;
  const standardDeviation = Math.sqrt(variance);
  const leaveOneOutMeans = values.map((_, index) => (total - values[index]) / (values.length - 1));
  const leaveOneOutDeltas = leaveOneOutMeans.map(mean => mean - average);
  const influentialIndex = leaveOneOutDeltas.reduce((best, delta, index) => Math.abs(delta) > Math.abs(leaveOneOutDeltas[best]) ? index : best, 0);
  const maxLeaveOneOutShift = Math.abs(leaveOneOutDeltas[influentialIndex]);
  const influentialLeaveOneOutMean = leaveOneOutMeans[influentialIndex];
  const influentialSampleChangesDirection = average === 0
    ? influentialLeaveOneOutMean !== 0
    : influentialLeaveOneOutMean !== 0 && Math.sign(influentialLeaveOneOutMean) !== Math.sign(average);
  return [average, total, totalAbsolute, netToAbsoluteRatio, updated, summedUpdate, variance, standardDeviation, maxLeaveOneOutShift, leaveOneOutMeans[influentialIndex], leaveOneOutDeltas[influentialIndex]].every(value => value === null || Number.isFinite(value))
    ? { average, total, totalAbsolute, netToAbsoluteRatio, updated, summedUpdate, positiveCount, negativeCount, zeroCount, minGradient: Math.min(...values), maxGradient: Math.max(...values), variance, standardDeviation, maxLeaveOneOutShift, influentialSample: influentialIndex + 1, influentialGradient: values[influentialIndex], leaveOneOutMean: influentialLeaveOneOutMean, leaveOneOutDelta: leaveOneOutDeltas[influentialIndex], influentialSampleChangesDirection }
    : null;
}
function renderBatchGradientExercise() {
  const output = byId('batchGradientResult');
  if (!output) return;
  const gradientIds = ['batchGradientOne','batchGradientTwo','batchGradientThree','batchGradientFour'];
  const gradients = gradientIds.map(id => byId(id).value);
  const result = calculateBatchGradientUpdate(byId('batchWeight').value, gradients, byId('batchRate').value);
  const aligned = calculateBatchGradientUpdate(byId('batchWeight').value, [1,1,1,1], byId('batchRate').value);
  const doubled = calculateBatchGradientUpdate(byId('batchWeight').value, [...gradients, ...gradients], byId('batchRate').value);
  const miniBatchOne = calculateBatchGradientUpdate(byId('batchWeight').value, gradients.slice(0, 2), byId('batchRate').value);
  const miniBatchTwo = miniBatchOne && calculateBatchGradientUpdate(miniBatchOne.updated, gradients.slice(2), byId('batchRate').value);
  const regroupedMiniBatchOne = calculateBatchGradientUpdate(byId('batchWeight').value, [gradients[0], gradients[2]], byId('batchRate').value);
  const regroupedMiniBatchTwo = regroupedMiniBatchOne && calculateBatchGradientUpdate(regroupedMiniBatchOne.updated, [gradients[1], gradients[3]], byId('batchRate').value);
  output.textContent = result ? `梯度方向：${result.positiveCount} 筆為正、${result.negativeCount} 筆為負、${result.zeroCount} 筆為零。平均梯度 = (${gradients.join(' + ')}) ÷ ${gradients.length} = ${result.average.toFixed(4)}；樣本範圍 ${result.minGradient.toFixed(4)} 至 ${result.maxGradient.toFixed(4)}；母體變異數 ${result.variance.toFixed(4)}、標準差 ${result.standardDeviation.toFixed(4)}。${result.standardDeviation === 0 ? '梯度完全一致：每筆都等於平均值。' : '梯度有分散：標準差表示單筆梯度典型地偏離平均多少。'}若逐一拿掉一筆，平均梯度最多改變 ${result.maxLeaveOneOutShift.toFixed(4)}；第 ${result.influentialSample} 筆（梯度 ${result.influentialGradient}）影響最大，拿掉後平均變成 ${result.leaveOneOutMean.toFixed(4)}（改變 ${result.leaveOneOutDelta >= 0 ? '+' : ''}${result.leaveOneOutDelta.toFixed(4)}）。這是目前批次的敏感度，不是模型品質指標。淨梯度占總絕對梯度比例 = ${result.netToAbsoluteRatio === null ? '未定義（全部梯度為零）' : `${result.netToAbsoluteRatio.toFixed(4)}。${result.netToAbsoluteRatio === 0 ? '正負方向完全抵銷。' : result.netToAbsoluteRatio === 1 ? '各筆非零梯度方向一致，沒有抵銷。' : '數值越低，正負梯度抵銷越多。'}`}批次更新一次：w新 = ${byId('batchWeight').value} − ${byId('batchRate').value} × ${result.average.toFixed(4)} = ${result.updated.toFixed(4)}。${result.average === 0 && result.minGradient < 0 && result.maxGradient > 0 ? '平均梯度為 0，正負梯度完全抵銷，所以這次權重不變；每筆梯度仍不為零。' : result.positiveCount && result.negativeCount ? '正負梯度互相抵銷一部分；平均值決定這次更新方向。' : ''}固定目前權重與學習率作對照：四筆梯度全為 +1 時平均也是 1，新權重 ${aligned ? aligned.updated.toFixed(4) : '—'}；平均更新相同，但樣本方向較一致。若直接加總而不平均，總梯度 ${result.total.toFixed(4)} 會得到 w新=${result.summedUpdate.toFixed(4)}。把同一批四筆資料重複一次：8 筆平均仍為 ${doubled ? doubled.average.toFixed(4) : '—'}，新權重 ${doubled ? doubled.updated.toFixed(4) : '—'}；未平均總梯度變成 ${doubled ? doubled.total.toFixed(4) : '—'}，新權重 ${doubled ? doubled.summedUpdate.toFixed(4) : '—'}。` : '請輸入權重、四個有限梯度與學習率；學習率需介於 0 與 1。';
  if (result) output.textContent += ` 拿掉影響最大的一筆後，${result.influentialSampleChangesDirection ? '梯度符號改變或零更新變成非零更新，權重更新方向因此改變。' : '批次平均梯度的更新方向維持不變。'}`;
  if (miniBatchOne && miniBatchTwo) output.textContent += ` 固定這四筆合成梯度再比較批次大小：完整 batch 平均一次更新到 ${result.updated.toFixed(4)}；分成 (1–2) 與 (3–4) 兩個 mini-batch、每批各更新一次，權重依序 ${miniBatchOne.updated.toFixed(4)} → ${miniBatchTwo.updated.toFixed(4)}。此處刻意固定梯度以隔離更新次數的影響；真實訓練每次更新後會重新計算梯度。`;
  if (regroupedMiniBatchOne && regroupedMiniBatchTwo) output.textContent += ` 維持同四筆梯度，只改成 (1,3) 與 (2,4) 分批，權重路徑變為 ${regroupedMiniBatchOne.updated.toFixed(4)} → ${regroupedMiniBatchTwo.updated.toFixed(4)}；兩種 mini-batch 分組的終點同為 ${miniBatchTwo.updated.toFixed(4)}，但中間更新路徑會隨分組改變。單次 full-batch 只更新一次，因此終點是 ${result.updated.toFixed(4)}。`;
}
function calculateMomentumUpdate(beta, previousVelocity, gradient, weight, rate) {
  const raw = [beta, previousVelocity, gradient, weight, rate];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [b, previous, g, w, eta] = raw.map(Number);
  if (![b, previous, g, w, eta].every(Number.isFinite) || b < 0 || b > 1 || eta < 0 || eta > 1) return null;
  const velocity = b * previous + g;
  const updated = w - eta * velocity;
  return Number.isFinite(velocity) && Number.isFinite(updated) ? { velocity, updated } : null;
}
function calculateMomentumSteps(beta, previousVelocity, firstGradient, nextGradient, thirdGradient, weight, rate) {
  const raw = [beta, previousVelocity, firstGradient, nextGradient, thirdGradient, weight, rate];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [b, previous, first, next, third, initialWeight, eta] = raw.map(Number);
  if (![b, previous, first, next, third, initialWeight, eta].every(Number.isFinite) || b < 0 || b > 1 || eta < 0 || eta > 1) return null;
  const velocity1 = b * previous + first;
  const weight1 = initialWeight - eta * velocity1;
  const velocity2 = b * velocity1 + next;
  const weight2 = weight1 - eta * velocity2;
  const velocity3 = b * velocity2 + third;
  const weight3 = weight2 - eta * velocity3;
  return [velocity1, weight1, velocity2, weight2, velocity3, weight3].every(Number.isFinite)
    ? { velocity1, weight1, velocity2, weight2, velocity3, weight3 } : null;
}
function renderMomentumExercise() {
  const output = byId('momentumResult');
  if (!output) return;
  const [beta, previous, gradient, nextGradient, thirdGradient, weight, rate] = ['momentumBeta','momentumPrevious','momentumGradient','momentumNextGradient','momentumThirdGradient','momentumWeight','momentumRate'].map(id => byId(id).value);
  const result = calculateMomentumSteps(beta, previous, gradient, nextGradient, thirdGradient, weight, rate);
  const previousContribution = Number(beta) * Number(previous);
  const noMomentum = calculateMomentumSteps(0, previous, gradient, nextGradient, thirdGradient, weight, rate);
  const lowerMomentum = calculateMomentumSteps(0.5, previous, gradient, nextGradient, thirdGradient, weight, rate);
  const opposingHistory = calculateMomentumUpdate(0.5,-0.5,1,2,0.1);
  output.textContent = result ? `第一步：βvₜ₋₁ = ${beta} × ${previous} = ${previousContribution.toFixed(4)}；vₜ = ${result.velocity1.toFixed(4)}，wₜ = ${result.weight1.toFixed(4)}。第二步沿用 vₜ：vₜ₊₁ = ${beta} × ${result.velocity1.toFixed(4)} + ${Number(nextGradient).toFixed(4)} = ${result.velocity2.toFixed(4)}，wₜ₊₁ = ${result.weight2.toFixed(4)}。第三步加入梯度 ${Number(byId('momentumThirdGradient').value).toFixed(4)}：vₜ₊₂ = ${beta} × ${result.velocity2.toFixed(4)} + ${Number(byId('momentumThirdGradient').value).toFixed(4)} = ${result.velocity3.toFixed(4)}，wₜ₊₂ = ${result.weight3.toFixed(5)}。第三步速度${Math.sign(result.velocity3) === Math.sign(result.velocity2) ? '尚未反向' : '已反向'}（${result.velocity2.toFixed(4)} → ${result.velocity3.toFixed(4)}），因此權重${result.weight3 > result.weight2 ? '上升' : result.weight3 < result.weight2 ? '下降' : '不變'}（${result.weight2.toFixed(5)} → ${result.weight3.toFixed(5)}）。這顯示梯度反向不代表累積速度會立刻反向。不保留動量（β=0）時，三步權重為 ${noMomentum ? `${noMomentum.weight1.toFixed(4)} → ${noMomentum.weight2.toFixed(4)} → ${noMomentum.weight3.toFixed(5)}` : '—'}；目前設定三步為 ${result.weight1.toFixed(4)} → ${result.weight2.toFixed(4)} → ${result.weight3.toFixed(5)}。β=0.5 時三步為 ${lowerMomentum ? `${lowerMomentum.weight1.toFixed(4)} → ${lowerMomentum.weight2.toFixed(4)} → ${lowerMomentum.weight3.toFixed(5)}` : '—'}。若歷史速度反向（β=0.5、vₜ₋₁=−0.5、gₜ=1），保留貢獻 −0.2500 會抵銷部分本步梯度，合成速度 0.7500，權重變為 1.9250。` : '請輸入七個有限數值；β 與學習率需介於 0 與 1。';
}
function calculateMomentumDirection(...components) {
  if (!components.length || components.length % 2 !== 0 || components.some(value => value == null || String(value).trim() === '')) return null;
  const values = components.map(Number);
  if (!values.every(Number.isFinite)) return null;
  const dimensions = values.length / 2, velocity = values.slice(0, dimensions), gradient = values.slice(dimensions);
  const vNorm = Math.hypot(...velocity), gNorm = Math.hypot(...gradient);
  const dot = velocity.reduce((sum, value, index) => sum + value * gradient[index], 0);
  if (![vNorm, gNorm, dot].every(Number.isFinite)) return null;
  if (vNorm === 0 || gNorm === 0) return { dimensions, vNorm, gNorm, dot, cosine: null, angleDegrees: null, parallel: null, perpendicular: null, relation: '零向量沒有可定義的方向' };
  // Normalize before multiplying so direction remains observable when the
  // product of two finite vector lengths would underflow or overflow.
  const unitGradient = gradient.map(value => value / gNorm);
  const cosine = Math.max(-1, Math.min(1, velocity.reduce((sum, value, index) => sum + (value / vNorm) * unitGradient[index], 0)));
  if (!Number.isFinite(cosine)) return null;
  const parallel = velocity.reduce((sum, value, index) => sum + value * unitGradient[index], 0);
  const perpendicular = Math.hypot(...velocity.map((value, index) => value - parallel * unitGradient[index]));
  if (![parallel, perpendicular].every(Number.isFinite)) return null;
  const angleDegrees = Math.acos(cosine) * 180 / Math.PI;
  const relation = cosine > 0.5 ? '大致同向：歷史速度會加強本步梯度方向'
    : cosine < -0.5 ? '大致反向：歷史速度會抵銷本步梯度方向'
      : '方向接近垂直：兩者的方向投影較小';
  return { dimensions, vNorm, gNorm, dot, cosine, angleDegrees, parallel, perpendicular, relation };
}
function renderMomentumDirection() {
  const output = byId('momentumDirectionResult');
  if (!output) return;
  const dimensions = Number(byId('momentumVectorDimension')?.value || 3);
  const ids = dimensions === 2
    ? ['momentumVectorV1','momentumVectorV2','momentumVectorG1','momentumVectorG2']
    : ['momentumVectorV1','momentumVectorV2','momentumVectorV3','momentumVectorG1','momentumVectorG2','momentumVectorG3'];
  if (typeof document !== 'undefined') document.querySelectorAll('[data-momentum-dimension="3"]').forEach((label) => { label.hidden = dimensions === 2; });
  const result = calculateMomentumDirection(...ids.map(id => byId(id).value));
  const decompositionCheck = result?.parallel == null || result?.perpendicular == null
    ? '分解核對：未定義（零向量沒有方向）'
    : `分解核對：|v|²=${(result.vNorm ** 2).toFixed(4)}，平行分量²＋垂直分量²=${(result.parallel ** 2 + result.perpendicular ** 2).toFixed(4)}`;
  output.textContent = result
    ? `維度=${result.dimensions}；|v|=${result.vNorm.toFixed(4)}；|g|=${result.gNorm.toFixed(4)}；v·g=${result.dot.toFixed(4)}；方向餘弦=${result.cosine == null ? '未定義' : result.cosine.toFixed(4)}；夾角=${result.angleDegrees == null ? '未定義' : `${result.angleDegrees.toFixed(2)}°`}；沿梯度方向的速度分量=${result.parallel == null ? '未定義' : result.parallel.toFixed(4)}；垂直分量大小=${result.perpendicular == null ? '未定義' : result.perpendicular.toFixed(4)}；${decompositionCheck}。${result.relation}`
    : '請輸入相同維度且有限的速度與梯度分量。';
}
function calculateActivationComparison(input, target = 1) {
  if ([input, target].some((value) => value == null || String(value).trim() === '')) return null;
  const z = Number(input), y = Number(target);
  if (![z, y].every(Number.isFinite)) return null;
  const sigmoid = z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z));
  const relu = Math.max(0, z);
  const tanh = Math.tanh(z);
  // Use the equivalent exponential form so rounding sigmoid to 1 does not
  // erase its small, nonzero derivative on the positive saturation tail.
  const sigmoidTail = Math.exp(-Math.abs(z));
  const sigmoidGradient = sigmoidTail / ((1 + sigmoidTail) ** 2);
  const reluGradient = z > 0 ? 1 : 0;
  // 1 - tanh(z)^2 cancels to zero once tanh rounds to ±1. Squaring
  // exp(-|z|) delays underflow compared with exp(-2|z|), while remaining
  // finite for every finite z (including magnitudes whose doubled value overflows).
  const tanhTail = Math.exp(-Math.abs(z));
  const tanhTailSquared = tanhTail * tanhTail;
  const tanhGradient = (4 * tanhTailSquared) / ((1 + tanhTailSquared) ** 2);
  // Compute the sigmoid residual from its small tail directly. `sigmoid`
  // rounds to 1 for large positive z, which would erase the residual even
  // though the stable local derivative above is still nonzero.
  const sigmoidResidual = z >= 0
    ? ((1 - y) - sigmoidTail * y) / (1 + sigmoidTail)
    : (sigmoidTail * (1 - y) - y) / (1 + sigmoidTail);
  const sigmoidLossGradient = 2 * sigmoidResidual * sigmoidGradient;
  const reluLossGradient = 2 * (relu - y) * reluGradient;
  const tanhLossGradient = 2 * (tanh - y) * tanhGradient;
  const sigmoidLoss = sigmoidResidual ** 2;
  const reluLoss = (relu - y) ** 2;
  const tanhLoss = (tanh - y) ** 2;
  const targetReachability = {
    sigmoid: y > 0 && y < 1,
    relu: y >= 0,
    tanh: y > -1 && y < 1,
  };
  const reluDeadZone = z <= 0 && y > 0;
  const values = [sigmoid, relu, tanh, sigmoidGradient, reluGradient, tanhGradient, sigmoidLossGradient, reluLossGradient, tanhLossGradient, sigmoidLoss, reluLoss, tanhLoss];
  // Finite inputs can still overflow when squared; reject the whole exercise
  // instead of presenting Infinity as a valid loss or gradient result.
  return values.every(Number.isFinite)
    ? { z, target: y, sigmoid, relu, tanh, sigmoidGradient, reluGradient, tanhGradient, sigmoidLossGradient, reluLossGradient, tanhLossGradient, sigmoidLoss, reluLoss, tanhLoss, targetReachability, reluDeadZone }
    : null;
}
function renderActivationExercise() {
  const output = byId('activationResult');
  if (!output) return;
  const result = calculateActivationComparison(byId('activationInput').value, byId('activationTarget').value);
  const showDerivative = (value) => value !== 0 && Math.abs(value) < 0.00005 ? value.toExponential(3) : value.toFixed(4);
  const descentDirection = (gradient) => gradient > 0 ? '梯度下降會降低 z' : gradient < 0 ? '梯度下降會提高 z' : '梯度下降不改變 z';
  output.textContent = result
    ? `z=${result.z}、y=${result.target}：Sigmoid=${result.sigmoid.toFixed(4)}（平方損失 ${result.sigmoidLoss.toFixed(4)}、局部導數 ${showDerivative(result.sigmoidGradient)}、平方損失梯度 ${result.sigmoidLossGradient.toExponential(3)}、目標${result.targetReachability.sigmoid ? '在' : '不在'}輸出範圍；${descentDirection(result.sigmoidLossGradient)}）；ReLU=${result.relu.toFixed(4)}（平方損失 ${result.reluLoss.toFixed(4)}、局部導數 ${showDerivative(result.reluGradient)}、平方損失梯度 ${result.reluLossGradient.toExponential(3)}、目標${result.targetReachability.relu ? '在' : '不在'}輸出範圍；${descentDirection(result.reluLossGradient)}）；Tanh=${result.tanh.toFixed(4)}（平方損失 ${result.tanhLoss.toFixed(4)}、局部導數 ${showDerivative(result.tanhGradient)}、平方損失梯度 ${result.tanhLossGradient.toExponential(3)}、目標${result.targetReachability.tanh ? '在' : '不在'}輸出範圍；${descentDirection(result.tanhLossGradient)}）。${result.reluDeadZone ? 'ReLU 負區提示：目標雖在輸出範圍且損失非零，局部導數仍為零；只靠這個神經元的梯度更新無法離開負區。' : ''}${Math.abs(result.z) >= 4 ? '對稱輸入 +|z| 與 −|z| 的 Sigmoid／Tanh 局部導數相同；方向相反時輸出不同，但飽和尾端都可能讓梯度很小。' : ''}`
    : '請輸入有限的神經元值 z 與目標 y。';
}
function calculateGradientClipping(weight, gradient, limit, rate) {
  const raw = [weight, gradient, limit, rate];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [w, g, max, eta] = raw.map(Number);
  if (![w, g, max, eta].every(Number.isFinite) || max < 0 || eta < 0) return null;
  const clipped = Math.max(-max, Math.min(max, g));
  const updated = w - eta * clipped;
  const unclippedUpdated = w - eta * g;
  const retainedFraction = g === 0 ? 1 : Math.abs(clipped / g);
  return Number.isFinite(clipped) && Number.isFinite(updated) && Number.isFinite(unclippedUpdated)
    ? { clipped, updated, unclippedUpdated, unclippedStep: Math.abs(eta * g), clippedStep: Math.abs(eta * clipped), retainedFraction } : null;
}
function calculateGradientDescentTrace(startWeight, rate, steps, curvature = 1) {
  const raw = [startWeight, rate, steps, curvature];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [initial, eta, count, c] = raw.map(Number);
  if (![initial, eta, count, c].every(Number.isFinite) || eta < 0 || eta > 1 || !Number.isInteger(count) || count < 1 || count > 10 || c < 0.1 || c > 5) return null;
  const rows = [{ step: 0, weight: initial, gradient: 2 * c * (initial - 1), loss: c * (initial - 1) ** 2 }];
  for (let step = 1; step <= count; step += 1) {
    const previous = rows[step - 1];
    const weight = previous.weight - eta * previous.gradient;
    const gradient = 2 * c * (weight - 1);
    const loss = c * (weight - 1) ** 2;
    if (![weight, gradient, loss].every(Number.isFinite)) return null;
    rows.push({ step, weight, gradient, loss });
  }
  return rows;
}
function gradientDescentDynamics(rate, curvature) {
  const multiplier = 1 - 2 * Number(rate) * Number(curvature);
  const magnitude = Math.abs(multiplier);
  const dynamics = magnitude < 1e-12
    ? '一步到達最低點'
    : magnitude < 1 - 1e-12
      ? (multiplier < 0 ? '交替越過最低點並收斂' : '不越過最低點而收斂')
      : (multiplier < 0
        ? (Math.abs(magnitude - 1) < 1e-12 ? '邊界振盪' : '交替發散')
        : '不更新');
  return { multiplier, dynamics };
}
function calculateAdamFirstStep(gradient, rate, beta1, beta2, epsilon = 1e-8) {
  if ([gradient, rate, beta1, beta2].some((value) => String(value).trim() === '')) return null;
  const g = Number(gradient), eta = Number(rate), b1 = Number(beta1), b2 = Number(beta2);
  if (![g, eta, b1, b2, epsilon].every(Number.isFinite) || eta <= 0 || eta > 1 || b1 < 0 || b1 >= 1 || b2 < 0 || b2 >= 1 || epsilon <= 0) return null;
  const m = (1 - b1) * g;
  const v = (1 - b2) * g * g;
  const mHat = m / (1 - b1);
  const vHat = v / (1 - b2);
  const adamDelta = eta * mHat / (Math.sqrt(vHat) + epsilon);
  const sgdDelta = eta * g;
  const values = [m, v, mHat, vHat, adamDelta, sgdDelta, 1 - adamDelta, 1 - sgdDelta];
  if (!values.every(Number.isFinite)) return null;
  return {m, v, mHat, vHat, adamDelta, sgdDelta, adamWeight: 1 - adamDelta, sgdWeight: 1 - sgdDelta};
}

function renderAdamStepExercise() {
  const output = byId('adamStepResult');
  if (!output) return;
  const result = calculateAdamFirstStep(byId('adamGradient').value, byId('adamRate').value, byId('adamBeta1').value, byId('adamBeta2').value);
  output.textContent = result
    ? `第 1 步：m₁=${result.m.toFixed(4)}、v₁=${result.v.toFixed(4)}；偏差校正後 m̂₁=${result.mHat.toFixed(4)}、v̂₁=${result.vHat.toFixed(4)}。SGD 位移=${result.sgdDelta.toFixed(4)}，w₁=${result.sgdWeight.toFixed(4)}；Adam 位移=${result.adamDelta.toFixed(4)}，w₁=${result.adamWeight.toFixed(4)}。`
    : '請輸入有限梯度、0 < η ≤ 1，以及 0 ≤ β₁、β₂ < 1。';
}

function calculateAdamTwoSteps(firstGradient, secondGradient, rate, beta1, beta2, epsilon = 1e-8) {
  if ([firstGradient, secondGradient, rate, beta1, beta2, epsilon].some((value) => String(value).trim() === '')) return null;
  const g1 = Number(firstGradient), g2 = Number(secondGradient), eta = Number(rate), b1 = Number(beta1), b2 = Number(beta2), eps = Number(epsilon);
  if (![g1, g2, eta, b1, b2, eps].every(Number.isFinite) || eta <= 0 || eta > 1 || b1 < 0 || b1 >= 1 || b2 < 0 || b2 >= 1 || eps <= 0 || eps > 1) return null;
  const m1 = (1 - b1) * g1, v1 = (1 - b2) * g1 * g1;
  const historyContribution2 = b1 * m1, currentContribution2 = (1 - b1) * g2;
  const secondMomentHistory2 = b2 * v1, secondMomentCurrent2 = (1 - b2) * g2 * g2;
  const m2 = historyContribution2 + currentContribution2, v2 = secondMomentHistory2 + secondMomentCurrent2;
  const mHat2 = m2 / (1 - b1 ** 2), vHat2 = v2 / (1 - b2 ** 2);
  if ((g1 !== 0 && v1 === 0) || (g2 !== 0 && secondMomentCurrent2 === 0) || ((g1 !== 0 || g2 !== 0) && v2 === 0)) return null;
  const adamDelta1 = eta * g1 / (Math.abs(g1) + eps);
  const adamDelta2 = eta * mHat2 / (Math.sqrt(vHat2) + eps);
  const sgdWeight2 = 1 - eta * g1 - eta * g2, adamWeight1 = 1 - adamDelta1, adamWeight2 = adamWeight1 - adamDelta2;
  if (![m1, v1, m2, v2, secondMomentHistory2, secondMomentCurrent2, mHat2, vHat2, adamDelta1, adamDelta2, sgdWeight2, adamWeight1, adamWeight2].every(Number.isFinite)) return null;
  const displayMoment = Math.abs(mHat2) < 0.00005 ? mHat2.toExponential(2) : mHat2.toFixed(4);
  const directionNote = g2 === 0 && mHat2 === 0
    ? '當步梯度 g₂ 與 Adam 校正動差 m̂₂ 都為零；兩者皆沒有方向。'
    : g2 === 0
      ? `當步梯度 g₂=0.0000 沒有方向；Adam 校正動差 m̂₂=${displayMoment} 仍保留先前累積方向。`
      : mHat2 === 0
        ? `Adam 校正動差 m̂₂=0.0000；歷史與當步梯度恰好抵銷，因此 Adam 第二步沒有更新方向，當步梯度 g₂=${g2.toFixed(4)} 仍有方向。`
        : Math.sign(g2) !== Math.sign(mHat2)
      ? `當步梯度 g₂=${g2.toFixed(4)} 與 Adam 校正動差 m̂₂=${displayMoment} 方向相反；SGD 依 g₂ 更新，Adam 依累積動差更新。`
      : `當步梯度 g₂=${g2.toFixed(4)} 與 Adam 校正動差 m̂₂=${displayMoment} 方向相同。`;
  return {historyContribution2, currentContribution2, secondMomentHistory2, secondMomentCurrent2, m2, v2, mHat2, vHat2, denominator2: Math.sqrt(vHat2) + eps, adamDelta2, sgdWeight2, adamWeight1, adamWeight2, directionNote};
}

function renderAdamTwoStepExercise() {
  const output = byId('adamTwoStepResult');
  if (!output) return;
  const epsilon = byId('adamEpsilon2').value;
  const firstGradient = byId('adamGradient1').value, secondGradient = byId('adamGradient2').value, rate = byId('adamRate2').value, beta1 = byId('adamBeta12').value, beta2 = byId('adamBeta22').value;
  const result = calculateAdamTwoSteps(firstGradient, secondGradient, rate, beta1, beta2, epsilon);
  // β₂=0 is valid for the comparison even though the calculator rejects it as
  // a user-selected beta; calculate its denominator directly for this limit.
  const noSquareGradientMemory = result ? (() => {
    const g1 = Number(firstGradient), g2 = Number(secondGradient), eta = Number(rate), b1 = Number(beta1), eps = Number(epsilon);
    const m2 = b1 * (1 - b1) * g1 + (1 - b1) * g2;
    const mHat2 = m2 / (1 - b1 ** 2), vHat2 = g2 * g2;
    const denominator2 = Math.sqrt(vHat2) + eps;
    return {denominator2, adamDelta2: eta * mHat2 / denominator2};
  })() : null;
  const scaledGradients = result ? calculateAdamTwoSteps(Number(firstGradient) * 10, Number(secondGradient) * 10, rate, beta1, beta2, epsilon) : null;
  const scaledSgdWeight2 = 1 - Number(rate) * 10 * (Number(firstGradient) + Number(secondGradient));
  const scaledComparison = scaledGradients && Number.isFinite(scaledSgdWeight2)
    ? `Adam 更新量 ${scaledGradients.adamDelta2.toFixed(4)}；SGD w₂=${scaledSgdWeight2.toFixed(4)}（原本 ${result.sgdWeight2.toFixed(4)}）`
    : '放大後超出數值範圍';
  output.textContent = result
    ? `第 2 步動差拆解：歷史項 β₁m₁=${result.historyContribution2.toFixed(4)}，當步項 (1−β₁)g₂=${result.currentContribution2.toFixed(4)}，相加 m₂=${result.m2.toFixed(4)}；平方梯度歷史項 β₂v₁=${result.secondMomentHistory2.toFixed(6)}，當步項 (1−β₂)g₂²=${result.secondMomentCurrent2.toFixed(6)}，相加 v₂=${result.v2.toFixed(6)}。校正後 m̂₂=${Math.abs(result.mHat2) < 0.00005 ? result.mHat2.toExponential(2) : result.mHat2.toFixed(4)}、v̂₂=${result.vHat2.toFixed(4)}。${result.directionNote}第二步分母 √v̂₂+ε=${Math.sqrt(result.vHat2).toFixed(4)}+${Number(epsilon).toExponential(1)}=${result.denominator2.toFixed(4)}，更新量 ηm̂₂/(√v̂₂+ε)=${result.adamDelta2.toFixed(4)}，所以權重改變 −${result.adamDelta2.toFixed(4)}。β₂ 記憶對照（相同梯度）：β₂=0 時分母 ${noSquareGradientMemory.denominator2.toFixed(4)}、更新量 ${noSquareGradientMemory.adamDelta2.toFixed(4)}；目前 β₂=${Number(beta2).toFixed(3)} 時分母 ${result.denominator2.toFixed(4)}、更新量 ${result.adamDelta2.toFixed(4)}。ε 對照（相同梯度與動差）：ε=0 時分母 ${Math.sqrt(result.vHat2).toFixed(4)}、更新量 ${Math.sqrt(result.vHat2) === 0 ? '未定義' : (Number(rate) * result.mHat2 / Math.sqrt(result.vHat2)).toFixed(4)}；目前 ε=${Number(epsilon).toExponential(1)} 時分母 ${result.denominator2.toFixed(4)}、更新量 ${result.adamDelta2.toFixed(4)}。梯度同乘 10（固定 β、η、ε）：${scaledComparison}。這是固定梯度序列，僅示範近似尺度不變性，ε 仍會造成差異。SGD 的 w₂=${result.sgdWeight2.toFixed(4)}；Adam 的 w₁=${result.adamWeight1.toFixed(4)} → w₂=${result.adamWeight2.toFixed(4)}。`
    : '請輸入兩個有限梯度、0 < η ≤ 1、0 ≤ β₁、β₂ < 1，以及 0 < ε ≤ 1；若極小梯度平方後低於數值範圍，請改用較大的算例梯度。';
}

function classifyOpposingGradients(dataGradient, penaltyGradient) {
  const dataMagnitude = Math.abs(dataGradient), penaltyMagnitude = Math.abs(penaltyGradient);
  if (dataMagnitude === penaltyMagnitude) return 'cancel';
  return dataMagnitude > penaltyMagnitude ? 'data' : 'penalty';
}

function calculateL2Regularization(weight, rate, strength) {
  if ([weight, rate, strength].some((value) => String(value).trim() === '')) return null;
  const w = Number(weight), eta = Number(rate), lambda = Number(strength);
  if (![w, eta, lambda].every(Number.isFinite) || eta < 0 || eta > 10 || lambda < 0 || lambda > 10) return null;
  const dataLossBefore = (w - 1) ** 2;
  const penaltyBefore = lambda * w ** 2;
  const dataGradient = 2 * (w - 1);
  const penaltyGradient = 2 * lambda * w;
  // L(w) = (w-1)^2 + lambda*w^2 has curvature 2(1+lambda).
  // For a quadratic, fixed-rate gradient descent contracts error when
  // 0 < eta < 2/curvature = 1/(1+lambda).
  const criticalRate = 1 / (1 + lambda);
  const optimumWeight = 1 / (1 + lambda);
  const errorMultiplier = 1 - 2 * eta * (1 + lambda);
  const stabilitySweep = [0.5, 1, 1.5].map((factor) => {
    const sweepRate = criticalRate * factor;
    const multiplier = 1 - 2 * sweepRate * (1 + lambda);
    const behavior = multiplier === 0 ? '一步到達最低點' : Math.abs(multiplier) < 1 ? '誤差縮小' : Math.abs(multiplier) === 1 ? '等距反向' : '誤差放大';
    return { rate: sweepRate, multiplier, behavior };
  });
  const distanceToOptimumBefore = Math.abs(w - optimumWeight);
  const optimumDataLoss = (optimumWeight - 1) ** 2;
  const optimumPenalty = lambda * optimumWeight ** 2;
  const optimumTotalLoss = optimumDataLoss + optimumPenalty;
  const optimumNote = lambda === 0
    ? 'λ=0 時沒有懲罰，最低點仍是資料目標偏好的 w=1。'
    : 'λ>0 時懲罰會把最低點拉向零，低於資料單獨偏好的 1。';
  const stabilityNote = eta === 0
    ? '穩定性：η=0，權重不移動。'
    : eta < criticalRate
      ? '穩定性：η 小於臨界值，這個二次目標的誤差會逐步縮小。'
      : eta === criticalRate
        ? '穩定性：η 等於臨界值，誤差每步反號且大小不變。'
        : '穩定性：η 大於臨界值，這個二次目標的誤差會逐步放大。';
  const totalGradient = dataGradient + penaltyGradient;
  const directionNote = (() => {
    if (dataGradient === 0 && penaltyGradient === 0) return '方向判讀：兩項梯度都為零，這一步權重不變。';
    if (penaltyGradient === 0) return '方向判讀：λ=0，更新只由資料梯度決定。';
    if (dataGradient === 0) return '方向判讀：資料梯度為零，更新只由 L2 懲罰梯度決定。';
    if (Math.sign(dataGradient) === Math.sign(penaltyGradient)) return `方向判讀：兩項梯度同向，合力讓權重${totalGradient > 0 ? '下降' : '上升'}。`;
    const dominant = classifyOpposingGradients(dataGradient, penaltyGradient);
    if (dominant === 'cancel') return '方向判讀：資料梯度與懲罰梯度相反且等大，正好抵銷。';
    return `方向判讀：資料梯度與懲罰梯度相反，${dominant === 'data' ? '資料項' : '懲罰項'}主導合力方向。`;
  })();
  const nextWeight = w - eta * totalGradient;
  const distanceToOptimumAfter = Math.abs(nextWeight - optimumWeight);
  const dataLossAfter = (nextWeight - 1) ** 2;
  const penaltyAfter = lambda * nextWeight ** 2;
  const totalBefore = dataLossBefore + penaltyBefore;
  const totalAfter = dataLossAfter + penaltyAfter;
  const dataLossChange = dataLossAfter - dataLossBefore;
  const penaltyChange = penaltyAfter - penaltyBefore;
  const values = [dataLossBefore, penaltyBefore, dataGradient, penaltyGradient, totalGradient, nextWeight, dataLossAfter, penaltyAfter, totalBefore, totalAfter];
  if (!values.every(Number.isFinite)) return null;
  const dataLossState = Math.sign(dataLossAfter - dataLossBefore);
  const totalLossState = Math.sign(totalAfter - totalBefore);
  const dataLossDirection = dataLossState < 0 ? '資料損失下降' : dataLossState > 0 ? '資料損失上升' : '資料損失不變';
  const totalLossDirection = totalLossState < 0 ? '總損失下降' : totalLossState > 0 ? '總損失上升' : '總損失不變';
  const penaltyState = Math.sign(penaltyChange);
  const penaltyDirection = penaltyState < 0 ? '懲罰下降' : penaltyState > 0 ? '懲罰上升' : '懲罰不變';
  const lossDirectionNote = dataLossState === -1 && penaltyState === 1 && totalLossState === -1
    ? `${dataLossDirection}；${penaltyDirection}，但資料項下降較多，所以${totalLossDirection}。`
    : dataLossState === 1 && penaltyState === -1 && totalLossState === 1
      ? `${dataLossDirection}；${penaltyDirection}，但資料項上升較多，所以${totalLossDirection}。`
      : `${dataLossDirection}；${penaltyDirection}；${totalLossDirection}。`;
  const cancellationExample = calculateL2CancellationExample();
  return {dataLossBefore, penaltyBefore, dataGradient, penaltyGradient, totalGradient, directionNote, nextWeight, dataLossAfter, penaltyAfter, totalBefore, totalAfter, dataLossChange, penaltyChange, dataLossDirection, totalLossDirection, lossDirectionNote, criticalRate, stabilitySweep, optimumWeight, optimumDataLoss, optimumPenalty, optimumTotalLoss, optimumNote, stabilityNote, errorMultiplier, distanceToOptimumBefore, distanceToOptimumAfter, cancellationExample};
}

function calculateWeightDecayComparison(gradient, weight, rate, decay) {
  if ([gradient, weight, rate, decay].some((value) => String(value).trim() === '')) return null;
  const g = Number(gradient), w = Number(weight), eta = Number(rate), wd = Number(decay);
  if (![g, w, eta, wd].every(Number.isFinite) || eta < 0 || eta > 10 || wd < 0 || wd > 10) return null;
  const coupled = w - eta * (g + wd * w);
  const decoupled = (1 - eta * wd) * w - eta * g;
  if (![coupled, decoupled].every(Number.isFinite)) return null;
  const gradientStep = -eta * g;
  const decayStep = -eta * wd * w;
  const rawDifference = decoupled - coupled;
  const difference = Math.abs(rawDifference) <= Number.EPSILON * Math.max(1, Math.abs(coupled), Math.abs(decoupled)) * 4 ? 0 : rawDifference;
  return {coupled, decoupled, difference, gradientStep, decayStep, retentionFactor: 1 - eta * wd};
}

function renderWeightDecayComparison() {
  const output = byId('weightDecayComparisonResult');
  if (!output) return;
  const result = calculateWeightDecayComparison(byId('weightDecayGradient').value, byId('weightDecayWeight').value, byId('weightDecayRate').value, byId('weightDecayStrength').value);
  output.textContent = result
    ? `同一梯度 g=${Number(byId('weightDecayGradient').value).toFixed(2)}、w=${Number(byId('weightDecayWeight').value).toFixed(2)}、η=${Number(byId('weightDecayRate').value).toFixed(2)}、λ=${Number(byId('weightDecayStrength').value).toFixed(2)}：權重保留比例 1−ηλ=${result.retentionFactor.toFixed(4)}；梯度更新量 −ηg=${result.gradientStep.toFixed(4)}；衰減更新量 −ηλw=${result.decayStep.toFixed(4)}。耦合 L2 更新 w=${result.coupled.toFixed(4)}；解耦權重衰減 w=${result.decoupled.toFixed(4)}；差=${result.difference.toFixed(4)}。方向拆解：梯度更新${result.gradientStep > 0 ? '增加' : result.gradientStep < 0 ? '減少' : '不改變'}權重，衰減更新${result.decayStep < 0 ? '減少' : result.decayStep > 0 ? '增加' : '不改變'}權重。`
    : '請輸入有限數值；η 與 λ 需介於 0 到 10。';
  renderAdamWeightDecayComparison();
}

function calculateAdamWeightDecayComparison(gradient, weight, rate, decay, epsilon = 1e-8) {
  if ([gradient, weight, rate, decay].some((value) => String(value).trim() === '')) return null;
  const g = Number(gradient), w = Number(weight), eta = Number(rate), wd = Number(decay);
  if (![g, w, eta, wd, epsilon].every(Number.isFinite) || eta < 0 || eta > 10 || wd < 0 || wd > 10 || epsilon <= 0) return null;
  const coupledGradient = g + wd * w;
  const coupled = w - eta * coupledGradient / (Math.abs(coupledGradient) + epsilon);
  const decoupled = w - eta * g / (Math.abs(g) + epsilon) - eta * wd * w;
  if (![coupledGradient, coupled, decoupled].every(Number.isFinite)) return null;
  return {coupled, decoupled, difference: decoupled - coupled};
}

function renderAdamWeightDecayComparison() {
  const output = byId('adamWeightDecayResult');
  if (!output) return;
  const result = calculateAdamWeightDecayComparison(byId('weightDecayGradient').value, byId('weightDecayWeight').value, byId('weightDecayRate').value, byId('weightDecayStrength').value);
  output.textContent = result
    ? `Adam 第一步（ε=10⁻⁸）：耦合 L2 w=${result.coupled.toFixed(4)}；解耦權重衰減 w=${result.decoupled.toFixed(4)}；差=${result.difference.toFixed(4)}。`
    : 'Adam 對照暫無結果；請先輸入有效數值。';
}

function calculateL2CancellationExample(ratio = 0.5) {
  const parsedRatio = Number(ratio);
  if (!Number.isFinite(parsedRatio) || parsedRatio < 0 || parsedRatio > 2) return null;
  const dataGradient = 2e-13, penaltyGradient = -2e-13 * parsedRatio;
  const relativeDifference = Math.abs(Math.abs(dataGradient) - Math.abs(penaltyGradient)) / Math.max(Math.abs(dataGradient), Math.abs(penaltyGradient));
  const classification = classifyOpposingGradients(dataGradient, penaltyGradient);
  const relativeDifferenceText = relativeDifference < 0.005 ? relativeDifference.toExponential(1) : relativeDifference.toFixed(2);
  const description = classification === 'cancel' ? '正好抵銷' : `${relativeDifferenceText} 的相對差，${classification === 'data' ? '資料項' : '懲罰項'}主導`;
  return {dataGradient, penaltyGradient, relativeDifference, classification, description};
}

function renderL2RegularizationExercise() {
  const output = byId('l2RegularizationResult');
  if (!output) return;
  const result = calculateL2Regularization(byId('l2Weight').value, byId('l2Rate').value, byId('l2Lambda').value);
  output.textContent = result
    ? `資料損失前=${result.dataLossBefore.toFixed(4)}、懲罰 λw²=${result.penaltyBefore.toFixed(4)}；梯度前的損失占比：資料 ${(result.totalBefore === 0 ? 0 : 100 * result.dataLossBefore / result.totalBefore).toFixed(1)}%、懲罰 ${(result.totalBefore === 0 ? 0 : 100 * result.penaltyBefore / result.totalBefore).toFixed(1)}%。資料梯度 2(w−1)=${result.dataGradient.toFixed(4)}，懲罰梯度 2λw=${result.penaltyGradient.toFixed(4)}，總梯度=${result.totalGradient.toFixed(4)}；梯度貢獻率：資料 ${result.totalGradient === 0 ? '未定義（總梯度為零）' : `${(100 * result.dataGradient / result.totalGradient).toFixed(1)}%`}、懲罰 ${result.totalGradient === 0 ? '未定義（總梯度為零）' : `${(100 * result.penaltyGradient / result.totalGradient).toFixed(1)}%`}。${result.directionNote}總目標最低點 w*=1/(1+λ)=${result.optimumWeight.toFixed(4)}；${result.optimumNote}最低點的損失分解：資料 ${(result.optimumDataLoss).toFixed(4)}、懲罰 ${(result.optimumPenalty).toFixed(4)}、合計 ${(result.optimumTotalLoss).toFixed(4)}。微小梯度比較：${result.cancellationExample.description}（資料 ${result.cancellationExample.dataGradient.toExponential(1)}、懲罰 ${result.cancellationExample.penaltyGradient.toExponential(1)}）。更新後 w=${result.nextWeight.toFixed(4)}；距最低點 ${result.distanceToOptimumBefore.toFixed(4)}→${result.distanceToOptimumAfter.toFixed(4)}（有號倍率 ${result.errorMultiplier.toFixed(4)}）；資料損失變化 ΔLdata=${result.dataLossChange >= 0 ? '+' : ''}${result.dataLossChange.toFixed(4)}，懲罰變化 ΔLpenalty=${result.penaltyChange >= 0 ? '+' : ''}${result.penaltyChange.toFixed(4)}，合計 ΔL=${(result.totalAfter - result.totalBefore >= 0 ? '+' : '')}${(result.totalAfter - result.totalBefore).toFixed(4)}；資料損失 ${result.dataLossBefore.toFixed(4)}→${result.dataLossAfter.toFixed(4)}，總損失 ${result.totalBefore.toFixed(4)}→${result.totalAfter.toFixed(4)}。${result.lossDirectionNote}${result.stabilityNote}臨界學習率 η*=1/(1+λ)=${result.criticalRate.toFixed(4)}。臨界值掃描：${result.stabilitySweep.map((item) => `η=${item.rate.toFixed(4)} → 倍率 ${item.multiplier.toFixed(4)}（${item.behavior}）`).join('；')}。`
    : '請輸入有限權重、學習率（0–10）與懲罰強度 λ（0–10）。';
  renderL2CancellationSweep();
  const tradeoffOutput = byId('l2LossTradeoffExercise');
  if (tradeoffOutput) {
    const tradeoff = calculateL2Regularization(0.5, 0.1, 0.1);
    tradeoffOutput.textContent = tradeoff
      ? `固定合成例 w=0.5、η=0.1、λ=0.1：ΔLdata=${tradeoff.dataLossChange.toFixed(4)}，ΔLpenalty=${tradeoff.penaltyChange.toFixed(5)}。${tradeoff.lossDirectionNote}比較兩項變化量的絕對值，可確認哪一項主導總損失。`
      : '目前無法計算練習例。';
  }
}

function renderL2CancellationSweep() {
  const output = byId('l2CancellationSweepResult');
  if (!output) return;
  const cases = [['資料主導', 0.5], ['精確抵銷', 1], ['近乎抵銷', 1 + 5e-13], ['懲罰主導', 1.5]].map(([label, ratio]) => {
    const result = calculateL2CancellationExample(ratio);
    return `${label}（懲罰/資料梯度比 ${ratio.toFixed(1)}）：總梯度 ${(result.dataGradient + result.penaltyGradient).toExponential(1)}，${result.description}`;
  });
  output.textContent = `掃描微小梯度的抵銷比例。固定資料梯度 2×10⁻¹³，調整反向懲罰梯度比例：${cases.join('；')}。梯度下降的權重位移方向與總梯度相反；精確抵銷時本步位移為零，近乎抵銷時仍有微小位移。`;
}

function renderGradientDescentTrace() {
  const output = byId('gradientDescentTraceResult');
  if (!output) return;
  const start = byId('traceStartWeight').value, rate = byId('traceLearningRate').value, steps = byId('traceStepCount').value, curvature = byId('traceCurvature').value;
  const rows = calculateGradientDescentTrace(start, rate, steps, curvature);
  output.textContent = rows
    ? (() => {
      const selectedDynamics = gradientDescentDynamics(rate, curvature);
      const currentRate = `目前設定 ηc=${(Number(rate) * Number(curvature)).toFixed(2)}，有號誤差倍率=${selectedDynamics.multiplier.toFixed(2)}（${selectedDynamics.dynamics}）。`;
      return `${currentRate} 合成損失 L=${Number(curvature)}(w−1)²：${rows.map((row, index) => {
      const delta = index === 0 ? null : row.loss - rows[index - 1].loss;
      const change = delta == null ? '起點' : delta < -1e-12 ? '下降' : delta > 1e-12 ? '上升' : '不變';
      const error = row.weight - 1;
      const distance = Math.abs(error);
      const previousError = index === 0 ? null : rows[index - 1].weight - 1;
      const ratio = previousError == null || previousError === 0 ? null : error / previousError;
      const movement = index === 0 ? null : row.weight - rows[index - 1].weight;
      const movementText = movement == null ? '' : `，權重位移 Δw=${movement >= 0 ? '+' : ''}${movement.toFixed(4)}（${movement < 0 ? '下降' : movement > 0 ? '上升' : '不變'}）`;
      return `步驟 ${row.step}：w=${row.weight.toFixed(4)}，距最低點 |w−1|=${distance.toFixed(4)}${ratio == null ? '' : `，有號誤差倍率=${ratio.toFixed(4)}`}，梯度=${row.gradient.toFixed(4)}${movementText}，L=${row.loss.toFixed(4)}${delta == null ? '' : `，ΔL=${delta >= 0 ? '+' : ''}${delta.toFixed(4)}（${change}）`}`;
      }).join('；')}。`;
    })()
    : '請輸入有限起始權重、曲率 0.1 到 5、學習率 0 到 1，以及 1 到 10 的整數步數；若更新後超出數值範圍，請縮小起始權重或學習率。';
  const comparison = byId('gradientDescentRateComparison');
  if (!comparison) return;
  if (!rows) { comparison.textContent = '完成有效輸入後，這裡會以相同曲率、起點與步數比較三種學習率。'; return; }
  comparison.textContent = `固定 c=${Number(curvature)}、w₀=${Number(start)}、${Number(steps)} 步的學習率比較：${[0.25, 0.5, 1].map((eta) => {
    const trace = calculateGradientDescentTrace(start, eta, steps, curvature);
    const changes = trace.slice(1).map((row, index) => row.loss - trace[index].loss);
    const direction = changes.map((change) => change < -1e-12 ? '下降' : change > 1e-12 ? '上升' : '不變');
    const { multiplier, dynamics } = gradientDescentDynamics(eta, curvature);
    const comparisonDynamics = dynamics === '交替越過最低點並收斂' ? '收斂（交替越過最低點）'
      : dynamics === '不越過最低點而收斂' ? '收斂'
        : dynamics === '交替發散' ? '發散（交替遠離最低點）' : dynamics;
    return `η=${eta}（誤差倍率 ${multiplier.toFixed(2)}；${comparisonDynamics}）→ 損失 ${trace.map((row) => row.loss.toFixed(4)).join('→')}；每步${direction.join('→')}`;
  }).join('；')}。此二次損失的誤差每步乘上 (1−2ηc)：0<ηc<1 時收斂，ηc=1 時一步到達最低點，ηc=0 或 ηc≥1 時不會漸近收斂；ηc>1 會交替發散。`;
}
function renderGradientClippingExercise() {
  const output = byId('gradientClippingResult');
  if (!output) return;
  const result = calculateGradientClipping(...['clippingWeight','clippingGradient','clippingLimit','clippingRate'].map(id => byId(id).value));
  output.textContent = result
    ? `原始梯度 ${byId('clippingGradient').value} 若不裁剪，更新步幅為 ${result.unclippedStep.toFixed(4)}、權重更新為 ${result.unclippedUpdated.toFixed(4)}；經上限 ±${byId('clippingLimit').value} 裁剪為 ${result.clipped.toFixed(4)} 後，保留原梯度大小的 ${(result.retainedFraction * 100).toFixed(1)}%，更新步幅為 ${result.clippedStep.toFixed(4)}、權重更新為 ${result.updated.toFixed(4)}。`
    : '請輸入四個有限數值；梯度上限與學習率不可為負。';
  const sweep = byId('clippingSweepResult');
  if (!sweep) return;
  if (!result) { sweep.textContent = '完成有效輸入後，這裡會並列不同上限下的更新。'; return; }
  const [weight, gradient, , rate] = ['clippingWeight','clippingGradient','clippingLimit','clippingRate'].map(id => Number(byId(id).value));
  sweep.textContent = `固定 w=${weight}、g=${gradient}、η=${rate} 的上限比較：${[0, 0.5, 1, 4].map(limit => {
    const example = calculateGradientClipping(weight, gradient, limit, rate);
    return `上限 ${limit} → 裁剪梯度 ${example.clipped.toFixed(2)}、新權重 ${example.updated.toFixed(2)}`;
  }).join('；')}。`;
}
function calculateVectorGradientClipping(g1, g2, limit) {
  const raw = [g1, g2, limit];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [a, b, max] = raw.map(Number);
  if (![a, b, max].every(Number.isFinite) || max < 0) return null;
  const norm = Math.hypot(a, b);
  if (!Number.isFinite(norm)) return null;
  const scale = norm === 0 || norm <= max ? 1 : max / norm;
  const clippedOne = a * scale, clippedTwo = b * scale;
  const clippedNorm = Math.hypot(clippedOne, clippedTwo);
  const componentClippedOne = Math.max(-max, Math.min(max, a));
  const componentClippedTwo = Math.max(-max, Math.min(max, b));
  const componentClippedNorm = Math.hypot(componentClippedOne, componentClippedTwo);
  return [clippedNorm, componentClippedNorm].every(Number.isFinite)
    ? { norm, scale, clippedOne, clippedTwo, clippedNorm, componentClippedOne, componentClippedTwo, componentClippedNorm }
    : null;
}
function calculateVectorGradientClipping3(g1, g2, g3, limit) {
  const raw = [g1, g2, g3, limit];
  if (raw.some(value => value == null || String(value).trim() === '')) return null;
  const [a, b, c, max] = raw.map(Number);
  if (![a, b, c, max].every(Number.isFinite) || max < 0) return null;
  const norm = Math.hypot(a, b, c);
  if (!Number.isFinite(norm)) return null;
  const scale = norm === 0 || norm <= max ? 1 : max / norm;
  const clipped = [a * scale, b * scale, c * scale];
  const clippedNorm = Math.hypot(...clipped);
  return Number.isFinite(clippedNorm) ? { norm, scale, clipped, clippedNorm } : null;
}
function calculateVectorGradientClippingN(components, limit) {
  if (!Array.isArray(components) || components.length < 1 || components.length > 64 || components.some(value => value == null || String(value).trim() === '') || limit == null || String(limit).trim() === '') return null;
  const values = components.map(Number), max = Number(limit);
  if (!values.every(Number.isFinite) || !Number.isFinite(max) || max < 0) return null;
  const norm = Math.hypot(...values);
  if (!Number.isFinite(norm)) return null;
  const scale = norm === 0 || norm <= max ? 1 : max / norm;
  const clipped = values.map(value => value * scale);
  const clippedNorm = Math.hypot(...clipped);
  const componentClipped = values.map(value => Math.max(-max, Math.min(max, value)));
  const componentClippedNorm = Math.hypot(...componentClipped);
  return [clippedNorm, componentClippedNorm].every(Number.isFinite)
    ? { norm, scale, clipped, clippedNorm, componentClipped, componentClippedNorm }
    : null;
}
function renderVectorGradientClipping4() {
  const output = byId('vectorGradientFourResult');
  if (!output) return;
  const components = ['vectorGradientFourOne','vectorGradientFourTwo','vectorGradientFourThree','vectorGradientFourFour'].map(id => byId(id).value);
  const result = calculateVectorGradientClippingN(components, byId('vectorGradientFourLimit').value);
  const cosine = (left, right) => {
    const leftNorm = Math.hypot(...left), rightNorm = Math.hypot(...right);
    return leftNorm === 0 || rightNorm === 0 ? null
      : Math.max(-1, Math.min(1, left.reduce((sum, value, index) => sum + value * right[index], 0) / (leftNorm * rightNorm)));
  };
  const angleDegrees = value => value === null ? null : Math.acos(value) * 180 / Math.PI;
  output.textContent = result
    ? `原始 L2 範數 ${result.norm.toFixed(4)}；共同縮放比例 ${result.scale.toFixed(4)}；範數裁剪後向量 (${result.clipped.map(value => value.toFixed(4)).join(', ')})，新範數 ${result.clippedNorm.toFixed(4)}，與原梯度方向餘弦 ${cosine(components.map(Number), result.clipped)?.toFixed(4) ?? '未定義'}、偏轉角 ${angleDegrees(cosine(components.map(Number), result.clipped))?.toFixed(2) ?? '未定義'}°。逐分量截斷後為 (${result.componentClipped.map(value => value.toFixed(4)).join(', ')})，範數 ${result.componentClippedNorm.toFixed(4)}，與原梯度方向餘弦 ${cosine(components.map(Number), result.componentClipped)?.toFixed(4) ?? '未定義'}、偏轉角 ${angleDegrees(cosine(components.map(Number), result.componentClipped))?.toFixed(2) ?? '未定義'}°。餘弦為 1、偏轉角為 0° 表示方向相同；偏轉角越大，方向改變越多。${result.norm === 0 ? '梯度為零時沒有更新方向；裁剪不會產生新的梯度。' : ''}${Number(byId('vectorGradientFourLimit').value) === 0 && result.norm > 0 ? '上限為 0 時，範數裁剪會把梯度縮放為零，這一步不會更新權重。' : ''}`
    : '請輸入四個有限梯度分量與非負的範數上限。';
}
function renderVectorGradientClipping() {
  const output = byId('vectorGradientResult');
  if (!output) return;
  const result = calculateVectorGradientClipping(...['vectorGradientOne','vectorGradientTwo','vectorGradientLimit'].map(id => byId(id).value));
  output.textContent = result
    ? `原始 L2 範數 ${result.norm.toFixed(4)}；共同縮放比例 ${result.scale.toFixed(4)}；範數裁剪後向量 (${result.clippedOne.toFixed(4)}, ${result.clippedTwo.toFixed(4)})，新範數 ${result.clippedNorm.toFixed(4)}。逐分量截斷則為 (${result.componentClippedOne.toFixed(4)}, ${result.componentClippedTwo.toFixed(4)})，範數 ${result.componentClippedNorm.toFixed(4)}；這種方法可能改變梯度方向。`
    : '請輸入兩個有限梯度分量與非負的範數上限。';
}
function renderVectorGradientClipping3() {
  const output = byId('vectorGradientThreeResult');
  if (!output) return;
  const result = calculateVectorGradientClipping3(...['vectorGradientThreeOne','vectorGradientThreeTwo','vectorGradientThreeThree','vectorGradientThreeLimit'].map(id => byId(id).value));
  output.textContent = result
    ? `原始 L2 範數 ${result.norm.toFixed(4)}；共同縮放比例 ${result.scale.toFixed(4)}；裁剪後向量 (${result.clipped.map(value => value.toFixed(4)).join(', ')})，新範數 ${result.clippedNorm.toFixed(4)}。`
    : '請輸入三個有限梯度分量與非負的範數上限。';
}
function calculateReturnConversion(price, returnPercent, type) {
  const base = Number(price), rate = Number(returnPercent) / 100;
  if (!Number.isFinite(base) || base <= 0 || !Number.isFinite(rate) || (type === 'simple' && rate <= -1)) return null;
  const converted = base * (type === 'log' ? Math.exp(rate) : 1 + rate);
  return Number.isFinite(converted) ? converted : null;
}
function renderReturnConversion() {
  const result = byId('conversionResult');
  if (!result) return;
  const price = byId('conversionPrice').value, rate = byId('conversionReturn').value, type = byId('conversionType').value;
  const value = calculateReturnConversion(price, rate, type);
  if (value === null) { result.textContent = '請輸入大於 0 的點位，以及有效的報酬；簡單報酬不可低於 −100%。'; return; }
  const alternate = calculateReturnConversion(price, rate, type === 'log' ? 'simple' : 'log');
  const label = type === 'log' ? '對數報酬換算' : '簡單報酬換算';
  const otherLabel = type === 'log' ? '若同數值視為簡單報酬' : '若同數值視為對數報酬';
  const format = (number) => number.toLocaleString('zh-TW', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const alternateText = alternate === null
    ? `${otherLabel}：此報酬低於 −100%，簡單報酬定義無效。`
    : `${otherLabel}：${format(alternate)} 點。`;
  result.textContent = `${label}：${format(value)} 點\n${alternateText}`;
}
function renderQuiz() {
  const question = QUIZ[quizIndex]; quizAnswered = false;
  byId('quizProgress').textContent = `第 ${quizIndex + 1} / ${QUIZ.length} 題`;
  byId('quizScore').textContent = `答對 ${quizScore} 題`;
  byId('quizQuestion').textContent = question.q;
  byId('quizChoices').innerHTML = question.choices.map((choice, index) => `<label class="quiz-choice"><input type="radio" name="learning-answer" value="${index}"><span>${choice}</span></label>`).join('');
  byId('quizFeedback').hidden = true; byId('quizFeedback').classList.remove('incorrect');
  byId('quizNext').disabled = true; byId('quizNext').textContent = '確認答案';
  byId('quizChoices').querySelectorAll('input').forEach((input) => input.addEventListener('change', () => { byId('quizNext').disabled = false; }));
}
function finishQuiz() {
  const percent = Math.round(quizScore / QUIZ.length * 100);
  byId('quizProgress').textContent = '自測完成'; byId('quizScore').textContent = `答對 ${quizScore} / ${QUIZ.length}`;
  byId('quizQuestion').textContent = percent >= 80 ? '概念掌握得不錯！' : '再練習一次，留意時間順序與測試集。';
  byId('quizChoices').innerHTML = `<p class="quiz-feedback">本次答對 ${quizScore} 題（${percent}%）。${percent >= 80 ? '可以到實驗任務試著驗證自己的理解。' : '可回到逐步導學複習，再重新挑戰。'}</p>`;
  byId('quizFeedback').hidden = true; byId('quizNext').disabled = false; byId('quizNext').textContent = '重新測驗'; quizFinished = true;
}
function chooseLearningTab(tab) {
  activeLearningTabId = tab.id;
  document.querySelectorAll('.learning-tab').forEach((button) => {
    const selected = button === tab;
    button.setAttribute('aria-selected', String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  document.querySelectorAll('.learning-view').forEach((view) => { view.hidden = view.id !== tab.getAttribute('aria-controls'); });
  if (tab.id === 'tabMath' && !traceLoaded) { loadTrace(); traceLoaded = true; }
  saveLearningProgress();
}
function initLearningCenter() {
  renderLesson(); renderQuiz();
  const savedTab = byId(activeLearningTabId);
  if (savedTab) chooseLearningTab(savedTab);
  ['conversionPrice','conversionReturn','conversionType'].forEach((id) => byId(id).addEventListener('input', renderReturnConversion));
  byId('conversionType').addEventListener('change', renderReturnConversion);
  ['gradientWeight','gradientValue','gradientRate'].forEach((id) => byId(id).addEventListener('input', renderGradientExercise));
  ['reluInput','reluTarget'].forEach((id) => byId(id).addEventListener('input', renderReluExercise));
  ['magnitudePredicted','magnitudeActual'].forEach((id) => byId(id).addEventListener('input', renderMagnitudeErrorExercise));
  ['forwardInput','forwardWeight','forwardBias'].forEach((id) => byId(id).addEventListener('input', renderForwardPassExercise));
  ['multiInputX1','multiInputW1','multiInputX2','multiInputW2','multiInputBias','multiInputTarget','updateTarget','updateRate'].forEach((id) => byId(id).addEventListener('input', renderGradientUpdateExercise));
  ['multiInputX1','multiInputW1','multiInputX2','multiInputW2','multiInputBias','updateTarget','gradientCheckEpsilon'].forEach((id) => byId(id).addEventListener('input', renderFiniteDifferenceGradientCheck));
  ['batchWeight','batchGradientOne','batchGradientTwo','batchGradientThree','batchGradientFour','batchRate'].forEach((id) => byId(id).addEventListener('input', renderBatchGradientExercise));
  ['momentumBeta','momentumPrevious','momentumGradient','momentumNextGradient','momentumThirdGradient','momentumWeight','momentumRate'].forEach((id) => byId(id).addEventListener('input', renderMomentumExercise));
  ['momentumVectorDimension','momentumVectorV1','momentumVectorV2','momentumVectorV3','momentumVectorG1','momentumVectorG2','momentumVectorG3'].forEach((id) => byId(id).addEventListener(id === 'momentumVectorDimension' ? 'change' : 'input', renderMomentumDirection));
  ['activationInput','activationTarget'].forEach((id) => byId(id).addEventListener('input', renderActivationExercise));
  ['clippingWeight','clippingGradient','clippingLimit','clippingRate'].forEach((id) => byId(id).addEventListener('input', renderGradientClippingExercise));
  ['vectorGradientOne','vectorGradientTwo','vectorGradientLimit'].forEach((id) => byId(id).addEventListener('input', renderVectorGradientClipping));
  ['vectorGradientThreeOne','vectorGradientThreeTwo','vectorGradientThreeThree','vectorGradientThreeLimit'].forEach((id) => byId(id).addEventListener('input', renderVectorGradientClipping3));
  ['vectorGradientFourOne','vectorGradientFourTwo','vectorGradientFourThree','vectorGradientFourFour','vectorGradientFourLimit'].forEach((id) => byId(id).addEventListener('input', renderVectorGradientClipping4));
  ['traceCurvature','traceStartWeight','traceLearningRate','traceStepCount'].forEach((id) => byId(id).addEventListener('input', renderGradientDescentTrace));
  ['adamGradient','adamRate','adamBeta1','adamBeta2'].forEach((id) => byId(id).addEventListener('input', renderAdamStepExercise));
  ['adamGradient1','adamGradient2','adamRate2','adamBeta12','adamBeta22','adamEpsilon2'].forEach((id) => byId(id).addEventListener('input', renderAdamTwoStepExercise));
  ['l2Weight','l2Rate','l2Lambda'].forEach((id) => byId(id).addEventListener('input', renderL2RegularizationExercise));
  ['weightDecayGradient','weightDecayWeight','weightDecayRate','weightDecayStrength'].forEach((id) => byId(id).addEventListener('input', renderWeightDecayComparison));
  renderL2CancellationSweep();
  ['intervalCenter','intervalSpread'].forEach((id) => byId(id).addEventListener('input', renderPredictionIntervalExample));
  ['magnitudePrice','magnitudeReturn'].forEach((id) => byId(id).addEventListener('input', renderMagnitudeExample));
  byId('magnitudeType').addEventListener('change', renderMagnitudeExample);
  const learningTabs = [...document.querySelectorAll('.learning-tab')];
  learningTabs.forEach((tab, index) => {
    tab.tabIndex = tab.getAttribute('aria-selected') === 'true' ? 0 : -1;
    tab.addEventListener('click', () => chooseLearningTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      const nextIndex = (index + direction + learningTabs.length) % learningTabs.length;
      const nextTab = learningTabs[nextIndex];
      chooseLearningTab(nextTab);
      nextTab.focus();
    });
  });
  byId('lessonBack').addEventListener('click', () => { lessonIndex = Math.max(0, lessonIndex - 1); renderLesson(); });
  byId('lessonNext').addEventListener('click', () => { lessonIndex = lessonIndex === LESSONS.length - 1 ? 0 : lessonIndex + 1; renderLesson(); });
  byId('checkCrossAsset').addEventListener('click', () => {
    const answer = document.querySelector('input[name="crossAssetAnswer"]:checked')?.value;
    const feedback = byId('crossAssetFeedback');
    feedback.hidden = false;
    if (!answer) { feedback.textContent = '請先選一個答案，再檢查。'; feedback.classList.add('incorrect'); return; }
    const correct = answer === 'insufficient';
    feedback.textContent = correct
      ? '答對了。方向比例和平均預測幅度只描述輸出；比較模型還要看各標的 OOF 誤差、基準、驗證期間與校準。'
      : '再想一步：預測方向比例和平均幅度沒有比較預測與實際誤差，也沒有和基準比較。';
    feedback.classList.toggle('incorrect', !correct);
  });
  ['tensorInputCount','tensorNeuronCount'].forEach((id) => byId(id).addEventListener('input', renderTensorShapeExercise));
  renderTensorShapeExercise();
  byId('checkTensorShape').addEventListener('click', () => {
    const answer = document.querySelector('input[name="tensorShapeAnswer"]:checked')?.value;
    const feedback = byId('tensorShapeFeedback');
    feedback.hidden = false;
    const result = tensorShapeFeedbackForAnswer(answer);
    feedback.textContent = result.text;
    feedback.classList.toggle('incorrect', !result.correct);
  });
  byId('checkWeightedBias').addEventListener('click', () => {
    const answer = document.querySelector('input[name="weightedBiasAnswer"]:checked')?.value;
    const feedback = byId('weightedBiasFeedback');
    feedback.hidden = false;
    const correct = answer === 'weighted';
    feedback.textContent = correct
      ? '答對了。依樣本數計算：(3 × −0.5 + 1 × 1.0) ÷ 4 = −0.125 個百分點；負號表示整體略偏高估。'
      : answer
        ? '再算一次：甲組有 3 筆、乙組只有 1 筆，不能把兩組偏差直接平均。'
        : '請先選一個答案，再檢查。';
    feedback.classList.toggle('incorrect', !correct);
  });
  byId('checkPartition').addEventListener('click', () => {
    const answer = document.querySelector('input[name="partitionAnswer"]:checked')?.value;
    const feedback = byId('partitionFeedback');
    feedback.hidden = false;
    const correct = answer === 'boundary';
    feedback.textContent = correct
      ? '答對了。切分日期只描述資料邊界；它本身不包含預測、誤差或模型成績。'
      : answer
        ? '再想一步：邊界只告訴你資料如何分段，沒有模型輸出與實際值的比較。'
        : '請先選一個答案，再檢查。';
    feedback.classList.toggle('incorrect', !correct);
  });
  byId('quizNext').addEventListener('click', () => {
    if (quizFinished) { quizIndex = 0; quizScore = 0; quizFinished = false; renderQuiz(); return; }
    if (quizAnswered) { if (quizIndex === QUIZ.length - 1) finishQuiz(); else { quizIndex += 1; renderQuiz(); } return; }
    const selected = byId('quizChoices').querySelector('input:checked'); if (!selected) return;
    quizAnswered = true; const question = QUIZ[quizIndex], correct = Number(selected.value) === question.answer;
    if (correct) quizScore += 1;
    const feedback = byId('quizFeedback'); feedback.hidden = false; feedback.classList.toggle('incorrect', !correct);
    feedback.textContent = `${correct ? '答對了。' : '再想想。'} ${question.why}`;
    byId('quizChoices').querySelectorAll('input').forEach((input) => { input.disabled = true; });
    byId('quizScore').textContent = `答對 ${quizScore} 題`;
    byId('quizNext').textContent = quizIndex === QUIZ.length - 1 ? '查看結果' : '下一題';
  });
  document.querySelectorAll('[data-focus]').forEach((button) => button.addEventListener('click', (event) => {
    event.stopPropagation();
    const target = document.querySelector(button.dataset.focus); if (!target) return;
    const advanced = target.closest('#advancedMenu'); if (advanced) advanced.open = true;
    target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.focus({ preventScroll: true });
  }));
  const noteKey = 'sequence-lab-learning-notes-v1';
  try { byId('experimentNote').value = localStorage.getItem(noteKey) || ''; } catch (_) {}
  byId('saveReflection').addEventListener('click', () => {
    try { localStorage.setItem(noteKey, byId('experimentNote').value); byId('reflectionStatus').textContent = '已儲存在此瀏覽器'; }
    catch (_) { byId('reflectionStatus').textContent = '瀏覽器無法儲存，請先複製你的筆記。'; }
  });
}

async function loadTrace() {
  byId('traceContent').innerHTML = '<div class="trace-loading">正在計算前向傳播與梯度…</div>';
  try {
    const t = await api('/api/learning/trace'), matrix = (v) => JSON.stringify(v, null, 2);
    const steps = [
      ['01　建立一筆訓練資料', `輸入張量 x = ${matrix(t.input)}\n實際目標 y = ${t.target}`],
      ['02　前向傳播', `z⁽¹⁾ = W⁽¹⁾x + b⁽¹⁾\n${matrix(t.hiddenPreActivation)}\na⁽¹⁾ = tanh(z⁽¹⁾)\n${matrix(t.hiddenActivation)}\nŷ = ${t.prediction.toFixed(8)}\nL = (ŷ − y)² = ${t.loss.toExponential(6)}\n本例只有一筆資料，與 PyTorch MSELoss 的 batch mean 相同。`],
      ['03　反向傳播', `δ² = 2(ŷ − y) = ${t.outputDelta.toFixed(8)}\nδ¹ = W²ᵀδ² ⊙ (1 − a²)\n${matrix(t.hiddenDelta)}\n∂L/∂W² = ${matrix(t.gradients.dW2)}\n∂L/∂W¹ = ${matrix(t.gradients.dW1)}\n本例用 MSE：L=(ŷ−y)²，所以輸出梯度有係數 2。若改用 L=½(ŷ−y)²，梯度會是 (ŷ−y)；兩種慣例的梯度相差 2 倍，需配合損失定義閱讀。`],
      ['04　更新權重', `W ← W − η∇W\nη = ${t.learningRate}\nW¹ 新值 = ${matrix(t.updatedWeights.W1)}\nb¹ 新值 = ${matrix(t.updatedWeights.b1)}\nW² 新值 = ${matrix(t.updatedWeights.W2)}\nb² 新值 = ${t.updatedWeights.b2.toFixed(8)}`],
    ];
    byId('traceContent').innerHTML = `${steps.map(([title,body])=>`<article class="trace-step"><h3>${title}</h3><pre>${body.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}</pre></article>`).join('')}<div class="trace-check">NumPy 手算與 PyTorch 自動微分最大梯度差 <strong>${t.gradientMaxAbsError.toExponential(2)}</strong></div>`;
  } catch (error) { byId('traceContent').textContent = `計算失敗：${error.message}`; }
}
async function refreshData() {
  if (state.activeJobId) return toast('模型工作執行中，請先等待或取消。');
  const button = byId('refreshData'); button.disabled = true;
  try {
    const before = state.status?.sha256;
    const result = await api('/api/data/refresh', { method:'POST', body:'{}' });
    const [status, series] = await Promise.all([api('/api/data/status'), api('/api/data/series')]);
    const fullSeries = await api(`/api/data/series?full=true&end=${encodeURIComponent(status.trainValidationEnd)}`);
    state.series = series.points; state.fullSeries = fullSeries.points; renderStatus(status);
    if (before && before !== status.sha256) { state.validation = null; state.validationConfig = null; resetResultPanels(); toast(`資料新增 ${result.updatedRows} 筆；請重新訓練模型。`); }
    else toast(`資料已同步；目前共 ${formatInt(result.rows)} 筆。`);
  } catch (error) { err(error.message); }
  finally { button.disabled = false; }
}
async function changeSymbol(symbol) {
  if (state.activeJobId) return toast('訓練中無法切換標的。');
  try {
    const [status, series] = await Promise.all([api(`/api/data/status?symbol=${encodeURIComponent(symbol)}`), api(`/api/data/series?symbol=${encodeURIComponent(symbol)}`)]);
    const fullSeries = await api(`/api/data/series?symbol=${encodeURIComponent(symbol)}&full=true&end=${encodeURIComponent(status.trainValidationEnd)}`);
    state.validation = null; state.validationConfig = null; state.series = series.points; state.fullSeries = fullSeries.points; renderStatus(status); resetResultPanels();
    const latest = await api(`/api/validation/latest?symbol=${encodeURIComponent(symbol)}`);
    if (latest) { state.validation = latest.result; state.validationConfig = latest.config; renderValidation(latest.result); invalidateIfEdited(); }
    await renderSavedCrossAssetComparison(symbol);
    saveDraftConfig(); renderStocks({stocks:state.stocks,universeNote:state.stockUniverseNote});
  } catch (error) { err(error.message); }
}
async function refreshStocks() {
  if (state.activeJobId) return toast('訓練中無法更新資料。');
  const button = byId('refreshStocks'); button.disabled=true; button.textContent='正在從 TWSE 更新…';
  try {
    const result = await api('/api/stocks/refresh',{method:'POST',body:'{}'});
    renderStocks(await api('/api/stocks'));
    toast(result.errors?.length?`同步完成 ${result.count} 檔，${result.errors.length} 檔更新失敗：${result.errors[0].message}`:`完成 ${result.count} 檔個股資料同步；選取標的後即可訓練。`);
  } catch(error) { err(error.message); }
  finally { button.disabled=false; button.textContent='更新個股資料'; }
}
function resetResultPanels() {
  byId('lossEmpty').hidden = false; byId('comparisonEmpty').hidden = false;
  ['metricMae','metricRmse','metricR2','metricSpearman','metricDirection'].forEach((id)=>byId(id).textContent='—');
  if (byId('directionMix')) byId('directionMix').textContent = '完成訓練後，這裡會顯示驗證資料漲跌比例。';
  byId('lossChart').innerHTML=''; byId('comparisonChart').innerHTML=''; byId('lossLegend').innerHTML='';
  byId('results').dataset.status='empty'; byId('runFinal').disabled=true;
  byId('diagnosticsPanel').dataset.status='empty';
  byId('diagnosticsStatus').textContent='完成訓練後可查看 out-of-fold 預測診斷';
  byId('residualChart').innerHTML='<text class="diagnostics-empty" x="310" y="130">完成模型訓練後顯示</text>';
  byId('foldErrorChart').innerHTML='<text class="diagnostics-empty" x="310" y="130">完成模型訓練後顯示</text>';
  byId('residualSummary').textContent='逐筆診斷資料僅從新訓練結果開始保存。'; byId('foldErrorLegend').replaceChildren();
  byId('validationStale').hidden=true;
  byId('finalStatus').textContent=state.finalUsed?'鎖定測試已使用；分數只供最終報告。':'尚未使用 · 只在選定模型後執行一次';
}
function resetSettings() {
  byId('modelType').value='mlp'; byId('symbolSelect').value='TAIEX'; byId('buyThreshold').value='0.2'; byId('sellThreshold').value='-0.2'; byId('horizon').value='1'; byId('returnType').value='simple';
  byId('lookback').value='20'; byId('epochs').value='25'; byId('batchSize').value='64'; byId('seed').value='42';
  byId('learningRate').value='0.001'; byId('dropout').value='0.2'; byId('loss').value='mse'; byId('optimizer').value='adam';
  byId('hiddenLayers').value='3'; byId('hiddenSize1').value='64'; byId('hiddenSize2').value='32'; byId('hiddenSize3').value='16'; byId('hiddenSize4').value='16';
  setPlaygroundLayerCount(3, false);
  document.querySelectorAll('#featureChoices input').forEach((input)=>{input.checked=true;});
  document.querySelectorAll('.model-compare input').forEach((input)=>{input.checked=false;});
  state.validation=null; state.validationConfig=null; resetResultPanels(); renderArchitecture(); err(); saveDraftConfig(); toast('已重設模型與訓練設定。');
}
function updateJobFromExisting(record) {
  if (record.config) { restoreDraftConfig(record.config); saveDraftConfig(); renderArchitecture(); }
  state.submitting=false; state.activeJobId=record.id; setBusy(true,'已接回先前的模型工作…');
  const config = record.config || buildConfig();
  pollJob(record.id,JSON.stringify(config),record.kind==='final');
}

async function init() {
  initLearningCenter();
  initNetworkMotion();
  renderRunHistory();
  const navLinks=[...document.querySelectorAll('.nav-item')];
  const navSections=navLinks.map(link=>({link,target:document.querySelector(link.getAttribute('href'))})).filter(item=>item.target);
  let navFrame=0;
  const syncNav=()=>{
    if(navFrame)return;
    navFrame=requestAnimationFrame(()=>{
      navFrame=0;
      const current=window.scrollY<180?navSections[0]:[...navSections].reverse().find(({target})=>target.getBoundingClientRect().top<=150)||navSections[0];
      navSections.forEach(({link})=>{const active=link===current.link;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
    });
  };
  navLinks.forEach(link=>link.addEventListener('click',()=>{if(link.getAttribute('href')==='#math')byId('math').open=true;}));
  window.addEventListener('scroll',syncNav,{passive:true});
  window.addEventListener('resize',syncNav);
  let comparisonResizeTimer;
  window.addEventListener('resize',()=>{clearTimeout(comparisonResizeTimer);comparisonResizeTimer=setTimeout(()=>renderComparison(state.comparisonRows),120);},{passive:true});
  syncNav();
  document.querySelectorAll('a[href="#math"]').forEach((link)=>link.addEventListener('click',()=>{byId('math').open=true;}));
  document.querySelectorAll('#modelType,#horizon,#returnType,#lookback,#epochs,#batchSize,#seed,#learningRate,#dropout,#loss,#optimizer,#hiddenLayers,#hiddenSize1,#hiddenSize2,#hiddenSize3,#hiddenSize4,#featureChoices input,.model-compare input').forEach((node)=>node.addEventListener('input',()=>{invalidateIfEdited(); saveDraftConfig();}));
  byId('addLayer').addEventListener('click',()=>setPlaygroundLayerCount(Number(byId('playgroundLayerCount').textContent)+1));
  byId('removeLayer').addEventListener('click',()=>setPlaygroundLayerCount(Number(byId('playgroundLayerCount').textContent)-1));
  byId('modelType').addEventListener('change',()=>{renderArchitecture();saveDraftConfig();});
  document.querySelectorAll('[data-open-advanced]').forEach(button => button.addEventListener('click', () => {
    const menu = byId('advancedMenu');
    if (menu) { menu.open = true; menu.scrollIntoView({ behavior:'smooth', block:'center' }); }
  }));
  document.querySelectorAll('#modelType,#horizon,#returnType,#loss,#optimizer,#featureChoices input,.model-compare input').forEach((node)=>node.addEventListener('change',()=>{invalidateIfEdited();saveDraftConfig();}));
  byId('runValidation').addEventListener('click',()=>startJob(false)); byId('topTrain').addEventListener('click',()=>startJob(false));
  byId('runFinal').addEventListener('click',openFinalConfirmation);
  byId('cancelFinalConfirm').addEventListener('click',()=>byId('finalConfirmDialog').close());
  byId('confirmFinalRun').addEventListener('click',()=>{if(!currentConfigMatches()||state.finalUsed){byId('finalConfirmDialog').close();invalidateIfEdited();return;}byId('finalConfirmDialog').close();startJob(true);});
  byId('runHistoryRows').addEventListener('click',(event)=>{const button=event.target.closest('[data-run-index]');if(!button)return;const run=readRunHistory()[Number(button.dataset.runIndex)];if(!run?.config)return;restoreDraftConfig(run.config);saveDraftConfig();invalidateIfEdited();setTimeout(()=>{byId('advancedMenu').open=true;},0);byId('data').scrollIntoView({behavior:'smooth',block:'start'});toast('已套用這筆實驗設定；確認後可重新訓練。');});
  byId('exportRunHistory')?.addEventListener('click',exportRunHistory);
  byId('footerTrain')?.addEventListener('click',()=>startJob(false));
  byId('footerCancel')?.addEventListener('click',cancelJob);
  byId('footerReset')?.addEventListener('click',()=>byId('resetSettings').click());
  byId('cancelJob').addEventListener('click',cancelJob); byId('refreshData').addEventListener('click',refreshData); byId('resetSettings').addEventListener('click',resetSettings);
  byId('symbolSelect').addEventListener('change',event=>changeSymbol(event.target.value));
  byId('stockCards').addEventListener('click',event=>{const card=event.target.closest('[data-symbol]');if(card)changeSymbol(card.dataset.symbol);});
  byId('refreshStocks').addEventListener('click',refreshStocks);
  ['buyThreshold','sellThreshold'].forEach(id=>byId(id).addEventListener('input',()=>{invalidateIfEdited();saveDraftConfig();if(state.validation)renderSignals(state.validation);}));
  byId('settingsShortcut').addEventListener('click',()=>{const menu=byId('advancedMenu');menu.open=!menu.open;if(menu.open)byId('lookback').focus();});
  document.addEventListener('click',(event)=>{
    const menu=byId('advancedMenu');
    const advancedTrigger=event.target.closest('[data-open-advanced]');
    if(menu.open&&!menu.contains(event.target)&&!byId('settingsShortcut').contains(event.target)&&!advancedTrigger)menu.open=false;
  });
  document.addEventListener('keydown',(event)=>{if(event.key==='Escape'&&byId('advancedMenu').open){byId('advancedMenu').open=false;byId('settingsShortcut').focus();}});
  byId('loadTrace').addEventListener('click',(event)=>{event.preventDefault();event.stopPropagation();loadTrace();traceLoaded=true;}); byId('showSplit').addEventListener('change',renderChart);
  document.querySelectorAll('#advancedMenu input,#advancedMenu select').forEach((node)=>node.addEventListener('input',()=>{invalidateIfEdited();saveDraftConfig();}));
  byId('staleTrain').addEventListener('click',()=>startJob(false));
  try {
    renderStocks(await api('/api/stocks'));
    const hasDraft = restoreDraftConfig();
    renderArchitecture();
    const symbol = byId('symbolSelect').value || 'TAIEX';
    const [status,series]=await Promise.all([api(`/api/data/status?symbol=${encodeURIComponent(symbol)}`),api(`/api/data/series?symbol=${encodeURIComponent(symbol)}`)]);
    const fullSeries=await api(`/api/data/series?symbol=${encodeURIComponent(symbol)}&full=true&end=${encodeURIComponent(status.trainValidationEnd)}`);
    state.series=series.points; state.fullSeries=fullSeries.points; renderStatus(status); renderArchitecture();
    await refreshLockStatus();
    const active = await api('/api/jobs/active');
    if (active) updateJobFromExisting(active);
    else {
      const latest = await api(`/api/validation/latest?symbol=${encodeURIComponent(status.symbol||'TAIEX')}`);
      if (latest) {
        if (!hasDraft) restoreDraftConfig(latest.config);
        state.validation=latest.result; state.validationConfig=latest.config;
        renderArchitecture(); renderValidation(latest.result); invalidateIfEdited();
      }
    }
    await renderSavedCrossAssetComparison(status.symbol || 'TAIEX');
    if(status.finalTest?.status==='running'&&status.finalTest.jobId){try{const rec=await api(`/api/jobs/${status.finalTest.jobId}`);updateJobFromExisting(rec);}catch(_){}}
  } catch(error) { byId('dataNote').textContent=error.message; err(error.message); }
}
init();
