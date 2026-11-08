# Feelings Wheel

An interactive three-ring feelings wheel drawn with p5.js: 6 core feelings, 36 middle and 72 outer.
You can explore it, color it (colors spread to the feelings they belong to), write notes on a
typewriter-style sheet, and add your own feelings in a fourth ring (Words mode). Everything can be
exported as images, PDF, text or SQLite.

## What's here

```
src/
  feelings-wheel.html      the wheel, written to run inside Claude (claude.ai artifacts)
  typewriter-note.html     the typewriter note field on its own page
dist/
  feelings-wheel-standalone.html   single offline file built from src/ (open it in any browser)
vendor/                    p5.js, jsPDF, sql.js, JSZip, and the Courier Prime fonts, with licenses
build_standalone.py        builds dist/ from src/ + vendor/
tools/embed_fonts.py       re-embeds vendor/fonts/*.ttf into src/feelings-wheel.html
tests/                     browser tests (pytest + Playwright)
```

p5.js is pinned at 1.11.11. Versions 1.11.12 and 1.11.13 throw an error when an off-screen
buffer is removed (`createGraphics(...).remove()`), which the image and PDF exports use. The page
works around it either way, but 1.11.11 avoids it. When upgrading, change the version in
`src/feelings-wheel.html`, `build_standalone.py` and `tests/conftest.py`, and replace `vendor/p5.min.js`.

The sketch (`FeelingsWheel` in `src/feelings-wheel.html`) uses p5's instance mode and only redraws when
something changes. In the browser console, `window.feelingsWheel` gives you the running wheel:
`feelingsWheel.hexOf(1, 4)` is the color Mad is showing, `feelingsWheel.nameOf(3, 56)` is `'Enraged'`.

### Two versions of the wheel

| | `src/feelings-wheel.html` (inside Claude) | `dist/feelings-wheel-standalone.html` |
|---|---|---|
| Libraries | loaded from jsDelivr and cdnjs | bundled in the file |
| Colors | browser storage | SQLite database in the page |
| Notes | Claude's per-account storage (`window.claude.use('db')`) | same SQLite database |
| Saving files | Claude's save prompt (`window.claude.use('downloads')`) | normal browser downloads |
| SQLite export | `.zip` with `feelings-wheel.sqlite` (the save prompt refuses `.sqlite`) | `.sqlite` |

The standalone file keeps its database in the browser's local storage after every change. In Chrome
and Edge it can also be linked to a `.sqlite` file on disk ("Save to a file on this computer…"),
which it rewrites after every change. "Open a database file…" loads any database with the same tables,
including the one inside the Claude version's zip export.

Edit `src/feelings-wheel.html`, then rebuild the standalone file:

```sh
python build_standalone.py
```

`build_standalone.py` is a list of find-and-replace steps applied to the source. If you change code
it patches, it stops with `pattern not found` and shows which piece no longer matches.

## Hosting on GitHub Pages

`.github/workflows/pages.yml` tests every push and pull request. When `main` passes, it builds the
standalone page and publishes it as `index.html` at https://eatxueit.github.io/emotionwheel/.

One-time setup: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

The workflow also checks that the committed `dist/feelings-wheel-standalone.html` matches what
`build_standalone.py` produces, so remember to rebuild and commit it after changing `src/`.

Each visitor's colors, notes and added words stay in their own browser; nothing is sent anywhere.

## Added words (Words mode)

Pick an outer feeling and type a word; it appears in a fourth ring just beyond it, with the path
core › middle › outer › your word. Each outer feeling holds up to 3 added words (`MAX_ADDED` in the
sketch), sharing its slice in the order they were added. Names already on the wheel are refused.
The fourth ring only shows when there are added words, or in Words mode; otherwise the wheel is
exactly the three-ring original. Added words have colors and notes like any other feeling, and
removing one (it asks first) removes its color and note too.

In the sketch an added word is level 4, addressed by its id (a millisecond timestamp, so ids never
collide). `feelingsWheel.added()` lists them; `feelingsWheel.setAdded(list)` replaces them.

## The color rule

A color you pick shows exactly on that feeling. Every feeling above it moves toward it, by how many
rings apart they are: 55% one ring in, 35% two rings in, 20% three rings in (`PULL` in the sketch).
So a color on Enraged pulls Furious 55% and Mad 35%; a color on an added word pulls its outer feeling
55%, its middle feeling 35% and its core 20%. Several picks in one branch combine as
`1 - (1 - p1)(1 - p2)...`, and the color they pull toward is the weighted average of the picks.

## Database tables

```
feelings(id, ring, name, parent_id, core, path, default_color, chosen_color, shown_color, added_at)
notes(feeling_id, text, typed_layout, updated_at)
meta(key, value)
```

`ring` is `core`, `middle`, `outer` or `added`. For the built-in wheel `id` follows wheel order: each
core, then its middle feelings, each followed by its two outer ones (Joyful = 1, Excited = 2,
Energetic = 3, Playful = 4, Cheerful = 5, ...). Added words keep their own id (a large number) and
their `parent_id` is the outer feeling they belong to. Databases saved before added words existed are
upgraded automatically when the standalone page opens them.
`typed_layout` is the note with the sheet's line breaks and tabs expanded.

```sql
SELECT f.path, n.text FROM notes n JOIN feelings f ON f.id = n.feeling_id;
```

## Tests

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
python -m pytest
```

The tests open every page from disk with the network switched off. Requests the Claude version makes
to jsDelivr and cdnjs are answered from `vendor/`. For the Claude version, `tests/claude_stub.js` stands in for
`window.claude`: an in-memory store for notes, a fixed user id, and a downloads object that records
files in `window.__saved` instead of saving them.

- `test_wheel.py`: drawing, selection, the color rule (exact percentages), resize, theme change,
  notes, no-erase, clear, every export from the Claude version, and added words (adding, refusing
  duplicates, the 3-word limit, the 55/35/20 pull, removing, exports, loading saved words)
- `test_typewriter.py`: tab stops, margins, carriage return, the Return key, no erasing, paste, clear, ruler
- `test_standalone.py`: rebuilds `dist/`, then offline font, persistence across reload, all downloads,
  opening and refusing database files, added words in the database, and upgrading an older database

`HEADED=1 python -m pytest` shows the browser; add `SLOWMO=200` to slow it down.

`tests/conftest.py` has a `Wheel` helper that clicks feelings by name
(`wheel.click('Enraged')`, using the sketch's own `centerOf()` so it works with three or four rings),
adds words (`wheel.add_word('Vengeful', beyond='Aggressive')`), picks colors, and reads back what the
sketch shows (`wheel.color_of('Mad')`).

Not covered: the Chrome/Edge linked-file feature (it needs a real file picker), and anything that
depends on how Claude itself hosts the page.

## Licenses

p5.js is LGPL 2.1; jsPDF and sql.js are MIT; JSZip is MIT or GPLv3; Courier Prime is under the
SIL Open Font License 1.1. Their license files are in `vendor/`.
