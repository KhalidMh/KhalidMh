"""Every card of the profile. Each function returns (svg text, alt text) for one theme and one width.
Desktop cards are 880 wide, phone cards 440 wide (shown when the screen is 600px or narrower)."""
import re
from datetime import date, timedelta

from svgkit import SVG, fit, tw, wrap

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def W(phone):
    return 440 if phone else 880


def nice_date(iso, year=False):
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


def plural(n, word):
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def frame(s, chrome_title=None):
    s.rect(0.5, 0.5, s.w - 1, s.h - 1, "panel", rx=16, stroke="border")
    if chrome_title is not None:
        for i, c in enumerate(("dot1", "dot2", "dot3")):
            s.circle(24 + i * 18, 22, 5, c)
        if chrome_title:
            s.text(s.w / 2, 27, chrome_title, 12, 400, "faint", anchor="middle")
        s.line(1, 44, s.w - 1, 44, "line")


# ------------------------------------------------------------------ hero
_TOK = re.compile(r"('[^']*')|(\b(?:service|entity|many|using|from|type|aspect|key)\b)|([{}\[\];:,=])|(\w+)|(\s+)|(.)")


def highlight(line):
    """Tiny CDS highlighter -> [(text, color)]."""
    out, prev_kw = [], False
    for m in _TOK.finditer(line):
        s, kw, punct, ident, ws, other = m.groups()
        if ws:
            out.append((ws, "text"))
            continue
        if s:
            out.append((s, "amber"))
        elif kw:
            out.append((kw, "pink"))
        elif punct:
            out.append((punct, "muted"))
        elif ident:
            rest = line[m.end():].lstrip()
            out.append((ident, "blue" if prev_kw else "teal" if rest.startswith(":") else "text"))
        else:
            out.append((other, "text"))
        prev_kw = bool(kw)
    return out


def hero(p, theme, phone):
    code = p["hero_code"]
    if phone:
        top_code = 212
        s = SVG(440, top_code + len(code) * 19 + 26 + 22, theme, "")
        frame(s, p.get("window_title", "~/profile.cds"))
        s.text(22, 84, p["greeting"], 13, 400, "muted")
        s.text(20, 134, p["name"], 52, 800, "text")
        s.text(22, 166, fit(p["tagline"], 13, 400), 13, 700, "text")
        _pin(s, 27, 186)
        s.text(38, 190, p["location"], 12, 400, "muted")
        s.rect(20, top_code, 400, len(code) * 19 + 26, "code", rx=12, stroke="line")
        for i, line in enumerate(code):
            s.spans(36, top_code + 30 + i * 19, highlight(line), 12)
    else:
        s = SVG(880, 284, theme, "")
        frame(s, p.get("window_title", "~/profile.cds"))
        s.text(46, 116, p["greeting"], 15, 400, "muted")
        s.text(42, 182, p["name"], 64, 800, "text")
        s.rect(46, 196, 56, 4, "teal", rx=2)
        s.text(46, 230, fit(p["tagline"], 15, 410), 15, 700, "text")
        _pin(s, 51, 251)
        s.text(64, 256, p["location"], 13, 400, "muted")
        h = len(code) * 20 + 30
        s.rect(470, 44 + (240 - h) / 2, 382, h, "code", rx=12, stroke="line")
        for i, line in enumerate(code):
            s.spans(490, 44 + (240 - h) / 2 + 32 + i * 20, highlight(line), 13)
    alt = f"Hi, I'm {p['name']}. {p['tagline']}. Based in {p['location']}."
    s.label = alt
    return s.render(), alt


def _pin(s, x, y):
    s.circle(x, y, 5.5, "none", stroke="teal", sw=2)
    s.circle(x, y, 1.8, "teal")


# ------------------------------------------------------------------ badges
def badge(kind, label, theme):
    w = int(16 + 24 + 12 + tw(label, 15) + 20)
    s = SVG(w, 44, theme, label)
    s.rect(0.5, 0.5, w - 1, 43, "panel", rx=22, stroke="border")
    if kind == "linkedin":
        s.rect(16, 11, 22, 22, "blue", rx=5)
        s.text(27, 27, "in", 13, 800, "panel", anchor="middle")
    else:
        s.rect(16, 14, 22, 16, "none", rx=3, stroke="teal", sw=2)
        s.path("M17 16 L27 23 L37 16", stroke="teal", sw=2)
    s.text(52, 27.5, label, 15, 700, "text")
    return s.render(), label


