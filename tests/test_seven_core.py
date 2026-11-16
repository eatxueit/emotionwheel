"""
The 7-core wheel (Happy, Sad, Disgusted, Angry, Fearful, Bad, Surprised), transcribed from the
image the wheel was asked to match, and switching between wheels.
"""
import math
import sqlite3

from conftest import Wheel, mix, rgb, saved_bytes

# clockwise from the top, as in the image
CORES = ['Fearful', 'Angry', 'Disgusted', 'Sad', 'Happy', 'Surprised', 'Bad']
MIDDLE_COUNTS = {'Fearful': 6, 'Angry': 8, 'Disgusted': 4, 'Sad': 6, 'Happy': 9, 'Surprised': 4, 'Bad': 4}


def all_names(w):
    return w.js('''() => { var p = window.feelingsWheel, n = p.counts(), out = {};
        [1, 2, 3].forEach(function (l) { out[l] = []; for (var i = 0; i < n[l]; i++) out[l].push(p.nameOf(l, i)); });
        return out; }''')


def test_new_visitors_get_the_seven_core_wheel(wheel7):
    assert wheel7.sketch('wheelId()') == 'roberts'
    assert wheel7.page.input_value('#wheel-choice') == 'roberts'
    assert wheel7.sketch('counts()') == {'1': 7, '2': 41, '3': 82}


def test_matches_the_image(wheel7):
    names = all_names(wheel7)
    assert names['1'] == CORES
    for core, count in MIDDLE_COUNTS.items():
        c = CORES.index(core)
        assert len(wheel7.sketch('childrenOf(1, %d)' % c)) == count, core
    # every middle feeling has two outer words
    assert all(len(wheel7.sketch('childrenOf(2, %d)' % m)) == 2 for m in range(41))
    # a sample of paths read off the image
    def path(name):
        level, i = wheel7.find(name)
        return wheel7.sketch('pathOf(%d, %d)' % (level, i)) + ' › ' + name
    assert path('Aroused') == 'Happy › Playful › Aroused'
    assert path('Out of control') == 'Bad › Stressed › Out of control'
    assert path('Betrayed') == 'Angry › Let down › Betrayed'
    assert path('Hesitant') == 'Disgusted › Repelled › Hesitant'
    assert path('Isolated') == 'Sad › Lonely › Isolated'
    assert path('Shocked') == 'Surprised › Startled › Shocked'
    assert path('Exposed') == 'Fearful › Threatened › Exposed'
    # words the image uses twice
    assert names['3'].count('Overwhelmed') == 2 and names['3'].count('Inferior') == 2
    assert names['3'].count('Embarrassed') == 2


def test_slices_grow_with_the_number_of_words(wheel7):
    # Happy covers outer feelings 48-65 (18 of 82), so its middle sits at 57 of 82 around the circle
    happy = CORES.index('Happy')
    c = wheel7.sketch('centerOf(1, %d)' % happy)
    size = wheel7.js("parseFloat(document.getElementById('wheel').style.width)")
    angle = math.degrees(math.atan2(c['y'] - size / 2, c['x'] - size / 2))
    expected = -90 + 57 * 360 / 82
    assert abs(((angle - expected + 180) % 360) - 180) < 0.5


def test_clicking_works_on_uneven_slices(wheel7):
    wheel7.mode('color')
    for name, path in (('Disgusted', 'Core feeling'), ('Playful', 'Happy'), ('Hesitant', 'Disgusted › Repelled'),
                       ('Bored', 'Bad'), ('Indifferent', 'Bad › Bored'), ('Helpless', 'Fearful › Scared')):
        wheel7.click(name)
        assert wheel7.page.inner_text('#sel-name') == name
        expected = path if path == 'Core feeling' else path + ' › ' + name
        assert wheel7.page.inner_text('#sel-path') == expected
        wheel7.click(name)    # let go again


