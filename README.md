# Feelings Wheel

An interactive feelings wheel drawn with p5.js, in three versions you can switch between:

- **7 core feelings** (Happy, Sad, Disgusted, Angry, Fearful, Bad, Surprised): 41 middle and 82 outer,
  130 words, the wheel commonly credited to Geoffrey Roberts. This is the default.
- **6 core feelings** (Joyful, Powerful, Peaceful, Sad, Mad, Scared): 36 middle and 72 outer,
  114 words, after Gloria Willcox's Feeling Wheel.
- **Kleinian** (Envy, Jealousy, Love, Gratitude, Hate), after Melanie Klein: five feelings only,
  taken from a hand drawing with its slice sizes (Hate 32%, Love 24%, Gratitude 17%, Envy 14%,
  Jealousy 13%) and colors. It grows as you add your own words beneath the five.

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

## The two wheels

All three are defined as data in the sketch (`FeelingsWheel.WHEELS` in `src/feelings-wheel.html`):
each core feeling has a name, a color, a list of middle feelings (each with its outer words) and
optionally a weight. Without weights every outer word gets the same width, so a core feeling's slice
grows with its number of words (Happy covers 18 of the 7-core wheel's 82 outer words, Bad 8). With
weights, as in the Kleinian wheel, each core's slice is its share of the total. `startDeg` rotates a
wheel. To add another wheel, add an entry there.

The wheel picker is remembered per browser. Each wheel keeps its own colors, notes and added words:
the 6-core wheel's data keeps the storage names it had before there was a choice (so older data
is still there), and the 7-core wheel's are prefixed with `roberts` (`roberts.note-3-40` in
Claude's storage, `feelings-wheel-picks:roberts` in the browser). The standalone file keeps one
SQLite database per wheel, and its `meta` table records which (`wheel = roberts` or `willcox`;
databases from before there was a choice count as `willcox`). Opening another wheel's database
offers to switch to that wheel.

## Added words (Words mode)

Pick a feeling on the outermost ring and type a word; it appears in a new ring just beyond it. Words
can go beneath any feeling that has no built-in feelings beneath it (the outer ring of the 6- and
7-core wheels, the five feelings of the Kleinian wheel) and beneath other added words, up to four
rings in all. A feeling's added words share its slice in the order they were added; how many fit
depends on the slice's width (3 beneath an outer feeling of the 6- or 7-core wheel, up to 12 beneath
a wide slice). Names already on the wheel are refused. The wheel shows only the rings it needs, plus
one more in Words mode. Added words have colors and notes like any other feeling; removing one (it
asks first) removes the words beneath it too, with their colors and notes.

In the sketch an added word is level 4, addressed by its id (a millisecond timestamp, so ids never
collide), and hangs beneath a parent key: `'3:40'` (an outer feeling), `'1:2'` (a core) or
`'4:<id>'` (another added word). `feelingsWheel.added()` lists them; `feelingsWheel.setAdded(list)`
replaces them. Saved words record their parent key and their full path by name, and saved notes
record the feeling's path, so if a wheel is ever rearranged, saved data can be matched to the right
feelings by name.

## The color rule

A color you pick shows exactly on that feeling. Every feeling above it moves toward it, by how many
rings apart they are: 55% one ring in, 35% two rings in, 20% three rings in (`PULL` in the sketch).
So a color on Enraged pulls Furious 55% and Mad 35%; a color on an added word pulls its outer feeling
55%, its middle feeling 35% and its core 20%. On the Kleinian wheel the same rule follows your added
rings. Several picks in one branch combine as
`1 - (1 - p1)(1 - p2)...`, and the color they pull toward is the weighted average of the picks.

## Database tables

```
feelings(id, ring, name, parent_id, core, path, default_color, chosen_color, shown_color, added_at)
notes(feeling_id, text, typed_layout, updated_at)
meta(key, value)
```

`ring` is `core`, `middle`, `outer` or `added`. For the wheel's own feelings `id` follows wheel
order: each core, then its middle feelings, each followed by its outer ones, so the 6-core wheel
runs 1-114 (Joyful = 1, Excited = 2, Energetic = 3, Playful = 4, Cheerful = 5, ...) and the 7-core
wheel 1-130 (Fearful = 1, Scared = 2, Helpless = 3, ...). Added words keep their own id (a large number) and
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
- `test_seven_core.py`: the 7-core wheel against the image it was transcribed from (every core,
  branch sizes, sample paths, repeated words, slice sizes), clicking uneven slices, the color pull,
  each wheel keeping its own data, older data staying on the 6-core wheel, the remembered choice,
  and exports naming the wheel
- `test_kleinian.py`: the Kleinian wheel against the drawing (order, colors, slice sizes), clicking,
  growing rings by adding words up to the fourth, wide slices holding more words, the color pull
  through added rings, removing a word with the words beyond it, what gets saved, and exports
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
