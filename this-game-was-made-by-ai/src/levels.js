'use strict';
// Level layouts and the narrator's script. Grids are 18 rows of 30px tiles.
//
// Tiles:  .  empty          #  solid
//         ~  hallucinated   looks solid, is not
//         ?  phantom        looks fake (dashed), is solid
//         ^  spike          F  flag        f  hallucinated flag
const TILE = 30, ROWS = 18;

class LevelBuilder {
  constructor(w) {
    this.w = w;
    this.g = [];
    for (let y = 0; y < ROWS; y++) this.g.push(new Array(w).fill('.'));
    this.ents = [];
    this.start = { x: 2, y: 14 };
  }
  set(x, y, c) { if (x >= 0 && x < this.w && y >= 0 && y < ROWS) this.g[y][x] = c; return this; }
  rect(x1, y1, x2, y2, c = '#') {
    for (let y = y1; y <= y2; y++) for (let x = x1; x <= x2; x++) this.set(x, y, c);
    return this;
  }
  ground(x1, x2, top = 15, c = '#') { return this.rect(x1, top, x2, ROWS - 1, c); }
  plat(x1, x2, y, c = '#') { return this.rect(x1, y, x2, y, c); }
  spikes(x1, x2, y) { return this.rect(x1, y, x2, y, '^'); }
  flag(x, y) { return this.set(x, y, 'F'); }
  player(x, y) { this.start = { x, y }; return this; }
  ent(type, x, y, extra) { this.ents.push(Object.assign({ type, x, y }, extra)); return this; }
  done() { return { grid: this.g, w: this.w, h: ROWS, start: this.start, ents: this.ents }; }
}

function flipLevel(lv) {
  lv.grid.reverse();
  lv.start.y = ROWS - 1 - lv.start.y;
  lv.ents.forEach(e => { e.y = ROWS - 1 - e.y; });
  return lv;
}

// Level 5: each bug you pick up fixes the next one on this list, in order.
const BUGS = [
  { id: 'swap', label: 'BUG-001  Left and right are swapped' },
  { id: 'lorem', label: 'BUG-002  Narrator localized to Lorem Ipsum' },
  { id: 'tex', label: 'BUG-003  Textures failed to load' },
  { id: 'tilt', label: 'BUG-004  Screen rotated 4 degrees' },
  { id: 'flicker', label: 'BUG-005  Player keeps flickering' },
];
const BUG_FIX_LINES = [
  'Bug fixed: controls. Left is left again. For now.',
  'Ah, I can speak again. Sorry, I was briefly localized into Latin. It was not even real Latin.',
  'Textures restored. The magenta was a bold design choice. It was not a design choice.',
  'Screen straightened. Your neck may now relax.',
  'All bugs fixed! I can finally ship this. The flag is unlocked.',
];

const GENERIC_DEATHS = [
  "You died. I've logged this as a feature.",
  "That's on me. Actually, no, that's on you.",
  'Respawning. I made no changes, out of respect for the challenge.',
  'Have you tried not touching the dangerous parts?',
  "I'm sorry you experienced that. Would you like me to regenerate you?",
  'Interesting strategy. Bold. Incorrect.',
  'My analysis suggests the floor was not where you were.',
  'Great attempt! (I say this to everyone.)',
  'I have regenerated you. You may notice no difference. That is the point.',
  "Don't worry. Statistically, you will eventually succeed by accident.",
  'Death logged. I would show you the log, but it just says "oops" a lot.',
];

const DEATH_MILESTONES = {
  10: "10 deaths. I considered adding an easy mode. I've considered it. No.",
  25: '25 deaths. You are now statistically my most dedicated playtester.',
  50: "50 deaths. I wrote you a poem: 'Rectangle fell / again and again / it was very sad'.",
  100: '100 deaths. I am legally required to tell you that this is a lot of deaths.',
};

