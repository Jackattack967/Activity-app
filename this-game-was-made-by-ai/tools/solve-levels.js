// Checks every level can be finished. Re-implements the player physics from
// src/game.js and breadth-first searches over held inputs (0.1 s each) for a
// route from the spawn to the flag. Run: node tools/solve-levels.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ctx = {};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'src', 'levels.js'), 'utf8') +
  '\nthis.LEVELS = LEVELS; this.LevelBuilder = LevelBuilder; this.flipLevel = flipLevel; this.TILE = TILE;', ctx);
const { LEVELS, LevelBuilder, flipLevel, TILE: T } = ctx;

const PHYS = { grav: 2000, jump: 720, run: 270, accG: 2600, accA: 1700, fricG: 2600, fricA: 700, maxFall: 900, coyote: 0.1, buffer: 0.13 };
const DT = 1 / 120, MACRO = 12, BEAM = 6000;
const approach = (v, t, d) => (v < t ? Math.min(v + d, t) : Math.max(v - d, t));
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const overlap = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

function solve(def, goal) {
  const b = new LevelBuilder(def.width);
  def.build(b, {});
  const lv = b.done();
  if (def.flipped) flipLevel(lv);
  const gd = def.flipped ? -1 : 1, gs = def.gravity || 1, js = def.jumpScale || 1;
  const at = (x, y) => (y < 0 || y >= lv.h || x < 0 || x >= lv.w ? '.' : lv.grid[y][x]);
  const solid = (x, y) => (x < 0 || x >= lv.w ? y >= 0 && y < lv.h : at(x, y) === '#' || at(x, y) === '?');
  const spikeUp = (x, y) => solid(x, y + 1) || (!solid(x, y - 1) && gd > 0);
  const spikeBox = (x, y) => (spikeUp(x, y) ? { x: x * T + 6, y: y * T + 12, w: T - 12, h: T - 12 } : { x: x * T + 6, y: y * T, w: T - 12, h: T - 12 });

  let target = goal;
  if (!target) {
    for (let y = 0; y < lv.h; y++) for (let x = 0; x < lv.w; x++) if (lv.grid[y][x] === 'F') target = { x: x * T + 8, y: gd > 0 ? (y - 1) * T : y * T, w: 14, h: 2 * T };
  }

  function step(p, dir, held, time) {
    if (dir) {
      const acc = (p.g ? PHYS.accG : PHYS.accA) * (Math.sign(p.vx) === -dir ? 1.8 : 1);
      p.vx = approach(p.vx, dir * PHYS.run, acc * DT);
    } else p.vx = approach(p.vx, 0, (p.g ? PHYS.fricG : PHYS.fricA) * DT);
    p.vy += gd * PHYS.grav * gs * DT;
    if (!held && p.vy * gd < 0) p.vy += gd * PHYS.grav * gs * DT * 1.4;
    const mf = Math.max(PHYS.maxFall * (gs < 1 ? 0.7 : 1), PHYS.jump);
    p.vy = clamp(p.vy, -mf, mf);
    p.co = p.g ? PHYS.coyote : p.co - DT;
    p.bu -= DT;
    if (p.bu > 0 && p.co > 0) { p.vy = -gd * PHYS.jump * js; p.bu = 0; p.co = 0; p.g = false; }
    // x
    p.x += p.vx * DT;
    let top = Math.floor(p.y / T), bot = Math.floor((p.y + p.h - 0.01) / T);
    if (p.vx > 0) { const tx = Math.floor((p.x + p.w - 0.01) / T); for (let ty = top; ty <= bot; ty++) if (solid(tx, ty)) { p.x = tx * T - p.w; p.vx = 0; break; } }
    else if (p.vx < 0) { const tx = Math.floor(p.x / T); for (let ty = top; ty <= bot; ty++) if (solid(tx, ty)) { p.x = (tx + 1) * T; p.vx = 0; break; } }
    // y
    p.g = false;
    const dy = p.vy * DT;
    p.y += dy;
    const l = Math.floor(p.x / T), r = Math.floor((p.x + p.w - 0.01) / T);
    if (dy > 0) { const ty = Math.floor((p.y + p.h - 0.01) / T); for (let tx = l; tx <= r; tx++) if (solid(tx, ty)) { p.y = ty * T - p.h; p.vy = 0; if (gd > 0) p.g = true; break; } }
    else if (dy < 0) { const ty = Math.floor(p.y / T); for (let tx = l; tx <= r; tx++) if (solid(tx, ty)) { p.y = (ty + 1) * T; p.vy = 0; if (gd < 0) p.g = true; break; } }
    // hazards
    const x0 = Math.floor((p.x + 2) / T), x1 = Math.floor((p.x + p.w - 2) / T), y0 = Math.floor((p.y + 2) / T), y1 = Math.floor((p.y + p.h - 2) / T);
    for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) if (at(tx, ty) === '^' && overlap(p, spikeBox(tx, ty))) return 'dead';
    if ((gd > 0 && p.y > lv.h * T + 40) || (gd < 0 && p.y + p.h < -40)) return 'dead';
    if (def.contextWall) {
      const wt = time - 3;
      const wall = -120 + (wt > 0 ? Math.min(120 * wt + 2 * wt * wt, 120 * 27.5 + 2 * 27.5 * 27.5 + 230 * Math.max(0, wt - 27.5)) : 0);
      if (p.x < wall) return 'dead';
    }
    if (overlap(p, target)) return 'win';
    return null;
  }

  const ph = 26, pw = 20;
  const start = { x: lv.start.x * T + (T - pw) / 2, y: gd > 0 ? lv.start.y * T + T - ph : lv.start.y * T, w: pw, h: ph, vx: 0, vy: 0, g: false, co: 0, bu: 0 };
  const key = p => `${Math.round(p.x / 3)},${Math.round(p.y / 3)},${Math.round(p.vx / 40)},${Math.round(p.vy / 50)},${p.g ? 1 : 0}`;
  const seen = new Set([key(start)]);
  let frontier = [start], depth = 0;
  const ACTIONS = [];
  for (const dir of [1, 0, -1]) for (const j of ['none', 'press', 'hold']) ACTIONS.push([dir, j]);
  while (frontier.length && depth < 700) {
    const next = [];
    for (const s of frontier) {
      for (const [dir, j] of ACTIONS) {
        if (j === 'hold' && s.g) continue;
        const p = Object.assign({}, s);
        if (j === 'press') p.bu = PHYS.buffer;
        let res = null;
        for (let i = 0; i < MACRO && !res; i++) res = step(p, dir, j !== 'none', (depth * MACRO + i) * DT);
        if (res === 'win') return { ok: true, seconds: ((depth + 1) * MACRO * DT).toFixed(1), explored: seen.size };
        if (res === 'dead') continue;
        const k = key(p);
        if (seen.has(k)) continue;
        seen.add(k); next.push(p);
      }
    }
    // Beam search: keep the states closest to the goal so long levels stay fast.
    if (next.length > BEAM) {
      const cx = target.x + target.w / 2, cy = target.y + target.h / 2;
      const d = p => Math.abs(p.x - cx) + 0.5 * Math.abs(p.y - cy);
      next.sort((a, b2) => d(a) - d(b2));
      next.length = BEAM;
    }
    frontier = next; depth++;
  }
  return { ok: false, explored: seen.size };
}

const jobs = [];
for (const base of LEVELS) {
  if (base.boss) continue;
  const defs = base.variants ? Object.entries(base.variants).map(([k, v]) => [`${base.name} (${k})`, Object.assign({}, base, v)]) : [[base.name, base]];
  for (const [name, def] of defs) {
    jobs.push([`${name}: flag`, def, null]);
    if (def.bugs) {
      const b = new LevelBuilder(def.width); def.build(b, {});
      b.done().ents.filter(e => e.type === 'bug').forEach(e => jobs.push([`${name}: bug ${e.id + 1}`, def, { x: e.x * T + 5, y: e.y * T + 6, w: 20, h: 18 }]));
    }
  }
}
let failed = 0;
for (const [name, def, goal] of jobs) {
  const r = solve(def, goal);
  if (!r.ok) failed++;
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${name.padEnd(28)} ${r.ok ? `fastest route ~${r.seconds}s` : 'no route found'}  (${r.explored} states)`);
}
process.exit(failed ? 1 : 0);
