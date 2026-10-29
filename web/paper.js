const byId = (id) => document.getElementById(id);
const money = (value) => Number(value).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
let hasAvailableSymbol = false;
let neuralReady = false;
let activeAccounts = [];
let retiredAccounts = [];
let selectedAccountId = null;
let createKey = null;
let lastCreatePayload = null;
let walking = new Set();
let walkGenerations = new Map();
let walkTimers = new Map();
let autoWalkTimers = new Map();
let resizeFrame = null;
let nextAutomaticIndex = 0;
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const MAX_ROOM_SEATS = 8;
const frameScheduler = window.createPaperFrameScheduler(window);
const PAPER_DESKS = window.PAPER_OFFICE_CONFIG.desks;
const PAPER_OFFICE_ITEMS = window.createPaperOfficeItems;
const paperRouteModel = (() => {
  try { return window.createPaperRouteModel(localStorage.getItem(window.PAPER_ROUTE_MODEL_KEY)); }
  catch { return window.createPaperRouteModel(); }
})();
let paperOffice = null;
let seatByAccount = new Map();
let mascotSpriteImages = {};
let paperOfficeRosterReady = false;

function persistPaperRouteModel() {
  try { localStorage.setItem(window.PAPER_ROUTE_MODEL_KEY, JSON.stringify(paperRouteModel)); }
  catch { /* Private browsing or storage limits must not stop mascot movement. */ }
  const status = byId('routeModelStatus');
  if (status) status.textContent = `線上學習路線模型 · 已學 ${paperRouteModel.total} 趟 · 64 條候選路線`;
}

function setupPaperOffice() {
  const officeCanvas = byId('officeCanvas');
  paperOffice = new window.Office(officeCanvas, byId('officeLabels'));
  paperOffice.setLayoutDoc({ items: PAPER_OFFICE_ITEMS() });
  paperOffice.setCharacterRenderer(drawPaperMascot);
  paperOffice.setEmployees([]);
  paperOffice.start();
  const routeStatus = byId('routeModelStatus');
  if (routeStatus) routeStatus.textContent = `線上學習路線模型 · 已學 ${paperRouteModel.total} 趟 · 64 條候選路線`;
  for (const [key, path] of Object.entries({
    seated: '/assets/paper-mascot-seated-front.png',
    walkingFront: '/assets/paper-mascot-walking-front.png',
    // This sheet is a clean back-facing walk cycle. `walking-v2` includes a
    // chair in the character art, which made it look attached while walking.
    walkingBack: '/assets/paper-mascot-walking.png',
    hatViewsTeal: '/assets/paper-mascot-hats-teal.png',
    hatViewsRed: '/assets/paper-mascot-hats-red.png',
    hatViewsBlue: '/assets/paper-mascot-hats-blue.png',
    hatViewsCream: '/assets/paper-mascot-hats-cream.png',
    hatWalkCap: '/assets/paper-mascot-walk-cap.png',
    hatWalkBeret: '/assets/paper-mascot-walk-beret.png',
    hatWalkCrown: '/assets/paper-mascot-walk-crown.png',
    previewAtlas: '/assets/paper-mascot-preview-atlas-v3.png',
  })) {
    const image = new Image();
    image.src = path;
    mascotSpriteImages[key] = image;
  }
  requestAnimationFrame(syncMascotCoordinates);
}

function mascotPaletteIndex(color) {
  return ({ teal: 0, red: 1, blue: 2, cream: 3 })[color] ?? 0;
}

function mascotHatStyle(accessory) {
  return ({ dot: 'cap', leaf: 'beret', star: 'crown' })[accessory] || accessory || 'cap';
}

function setMascotPortrait(element, account) {
  const sprite = window.getPaperMascotPreviewFrame(account.mascotAccessory, account.mascotColor);
  element.style.backgroundImage = "url('/assets/paper-mascot-preview-atlas-v3.png')";
  element.style.backgroundSize = '400% 400%';
  element.style.backgroundPosition = `${sprite.column * (100 / 3)}% ${sprite.colorIndex * (100 / 3)}%`;
}

function updateCreationMascotPreview() {
  const color = document.querySelector('input[name="mascotColor"]:checked')?.value || 'teal';
  const accessory = byId('accessory')?.value || 'cap';
  const nickname = byId('nickname')?.value.trim() || '新夥伴';
  const colorNames = { teal: '湖綠', red: '珊瑚', blue: '藍莓', cream: '奶油' };
  const accessoryNames = { cap: '經典鴨舌帽', beret: '柔軟貝雷帽', crown: '小小皇冠', none: '不戴帽子' };
  const preview = byId('creationMascotPreview');
  const avatar = byId('creationMascotAvatar');
  if (!preview || !avatar) return;

  preview.classList.remove('mascot-teal', 'mascot-red', 'mascot-blue', 'mascot-cream',
    'accessory-cap', 'accessory-beret', 'accessory-crown', 'accessory-none');
  preview.classList.add(`mascot-${color}`, `accessory-${accessory}`);
  setMascotPortrait(avatar, { mascotColor: color, mascotAccessory: accessory });
  byId('creationMascotName').textContent = nickname;
  byId('creationMascotStyle').textContent = `${colorNames[color]} · ${accessoryNames[accessory]}`;
  avatar.setAttribute('aria-label', `${nickname}，${colorNames[color]}、${accessoryNames[accessory]}吉祥物預覽`);
  byId('creationPreviewAnnouncement').textContent = `${nickname}，${colorNames[color]}，${accessoryNames[accessory]}。外觀即時預覽，建立帳戶前不會儲存。`;
}

function updateMascotPreview() {
  const content = byId('inspectorContent');
  const hero = content.querySelector('.inspector-mascot');
  const portrait = hero?.querySelector('.mascot-character');
  if (!hero || !portrait) return;
  const color = content.querySelector('[data-color].selected')?.dataset.color || 'teal';
  const accessory = byId('editAccessory')?.value || 'cap';
  hero.classList.remove('mascot-teal', 'mascot-red', 'mascot-blue', 'mascot-cream',
    'accessory-cap', 'accessory-beret', 'accessory-crown', 'accessory-none');
  hero.classList.add(`mascot-${color}`, `accessory-${mascotHatStyle(accessory)}`);
  setMascotPortrait(portrait, { mascotColor: color, mascotAccessory: accessory });
  const note = hero.querySelector('.inspector-preview-note');
  const saved = color === hero.dataset.savedColor && mascotHatStyle(accessory) === hero.dataset.savedAccessory;
  if (note) note.textContent = saved ? '目前已儲存造型' : '即時預覽 · 尚未儲存';
}

