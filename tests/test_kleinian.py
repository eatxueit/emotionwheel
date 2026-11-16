"""
The Kleinian wheel (Envy, Jealousy, Love, Gratitude, Hate), taken from a hand drawing: five feelings
with the drawing's slice sizes and colors. Words you add grow it, ring by ring, up to four rings.
"""
import io
import math
import sqlite3
import zipfile

import pytest

from conftest import mix, rgb, saved_bytes

CORES = ['Envy', 'Jealousy', 'Love', 'Gratitude', 'Hate']
WEIGHTS = [14, 13, 24, 17, 32]
COLORS = ['#840c15', '#df2445', '#ff9909', '#16143a', '#13261a']
START_DEG = -14


@pytest.fixture
def klein(wheel7):
    wheel7.switch_wheel('klein')
    return wheel7


def angle_of(w, level, i):
    c = w.sketch('centerOf(%d, %d)' % (level, i))
    size = w.js("parseFloat(document.getElementById('wheel').style.width)")
    return math.degrees(math.atan2(c['y'] - size / 2, c['x'] - size / 2)) + 90   # clockwise from the top


def close_deg(a, b, tol=0.5):
    return abs(((a - b + 180) % 360) - 180) < tol


def test_it_is_in_the_wheel_choice(wheel7):
    labels = wheel7.page.eval_on_selector_all('#wheel-choice option', 'os => os.map(o => o.textContent)')
    assert 'Kleinian (Envy, Jealousy, Love…)' in labels


def test_five_feelings_as_drawn(klein):
    assert klein.sketch('counts()') == {'1': 5, '2': 0, '3': 0}
    assert [klein.sketch('nameOf(1, %d)' % i) for i in range(5)] == CORES
    assert [klein.sketch('defaultHexOf(1, %d)' % i) for i in range(5)] == COLORS
    assert klein.sketch('ringsShown()') == 1


def test_slices_keep_the_drawn_sizes(klein):
    at = 0
    for i, wgt in enumerate(WEIGHTS):
        middle = START_DEG + (at + wgt / 2) * 3.6
        assert close_deg(angle_of(klein, 1, i), middle), CORES[i]
        at += wgt


def test_clicking_each_feeling(klein):
    klein.mode('color')
    for name in CORES:
        klein.click(name)
        assert klein.page.inner_text('#sel-name') == name
        assert klein.page.inner_text('#sel-path') == 'Core feeling'
        klein.click(name)


def test_words_grow_new_rings(klein):
    klein.add_word('Spoiling', beyond='Envy')
    assert klein.sketch('ringOf(4, %d)' % klein.find('Spoiling')[1]) == 2
    klein.add_word('Begrudging', beyond='Spoiling')
    klein.add_word('Contempt', beyond='Begrudging')
    level, i = klein.find('Contempt')
    assert klein.sketch('ringOf(4, %d)' % i) == 4
    assert klein.sketch('pathOf(4, %d)' % i) == 'Envy › Spoiling › Begrudging'
    klein.mode('explore')
    assert klein.sketch('ringsShown()') == 4
    # the fourth ring is the last: nothing can go beyond Contempt
    klein.mode('words'); klein.click('Contempt')
    assert klein.page.is_hidden('#word-form')
    assert 'holds four rings' in klein.page.inner_text('#word-msg')


def test_a_wide_slice_holds_more_than_three_words(klein):
    for name in ('Spoiling', 'Begrudging', 'Greed', 'Rivalry', 'Coveting'):
        klein.add_word(name, beyond='Envy')
    assert len(klein.sketch('addedUnder(1, 0)')) == 5
    assert klein.sketch('maxAddedBeneath(1, 0)') > 5


