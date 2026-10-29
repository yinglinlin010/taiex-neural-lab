'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
require('../web/vendor/pixel-office/layout.js');
const { createPaperFrameScheduler, getPaperMascotSpriteFrame, getPaperMascotPreviewFrame, getPaperMascotViewCrop, canStartPaperWalk, getPaperPatrolRoute, getPaperPatrolCandidates, createPaperRouteModel, selectPaperPatrolRoute, recordPaperPatrolOutcome, setPaperRosterActivity, shouldPaperMascotStaySeated, prunePaperWalkingState, createPaperOfficeItems, getPaperChairGeometry, PAPER_OFFICE_CONFIG } = require('../web/paper-motion.js');

function createOfficeLayout() {
  const deskTiles = PAPER_OFFICE_CONFIG.desks;
  const desks = deskTiles.map(([tx, ty], index) => ({
    id: `paperdesk${index}`, type: 'desk', tx, ty, emp: `account${index}`,
  }));
  const items = createPaperOfficeItems().filter((item) => item.type !== 'desk').concat(desks);
  const result = globalThis.POLayout.check(items, { empCount: 8 });
  return { deskTiles, result };
}

test('frame scheduler uses and cancels the matching browser API', () => {
  const calls = [];
  const host = {
    requestAnimationFrame: () => 17,
    cancelAnimationFrame: (id) => calls.push(['animation', id]),
    setTimeout: () => 41,
    clearTimeout: (id) => calls.push(['timeout', id]),
  };
  const scheduler = createPaperFrameScheduler(host);
  scheduler.cancel(scheduler.schedule(() => {}));
  assert.deepEqual(calls, [['animation', 17]]);

  const fallbackCalls = [];
  const fallback = createPaperFrameScheduler({ setTimeout: () => 41, clearTimeout: (id) => fallbackCalls.push(id) });
  fallback.cancel(fallback.schedule(() => {}));
  assert.deepEqual(fallbackCalls, [41]);
  scheduler.cancel(null);
});

test('mascot atlas selects the right hat, color row, view, and alternating walk frame', () => {
  const colors = ['teal', 'red', 'blue', 'cream'];
  const hats = ['cap', 'beret', 'crown'];
  colors.forEach((color, row) => hats.forEach((hat, group) => {
    assert.deepEqual(getPaperMascotSpriteFrame(hat, color, 'down', false), {
      kind: 'views', colorIndex: row, column: group, row: 0, flipX: false, frame: 0,
    });
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'right', false).row, 1);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'up', false).row, 2);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'left', false).flipX, true);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'down', true, 0).column, 0);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'down', true, 1).column, 1);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'right', true, 0).column, 2);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'up', true, 0).column, 4);
    assert.equal(getPaperMascotSpriteFrame(hat, color, 'up', true, 1).column, 5);
  }));
});

test('preview atlas uses one fixed cell and matching color row for every hat including none', () => {
  const colors = ['teal', 'red', 'blue', 'cream'];
  const accessories = ['none', 'cap', 'beret', 'crown'];
  colors.forEach((color, row) => accessories.forEach((accessory, column) => {
    assert.deepEqual(getPaperMascotPreviewFrame(accessory, color), {
      kind: 'preview', colorIndex: row, column, row, accessory,
    });
  }));
  assert.equal(getPaperMascotPreviewFrame(undefined, 'red').column, 0);
  assert.equal(getPaperMascotPreviewFrame('unknown', 'blue').column, 0);
  assert.equal(getPaperMascotPreviewFrame('dot', 'teal').column, 1);
  assert.equal(getPaperMascotPreviewFrame('leaf', 'teal').column, 2);
  assert.equal(getPaperMascotPreviewFrame('star', 'teal').column, 3);
});

test('preview sprite sheet has equally divisible four-by-four cells', () => {
  const png = fs.readFileSync(path.join(__dirname, '../web/paper-mascot-preview-atlas-v3.png'));
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  assert.equal(width % 4, 0);
  assert.equal(height % 4, 0);
  assert.deepEqual([width / 4, height / 4], [317, 320]);
});

