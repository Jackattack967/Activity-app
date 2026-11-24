'use strict';
// Every sound in the game is synthesized here with WebAudio, so the game
// ships with no audio files at all. "Music (generated)" is a tiny step
// sequencer playing arpeggiated chords.
const Sound = (() => {
  let ac = null, master, sfxBus, musicBus, noiseBuf = null, timer = null;
  let musicOn = true, track = 'title', step = 0, nextT = 0;
  try { musicOn = localStorage.getItem('tgwmbai.music') !== 'off'; } catch (e) { /* storage blocked */ }

  const mtof = n => 440 * Math.pow(2, (n - 69) / 12);

  function init() {
    if (ac) { if (ac.state === 'suspended') ac.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    ac = new AC();
    master = ac.createGain(); master.gain.value = 0.6; master.connect(ac.destination);
    sfxBus = ac.createGain(); sfxBus.gain.value = 0.9; sfxBus.connect(master);
    musicBus = ac.createGain(); musicBus.gain.value = musicOn ? 0.32 : 0; musicBus.connect(master);
    nextT = ac.currentTime + 0.1;
    timer = setInterval(schedule, 25);
  }

  function tone(o) {
    if (!ac) return;
    const t = o.at != null ? o.at : ac.currentTime + (o.delay || 0);
    const osc = ac.createOscillator(), g = ac.createGain();
    osc.type = o.type || 'square';
    osc.frequency.setValueAtTime(o.freq, t);
    if (o.to) osc.frequency.exponentialRampToValueAtTime(o.to, t + o.dur);
    g.gain.setValueAtTime(o.vol != null ? o.vol : 0.15, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    osc.connect(g); g.connect(o.bus || sfxBus);
    osc.start(t); osc.stop(t + o.dur + 0.02);
  }

  function noise(o) {
    if (!ac) return;
    if (!noiseBuf) {
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    const t = o.at != null ? o.at : ac.currentTime + (o.delay || 0);
    const src = ac.createBufferSource(); src.buffer = noiseBuf;
    const g = ac.createGain();
    g.gain.setValueAtTime(o.vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    let node = src;
    if (o.lowpass || o.highpass) {
      const f = ac.createBiquadFilter();
      f.type = o.lowpass ? 'lowpass' : 'highpass';
      f.frequency.value = o.lowpass || o.highpass;
      src.connect(f); node = f;
    }
    node.connect(g); g.connect(o.bus || sfxBus);
    src.start(t); src.stop(t + o.dur + 0.02);
  }

  // ---- music ------------------------------------------------------------
  const TRACKS = {
    title: { bpm: 92, chords: [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], arp: 'triangle', vol: 0.06 },
    main: { bpm: 112, chords: [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], arp: 'triangle', vol: 0.06, hats: true },
    calm: { bpm: 72, chords: [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]], arp: 'sine', vol: 0.08 },
    tense: { bpm: 132, chords: [[50, 53, 57], [50, 53, 57], [46, 50, 53], [48, 52, 55]], arp: 'square', vol: 0.035, drums: true },
    bugs: { bpm: 104, chords: [[52, 55, 59], [53, 57, 60], [52, 55, 59], [50, 54, 57]], arp: 'square', vol: 0.035, hats: true },
    boss: { bpm: 152, chords: [[57, 60, 64], [57, 60, 64], [53, 57, 60], [52, 56, 59]], arp: 'sawtooth', vol: 0.03, drums: true },
    credits: { bpm: 96, chords: [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]], arp: 'triangle', vol: 0.06, hats: true },
  };
  const ARP = [0, 1, 2, 1];

  function playStep(s, t) {
    const tr = TRACKS[track];
    const sp = 60 / tr.bpm / 4;
    const ch = tr.chords[Math.floor(s / 16) % tr.chords.length];
    const i = s % 16;
    const note = ch[ARP[i % 4]] + (i >= 8 ? 12 : 0);
    tone({ at: t, freq: mtof(note), dur: sp * 0.9, type: tr.arp, vol: tr.vol, bus: musicBus });
    if (i % 8 === 0) tone({ at: t, freq: mtof(ch[0] - 24), dur: sp * 7.5, type: 'triangle', vol: 0.16, bus: musicBus });
    if (tr.drums) {
      if (i % 4 === 0) tone({ at: t, freq: 140, to: 40, dur: 0.12, type: 'sine', vol: 0.35, bus: musicBus });
      if (i % 8 === 4) noise({ at: t, dur: 0.12, vol: 0.12, highpass: 1500, bus: musicBus });
    }
    if ((tr.hats || tr.drums) && i % 2 === 1) noise({ at: t, dur: 0.03, vol: 0.04, highpass: 6000, bus: musicBus });
  }

  function schedule() {
    if (!ac) return;
    const sp = 60 / TRACKS[track].bpm / 4;
    if (nextT < ac.currentTime - 0.2) nextT = ac.currentTime + 0.05; // tab was asleep
    while (nextT < ac.currentTime + 0.15) { playStep(step, nextT); nextT += sp; step++; }
  }

  function setTrack(name) {
    if (!TRACKS[name] || name === track) return;
    track = name; step = 0;
  }

  function toggleMusic() {
    musicOn = !musicOn;
    try { localStorage.setItem('tgwmbai.music', musicOn ? 'on' : 'off'); } catch (e) { /* ignore */ }
    if (musicBus) musicBus.gain.setTargetAtTime(musicOn ? 0.32 : 0, ac.currentTime, 0.05);
    return musicOn;
  }

  // ---- effects ------------------------------------------------------------
  const sfx = {
    jump: () => tone({ freq: 280, to: 560, dur: 0.11, vol: 0.11 }),
    die: () => { tone({ freq: 420, to: 60, dur: 0.45, type: 'sawtooth', vol: 0.16 }); noise({ dur: 0.25, vol: 0.18, lowpass: 2000 }); },
    flag: () => [0, 4, 7, 12, 16].forEach((n, i) => tone({ freq: mtof(72 + n), dur: 0.2, delay: i * 0.08, vol: 0.09 })),
    quack: () => {
      tone({ freq: 640, to: 380, dur: 0.09, type: 'sawtooth', vol: 0.11 });
      tone({ freq: 580, to: 330, dur: 0.1, type: 'sawtooth', vol: 0.09, delay: 0.11 });
    },
    bug: () => [0, 7, 12, 19].forEach((n, i) => tone({ freq: mtof(76 + n), dur: 0.1, delay: i * 0.05, vol: 0.08 })),
    type: () => tone({ freq: 1100 + Math.random() * 300, dur: 0.012, vol: 0.022 }),
    select: () => tone({ freq: 660, dur: 0.05, vol: 0.07 }),
    confirm: () => { tone({ freq: 523, dur: 0.07, vol: 0.08 }); tone({ freq: 784, dur: 0.1, vol: 0.08, delay: 0.07 }); },
    slam: () => { noise({ dur: 0.5, vol: 0.45, lowpass: 600 }); tone({ freq: 90, to: 35, dur: 0.4, type: 'sine', vol: 0.4 }); },
    hit: () => { tone({ freq: 200, to: 900, dur: 0.15, vol: 0.13 }); noise({ dur: 0.15, vol: 0.18 }); },
    bounce: () => tone({ freq: 350, to: 720, dur: 0.09, type: 'triangle', vol: 0.12 }),
    glitch: () => { for (let i = 0; i < 6; i++) tone({ freq: 200 + Math.random() * 1600, dur: 0.03, delay: i * 0.03, vol: 0.05 }); },
    error: () => { tone({ freq: 220, dur: 0.15, vol: 0.12 }); tone({ freq: 165, dur: 0.3, vol: 0.12, delay: 0.16 }); },
  };

  return { init, sfx, setTrack, toggleMusic, isMusicOn: () => musicOn };
})();
