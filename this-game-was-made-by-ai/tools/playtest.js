// Smoke test in a real browser: loads every level, fights the boss through
// to the ending, fails on any page error. Screenshots go to tools/shots/.
// Run: node tools/playtest.js   (needs the `playwright` package)
'use strict';
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const ROOT = 'file://' + path.join(__dirname, '..', 'index.html');
const OUT = path.join(__dirname, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const shot = name => page.screenshot({ path: path.join(OUT, name + '.png') });
  const state = () => page.evaluate(() => window.__game.G.state);

  // Title -> New Game -> generating card -> Level 1
  await page.goto(ROOT);
  await sleep(600);
  await shot('00-title');
  await page.keyboard.press('Enter');
  await sleep(1200);
  await shot('01-card');
  await page.keyboard.press('Enter');
  await sleep(300);
  if (await state() !== 'play') throw new Error('expected to be playing level 1, got ' + await state());
  await page.keyboard.down('ArrowRight');
  await sleep(1500);
  await page.keyboard.up('ArrowRight');
  await shot('02-level1');

  // Every level, straight in
  const levels = [['1'], ['2'], ['3', 'hard'], ['3', 'chill'], ['3', 'flip'], ['4'], ['5'], ['6']];
  for (const [n, v] of levels) {
    await page.goto(`${ROOT}?level=${n}${v ? '&variant=' + v : ''}`);
    await sleep(2200);
    await shot(`10-level${n}${v ? '-' + v : ''}`);
  }

  // Level 4: standing still must get you forgotten.
  await page.goto(`${ROOT}?level=4`);
  await sleep(6500);
  const deaths4 = await page.evaluate(() => window.__game.G.run.deaths);
  if (deaths4 < 1) throw new Error('context wall never caught an idle player');
  await shot('20-context-wall');

  // Level 5: collecting a bug fixes BUG-001 (swapped controls).
  await page.goto(`${ROOT}?level=5`);
  await sleep(300);
  await page.keyboard.down('ArrowLeft'); // swapped: left moves right, towards bug 1
  await sleep(900);
  await page.keyboard.up('ArrowLeft');
  const bugs = await page.evaluate(() => window.__game.G.lp.collected.size);
  if (bugs !== 1) throw new Error('expected to collect bug 1 with swapped controls, got ' + bugs);
  await shot('21-bug-collected');

  // Boss: drop the player onto the resting hand three times.
  await page.goto(`${ROOT}?level=6`);
  // The test player stands still, so tokens sometimes get it; that resets the
  // fight, which is correct gameplay. Keep trying until the boss is down.
  const bossHp = () => page.evaluate(() => { const b = window.__game.G.ents.find(e => e.type === 'boss'); return b ? b.hp : 0; });
  for (let tries = 0; tries < 12 && (await bossHp()) > 0; tries++) {
    await page.waitForFunction(() => {
      const b = window.__game.G.ents.find(e => e.type === 'boss');
      return b && b.state === 'tele';
    }, null, { timeout: 15000 });
    await page.evaluate(() => { // dodge: step out from under the hand
      const G = window.__game.G, b = G.ents.find(e => e.type === 'boss'), p = G.player;
      p.x = b.x > 400 ? 60 : 880; p.vx = 0;
    });
    await page.waitForFunction(() => {
      const b = window.__game.G.ents.find(e => e.type === 'boss');
      return b && b.state === 'rest';
    }, null, { timeout: 15000 });
    if (tries === 0) await shot('30-boss-resting');
    await page.evaluate(() => {
      const G = window.__game.G, b = G.ents.find(e => e.type === 'boss'), p = G.player;
      if (G.dead > 0) return;
      p.x = b.x + 40; p.y = b.y - p.h - 6; p.vy = 300;
    });
    await sleep(700);
    if ((await bossHp()) === 1) await shot('31-boss-phase3');
  }
  if ((await bossHp()) > 0) throw new Error('could not defeat the boss');
  await page.waitForFunction(() => window.__game.G.state === 'rating', null, { timeout: 10000 });
  await sleep(700);
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('Enter');
  await sleep(2500);
  await shot('40-rating');
  await page.keyboard.press('Enter');
  await sleep(4000);
  if (await state() !== 'credits') throw new Error('expected credits, got ' + await state());
  await shot('41-credits');
  await page.keyboard.press('Enter');
  await sleep(600);
  await page.keyboard.press('Enter'); // "Yes" to a sequel
  await sleep(3200);
  await shot('42-sequel');
  await sleep(1200);
  await page.keyboard.press('Enter');
  await sleep(400);
  if (await state() !== 'title') throw new Error('expected to return to title, got ' + await state());

  // Level 3 prompt screen
  await page.evaluate(() => {
    localStorage.setItem('tgwmbai.save.v1', JSON.stringify({ unlocked: 2 }));
  });
  await page.goto(ROOT);
  await sleep(300);
  await page.keyboard.press('ArrowDown'); // Continue
  await page.keyboard.press('Enter');
  await sleep(700);
  await page.keyboard.press('Enter'); // skip card
  await sleep(300);
  if (await state() !== 'choice') throw new Error('expected prompt screen, got ' + await state());
  await page.keyboard.press('ArrowRight');
  await sleep(300);
  await shot('50-prompt');

  await browser.close();
  if (errors.length) { console.error('PAGE ERRORS:\n' + errors.join('\n')); process.exit(1); }
  console.log('playtest passed; screenshots in tools/shots/');
})().catch(e => { console.error(e); process.exit(1); });
