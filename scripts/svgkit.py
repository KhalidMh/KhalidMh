"""Small SVG toolkit: themes, a monospace text measure, and font subsetting.

Every card is drawn in JetBrains Mono (SIL OFL, see fonts/OFL-JetBrainsMono.txt). The font is subset to the
characters each SVG uses and embedded as base64 woff2, so GitHub shows the same letters on every device.
JetBrains Mono is monospaced (600 units per 1000 em), so text width is simply 0.6 * size * len(text).
"""
import base64
import io
from functools import lru_cache
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).parent / "fonts"
FONT_FILES = {400: "jetbrains-mono-latin-400-normal.woff2",
              700: "jetbrains-mono-latin-700-normal.woff2",
              800: "jetbrains-mono-latin-800-normal.woff2"}
ADVANCE = 0.6

THEMES = {
    "dark": {
        "bg": "#0e1420", "panel": "#131b2b", "code": "#0b111c", "border": "#253149", "line": "#1d2739",
        "text": "#e7edf7", "muted": "#8d9ab4", "faint": "#5c6a85",
        "teal": "#34d6bf", "amber": "#f4b54a", "blue": "#6aa5ff", "pink": "#ff7d9c", "violet": "#b394ff",
        "dot1": "#ff6b6b", "dot2": "#f4b54a", "dot3": "#3ccf8e",
        "heat": ["#18212f", "#0f4f4a", "#14806f", "#21b39a", "#45e3c8"],
        "chip": "#1a2438",
    },
    "light": {
        "bg": "#fbfaf6", "panel": "#ffffff", "code": "#f5f3ec", "border": "#e3dfd3", "line": "#ece8de",
        "text": "#18202f", "muted": "#626b7d", "faint": "#9aa1ae",
        "teal": "#0b8f7d", "amber": "#b77a08", "blue": "#2862d6", "pink": "#c8325a", "violet": "#6a46d1",
        "dot1": "#ee5f5f", "dot2": "#e7a62f", "dot3": "#2fb67b",
        "heat": ["#eeebe3", "#bfe8de", "#7fd1bf", "#2fae97", "#0b7c6c"],
        "chip": "#f2efe7",
    },
}


def tw(text, size):
    """Width of a string in px at a font size."""
    return len(text) * ADVANCE * size


def fit(text, size, width):
    """Cut a string with an ellipsis so it fits a width."""
    n = int(width // (ADVANCE * size))
    return text if len(text) <= n else text[: max(0, n - 3)] + "..."


def wrap(text, size, width):
    """Greedy word wrap for monospace text."""
    n = max(8, int(width // (ADVANCE * size)))
    lines, cur = [], ""
    for word in text.split():
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= n:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return [l if len(l) <= n else l[: n - 3] + "..." for l in lines] or [""]


@lru_cache(maxsize=None)
def _font_b64(weight, chars):
    font = TTFont(str(FONT_DIR / FONT_FILES[weight]), recalcTimestamp=False)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    opts.name_IDs = []
    opts.notdef_outline = True
    opts.recalc_timestamp = False
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class SVG:
    def __init__(self, width, height, theme, label):
        self.w, self.h, self.label = width, height, label
        self.t = THEMES[theme]
        self.parts = []
        self.chars = {}

    def c(self, color):
        return self.t.get(color, color)

    def add(self, raw):
        self.parts.append(raw)

    def rect(self, x, y, w, h, fill="panel", rx=0, stroke=None, sw=1, opacity=None):
        extra = f' stroke="{self.c(stroke)}" stroke-width="{_num(sw)}"' if stroke else ""
        extra += f' opacity="{_num(opacity)}"' if opacity is not None else ""
        self.add(f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" rx="{_num(rx)}" '
                 f'fill="{self.c(fill)}"{extra}/>')

    def circle(self, cx, cy, r, fill, stroke=None, sw=1):
        extra = f' stroke="{self.c(stroke)}" stroke-width="{_num(sw)}"' if stroke else ""
        self.add(f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(r)}" fill="{self.c(fill)}"{extra}/>')

    def line(self, x1, y1, x2, y2, stroke="line", sw=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" y2="{_num(y2)}" '
                 f'stroke="{self.c(stroke)}" stroke-width="{_num(sw)}"{d}/>')

    def path(self, d, fill="none", stroke=None, sw=1, opacity=None, extra=""):
        s = f' stroke="{self.c(stroke)}" stroke-width="{_num(sw)}" stroke-linejoin="round" stroke-linecap="round"' if stroke else ""
        o = f' opacity="{_num(opacity)}"' if opacity is not None else ""
        self.add(f'<path d="{d}" fill="{self.c(fill)}"{s}{o}{extra}/>')

    def text(self, x, y, s, size=14, weight=400, fill="text", anchor="start", opacity=None):
        self.chars.setdefault(weight, set()).update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        o = f' opacity="{_num(opacity)}"' if opacity is not None else ""
        self.add(f'<text x="{_num(x)}" y="{_num(y)}" font-size="{_num(size)}" font-weight="{weight}" '
                 f'fill="{self.c(fill)}"{a}{o}>{escape(s, quote=False)}</text>')

    def spans(self, x, y, pieces, size=14, weight=400):
        """One line of differently coloured pieces: [(text, color), ...]."""
        out = []
        for txt, color in pieces:
            self.chars.setdefault(weight, set()).update(txt)
            out.append(f'<tspan fill="{self.c(color)}">{escape(txt, quote=False)}</tspan>')
        self.add(f'<text x="{_num(x)}" y="{_num(y)}" font-size="{_num(size)}" font-weight="{weight}" '
                 f'xml:space="preserve">{"".join(out)}</text>')

    def render(self):
        faces = []
        for weight in sorted(self.chars):
            chars = "".join(sorted(self.chars[weight] | {" "}))
            faces.append(f"@font-face{{font-family:KM;font-weight:{weight};"
                         f"src:url(data:font/woff2;base64,{_font_b64(weight, chars)}) format('woff2')}}")
        style = "".join(faces) + "text{font-family:KM,'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace}"
        label = escape(self.label)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{label}"><title>{label}</title>'
                f'<defs><style>{style}</style></defs>' + "".join(self.parts) + "</svg>\n")
