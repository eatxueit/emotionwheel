"""
The Claude version (src/feelings-wheel.html), with Claude's storage and save prompt replaced by
tests/claude_stub.js.
"""
import io
import sqlite3
import zipfile

from conftest import mix, rgb, saved_bytes

CLOSE = 2   # allowed difference per color channel, for rounding


def close_to(actual_hex, expected_rgb):
    a = rgb(actual_hex)
    return all(abs(a[k] - expected_rgb[k]) <= CLOSE for k in range(3))


# ---------------------------------------------------------------- drawing

def test_wheel_draws_all_feelings(wheel):
    assert wheel.js("document.getElementById('wheel').width") > 300
    names = wheel.js('''() => { var p = window.feelingsWheel, out = [];
        [[1,6],[2,36],[3,72]].forEach(function (r) { for (var i = 0; i < r[1]; i++) out.push(p.nameOf(r[0], i)); });
        return out; }''')
    assert len(names) == 114 and len(set(names)) == 114
    assert {'Joyful', 'Powerful', 'Peaceful', 'Sad', 'Mad', 'Scared'} <= set(names)


def test_clicking_selects_and_unselects_a_feeling(wheel):
    wheel.mode('color')
    wheel.click('Embarrassed')
    assert wheel.page.inner_text('#sel-name') == 'Embarrassed'
    assert wheel.page.inner_text('#sel-path') == 'Scared › Embarrassed'
    wheel.click('Embarrassed')          # clicking again lets go
    assert wheel.page.inner_text('#sel-name') == 'Pick a feeling on the wheel'


# ---------------------------------------------------------------- color spreading

def test_a_color_pulls_parent_55_and_grandparent_35_percent(wheel):
    pick = '#1a1a8c'
    furious0, mad0 = wheel.default_color_of('Furious'), wheel.default_color_of('Mad')
    wheel.mode('color')
    wheel.click('Enraged')
    wheel.pick_color(pick)
    assert wheel.color_of('Enraged') == pick
    assert close_to(wheel.color_of('Furious'), mix(furious0, pick, 0.55))
    assert close_to(wheel.color_of('Mad'), mix(mad0, pick, 0.35))


def test_picks_in_the_same_branch_add_up(wheel):
    pick = '#1a1a8c'
    furious0, mad0 = wheel.default_color_of('Furious'), wheel.default_color_of('Mad')
    wheel.mode('color')
    for name in ('Enraged', 'Livid'):
        wheel.click(name)
        wheel.pick_color(pick)
    # two independent 55% pulls: 1 - 0.45 * 0.45 = 0.7975; two 35% pulls on Mad: 1 - 0.65^2 = 0.5775
    assert close_to(wheel.color_of('Furious'), mix(furious0, pick, 1 - 0.45 * 0.45))
    assert close_to(wheel.color_of('Mad'), mix(mad0, pick, 1 - 0.65 * 0.65))


def test_different_picks_blend(wheel):
    blue, green = '#0000ff', '#00ff00'
    mad0 = wheel.default_color_of('Mad')
    wheel.mode('color')
    wheel.click('Enraged'); wheel.pick_color(blue)        # outer: pulls Mad 35%
    wheel.click('Irritated'); wheel.pick_color(green)     # outer, other branch: pulls Mad 35%
    target = '#%02x%02x%02x' % (0, 128, 128)                # equal weights -> halfway between
    assert close_to(wheel.color_of('Mad'), mix(mad0, target, 1 - 0.65 * 0.65))


def test_reset_one_and_all(wheel):
    wheel.mode('color')
    wheel.click('Enraged'); wheel.pick_color('#1a1a8c')
    wheel.click('Calm'); wheel.pick_color('#ff8800')
    wheel.click('Calm'); wheel.click('Calm')              # make sure Calm is the one selected
    wheel.page.click('#reset-one')
    assert wheel.color_of('Calm') == wheel.default_color_of('Calm')
    assert wheel.color_of('Enraged') == '#1a1a8c'
    wheel.page.click('#reset-all')
    assert wheel.color_of('Enraged') == wheel.default_color_of('Enraged')


def test_selection_and_colors_survive_a_resize(wheel):
    wheel.mode('color')
    wheel.click('Enraged'); wheel.pick_color('#1a1a8c')
    wheel.page.set_viewport_size({'width': 620, 'height': 1400})
    wheel.page.wait_for_timeout(600)
    wheel.wait_ready()
    assert wheel.page.inner_text('#sel-name') == 'Enraged'
    assert wheel.color_of('Enraged') == '#1a1a8c'


# ---------------------------------------------------------------- notes

