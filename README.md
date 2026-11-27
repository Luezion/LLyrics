# LLyrics

**English** · [Español](README.es.md) · [Português](README.pt-BR.md)

Synced lyrics overlay for Windows, made for gaming. It shows the lyrics of the song you're playing on top of any game, with animations in the style of the Minecraft mod *Show the Lyrics*.

![Preview](docs/previa.png)

## Download

**[⬇ Download the latest version](https://github.com/Luezion/LLyrics/releases/latest/download/LLyrics-windows.zip)** (Windows 10/11)

1. Extract the zip into a folder of yours (e.g. `Documents\LLyrics`). Avoid `Program Files`, otherwise the app can't update itself.
2. Open `LLyrics.exe`. The app lives in the tray, near the clock (♪ icon). No Python needed.
3. Play a song.

Windows may show "Windows protected your PC" because the app doesn't have a paid digital signature. Click **More info → Run anyway**.

When a new version comes out, the app shows a window to update with one click.

## Features

- Reads whatever is playing in any player that shows up in the Windows media controls (Spotify, YouTube and YouTube Music in the browser, Apple Music, Deezer, VLC…)
- Fetches synced lyrics from [lrclib.net](https://lrclib.net)
- Draws the lyrics in a transparent, always-on-top window that **lets clicks pass through** to the game
- "Now playing" widget with cover, title, artist and progress bar; the cover can be a square, a circle or a spinning vinyl record, as a card or as an Instagram-style sticker
- Available in **English, Español and Português (Brasil)**

### Styles

- Entrances: typewriter (synced to the singing), drop, rise, words, fade, pop, wave
- Exits: same as entrance, fade, blown away
- 12 layouts: lines, **stack** (key words big, little words small), first word highlighted (with or without tilt), **arc**, **snake**, **spotlight** (one big word at a time), **scatter**, **poster**, **punchline**, **tilted** and **side perspective** (lines leaning on the left/right like side walls)
- Karaoke, instrumental countdown, previous line and next line preview
- Album cover colour, palettes, rainbow, custom colour, **2 or 3 colour gradients**, flowing rainbow
- Idle motion (shake, wave, bounce, pulse, float, sway), sparkles and party mode
- Outline, shadow, glow and background; 12 free fonts (Google Fonts)
- **My styles**: save your looks on your PC and switch between them with one click (also from the tray menu)
- **Style for this song**: a look generated from the song's rhythm, lyrics, the artist's genre ([MusicBrainz](https://musicbrainz.org)) and the cover colours, once or on every song, with a **Generator** page to set size limits, motion, effects, colours, layouts and fonts
- Ready-made styles, including "Shake" and "Void Echoes", and importing looks from the mod's community site with a `STL-XXXXXX` code

### Position

- Fixed (drag it with **Ctrl+Shift+K**) or **random on every line**
- Option to **never appear in the middle of the screen**, so it doesn't cover the crosshair in shooters

### Shortcuts

Default shortcuts. You can change them in **Settings → Shortcuts**.

| Shortcut | Action |
|---|---|
| Ctrl+Shift+L | Show/hide |
| Ctrl+Shift+K | Move the windows |
| Ctrl+Shift+O | Settings |

## Community

Share your styles and try the ones other players made, in **Settings → Community**:

- **Copy code**: turns your current look into a code (`LLY1-…`) you can send to anyone. They paste it in *Style → Community looks → Import*.
- **Publish to community**: opens a GitHub form already filled in. Once approved, the style shows up in everyone's gallery.
- **Community gallery**: browse, preview and apply styles with one click.

Looks from the mod's site ([lyrics.remake.lol](https://lyrics.remake.lol/)) can be imported too (`STL-…` codes), but publishing there is only possible from inside Minecraft with the mod.

## In games (Valorant and others)

Set the game to **windowed fullscreen** (borderless). In exclusive fullscreen no overlay can appear on top.

LLyrics doesn't touch the game: it doesn't read memory, inject anything or install drivers. It's just transparent Windows windows, like the Discord overlay. Still, there's no official approval from any game developer for third-party apps; use it at your own risk.

## Run from source

1. Install [Python 3.10+](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**
2. Download the code (**Code → Download ZIP**) and extract it
3. Double-click `Iniciar.bat`

## Releasing a new version

1. Write the changes at the top of `CHANGELOG.md` (`## 1.3.0`, then `### English`, `### Español` and `### Português`)
2. Change the number in `version.py`
3. Push to `main`. GitHub Actions builds the `.exe`, creates the Release, and everyone gets the update window in their language.

## Translations

All the app's text lives in `i18n.py`. To add a language, copy the English column, translate it and add it to `LANGUAGES`.

## Project layout

| File | What it does |
|---|---|
| `main.py` | Starts the app, tray and shortcuts |
| `media.py` | Reads the player through Windows (SMTC) |
| `lyrics.py` | Fetches and parses LRC lyrics from lrclib |
| `render.py` | Draws the lyrics, layouts, animations and widget |
| `overlay.py` | Overlay windows and positioning |
| `settings_ui.py` | Settings window |
| `i18n.py` | Translations (English, Español, Português) |
| `hotkeys.py` | Configurable global shortcuts |
| `looks.py` | Imports looks from the mod's site |
| `autostyle.py` | Generates a style for the song that's playing |
| `perspective.py` | Side perspective layout |
| `mystyles.py` | Styles saved on the PC |
| `community.py` | Community gallery and sharing |
| `lookcode.py` | Style codes (`LLY1-…`) |
| `updater.py` | Checks for a new version and updates the app |
| `config.py` | Options and defaults |
| `version.py` | Version number |
| `winutil.py` | Click-through, always on top, global hotkeys, start with Windows |

## Credits

- Inspired by the Minecraft mod *Show the Lyrics* by FireStund. Community looks: [lyrics.remake.lol](https://lyrics.remake.lol/). LLyrics was written from scratch; no code from the mod was used.
- Lyrics: [lrclib.net](https://lrclib.net)
- Fonts: Google Fonts, SIL OFL (`fonts/OFL-licenca-fontes.txt`)