test('simultaneous walkers keep independent atlas rows and legacy hat records remain supported', () => {
  const walkers = [
    ['cap', 'teal', 'down', 0], ['beret', 'red', 'up', 1], ['crown', 'blue', 'left', 0],
    ['cap', 'cream', 'right', 1], ['beret', 'teal', 'down', 1], ['crown', 'red', 'up', 0],
  ].map(([hat, color, direction, frame]) => getPaperMascotSpriteFrame(hat, color, direction, true, frame));
  assert.deepEqual(walkers.map(({ colorIndex }) => colorIndex), [0, 1, 2, 3, 0, 1]);
  assert.deepEqual(walkers.slice(2, 4).map(({ flipX }) => flipX), [true, false]);
  assert.equal(getPaperMascotSpriteFrame('dot', 'teal').column, 0);
  assert.equal(getPaperMascotSpriteFrame('leaf', 'red').column, 1);
  assert.equal(getPaperMascotSpriteFrame('star', 'blue').column, 2);
  assert.equal(getPaperMascotSpriteFrame('none', 'cream').kind, 'legacy');
});

test('no-hat preview still selects the requested mascot palette instead of a different character color', () => {
  const colors = ['teal', 'red', 'blue', 'cream'];
  colors.forEach((color, colorIndex) => {
    const sprite = getPaperMascotSpriteFrame('none', color);
    assert.equal(sprite.kind, 'legacy');
    assert.equal(sprite.colorIndex, colorIndex);
  });
});

test('mascot atlas crops include front and side feet while keeping the back crop inside the image', () => {
  assert.deepEqual(getPaperMascotViewCrop(0, 413, 1240), { y: 0, height: 443 });
  assert.deepEqual(getPaperMascotViewCrop(1, 413, 1240), { y: 443, height: 443 });
  assert.deepEqual(getPaperMascotViewCrop(2, 413, 1240), { y: 826, height: 414 });
  for (const args of [[-1, 413, 1240], [3, 413, 1240], [0, 0, 1240], [0, 413, 0]]) {
    assert.equal(getPaperMascotViewCrop(...args), null);
  }
});

test('manual patrol accepts one or several distinct walkers and rejects a duplicate start', () => {
  const walking = new Set();
  assert.equal(canStartPaperWalk('trader-a', walking), true);
  walking.add('trader-a');
  assert.equal(canStartPaperWalk('trader-b', walking), true);
  walking.add('trader-b');
  assert.equal(canStartPaperWalk('trader-c', walking), true);
  assert.equal(canStartPaperWalk('trader-a', walking), false);
  assert.equal(canStartPaperWalk('', walking), false);
  assert.equal(canStartPaperWalk('trader-c', null), false);
});

test('eight seats cycle through eight distinct perimeter patrol profiles and return home', () => {
  const routes = PAPER_OFFICE_CONFIG.desks.map(([tx, ty], index) => getPaperPatrolRoute({ tx, ty }, undefined, undefined, undefined, index));
  assert.equal(new Set(routes.map((route) => JSON.stringify(route.slice(1, -1)))).size, 8);
  assert.deepEqual(new Set(routes.map((route) => {
    const destination = route.at(-3);
    return globalThis.POLayout.ROOMS.find((room) => destination.tx >= room.x0 && destination.tx <= room.x1
      && destination.ty >= room.y0 && destination.ty <= room.y1)?.key;
  })), new Set(['kitchen', 'meeting', 'lounge', 'archive']));
  routes.forEach((route, index) => {
    assert.deepEqual(route.at(-1), { tx: PAPER_OFFICE_CONFIG.desks[index][0], ty: PAPER_OFFICE_CONFIG.desks[index][1] });
    assert.ok(route.some((point) => point.ty === 8 || point.ty === 9), 'each route uses a central cross aisle');
    assert.ok(route.some((point) => point.ty === 13 || point.ty === 14), 'each route uses a lower cross aisle');
    assert.ok(PAPER_OFFICE_CONFIG.roomStops[index].room, 'each route includes a room destination');
  });
  assert.equal(getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 0)[2].ty, 14);
  assert.equal(getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 2)[2].ty, 13);
  assert.equal(getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 3)[2].ty, 13);
  assert.equal(getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 4)[0].ty, 9);
  assert.deepEqual(getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 8), getPaperPatrolRoute({ tx: 9, ty: 4 }, undefined, undefined, undefined, 0));
  const exploredRooms = new Set(Array.from({ length: 4 }, (_, visit) => (
    PAPER_OFFICE_CONFIG.roomStops[(visit + 3) % PAPER_OFFICE_CONFIG.roomStops.length].room
  )));
  assert.deepEqual(exploredRooms, new Set(['kitchen', 'meeting', 'lounge', 'archive']));
});