def test_note_saves_to_storage_and_marks_the_feeling(wheel):
    wheel.mode('notes')
    wheel.click('Enraged')
    wheel.page.keyboard.press('Tab')
    wheel.type_note('Traffic on the way to work.')
    store = wheel.js('window.__store')
    level, i = wheel.find('Enraged')
    doc = store['note-%d-%d' % (level, i)]
    assert doc['text'] == '\tTraffic on the way to work.'
    assert wheel.js('window.__dbPath') == 'data/users/test-user'
    assert wheel.sketch('hasNote(%d, %d)' % (level, i)) is True
    assert wheel.page.inner_text('#note-count') == '1 feeling has a note'


def test_note_comes_back_when_the_feeling_is_reopened(wheel):
    wheel.mode('notes')
    wheel.click('Joyful'); wheel.type_note('Saturday mornings.')
    wheel.click('Enraged'); wheel.type_note('Traffic.')
    wheel.click('Joyful')
    assert wheel.note_text() == 'Saturday mornings.'


def test_typewriter_cannot_erase(wheel):
    wheel.mode('notes')
    wheel.click('Enraged')
    wheel.type_note('Hello there')
    for key in ('Backspace', 'Backspace', 'Delete'):
        wheel.page.keyboard.press(key)
    assert wheel.note_text() == 'Hello there'


def test_line_breaks_are_saved_and_exported(wheel):
    wheel.mode('notes')
    wheel.click('Enraged')
    wheel.page.keyboard.type('First line.')
    wheel.page.keyboard.press('Enter')
    wheel.page.keyboard.press('Enter')
    wheel.type_note('After a blank line.')
    level, i = wheel.find('Enraged')
    assert wheel.js('window.__store')['note-%d-%d' % (level, i)]['text'] == 'First line.\n\nAfter a blank line.'
    wheel.page.click('#note-txt')
    wheel.page.wait_for_function('window.__saved')
    name, data = saved_bytes(wheel.page)
    assert data.decode().splitlines()[4:7] == ['First line.', '', 'After a blank line.']


def test_clear_note_asks_first_then_deletes(wheel):
    wheel.mode('notes')
    wheel.click('Enraged')
    wheel.type_note('Hello there')
    wheel.page.click('#note-clear')
    assert wheel.page.is_visible('#note-confirm')
    wheel.page.click('#note-clear-no')
    assert wheel.note_text() == 'Hello there'
    wheel.page.click('#note-clear')
    wheel.page.click('#note-clear-yes')
    wheel.page.wait_for_timeout(300)
    assert wheel.note_text() == ''
    assert wheel.js('Object.keys(window.__store)') == []


# ---------------------------------------------------------------- exports

def test_image_exports_are_2000px(wheel):
    from PIL import Image
    for button, fmt in (('#save-png', 'PNG'), ('#save-jpg', 'JPEG')):
        wheel.page.click(button)
        wheel.page.wait_for_function('window.__saved && window.__saved.dataUrl')
        name, data = saved_bytes(wheel.page)
        img = Image.open(io.BytesIO(data))
        assert img.format == fmt and img.size == (2000, 2000)
        wheel.js('window.__saved = null')


def test_note_exports_as_text_and_pdf(wheel):
    wheel.mode('notes')
    wheel.click('Enraged')
    wheel.page.keyboard.press('Tab')
    wheel.type_note('The drive in was the same as always, and still I was gripping the wheel.')
    wheel.page.click('#note-txt')
    wheel.page.wait_for_function('window.__saved')
    name, data = saved_bytes(wheel.page)
    lines = data.decode().splitlines()
    assert name == 'enraged-note.txt'
    assert lines[:2] == ['ENRAGED', 'Mad > Furious > Enraged']
    assert all(len(l) <= 52 for l in lines[4:])
    assert lines[4].startswith('     The drive')        # the tab became 5 columns

    wheel.js('window.__saved = null')
    wheel.page.click('#note-pdf')
    wheel.page.wait_for_function('window.__saved')
    name, data = saved_bytes(wheel.page)
    assert name == 'enraged-note.pdf' and data.startswith(b'%PDF')
    assert b'CourierPrime' in data                      # the sheet's font is embedded


def test_export_everything_as_sqlite(wheel, tmp_path):
    wheel.mode('color')
    wheel.click('Enraged'); wheel.pick_color('#1a1a8c')
    wheel.mode('notes')
    wheel.click('Joyful'); wheel.type_note('Saturday mornings.')
    wheel.page.click('#all-sqlite')
    wheel.page.wait_for_function('window.__saved', timeout=20000)
    name, data = saved_bytes(wheel.page)
    assert name.endswith('.zip')
    z = zipfile.ZipFile(io.BytesIO(data))
    assert set(z.namelist()) == {'feelings-wheel.sqlite', 'README.txt'}
    db_path = tmp_path / 'out.sqlite'
    db_path.write_bytes(z.read('feelings-wheel.sqlite'))
    db = sqlite3.connect(db_path)
    assert db.execute('SELECT COUNT(*) FROM feelings').fetchone() == (114,)
    assert db.execute("SELECT chosen_color FROM feelings WHERE name = 'Enraged'").fetchone() == ('#1a1a8c',)
    assert db.execute('''SELECT p.name FROM feelings f JOIN feelings p ON p.id = f.parent_id
                         WHERE f.name = 'Enraged' ''').fetchone() == ('Furious',)
    assert db.execute('''SELECT f.name, n.text FROM notes n JOIN feelings f ON f.id = n.feeling_id''').fetchall() \
        == [('Joyful', 'Saturday mornings.')]


