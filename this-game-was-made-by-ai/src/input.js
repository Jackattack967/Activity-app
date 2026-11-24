'use strict';
// Keyboard + gamepad, reduced to named actions. `down` is held state,
// `pressed` is the edge since the last endFrame().
const Input = (() => {
  const KEYMAP = {
    ArrowLeft: 'left', KeyA: 'left',
    ArrowRight: 'right', KeyD: 'right',
    ArrowUp: 'up', KeyW: 'up',
    ArrowDown: 'down', KeyS: 'down',
    Space: 'jump', KeyZ: 'jump', KeyK: 'jump',
    Enter: 'confirm', NumpadEnter: 'confirm',
    Escape: 'pause', KeyP: 'pause',
    Backspace: 'back',
    KeyM: 'music',
    KeyR: 'restart',
  };
  const codes = new Set();
  const pressed = new Set();
  let padDown = new Set();
  const listeners = [];

  window.addEventListener('keydown', e => {
    listeners.forEach(fn => fn());
    const a = KEYMAP[e.code];
    if (!a) return;
    e.preventDefault();
    if (e.repeat) return;
    if (!isDown(a)) pressed.add(a);
    codes.add(e.code);
  });
  window.addEventListener('keyup', e => { codes.delete(e.code); });
  window.addEventListener('blur', () => codes.clear());
  window.addEventListener('pointerdown', () => listeners.forEach(fn => fn()));

  function isDown(a) {
    if (padDown.has(a)) return true;
    for (const c of codes) if (KEYMAP[c] === a) return true;
    return false;
  }

  function pollPad() {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const cur = new Set();
    for (const gp of pads) {
      if (!gp) continue;
      const b = i => gp.buttons[i] && gp.buttons[i].pressed;
      const ax = gp.axes[0] || 0, ay = gp.axes[1] || 0;
      if (b(14) || ax < -0.4) cur.add('left');
      if (b(15) || ax > 0.4) cur.add('right');
      if (b(12) || ay < -0.75) cur.add('up');
      if (b(13) || ay > 0.75) cur.add('down');
      if (b(0)) { cur.add('jump'); cur.add('confirm'); }
      if (b(1)) cur.add('back');
      if (b(9)) cur.add('pause');
    }
    if (cur.size) listeners.forEach(fn => fn());
    for (const a of cur) if (!padDown.has(a)) pressed.add(a);
    padDown = cur;
  }

  return {
    down: isDown,
    pressed: a => pressed.has(a),
    any: () => pressed.size > 0,
    poll: pollPad,
    endFrame: () => pressed.clear(),
    onActivity: fn => listeners.push(fn),
  };
})();