test('online route model scores 64 candidates, explores new rooms, and learns from completed trips', () => {
  const seat = { tx: 13, ty: 4 };
  const model = createPaperRouteModel();
  const candidates = getPaperPatrolCandidates(seat);
  assert.equal(candidates.length, 64);
  assert.equal(new Set(candidates.map((route) => route.routeId)).size, 64);
  assert.ok(candidates.every((route) => route.features.length === 11 && route.at(-1).tx === seat.tx && route.at(-1).ty === seat.ty));

  const first = selectPaperPatrolRoute(seat, model, 0, () => 0);
  assert.ok(first);
  assert.equal(recordPaperPatrolOutcome(model, first, true, 20_000), 1);
  assert.equal(model.total, 1);
  assert.equal(model.counts[first.routeId], 1);
  assert.ok(model.weights.some((weight) => weight !== 0), 'completed trips update the learned logistic model');

  const second = selectPaperPatrolRoute(seat, model, 1, () => 0);
  assert.ok(second);
  assert.notEqual(second.routeId, first.routeId, 'recently used route profiles are down-weighted');
  assert.notEqual(second.room, first.room, 'near-term route selection favors exploring another room');
  assert.equal(recordPaperPatrolOutcome(model, second, false), 0);
  assert.equal(model.total, 2);
  assert.ok(model.weights.every((weight) => Number.isFinite(weight) && Math.abs(weight) <= 8));

  const restored = createPaperRouteModel(JSON.stringify(model));
  assert.deepEqual(restored, model);
  assert.equal(createPaperRouteModel('{broken json').total, 0);
  assert.equal(createPaperRouteModel({ weights: [Infinity], counts: { 'bad id': 9 }, total: -1 }).total, 0);
  assert.equal(selectPaperPatrolRoute(null, model), null);
  assert.equal(selectPaperPatrolRoute(seat, model, -1), null);
  assert.equal(recordPaperPatrolOutcome(model, [], true), null);
});

test('rejects invalid seats and route boundaries instead of producing unsafe coordinates', () => {
  for (const seat of [null, undefined, {}, { tx: 7, ty: 5 }, { tx: 18, ty: 16 }, { tx: 18.5, ty: 10 }]) {
    assert.equal(getPaperPatrolRoute(seat), null);
  }
  assert.equal(getPaperPatrolRoute({ tx: 18, ty: 10 }, 21, 20), null);
  assert.equal(getPaperPatrolRoute({ tx: 18, ty: 10 }, 8, 22), null);
  assert.equal(getPaperPatrolRoute({ tx: 18, ty: 10 }, 8, 21, 16), null);
  assert.equal(getPaperPatrolRoute({ tx: 18, ty: 10 }, undefined, undefined, undefined, -1), null);
});

