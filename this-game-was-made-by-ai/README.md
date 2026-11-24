# This Game Was Made By AI

A short comedy platformer (about 15–25 minutes) narrated by the AI that
made it. The AI is very confident. It shouldn't be.

## The levels

| # | Level | The joke |
|---|-------|----------|
| 1 | **A Level** | Tutorial. The protagonist is a rectangle; the flag "might be a very thin tree." |
| 2 | **Trust Me** | Hallucinated platforms look solid and aren't. The dashed ones the AI says are fake are the real ones. Two flags, one hallucinated. After 3 deaths the AI adds a "hallucination detector." |
| 3 | **Prompt Engineering** | You write the next level's prompt. *More challenge* means spikes (later swapped for ducks), *Something relaxing* means half gravity and a sunset, *Surprise me* turns gravity upside down. |
| 4 | **Context Window** | A long level. The AI forgets the start of it as you go: a wall of static eats the level from the left. It also forgets your name. |
| 5 | **Bug Bounty** | Swapped controls, Lorem Ipsum narration, missing textures, a tilted screen. Each bug you catch fixes one. The flag stays locked until the game is shippable. |
| 6 | **Final Boss (Generated)** | A giant hand with "the correct number of fingers" (6). Each hit adds a finger. |

Then the game asks you to rate it, rolls credits ("Bug Fixes: You"), and
offers to generate a sequel.

## Play it

**In a browser:** open `index.html`. No build step and no server needed.

**As the desktop app (this is the Steam build):**

```bash
npm install
```

```bash
npm start
```

Controls: arrows/WASD to move, Space/Z/Up to jump, Esc to pause, R to retry,
M to toggle music, F11 for fullscreen in the desktop app. Gamepads work too
(D-pad/stick, A to jump, Start to pause). Menus also take the mouse.

Progress, death count and music preference are saved locally.

## How it's built

There are no asset files. Everything is drawn on a canvas and every sound is
synthesized with WebAudio.

| File | What it does |
|------|--------------|
| `src/levels.js` | Level layouts (built with a small tile builder), the narrator's script, per-level gimmicks |
| `src/game.js` | Physics, entities, the boss, rendering, menus, game states |
| `src/audio.js` | Synthesized sound effects plus a small step-sequencer for the music |
| `src/input.js` | Keyboard and gamepad, mapped to actions |
| `electron/main.js` | Desktop wrapper for Steam |

To jump straight into a level while working on it, open
`index.html?level=4` (or `?level=3&variant=flip`).

## Checks

```bash
node tools/solve-levels.js
```

Re-implements the player physics and searches every level for a route from
the spawn point to the flag (and to every bug in level 5). Run it after you
change a layout so you never ship an impossible jump.

```bash
node tools/playtest.js
```

Plays through in headless Chromium: every level loads, the context wall
catches an idle player, picking up a bug fixes the swapped controls, the boss
can be beaten, and the rating, credits and sequel screens lead back to the
title. It fails on any JavaScript error and saves screenshots to
`tools/shots/`. Both scripts need Playwright.

```bash
node tools/make-art.js
```

Regenerates the app icon (`build/icon.png`) and the Steam store capsules
(`steam/store-art/`).

## Shipping to Steam

See [STEAM.md](STEAM.md).