def test_color_pull_follows_rings(klein):
    pick = '#1a1a8c'
    klein.add_word('Reparation', beyond='Gratitude')
    klein.add_word('Generosity', beyond='Reparation')
    start_rep = klein.default_color_of('Reparation')
    start_grat = klein.default_color_of('Gratitude')
    klein.mode('color'); klein.click('Generosity'); klein.pick_color(pick)
    for name, start, pull in (('Reparation', start_rep, 0.55), ('Gratitude', start_grat, 0.35)):
        got, want = rgb(klein.color_of(name)), mix(start, pick, pull)
        assert all(abs(got[k] - want[k]) <= 2 for k in range(3)), name


def test_removing_a_word_takes_the_words_beyond_it(klein):
    klein.add_word('Spoiling', beyond='Envy')
    klein.add_word('Begrudging', beyond='Spoiling')
    klein.mode('notes'); klein.click('Begrudging'); klein.type_note('A note further out.')
    assert any(k.startswith('klein.note-4-') for k in klein.js('window.__store'))

    klein.mode('words'); klein.click('Spoiling')
    klein.page.click('#word-remove-btn')
    assert klein.page.inner_text('#word-confirm-text') == \
        'Remove Spoiling? The word added beyond it will go too, with their colors and notes.'
    klein.page.click('#word-confirm-yes')
    klein.page.wait_for_timeout(200)
    assert klein.sketch('added().length') == 0
    assert klein.js('Object.keys(window.__store)') == []
    assert klein.page.inner_text('#word-msg') == 'Removed Spoiling and the word beyond it.'


def test_saved_words_keep_their_place_and_path(klein):
    klein.add_word('Spoiling', beyond='Envy')
    klein.add_word('Begrudging', beyond='Spoiling')
    store = klein.js('window.__store')
    docs = {d['name']: d for k, d in store.items() if k.startswith('klein.word-')}
    assert docs['Spoiling']['parentKey'] == '1:0' and docs['Spoiling']['path'] == 'Envy › Spoiling'
    assert docs['Begrudging']['parentKey'] == '4:%d' % docs['Spoiling']['id']
    assert docs['Begrudging']['path'] == 'Envy › Spoiling › Begrudging'
    klein.mode('notes'); klein.click('Begrudging'); klein.type_note('A note.')
    note = [d for k, d in klein.js('window.__store').items() if k.startswith('klein.note-')][0]
    assert note['feeling'] == 'Envy > Spoiling > Begrudging'


def test_exports(klein, tmp_path):
    klein.add_word('Spoiling', beyond='Envy')
    klein.add_word('Begrudging', beyond='Spoiling')
    klein.mode('notes'); klein.click('Begrudging'); klein.type_note('A note.')
    klein.page.click('#all-txt')
    klein.page.wait_for_function('window.__saved')
    text = saved_bytes(klein.page)[1].decode()
    assert 'Wheel: Kleinian' in text and 'Envy > Spoiling > Begrudging' in text

    klein.js('window.__saved = null')
    klein.page.click('#all-sqlite')
    klein.page.wait_for_function('window.__saved', timeout=20000)
    z = zipfile.ZipFile(io.BytesIO(saved_bytes(klein.page)[1]))
    path = tmp_path / 'k.sqlite'
    path.write_bytes(z.read('feelings-wheel.sqlite'))
    db = sqlite3.connect(path)
    assert db.execute("SELECT value FROM meta WHERE key = 'wheel'").fetchone() == ('klein',)
    assert db.execute("SELECT id, name FROM feelings WHERE ring = 'core' ORDER BY id").fetchall() == \
        [(1, 'Envy'), (2, 'Jealousy'), (3, 'Love'), (4, 'Gratitude'), (5, 'Hate')]
    rows = db.execute('''SELECT f.name, p.name FROM feelings f JOIN feelings p ON p.id = f.parent_id
                         WHERE f.ring = 'added' ORDER BY f.id''').fetchall()
    assert rows == [('Spoiling', 'Envy'), ('Begrudging', 'Spoiling')]

    klein.js('window.__saved = null')
    klein.page.click('#save-png')
    klein.page.wait_for_function('window.__saved && window.__saved.dataUrl')
    from PIL import Image
    assert Image.open(io.BytesIO(saved_bytes(klein.page)[1])).size == (2000, 2000)