test('roster refresh preserves an active patrol path and does not invent a new idle state', () => {
  const path = [{ tx: 10, ty: 12 }, { tx: 20, ty: 13 }];
  const employee = { status: 'working', path, tx: 10, ty: 11, paperPatrolling: false, restUntil: 0 };
  assert.equal(setPaperRosterActivity(employee, true), employee);
  assert.equal(employee.path, path);
  assert.equal(employee.tx, 10);
  assert.equal(employee.ty, 11);
  assert.equal(employee.paperPatrolling, true);
  assert.equal(employee.restUntil, Infinity);
  assert.equal(employee.status, 'working');
  setPaperRosterActivity(employee, false);
  assert.equal(employee.path, path);
  assert.equal(employee.status, 'idle');
  assert.equal(employee.paperPatrolling, false);
  assert.equal(setPaperRosterActivity(null, true), null);
});

test('managed mascots stay seated unless entering or following an explicit patrol', () => {
  const employee = { paperManaged: true, entering: false, paperPatrolling: false, path: [] };
  assert.equal(shouldPaperMascotStaySeated(employee, true), true);
  assert.equal(shouldPaperMascotStaySeated(employee, false), false);
  assert.equal(shouldPaperMascotStaySeated({ ...employee, entering: true }, true), false);
  assert.equal(shouldPaperMascotStaySeated({ ...employee, paperPatrolling: true }, true), false);
  assert.equal(shouldPaperMascotStaySeated({ ...employee, path: [{ tx: 1, ty: 2 }] }, true), false);
  assert.equal(shouldPaperMascotStaySeated({ ...employee, paperManaged: false }, true), false);
  assert.equal(shouldPaperMascotStaySeated(null, true), false);
});

test('removing an account cancels its patrol and automatic timers without disturbing active accounts', () => {
  const cleared = [];
  const state = {
    walking: new Set(['kept', 'removed']),
    generations: new Map([['kept', 3], ['removed', 8]]),
    walkTimers: new Map([['kept', 11], ['removed', 12]]),
    autoWalkTimers: new Map([['kept', 21], ['removed', 22]]),
  };
  prunePaperWalkingState(new Set(['kept']), state, (timer) => cleared.push(timer));
  assert.deepEqual(cleared.sort(), [12, 22]);
  assert.deepEqual([...state.walking], ['kept']);
  assert.equal(state.generations.get('removed'), 9);
  assert.equal(state.walkTimers.has('removed'), false);
  assert.equal(state.autoWalkTimers.has('removed'), false);
  assert.equal(state.generations.get('kept'), 3);
  assert.equal(state.walkTimers.get('kept'), 11);
  assert.equal(state.autoWalkTimers.get('kept'), 21);
});

