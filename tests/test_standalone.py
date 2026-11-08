"""
The single-file standalone build (dist/feelings-wheel-standalone.html), opened from disk
with the network off. The build is regenerated at the start of the test run.
"""
import sqlite3

from conftest import Wheel


def download(page, selector, tmp_path):
    with page.expect_download() as d:
        page.click(selector)
    path = tmp_path / d.value.suggested_filename
    d.value.save_as(path)
    return path


def test_works_offline_with_its_own_font(standalone):
    assert standalone.page.inner_text('#store-state') == 'Saving in this browser'
    assert standalone.js('''document.fonts.check('italic 16px "Courier Prime"')''') is True
    assert standalone.js('typeof window.claude') == 'undefined'


def test_colors_and_notes_survive_a_reload(standalone):
    w = standalone
    w.mode('color')
    w.click('Enraged'); w.pick_color('#1a1a8c')
    w.mode('notes')
    w.click('Enraged')
    w.page.keyboard.press('Tab')
    w.type_note('Traffic again.')
    assert w.page.inner_text('#note-status') == 'Saved in this browser'
    w.page.wait_for_timeout(600)

    w.page.reload()
    w = Wheel(w.page); w.wait_ready()
    w.page.wait_for_function("document.getElementById('store-state').textContent === 'Saving in this browser'")
    w.mode('notes')
    w.click('Enraged')
    assert w.note_text() == '\tTraffic again.'
    assert w.color_of('Enraged') == '#1a1a8c'


def test_sqlite_export_is_the_live_database(standalone, tmp_path):
    w = standalone
    w.mode('color'); w.click('Calm'); w.pick_color('#ff8800')
    w.mode('notes'); w.click('Joyful'); w.type_note('Saturday mornings.')
    path = download(w.page, '#all-sqlite', tmp_path)
    assert path.suffix == '.sqlite'
    db = sqlite3.connect(path)
    assert db.execute('SELECT COUNT(*) FROM feelings').fetchone() == (114,)
    assert db.execute("SELECT chosen_color FROM feelings WHERE name = 'Calm'").fetchone() == ('#ff8800',)
    assert db.execute("SELECT f.name, n.text FROM notes n JOIN feelings f ON f.id = n.feeling_id").fetchall() \
        == [('Joyful', 'Saturday mornings.')]
    # shown_color holds what the wheel displayed, including the pull on Calm's parent
    relaxed = db.execute("SELECT shown_color, default_color FROM feelings WHERE name = 'Relaxed'").fetchone()
    assert relaxed[0] != relaxed[1]


def test_all_downloads(standalone, tmp_path):
    w = standalone
    w.mode('notes'); w.click('Enraged'); w.type_note('Traffic.')
    expected = {'#save-png': '.png', '#save-jpg': '.jpg', '#note-pdf': '.pdf', '#note-txt': '.txt',
                '#all-pdf': '.pdf', '#all-txt': '.txt', '#all-sqlite': '.sqlite'}
    for selector, suffix in expected.items():
        path = download(w.page, selector, tmp_path)
        assert path.suffix == suffix and path.stat().st_size > 0, selector


def test_opening_a_database_file_asks_then_replaces(standalone, tmp_path):
    w = standalone
    w.mode('notes'); w.click('Enraged'); w.type_note('Current note.')
    exported = download(w.page, '#all-sqlite', tmp_path)

    # change the file outside the page, the way you might with the sqlite3 command
    db = sqlite3.connect(exported)
    db.execute("UPDATE feelings SET chosen_color = '#ff8800' WHERE name = 'Calm'")
    db.execute("DELETE FROM notes")
    db.execute("INSERT INTO notes (feeling_id, text, typed_layout) "
               "SELECT id, 'Written in sqlite3.', 'Written in sqlite3.' FROM feelings WHERE name = 'Sad'")
    db.commit(); db.close()

    w.page.click('#store-open')
    w.page.set_input_files('#store-file', str(exported))
    w.page.wait_for_selector('#store-confirm', state='visible')
    w.page.click('#store-confirm-yes')
    w.page.wait_for_function("document.getElementById('store-msg').textContent.startsWith('Opened')")
    assert w.color_of('Calm') == '#ff8800'
    w.click('Sad')
    assert w.note_text() == 'Written in sqlite3.'
    assert w.page.inner_text('#note-count') == '1 feeling has a note'


