// Renders the app icon and Steam store capsules in the game's own style.
// Run: node tools/make-art.js   ->  build/icon.png, steam/store-art/*.png
'use strict';
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
// [file, width, height, kind]
const ART = [
  ['build/icon.png', 512, 512, 'icon'],
  ['steam/store-art/header_capsule.png', 920, 430, 'capsule'],
  ['steam/store-art/small_capsule.png', 462, 174, 'capsule'],
  ['steam/store-art/main_capsule.png', 1232, 706, 'capsule'],
  ['steam/store-art/vertical_capsule.png', 748, 896, 'capsule'],
  ['steam/store-art/library_capsule.png', 600, 900, 'capsule'],
  ['steam/store-art/library_hero.png', 3840, 1240, 'hero'],
  ['steam/store-art/library_logo.png', 1280, 720, 'logo'],
];

function draw(w, h, kind) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  document.body.appendChild(c);
  const x = c.getContext('2d');
  const FONT = '"DejaVu Sans Mono", Consolas, monospace';
  const u = Math.min(w, h) / 100; // layout unit
  const lines = ['if (player.isHavingFun()) { keep(); }', '// TODO: make game good', 'spikes.push(spike); // more?',
    'gravity = 9.8 * vibes;', '/* generated in one try */', 'fingers = 5; // or 6', "// I don't know why this works", '// sorry'];

  function background() {
    x.fillStyle = '#0b0d12'; x.fillRect(0, 0, w, h);
    x.strokeStyle = '#121722'; x.lineWidth = Math.max(1, u * 0.15);
    const g = Math.max(18, u * 6);
    for (let i = 0; i < w; i += g) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, h); x.stroke(); }
    x.font = `${Math.max(10, u * 2.6)}px ${FONT}`; x.fillStyle = 'rgba(45,212,191,0.12)';
    let seed = 7; const r = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
    for (let i = 0; i < 26; i++) x.fillText(lines[i % lines.length], r() * w - w * 0.1, r() * h);
    // ground strip
    const gy = h - u * 14, t = u * 7;
    for (let i = 0; i < w; i += t) { x.fillStyle = '#161c2a'; x.fillRect(i, gy, t, h - gy); x.fillStyle = '#1b2335'; x.fillRect(i + 2, gy + 2, t - 4, t - 4); }
    x.fillStyle = '#2dd4bf'; x.fillRect(0, gy, w, Math.max(2, u * 0.5));
    return gy;
  }
  function hero(cx, gy, s) { // the rectangle protagonist
    x.fillStyle = '#fff'; x.fillRect(cx - s * 0.38, gy - s, s * 0.77, s);
    x.fillStyle = '#0b0d12'; x.fillRect(cx - s * 0.12, gy - s * 0.78, s * 0.11, s * 0.15); x.fillRect(cx + s * 0.13, gy - s * 0.78, s * 0.11, s * 0.15);
  }
  function spikes(x0, gy, n, s) {
    x.fillStyle = '#f43f5e'; x.beginPath();
    for (let i = 0; i < n; i++) { x.moveTo(x0 + i * s, gy); x.lineTo(x0 + i * s + s / 2, gy - s * 1.2); x.lineTo(x0 + (i + 1) * s, gy); }
    x.fill();
  }
  function glitch(text, cx, cy, size) {
    x.font = `bold ${size}px ${FONT}`; x.textAlign = 'center'; x.textBaseline = 'middle';
    const o = Math.max(2, size * 0.05);
    x.globalCompositeOperation = 'lighter';
    x.fillStyle = 'rgba(244,63,94,0.85)'; x.fillText(text, cx - o, cy);
    x.fillStyle = 'rgba(45,212,191,0.85)'; x.fillText(text, cx + o, cy);
    x.globalCompositeOperation = 'source-over';
    x.fillStyle = '#e5e7eb'; x.fillText(text, cx, cy);
  }
  function fit(text, maxW, maxSize) {
    let s = maxSize;
    x.font = `bold ${s}px ${FONT}`;
    while (x.measureText(text).width > maxW && s > 8) { s -= 1; x.font = `bold ${s}px ${FONT}`; }
    return s;
  }
  function title(cx, top, maxW, maxH, subtitle) {
    const s1 = Math.min(fit('THIS GAME WAS', maxW, maxH * 0.32), fit('MADE BY AI', maxW, maxH * 0.42) * 0.78);
    const s2 = fit('MADE BY AI', maxW, maxH * 0.42);
    glitch('THIS GAME WAS', cx, top + s1 * 0.6, s1);
    glitch('MADE BY AI', cx, top + s1 * 1.2 + s2 * 0.62, s2);
    if (subtitle) {
      x.font = `${s2 * 0.26}px ${FONT}`; x.fillStyle = '#f59e0b'; x.textAlign = 'center';
      x.fillText('(mostly)', cx, top + s1 * 1.2 + s2 * 1.45);
    }
  }

  if (kind === 'icon') {
    x.fillStyle = '#0b0d12'; x.beginPath(); x.roundRect(0, 0, w, h, w * 0.18); x.fill();
    x.strokeStyle = '#2dd4bf'; x.lineWidth = w * 0.03; x.beginPath(); x.roundRect(w * 0.03, h * 0.03, w * 0.94, h * 0.94, w * 0.16); x.stroke();
    hero(w / 2, h * 0.78, h * 0.5);
    x.font = `bold ${w * 0.16}px ${FONT}`; x.fillStyle = '#2dd4bf'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillText('AI', w / 2, h * 0.17);
    return;
  }
  if (kind === 'logo') { // transparent, title only
    title(w / 2, h * 0.12, w * 0.92, h * 0.8, false);
    return;
  }
  const gy = background();
  if (kind === 'hero') { // Steam says: no text on the library hero
    hero(w * 0.62, gy, u * 22);
    spikes(w * 0.72, gy, 4, u * 6);
    x.fillStyle = '#22c55e'; x.fillRect(w * 0.88, gy - u * 30, u * 1, u * 30);
    x.beginPath(); x.moveTo(w * 0.88 + u, gy - u * 30); x.lineTo(w * 0.88 + u * 9, gy - u * 26); x.lineTo(w * 0.88 + u, gy - u * 22); x.fill();
    return;
  }
  const portrait = h > w;
  const small = h < 200;
  title(w / 2, portrait ? h * 0.12 : h * 0.06, w * 0.9, portrait ? h * 0.42 : h * (small ? 0.78 : 0.62), !small);
  if (!small) {
    hero(w * 0.5, gy, u * (portrait ? 20 : 16));
    spikes(w * 0.66, gy, 3, u * 4.5);
  }
}

(async () => {
  const browser = await chromium.launch();
  for (const [file, w, h, kind] of ART) {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.setContent('<html><body style="margin:0;background:transparent"></body></html>');
    await page.evaluate(`(${draw.toString()})(${w}, ${h}, ${JSON.stringify(kind)})`);
    const out = path.join(ROOT, file);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await page.locator('canvas').screenshot({ path: out, omitBackground: true });
    await page.close();
    console.log('wrote', file, `${w}x${h}`);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