test('eight-station floor has aligned desk banks, unobstructed cross aisles and a market screen on the office wall', () => {
  const { deskTiles, result } = createOfficeLayout();
  assert.equal(result.ok, true, JSON.stringify(result.errors));
  assert.equal(result.build.desks.length, 8);
  assert.equal(new Set(result.build.desks.map(({ tx, ty }) => `${tx}:${ty}`)).size, 8);

  assert.deepEqual(deskTiles, [[9, 4], [13, 4], [16, 4], [20, 4], [9, 11], [13, 11], [16, 11], [20, 11]]);
  const marketScreen = result.build && createPaperOfficeItems().find((item) => item.id === 'paperMarketScreen');
  assert.deepEqual({ type: marketScreen.type, tx: marketScreen.tx, ty: marketScreen.ty }, { type: 'default_tv', tx: 12, ty: 0 });
  const blocked = new Set([...result.build.blocked, ...result.build.soft.keys()]);
  for (const y of [8, 13, 14]) {
    for (let x = 8; x <= 21; x += 1) assert.equal(blocked.has(`${x},${y}`), false, `aisle tile ${x},${y} must stay open`);
  }
  const seatTiles = new Set(deskTiles.map(([tx, ty]) => `${tx},${ty}`));
  const findPath = (start, goal, ownSeat) => {
    const queue = [[start.tx, start.ty]];
    const startKey = `${start.tx},${start.ty}`;
    const seen = new Set([startKey]);
    const previous = new Map([[startKey, null]]);
    for (let i = 0; i < queue.length; i += 1) {
      const [x, y] = queue[i];
      if (x === goal.tx && y === goal.ty) {
        const path = [];
        let cursor = `${x},${y}`;
        while (cursor) {
          const [tx, ty] = cursor.split(',').map(Number);
          path.unshift({ tx, ty }); cursor = previous.get(cursor);
        }
        return path;
      }
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy, key = `${nx},${ny}`;
        if (nx < 0 || nx >= globalThis.POLayout.COLS || ny < 0 || ny >= globalThis.POLayout.ROWS || seen.has(key)) continue;
        if (!result.build.reach.has(key) && key !== ownSeat) continue;
        if (result.build.blocked.has(key) || result.build.soft.has(key) && key !== ownSeat || seatTiles.has(key) && key !== ownSeat) continue;
        seen.add(key);
        previous.set(key, `${x},${y}`);
        queue.push([nx, ny]);
      }
    }
    return null;
  };
  const uniqueRouteShapes = new Set();
  deskTiles.forEach(([tx, ty], index) => {
    const ownSeat = `${tx},${ty}`;
    const entryPath = findPath({ tx: 14, ty: 16 }, { tx, ty }, ownSeat);
    assert.ok(entryPath, `mascot ${index} cannot walk from the room entrance to its assigned chair`);
    assert.deepEqual(entryPath.at(-1), { tx, ty });
    const route = getPaperPatrolRoute({ tx, ty }, undefined, undefined, undefined, index);
    uniqueRouteShapes.add(JSON.stringify(route.slice(1, -1)));
    let current = { tx, ty };
    for (const waypoint of route) {
      const path = findPath(current, waypoint, ownSeat);
      assert.ok(path, `mascot ${index} cannot reach ${waypoint.tx},${waypoint.ty} without crossing furniture or a colleague's seat`);
      for (const point of path) {
        assert.equal(result.build.reach.has(`${point.tx},${point.ty}`) || `${point.tx},${point.ty}` === ownSeat, true, 'patrol stays on a connected room or doorway tile');
        assert.equal(result.build.blocked.has(`${point.tx},${point.ty}`), false, 'patrol never crosses furniture');
        assert.equal(seatTiles.has(`${point.tx},${point.ty}`) && `${point.tx},${point.ty}` !== ownSeat, false, 'patrol never crosses another mascot seat');
      }
      current = waypoint;
    }

    const candidates = getPaperPatrolCandidates({ tx, ty });
    assert.equal(candidates.length, 64, 'each seat receives the full learned route candidate set');
    for (const candidate of candidates) {
      current = { tx, ty };
      for (const waypoint of candidate) {
        const path = findPath(current, waypoint, ownSeat);
        assert.ok(path, `learned candidate ${candidate.routeId} cannot reach ${waypoint.tx},${waypoint.ty} without hitting an obstacle`);
        for (const point of path) {
          assert.equal(result.build.blocked.has(`${point.tx},${point.ty}`), false, 'learned routes never cross furniture');
          assert.equal(seatTiles.has(`${point.tx},${point.ty}`) && `${point.tx},${point.ty}` !== ownSeat, false, 'learned routes never cross another assigned seat');
        }
        current = waypoint;
      }
    }
  });
  assert.equal(uniqueRouteShapes.size, 8, 'all eight colleagues receive a distinct route profile');
});

test('chair back and seat are wider than the seated mascot and stay centered on its hips', () => {
  const geometry = getPaperChairGeometry(320, 192);
  assert.deepEqual(geometry.back, { x: 313, y: 154, width: 46, height: 24 });
  assert.deepEqual(geometry.seat, { x: 314, y: 184, width: 44, height: 8 });
  assert.ok(geometry.back.x < 316 && geometry.back.x + geometry.back.width > 356, 'backrest peeks out on both sides of the 40px sprite');
  assert.ok(geometry.seat.x < 316 && geometry.seat.x + geometry.seat.width > 356, 'seat peeks out beneath the mascot hips');
});
