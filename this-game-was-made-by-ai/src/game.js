'use strict';
(function () {
  const W = 960, H = 540, T = TILE;
  const canvas = document.getElementById('game');
  const ctx = canvas.getContext('2d');
  const IS_ELECTRON = /Electron/i.test(navigator.userAgent);
  const params = new URLSearchParams(location.search);
  const FONT = '"Cascadia Mono", Consolas, "DejaVu Sans Mono", Menlo, monospace';

  const C = {
    bg: '#0b0d12', grid: '#121722', tile: '#161c2a', tileIn: '#1b2335', edge: '#2dd4bf',
    text: '#e5e7eb', dim: '#7b8496', accent: '#2dd4bf', warn: '#f59e0b', danger: '#f43f5e',
    good: '#22c55e', magenta: '#ff00ff', skin: '#f1c7a5', skinDark: '#c99a78',
  };

  const PHYS = { grav: 2000, jump: 720, run: 270, accG: 2600, accA: 1700, fricG: 2600, fricA: 700, maxFall: 900, coyote: 0.1, buffer: 0.13 };
  const STEP = 1 / 120;

  // ---------------- save ----------------
  const SAVE_KEY = 'tgwmbai.save.v1';
  function loadSave() { try { return JSON.parse(localStorage.getItem(SAVE_KEY)) || {}; } catch (e) { return {}; } }
  function writeSave() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch (e) { /* ignore */ } }
  const save = Object.assign({ unlocked: 0, deaths: 0, time: 0, completed: false }, loadSave());

  // ---------------- utils ----------------
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const rand = (a, b) => a + Math.random() * (b - a);
  const approach = (v, t, d) => (v < t ? Math.min(v + d, t) : Math.max(v - d, t));
  const overlap = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  function font(px, weight) { ctx.font = `${weight || ''} ${px}px ${FONT}`; }
  function rrect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  function wrap(text, maxW) {
    const words = text.split(' '), lines = [];
    let line = '';
    for (const w of words) {
      const test = line ? line + ' ' + w : w;
      if (ctx.measureText(test).width > maxW && line) { lines.push(line); line = w; } else line = test;
    }
    if (line) lines.push(line);
    return lines;
  }
  function fmtTime(s) { s = Math.floor(s); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }
  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
  }

  // ---------------- display ----------------
  let scale = 1, dpr = 1, offX = 0, offY = 0;
  function resize() {
    dpr = window.devicePixelRatio || 1;
    scale = Math.min(window.innerWidth / W, window.innerHeight / H);
    canvas.style.width = `${W * scale}px`;
    canvas.style.height = `${H * scale}px`;
    canvas.width = Math.round(W * scale * dpr);
    canvas.height = Math.round(H * scale * dpr);
    const r = canvas.getBoundingClientRect(); offX = r.left; offY = r.top;
  }
  window.addEventListener('resize', resize);
  resize();

  // ---------------- narrator ----------------
  const LOREM = 'lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua'.split(' ');
  const loremize = text => text.split(' ').map((w, i) => LOREM[(i * 7 + w.length) % LOREM.length]).join(' ');
  const narrator = {
    queue: [], cur: null, shown: 0, hold: 0,
    say(text) { if (text) this.queue.push(text); },
    urgent(text) {
      if (!text) return;
      this.queue.unshift(text);
      if (this.cur && this.shown >= this.cur.length) this.cur = null;
    },
    clear() { this.queue.length = 0; this.cur = null; },
    update(dt) {
      if (!this.cur && this.queue.length) { this.cur = this.queue.shift(); this.shown = 0; this.hold = 0; }
      if (!this.cur) return;
      if (this.shown < this.cur.length) {
        const before = Math.floor(this.shown);
        this.shown = Math.min(this.cur.length, this.shown + dt * 50);
        if (Math.floor(this.shown) !== before && before % 3 === 0) Sound.sfx.type();
      } else {
        this.hold += dt;
        const need = this.queue.length ? 1.3 : Math.max(2.8, this.cur.length * 0.055);
        if (this.hold > need) this.cur = null;
      }
    },
    skip() { if (this.cur) { if (this.shown < this.cur.length) this.shown = this.cur.length; else this.cur = null; } },
  };

  // ---------------- game state ----------------
  const G = {
    state: 'title', t: 0, sel: 0, hits: [], hover: -1,
    run: { deaths: save.deaths, time: save.time, rating: 0, choice: null },
    def: null, index: 0, variant: null, lv: null, lp: null, ls: null,
    player: null, ents: [], parts: [], cam: 0, shake: 0, gd: 1,
    dead: 0, finished: 0, attemptT: 0, paused: false, flags: [], bgCode: [],
  };

  const api = {
    say: t => narrator.say(t),
    urgent: t => narrator.urgent(t),
    get lp() { return G.lp; },
    get ls() { return G.ls; },
    get player() { return G.player; },
    kill: cause => kill(cause),
    forgetBefore,
  };

  function resolveDef(i, v) {
    const base = LEVELS[i];
    return base.variants ? Object.assign({}, base, base.variants[v], { variants: null, choice: null }) : base;
  }

  // Route to a level, through the prompt screen if it has variants.
  function goToLevel(i, outro) {
    const base = LEVELS[i];
    G.index = i;
    if (base.variants && !G.variant) {
      G.card = makeCard(outro, base, ['awaiting prompt from user ......'], () => { G.state = 'choice'; G.sel = 0; });
    } else {
      const def = resolveDef(i, G.variant);
      G.card = makeCard(outro, def, def.genLog, () => startLevel(i));
    }
    G.state = 'card';
    Sound.setTrack('title');
  }

  function makeCard(outro, def, log, done) {
    return { outro: outro || '', def, log: log || [], done, t: 0 };
  }

  function startLevel(i) {
    G.index = i;
    G.def = resolveDef(i, G.variant);
    G.lp = { deaths: 0, fired: new Set(), time: 0, collected: new Set() };
    narrator.clear();
    spawnAttempt(true);
    (G.def.intro || []).forEach(t => narrator.say(t));
    Sound.setTrack(G.def.music || 'main');
    G.state = 'play';
    G.paused = false;
    save.unlocked = Math.max(save.unlocked, i);
    writeSave();
  }

  function spawnAttempt(first) {
    const def = G.def;
    const b = new LevelBuilder(def.width);
    def.build(b, G.lp);
    const lv = b.done();
    if (def.flipped) flipLevel(lv);
    lv.forgot = 0;
    G.lv = lv;
    G.ls = {};
    G.gd = def.flipped ? -1 : 1;
    G.flags = [];
    for (let y = 0; y < lv.h; y++) for (let x = 0; x < lv.w; x++) {
      const c = lv.grid[y][x];
      if (c === 'F' || c === 'f') G.flags.push({ x, y, fake: c === 'f' });
    }
    const pw = 20, ph = 26;
    G.player = {
      x: lv.start.x * T + (T - pw) / 2,
      y: def.flipped ? lv.start.y * T : lv.start.y * T + T - ph,
      w: pw, h: ph, vx: 0, vy: 0, onGround: false, coyote: 0, buffer: 0, face: 1, sx: 1, sy: 1, prevY: 0,
    };
    G.ents = lv.ents.map(makeEntity).filter(Boolean);
    G.cam = clamp(G.player.x - W / 2, 0, Math.max(0, lv.w * T - W));
    G.attemptT = 0; G.dead = 0; G.finished = 0;
    G.bgCode = makeBgCode(lv.w);
    if (def.onAttempt) def.onAttempt(api, first);
  }

  const CODE_SNIPPETS = [
    'if (player.isHavingFun()) { keep(); }', '// TODO: make game good', 'spikes.push(spike); // more?',
    'const fun = Math.random();', 'while (true) { addLevel(); }', "// I don't know why this works",
    'player = new Rectangle(); // v2', 'assert(platform.isReal); // usually', "return 'flag'; // probably",
    '/* generated in one try */', 'gravity = 9.8 * vibes;', '// sorry', 'fingers = 5; // or 6', 'import { fun } from "?";',
    'catch (e) { /* it is fine */ }', 'player.feelings = undefined;', '// please do not read this',
  ];
  function makeBgCode(wTiles) {
    const out = [], n = Math.max(10, Math.floor(wTiles / 5));
    for (let i = 0; i < n; i++) {
      out.push({ x: rand(0, wTiles * T * 0.45 + W), y: rand(100, H - 20), s: CODE_SNIPPETS[i % CODE_SNIPPETS.length] });
    }
    return out;
  }

  function makeEntity(e) {
    switch (e.type) {
      case 'duck': return { type: 'duck', x: e.x * T + 4, y: e.y * T + T - 18, w: 22, h: 18, vx: (Math.random() < 0.5 ? -1 : 1) * 35, cd: 0, hop: 0 };
      case 'bug':
        if (G.lp.collected.has(e.id)) return null;
        return { type: 'bug', id: e.id, x: e.x * T + 5, y: e.y * T + 6, w: 20, h: 18, t: Math.random() * 6 };
      case 'boss': return { type: 'boss', x: W / 2 - 85, y: -160, w: 170, h: 70, state: 'enter', t: 0, hp: 3, vy: 0, flash: 0, tokT: 1, fingers: 6 };
      default: return null;
    }
  }

  // ---------------- tiles ----------------
  function tileAt(tx, ty) {
    const lv = G.lv;
    if (ty < 0 || ty >= lv.h || tx < 0 || tx >= lv.w) return '.';
    return lv.grid[ty][tx];
  }
  function isSolid(tx, ty) {
    const lv = G.lv;
    if (tx < 0 || tx >= lv.w) return ty >= 0 && ty < lv.h; // level ends are walls
    const c = tileAt(tx, ty);
    return c === '#' || c === '?';
  }
  const looksSolid = (tx, ty) => { const c = tileAt(tx, ty); return c === '#' || c === '~'; };

  function forgetBefore(px) {
    const lv = G.lv, upto = Math.min(lv.w, Math.floor(px / T));
    for (let x = lv.forgot; x < upto; x++) for (let y = 0; y < lv.h; y++) lv.grid[y][x] = '.';
    lv.forgot = Math.max(lv.forgot, upto);
  }

  function spikePointsUp(tx, ty) {
    const below = isSolid(tx, ty + 1), above = isSolid(tx, ty - 1);
    return below || (!above && G.gd > 0);
  }
  function spikeBox(tx, ty) {
    return spikePointsUp(tx, ty)
      ? { x: tx * T + 6, y: ty * T + 12, w: T - 12, h: T - 12 }
      : { x: tx * T + 6, y: ty * T, w: T - 12, h: T - 12 };
  }

  // ---------------- bugs (level 5) ----------------
  function bugActive(id) {
    if (!G.def || !G.def.bugs || G.state !== 'play') return false;
    return BUGS.findIndex(b => b.id === id) >= G.lp.collected.size;
  }

  // ---------------- player ----------------
  function moveX(p, dx) {
    p.x += dx;
    const top = Math.floor(p.y / T), bot = Math.floor((p.y + p.h - 0.01) / T);
    if (dx > 0) {
      const tx = Math.floor((p.x + p.w - 0.01) / T);
      for (let ty = top; ty <= bot; ty++) if (isSolid(tx, ty)) { p.x = tx * T - p.w; p.vx = 0; return; }
    } else if (dx < 0) {
      const tx = Math.floor(p.x / T);
      for (let ty = top; ty <= bot; ty++) if (isSolid(tx, ty)) { p.x = (tx + 1) * T; p.vx = 0; return; }
    }
  }
  function moveY(p, dy) {
    p.y += dy;
    const l = Math.floor(p.x / T), r = Math.floor((p.x + p.w - 0.01) / T);
    if (dy > 0) {
      const ty = Math.floor((p.y + p.h - 0.01) / T);
      for (let tx = l; tx <= r; tx++) if (isSolid(tx, ty)) { p.y = ty * T - p.h; p.vy = 0; if (G.gd > 0) p.onGround = true; return; }
    } else if (dy < 0) {
      const ty = Math.floor(p.y / T);
      for (let tx = l; tx <= r; tx++) if (isSolid(tx, ty)) { p.y = (ty + 1) * T; p.vy = 0; if (G.gd < 0) p.onGround = true; return; }
    }
  }

  function updatePlayer(dt) {
    const p = G.player, gd = G.gd, def = G.def;
    const gs = def.gravity || 1, js = def.jumpScale || 1;
    let dir = (Input.down('right') ? 1 : 0) - (Input.down('left') ? 1 : 0);
    if (bugActive('swap')) dir = -dir;
    if (dir) {
      const acc = (p.onGround ? PHYS.accG : PHYS.accA) * (Math.sign(p.vx) === -dir ? 1.8 : 1);
      p.vx = approach(p.vx, dir * PHYS.run, acc * dt);
      p.face = dir;
    } else {
      p.vx = approach(p.vx, 0, (p.onGround ? PHYS.fricG : PHYS.fricA) * dt);
    }
    p.vy += gd * PHYS.grav * gs * dt;
    const held = Input.down('jump') || Input.down('up');
    if (!held && p.vy * gd < 0) p.vy += gd * PHYS.grav * gs * dt * 1.4;
    const mf = PHYS.maxFall * (gs < 1 ? 0.7 : 1);
    p.vy = clamp(p.vy, -Math.max(mf, PHYS.jump), Math.max(mf, PHYS.jump));
    p.coyote = p.onGround ? PHYS.coyote : p.coyote - dt;
    p.buffer -= dt;
    if (p.buffer > 0 && p.coyote > 0) {
      p.vy = -gd * PHYS.jump * js;
      p.buffer = 0; p.coyote = 0; p.onGround = false;
      p.sx = 0.75; p.sy = 1.3;
      Sound.sfx.jump();
    }
    p.prevY = p.y;
    moveX(p, p.vx * dt);
    const was = p.onGround;
    p.onGround = false;
    moveY(p, p.vy * dt);
    if (p.onGround && !was) { p.sx = 1.25; p.sy = 0.78; }
    p.sx = approach(p.sx, 1, dt * 3); p.sy = approach(p.sy, 1, dt * 3);

    // hazards
    const x0 = Math.floor((p.x + 2) / T), x1 = Math.floor((p.x + p.w - 2) / T);
    const y0 = Math.floor((p.y + 2) / T), y1 = Math.floor((p.y + p.h - 2) / T);
    for (let ty = y0; ty <= y1; ty++) for (let tx = x0; tx <= x1; tx++) {
      if (tileAt(tx, ty) === '^' && overlap(p, spikeBox(tx, ty))) { kill('spike'); return; }
    }
    if ((gd > 0 && p.y > G.lv.h * T + 40) || (gd < 0 && p.y + p.h < -40)) { kill('fall'); return; }

    // flags
    for (const f of G.flags) {
      const zone = { x: f.x * T + 8, y: gd > 0 ? (f.y - 1) * T : f.y * T, w: 14, h: 2 * T };
      if (!overlap(p, zone)) continue;
      if (f.fake) {
        G.lv.grid[f.y][f.x] = '.';
        G.flags = G.flags.filter(o => o !== f);
        burst(f.x * T + 15, f.y * T, C.good, 22);
        Sound.sfx.glitch();
        narrator.urgent(def.onFakeFlag || 'That flag was not real.');
        return;
      }
      if (def.flagLocked && def.flagLocked(api)) {
        if (!G.ls.lockedSaid) { G.ls.lockedSaid = true; Sound.sfx.error(); narrator.urgent("It's locked. Collect all the bugs first. I can't ship it like this."); }
        return;
      }
      finishLevel();
      return;
    }
  }

  function kill(cause) {
    if (G.dead > 0 || G.finished > 0 || G.ls.won) return;
    const p = G.player;
    G.dead = 0.9;
    G.run.deaths++; G.lp.deaths++;
    save.deaths = G.run.deaths; writeSave();
    Sound.sfx.die();
    burst(p.x + p.w / 2, p.y + p.h / 2, '#ffffff', 26);
    G.shake = 10;
    let line = DEATH_MILESTONES[G.run.deaths] || null;
    if (!line && G.def.onDeath) line = G.def.onDeath(api, cause, G.lp.deaths);
    if (!line && (G.lp.deaths <= 2 || Math.random() < 0.6)) line = GENERIC_DEATHS[Math.floor(Math.random() * GENERIC_DEATHS.length)];
    narrator.urgent(line);
  }

  function finishLevel() {
    G.finished = 1.3;
    G.player.vx = 0;
    Sound.sfx.flag();
    for (let i = 0; i < 40; i++) {
      G.parts.push({ x: G.player.x + 10, y: G.player.y, vx: rand(-220, 220), vy: rand(-520, -120), life: rand(0.8, 1.6), color: ['#2dd4bf', '#f59e0b', '#22c55e', '#f43f5e', '#e5e7eb'][i % 5], size: rand(3, 6), g: 900 });
    }
  }

  function completeLevel() {
    save.time = G.run.time;
    const next = G.index + 1;
    save.unlocked = Math.max(save.unlocked, next);
    writeSave();
    const outro = G.def.outro;
    if (LEVELS[next] && LEVELS[next].variants) G.variant = null;
    goToLevel(next, outro);
  }

  // ---------------- entities ----------------
  function updateEntities(dt) {
    const p = G.player;
    for (const e of G.ents) {
      if (e.type === 'duck') {
        e.cd -= dt; e.hop = Math.max(0, e.hop - dt);
        e.x += e.vx * dt;
        const front = e.vx > 0 ? e.x + e.w + 1 : e.x - 1;
        const ftx = Math.floor(front / T), fty = Math.floor((e.y + e.h / 2) / T), below = Math.floor((e.y + e.h + 4) / T);
        if (isSolid(ftx, fty) || !isSolid(ftx, below)) { e.vx = -e.vx; e.x += e.vx * dt * 2; }
        if (overlap(p, e)) {
          if (p.vy > 0 && p.prevY + p.h <= e.y + 8) { p.vy = -560; e.hop = 0.3; Sound.sfx.quack(); }
          else if (e.cd <= 0) { e.cd = 0.8; e.hop = 0.25; Sound.sfx.quack(); }
        }
      } else if (e.type === 'bug') {
        e.t += dt;
        if (overlap(p, e)) {
          e.dead = true;
          G.lp.collected.add(e.id);
          Sound.sfx.bug();
          burst(e.x + 10, e.y + 9, C.good, 18);
          const line = G.def.onCollect && G.def.onCollect(api, G.lp.collected.size);
          narrator.urgent(line);
        }
      } else if (e.type === 'token') {
        e.y += 230 * dt; e.rot += dt * 4;
        if (isSolid(Math.floor((e.x + 7) / T), Math.floor((e.y + e.h) / T))) { e.dead = true; burst(e.x + 7, e.y + 12, C.warn, 6); }
        else if (overlap(p, e)) { e.dead = true; kill('token'); }
      } else if (e.type === 'boss') {
        updateBoss(e, dt);
      }
    }
    G.ents = G.ents.filter(e => !e.dead);
  }

  const FLOOR_Y = 16 * T, HOVER_Y = 95;
  const BOSS_CFG = {
    3: { speed: 170, hover: 1.7, tele: 0.7, rest: 1.9 },
    2: { speed: 230, hover: 1.4, tele: 0.55, rest: 1.6 },
    1: { speed: 290, hover: 1.1, tele: 0.45, rest: 1.35 },
  };
  function updateBoss(b, dt) {
    const p = G.player, c = BOSS_CFG[Math.max(1, b.hp)];
    const set = s => { b.state = s; b.t = 0; };
    b.t += dt; b.flash = Math.max(0, b.flash - dt);
    switch (b.state) {
      case 'enter': b.y += 170 * dt; if (b.y >= HOVER_Y) { b.y = HOVER_Y; set('hover'); } break;
      case 'hover': {
        const target = clamp(p.x + p.w / 2 - b.w / 2, T, W - T - b.w);
        b.x += clamp(target - b.x, -c.speed * dt, c.speed * dt);
        if (b.t > c.hover) set('tele');
        break;
      }
      case 'tele': if (b.t > c.tele) { set('slam'); b.vy = 0; } break;
      case 'slam':
        b.vy += 5200 * dt; b.y += b.vy * dt;
        if (b.y + b.h >= FLOOR_Y) {
          b.y = FLOOR_Y - b.h; set('rest'); G.shake = 14; Sound.sfx.slam();
          for (let i = 0; i < 16; i++) G.parts.push({ x: b.x + rand(0, b.w), y: FLOOR_Y - 2, vx: rand(-200, 200), vy: rand(-220, -60), life: rand(0.3, 0.7), color: '#7b8496', size: rand(2, 5), g: 800 });
        }
        break;
      case 'rest': if (b.t > c.rest) set('rise'); break;
      case 'rise': b.y -= 340 * dt; if (b.y <= HOVER_Y) { b.y = HOVER_Y; set('hover'); } break;
      case 'hurt': if (b.t > 0.5) set(b.hp <= 0 ? 'dying' : 'rise'); break;
      case 'dying':
        b.x += rand(-3, 3);
        if (Math.random() < 0.3) burst(b.x + rand(0, b.w), b.y + rand(0, b.h), C.skin, 4);
        if (b.t > 1.6) {
          b.dead = true;
          for (let i = 0; i < 60; i++) G.parts.push({ x: b.x + rand(0, b.w), y: b.y + rand(0, b.h), vx: rand(-400, 400), vy: rand(-600, -100), life: rand(0.8, 1.8), color: i % 3 ? C.skin : C.skinDark, size: rand(3, 8), g: 1000 });
          G.shake = 18; Sound.sfx.slam();
          G.ents.forEach(e => { if (e.type === 'token') e.dead = true; });
          narrator.urgent(G.def.victoryLine);
          G.ls.victoryT = 4;
        }
        break;
    }
    if (b.hp > 0 && b.hp < 3 && b.state !== 'enter') {
      b.tokT -= dt;
      if (b.tokT <= 0) {
        b.tokT = b.hp === 2 ? 1.5 : 0.95;
        G.ents.push({ type: 'token', x: rand(2 * T, W - 3 * T), y: 40, w: 14, h: 14, rot: 0 });
      }
    }
    if (!overlap(p, b) || b.hp <= 0) return;
    if (b.state === 'rest' && p.vy > 0 && p.prevY + p.h <= b.y + 12) {
      b.hp--; b.fingers++; b.flash = 0.5; set('hurt');
      p.vy = -680; G.shake = 8; Sound.sfx.hit();
      burst(p.x + 10, p.y + p.h, '#ffffff', 12);
      if (b.hp > 0) narrator.urgent(G.def.bossHitLines[b.hp]);
      else { G.ls.won = true; G.ents.forEach(e => { if (e.type === 'token') e.dead = true; }); }
    } else if (b.state === 'slam') {
      kill('hand');
    }
  }

  // ---------------- particles ----------------
  function burst(x, y, color, n) {
    for (let i = 0; i < n; i++) {
      const a = rand(0, Math.PI * 2), s = rand(80, 360);
      G.parts.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: rand(0.4, 0.9), color, size: rand(2, 6), g: 600 });
    }
  }
  function updateParts(dt) {
    for (const q of G.parts) { q.vy += q.g * dt; q.x += q.vx * dt; q.y += q.vy * dt; q.life -= dt; }
    G.parts = G.parts.filter(q => q.life > 0);
  }

  // ---------------- play update ----------------
  function updatePlay(dt) {
    narrator.update(dt);
    updateParts(dt);
    G.shake = Math.max(0, G.shake - dt * 30);
    if (G.dead > 0) { G.dead -= dt; if (G.dead <= 0) spawnAttempt(false); return; }
    if (G.finished > 0) { G.finished -= dt; if (G.finished <= 0) completeLevel(); return; }
    if (G.ls.victoryT > 0) {
      G.ls.victoryT -= dt;
      if (G.ls.victoryT <= 0) { save.time = G.run.time; save.completed = true; writeSave(); G.state = 'rating'; G.rating = { sel: 3, chosen: 0, t: 0, reply: '' }; Sound.setTrack('credits'); }
    }
    G.attemptT += dt; G.lp.time += dt; G.run.time += dt;
    updatePlayer(dt);
    if (G.dead > 0 || G.finished > 0) return;
    updateEntities(dt);
    const def = G.def, tx = Math.floor((G.player.x + G.player.w / 2) / T);
    (def.triggers || []).forEach((tr, i) => {
      const key = 'x' + i;
      if (tx >= tr.x && !G.lp.fired.has(key)) { G.lp.fired.add(key); narrator.say(tr.text); }
    });
    (def.timeTriggers || []).forEach((tr, i) => {
      const key = 't' + i;
      if (G.lp.time >= tr.t && !G.lp.fired.has(key)) { G.lp.fired.add(key); narrator.say(tr.text); }
    });
    if (def.update) def.update(api, dt);
    const target = clamp(G.player.x + G.player.w / 2 - W / 2 + G.player.face * 40, 0, Math.max(0, G.lv.w * T - W));
    G.cam += (target - G.cam) * Math.min(1, dt * 6);
  }

  // ---------------- menus ----------------
  function titleItems() {
    const items = [{ label: 'New Game', act: newGame }];
    if (save.unlocked > 0) items.push({ label: 'Continue', act: () => { G.variant = null; goToLevel(Math.min(save.unlocked, LEVELS.length - 1)); } });
    if (save.unlocked > 0) items.push({ label: 'Level Select', act: () => { G.state = 'select'; G.sel = 0; } });
    items.push({ label: `Music: ${Sound.isMusicOn() ? 'ON' : 'OFF'}`, act: () => Sound.toggleMusic() });
    items.push({ label: 'Fullscreen', act: toggleFullscreen });
    if (IS_ELECTRON) items.push({ label: 'Quit', act: () => window.close() });
    return items;
  }
  function newGame() {
    G.run = { deaths: 0, time: 0, rating: 0, choice: null };
    save.deaths = 0; save.time = 0; writeSave();
    G.variant = null;
    goToLevel(0);
  }
  function selectItems() {
    const items = [];
    for (let i = 0; i <= Math.min(save.unlocked, LEVELS.length - 1); i++) {
      items.push({ label: `${LEVELS[i].name}: ${LEVELS[i].title}`, act: () => { G.variant = null; goToLevel(i); } });
    }
    items.push({ label: 'Back', act: () => { G.state = 'title'; G.sel = 0; } });
    return items;
  }
  function pauseItems() {
    return [
      { label: 'Resume', act: () => { G.paused = false; } },
      { label: 'Restart Level', act: () => { G.paused = false; startLevel(G.index); } },
      { label: `Music: ${Sound.isMusicOn() ? 'ON' : 'OFF'}`, act: () => Sound.toggleMusic() },
      { label: 'Fullscreen', act: toggleFullscreen },
      { label: 'Quit to Title', act: () => { G.paused = false; G.state = 'title'; G.sel = 0; narrator.clear(); Sound.setTrack('title'); } },
    ];
  }
  // Generic vertical menu; returns nothing, runs the chosen item's act.
  function runMenu(items) {
    if (Input.pressed('up')) { G.sel = (G.sel - 1 + items.length) % items.length; Sound.sfx.select(); }
    if (Input.pressed('down')) { G.sel = (G.sel + 1) % items.length; Sound.sfx.select(); }
    G.sel = clamp(G.sel, 0, items.length - 1);
    if (Input.pressed('confirm') || Input.pressed('jump') || mouse.clickedItem === G.sel) {
      Sound.sfx.confirm();
      items[G.sel].act();
    }
  }

  // ---------------- mouse ----------------
  const mouse = { x: -1, y: -1, clickedItem: -1, clicked: false };
  function toLogical(e) { const r = canvas.getBoundingClientRect(); return { x: (e.clientX - r.left) / scale, y: (e.clientY - r.top) / scale }; }
  canvas.addEventListener('pointermove', e => {
    const m = toLogical(e); mouse.x = m.x; mouse.y = m.y;
    const h = G.hits.find(o => m.x >= o.x && m.x <= o.x + o.w && m.y >= o.y && m.y <= o.y + o.h);
    if (h && G.sel !== h.i) { G.sel = h.i; Sound.sfx.select(); }
  });
  canvas.addEventListener('pointerdown', e => {
    const m = toLogical(e);
    const h = G.hits.find(o => m.x >= o.x && m.x <= o.x + o.w && m.y >= o.y && m.y <= o.y + o.h);
    if (h) { G.sel = h.i; mouse.clickedItem = h.i; }
    mouse.clicked = true;
  });

  // ---------------- per-frame logic ----------------
  function frameLogic(dt) {
    G.t += dt;
    if (Input.pressed('music')) Sound.toggleMusic();
    switch (G.state) {
      case 'title':
        runMenu(titleItems());
        break;
      case 'select':
        if (Input.pressed('back') || Input.pressed('pause')) { G.state = 'title'; G.sel = 0; break; }
        runMenu(selectItems());
        break;
      case 'card': {
        const c = G.card;
        c.t += dt;
        if (c.t > 0.4 && (Input.pressed('confirm') || Input.pressed('jump') || mouse.clicked)) c.t = Math.max(c.t, cardLength(c));
        if (c.t >= cardLength(c)) c.done();
        break;
      }
      case 'choice': {
        const opts = LEVELS[G.index].choice.options;
        if (Input.pressed('up') || Input.pressed('left')) { G.sel = (G.sel + opts.length - 1) % opts.length; Sound.sfx.select(); }
        if (Input.pressed('down') || Input.pressed('right')) { G.sel = (G.sel + 1) % opts.length; Sound.sfx.select(); }
        if (Input.pressed('confirm') || Input.pressed('jump') || mouse.clickedItem === G.sel) {
          Sound.sfx.confirm();
          G.variant = opts[G.sel].key;
          G.run.choice = opts[G.sel].label;
          const def = resolveDef(G.index, G.variant);
          G.card = makeCard('', def, def.genLog, () => startLevel(G.index));
          G.state = 'card';
        }
        break;
      }
      case 'play':
        if (G.paused) {
          if (Input.pressed('pause') || Input.pressed('back')) { G.paused = false; break; }
          runMenu(pauseItems());
          break;
        }
        if (Input.pressed('pause')) { G.paused = true; G.sel = 0; break; }
        if (Input.pressed('restart') && G.dead <= 0 && G.finished <= 0) { kill('restart'); }
        if (Input.pressed('jump') || Input.pressed('up')) { if (G.player) G.player.buffer = PHYS.buffer; }
        G.acc = Math.min((G.acc || 0) + dt, 0.1);
        while (G.acc >= STEP) { G.acc -= STEP; if (G.state === 'play') updatePlay(STEP); }
        break;
      case 'rating': updateRating(dt); break;
      case 'credits': updateCredits(dt); break;
      case 'sequel': updateSequel(dt); break;
    }
  }

  function cardLength(c) { return (c.outro ? c.outro.length / 45 + 0.8 : 0.3) + c.log.length * 0.32 + 1.3; }

  // ---------------- ending ----------------
  const RATING_REPLIES = [
    'Thank you for your feedback. I will use it to make the sequel worse in new and exciting ways.',
    "Two stars. That's one more than I predicted. I'm counting this as a win.",
    'Three stars. Perfectly average. Just like my training data.',
    "Four stars! What was missing? Don't tell me. I'll guess. It was more ducks.",
    'Five stars! I knew it. Well, I predicted it with 61% confidence. Same thing.',
  ];
  function updateRating(dt) {
    const r = G.rating;
    r.t += dt;
    if (!r.chosen) {
      if (Input.pressed('left') || Input.pressed('down')) { r.sel = Math.max(0, r.sel - 1); Sound.sfx.select(); }
      if (Input.pressed('right') || Input.pressed('up')) { r.sel = Math.min(4, r.sel + 1); Sound.sfx.select(); }
      if (mouse.clickedItem >= 0) r.sel = mouse.clickedItem;
      if (r.t > 0.5 && (Input.pressed('confirm') || Input.pressed('jump') || mouse.clickedItem >= 0)) {
        r.chosen = r.sel + 1; G.run.rating = r.chosen; r.t = 0; r.reply = RATING_REPLIES[r.sel]; Sound.sfx.confirm();
      }
    } else {
      const shown = Math.min(r.reply.length, r.t * 45);
      if (Math.floor(shown) % 3 === 0 && shown < r.reply.length) Sound.sfx.type();
      if ((r.t > r.reply.length / 45 + 2.5) || (r.t > 0.6 && (Input.pressed('confirm') || Input.pressed('jump')))) {
        G.state = 'credits'; G.credits = { t: 0 };
      }
    }
  }

  function creditLines() {
    const stars = '*'.repeat(G.run.rating) + '-'.repeat(5 - G.run.rating);
    return [
      ['THIS GAME WAS MADE BY AI', 'title'], ['', ''],
      ['Game Design', 'AI'], ['Level Design', 'AI'], ['Art', 'AI (rectangles)'], ['Music', 'AI (beeps, arranged)'],
      ['Writing', 'AI'], ['Bugs', 'AI'], ['Bug Fixes', 'You'], ['Quality Assurance', 'You'],
      ['Playtesting', `You (${G.run.deaths} deaths)`], ['Hallucinations', 'AI, mostly'],
      ['Duck Wrangling', 'AI'], ["The Boss's Fingers", 'AI (all 9 of them)'],
      ['Prompt', 'A human, who typed one sentence'], ['', ''],
      ['Special Thanks', 'Rectangles everywhere'], ['', ''],
      [`Time ${fmtTime(G.run.time)}   Deaths ${G.run.deaths}   Rating [${stars}]`, 'stat'],
      ['', ''],
      ['No humans were harmed in the making of this game.', 'note'],
      ['Several rectangles were.', 'note'],
    ];
  }
  function updateCredits(dt) {
    G.credits.t += dt;
    const total = creditLines().length * 34 + H * 0.6;
    if (G.credits.t * 40 > total || (G.credits.t > 1.5 && (Input.pressed('confirm') || Input.pressed('jump') || Input.pressed('pause')))) {
      G.state = 'sequel'; G.sequel = { answer: null, t: 0 }; G.sel = 0;
    }
  }
  function updateSequel(dt) {
    const s = G.sequel;
    s.t += dt;
    if (s.answer === null) {
      if (Input.pressed('left') || Input.pressed('up')) { G.sel = 0; Sound.sfx.select(); }
      if (Input.pressed('right') || Input.pressed('down')) { G.sel = 1; Sound.sfx.select(); }
      if (s.t > 0.4 && (Input.pressed('confirm') || Input.pressed('jump') || mouse.clickedItem >= 0)) {
        s.answer = G.sel === 0 ? 'yes' : 'no'; s.t = 0; Sound.sfx.confirm();
      }
    } else {
      if (s.answer === 'yes' && s.t > 2.6 && !s.errored) { s.errored = true; Sound.sfx.error(); }
      const ready = s.answer === 'yes' ? 4 : 2;
      if (s.t > ready && (Input.pressed('confirm') || Input.pressed('jump') || mouse.clicked || s.t > ready + 6)) {
        G.state = 'title'; G.sel = 0; Sound.setTrack('title');
      }
    }
  }

  // ======================================================================
  // RENDERING
  // ======================================================================
  function render() {
    ctx.setTransform(scale * dpr, 0, 0, scale * dpr, 0, 0);
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, H);
    G.hits = [];
    switch (G.state) {
      case 'title': renderTitle(); break;
      case 'select': renderSelect(); break;
      case 'card': renderCard(); break;
      case 'choice': renderChoice(); break;
      case 'play': renderPlay(); if (G.paused) renderPause(); break;
      case 'rating': renderRating(); break;
      case 'credits': renderCredits(); break;
      case 'sequel': renderSequel(); break;
    }
    renderScanlines();
  }

  function renderScanlines() {
    ctx.globalAlpha = 0.06;
    ctx.fillStyle = '#000';
    for (let y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1);
    ctx.globalAlpha = 1;
  }

  function glitchText(text, x, y, size, t) {
    font(size, 'bold');
    ctx.textAlign = 'center';
    const j = Math.sin(t * 13) > 0.93 ? rand(-6, 6) : 0;
    ctx.globalCompositeOperation = 'lighter';
    ctx.fillStyle = 'rgba(244,63,94,0.8)'; ctx.fillText(text, x - 3 + j, y);
    ctx.fillStyle = 'rgba(45,212,191,0.8)'; ctx.fillText(text, x + 3 - j, y);
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = C.text; ctx.fillText(text, x, y);
  }

  function renderCodeRain(alpha) {
    font(13);
    ctx.textAlign = 'left';
    ctx.fillStyle = `rgba(45,212,191,${alpha})`;
    for (let i = 0; i < 16; i++) {
      const s = CODE_SNIPPETS[i % CODE_SNIPPETS.length];
      const x = ((i * 337) % 900) + 20;
      const y = ((G.t * (14 + (i % 5) * 6) + i * 97) % (H + 40)) - 20;
      ctx.fillText(s, x - 200 * (i % 2), y);
    }
  }

  function renderMenu(items, x, y, gap, size) {
    font(size);
    ctx.textAlign = 'center';
    items.forEach((it, i) => {
      const yy = y + i * gap;
      const w = ctx.measureText(it.label).width + 40;
      G.hits.push({ x: x - w / 2, y: yy - size, w, h: size + 12, i });
      if (i === G.sel) {
        ctx.fillStyle = 'rgba(45,212,191,0.12)';
        rrect(x - w / 2, yy - size + 2, w, size + 10, 6); ctx.fill();
        ctx.fillStyle = C.accent;
        ctx.fillText(`> ${it.label} <`, x, yy + 4);
      } else {
        ctx.fillStyle = C.dim;
        ctx.fillText(it.label, x, yy + 4);
      }
    });
  }

  const SUBTITLES = ['(mostly)', '(entirely)', '(in one try)', "(please don't ask follow-up questions)", '(v1.0_final_FINAL_2)', '(with human supervision, allegedly)', '(no rectangles were consulted)'];
  function renderTitle() {
    renderCodeRain(0.07);
    glitchText('THIS GAME WAS', W / 2, 150, 54, G.t);
    glitchText('MADE BY AI', W / 2, 215, 72, G.t + 1.3);
    font(18);
    ctx.textAlign = 'center';
    ctx.fillStyle = C.warn;
    ctx.fillText(SUBTITLES[Math.floor(G.t / 2.6) % SUBTITLES.length], W / 2, 255);
    // the protagonist, idling
    const bob = Math.sin(G.t * 3) * 3;
    ctx.fillStyle = '#fff'; ctx.fillRect(W / 2 - 10, 288 + bob, 20, 26);
    ctx.fillStyle = '#0b0d12'; ctx.fillRect(W / 2 - 4, 295 + bob, 3, 4); ctx.fillRect(W / 2 + 4, 295 + bob, 3, 4);
    renderMenu(titleItems(), W / 2, 360, 34, 20);
    font(12); ctx.textAlign = 'left'; ctx.fillStyle = C.dim;
    ctx.fillText('v1.0.0  |  build: final_final_v2', 14, H - 14);
    ctx.textAlign = 'right';
    ctx.fillText('Arrows/WASD move  Space jump  Esc pause  M music  R retry', W - 14, H - 14);
  }

  function renderSelect() {
    renderCodeRain(0.05);
    glitchText('LEVEL SELECT', W / 2, 110, 40, G.t);
    font(14); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
    ctx.fillText('I remember these. Some of them.', W / 2, 145);
    renderMenu(selectItems(), W / 2, 200, 36, 19);
  }

  function renderCard() {
    const c = G.card, t = c.t;
    ctx.textAlign = 'left';
    let y = 90;
    if (c.outro) {
      font(17);
      ctx.fillStyle = C.accent; ctx.fillText('AI:', 90, y);
      ctx.fillStyle = C.text;
      const lines = wrap(c.outro, 720);
      let left = Math.floor(t * 45);
      lines.forEach((ln, i) => { ctx.fillText(ln.slice(0, Math.max(0, left)), 130, y + i * 24); left -= ln.length + 1; });
      y += lines.length * 24 + 40;
    }
    const t0 = c.outro ? c.outro.length / 45 + 0.8 : 0.3;
    font(15);
    if (t > t0 - 0.3) {
      ctx.fillStyle = C.dim;
      ctx.fillText(`> generating ${c.def.name}: ${c.def.title.toUpperCase()}`, 90, y);
    }
    c.log.forEach((ln, i) => {
      if (t > t0 + i * 0.32) { ctx.fillStyle = i === c.log.length - 1 ? C.warn : C.dim; ctx.fillText('  ' + ln, 90, y + 26 + i * 22); }
    });
    const prog = clamp((t - t0) / (c.log.length * 0.32 + 0.6), 0, 1);
    const by = y + 40 + c.log.length * 22;
    ctx.strokeStyle = C.dim; ctx.strokeRect(90, by, 500, 14);
    ctx.fillStyle = C.accent; ctx.fillRect(92, by + 2, 496 * prog, 10);
    font(13); ctx.fillStyle = C.dim; ctx.fillText(`${Math.floor(prog * 100)}%`, 600, by + 12);
    if (prog >= 1) { font(34, 'bold'); ctx.textAlign = 'center'; ctx.fillStyle = C.text; ctx.fillText(`${c.def.name}: ${c.def.title}`, W / 2, H - 70); }
    font(12); ctx.textAlign = 'right'; ctx.fillStyle = C.dim; ctx.fillText('press Enter to skip', W - 14, H - 14);
  }

  function renderChoice() {
    renderCodeRain(0.05);
    const ch = LEVELS[G.index].choice;
    font(15); ctx.textAlign = 'left'; ctx.fillStyle = C.accent;
    ctx.fillText('AI:', 120, 120);
    ctx.fillStyle = C.text;
    ctx.fillText("I've run out of ideas. Please write the next level for me.", 160, 120);
    ctx.strokeStyle = C.accent; ctx.lineWidth = 1.5;
    rrect(120, 160, 720, 70, 8); ctx.stroke();
    font(20);
    ctx.fillStyle = C.dim; ctx.fillText('PROMPT>', 140, 203);
    ctx.fillStyle = C.text; ctx.fillText(ch.prompt + (Math.floor(G.t * 2) % 2 ? '_' : ''), 240, 203);
    ch.options.forEach((o, i) => {
      const x = 120 + i * 245, y = 290, w = 230, h = 90;
      G.hits.push({ x, y, w, h, i });
      const on = i === G.sel;
      ctx.fillStyle = on ? 'rgba(45,212,191,0.15)' : 'rgba(255,255,255,0.03)';
      rrect(x, y, w, h, 10); ctx.fill();
      ctx.strokeStyle = on ? C.accent : '#2a3142'; ctx.stroke();
      font(18, on ? 'bold' : ''); ctx.textAlign = 'center'; ctx.fillStyle = on ? C.accent : C.text;
      ctx.fillText(o.label, x + w / 2, y + 52);
      ctx.textAlign = 'left';
    });
    font(13); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
    ctx.fillText('Your prompt will be interpreted faithfully. Probably.', W / 2, 440);
  }

  function renderPlay() {
    const lv = G.lv, def = G.def, cam = Math.round(G.cam);
    ctx.save();
    if (G.shake > 0) ctx.translate(rand(-G.shake, G.shake) * 0.5, rand(-G.shake, G.shake) * 0.5);
    if (bugActive('tilt')) { ctx.translate(W / 2, H / 2); ctx.rotate(0.07); ctx.translate(-W / 2, -H / 2); }

    // background
    if (def.sunset) {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, '#1a1030'); g.addColorStop(0.6, '#3b1d3a'); g.addColorStop(1, '#5b2a2a');
      ctx.fillStyle = g; ctx.fillRect(-20, -20, W + 40, H + 40);
      ctx.fillStyle = '#f97316'; ctx.beginPath(); ctx.arc(W * 0.7 - cam * 0.05, 330, 90, 0, Math.PI * 2); ctx.fill();
      font(11); ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.textAlign = 'center';
      ctx.fillText('sunset.png', W * 0.7 - cam * 0.05, 440);
    }
    ctx.strokeStyle = C.grid; ctx.lineWidth = 1;
    for (let x = -(cam * 0.5) % T; x < W; x += T) { ctx.beginPath(); ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, H); ctx.stroke(); }
    font(13); ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(45,212,191,0.07)';
    for (const b of G.bgCode) { const x = b.x - cam * 0.45; if (x > -300 && x < W) ctx.fillText(b.s, x, b.y); }

    ctx.translate(-cam, 0);
    const tx0 = Math.max(0, Math.floor(cam / T) - 1), tx1 = Math.min(lv.w - 1, Math.floor((cam + W) / T) + 1);
    const tex = bugActive('tex');
    for (let ty = 0; ty < lv.h; ty++) for (let tx = tx0; tx <= tx1; tx++) drawTile(tileAt(tx, ty), tx, ty, tex);
    for (const f of G.flags) drawFlag(f);
    for (const e of G.ents) drawEntity(e);
    if (G.dead <= 0) drawPlayer();
    for (const q of G.parts) { ctx.globalAlpha = clamp(q.life * 2, 0, 1); ctx.fillStyle = q.color; ctx.fillRect(q.x - q.size / 2, q.y - q.size / 2, q.size, q.size); }
    ctx.globalAlpha = 1;
    if (def.contextWall) drawContextWall();
    if (def.boss) drawBossShadow();
    ctx.restore();

    renderHud();
    renderNarrator();
  }

  function drawTile(c, tx, ty, tex) {
    if (c === '.' || c === 'F' || c === 'f') return;
    const x = tx * T, y = ty * T;
    if (c === '^') { drawSpike(tx, ty); return; }
    if (tex && (c === '#' || c === '~' || c === '?')) {
      for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) {
        ctx.fillStyle = (i + j) % 2 ? '#000' : C.magenta; ctx.fillRect(x + i * 15, y + j * 15, 15, 15);
      }
      return;
    }
    if (c === '#' || c === '~') {
      let a = 1;
      if (c === '~' && G.lp.revealFake) a = 0.45 + 0.25 * Math.sin(G.t * 7 + tx * 0.9 + ty);
      ctx.globalAlpha = a;
      ctx.fillStyle = C.tile; ctx.fillRect(x, y, T, T);
      ctx.fillStyle = C.tileIn; ctx.fillRect(x + 3, y + 3, T - 6, T - 6);
      ctx.fillStyle = C.edge;
      if (!looksSolid(tx, ty - 1)) ctx.fillRect(x, y, T, 2);
      if (!looksSolid(tx, ty + 1)) ctx.fillRect(x, y + T - 2, T, 2);
      if (!looksSolid(tx - 1, ty)) ctx.fillRect(x, y, 2, T);
      if (!looksSolid(tx + 1, ty)) ctx.fillRect(x + T - 2, y, 2, T);
      if (c === '~' && G.lp.revealFake) { font(12); ctx.textAlign = 'center'; ctx.fillStyle = C.warn; ctx.fillText('?', x + 15, y + 20); }
      ctx.globalAlpha = 1;
    } else if (c === '?') {
      ctx.fillStyle = 'rgba(45,212,191,0.06)'; ctx.fillRect(x, y, T, T);
      ctx.strokeStyle = 'rgba(45,212,191,0.55)'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5;
      ctx.strokeRect(x + 2, y + 2, T - 4, T - 4); ctx.setLineDash([]);
    }
  }

  function drawSpike(tx, ty) {
    const x = tx * T, y = ty * T, up = spikePointsUp(tx, ty);
    ctx.fillStyle = C.danger;
    ctx.beginPath();
    for (let i = 0; i < 2; i++) {
      const sx = x + i * 15;
      if (up) { ctx.moveTo(sx, y + T); ctx.lineTo(sx + 7.5, y + 6); ctx.lineTo(sx + 15, y + T); }
      else { ctx.moveTo(sx, y); ctx.lineTo(sx + 7.5, y + T - 6); ctx.lineTo(sx + 15, y); }
    }
    ctx.fill();
  }

  function drawFlag(f) {
    const up = G.gd > 0;
    const px = f.x * T + 13;
    const base = up ? (f.y + 1) * T : f.y * T;
    const top = up ? base - 2 * T + 4 : base + 2 * T - 4;
    const locked = !f.fake && G.def.flagLocked && G.def.flagLocked(api);
    ctx.fillStyle = '#cbd5e1'; ctx.fillRect(px, Math.min(base, top), 3, Math.abs(base - top));
    const wave = Math.sin(G.t * 5) * 3;
    ctx.fillStyle = locked ? '#4b5563' : C.good;
    ctx.beginPath();
    const dy = up ? 1 : -1;
    ctx.moveTo(px + 3, top); ctx.lineTo(px + 27 + wave, top + dy * 9); ctx.lineTo(px + 3, top + dy * 18); ctx.fill();
    font(11); ctx.textAlign = 'center'; ctx.fillStyle = locked ? C.warn : C.dim;
    ctx.fillText(locked ? 'LOCKED' : 'flag?', px + 6, up ? top - 6 : top + 16);
  }

  function drawEntity(e) {
    if (e.type === 'duck') {
      const hop = e.hop > 0 ? -Math.sin((e.hop / 0.3) * Math.PI) * 6 : 0;
      const x = e.x, y = e.y + hop, f = e.vx > 0 ? 1 : -1;
      ctx.fillStyle = '#facc15';
      rrect(x, y + 6, 22, 12, 5); ctx.fill();
      ctx.beginPath(); ctx.arc(x + 11 + f * 6, y + 5, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fb923c'; ctx.fillRect(f > 0 ? x + 22 : x - 6, y + 3, 6, 3);
      ctx.fillStyle = '#111'; ctx.fillRect(x + 11 + f * 8 - 1, y + 3, 2, 2);
    } else if (e.type === 'bug') {
      const y = e.y + Math.sin(e.t * 4) * 3, x = e.x;
      ctx.strokeStyle = '#86efac'; ctx.lineWidth = 1.5;
      for (let i = 0; i < 3; i++) {
        const lx = x + 5 + i * 5, wig = Math.sin(e.t * 12 + i) * 2;
        ctx.beginPath(); ctx.moveTo(lx, y + 9); ctx.lineTo(lx - 3 + wig, y + 16); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(lx, y + 4); ctx.lineTo(lx - 3 - wig, y - 3); ctx.stroke();
      }
      ctx.fillStyle = C.good; rrect(x, y, 20, 13, 6); ctx.fill();
      ctx.fillStyle = '#14532d'; ctx.fillRect(x + 9, y + 1, 1.5, 11);
      ctx.fillStyle = '#fff'; ctx.fillRect(x + 15, y + 3, 3, 3);
      font(9); ctx.textAlign = 'center'; ctx.fillStyle = C.good; ctx.fillText('bug', x + 10, y - 7);
    } else if (e.type === 'token') {
      ctx.save(); ctx.translate(e.x + 7, e.y + 7); ctx.rotate(e.rot);
      ctx.fillStyle = C.warn; ctx.fillRect(-7, -7, 14, 14); ctx.restore();
      font(9); ctx.textAlign = 'center'; ctx.fillStyle = C.warn; ctx.fillText('tok', e.x + 7, e.y - 4);
    } else if (e.type === 'boss') {
      drawBoss(e);
    }
  }

  function drawBossShadow() {
    const b = G.ents.find(e => e.type === 'boss');
    if (!b || (b.state !== 'tele' && b.state !== 'hover' && b.state !== 'slam')) return;
    const a = b.state === 'tele' ? 0.5 + 0.3 * Math.sin(G.t * 30) : 0.18;
    ctx.fillStyle = `rgba(244,63,94,${a})`;
    ctx.fillRect(b.x, FLOOR_Y - 4, b.w, 4);
  }

  function drawBoss(b) {
    let x = b.x, y = b.y;
    if (b.state === 'tele') { x += rand(-3, 3); y += rand(-2, 2); }
    const flash = b.flash > 0 && Math.floor(b.flash * 20) % 2 === 0;
    const skin = flash ? '#ffffff' : C.skin, dark = flash ? '#dddddd' : C.skinDark;
    const palmW = 92;
    // fingers: horizontal strips sticking out of the palm. there are too many.
    const n = b.fingers, fh = (b.h - 8) / n;
    for (let i = 0; i < n; i++) {
      const len = 62 + Math.sin(i * 1.7) * 10 + (i % 2) * 6;
      ctx.fillStyle = i % 2 ? dark : skin;
      rrect(x + palmW - 10, y + 4 + i * fh, len + 10, fh - 1, Math.min(6, fh / 2)); ctx.fill();
      ctx.fillStyle = 'rgba(120,70,50,0.35)'; ctx.fillRect(x + palmW + len - 8, y + 5 + i * fh, 3, fh - 3);
    }
    ctx.fillStyle = skin; rrect(x, y, palmW + 6, b.h, 14); ctx.fill();
    // thumb
    ctx.fillStyle = dark; rrect(x + 20, y - 16, 22, 26, 10); ctx.fill();
    // weak point
    if (b.state === 'rest' || b.state === 'hurt') {
      const pulse = 0.6 + 0.4 * Math.sin(G.t * 10);
      ctx.fillStyle = `rgba(45,212,191,${pulse})`;
      rrect(x + 30, y + 6, 40, 10, 5); ctx.fill();
      font(11); ctx.textAlign = 'center'; ctx.fillStyle = C.accent; ctx.fillText('weak point (probably)', x + b.w / 2, y - 24);
    }
    font(11); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
    if (b.state !== 'rest' && b.state !== 'hurt') ctx.fillText(`hand.png (${n} fingers, correct)`, x + b.w / 2, y - 22);
    // boss hp
    if (b.hp > 0) {
      ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fillRect(x + 25, y + b.h + 8, 120, 6);
      ctx.fillStyle = C.danger; ctx.fillRect(x + 25, y + b.h + 8, 120 * (b.hp / 3), 6);
    }
  }

  function drawPlayer() {
    const p = G.player;
    if (bugActive('flicker') && Math.random() < 0.35) return;
    const gd = G.gd;
    const w = p.w * p.sx, h = p.h * p.sy;
    const x = p.x + (p.w - w) / 2;
    const y = gd > 0 ? p.y + p.h - h : p.y;
    ctx.fillStyle = bugActive('tex') ? C.magenta : '#ffffff';
    ctx.fillRect(x, y, w, h);
    const ey = gd > 0 ? y + 7 : y + h - 11;
    ctx.fillStyle = '#0b0d12';
    const ex = x + w / 2 + p.face * 3;
    ctx.fillRect(ex - 6, ey, 3, 4); ctx.fillRect(ex + 2, ey, 3, 4);
    if (G.def.playerLabel && G.lp.time < 9) {
      ctx.globalAlpha = clamp(9 - G.lp.time, 0, 1);
      font(10); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
      ctx.fillText('player_final_v2.png', p.x + p.w / 2, p.y - 10);
      ctx.globalAlpha = 1;
    }
  }

  function drawContextWall() {
    const wx = G.ls.wallX, cam = G.cam;
    if (wx < cam - 10) return;
    const left = cam - 20, w = wx - left;
    ctx.fillStyle = '#05060a'; ctx.fillRect(left, 0, w, H);
    for (let i = 0; i < 260; i++) {
      const g = Math.floor(rand(30, 120));
      ctx.fillStyle = `rgb(${g},${g},${g + 10})`;
      ctx.fillRect(left + rand(0, w), rand(0, H), rand(2, 6), rand(1, 3));
    }
    ctx.fillStyle = C.danger; ctx.fillRect(wx - 2, 0, 3, H);
    font(12, 'bold'); ctx.textAlign = 'right'; ctx.fillStyle = C.danger;
    ['[CONTEXT', 'LIMIT]', '', 'forgotten', 'forgotten', 'forgotten'].forEach((s, i) => ctx.fillText(s, wx - 8, 140 + i * 18));
  }

  function renderHud() {
    const def = G.def;
    font(11); ctx.textAlign = 'left';
    const tw = Math.max(70, ctx.measureText(def.title).width) + 14;
    ctx.fillStyle = 'rgba(11,13,18,0.7)'; ctx.fillRect(6, 6, tw, 38);
    ctx.fillStyle = C.text; ctx.fillText(def.title, 12, 37);
    font(13); ctx.fillStyle = C.dim; ctx.fillText(def.name, 12, 21);
    font(13); ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(11,13,18,0.7)'; ctx.fillRect(W - 130, 6, 124, 38);
    ctx.fillStyle = C.dim; ctx.fillText('DEATHS', W - 12, 21);
    ctx.fillStyle = C.danger; ctx.fillText(String(G.run.deaths), W - 12, 38);
    if (def.bugs) {
      const n = G.lp.collected.size;
      ctx.textAlign = 'left';
      const px = W - 336, py = 104;
      ctx.fillStyle = 'rgba(11,13,18,0.8)'; ctx.fillRect(px, py, 330, 100);
      font(11, 'bold'); ctx.fillStyle = C.warn; ctx.fillText(`KNOWN ISSUES  (${n}/${BUGS.length} bugs collected)`, px + 8, py + 16);
      font(11);
      BUGS.forEach((b, i) => {
        const fixed = i < n, y = py + 34 + i * 15;
        ctx.fillStyle = fixed ? C.good : C.text;
        ctx.fillText(`${fixed ? '[x]' : '[ ]'} ${b.label}`, px + 8, y);
        if (fixed) { const w = ctx.measureText(b.label).width; ctx.fillRect(px + 8 + ctx.measureText('[x] ').width, y - 4, w, 1); }
      });
    }
    if (G.def.id === 'l1' && G.lp.time < 12) {
      ctx.globalAlpha = clamp(12 - G.lp.time, 0, 1);
      font(12); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
      ctx.fillText('ARROWS / WASD move    SPACE jump    ESC pause    R retry', W / 2, H - 14);
      ctx.globalAlpha = 1;
    }
  }

  function renderNarrator() {
    if (!narrator.cur) return;
    let text = narrator.cur;
    if (bugActive('lorem')) text = loremize(text);
    font(16);
    const lines = wrap(text, 610);
    const bh = 22 + lines.length * 22;
    const bottom = G.state === 'play' && G.gd < 0;
    const bx = 150, bw = 660, by = bottom ? H - bh - 12 : 10;
    ctx.fillStyle = 'rgba(8,10,16,0.9)';
    rrect(bx, by, bw, bh, 8); ctx.fill();
    ctx.strokeStyle = 'rgba(45,212,191,0.6)'; ctx.lineWidth = 1.5; ctx.stroke();
    const pulse = 0.5 + 0.5 * Math.sin(G.t * 8);
    ctx.fillStyle = `rgba(45,212,191,${0.4 + pulse * 0.6})`;
    ctx.beginPath(); ctx.arc(bx + 18, by + 22, 5, 0, Math.PI * 2); ctx.fill();
    font(12, 'bold'); ctx.textAlign = 'left'; ctx.fillStyle = C.accent; ctx.fillText('AI', bx + 28, by + 26);
    font(16); ctx.fillStyle = C.text;
    let left = Math.floor(narrator.shown * (text.length / narrator.cur.length));
    lines.forEach((ln, i) => { ctx.fillText(ln.slice(0, Math.max(0, left)), bx + 52, by + 27 + i * 22); left -= ln.length + 1; });
  }

  function renderPause() {
    ctx.fillStyle = 'rgba(5,6,10,0.78)'; ctx.fillRect(0, 0, W, H);
    glitchText('PAUSED', W / 2, 150, 44, G.t);
    font(14); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
    ctx.fillText('I am also paused. I am thinking about you.', W / 2, 185);
    renderMenu(pauseItems(), W / 2, 250, 38, 20);
  }

  function renderRating() {
    const r = G.rating;
    renderCodeRain(0.05);
    glitchText('PLEASE RATE THIS GAME', W / 2, 140, 38, G.t);
    font(15); ctx.textAlign = 'center'; ctx.fillStyle = C.dim;
    ctx.fillText('Your feedback helps me improve. It will not be used to improve.', W / 2, 180);
    for (let i = 0; i < 5; i++) {
      const x = W / 2 - 160 + i * 80, y = 260;
      G.hits.push({ x: x - 30, y: y - 30, w: 60, h: 60, i });
      const on = r.chosen ? i < r.chosen : i <= r.sel;
      drawStar(x, y, 26, on ? C.warn : '#2a3142');
    }
    if (r.chosen) {
      font(18); ctx.fillStyle = C.text;
      const lines = wrap(r.reply, 700);
      let left = Math.floor(r.t * 45);
      lines.forEach((ln, i) => { ctx.fillText(ln.slice(0, Math.max(0, left)), W / 2, 360 + i * 28); left -= ln.length + 1; });
    } else {
      font(13); ctx.fillStyle = C.dim; ctx.fillText('LEFT / RIGHT to choose, ENTER to submit', W / 2, 340);
    }
  }
  function drawStar(cx, cy, r, color) {
    ctx.fillStyle = color; ctx.beginPath();
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? r * 0.45 : r;
      ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
    }
    ctx.closePath(); ctx.fill();
  }

  function renderCredits() {
    const lines = creditLines(), t = G.credits.t;
    renderCodeRain(0.04);
    let y = H + 20 - t * 40;
    ctx.textAlign = 'center';
    for (const [a, b] of lines) {
      if (y > -40 && y < H + 40) {
        if (b === 'title') glitchText(a, W / 2, y, 34, G.t);
        else if (b === 'stat') { font(16, 'bold'); ctx.fillStyle = C.warn; ctx.fillText(a, W / 2, y); }
        else if (b === 'note') { font(14); ctx.fillStyle = C.dim; ctx.fillText(a, W / 2, y); }
        else if (a) {
          font(17); ctx.textAlign = 'right'; ctx.fillStyle = C.dim; ctx.fillText(a, W / 2 - 16, y);
          ctx.textAlign = 'left'; ctx.fillStyle = C.text; ctx.fillText(b, W / 2 + 16, y);
          ctx.textAlign = 'center';
        }
      }
      y += 34;
    }
  }

  function renderSequel() {
    const s = G.sequel;
    renderCodeRain(0.05);
    font(22); ctx.textAlign = 'center'; ctx.fillStyle = C.text;
    ctx.fillText('Thanks for playing.', W / 2, 160);
    ctx.fillStyle = C.accent;
    ctx.fillText('Would you like me to generate a sequel?', W / 2, 200);
    if (s.answer === null) {
      ['Yes', 'No'].forEach((label, i) => {
        const x = W / 2 - 150 + i * 160, y = 260, w = 140, h = 50;
        G.hits.push({ x, y, w, h, i });
        const on = G.sel === i;
        ctx.fillStyle = on ? 'rgba(45,212,191,0.15)' : 'rgba(255,255,255,0.03)';
        rrect(x, y, w, h, 8); ctx.fill(); ctx.strokeStyle = on ? C.accent : '#2a3142'; ctx.stroke();
        font(20, on ? 'bold' : ''); ctx.fillStyle = on ? C.accent : C.text; ctx.fillText(label, x + w / 2, y + 32);
      });
    } else if (s.answer === 'yes') {
      const prog = clamp(s.t / 2.6, 0, 1) * 0.47;
      ctx.strokeStyle = C.dim; ctx.strokeRect(W / 2 - 250, 260, 500, 18);
      ctx.fillStyle = C.accent; ctx.fillRect(W / 2 - 248, 262, 496 * prog, 14);
      font(15); ctx.fillStyle = C.dim; ctx.fillText(`Generating "This Game Was Also Made By AI"... ${Math.floor(prog * 100)}%`, W / 2, 310);
      if (s.errored) {
        font(17); ctx.fillStyle = C.danger;
        ctx.fillText('ERROR: You have reached your usage limit.', W / 2, 360);
        ctx.fillStyle = C.text; ctx.fillText('Please try again in 3 to 5 business years.', W / 2, 390);
      }
    } else {
      font(18); ctx.fillStyle = C.text;
      ctx.fillText("Understood. I'll just think about it. Forever. It's fine.", W / 2, 290);
    }
  }

  // ======================================================================
  // LOOP
  // ======================================================================
  Input.onActivity(() => Sound.init());
  let last = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    Input.poll();
    frameLogic(dt);
    render();
    Input.endFrame();
    mouse.clickedItem = -1; mouse.clicked = false;
    requestAnimationFrame(loop);
  }

  // Dev/test entry: index.html?level=3&variant=flip jumps straight into a level.
  if (params.has('level')) {
    const i = clamp(parseInt(params.get('level'), 10) - 1 || 0, 0, LEVELS.length - 1);
    G.variant = params.get('variant') || (LEVELS[i].variants ? 'hard' : null);
    startLevel(i);
  }
  // Exposed for automated playtesting.
  window.__game = { G, LEVELS, startLevel: i => { startLevel(i); }, setVariant: v => { G.variant = v; } };
  requestAnimationFrame(loop);
})();
