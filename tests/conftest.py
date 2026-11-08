"""
Shared setup for the browser tests.

Every page is opened from disk with the network switched off. Library requests the
Claude version makes to jsDelivr and cdnjs are answered from vendor/, so the tests never need
the internet. Set HEADED=1 to watch the browser, SLOWMO=200 to slow it down.
"""
import base64
import os
import pathlib
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
VENDOR = ROOT / 'vendor'
STUB = pathlib.Path(__file__).with_name('claude_stub.js')

# CDN paths used by the Claude version -> files in vendor/
CDN = {
    'p5@1.11.11/lib/p5.min.js': 'p5.min.js',
    'jspdf/2.5.1/jspdf.umd.min.js': 'jspdf.umd.min.js',
    'sql.js/1.8.0/sql-asm.js': 'sql-asm.js',
    'jszip/3.10.1/jszip.min.js': 'jszip.min.js',
}

# Inside Claude the page is wrapped in a small document with this reset; reproduce it.
SKELETON_HEAD = (
    '<!doctype html><html><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui,sans-serif}'
    'img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
)


# ---------------------------------------------------------------- browser

@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=not os.environ.get('HEADED'),
                              slow_mo=int(os.environ.get('SLOWMO', '0')))
        yield b
        b.close()


def _route(route):
    url = route.request.url
    if url.startswith('file:') or url.startswith('blob:') or url.startswith('data:'):
        return route.continue_()
    for path, name in CDN.items():
        if url.endswith(path):
            return route.fulfill(path=str(VENDOR / name), content_type='application/javascript')
    return route.abort()          # everything else (fonts.googleapis.com, ...) is offline


@pytest.fixture
def context_factory(browser):
    made = []

    def make(width=900, height=1500, claude=False, file_pickers=False):
        ctx = browser.new_context(viewport={'width': width, 'height': height}, accept_downloads=True)
        ctx.route('**/*', _route)
        if claude:
            ctx.add_init_script(path=str(STUB))
        if not file_pickers:
            # headless Chromium can't answer a real file picker; use the plain <input type=file> path
            ctx.add_init_script('delete window.showOpenFilePicker; delete window.showSaveFilePicker;')
        made.append(ctx)
        return ctx

    yield make
    for ctx in made:
        ctx.close()


@pytest.fixture
def page_errors():
    return []


def _watch(page, errors):
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text)
            if m.type == 'error' and 'Failed to load resource' not in m.text and 'net::' not in m.text else None)


# ---------------------------------------------------------------- pages

def artifact_file(tmp_path, name):
    """The Claude version as Claude serves it: the page wrapped in its skeleton."""
    out = tmp_path / ('wrapped-' + name)
    out.write_text(SKELETON_HEAD + (SRC / name).read_text() + '</body></html>')
    return out


@pytest.fixture
def wheel(context_factory, tmp_path, page_errors):
    """The Claude version of the wheel, with the Claude stand-in."""
    ctx = context_factory(claude=True)
    page = ctx.new_page()
    _watch(page, page_errors)
    page.goto(artifact_file(tmp_path, 'feelings-wheel.html').as_uri())
    w = Wheel(page)
    w.wait_ready()
    yield w
    assert not page_errors, page_errors


@pytest.fixture
def typewriter_page(context_factory, tmp_path, page_errors):
    ctx = context_factory()
    page = ctx.new_page()
    _watch(page, page_errors)
    page.goto(artifact_file(tmp_path, 'typewriter-note.html').as_uri())
    page.wait_for_function('window.box && document.querySelector(".tw-line")')
    yield page
    assert not page_errors, page_errors


@pytest.fixture(scope='session')
def standalone_file():
    """Builds dist/feelings-wheel-standalone.html fresh for the test run."""
    subprocess.run([sys.executable, str(ROOT / 'build_standalone.py')], check=True, capture_output=True)
    return DIST / 'feelings-wheel-standalone.html'


@pytest.fixture
def standalone(context_factory, standalone_file, page_errors):
    ctx = context_factory()
    page = ctx.new_page()
    _watch(page, page_errors)
    page.goto(standalone_file.as_uri())
    w = Wheel(page)
    w.wait_ready()
    page.wait_for_function("document.getElementById('store-state').textContent !== 'Loading…'")
    yield w
    assert not page_errors, page_errors


# ---------------------------------------------------------------- driving the wheel

class Wheel:
    def __init__(self, page):
        self.page = page

    def wait_ready(self):
        self.page.wait_for_function(
            "window.feelingsWheel && window.feelingsWheel.ready && window.feelingsWheel.frameCount > 0")

    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg)

    def sketch(self, call):
        """Call a function on the running sketch, e.g. sketch('hexOf(1, 4)')."""
        return self.page.evaluate("window.feelingsWheel." + call)

    def find(self, name):
        """(level, index) of a feeling by its word, including words you added (level 4)."""
        return tuple(self.page.evaluate('''name => {
            var p = window.feelingsWheel, n = {1: 6, 2: 36, 3: 72};
            for (var level = 1; level <= 3; level++)
              for (var i = 0; i < n[level]; i++)
                if (p.nameOf(level, i) === name) return [level, i];
            var w = p.added().filter(function (w) { return w.name === name; })[0];
            if (w) return [4, w.id];
            throw new Error('no feeling called ' + name);
        }''', name))

    def click(self, name):
        """Click a feeling on the wheel by its word. The wheel says where each segment is."""
        level, i = self.find(name)
        box = self.page.locator('#wheel').bounding_box()
        c = self.page.evaluate('([l, i]) => window.feelingsWheel.centerOf(l, i)', [level, i])
        css = self.page.evaluate("parseFloat(document.getElementById('wheel').style.width)")
        scale = box['width'] / css
        x, y = box['x'] + c['x'] * scale, box['y'] + c['y'] * scale
        self.page.mouse.move(x, y)
        self.page.mouse.click(x, y)
        self.page.wait_for_timeout(100)

    def add_word(self, name, beyond):
        """Add a word in Words mode beyond an outer feeling."""
        self.mode('words')
        self.click(beyond)
        self.page.fill('#word-input', name)
        self.page.click('#word-add')
        self.page.wait_for_timeout(150)

    def mode(self, which):
        self.page.click('#mode-' + which)

    def pick_color(self, hex_color):
        self.page.evaluate('''v => { var p = document.getElementById('picker');
                                   p.value = v; p.dispatchEvent(new Event('input')); }''', hex_color)

    def color_of(self, name):
        level, i = self.find(name)
        return self.sketch('hexOf(%d, %d)' % (level, i)).lower()

    def default_color_of(self, name):
        level, i = self.find(name)
        return self.sketch('defaultHexOf(%d, %d)' % (level, i)).lower()

    def note_text(self):
        return self.page.evaluate('document.querySelector("#note-box .tw-input").value')

    def type_note(self, text):
        self.page.keyboard.type(text)
        self.page.wait_for_timeout(900)   # notes save after a short pause in typing


# ---------------------------------------------------------------- small helpers

def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(base, target, t):
    """base moved t of the way toward target, per channel (what lerpColor does)."""
    b, g = rgb(base), rgb(target)
    return tuple(round(b[k] + (g[k] - b[k]) * t) for k in range(3))


def saved_bytes(page):
    """The last file handed to the Claude stand-in's downloads.save, as bytes."""
    saved = page.evaluate('window.__saved')
    if 'text' in saved:
        return saved['name'], saved['text'].encode()
    return saved['name'], base64.b64decode(saved['dataUrl'].split(',', 1)[1])
