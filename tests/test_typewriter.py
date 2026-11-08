"""
The typewriter note on its own page (src/typewriter-note.html), driven through the
TypewriterBox component it exposes as window.box.
"""


def lines(page):
    """The sheet as plain text lines, exactly as laid out (tabs expanded, trailing spaces kept)."""
    return page.evaluate('''() => box._layout().lines.map(l => l.map(g => g.c).join(''))''')


def set_text(page, text):
    page.evaluate('t => { box.value = t; }', text)


def test_tab_jumps_to_the_next_stop_every_5_columns(typewriter_page):
    set_text(typewriter_page, 'ab\tc\t\td')
    assert lines(typewriter_page) == ['ab   c         d']


def test_words_never_cross_the_right_margin(typewriter_page):
    set_text(typewriter_page, ' '.join(['margin'] * 30))
    out = lines(typewriter_page)
    assert len(out) > 1
    assert all(len(l) <= 52 for l in out)
    assert all(not l.startswith('argin') for l in out)     # no word split across lines


def test_space_at_the_margin_returns_the_carriage(typewriter_page):
    para = 'x' * 50
    set_text(typewriter_page, para + ' ' * 3 + 'next')       # 2 spaces fill the line, the 3rd returns
    assert lines(typewriter_page) == [para + '  ', 'next']


def test_a_word_longer_than_a_line_breaks_at_the_margin(typewriter_page):
    set_text(typewriter_page, 'y' * 60)
    assert lines(typewriter_page) == ['y' * 52, 'y' * 8]


def test_return_starts_a_new_line(typewriter_page):
    page = typewriter_page
    set_text(page, '')
    page.click('.tw-sheet')
    page.keyboard.type('one')
    page.keyboard.press('Enter')
    page.keyboard.type('two')
    assert page.evaluate('box.value') == 'one\ntwo'
    assert lines(page) == ['one', 'two']
    assert page.inner_text('.tw-status .pos').startswith('Line 2 · Column 4')


def test_return_twice_leaves_a_blank_line(typewriter_page):
    page = typewriter_page
    set_text(page, '')
    page.click('.tw-sheet')
    page.keyboard.type('one')
    page.keyboard.press('Enter')
    page.keyboard.press('Enter')
    page.keyboard.type('two')
    assert lines(page) == ['one', '', 'two']


def test_return_on_a_full_line_still_moves_down(typewriter_page):
    # a full line has already sent the caret to the next line, so Return moves one further
    set_text(typewriter_page, 'x' * 52 + '\n' + 'y')
    assert lines(typewriter_page) == ['x' * 52, '', 'y']


def test_return_cannot_be_erased(typewriter_page):
    page = typewriter_page
    set_text(page, '')
    page.click('.tw-sheet')
    page.keyboard.type('one')
    page.keyboard.press('Enter')
    page.keyboard.press('Backspace')
    page.keyboard.type('two')
    assert page.evaluate('box.value') == 'one\ntwo'


def test_a_new_line_resets_word_wrapping(typewriter_page):
    set_text(typewriter_page, 'a\n' + ' '.join(['margin'] * 9))
    out = lines(typewriter_page)
    assert out[0] == 'a'
    assert out[1].startswith('margin margin') and len(out[1]) <= 52


def test_backspace_and_delete_do_not_erase(typewriter_page):
    page = typewriter_page
    set_text(page, '')
    page.click('.tw-sheet')
    page.keyboard.type('kept')
    for key in ('Backspace', 'Delete', 'Backspace'):
        page.keyboard.press(key)
    assert page.evaluate('box.value') == 'kept'


def test_arrow_keys_do_not_move_back_into_the_text(typewriter_page):
    page = typewriter_page
    set_text(page, '')
    page.click('.tw-sheet')
    page.keyboard.type('abc')
    page.keyboard.press('ArrowLeft')
    page.keyboard.press('Home')
    page.keyboard.type('d')
    assert page.evaluate('box.value') == 'abcd'


def test_pasted_line_breaks_are_kept(typewriter_page):
    set_text(typewriter_page, 'one\ntwo\r\nthree\rfour')
    assert typewriter_page.evaluate('box.value') == 'one\ntwo\nthree\nfour'
    assert lines(typewriter_page) == ['one', 'two', 'three', 'four']


def test_clear_asks_first(typewriter_page):
    page = typewriter_page
    page.click('#clear')
    assert page.is_visible('#confirm')
    page.click('#clear-no')
    assert page.evaluate('box.value') != ''
    page.click('#clear')
    page.click('#clear-yes')
    assert page.evaluate('box.value') == ''


def test_ruler_marks_line_up_with_the_columns(typewriter_page):
    page = typewriter_page
    set_text(page, 'x' * 10)
    page.wait_for_timeout(200)       # the carriage marker slides into place
    # the carriage marker sits over column 11 (1-based), the same place the caret is
    caret_x = page.evaluate("document.querySelector('.tw-caret').getBoundingClientRect().left")
    marker = page.evaluate('''() => { var r = document.querySelector('.tw-ruler .carriage').getBoundingClientRect();
                                      return r.left + r.width / 2; }''')
    cw = page.evaluate("parseFloat(getComputedStyle(document.querySelector('.tw')).getPropertyValue('--tw-cw'))")
    assert abs((caret_x + cw / 2) - marker) < 2