const LEVELS = [
  // ---------------------------------------------------------------------
  {
    id: 'l1', name: 'LEVEL 1', title: 'A Level', width: 90, music: 'main', playerLabel: true,
    genLog: [
      'booting creativity.exe ........ ok',
      'generating terrain ............ done',
      'generating protagonist ........ rectangle',
      'placing spikes ................ yes',
      'checking if fun ............... skipped',
    ],
    build(b) {
      b.ground(0, 18).ground(22, 35).ground(30, 35, 13).spikes(26, 27, 14)
        .ground(39, 50, 13)
        .ground(51, 68, 16).spikes(51, 68, 15)
        .plat(53, 56, 12).plat(59, 62, 11).plat(65, 68, 12)
        .ground(69, 89).flag(85, 14).player(2, 14);
    },
    intro: [
      'Hello. I am the AI that made this game.',
      'I made it in one try. Please do not look too closely.',
      'I have generated a character for you. It is a rectangle. Rectangles are timeless.',
    ],
    triggers: [
      { x: 6, text: "Move with the arrow keys or WASD. Jump with Space. I assume. I didn't check." },
      { x: 17, text: "That's a gap. Gaps are where the floor isn't." },
      { x: 23, text: 'These red triangles are spikes. My training data was very clear that games need spikes.' },
      { x: 40, text: "You're doing great. I can tell because I'm guessing." },
      { x: 52, text: "This part is called 'platforming'. I named the genre after it." },
      { x: 72, text: 'Up ahead is the flag. I think. It might be a very thin tree.' },
    ],
    outro: "Level complete! I'd rate it 10/10. I'm not biased. I just made it.",
  },

  // ---------------------------------------------------------------------
  {
    id: 'l2', name: 'LEVEL 2', title: 'Trust Me', width: 90, music: 'main',
    genLog: [
      'generating platforms .......... done',
      'verifying platforms are real .. probably',
      'confidence .................... 100%',
      'citing sources ................ [1] trust me',
    ],
    build(b) {
      b.ground(0, 12).rect(13, 15, 16, 17, '~').plat(14, 15, 12, '?')
        .ground(17, 40).ground(31, 40, 12).rect(27, 4, 28, 14, '~')
        .plat(43, 45, 12).plat(48, 50, 12, '~').plat(48, 50, 9, '?')
        .plat(53, 55, 10).plat(57, 59, 10, '~')
        .ground(60, 89, 12).set(72, 11, 'f').spikes(77, 78, 11).flag(86, 11)
        .player(2, 14);
    },
    intro: [
      "Level 2. I've double-checked this one.",
      'Every platform here is 100% solid. I am extremely confident.',
      "Oh, and the dashed outlines are not real. Don't stand on those.",
    ],
    triggers: [
      { x: 23, text: "A wall. You'll need to find another way around. There is no other way around." },
      { x: 29, text: "Oh. You walked through it. I'll pretend that was intentional." },
      { x: 42, text: 'Reminder: dashed platforms are not real. You can trust me on that.' },
      { x: 49, text: "...You're standing on a dashed one. That's fine. That's totally fine." },
      { x: 63, text: 'There are two flags ahead. Statistically, at least one of them is real.' },
    ],
    onDeath(api, cause, n) {
      if (n === 3) {
        api.lp.revealFake = true;
        return "I've added a hallucination detector. Fake things will shimmer now. You're welcome.";
      }
      if (cause === 'fall' && !api.lp.saidFall) {
        api.lp.saidFall = true;
        return 'Ah. That ground was hallucinated. It looked real to me too.';
      }
      return null;
    },
    onFakeFlag: 'That flag was a hallucination. The real one is further along. Probably.',
    outro: "Level 2 complete. I've updated my confidence to 'medium-high'.",
  },

  // ---------------------------------------------------------------------
  {
    id: 'l3', name: 'LEVEL 3', title: 'Prompt Engineering',
    choice: {
      prompt: 'What should the next level have?',
      options: [
        { key: 'hard', label: 'More challenge' },
        { key: 'chill', label: 'Something relaxing' },
        { key: 'flip', label: 'Surprise me' },
      ],
    },
    variants: {
      hard: {
        title: 'More Challenge', width: 75, music: 'tense',
        genLog: [
          'parsing prompt: "more challenge"',
          'interpreting as ............... more spikes',
          'adding spikes ................. done',
          'adding more spikes ............ done',
        ],
        build(b, lp) {
          b.ground(0, 74).player(2, 14).flag(71, 14);
          const clusters = [[7, 8], [12, 13], [17, 19], [24, 25], [30, 32], [38, 39], [44, 46], [54, 55], [58, 60], [64, 65]];
          clusters.forEach(([a, z], i) => {
            if (lp.duckified && i % 2 === 1) { for (let x = a; x <= z; x++) b.ent('duck', x, 14); }
            else b.spikes(a, z, 14);
          });
          b.rect(49, 13, 50, 14).spikes(49, 50, 12);
        },
        intro: ['You asked for more challenge.', 'I have added more spikes. That is what challenge is.'],
        triggers: [
          { x: 20, text: "Challenge level: high. Fun level: unknown. I didn't measure it." },
          { x: 47, text: 'This block has spikes on top. I call it "the spike block". Naming is hard.' },
          { x: 57, text: "Almost there. I've left the last few spikes in for authenticity." },
        ],
        onDeath(api, cause, n) {
          if (n === 3) {
            api.lp.duckified = true;
            return "Too much? I've replaced some spikes with ducks. Ducks are the opposite of spikes.";
          }
          return null;
        },
        outro: "You beat 'more challenge'. I'll remember that you enjoy pain.",
      },
      chill: {
        title: 'Something Relaxing', width: 70, music: 'calm', gravity: 0.5, jumpScale: 0.8, sunset: true,
        genLog: [
          'parsing prompt: "something relaxing"',
          'reducing gravity .............. 50%',
          'adding ducks .................. 5',
          'adding sunset ................. orange circle',
        ],
        build(b) {
          b.ground(0, 14).plat(18, 21, 11).plat(25, 28, 8).ground(32, 40, 13)
            .plat(45, 48, 10).plat(53, 56, 12).ground(60, 69).flag(67, 14).player(2, 14)
            .ent('duck', 5, 14).ent('duck', 9, 14).ent('duck', 35, 12).ent('duck', 38, 12).ent('duck', 63, 14);
        },
        intro: [
          'You asked for something relaxing.',
          "I've reduced gravity by 50%. Studies show floating is relaxing. I made up the studies.",
          "I've also added ducks. Ducks are calming. That part is not made up.",
        ],
        triggers: [
          { x: 19, text: 'Please enjoy the sunset. It is an orange circle. I worked very hard on it.' },
          { x: 42, text: 'Breathe in. Breathe out. Do not fall into the void.' },
        ],
        outro: "I hope that was relaxing. If not, I've filed a ticket with myself.",
      },
      flip: {
        title: 'Surprise Me', width: 80, music: 'main', flipped: true,
        genLog: [
          'parsing prompt: "surprise me"',
          'surprise level ................ maximum',
          'gravity ....................... -1',
          'moving text box ............... done',
        ],
        build(b) {
          b.ground(0, 15).ground(19, 30).spikes(24, 25, 14).ground(33, 45, 13)
            .plat(48, 51, 11).plat(55, 58, 13).ground(62, 79).spikes(66, 67, 14)
            .flag(76, 14).player(2, 14);
        },
        intro: [
          "You said 'surprise me'.",
          'Surprise! Gravity is upside down. I was trained on what surprises look like.',
          "I moved my text box to the bottom so it won't block the floor. The ceiling. The floor.",
        ],
        triggers: [
          { x: 22, text: 'If you feel dizzy, that is the surprise working as intended.' },
          { x: 50, text: "Fun fact: in this level, 'jump' means 'fall up, but on purpose'." },
        ],
        outro: "Surprise complete. Was it a good surprise? Don't answer. I've decided it was.",
      },
    },
  },

  // ---------------------------------------------------------------------
  {
    id: 'l4', name: 'LEVEL 4', title: 'Context Window', width: 150, music: 'tense', contextWall: true,
    genLog: [
      'generating a very long level ..',
      'level length .................. 4,500 px',
      'context window ................ less than that',
      'remembering the start ......... [truncated]',
    ],
    build(b) {
      b.ground(0, 20).ground(24, 34).spikes(29, 30, 14).ground(37, 42, 13)
        .plat(45, 47, 11).plat(50, 52, 11).ground(55, 70, 14).spikes(60, 61, 13)
        .ground(73, 80, 12).ground(83, 95).spikes(87, 88, 14).spikes(92, 93, 14)
        .plat(98, 100, 12).plat(103, 105, 10).plat(108, 110, 12)
        .ground(113, 125).spikes(118, 120, 14).ground(128, 149).flag(145, 14).player(2, 14);
    },
    intro: ['Level 4. This level is very long.', 'My context window, however, is not.'],
    timeTriggers: [
      { t: 5, text: "I'm starting to forget the beginning of the level. Please keep moving right." },
      { t: 12, text: 'What was I saying? Oh, right. Welcome to Level 1!' },
      { t: 19, text: "Wait. This isn't Level 1. I've lost track. Let's call it Level Some." },
      { t: 26, text: "I've forgotten your name. I'll call you Rectangle. It feels right." },
      { t: 33, text: 'Summary of the level so far: there was a level.' },
    ],
    triggers: [{ x: 132, text: "I remember this part! It's the end. I'm almost sure it's the end." }],
    onAttempt(api) { api.ls.wallX = -120; api.ls.wallT = 0; },
    update(api, dt) {
      const s = api.ls;
      s.wallT += dt;
      if (s.wallT > 3) s.wallX += Math.min(230, 120 + (s.wallT - 3) * 4) * dt;
      api.forgetBefore(s.wallX);
      if (api.player.x < s.wallX) api.kill('forgotten');
    },
    onDeath(api, cause) {
      if (cause === 'forgotten') {
        return pickOne([
          'I forgot you existed. Sorry. Respawning you from memory.',
          'You fell out of my context window. It happens to the best of us.',
          'Who are you again? Never mind. Try again.',
        ]);
      }
      return null;
    },
    outro: "Level 4 complete. I'll be honest, I don't remember it.",
  },

  // ---------------------------------------------------------------------
  {
    id: 'l5', name: 'LEVEL 5', title: 'Bug Bounty', width: 100, music: 'bugs', bugs: true,
    genLog: [
      'generating level .............. done',
      'running tests ................. 5 failed',
      'fixing tests .................. deleted them',
      'shipping ...................... blocked',
    ],
    build(b) {
      b.ground(0, 99).ent('bug', 8, 14, { id: 0 })
        .plat(12, 16, 12).plat(19, 23, 9).ent('bug', 21, 8, { id: 1 })
        .rect(28, 15, 33, 16, '.').spikes(28, 33, 16).plat(30, 31, 12)
        .plat(40, 42, 12)
        .rect(45, 9, 53, 9).rect(45, 10, 45, 14, '~').rect(53, 10, 53, 14).ent('bug', 49, 14, { id: 2 })
        .plat(57, 60, 8).ent('bug', 58, 7, { id: 3 })
        .spikes(66, 67, 14).spikes(72, 74, 14)
        .plat(78, 80, 12).plat(82, 85, 9).ent('bug', 83, 8, { id: 4 })
        .flag(96, 14).player(2, 14);
    },
    intro: [
      'Level 5. I may have introduced a few bugs.',
      'Collect all 5 of them and I will fix them. Then I can ship the game.',
    ],
    triggers: [
      { x: 38, text: "There's definitely nothing behind that wall. I would know. I made it." },
      { x: 90, text: "That flag is locked until the bugs are fixed. I can't ship with known bugs. Only unknown ones." },
    ],
    flagLocked: api => api.lp.collected.size < BUGS.length,
    onCollect(api, n) { return BUG_FIX_LINES[n - 1]; },
    outro: 'Zero known bugs. There are unknown bugs. There are always unknown bugs.',
  },

  // ---------------------------------------------------------------------
  {
    id: 'l6', name: 'LEVEL 6', title: 'Final Boss (Generated)', width: 32, music: 'boss', boss: true,
    genLog: [
      'prompt: "scary final boss hand"',
      'generating hand ............... done',
      'counting fingers .............. 6',
      'is that right? ................ yes',
    ],
    build(b) {
      b.ground(0, 31, 16).rect(0, 0, 0, 15).rect(31, 0, 31, 15)
        .plat(4, 7, 12).plat(24, 27, 12).player(15, 15).ent('boss', 0, 0);
    },
    intro: [
      "Final level. I generated a boss from the prompt 'scary hand'.",
      'It has the correct number of fingers.',
      "Jump on it while it's resting. That's how bosses work. I checked.",
    ],
    bossHitLines: [
      '',
      "I've been told hands are hard to generate. I'm starting to see why.",
      'It has more fingers now. That is also correct. It is throwing tokens at you. Those are expensive.',
    ],
    onDeath(api, cause) {
      if (cause === 'hand') return pickOne(['High five! No, wait. Low five. Very low.', 'You were handled.', 'That was the palm. The palm is the dangerous side.']);
      if (cause === 'token') return pickOne(['Hit by a token. That one cost me $0.00002.', 'Token limit reached. Yours, specifically.']);
      return null;
    },
    victoryLine: "You defeated the boss. I'll mark it as 'resolved'.",
  },
];

function pickOne(a) { return a[Math.floor(Math.random() * a.length)]; }