function drawPaperMascot(context, employee) {
  const account = employee.paperAccount;
  if (!account) return;
  const walking = employee.path.length > 0 || employee.entering || employee.paperPatrolling;
  const colorIndex = mascotPaletteIndex(account.mascotColor);
  const frame = Math.floor(employee.walkDist / 10) % 2;
  if (!walking) {
    const preview = window.getPaperMascotPreviewFrame(account.mascotAccessory, account.mascotColor);
    const image = mascotSpriteImages.previewAtlas;
    if (image?.complete && image.naturalWidth) {
      const cellWidth = image.naturalWidth / 4;
      const cellHeight = image.naturalHeight / 4;
      context.drawImage(image, preview.column * cellWidth, preview.colorIndex * cellHeight,
        cellWidth, cellHeight, employee.x - 4, employee.y - 12, 40, 42);
      context.restore();
      return;
    }
  }
  const sprite = window.getPaperMascotSpriteFrame(account.mascotAccessory, account.mascotColor, employee.dir, walking, frame);
  context.save();
  context.imageSmoothingEnabled = false;
  if (sprite.kind === 'walk') {
    const image = mascotSpriteImages[['hatWalkCap', 'hatWalkBeret', 'hatWalkCrown'][sprite.hatIndex]];
    if (image?.complete && image.naturalWidth) {
      const cellWidth = image.naturalWidth / 6;
      const cellHeight = image.naturalHeight / 4;
      if (sprite.flipX) {
        context.translate(employee.x + 16, 0);
        context.scale(-1, 1);
        context.drawImage(image, sprite.column * cellWidth, sprite.colorIndex * cellHeight, cellWidth, cellHeight, -20, employee.y - 12, 40, 42);
      } else {
        context.drawImage(image, sprite.column * cellWidth, sprite.colorIndex * cellHeight, cellWidth, cellHeight, employee.x - 4, employee.y - 12, 40, 42);
      }
    }
  } else if (sprite.kind === 'views') {
    const image = mascotSpriteImages[['hatViewsTeal', 'hatViewsRed', 'hatViewsBlue', 'hatViewsCream'][sprite.colorIndex]];
    if (image?.complete && image.naturalWidth) {
      const cellWidth = image.naturalWidth / 3;
      const cellHeight = image.naturalHeight / 3;
      const crop = window.getPaperMascotViewCrop(sprite.row, cellHeight, image.naturalHeight);
      if (!crop) { context.restore(); return; }
      if (sprite.flipX) {
        context.translate(employee.x + 16, 0);
        context.scale(-1, 1);
        context.drawImage(image, sprite.column * cellWidth, crop.y, cellWidth, crop.height, -20, employee.y - 12, 40, 42);
      } else {
        context.drawImage(image, sprite.column * cellWidth, crop.y, cellWidth, crop.height, employee.x - 4, employee.y - 12, 40, 42);
      }
    }
  } else if (walking) {
    const image = employee.dir === 'up' ? mascotSpriteImages.walkingBack : mascotSpriteImages.walkingFront;
    const columns = 2;
    const rows = 4;
    if (image?.complete && image.naturalWidth) {
      const cellWidth = image.naturalWidth / columns;
      const cellHeight = image.naturalHeight / rows;
      context.drawImage(image, frame * cellWidth, colorIndex * cellHeight, cellWidth, cellHeight, employee.x - 4, employee.y - 12, 40, 42);
    }
  } else {
    const image = mascotSpriteImages.seated;
    if (image?.complete && image.naturalWidth) {
      const cellWidth = image.naturalWidth / 2;
      const cellHeight = image.naturalHeight / 2;
      context.drawImage(image, (colorIndex % 2) * cellWidth, Math.floor(colorIndex / 2) * cellHeight, cellWidth, cellHeight, employee.x - 4, employee.y - 12, 40, 42);
    }
  }
  context.restore();
}

function syncPaperOfficeRoster(enteringIds = null) {
  if (!paperOffice) return;
  const previousIds = new Set(paperOffice.emps.map((employee) => employee.id));
  const activeIds = new Set(activeAccounts.map((account) => account.id));
  for (const accountId of seatByAccount.keys()) if (!activeIds.has(accountId)) seatByAccount.delete(accountId);
  const usedSlots = new Set(seatByAccount.values());
  for (const account of activeAccounts) {
    if (seatByAccount.has(account.id)) continue;
    const slot = Array.from({ length: MAX_ROOM_SEATS }, (_, index) => index).find((index) => !usedSlots.has(index));
    if (slot !== undefined) { seatByAccount.set(account.id, slot); usedSlots.add(slot); }
  }
  const assignedDesks = PAPER_DESKS.map(([tx, ty], index) => {
    const owner = [...seatByAccount].find(([, slot]) => slot === index)?.[0];
    return { id: `paperdesk${index}`, type: 'desk', tx, ty, ...(owner ? { emp: owner } : {}) };
  });
  paperOffice.setLayoutDoc({ items: [...PAPER_OFFICE_ITEMS().filter((item) => item.type !== 'desk'), ...assignedDesks] });
  const employees = activeAccounts.map((account) => {
    const colors = { teal: '#36b6ae', red: '#ef716b', blue: '#4d8cf0', cream: '#ead7a7' };
    return {
      id: account.id,
      name: account.nickname || `${account.symbol} 吉祥物`,
      role: account.strategy === 'neural' ? '凍結神經網路' : account.strategy === 'agent' ? `${account.agentProvider === 'antigravity' ? 'AGY' : 'Codex'} 訂閱代理` : '時間序列策略',
      color: colors[account.mascotColor] || colors.teal,
      look: { top: colors[account.mascotColor] || colors.teal, bottom: '#283747' },
      status: 'idle',
      paperAccount: account,
    };
  });
  const arriving = enteringIds || (paperOfficeRosterReady ? new Set(employees.map((employee) => employee.id).filter((id) => !previousIds.has(id))) : null);
  paperOffice.setEmployees(employees, arriving);
  paperOfficeRosterReady = true;
  for (const employee of paperOffice.emps) {
    employee.paperManaged = true;
    window.setPaperRosterActivity(employee, walking.has(employee.id));
    employee.paperAccount = activeAccounts.find((account) => account.id === employee.id) || employee.paperAccount;
  }
  paperOffice.fit();
}