def test_export_everything_as_text_and_pdf(wheel):
    wheel.mode('notes')
    wheel.click('Enraged'); wheel.type_note('Traffic.')
    wheel.page.click('#all-txt')
    wheel.page.wait_for_function('window.__saved')
    name, data = saved_bytes(wheel.page)
    text = data.decode()
    assert name.endswith('.txt') and 'NOTES (1)' in text and 'Traffic.' in text

    wheel.js('window.__saved = null')
    wheel.page.click('#all-pdf')
    wheel.page.wait_for_function('window.__saved', timeout=20000)
    name, data = saved_bytes(wheel.page)
    assert name.endswith('.pdf') and data.startswith(b'%PDF')


def test_theme_change_redraws_without_losing_state(wheel):
    wheel.mode('color')
    wheel.click('Enraged'); wheel.pick_color('#1a1a8c')
    corner = "(() => { var c = document.getElementById('wheel'); return Array.from(c.getContext('2d').getImageData(2, 2, 1, 1).data.slice(0, 3)); })()"
    light = wheel.js(corner)
    wheel.js("document.documentElement.setAttribute('data-theme', 'dark')")
    wheel.page.wait_for_function(corner.replace('return Array', 'var d = Array').replace(".slice(0, 3)); })()", ".slice(0, 3)); return d[0] < 60; })()"))
    dark = wheel.js(corner)
    assert light[0] > 200 and dark[0] < 60          # the background follows the theme
    assert wheel.page.inner_text('#sel-name') == 'Enraged'
    assert wheel.color_of('Enraged') == '#1a1a8c'


# ---------------------------------------------------------------- words you add (a fourth ring)

def test_add_a_word_beyond_an_outer_feeling(wheel):
    wheel.add_word('vengeful', beyond='Aggressive')
    level, i = wheel.find('Vengeful')                     # first letter capitalized
    assert level == 4
    assert wheel.sketch('pathOf(4, %d)' % i) == 'Mad › Hostile › Aggressive'
    assert 'Added Vengeful beyond Aggressive' in wheel.page.inner_text('#word-msg')
    doc = wheel.js('window.__store')['word-%d' % i]
    assert doc['name'] == 'Vengeful' and doc['parent'] == wheel.find('Aggressive')[1]
    # the new word sits further out than the outer ring
    outer = wheel.sketch('centerOf(3, %d)' % wheel.find('Aggressive')[1])
    added = wheel.sketch('centerOf(4, %d)' % i)
    size = wheel.js("parseFloat(document.getElementById('wheel').style.width)")
    dist = lambda c: ((c['x'] - size / 2) ** 2 + (c['y'] - size / 2) ** 2) ** 0.5
    assert dist(added) > dist(outer)


def test_added_word_can_be_selected_on_the_wheel(wheel):
    wheel.add_word('Vengeful', beyond='Aggressive')
    wheel.mode('explore'); wheel.mode('color')
    wheel.click('Vengeful')
    assert wheel.page.inner_text('#sel-name') == 'Vengeful'
    assert wheel.page.inner_text('#sel-path') == 'Mad › Hostile › Aggressive › Vengeful'


def test_added_word_color_pulls_three_rings(wheel):
    from conftest import mix, rgb
    pick = '#1a1a8c'
    wheel.add_word('Vengeful', beyond='Aggressive')
    starts = {n: wheel.default_color_of(n) for n in ('Aggressive', 'Hostile', 'Mad')}
    wheel.mode('color')
    wheel.click('Vengeful')
    wheel.pick_color(pick)
    for name, pull in (('Aggressive', 0.55), ('Hostile', 0.35), ('Mad', 0.20)):
        got, want = rgb(wheel.color_of(name)), mix(starts[name], pick, pull)
        assert all(abs(got[k] - want[k]) <= 2 for k in range(3)), (name, got, want)


def test_names_already_on_the_wheel_are_refused(wheel):
    wheel.add_word('calm', beyond='Aggressive')
    assert wheel.page.inner_text('#word-msg') == 'Calm is already on the wheel.'
    wheel.page.fill('#word-input', 'Vengeful'); wheel.page.click('#word-add')
    wheel.click('Provoked')
    wheel.page.fill('#word-input', 'vengeful'); wheel.page.click('#word-add')
    assert wheel.page.inner_text('#word-msg') == 'Vengeful is already on the wheel.'


