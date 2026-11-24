# Releasing on Steam

A checklist for getting from this folder to a Steam store page. Steam's own
rules change, so check each step against the
[Steamworks documentation](https://partner.steamgames.com/doc/home) as you go.

## 1. Steamworks account (do this first; it has waiting periods)

1. Sign up at [partner.steamgames.com](https://partner.steamgames.com/) and
   pay the Steam Direct fee for one app. It's $100, and Valve pays it back
   once the game earns $1,000 in gross revenue.
2. Fill in the tax interview, bank details and identity verification.
3. Expect waiting periods: a new developer account has to wait before its
   first release, and the store page has to show as "Coming Soon" for a
   while before launch. Valve also reviews both the store page and the build,
   which takes a few business days each.

When that's done you'll have an **App ID** and at least one **Depot ID**.

## 2. Disclose the AI use (required)

Steam's Content Survey asks whether the game uses AI-generated content. This
one does: the code, level design, writing, art and music came out of an AI
coding session. Disclose it as **pre-generated** AI content and describe it
honestly. The game's whole premise is that it was made by AI, so the
disclosure doubles as marketing.

The game doesn't generate anything with AI while it runs (the narrator's
lines are pre-written), so there's no **live-generated** content to declare.

## 3. Build

Build each platform on that platform. Windows builds made on Linux need Wine
for some steps.

```bash
npm install
```

```bash
npm run dist:win
```

That produces `dist/win-unpacked/`, the folder Steam uploads. `dist:linux`
and `dist:mac` produce `dist/linux-unpacked/` and `dist/mac/`. A macOS build
needs Apple code signing and notarization before it can ship, so the simplest
start is Windows only, with Linux added later. A Linux build also runs on
Steam Deck.

Before every upload, run the checks:

```bash
node tools/solve-levels.js
```

```bash
node tools/playtest.js
```

## 4. Upload with SteamPipe

1. Download the Steamworks SDK from the partner site. It includes `steamcmd`
   under `tools/ContentBuilder`.
2. In `steam/app_build.vdf`, replace `YOUR_APP_ID` and `YOUR_WINDOWS_DEPOT_ID`
   with your real IDs.
3. Upload:

   ```bash
   steamcmd +login YOUR_STEAM_USERNAME +run_app_build "$PWD/steam/app_build.vdf" +quit
   ```

4. In Steamworks, go to **SteamPipe → Builds**, put the new build live on the
   `default` branch, and set the launch option to
   `This Game Was Made By AI.exe` (Windows) or `this-game-was-made-by-ai`
   (Linux).

## 5. Store page

Draft art is in `steam/store-art/`. To regenerate it, run
`node tools/make-art.js`. Steam's art guidelines are strict: the capsules
need to look clean at small sizes, and the library hero must have no text.
Polish or replace the draft art before you submit.

| File | Size | Where Steam uses it |
|------|------|---------------------|
| `header_capsule.png` | 920×430 | Top of the store page |
| `small_capsule.png` | 462×174 | Search results and lists |
| `main_capsule.png` | 1232×706 | Front-page features |
| `vertical_capsule.png` | 748×896 | Seasonal sales |
| `library_capsule.png` | 600×900 | Steam library grid |
| `library_hero.png` | 3840×1240 | Library page banner (no text) |
| `library_logo.png` | 1280×720 | Logo drawn over the hero (transparent) |

You also need at least five 1920×1080 screenshots. Play the desktop build in
fullscreen and capture them there.

A draft of the short description:

> A platformer written, designed, drawn and scored by an AI that is very
> confident it did a good job. Dodge hallucinated platforms, write the next
> level's prompt, outrun the AI's context window, fix its bugs, and defeat a
> final boss with the correct number of fingers.

## Optional extras

- **Achievements and Steam Cloud:** add [steamworks.js](https://github.com/ceifa/steamworks.js)
  to the Electron app. Natural achievements: "Trust Issues" (die to a
  hallucinated platform), "Prompt Engineer" (finish all three Level 3
  prompts), "Duck Whisperer" (bounce on 10 ducks), "Five Stars".
- **Steam overlay:** the overlay doesn't hook into Electron windows reliably.
  The game plays fine without it.
- **Its own repository:** the game currently sits inside the Activity
  dashboard repo. Moving `this-game-was-made-by-ai/` to its own repository
  will keep releases and history separate.