function syncMascotCoordinates() {
  if (!paperOffice) return;
  const map = byId('officeMap');
  const canvasRect = paperOffice.canvas.getBoundingClientRect();
  const mapRect = map.getBoundingClientRect();
  const employees = new Map(paperOffice.emps.map((employee) => [employee.id, employee]));
  for (const seat of byId('roomSeats').querySelectorAll('.mascot-seat[data-id]')) {
    const employee = employees.get(seat.dataset.id);
    if (!employee) continue;
    seat.style.left = `${canvasRect.left - mapRect.left + (employee.x + 16) * paperOffice.scale}px`;
    seat.style.top = `${canvasRect.top - mapRect.top + (employee.y + 13) * paperOffice.scale}px`;
    seat.classList.toggle('is-walking', walking.has(employee.id));
    seat.classList.toggle('is-facing-away', walking.has(employee.id) && employee.dir === 'up');
  }
  requestAnimationFrame(syncMascotCoordinates);
}

async function request(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function element(tag, className = '', text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function moneyMetric(label, value, tone = '') {
  const row = element('div', `inspector-metric ${tone}`);
  row.append(element('span', '', label), element('strong', '', value));
  return row;
}

function makeSeat(account, index, total, retired = false) {
  const seat = element('button', `mascot-seat mascot-${account.mascotColor || 'teal'} accessory-${mascotHatStyle(account.mascotAccessory)}${retired ? ' is-retired' : ''}`);
  seat.type = 'button';
  seat.dataset.id = account.id;
  seat.dataset.position = String(index);
  seat.dataset.search = `${account.nickname || ''} ${account.symbol} ${account.strategy}`.toLocaleLowerCase();
  seat.style.setProperty('--seat-index', String(index));
  seat.setAttribute('aria-label', `${account.nickname || `${account.symbol} 吉祥物`}，${retired ? '退場，可查看帳戶紀錄' : account.pendingAction}，開啟帳戶詳情`);

  if (retired) {
    const mascot = element('span', 'mascot-character pose-seated');
    mascot.setAttribute('aria-hidden', 'true');
    seat.append(mascot);
  }
  const label = element('span', 'seat-caption');
  label.append(element('strong', '', account.nickname || `${account.symbol} 小夥伴`), element('small', '', `${account.symbol} · ${account.lastDate}`));
  const state = element('span', `seat-state${retired ? ' retired' : account.paused ? ' paused' : ''}`, retired ? '已退場' : account.paused ? '停止中' : account.pendingAction);
  seat.append(label, state);
  return seat;
}

function renderRoom() {
  const stage = byId('officeStage');
  const room = byId('roomSeats');
  syncPaperOfficeRoster();
  const query = byId('seatSearch').value.trim().toLocaleLowerCase();
  const filtered = activeAccounts.filter((a) => !query || `${a.nickname} ${a.symbol} ${a.strategy}`.toLocaleLowerCase().includes(query));
  const visibleIds = new Set([...filtered, ...activeAccounts.filter((account) => walking.has(account.id))].map((account) => account.id));
  const existingSeats = new Map([...room.querySelectorAll('.mascot-seat[data-id]')].map((seat) => [seat.dataset.id, seat]));
  const mobile = window.matchMedia('(max-width: 900px)').matches;
  stage.style.minHeight = `${mobile ? 710 : 780}px`;
  paperOffice?.fit();
  room.querySelector('.room-empty')?.remove();
  if (!activeAccounts.length) {
    const empty = element('div', 'room-empty');
    empty.append(element('span', 'empty-window'), element('strong', '', activeAccounts.length ? '沒有符合的角色' : '房間裡還沒有吉祥物'),
      element('span', '', '八個工位已備妥；按「呼叫吉祥物」建立紙上模擬帳戶，讓它從門口走到座位。'));
    room.append(empty);
  } else {
    activeAccounts.forEach((account, index) => {
      const seat = existingSeats.get(account.id) || makeSeat(account, index, activeAccounts.length);
      seat.className = `mascot-seat mascot-${account.mascotColor || 'teal'} accessory-${mascotHatStyle(account.mascotAccessory)}${walking.has(account.id) ? ' is-walking' : ''}`;
      seat.querySelector('.seat-caption strong').textContent = account.nickname || `${account.symbol} 小夥伴`;
      seat.querySelector('.seat-caption small').textContent = `${account.symbol} · ${account.lastDate}`;
      seat.querySelector('.seat-state').textContent = account.paused ? (account.shares ? '等待最後平倉' : '停止中') : account.pendingAction;
      seat.hidden = !visibleIds.has(account.id);
      seat.dataset.position = String(index);
      if (!seat.isConnected || seat.parentElement !== room) room.append(seat);
    });
    for (const [id, seat] of existingSeats) if (!activeAccounts.some((account) => account.id === id)) seat.remove();
    room.querySelector('.room-filter-empty')?.remove();
    if (activeAccounts.length && filtered.length === 0) {
      const note = element('div', 'room-filter-empty');
      note.setAttribute('role', 'status');
      note.append(element('span', '', '搜尋沒有符合項目；為避免角色移動時消失，散步中的吉祥物仍會顯示。'));
      const clear = element('button', 'room-filter-clear', '清除搜尋');
      clear.type = 'button';
      clear.addEventListener('click', () => {
        byId('seatSearch').value = '';
        renderRoom();
        byId('seatSearch').focus();
      });
      note.append(clear);
      room.append(note);
    }
  }
  const retiredSection = byId('retiredSection');
  retiredSection.hidden = retiredAccounts.length === 0;
  byId('retiredSeats').replaceChildren(...retiredAccounts.map((account, index) => makeSeat(account, index, retiredAccounts.length, true)));
  byId('activeCount').textContent = String(activeAccounts.length).padStart(2, '0');
  byId('retiredCount').textContent = String(retiredAccounts.length).padStart(2, '0');
  byId('seatCapacity').textContent = `${String(Math.min(activeAccounts.length, MAX_ROOM_SEATS)).padStart(2, '0')}/${MAX_ROOM_SEATS}`;
  byId('callMascot').disabled = activeAccounts.length >= MAX_ROOM_SEATS;
  byId('callMascot').title = activeAccounts.length >= MAX_ROOM_SEATS ? '8 個座位都已使用' : '呼叫吉祥物並安排到空座位';
  syncMascotCoordinates();
}

async function loadAccounts() {
  try {
    const result = await request('/api/paper/accounts');
    activeAccounts = result.accounts || [];
    retiredAccounts = result.retiredAccounts || [];
    const activeIds = new Set(activeAccounts.map((account) => account.id));
    window.prunePaperWalkingState(activeIds, {
      walking, generations: walkGenerations, walkTimers, autoWalkTimers,
    });
    renderRoom();
    scheduleAutomaticPatrols();
  } catch (error) {
    byId('roomMessage').textContent = `讀取失敗：${error.message}`;
  }
}

async function loadSymbols() {
  try {
    const { stocks } = await request('/api/stocks');
    const select = byId('symbol');
    select.replaceChildren();
    for (const stock of stocks) {
      const option = document.createElement('option');
      option.value = stock.symbol;
      option.textContent = `${stock.symbol} · ${stock.name}${stock.available ? '' : '（尚無本機資料）'}`;
      option.disabled = !stock.available;
      select.append(option);
    }
    hasAvailableSymbol = stocks.some((stock) => stock.available);
    byId('startAccount').disabled = !hasAvailableSymbol || (byId('strategy').value === 'neural' && !neuralReady);
    byId('startAccount').textContent = hasAvailableSymbol ? '建立帳戶並安排座位' : '沒有可用個股資料';
  } catch (error) {
    byId('formError').hidden = false;
    byId('formError').textContent = `無法讀取標的清單：${error.message}`;
  }
}

async function loadNeuralModels() {
  const panel = byId('neuralSettings');
  panel.hidden = byId('strategy').value !== 'neural';
  if (panel.hidden) return;
  const select = byId('model');
  try {
    const latest = await request(`/api/validation/latest?symbol=${encodeURIComponent(byId('symbol').value)}`);
    const lock = await request(`/api/data/lock-status?symbol=${encodeURIComponent(byId('symbol').value)}`);
    neuralReady = false;
    select.replaceChildren();
    if (!latest) {
      select.append(new Option('沒有相符的最新驗證', ''));
      select.disabled = true;
      byId('modelInfo').textContent = '請先回研究工作台，對此標的完成驗證；資料更新後需重新驗證。';
      byId('startAccount').disabled = true;
      return;
    }
    const choices = (latest.result.models || []).map((model) => model.key);
    choices.forEach((key) => select.append(new Option(key.toUpperCase(), key)));
    byId('buyThreshold').value = latest.config.buyThreshold;
    byId('sellThreshold').value = latest.config.sellThreshold;
    neuralReady = lock.status === 'spent' && !lock.datasetHashMismatch;
    byId('modelInfo').textContent = `資料版本 ${latest.datasetHash.slice(0, 12)} · 特徵 ${(latest.config.features || []).join('、')} · ${latest.config.horizon} 日目標 · 鎖定測試${neuralReady ? '已完成' : '尚未完成'}。${neuralReady ? '帳戶會保存凍結權重。' : '需先在研究工作台完成此資料版本的鎖定測試。'}`;
    select.disabled = choices.length === 0;
    byId('startAccount').disabled = !hasAvailableSymbol || !neuralReady || choices.length === 0;
  } catch (error) {
    neuralReady = false;
    select.replaceChildren(new Option('無法讀取驗證結果', ''));
    byId('modelInfo').textContent = error.message;
    byId('startAccount').disabled = true;
  }
}

function openCallDialog() {
  if (activeAccounts.length >= MAX_ROOM_SEATS) {
    byId('roomMessage').textContent = '8 個固定座位都已使用，請先讓目前角色退場再呼叫新吉祥物。';
    return;
  }
  createKey = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  lastCreatePayload = null;
  byId('accountForm').reset();
  byId('accountForm').querySelectorAll('details').forEach((details) => { details.open = false; });
  byId('formError').hidden = true;
  updateCreationMascotPreview();
  byId('callDialog').showModal();
  byId('agentSettings').hidden = byId('strategy').value !== 'agent';
  loadNeuralModels();
}

function statusFor(account) {
  if (account.retired) return '退場完成';
  if (account.paused && account.shares > 0) return '停止中 · 等待最後平倉';
  if (account.paused) return '已停止';
  return account.pendingAction;
}

function showInspector(accountId) {
  const account = [...activeAccounts, ...retiredAccounts].find((item) => item.id === accountId);
  if (!account) return;
  selectedAccountId = accountId;
  const content = byId('inspectorContent');
  content.replaceChildren();
  const head = element('div', 'drawer-top');
  const title = element('div');
  title.append(element('p', 'drawer-kicker', account.retired ? 'RESTING ROOM' : 'ACCOUNT SEAT'), element('h2', '', account.nickname || `${account.symbol} 吉祥物`));
  head.append(title);
  const close = element('button', 'icon-button', '×');
  close.type = 'button'; close.dataset.close = 'inspectorDialog'; close.setAttribute('aria-label', '關閉帳戶詳情');
  head.append(close); content.append(head);
  const hero = element('div', `inspector-mascot mascot-${account.mascotColor || 'teal'} accessory-${mascotHatStyle(account.mascotAccessory)}`);
  hero.dataset.savedColor = account.mascotColor || 'teal';
  hero.dataset.savedAccessory = mascotHatStyle(account.mascotAccessory);
  const portrait = element('span', 'mascot-character pose-seated');
  setMascotPortrait(portrait, account);
  hero.append(portrait, element('div', 'inspector-status', statusFor(account)), element('div', 'inspector-preview-note', '目前已儲存造型'));
  content.append(hero);
  const strategyLabel = account.strategy === 'neural'
    ? `${account.model?.key?.toUpperCase() || 'NN'} 凍結模型 · ${account.model?.horizon} 日預測`
    : account.strategy === 'agent'
      ? `${account.agentProvider === 'antigravity' ? 'Google Antigravity（AGY）' : 'OpenAI Codex'} 訂閱代理`
      : `${account.lookback} 日時間序列動能`;
  content.append(element('p', 'inspector-strategy', `${strategyLabel} · ${account.symbol}`));
  const metrics = element('div', 'inspector-metrics');
  metrics.append(moneyMetric('模擬淨值', `NT$ ${money(account.equity)}`),
    moneyMetric('累計損益', `${account.pnl >= 0 ? '+' : ''}NT$ ${money(account.pnl)}`, account.pnl < 0 ? 'negative' : 'positive'),
    moneyMetric('現金', `NT$ ${money(account.cash)}`), moneyMetric('持有股數', `${money(account.shares)} 股`),
    moneyMetric('最大收盤回撤', `${account.maxDrawdownPct.toFixed(2)}%`), moneyMetric('資料截至', account.lastDate));
  content.append(metrics);

  if (account.strategy === 'agent' && !account.retired) {
    const agent = element('section', 'agent-control');
    agent.append(element('h3', '', '訂閱代理控制'));
    agent.append(element('p', 'fineprint', account.agentAutoEnabled
      ? '代理已允許提交決策。請確認對應客戶端已載入本機 MCP 設定與排程。'
      : '代理目前停用；重新啟用後，對應客戶端排程可恢復提交決策。'));
    const toggleAgent = element('button', account.agentAutoEnabled ? 'stop-button full-width' : 'secondary-button full-width',
      account.agentAutoEnabled ? '停止接受新代理決策' : '啟用代理自動決策');
    toggleAgent.type = 'button'; toggleAgent.dataset.action = 'agent-automation'; toggleAgent.dataset.id = account.id;
    agent.append(toggleAgent);
    agent.append(element('p', 'fineprint', '設定指南：docs/paper-agent-setup.md。訂閱登入留在 Codex／Antigravity；不會傳送券商委託。'));
    content.append(agent);
  }

  const edit = element('section', 'mascot-edit');
  edit.append(element('h3', '', '吉祥物造型'));
  const nameInput = document.createElement('input'); nameInput.id = 'editNickname'; nameInput.maxLength = 24; nameInput.value = account.nickname || ''; nameInput.placeholder = '輸入暱稱'; nameInput.setAttribute('aria-label', '吉祥物暱稱');
  edit.append(nameInput);
  const controls = element('div', 'swatch-row compact-swatches');
  for (const [value, label] of [['teal','湖綠'],['red','珊瑚'],['blue','藍莓'],['cream','奶油']]) {
    const option = document.createElement('button'); option.type = 'button'; option.className = `swatch-button ${account.mascotColor === value ? 'selected' : ''}`;
    option.dataset.color = value; option.setAttribute('aria-label', `選擇${label}`); option.setAttribute('aria-pressed', String(account.mascotColor === value));
    option.append(element('span', `swatch ${value}`)); controls.append(option);
  }
  edit.append(controls);
  const accessory = document.createElement('select'); accessory.id = 'editAccessory'; accessory.setAttribute('aria-label', '選擇配件');
  for (const [value,label] of [['cap','經典鴨舌帽'],['beret','柔軟貝雷帽'],['crown','小小皇冠'],['none','不戴帽子']]) accessory.append(new Option(label,value));
  accessory.value = mascotHatStyle(account.mascotAccessory); edit.append(accessory);
  const save = element('button', 'secondary-button full-width', '儲存吉祥物外觀'); save.type = 'button'; save.dataset.action = 'save-mascot'; edit.append(save);
  content.append(edit);

  if (!account.firstSync && !account.retired) {
    const settings = element('section', 'account-settings-edit');
    settings.append(element('h3', '', '首次同步前可調模擬條件'));
    const field = (id, label, value, min, max, step = '1') => {
      const wrap = element('label', 'setting-field');
      wrap.append(element('span', '', label));
      const input = document.createElement('input'); input.id = id; input.type = 'number'; input.value = value; input.min = min; input.max = max; input.step = step; wrap.append(input);
      return wrap;
    };
    const grid = element('div', 'setting-grid');
    if (account.strategy === 'momentum') grid.append(field('editLookback','動能回看日數',account.lookback,1,252));
    grid.append(field('editCapital','模擬本金',account.initialCash,1,100000000,1),
      field('editExposure','曝險上限 %',account.costAssumptions.maxExposurePct,1,100),
      field('editCommission','手續費 bp',account.costAssumptions.commissionBps,0,500,'0.25'),
      field('editTax','賣出稅 bp',account.costAssumptions.sellTaxBps,0,500,'0.5'),
      field('editSlippage','滑價 bp',account.costAssumptions.slippageBps,0,500,'1'));
    settings.append(grid);
    if (account.strategy === 'neural') settings.append(element('p','fineprint','驗證用模型、預測門檻與特徵保持凍結；此處可調本金、曝險與成交成本。'));
    const saveSettings = element('button','secondary-button full-width','儲存模擬條件'); saveSettings.type='button'; saveSettings.dataset.action='save-settings'; settings.append(saveSettings);
    content.append(settings);
  }

  const move = element('button', 'walk-button full-width', walking.has(accountId) ? '帶它回自己的座位' : '讓它沿走道散步');
  move.type = 'button'; move.dataset.action = 'walk'; move.dataset.id = accountId;
  if (account.retired || (motionPreference.matches && !walking.has(accountId))) move.disabled = true;
  content.append(move);
  const actions = element('div', 'inspector-actions');
  if (!account.retired) {
    const advance = element('button', 'primary-button', account.paused && account.shares > 0 ? '同步並執行最後平倉' : '同步新收盤日');
    advance.type = 'button'; advance.dataset.action = 'advance'; advance.dataset.id = account.id; actions.append(advance);
    if (!account.paused) {
      const pause = element('button', 'stop-button', '停止策略並安排退場'); pause.type = 'button'; pause.dataset.action = 'pause'; pause.dataset.id = account.id; actions.append(pause);
    }
  }
  content.append(actions);
  const history = element('section', 'trade-history');
  history.append(element('h3', '', '最近事件'));
  const events = [...account.events].reverse().filter((event) => ['buy','sell','started','paused','resumed','rejected','retired','agent_decision','agent_automation'].includes(event.kind)).slice(0,8);
  if (!events.length) history.append(element('p', 'fineprint', '尚無交易事件。同步新收盤日後，策略才會依模擬規則建立紀錄。'));
  for (const event of events) {
    const line = element('div', `history-line event-${event.kind}`);
    const label = ({buy:'模擬買進',sell:'模擬賣出',started:'帳戶啟動',paused:'停止策略',resumed:'重新啟動',rejected:'委託未成交',retired:'吉祥物退場',agent_decision:'代理決策',agent_automation:'代理設定'})[event.kind] || event.kind;
    const detail = event.kind === 'agent_decision' ? `${Number(event.targetExposurePct || 0).toFixed(1)}% · ${event.rationale || ''}`
      : event.kind === 'agent_automation' ? (event.enabled ? '自動決策已啟用' : '自動決策已停用')
      : event.shares == null ? '—' : `${money(event.shares)} 股`;
    line.append(element('time','',event.date), element('strong','',label), element('span','',detail)); history.append(line);
  }
  content.append(history);
  byId('inspectorDialog').showModal();
}

function updateWalkControl(accountId) {
  if (selectedAccountId !== accountId) return;
  const button = byId('inspectorContent').querySelector('[data-action="walk"]');
  if (button) {
    const isWalking = walking.has(accountId);
    button.textContent = isWalking ? '帶它回自己的座位' : '讓它沿走道散步';
    button.disabled = motionPreference.matches && !isWalking;
  }
}

function scheduleAutomaticPatrols() {
  if (motionPreference.matches) {
    for (const timer of autoWalkTimers.values()) clearTimeout(timer);
    autoWalkTimers.clear();
    return;
  }
  if (walking.size || autoWalkTimers.size || !activeAccounts.length || !paperOffice) return;
  const index = nextAutomaticIndex % activeAccounts.length;
  const account = activeAccounts[index];
  nextAutomaticIndex = (index + 1) % activeAccounts.length;
  const timer = setTimeout(() => {
    autoWalkTimers.delete(account.id);
    const employee = paperOffice.emps.find((candidate) => candidate.id === account.id);
    if (activeAccounts.some((candidate) => candidate.id === account.id) && !walking.size && employee && paperOffice.atSeat(employee)) toggleWalk(account.id, true);
    else scheduleAutomaticPatrols();
  }, 2400);
  autoWalkTimers.set(account.id, timer);
}

function resetWalkerToSeat(accountId, seat = null, message = '', render = true, scheduleNextPatrol = true) {
  const employee = paperOffice?.emps.find((candidate) => candidate.id === accountId);
  walkGenerations.set(accountId, (walkGenerations.get(accountId) || 0) + 1);
  const timer = walkTimers.get(accountId);
  if (timer) clearTimeout(timer);
  walkTimers.delete(accountId);
  walking.delete(accountId);
  const autoTimer = autoWalkTimers.get(accountId);
  if (autoTimer) clearTimeout(autoTimer);
  autoWalkTimers.delete(accountId);
  if (employee) {
    employee.paperPatrolling = false;
    employee.status = 'idle';
    employee.restUntil = Infinity;
    employee.path = [];
    employee.tx = employee.seat.tx; employee.ty = employee.seat.ty;
    employee.x = employee.tx * 32; employee.y = employee.ty * 32;
    employee.anim = 'sit';
  }
  if (message) byId('roomMessage').textContent = message;
  if (render) renderRoom();
  updateWalkControl(accountId);
  if (scheduleNextPatrol) scheduleAutomaticPatrols();
}

function followOfficeRoute(accountId, generation, route, index = 0) {
  const employee = paperOffice?.emps.find((candidate) => candidate.id === accountId);
  if (!employee || walkGenerations.get(accountId) !== generation || !walking.has(accountId)) return;
  if (index >= route.length) {
    if (window.recordPaperPatrolOutcome(paperRouteModel, route, true, Date.now() - (route.startedAt || Date.now())) !== null) {
      persistPaperRouteModel();
      byId('roomMessage').textContent = `巡走完成並更新路線模型；已學習 ${paperRouteModel.total} 次路線結果。`;
    }
    resetWalkerToSeat(accountId, null, '', true, false);
    scheduleAutomaticPatrols();
    return;
  }
  employee.paperPatrolling = true;
  employee.restUntil = Infinity;
  const target = route[index];
  if (!paperOffice.goTo(employee, target.tx, target.ty)) {
    if (window.recordPaperPatrolOutcome(paperRouteModel, route, false) !== null) persistPaperRouteModel();
    resetWalkerToSeat(accountId, null, '走道目前無法連通，吉祥物已安全回到座位。');
    return;
  }
  const poll = () => {
    if (walkGenerations.get(accountId) !== generation || !walking.has(accountId)) return;
    if (employee.path.length || employee.tx !== target.tx || employee.ty !== target.ty) {
      const timer = setTimeout(poll, 100);
      walkTimers.set(accountId, timer);
      return;
    }
    employee.restUntil = Infinity;
    const timer = setTimeout(() => followOfficeRoute(accountId, generation, route, index + 1), 360);
    walkTimers.set(accountId, timer);
  };
  const timer = setTimeout(poll, 100);
  walkTimers.set(accountId, timer);
}

function toggleWalk(accountId, automatic = false) {
  const seat = [...document.querySelectorAll('.mascot-seat')].find((node) => node.dataset.id === accountId);
  const employee = paperOffice?.emps.find((candidate) => candidate.id === accountId);
  if (!seat || !employee) return;
  if (motionPreference.matches && !walking.has(accountId)) {
    byId('roomMessage').textContent = '系統已啟用減少動態，吉祥物會保持就座。';
    return;
  }
  const accountIndex = activeAccounts.findIndex((account) => account.id === accountId);
  if (accountIndex < 0) return;
  if (!walking.has(accountId) && !window.canStartPaperWalk(accountId, walking)) {
    byId('roomMessage').textContent = '這位吉祥物已在路線上。';
    return;
  }
  if (!automatic && !walking.has(accountId)) {
    for (const timer of autoWalkTimers.values()) clearTimeout(timer);
    autoWalkTimers.clear();
    nextAutomaticIndex = (accountIndex + 1) % Math.max(1, activeAccounts.length);
  }
  const oldTimer = walkTimers.get(accountId);
  if (oldTimer) clearTimeout(oldTimer);
  if (walking.has(accountId)) {
    const generation = (walkGenerations.get(accountId) || 0) + 1;
    walkGenerations.set(accountId, generation);
    employee.paperPatrolling = true;
    employee.restUntil = Infinity;
    byId('roomMessage').textContent = `${activeAccounts[accountIndex]?.nickname || '吉祥物'} 正沿走道回到自己的工位。`;
    followOfficeRoute(accountId, generation, [employee.seat]);
    return;
  }
  if (!paperOffice.atSeat(employee)) return;
  const generation = (walkGenerations.get(accountId) || 0) + 1;
  walkGenerations.set(accountId, generation);
  employee.paperPatrolling = true;
  employee.restUntil = Infinity;
  walking.add(accountId);
  const walkerCount = walking.size;
  byId('roomMessage').textContent = walkerCount > 1
    ? `${activeAccounts[accountIndex]?.nickname || '吉祥物'} 加入巡走；目前 ${walkerCount} 隻正在走動。`
    : `${activeAccounts[accountIndex]?.nickname || '吉祥物'} 正沿學習型避障路線巡走。`;
  updateWalkControl(accountId);
  const route = window.selectPaperPatrolRoute(employee.seat, paperRouteModel, accountIndex + generation - 1);
  if (!route) {
    resetWalkerToSeat(accountId, null, '目前座位無法建立安全巡走路線，角色已留在原位。');
    return;
  }
  route.startedAt = Date.now();
  followOfficeRoute(accountId, generation, route);
}

function resetWalkingOnResize() {
  paperOffice?.fit();
  syncPaperOfficeRoster();
  renderRoom();
  byId('roomMessage').textContent = '視窗尺寸已改變，角色會沿同一條家具避障路線繼續移動。';
}

function handleMotionPreferenceChange(event) {
  if (!event.matches) {
    scheduleAutomaticPatrols();
    return;
  }
  for (const timer of autoWalkTimers.values()) clearTimeout(timer);
  autoWalkTimers.clear();
  for (const accountId of [...walking]) resetWalkerToSeat(accountId, null, '', false, false);
  renderRoom();
  byId('roomMessage').textContent = '已依系統的減少動態設定暫停自動巡走。';
}

function renderSyncReport(outcomes) {
  const report = byId('syncReport');
  report.replaceChildren();
  report.hidden = outcomes.length === 0;
  const index = new Map([...activeAccounts, ...retiredAccounts].map((account) => [account.id, account]));
  for (const result of outcomes) {
    const account = index.get(result.id);
    const row = element('div', `sync-report-row ${result.ok ? 'success' : 'failure'}`);
    const detail = result.ok ? (result.advancedSessions ? `處理 ${result.advancedSessions} 個交易日 · 資料截至 ${result.lastDate}` : `沒有新交易日 · 資料截至 ${result.lastDate}`) : `同步失敗 · ${result.error}`;
    row.append(element('strong', '', account?.nickname || account?.symbol || result.id.slice(0,8)), element('span', '', detail));
    report.append(row);
  }
}

async function advanceOne(accountId, button) {
  button.disabled = true;
  byId('officeStage').classList.add('is-syncing');
  byId('roomMessage').textContent = '全室燈號亮起，正在按各自的新收盤日同步…';
  try {
    const result = await request(`/api/paper/accounts/${accountId}/advance`, { method: 'POST' });
    const account = result.account;
    const anchorNote = account.historyVerification === 'verified_with_saved_anchors'
      ? '本次沿用帳戶保存的錨點核對歷史。'
      : account.historyVerification === 'verified' ? '提交的歷史已與帳戶錨點核對。' : '';
    const syncNote = account.advancedSessions === 0 ? `${account.nickname || account.symbol} 沒有新交易日，帳戶未變動（截至 ${account.lastDate}）。` : `${account.nickname || account.symbol} 已處理 ${account.advancedSessions} 個新交易日，估值截至 ${account.lastDate}。`;
    byId('roomMessage').textContent = [syncNote, anchorNote].filter(Boolean).join(' ');
    if (walking.has(accountId)) {
      const walkingSeat = [...document.querySelectorAll('.mascot-seat.is-walking')].find((seat) => seat.dataset.id === accountId);
      if (walkingSeat) resetWalkerToSeat(accountId, walkingSeat, '', false);
    }
    const walkTimer = walkTimers.get(accountId);
    walkGenerations.set(accountId, (walkGenerations.get(accountId) || 0) + 1);
    if (walkTimer) clearTimeout(walkTimer);
    walkTimers.delete(accountId);
    walking.delete(accountId);
    await loadAccounts();
    if (byId('inspectorDialog').open) showInspector(accountId);
  } catch (error) {
    const motionNote = walking.has(accountId) ? ' 吉祥物巡走保持原狀。' : '';
    byId('roomMessage').textContent = `同步沒有完成：${error.message}${motionNote}`;
  } finally {
    byId('officeStage').classList.remove('is-syncing');
    button.disabled = false;
  }
}

byId('accountForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = byId('startAccount'), errorNode = byId('formError');
  errorNode.hidden = true;
  if (activeAccounts.length >= MAX_ROOM_SEATS) {
    errorNode.textContent = '8 個固定座位都已使用，請先讓角色退場。';
    errorNode.hidden = false;
    return;
  }
  button.disabled = true;
  try {
    const payload = {
      symbol: byId('symbol').value, strategy: byId('strategy').value,
      model: byId('strategy').value === 'neural' ? byId('model').value : null,
      agentProvider: byId('strategy').value === 'agent' ? byId('agentProvider').value : null,
      agentAutoEnabled: byId('strategy').value === 'agent' && byId('agentAutoEnabled').checked,
      buyThreshold: Number(byId('buyThreshold').value), sellThreshold: Number(byId('sellThreshold').value),
      initialCash: Number(byId('capital').value), lookback: Number(byId('lookback').value),
      maxExposurePct: Number(byId('maxExposure').value), commissionBps: Number(byId('commission').value),
      sellTaxBps: Number(byId('sellTax').value), slippageBps: Number(byId('slippage').value),
      nickname: byId('nickname').value, mascotColor: document.querySelector('input[name="mascotColor"]:checked').value,
      mascotAccessory: byId('accessory').value,
    };
    const fingerprint = JSON.stringify(payload);
    if (lastCreatePayload && lastCreatePayload !== fingerprint) {
      createKey = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }
    payload.creationKey = createKey;
    lastCreatePayload = fingerprint;
    await request('/api/paper/accounts', { method: 'POST', body: JSON.stringify(payload) });
    byId('callDialog').close();
    byId('roomMessage').textContent = '新夥伴找到座位了。點它可以查看策略與模擬帳戶。';
    await loadAccounts();
    createKey = null; lastCreatePayload = null;
  } catch (error) {
    errorNode.textContent = error.message; errorNode.hidden = false;
    button.disabled = false;
  }
});

byId('roomSeats').addEventListener('click', (event) => {
  const seat = event.target.closest('.mascot-seat');
  if (seat) showInspector(seat.dataset.id);
});
byId('retiredSeats').addEventListener('click', (event) => {
  const seat = event.target.closest('.mascot-seat');
  if (seat) showInspector(seat.dataset.id);
});
byId('inspectorContent').addEventListener('click', async (event) => {
  const closeButton = event.target.closest('[data-close]');
  if (closeButton) { byId(closeButton.dataset.close).close(); return; }
  const color = event.target.closest('[data-color]');
  if (color) {
    byId('inspectorContent').querySelectorAll('[data-color]').forEach((node) => { node.classList.remove('selected'); node.setAttribute('aria-pressed','false'); });
    color.classList.add('selected'); color.setAttribute('aria-pressed','true');
    updateMascotPreview();
    return;
  }
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  if (button.dataset.action === 'agent-automation') {
    button.disabled = true;
    try {
      await request(`/api/paper/accounts/${button.dataset.id}/agent-automation`, {
        method: 'POST', body: JSON.stringify({ enabled: !activeAccounts.find((item) => item.id === button.dataset.id)?.agentAutoEnabled }),
      });
      byId('roomMessage').textContent = '代理自動決策設定已更新；排程仍由對應的 Codex／Antigravity 客戶端執行。';
      await loadAccounts(); showInspector(button.dataset.id);
    } catch (error) { byId('roomMessage').textContent = `更新代理設定失敗：${error.message}`; button.disabled = false; }
    return;
  }
  if (button.dataset.action === 'walk') { toggleWalk(button.dataset.id); return; }
  if (button.dataset.action === 'save-mascot') {
    const selectedColor = byId('inspectorContent').querySelector('[data-color].selected')?.dataset.color || 'teal';
    button.disabled = true;
    try {
      await request(`/api/paper/accounts/${selectedAccountId}/mascot`, { method:'POST', body:JSON.stringify({
        nickname:byId('editNickname').value, mascotColor:selectedColor, mascotAccessory:byId('editAccessory').value,
      }) });
      await loadAccounts(); showInspector(selectedAccountId);
    } catch (error) { byId('roomMessage').textContent = `儲存外觀失敗：${error.message}`; button.disabled = false; }
    return;
  }
  if (button.dataset.action === 'save-settings') {
    button.disabled = true;
    try {
      await request(`/api/paper/accounts/${selectedAccountId}/settings`, { method:'POST', body:JSON.stringify({
        lookback:Number(byId('editLookback')?.value || activeAccounts.find((a)=>a.id===selectedAccountId)?.lookback || 20),
        initialCash:Number(byId('editCapital').value), maxExposurePct:Number(byId('editExposure').value),
        commissionBps:Number(byId('editCommission').value), sellTaxBps:Number(byId('editTax').value),
        slippageBps:Number(byId('editSlippage').value),
      }) });
      byId('roomMessage').textContent = '模擬條件已更新；第一次同步後會鎖定。';
      await loadAccounts(); showInspector(selectedAccountId);
    } catch (error) { byId('roomMessage').textContent = `儲存條件失敗：${error.message}`; button.disabled = false; }
    return;
  }
  if (button.dataset.action === 'pause' && !window.confirm('停止後不再建立新部位；若仍持有股票，會在下個新交易日收盤模擬最後平倉，完成後角色退場。若目前空手，角色會立即退場。繼續？')) return;
  if (button.dataset.action === 'advance') { await advanceOne(button.dataset.id, button); return; }
  button.disabled = true;
  try {
    await request(`/api/paper/accounts/${button.dataset.id}/${button.dataset.action}`, { method:'POST' });
    byId('roomMessage').textContent = button.dataset.action === 'pause' ? '策略已停止；吉祥物會留在座位等候最後平倉。' : '帳戶狀態已更新。';
    await loadAccounts(); showInspector(button.dataset.id);
  } catch (error) { byId('roomMessage').textContent = `操作失敗：${error.message}`; button.disabled = false; }
});
byId('inspectorContent').addEventListener('change', (event) => {
  if (event.target.id === 'editAccessory') updateMascotPreview();
});

byId('syncAll').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  if (!activeAccounts.length) { byId('roomMessage').textContent = '目前沒有在席帳戶可同步。'; return; }
  button.disabled = true; byId('officeStage').classList.add('is-syncing');
  byId('roomMessage').textContent = `全室 ${activeAccounts.length} 個帳戶正在各自同步；單一帳戶失敗不會中斷其他帳戶。`;
  try {
    const { outcomes } = await request('/api/paper/sync-all', { method:'POST' });
    const ok = outcomes.filter((item) => item.ok).length;
    const failed = outcomes.length - ok;
    await loadAccounts();
    renderSyncReport(outcomes);
    byId('roomMessage').textContent = `全室同步完成：${ok} 個帳戶成功，${failed} 個失敗。下方逐一列出日期與錯誤。`;
    if (selectedAccountId && byId('inspectorDialog').open) showInspector(selectedAccountId);
  } catch (error) { byId('roomMessage').textContent = `全室同步失敗：${error.message}`; }
  finally { button.disabled = false; byId('officeStage').classList.remove('is-syncing'); }
});