def test_cancelled_open_changes_nothing(standalone, tmp_path):
    w = standalone
    w.mode('notes'); w.click('Enraged'); w.type_note('Keep me.')
    exported = download(w.page, '#all-sqlite', tmp_path)
    w.page.click('#store-open')
    w.page.set_input_files('#store-file', str(exported))
    w.page.wait_for_selector('#store-confirm', state='visible')
    w.page.click('#store-confirm-no')
    assert not w.page.is_visible('#store-confirm')
    w.click('Enraged'); w.click('Enraged')
    assert w.note_text() == 'Keep me.'


def test_a_file_that_is_not_a_wheel_database_is_refused(standalone, tmp_path):
    other = tmp_path / 'other.sqlite'
    db = sqlite3.connect(other); db.execute('CREATE TABLE x (y)'); db.commit(); db.close()
    standalone.page.click('#store-open')
    standalone.page.set_input_files('#store-file', str(other))
    standalone.page.wait_for_function("document.getElementById('store-msg').textContent !== ''")
    assert 'is not a feelings wheel database' in standalone.page.inner_text('#store-msg')


# ---------------------------------------------------------------- words you add

def test_added_words_are_saved_in_the_database(standalone, tmp_path):
    w = standalone
    w.add_word('Vengeful', beyond='Aggressive')
    w.mode('notes'); w.click('Vengeful'); w.type_note('Wanted to get back at him.')
    w.page.wait_for_timeout(600)

    w.page.reload()
    w = Wheel(w.page); w.wait_ready()
    w.page.wait_for_function('window.feelingsWheel.added().length === 1')
    w.mode('notes'); w.click('Vengeful')
    assert w.note_text() == 'Wanted to get back at him.'

    db = sqlite3.connect(download(w.page, '#all-sqlite', tmp_path))
    assert db.execute('''SELECT f.ring, p.name FROM feelings f JOIN feelings p ON p.id = f.parent_id
                         WHERE f.name = 'Vengeful' ''').fetchone() == ('added', 'Aggressive')


def test_removing_a_word_deletes_it_from_the_database(standalone, tmp_path):
    w = standalone
    w.add_word('Vengeful', beyond='Aggressive')
    w.mode('notes'); w.click('Vengeful'); w.type_note('Gone soon.')
    w.mode('words'); w.click('Vengeful')
    w.page.click('#word-remove-btn'); w.page.click('#word-confirm-yes')
    db = sqlite3.connect(download(w.page, '#all-sqlite', tmp_path))
    assert db.execute("SELECT COUNT(*) FROM feelings WHERE ring = 'added'").fetchone() == (0,)
    assert db.execute('SELECT COUNT(*) FROM notes').fetchone() == (0,)


OLD_FEELINGS = """CREATE TABLE feelings (id INTEGER PRIMARY KEY,
  ring TEXT NOT NULL CHECK (ring IN ('core','middle','outer')), name TEXT NOT NULL,
  parent_id INTEGER REFERENCES feelings(id), core TEXT NOT NULL, path TEXT NOT NULL,
  default_color TEXT NOT NULL, chosen_color TEXT, shown_color TEXT NOT NULL)"""


def test_a_database_from_before_added_words_is_upgraded(standalone, tmp_path):
    # export the current database, then rebuild it with the old feelings table
    w = standalone
    w.mode('notes'); w.click('Sad'); w.type_note('An old note.')
    path = download(w.page, '#all-sqlite', tmp_path)
    db = sqlite3.connect(path)
    db.executescript('ALTER TABLE feelings RENAME TO f2;' + OLD_FEELINGS + ';'
                     'INSERT INTO feelings SELECT id, ring, name, parent_id, core, path, default_color, '
                     'chosen_color, shown_color FROM f2; DROP TABLE f2;')
    db.commit(); db.close()

    w.page.click('#store-open')
    w.page.set_input_files('#store-file', str(path))
    w.page.wait_for_selector('#store-confirm', state='visible')
    w.page.click('#store-confirm-yes')
    w.page.wait_for_function("document.getElementById('store-msg').textContent.startsWith('Opened')")
    w.add_word('Vengeful', beyond='Aggressive')

    db = sqlite3.connect(download(w.page, '#all-sqlite', tmp_path))
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name = 'feelings'").fetchone()[0]
    assert "'added'" in sql and 'added_at' in sql
    assert db.execute("SELECT COUNT(*) FROM feelings WHERE ring = 'added'").fetchone() == (1,)
    assert db.execute("SELECT n.text FROM notes n JOIN feelings f ON f.id = n.feeling_id").fetchall() \
        == [('An old note.',)]
