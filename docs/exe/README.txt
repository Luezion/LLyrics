LLYRICS - synced lyrics overlay for gaming
==========================================

Shows the lyrics of the song you're playing on top of your game, in the style of
the Minecraft mod "Show the Lyrics": typewriter, karaoke, album-cover colours,
instrumental countdown and a "now playing" widget.
Works with any player that shows up in the Windows media controls
(Spotify, YouTube/YouTube Music in the browser, Apple Music, Deezer, VLC...).
Lyrics come from lrclib.net, the same site the mod uses.

HOW TO OPEN
1. Extract the whole zip into a folder of yours (e.g. Documents\LLyrics).
   Don't run the .exe from inside the zip, and keep the _internal folder next to it.
   Avoid "Program Files": the app can't update itself there.
2. Double-click LLyrics.exe. No need to install Python or anything else.
   If you see "Windows protected your PC", click
   "More info" > "Run anyway" (the app doesn't have a paid signature).
3. Play a song. The app lives in the tray, near the clock (♪ icon).

LANGUAGE
Settings > General > Language: English, Español or Português (Brasil).

SHORTCUTS (you can change them in Settings > Shortcuts)
  Ctrl+Shift+L  show/hide the overlay
  Ctrl+Shift+K  move mode: drag the lyrics and the widget; press again to finish
  Ctrl+Shift+O  settings (or click the ♪ tray icon)

START WITH WINDOWS
Settings > General > "Start with Windows".

UPDATES
When a new version comes out, the app shows a window to update with one click.
You can also check from the ♪ icon menu > "Check for updates".

IN VALORANT AND OTHER GAMES
- Use "Windowed fullscreen" (borderless). In exclusive fullscreen no overlay can
  appear on top.
- The overlay lets your mouse clicks go straight through to the game.
- Turn off "Can appear in the middle of the screen" so the lyrics never cover
  your crosshair.
- It doesn't touch the game: it's just transparent Windows windows, like the
  Discord overlay. Still, there's no official approval from game developers for
  third-party apps; use it at your own risk.

COMMUNITY LOOKS (lyrics.remake.lol)
In Settings > Style, paste a look's code (e.g. STL-JMQZYC) or its link and
click Import. "Shake" and "Void Echoes" are already in "Ready-made styles".
Credits: the "Show the Lyrics" mod is by FireStund; lyrics.remake.lol is its community gallery.

COMMON PROBLEMS
- Lyrics early/late: General > Sync adjustment.
- "No synced lyrics": lrclib doesn't have this song with timestamps.
- Disappears when paused: turn off "Hide when paused".
- Some sites in the browser don't report the song position, so syncing isn't
  possible. Spotify and YouTube work.

Settings are stored in %APPDATA%\LLyrics\config.json.
Fonts come from Google Fonts (SIL Open Font License).
