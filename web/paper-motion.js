(function attachPaperMotion(root) {
  const OFFICE_CONFIG = Object.freeze({
    // Two aligned banks of four, with a broad cross aisle between them.
    desks: Object.freeze([[9, 4], [13, 4], [16, 4], [20, 4], [9, 11], [13, 11], [16, 11], [20, 11]].map(Object.freeze)),
    leftEdge: 8,
    rightEdge: 21,
    aisleRow: 8,
    splitX: 14,
    // Clear floor tiles in each adjoining room. Two targets per room give
    // returning patrols a different destination while keeping away from props.
    roomStops: Object.freeze([
      Object.freeze({ tx: 2, ty: 4, room: 'kitchen' }),
      Object.freeze({ tx: 28, ty: 7, room: 'meeting' }),
      Object.freeze({ tx: 2, ty: 15, room: 'lounge' }),
      Object.freeze({ tx: 28, ty: 15, room: 'archive' }),
      Object.freeze({ tx: 4, ty: 7, room: 'kitchen' }),
      Object.freeze({ tx: 23, ty: 5, room: 'meeting' }),
      Object.freeze({ tx: 5, ty: 13, room: 'lounge' }),
      Object.freeze({ tx: 24, ty: 12, room: 'archive' }),
    ]),
  });
  const ROUTE_FEATURE_COUNT = 11;
  const ROUTE_MODEL_KEY = 'paper-route-learning-v1';

  function createPaperOfficeItems(baseItems = root.POLayout?.defaultItems?.() || []) {
    // Keep the shared rooms furnished, but clear the trading floor's side lanes
    // and entrance so all eight desks have a continuous, usable circulation path.
    const items = baseItems.filter((item) => !['plant5', 'plant6', 'brew'].includes(item.id));
    return [
      ...items,
      // Put the market display on the open office wall; the upstream default
      // puts it in the neighboring meeting room where traders cannot see it.
      { id: 'default_cabinets', type: 'default_cabinets', tx: 0, ty: 0 },
      { id: 'paperMarketScreen', type: 'default_tv', tx: 12, ty: 0 },
      { id: 'default_shelf', type: 'default_shelf', tx: 20, ty: 0 },
      { id: 'default_whiteboard', type: 'default_whiteboard', tx: 28, ty: 0 },
      ...OFFICE_CONFIG.desks.map(([tx, ty], index) => ({ id: `paperdesk${index}`, type: 'desk', tx, ty })),
    ];
  }

  function getPaperChairGeometry(x, feet) {
    return {
      back: { x: x - 7, y: feet - 38, width: 46, height: 24 },
      seat: { x: x - 6, y: feet - 8, width: 44, height: 8 },
      stem: { x: x + 14, y: feet - 10, width: 4, height: 8 },
      base: { x: x + 3, y: feet - 3, width: 26, height: 3 },
    };
  }

  function createPaperFrameScheduler(host) {
    return {
      schedule(callback) {
        if (typeof host.requestAnimationFrame === 'function') {
          return { type: 'animation', id: host.requestAnimationFrame(callback) };
        }
        return { type: 'timeout', id: host.setTimeout(callback, 0) };
      },
      cancel(frame) {
        if (!frame) return;
        if (frame.type === 'animation' && typeof host.cancelAnimationFrame === 'function') {
          host.cancelAnimationFrame(frame.id);
        } else if (frame.type === 'timeout') {
          host.clearTimeout(frame.id);
        }
      },
    };
  }

  function getPaperMascotSpriteFrame(accessory, color, direction = 'down', walking = false, frame = 0) {
    const normalizedAccessory = ({ dot: 'cap', leaf: 'beret', star: 'crown' })[accessory] || accessory || 'cap';
    const hatIndex = ({ cap: 0, beret: 1, crown: 2 })[normalizedAccessory];
    const colorIndex = ({ teal: 0, red: 1, blue: 2, cream: 3 })[color] ?? 0;
    if (hatIndex === undefined || normalizedAccessory === 'none') {
      return { kind: 'legacy', colorIndex, direction: direction === 'up' ? 'up' : 'down', frame: ((frame % 2) + 2) % 2 };
    }
    const step = ((frame % 2) + 2) % 2;
    if (walking) {
      const group = direction === 'up' ? 2 : direction === 'left' || direction === 'right' ? 1 : 0;
      return { kind: 'walk', colorIndex, hatIndex, column: group * 2 + step, flipX: direction === 'left', frame: step };
    }
    const view = direction === 'up' ? 2 : direction === 'left' || direction === 'right' ? 1 : 0;
    return { kind: 'views', colorIndex, column: hatIndex, row: view, flipX: direction === 'left', frame: step };
  }

  function getPaperMascotPreviewFrame(accessory, color) {
    const normalizedAccessory = ({ dot: 'cap', leaf: 'beret', star: 'crown' })[accessory] || accessory || 'none';
    const column = ({ none: 0, cap: 1, beret: 2, crown: 3 })[normalizedAccessory] ?? 0;
    const colorIndex = ({ teal: 0, red: 1, blue: 2, cream: 3 })[color] ?? 0;
    return { kind: 'preview', colorIndex, column, row: colorIndex, accessory: normalizedAccessory };
  }

  function getPaperMascotViewCrop(row, cellHeight, imageHeight) {
    if (![0, 1, 2].includes(row) || !Number.isFinite(cellHeight) || cellHeight <= 0
      || !Number.isFinite(imageHeight) || imageHeight <= 0) return null;
    // Generated pose atlases place the feet about 30 source pixels below the
    // nominal first/side row. Extend those crops so front and profile views
    // keep their full bodies instead of clipping at the atlas grid line.
    const y = row === 0 ? 0 : row === 1 ? cellHeight + 30 : cellHeight * 2;
    const height = row === 2 ? imageHeight - y : cellHeight + 30;
    if (y >= imageHeight || height <= 0) return null;
    return { y, height: Math.min(height, imageHeight - y) };
  }

  // Manual patrols are independent: another mascot already walking must not
  // prevent this one from joining the route. The same mascot cannot be started
  // twice, which keeps its generation/timer state unambiguous.
  function canStartPaperWalk(accountId, walking) {
    return typeof accountId === 'string' && accountId.length > 0
      && walking instanceof Set && !walking.has(accountId);
  }

  function getPaperPatrolRoute(seat, leftEdge = OFFICE_CONFIG.leftEdge, rightEdge = OFFICE_CONFIG.rightEdge, aisleRow = OFFICE_CONFIG.aisleRow, routeIndex = 0) {
    const office = root.POLayout?.ROOMS?.find((room) => room.key === 'office');
    const minX = office?.x0 ?? 8, maxX = office?.x1 ?? 21;
    const minY = office?.y0 ?? 2, maxSeatY = (office?.y1 ?? 16) - 1;
    if (!seat || ![seat.tx, seat.ty, leftEdge, rightEdge, aisleRow].every(Number.isInteger)
      || seat.tx < minX || seat.tx > maxX || seat.ty < minY || seat.ty > maxSeatY
      || leftEdge < minX || rightEdge > maxX || leftEdge >= rightEdge
      || aisleRow < minY || aisleRow > maxSeatY
      || !Number.isInteger(routeIndex) || routeIndex < 0) return null;
    const style = routeIndex % 8;
    const firstEdge = style % 2 === 0 ? leftEdge : rightEdge;
    const secondEdge = firstEdge === leftEdge ? rightEdge : leftEdge;
    const lowerLane = Math.floor(style / 2) % 2 === 0 ? 14 : 13;
    const mainLane = Math.floor(style / 4) % 2 === 0 ? aisleRow : aisleRow + 1;
    // Each loop leaves the desk bank, uses the office aisles, visits one
    // adjoining room, then returns to the assigned chair. goTo() routes every
    // leg around furniture and the fixed room layout; the caller rotates the
    // profile so mascots eventually visit all four rooms.
    const stop = OFFICE_CONFIG.roomStops[style];
    const route = [
      { tx: seat.tx, ty: mainLane },
      { tx: firstEdge, ty: mainLane },
      { tx: firstEdge, ty: lowerLane },
      { tx: secondEdge, ty: lowerLane },
      { tx: secondEdge, ty: mainLane },
      { tx: stop.tx, ty: stop.ty },
      { tx: seat.tx, ty: mainLane },
      { tx: seat.tx, ty: seat.ty },
    ];
    return route.filter((point, index) => index === 0
      || point.tx !== route[index - 1].tx || point.ty !== route[index - 1].ty);
  }

  function buildPaperRoute(seat, stopIndex, mainLane, firstEdge, lowerLane, leftEdge, rightEdge) {
    const stop = OFFICE_CONFIG.roomStops[stopIndex];
    const secondEdge = firstEdge === leftEdge ? rightEdge : leftEdge;
    const route = [
      { tx: seat.tx, ty: mainLane },
      { tx: firstEdge, ty: mainLane },
      { tx: firstEdge, ty: lowerLane },
      { tx: secondEdge, ty: lowerLane },
      { tx: secondEdge, ty: mainLane },
      { tx: stop.tx, ty: stop.ty },
      { tx: seat.tx, ty: mainLane },
      { tx: seat.tx, ty: seat.ty },
    ].filter((point, index, points) => index === 0
      || point.tx !== points[index - 1].tx || point.ty !== points[index - 1].ty);
    const roomIndex = ['kitchen', 'meeting', 'lounge', 'archive'].indexOf(stop.room);
    const featureVector = [
      1,
      ...[0, 1, 2, 3].map((index) => Number(index === roomIndex)),
      Number(mainLane !== OFFICE_CONFIG.aisleRow),
      Number(firstEdge === rightEdge),
      Number(lowerLane === 13),
      Number(stopIndex >= 4),
      Math.min(1, route.slice(1).reduce((distance, point, index) => (
        distance + Math.abs(point.tx - route[index].tx) + Math.abs(point.ty - route[index].ty)
      ), 0) / 160),
      Math.min(1, route.slice(2).reduce((turns, point, index) => {
        const before = route[index + 1], after = route[index + 2];
        if (!before || !after) return turns;
        const inX = Math.sign(before.tx - route[index].tx), inY = Math.sign(before.ty - route[index].ty);
        const outX = Math.sign(after.tx - before.tx), outY = Math.sign(after.ty - before.ty);
        return turns + Number(inX !== outX || inY !== outY);
      }, 0) / 7),
    ];
    route.routeId = `${stop.room}:${Number(stopIndex >= 4)}:${mainLane}:${firstEdge}:${lowerLane}`;
    route.room = stop.room;
    route.features = featureVector;
    return route;
  }

  function getPaperPatrolCandidates(seat, leftEdge = OFFICE_CONFIG.leftEdge, rightEdge = OFFICE_CONFIG.rightEdge, aisleRow = OFFICE_CONFIG.aisleRow) {
    const office = root.POLayout?.ROOMS?.find((room) => room.key === 'office');
    const minX = office?.x0 ?? 8, maxX = office?.x1 ?? 21;
    const minY = office?.y0 ?? 2, maxSeatY = (office?.y1 ?? 16) - 1;
    if (!seat || ![seat.tx, seat.ty, leftEdge, rightEdge, aisleRow].every(Number.isInteger)
      || seat.tx < minX || seat.tx > maxX || seat.ty < minY || seat.ty > maxSeatY
      || leftEdge < minX || rightEdge > maxX || leftEdge >= rightEdge
      || aisleRow < minY || aisleRow + 1 > maxSeatY) return [];
    const routes = [];
    for (let stopIndex = 0; stopIndex < OFFICE_CONFIG.roomStops.length; stopIndex += 1) {
      for (const mainLane of [aisleRow, aisleRow + 1]) {
        for (const firstEdge of [leftEdge, rightEdge]) {
          for (const lowerLane of [13, 14]) {
            routes.push(buildPaperRoute(seat, stopIndex, mainLane, firstEdge, lowerLane, leftEdge, rightEdge));
          }
        }
      }
    }
    return routes;
  }

  function createPaperRouteModel(saved) {
    let source = saved;
    if (typeof source === 'string') {
      try { source = JSON.parse(source); } catch { source = null; }
    }
    const weights = Array.isArray(source?.weights) && source.weights.length === ROUTE_FEATURE_COUNT
      ? source.weights.map((value) => Number.isFinite(value) ? Math.max(-8, Math.min(8, value)) : 0)
      : Array(ROUTE_FEATURE_COUNT).fill(0);
    const counts = {};
    if (source?.counts && typeof source.counts === 'object') {
      for (const [key, value] of Object.entries(source.counts)) {
        if (/^[a-z]+:\d:[0-9]+:[0-9]+:(?:13|14)$/.test(key) && Number.isInteger(value) && value >= 0) counts[key] = value;
      }
    }
    const recent = Array.isArray(source?.recent) ? source.recent.filter((id) => typeof id === 'string').slice(-8) : [];
    const recentRooms = Array.isArray(source?.recentRooms)
      ? source.recentRooms.filter((room) => ['kitchen', 'meeting', 'lounge', 'archive'].includes(room)).slice(-4)
      : [];
    return {
      version: 1,
      weights,
      counts,
      total: Number.isInteger(source?.total) && source.total >= 0 ? source.total : 0,
      recent,
      recentRooms,
    };
  }

  function sigmoid(value) {
    const bounded = Math.max(-30, Math.min(30, value));
    return 1 / (1 + Math.exp(-bounded));
  }

  function selectPaperPatrolRoute(seat, modelValue, rotationIndex = 0, random = Math.random) {
    const model = createPaperRouteModel(modelValue);
    if (!Number.isInteger(rotationIndex) || rotationIndex < 0) return null;
    const candidates = getPaperPatrolCandidates(seat);
    if (!candidates.length) return null;
    const recentRoutes = new Set(model.recent.slice(-4));
    const recentRooms = new Set(model.recentRooms.slice(-3));
    const logTotal = Math.log(model.total + 2);
    let bestScore = -Infinity;
    let best = [];
    for (let index = 0; index < candidates.length; index += 1) {
      const route = candidates[index];
      const prediction = sigmoid(route.features.reduce((sum, feature, i) => sum + feature * model.weights[i], 0));
      const visits = model.counts[route.routeId] || 0;
      const exploration = 0.3 * Math.sqrt(logTotal / (visits + 1));
      const repetitionPenalty = (recentRoutes.has(route.routeId) ? 0.65 : 0)
        + (recentRooms.has(route.room) ? 0.18 : 0);
      const tieBreak = ((index + rotationIndex) % candidates.length) * 1e-7 + random() * 1e-9;
      const score = prediction + exploration - repetitionPenalty + tieBreak;
      if (score > bestScore + 1e-10) { bestScore = score; best = [route]; }
      else if (Math.abs(score - bestScore) <= 1e-10) best.push(route);
    }
    return best[(rotationIndex + Math.floor(random() * best.length)) % best.length] || null;
  }

  function recordPaperPatrolOutcome(modelValue, route, success, durationMs = 0) {
    if (!modelValue || !route?.routeId || !Array.isArray(route.features)
      || route.features.length !== ROUTE_FEATURE_COUNT || !Array.isArray(modelValue.weights)
      || modelValue.weights.length !== ROUTE_FEATURE_COUNT || !modelValue.counts
      || !Number.isInteger(modelValue.total) || !Array.isArray(modelValue.recent)
      || !Array.isArray(modelValue.recentRooms)) return null;
    const model = modelValue;
    const wasRecentlySeen = model.recent.includes(route.routeId);
    const roomRecentlySeen = model.recentRooms.slice(-3).includes(route.room);
    const durationPenalty = Number.isFinite(durationMs) && durationMs > 90000
      ? Math.min(0.25, (durationMs - 90000) / 360000) : 0;
    const reward = success
      ? Math.max(0, Math.min(1, 0.65 + (wasRecentlySeen ? 0 : 0.2) + (roomRecentlySeen ? 0 : 0.15) - durationPenalty))
      : 0;
    const prediction = sigmoid(route.features.reduce((sum, feature, i) => sum + feature * model.weights[i], 0));
    const error = reward - prediction;
    for (let i = 0; i < ROUTE_FEATURE_COUNT; i += 1) {
      model.weights[i] = Math.max(-8, Math.min(8, model.weights[i] + 0.16 * error * route.features[i] - 0.002 * model.weights[i]));
    }
    model.counts[route.routeId] = (model.counts[route.routeId] || 0) + 1;
    model.total += 1;
    model.recent.push(route.routeId);
    model.recent = model.recent.slice(-8);
    model.recentRooms.push(route.room);
    model.recentRooms = model.recentRooms.slice(-4);
    return reward;
  }

  function setPaperRosterActivity(employee, isWalking) {
    if (!employee) return null;
    employee.restUntil = Infinity;
    employee.paperPatrolling = Boolean(isWalking);
    if (!isWalking) employee.status = 'idle';
    return employee;
  }

  function shouldPaperMascotStaySeated(employee, atSeat) {
    return Boolean(employee?.paperManaged && !employee.entering && !employee.paperPatrolling
      && !employee.path?.length && atSeat);
  }

  function prunePaperWalkingState(activeIds, state, clearTimer = clearTimeout) {
    const active = activeIds instanceof Set ? activeIds : new Set(activeIds || []);
    for (const accountId of [...state.walking]) {
      if (active.has(accountId)) continue;
      state.generations.set(accountId, (state.generations.get(accountId) || 0) + 1);
      const timer = state.walkTimers.get(accountId);
      if (timer) clearTimer(timer);
      state.walkTimers.delete(accountId);
      state.walking.delete(accountId);
    }
    for (const [accountId, timer] of [...state.autoWalkTimers]) {
      if (active.has(accountId)) continue;
      clearTimer(timer);
      state.autoWalkTimers.delete(accountId);
    }
    return state;
  }

  root.createPaperFrameScheduler = createPaperFrameScheduler;
  root.getPaperMascotSpriteFrame = getPaperMascotSpriteFrame;
  root.getPaperMascotPreviewFrame = getPaperMascotPreviewFrame;
  root.getPaperMascotViewCrop = getPaperMascotViewCrop;
  root.canStartPaperWalk = canStartPaperWalk;
  root.getPaperPatrolRoute = getPaperPatrolRoute;
  root.getPaperPatrolCandidates = getPaperPatrolCandidates;
  root.createPaperRouteModel = createPaperRouteModel;
  root.selectPaperPatrolRoute = selectPaperPatrolRoute;
  root.recordPaperPatrolOutcome = recordPaperPatrolOutcome;
  root.PAPER_ROUTE_MODEL_KEY = ROUTE_MODEL_KEY;
  root.setPaperRosterActivity = setPaperRosterActivity;
  root.shouldPaperMascotStaySeated = shouldPaperMascotStaySeated;
  root.prunePaperWalkingState = prunePaperWalkingState;
  root.PAPER_OFFICE_CONFIG = OFFICE_CONFIG;
  root.createPaperOfficeItems = createPaperOfficeItems;
  root.getPaperChairGeometry = getPaperChairGeometry;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { createPaperFrameScheduler, getPaperMascotSpriteFrame, getPaperMascotPreviewFrame, getPaperMascotViewCrop, canStartPaperWalk, getPaperPatrolRoute, getPaperPatrolCandidates, createPaperRouteModel, selectPaperPatrolRoute, recordPaperPatrolOutcome, setPaperRosterActivity, shouldPaperMascotStaySeated, prunePaperWalkingState, createPaperOfficeItems, getPaperChairGeometry, PAPER_OFFICE_CONFIG: OFFICE_CONFIG, PAPER_ROUTE_MODEL_KEY: ROUTE_MODEL_KEY };
  }
})(typeof globalThis === 'undefined' ? this : globalThis);