def test_color_pull_on_the_seven_core_wheel(wheel7):
    pick = '#1a1a8c'
    starts = {n: wheel7.default_color_of(n) for n in ('Playful', 'Happy')}
    wheel7.mode('color')
    wheel7.click('Aroused')
    wheel7.pick_color(pick)
    for name, pull in (('Playful', 0.55), ('Happy', 0.35)):
        got, want = rgb(wheel7.color_of(name)), mix(starts[name], pick, pull)
        assert all(abs(got[k] - want[k]) <= 2 for k in range(3)), name


def test_each_wheel_keeps_its_own_notes_colors_and_words(wheel7):
    w = wheel7
    w.mode('notes'); w.click('Aroused'); w.type_note('Seven-core note.')
    w.add_word('Lustful', beyond='Aroused')
    w.mode('color'); w.click('Bored'); w.pick_color('#00aa00')
    store = w.js('window.__store')
    aroused = w.find('Aroused')[1]
    assert 'roberts.note-3-%d' % aroused in store
    assert any(k.startswith('roberts.word-') for k in store)

    w.switch_wheel('willcox')
    w.mode('notes')
    assert w.page.inner_text('#note-count') == 'No notes yet'
    assert w.sketch('added().length') == 0
    w.click('Enraged'); w.type_note('Six-core note.')
    assert 'note-3-56' in w.js('window.__store')

    w.switch_wheel('roberts')
    w.mode('notes'); w.click('Aroused')
    assert w.note_text() == 'Seven-core note.'
    assert w.page.inner_text('#note-count') == '1 feeling has a note'
    assert [x['name'] for x in w.sketch('added()')] == ['Lustful']
    assert w.color_of('Bored') == '#00aa00'


def test_existing_six_core_data_stays_on_the_six_core_wheel(context_factory, tmp_path):
    from conftest import artifact_file
    ctx = context_factory(claude=True)
    ctx.add_init_script("window.__store['note-3-56'] = { level: 3, index: 56, text: 'An older note.' };")
    page = ctx.new_page()
    page.goto(artifact_file(tmp_path, 'feelings-wheel.html').as_uri())
    w = Wheel(page); w.wait_ready()
    w.mode('notes')
    page.wait_for_timeout(300)
    assert page.inner_text('#note-count') == 'No notes yet'          # the 7-core wheel starts empty
    w.switch_wheel('willcox')
    w.mode('notes'); w.click('Enraged')
    assert w.note_text() == 'An older note.'


def test_the_choice_is_remembered(wheel7):
    wheel7.switch_wheel('willcox')
    wheel7.page.reload()
    w = Wheel(wheel7.page); w.wait_ready()
    assert w.sketch('wheelId()') == 'willcox'
    assert w.page.input_value('#wheel-choice') == 'willcox'


def test_exports_say_which_wheel(wheel7, tmp_path):
    import io
    import zipfile
    w = wheel7
    w.mode('notes'); w.click('Aroused'); w.type_note('Seven-core note.')
    w.page.click('#all-txt')
    w.page.wait_for_function('window.__saved')
    text = saved_bytes(w.page)[1].decode()
    assert 'Wheel: 7 core feelings' in text and 'Happy > Playful > Aroused' in text

    w.js('window.__saved = null')
    w.page.click('#all-sqlite')
    w.page.wait_for_function('window.__saved', timeout=20000)
    z = zipfile.ZipFile(io.BytesIO(saved_bytes(w.page)[1]))
    path = tmp_path / 'r.sqlite'; path.write_bytes(z.read('feelings-wheel.sqlite'))
    db = sqlite3.connect(path)
    assert db.execute("SELECT value FROM meta WHERE key = 'wheel'").fetchone() == ('roberts',)
    assert db.execute('SELECT COUNT(*) FROM feelings').fetchone() == (130,)
    assert db.execute("SELECT id FROM feelings WHERE name = 'Happy'").fetchone() == (1 + 19 + 25 + 13 + 19,)
