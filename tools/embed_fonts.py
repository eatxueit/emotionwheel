"""
Re-embeds the Courier Prime fonts from vendor/fonts/ into the pages that carry them
(src/feelings-wheel.html). Run it after swapping a font file, then rebuild the standalone page.

    python tools/embed_fonts.py
"""
import base64, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONTS = ROOT / 'vendor' / 'fonts'
FILES = {'italic': 'CourierPrime-Italic.ttf', 'normal': 'CourierPrime-Regular.ttf', 'bold': 'CourierPrime-Bold.ttf'}

block = 'window.COURIER_PRIME_TTF = {\n' + ',\n'.join(
    "  %s: '%s'" % (k, base64.b64encode((FONTS / f).read_bytes()).decode()) for k, f in FILES.items()
) + '\n};'

for page in [ROOT / 'src' / 'feelings-wheel.html']:
    s = page.read_text()
    new, n = re.subn(r'window\.COURIER_PRIME_TTF = \{.*?\n\};', lambda m: block, s, count=1, flags=re.S)
    if not n:
        raise SystemExit('no embedded font block found in ' + str(page))
    page.write_text(new)
    print('updated', page.relative_to(ROOT))