# ------------------------------------------------------------------ stats
def stats(d, theme, phone):
    tiles = [
        (f"{d['last_year']:,}", "contributions", "in the last 12 months", "teal"),
        (f"{d['current']['days']:,}", "day streak",
         f"since {nice_date(d['current']['start'])}" if d["current"]["start"] else "next one starts today", "amber"),
        (f"{d['longest']['days']:,}", "longest streak",
         f"{nice_date(d['longest']['start'])} – {nice_date(d['longest']['end'], True)}" if d["longest"]["start"] else "not started yet",
         "pink"),
        (f"{d['repos']:,}", "public repos", plural(d["stars"], "star") + " earned", "blue"),
    ]
    width = W(phone)
    cols = 2 if phone else 4
    pad, gap, th = (20, 12, 118) if phone else (28, 14, 124)
    tw_ = (width - 2 * pad - (cols - 1) * gap) / cols
    rows = (len(tiles) + cols - 1) // cols
    s = SVG(width, 60 + rows * th + (rows - 1) * gap + 22, theme, "")
    frame(s)
    s.text(pad, 36, f"~/github/{d['user']}", 12 if phone else 13, 700, "muted")
    s.text(width - pad, 36, f"{d['all_time']:,} since {d['since']}", 11 if phone else 13, 400, "faint", anchor="end")
    for i, (val, label, sub, color) in enumerate(tiles):
        x = pad + (i % cols) * (tw_ + gap)
        y = 56 + (i // cols) * (th + gap)
        s.rect(x, y, tw_, th, "code", rx=12, stroke="line")
        s.rect(x + 18, y + 18, 26, 4, color, rx=2)
        s.text(x + 18, y + 62, val, 32 if phone else 36, 800, "text")
        s.text(x + 18, y + 86, label, 13, 700, color)
        s.text(x + 18, y + 104, fit(sub, 11 if phone else 12, tw_ - 30), 11 if phone else 12, 400, "muted")
    alt = (f"On GitHub: {d['last_year']:,} contributions in the last 12 months, {d['current']['days']}-day current streak, "
           f"longest streak {d['longest']['days']} days, {d['all_time']:,} contributions since {d['since']}, "
           f"{d['repos']} public repos, {d['stars']} stars earned.")
    s.label = alt
    return s.render(), alt


# ------------------------------------------------------------------ heatmap
def level(c, top):
    if c <= 0 or top <= 0:
        return 0
    r = c / top
    return 1 if r <= 0.25 else 2 if r <= 0.5 else 3 if r <= 0.75 else 4


def heatmap(d, months, theme, phone):
    weeks = 27 if months == 6 else 53
    end = date.fromisoformat(d["end"])
    first = end - timedelta(days=(end.weekday() + 1) % 7 + 7 * (weeks - 1))
    width = W(phone)
    left, right, top = (40, 20, 78) if phone else (56, 28, 84)
    step = int((width - left - right) // weeks)
    cell = max(4, round(step * 0.82))
    cutoff = end - timedelta(days=182 if months == 6 else 364)
    cells = [(first + timedelta(days=i)) for i in range(weeks * 7) if first + timedelta(days=i) <= end]
    counts = [d["days"].get(x.isoformat(), 0) if x >= cutoff else 0 for x in cells]
    total, peak = sum(counts), max(counts or [0])
    s = SVG(width, top + 7 * step + 56, theme, "")
    frame(s)
    fs = 12 if phone else 13
    s.text(left - 2 if not phone else 20, 36, f"contributions · last {months} months", fs, 700, "text")
    s.text(width - right, 36, plural(total, "contribution"), fs, 700, "teal", anchor="end")
    last_label = -10
    for col in range(weeks):
        sunday = first + timedelta(days=7 * col)
        for k in range(7):
            day = sunday + timedelta(days=k)
            if day.day == 1 and day <= end and col - last_label >= 3:
                s.text(left + col * step, top - 12, MONTHS[day.month - 1], 10 if phone else 12, 400, "muted")
                last_label = col
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.text(left - 8, top + row * step + cell * 0.8, name, 9 if phone else 11, 400, "faint", anchor="end")
    rx = max(1.5, cell / 5)
    heat = s.t["heat"]
    for i, (day, c) in enumerate(zip(cells, counts)):
        col, row = divmod(i, 7)
        if day < cutoff:
            continue
        s.rect(left + col * step, top + row * step, cell, cell, heat[level(c, peak)], rx=rx)
    ly = top + 7 * step + 22
    box = 10 if phone else 12
    x = width - right - 5 * (box + 4) - tw("more", 11) - 6
    s.text(x - 8, ly + box - 2, "less", 11, 400, "faint", anchor="end")
    for i in range(5):
        s.rect(x + i * (box + 4), ly, box, box, heat[i], rx=2.5)
    s.text(x + 5 * (box + 4) + 4, ly + box - 2, "more", 11, 400, "faint")
    if peak:
        pd = cells[counts.index(peak)].isoformat()
        best = f"best day: {peak:,} on {nice_date(pd)}" if phone else f"best day: {plural(peak, 'contribution')} on {nice_date(pd, True)}"
        s.text(left - 2 if not phone else 20, ly + box - 2, best, 11, 400, "faint")
    alt = f"{plural(total, 'contribution')} in the last {months} months"
    s.label = alt
    return s.render(), alt


# ------------------------------------------------------------------ 30-day line
def line30(d, theme, phone):
    end = date.fromisoformat(d["end"])
    days = [end - timedelta(days=29 - i) for i in range(30)]
    counts = [d["days"].get(x.isoformat(), 0) for x in days]
    total, peak = sum(counts), max(counts)
    width = W(phone)
    x0, x1, y0, y1 = (40, width - 22, 72, 170) if phone else (52, width - 32, 76, 186)
    s = SVG(width, y1 + 46, theme, "")
    frame(s)
    fs = 12 if phone else 13
    s.text(20 if phone else 28, 36, "last 30 days", fs, 700, "text")
    s.text(width - (20 if phone else 28), 36, plural(total, "contribution"), fs, 700, "amber", anchor="end")
    top = max(peak, 1)
    shown = set()
    for frac in (0, 0.5, 1):
        y = y1 - frac * (y1 - y0)
        s.line(x0, y, x1, y, "line", 1, dash=None if frac == 0 else "3 5")
        val = round(peak * frac)
        if val not in shown:
            s.text(x0 - 10, y + 4, f"{val:,}", 10 if phone else 11, 400, "faint", anchor="end")
            shown.add(val)
    if not peak:
        s.text((x0 + x1) / 2, (y0 + y1) / 2, "quiet month: no public contributions", 12, 400, "faint", anchor="middle")
    pts = [(x0 + i * (x1 - x0) / 29, y1 - c / top * (y1 - y0)) for i, c in enumerate(counts)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    s.path(f"{line} L{x1:.1f} {y1:.1f} L{x0:.1f} {y1:.1f} Z", fill="amber", opacity=0.14)
    s.path(line, stroke="amber", sw=2.5)
    if peak:
        i = counts.index(peak)
        px, py = pts[i]
        s.circle(px, py, 5, "panel", stroke="amber", sw=2.5)
        lab = f"{peak:,} on {nice_date(days[i].isoformat())}"
        anchor = "end" if px > width * 0.7 else "start" if px < width * 0.3 else "middle"
        s.text(px + (-8 if anchor == "end" else 8 if anchor == "start" else 0), py - 12, lab, 11, 700, "text", anchor=anchor)
    for i, anchor in ((0, "start"), (15, "middle"), (29, "end")):
        s.text(pts[i][0], y1 + 24, nice_date(days[i].isoformat()), 10 if phone else 11, 400, "muted", anchor=anchor)
    alt = f"{plural(total, 'contribution')} in the last 30 days"
    s.label = alt
    return s.render(), alt


# ------------------------------------------------------------------ whoami terminal
def whoami(p, theme, phone):
    width = W(phone)
    size, lh, pad = (12, 21, 20) if phone else (14, 25, 30)
    prompt = p.get("prompt", f"{p['name'].lower()}:~$") + " "
    lines = []
    for entry in p["whoami"]:
        lines.append(("cmd", entry["cmd"]))
        for out in entry["out"]:
            for piece in wrap(out, size, width - 2 * pad - tw("  ", size)):
                lines.append(("out", "  " + piece))
    lines.append(("cursor", ""))
    s = SVG(width, 44 + 34 + (len(lines) - 1) * lh + 26, theme, "")
    frame(s, "bash")
    for i, (kind, txt) in enumerate(lines):
        y = 44 + 34 + i * lh
        if kind == "out":
            s.text(pad, y, txt, size, 400, "muted")
        else:
            s.spans(pad, y, [(prompt, "teal"), (txt, "text")], size, 700)
            if kind == "cursor":
                s.add(f'<rect x="{pad + tw(prompt, size) + 2:.1f}" y="{y - size + 1}" width="{size * 0.6:.1f}" '
                      f'height="{size + 2}" fill="{s.c("teal")}"><animate attributeName="opacity" values="1;1;0;0" '
                      f'dur="1.1s" repeatCount="indefinite"/></rect>')
    alt = "whoami: " + "; ".join(o for e in p["whoami"] for o in e["out"]) + "."
    s.label = alt
    return s.render(), alt


# ------------------------------------------------------------------ section label
def label(text, theme, phone):
    width = W(phone)
    size = 18 if phone else 20
    s = SVG(width, 56, theme, text)
    s.spans(4, 36, [("## ", "teal"), (text, "text")], size, 800)
    s.line(4 + tw("## " + text, size) + 16, 30, width - 4, 30, "border", 1.5)
    return s.render(), text


# ------------------------------------------------------------------ project card
def project(p, facts, theme, phone):
    width = W(phone)
    ver, dls, stars = facts.get("npm_version"), facts.get("npm_downloads"), facts.get("stars")
    status = (f"v{ver} on npm", "teal") if ver else (p.get("status_unpublished", "in the works"), "amber")
    fact_items = []
    if ver:
        fact_items.append((f"{dls or 0:,} downloads / month", "teal"))
    else:
        fact_items.append(("not on npm yet", "amber"))
    if stars is not None:
        fact_items.append((plural(stars, "star"), "pink"))
    if phone:
        pad, icon, size = 20, 46, 13
        body = wrap(p["line"], size, width - 2 * pad)
        y_line = 100
        chips_y = y_line + len(body) * 20 + 4
        facts_y = chips_y + 26 + 30
        h = facts_y + 24
        s = SVG(width, h, theme, "")
        frame(s)
        _icon(s, pad, 22, icon)
        s.text(pad + icon + 14, 46, p["name"], 22, 800, "text")
        _pill(s, pad + icon + 14, 56, status[0], status[1], 11)
        for i, l in enumerate(body):
            s.text(pad, y_line + i * 20, l, size, 400, "muted")
    else:
        pad, icon, size = 28, 60, 15
        tx = pad + icon + 20
        body = wrap(p["line"], size, width - tx - pad)
        chips_y = 92 + len(body) * 22
        facts_y = chips_y + 26 + 38
        h = facts_y + 26
        s = SVG(width, h, theme, "")
        frame(s)
        _icon(s, pad, 28, icon)
        s.text(tx, 58, p["name"], 26, 800, "text")
        _pill(s, tx + tw(p["name"], 26) + 16, 39, status[0], status[1], 12)
        for i, l in enumerate(body):
            s.text(tx, 88 + i * 22, l, size, 400, "muted")
        pad = tx
    x = pad
    for chip in p.get("chips", []):
        cw = tw(chip, 12) + 22
        if x + cw > width - 20:
            break
        s.rect(x, chips_y, cw, 26, "chip", rx=13, stroke="line")
        s.text(x + 11, chips_y + 17.5, chip, 12, 700, "text")
        x += cw + 8
    s.line(pad, facts_y - 22, width - (20 if phone else 28), facts_y - 22, "line")
    x = pad
    for txt, color in fact_items:
        s.circle(x + 4, facts_y - 4, 4, color)
        s.text(x + 14, facts_y, txt, 12, 700, "muted")
        x += 14 + tw(txt, 12) + 22
    alt = f"{p['name']}: {p['line']} {status[0]}; " + "; ".join(t for t, _ in fact_items) + "."
    s.label = alt
    return s.render(), alt


def _icon(s, x, y, size):
    s.rect(x, y, size, size, "code", rx=size * 0.24, stroke="line")
    fs = size * 0.36
    s.text(x + size / 2, y + size / 2 + fs * 0.36, ">_", fs, 800, "teal", anchor="middle")


def _pill(s, x, y, text, color, size):
    w = tw(text, size) + 20
    h = size + 12
    s.rect(x, y, w, h, color, rx=h / 2, opacity=0.14)
    s.rect(x, y, w, h, "none", rx=h / 2, stroke=color, sw=1)
    s.text(x + 10, y + h / 2 + size * 0.36, text, size, 700, color)