byId('callMascot').addEventListener('click', openCallDialog);
byId('seatSearch').addEventListener('input', renderRoom);
document.querySelectorAll('[data-close]').forEach((button) => button.addEventListener('click', () => byId(button.dataset.close).close()));
document.querySelectorAll('dialog').forEach((dialog) => dialog.addEventListener('click', (event) => {
  const bounds = dialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
}));
byId('strategy').addEventListener('change', () => {
  const strategy = byId('strategy').value;
  byId('agentSettings').hidden = strategy !== 'agent';
  if (strategy === 'neural') loadNeuralModels();
  else { neuralReady = false; byId('startAccount').disabled = !hasAvailableSymbol; }
});
byId('symbol').addEventListener('change', loadNeuralModels);
byId('nickname').addEventListener('input', updateCreationMascotPreview);
document.querySelectorAll('input[name="mascotColor"]').forEach((input) => input.addEventListener('change', updateCreationMascotPreview));
byId('accessory').addEventListener('change', updateCreationMascotPreview);
window.addEventListener('resize', () => {
  if (resizeFrame) frameScheduler.cancel(resizeFrame);
  resizeFrame = frameScheduler.schedule(() => {
    resizeFrame = null;
    paperOffice?.fit();
    if (!walking.size) renderRoom(); else resetWalkingOnResize();
  });
});
if (typeof motionPreference.addEventListener === 'function') motionPreference.addEventListener('change', handleMotionPreferenceChange);
else if (typeof motionPreference.addListener === 'function') motionPreference.addListener(handleMotionPreferenceChange);
setupPaperOffice();
loadNeuralModels(); loadSymbols(); loadAccounts();