def test_at_most_three_words_per_outer_feeling(wheel):
    for name in ('Vengeful', 'Spiteful', 'Destructive'):
        wheel.add_word(name, beyond='Aggressive')
    wheel.click('Aggressive'); wheel.click('Aggressive')    # reselect to refresh the panel
    if wheel.page.inner_text('#word-name') != 'Aggressive':
        wheel.click('Aggressive')
    assert wheel.page.is_disabled('#word-input')
    assert 'the most it can hold' in wheel.page.inner_text('#word-msg')
    assert wheel.page.inner_text('#word-list').split() == ['Vengeful', 'Spiteful', 'Destructive']


def test_choosing_a_middle_or_core_feeling_explains_where_words_go(wheel):
    wheel.mode('words')
    wheel.click('Hostile')
    assert wheel.page.is_hidden('#word-form')
    assert 'outer ring' in wheel.page.inner_text('#word-msg')


def test_removing_a_word_asks_first_and_takes_its_note_and_color(wheel):
    wheel.add_word('Vengeful', beyond='Aggressive')
    level, i = wheel.find('Vengeful')
    wheel.mode('color'); wheel.click('Vengeful'); wheel.pick_color('#1a1a8c')
    wheel.mode('notes'); wheel.click('Vengeful'); wheel.type_note('Wanted to get back at him.')
    assert 'note-4-%d' % i in wheel.js('window.__store')

    wheel.mode('words'); wheel.click('Vengeful')
    wheel.page.click('#word-remove-btn')
    assert wheel.page.inner_text('#word-confirm-text') == 'Remove Vengeful? Its color and note will be removed too.'
    wheel.page.click('#word-confirm-no')
    assert wheel.sketch('added().length') == 1
    wheel.page.click('#word-remove-btn')
    wheel.page.click('#word-confirm-yes')
    wheel.page.wait_for_timeout(200)
    assert wheel.sketch('added().length') == 0
    assert set(wheel.js('Object.keys(window.__store)')) == set()
    assert wheel.color_of('Aggressive') == wheel.default_color_of('Aggressive')
    assert wheel.page.inner_text('#word-msg') == 'Removed Vengeful.'


def test_added_words_are_in_every_export(wheel, tmp_path):
    wheel.add_word('Vengeful', beyond='Aggressive')
    wheel.mode('notes'); wheel.click('Vengeful'); wheel.type_note('Wanted to get back at him.')

    wheel.page.click('#all-txt')
    wheel.page.wait_for_function('window.__saved')
    text = saved_bytes(wheel.page)[1].decode()
    assert 'Mad > Hostile > Aggressive > Vengeful' in text and 'Wanted to get back at him.' in text

    wheel.js('window.__saved = null')
    wheel.page.click('#all-sqlite')
    wheel.page.wait_for_function('window.__saved', timeout=20000)
    z = zipfile.ZipFile(io.BytesIO(saved_bytes(wheel.page)[1]))
    path = tmp_path / 'w.sqlite'; path.write_bytes(z.read('feelings-wheel.sqlite'))
    db = sqlite3.connect(path)
    row = db.execute('''SELECT f.ring, p.name, f.path, f.added_at IS NOT NULL, n.text
                        FROM feelings f JOIN feelings p ON p.id = f.parent_id
                        LEFT JOIN notes n ON n.feeling_id = f.id WHERE f.name = 'Vengeful' ''').fetchone()
    assert row == ('added', 'Aggressive', 'Mad > Hostile > Aggressive > Vengeful', 1, 'Wanted to get back at him.')
    # built-in feelings keep the same ids whether or not words were added
    assert db.execute("SELECT id FROM feelings WHERE name = 'Mad'").fetchone() == (77,)
    assert db.execute('SELECT COUNT(*) FROM feelings').fetchone() == (115,)


def test_saved_words_come_back_when_the_page_opens(context_factory, tmp_path):
    from conftest import Wheel, artifact_file
    ctx = context_factory(claude=True)
    ctx.add_init_script("""window.__store['word-1700000000000'] =
        { id: 1700000000000, name: 'Lustful', parent: 8, addedAt: '2026-11-01T10:00:00Z' };""")
    page = ctx.new_page()
    page.goto(artifact_file(tmp_path, 'feelings-wheel.html').as_uri())
    w = Wheel(page); w.wait_ready()
    page.wait_for_function('window.feelingsWheel.added().length === 1')
    assert w.sketch('pathOf(4, 1700000000000)') == 'Joyful › Sensuous › Stimulated'
    w.mode('color'); w.click('Lustful')
    assert page.inner_text('#sel-name') == 'Lustful'
