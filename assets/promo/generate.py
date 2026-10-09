#!/usr/bin/env python3
"""
imranakki — terminal profile promo.

Renders `imranakki-terminal.gif`, the looping header of the profile README:
a terminal powers on, answers `whoami` with an identity card (Laval / INSEA), compiles and
solves a contest problem, plans a bike-share trip across Québec City without
paying overage, lists the public repos, and signs off.

Every frame is drawn with Pillow; there is no source footage. The random seed
is fixed, so a re-run reproduces the same file.

Deps: pillow >= 10
Run:  python3 assets/promo/generate.py
"""

import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Layout is authored in an 880 x 440 space and drawn at EXPORT times that size.
# GitHub shows the README in a ~880px column, so 2x is sharp on HiDPI screens.
W, H = 880, 440
EXPORT = int(os.environ.get("PROMO_EXPORT", "2"))
OUT = Path(__file__).with_name("imranakki-terminal.gif")

BG = (10, 12, 17)
INK = (214, 219, 228)      # primary text
DIM = (128, 136, 150)      # secondary text
FAINT = (60, 66, 78)       # chrome, inactive graph
GHOST = (30, 34, 42)       # glyph rain
ACCENT = (56, 189, 248)    # the only saturated colour; spent once per scene
GOOD = (134, 239, 172)     # "Accepted" only

FONT_DIRS = [
    Path.home() / ".local/share/fonts",
    Path("/usr/share/fonts/truetype/jetbrains-mono"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/lato"),
]


def find_font(*names):
    for d in FONT_DIRS:
        for n in names:
            p = d / n
            if p.exists():
                return str(p)
    raise SystemExit(f"none of these fonts are installed: {names}")


MONO = find_font("JetBrainsMonoNerdFontMono-Regular.ttf", "JetBrainsMono-Regular.ttf", "DejaVuSansMono.ttf")
MONO_BOLD = find_font("JetBrainsMonoNerdFontMono-ExtraBold.ttf", "JetBrainsMono-ExtraBold.ttf", "DejaVuSansMono-Bold.ttf")
DISPLAY = find_font("Lato-Black.ttf", "DejaVuSans-Bold.ttf")

_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, int(size * EXPORT))
    return _fonts[key]


def S(v):
    return int(round(v * EXPORT))


def mix(c, k, base=BG):
    """Fade colour c toward the background; k=1 is full colour, k=0 is gone."""
    k = max(0.0, min(1.0, k))
    return tuple(int(base[i] + (c[i] - base[i]) * k) for i in range(3))


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- backdrop

def build_backdrop():
    img = Image.new("RGB", (S(W), S(H)), BG)
    px = img.load()
    cx, cy = S(W) / 2, S(H) / 2
    rmax = math.hypot(cx, cy)
    # Soft vignette: a little lift in the middle, darker toward the corners.
    for y in range(0, S(H)):
        for x in range(0, S(W), 1):
            r = math.hypot(x - cx, y - cy) / rmax
            k = 1.10 - 0.45 * r * r
            px[x, y] = tuple(min(255, int(c * k)) for c in BG)
    d = ImageDraw.Draw(img)
    # Scanlines pinned to one layout pixel so they survive any EXPORT.
    for y in range(0, H, 3):
        d.rectangle([0, S(y), S(W), S(y) + max(1, EXPORT // 2) - 1], fill=mix(BG, 0.82, (0, 0, 0)))
    return img


BACKDROP = None


class Rain:
    """Sparse, dim columns of contest-flavoured glyphs. Texture, not content."""

    GLYPHS = list("{}();<>=+-*/%&|^~!?#0123456789") + ["++", "<<", ">>", "::", "&&", "->", "dp", "i", "j", "n"]

    def __init__(self, rng):
        self.cols = []
        for _ in range(14):
            self.cols.append({
                "x": rng.randrange(40, W - 40),
                "y": rng.uniform(-H, H),
                "speed": rng.uniform(1.6, 3.2),
                "len": rng.randrange(5, 12),
                "glyphs": [rng.choice(self.GLYPHS) for _ in range(14)],
            })

    def step(self):
        for c in self.cols:
            c["y"] += c["speed"]
            if c["y"] - c["len"] * 18 > H:
                c["y"] = -20

    def draw(self, d, k=1.0):
        f = font(MONO, 12)
        for c in self.cols:
            for i in range(c["len"]):
                y = c["y"] - i * 18
                if 0 <= y <= H - 40:
                    fade = (1 - i / c["len"]) * k
                    d.text((S(c["x"]), S(y)), c["glyphs"][i % len(c["glyphs"])], font=f, fill=mix(GHOST, fade * 0.9))


def chrome(d, label, k=1.0):
    col = mix(FAINT, k)
    L = 22
    for (x, y, sx, sy) in [(16, 16, 1, 1), (W - 16, 16, -1, 1), (16, H - 16, 1, -1), (W - 16, H - 16, -1, -1)]:
        d.line([S(x), S(y), S(x + sx * L), S(y)], fill=col, width=S(1))
        d.line([S(x), S(y), S(x), S(y + sy * L)], fill=col, width=S(1))
    d.line([S(28), S(H - 38), S(W - 28), S(H - 38)], fill=mix(GHOST, k * 1.4), width=S(1))
    f = font(MONO, 10)
    d.text((S(28), S(H - 31)), label, font=f, fill=col)
    right = "github.com/imranakki"
    d.text((S(W - 28) - d.textlength(right, font=f), S(H - 31)), right, font=f, fill=col)


# ---------------------------------------------------------------- frames

class Frame:
    def __init__(self, label, k=1.0):
        self.img = BACKDROP.copy()
        self.d = ImageDraw.Draw(self.img)
        self.label = label
        self.k = k

    def text(self, x, y, s, size=15, fill=INK, path=MONO, k=1.0):
        self.d.text((S(x), S(y)), s, font=font(path, size), fill=mix(fill, k * self.k))

    def width(self, s, size=15, path=MONO):
        return self.d.textlength(s, font=font(path, size)) / EXPORT

    def ctext(self, y, s, size=15, fill=INK, path=MONO, k=1.0):
        self.text((W - self.width(s, size, path)) / 2, y, s, size, fill, path, k)


PROMPT = "imran@akki ~"


def prompt(fr, x, y, typed, cursor_on=True, k=1.0):
    fr.text(x, y, PROMPT, 15, DIM, k=k)
    px = x + fr.width(PROMPT + " ")
    fr.text(px, y, "$", 15, ACCENT, k=k)
    tx = px + fr.width("$ ")
    fr.text(tx, y, typed, 15, INK, k=k)
    if cursor_on:
        cx = tx + fr.width(typed)
        fr.d.rectangle([S(cx), S(y + 2), S(cx + 8), S(y + 18)], fill=mix(INK, 0.8 * k * fr.k))


class Timeline:
    def __init__(self):
        self.frames = []
        self.rng = random.Random(7)
        self.rain = Rain(self.rng)
        self.tick = 0

    def new(self, label, k=1.0, rain=True):
        fr = Frame(label, k)
        if rain:
            self.rain.draw(fr.d, k)
        self.rain.step()
        self.tick += 1
        return fr

    def push(self, fr, ms):
        chrome(fr.d, fr.label, fr.k)
        self.frames.append((fr.img, max(20, int(round(ms / 10.0)) * 10)))

    @property
    def blink(self):
        return (self.tick // 6) % 2 == 0


# ---------------------------------------------------------------- scenes

def scene_power(tl):
    # A CRT line opens vertically into the screen.
    n = 12
    for i in range(n):
        t = ease(i / (n - 1))
        img = Image.new("RGB", (S(W), S(H)), (0, 0, 0))
        d = ImageDraw.Draw(img)
        h = max(1, int(S(H) * t))
        top = (S(H) - h) // 2
        if t < 0.98:
            img.paste(BACKDROP.crop((0, top, S(W), top + h)), (0, top))
            glow = mix((255, 255, 255), 1 - t, BG)
            d.rectangle([0, S(H) // 2 - S(1), S(W), S(H) // 2 + S(1)], fill=glow)
        else:
            img = BACKDROP.copy()
        tl.frames.append((img, 40))
        tl.tick += 1


def type_cmd(tl, label, lines_above, x, y, cmd, after_ms=350):
    """Type `cmd` at the prompt, one or two characters per frame."""
    i = 0
    while i <= len(cmd):
        fr = tl.new(label)
        lines_above(fr)
        prompt(fr, x, y, cmd[:i], True)
        tl.push(fr, 50 if i else 300)
        i += 1
    for _ in range(3):
        fr = tl.new(label)
        lines_above(fr)
        prompt(fr, x, y, cmd, tl.blink)
        tl.push(fr, after_ms / 3)


def scene_whoami(tl):
    label = "boot"
    x, y = 56, 150
    type_cmd(tl, label, lambda fr: None, x, y, "whoami")


def scene_identity(tl):
    label = "whoami"
    lines = [
        ("backend & systems engineer", INK),
        ("msc computer science (ai) @ université laval", DIM),
        ("double degree with insea, rabat  ->  québec, qc", DIM),
        ("codeforces expert  ·  meta hacker cup 2025 top 4%", DIM),
    ]

    def card(fr, t):
        fr.text(56, 70, "$ whoami", 13, FAINT)
        a = ease(t * 3)
        fr.text(56, 104, "Imran Akki", 54, INK, DISPLAY, k=a)
        rule = ease((t - 0.15) * 3)
        fr.d.rectangle([S(58), S(180), S(58 + 90 * rule), S(183)], fill=mix(ACCENT, rule * fr.k))
        for j, (s, c) in enumerate(lines):
            lk = ease((t - 0.25 - j * 0.12) * 4)
            fr.text(58, 204 + j * 28, s, 15, c, k=lk)

    n = 18
    for i in range(n):
        fr = tl.new(label)
        card(fr, i / (n - 1))
        tl.push(fr, 55)
    for _ in range(6):
        fr = tl.new(label)
        card(fr, 1.0)
        tl.push(fr, 3600 / 6)
    fade_out(tl, label, lambda fr: card(fr, 1.0))


def scene_solve(tl):
    label = "contest"
    x, y0 = 56, 70
    cmd = "g++ -O2 -std=c++20 solve.cpp && ./a.out < tests"
    type_cmd(tl, label, lambda fr: None, x, y0, cmd, after_ms=250)

    tests = [("01", 3), ("02", 4), ("03", 11), ("04", 38), ("05", 61), ("06", 46)]

    def body(fr, shown, verdict, footer):
        prompt(fr, x, y0, cmd, False)
        for j in range(shown):
            name, ms = tests[j]
            s = f"test {name}  ........  ok   {ms:>3} ms"
            fr.text(x, y0 + 40 + j * 24, s, 14, DIM)
        if verdict:
            fr.text(x, y0 + 40 + len(tests) * 24 + 14, "Accepted", 20, GOOD, MONO_BOLD)
            fr.text(x + fr.width("Accepted  ", 20, MONO_BOLD), y0 + 40 + len(tests) * 24 + 19,
                    "6/6 passed, max 61 ms", 14, DIM)
        if footer:
            fr.text(x, y0 + 40 + len(tests) * 24 + 60, "meta hacker cup 2025", 14, INK, k=footer)
            fr.text(x + fr.width("meta hacker cup 2025   "), y0 + 40 + len(tests) * 24 + 60,
                    "rank 491 / 13,779", 14, ACCENT, k=footer)

    for j in range(1, len(tests) + 1):
        for _ in range(2):
            fr = tl.new(label)
            body(fr, j, False, 0)
            tl.push(fr, 60)
    fr = tl.new(label)
    body(fr, len(tests), True, 0)
    tl.push(fr, 700)
    for i in range(6):
        fr = tl.new(label)
        body(fr, len(tests), True, ease((i + 1) / 6))
        tl.push(fr, 50)
    for _ in range(4):
        fr = tl.new(label)
        body(fr, len(tests), True, 1)
        tl.push(fr, 2600 / 4)
    fade_out(tl, label, lambda fr: body(fr, len(tests), True, 1))


# Stations are a stylised, hand-placed map, not real coordinates.
STATIONS = {
    "place-royale": (150, 260), "st-roch": (250, 200), "limoilou": (330, 128),
    "vieux-port": (210, 320), "saint-jean": (390, 250), "montcalm": (470, 300),
    "sillery": (580, 330), "ste-foy": (640, 240), "ulaval": (740, 268),
    "cartier": (520, 190), "lebourgneuf": (610, 128),
}
EDGES = [
    ("place-royale", "st-roch"), ("place-royale", "vieux-port"), ("st-roch", "limoilou"),
    ("st-roch", "saint-jean"), ("vieux-port", "saint-jean"), ("saint-jean", "montcalm"),
    ("saint-jean", "cartier"), ("limoilou", "cartier"), ("cartier", "lebourgneuf"),
    ("cartier", "ste-foy"), ("montcalm", "sillery"), ("sillery", "ste-foy"),
    ("ste-foy", "ulaval"), ("lebourgneuf", "ste-foy"), ("sillery", "ulaval"),
]
ROUTE = ["place-royale", "st-roch", "saint-jean", "cartier", "ste-foy", "ulaval"]
RESET = "saint-jean"


def scene_avelo(tl):
    label = "avelo route optimizer"
    cmd = "avelo plan place-royale ulaval --max-ride 30m"

    def head(fr):
        pass

    type_cmd(tl, label, head, 56, 46, cmd, after_ms=200)

    # Route as a polyline with cumulative lengths so it can be drawn partially.
    pts = [STATIONS[s] for s in ROUTE]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    reset_at = sum(seg[:ROUTE.index(RESET)]) / total

    def partial(p):
        out = [pts[0]]
        left = p * total
        for i, L in enumerate(seg):
            if left >= L:
                out.append(pts[i + 1])
                left -= L
            else:
                a, b = pts[i], pts[i + 1]
                out.append((a[0] + (b[0] - a[0]) * left / L, a[1] + (b[1] - a[1]) * left / L))
                break
        return out

    def body(fr, graph_k, p, summary_k):
        prompt(fr, 56, 46, cmd, False)
        for a, b in EDGES:
            (x1, y1), (x2, y2) = STATIONS[a], STATIONS[b]
            fr.d.line([S(x1), S(y1), S(x2), S(y2)], fill=mix(FAINT, graph_k * 0.9 * fr.k), width=S(1))
        for name, (x, y) in STATIONS.items():
            r = 4.5
            on_route = name in ROUTE
            fr.d.ellipse([S(x - r), S(y - r), S(x + r), S(y + r)],
                         fill=mix(DIM if on_route else FAINT, graph_k * fr.k))
            if name in ("place-royale", "ulaval", RESET):
                fr.text(x - fr.width(name, 11) / 2, y + 9, name, 11, DIM, k=graph_k)
        if p > 0:
            line = partial(p)
            fr.d.line([(S(a), S(b)) for a, b in line], fill=mix(ACCENT, fr.k), width=S(2.5), joint="curve")
            hx, hy = line[-1]
            fr.d.ellipse([S(hx - 6), S(hy - 6), S(hx + 6), S(hy + 6)], outline=mix(ACCENT, fr.k), width=S(2))
            if p >= reset_at:
                x, y = STATIONS[RESET]
                fr.d.ellipse([S(x - 7), S(y - 7), S(x + 7), S(y + 7)], fill=mix(ACCENT, fr.k))
                fr.text(x + 12, y - 28, "dock + re-unlock, clock resets", 11, INK)
                fr.text(x - 98, y - 52, "leg 1   9.2 min", 11, DIM)
            if p >= 1:
                fr.text(STATIONS["ste-foy"][0] - 40, STATIONS["ste-foy"][1] - 40, "leg 2   27.7 min", 11, DIM)
        if summary_k:
            y = 352
            fr.text(56, y, "naive        43.7 min   $2.70   one ride, over the limit", 13, DIM, k=summary_k)
            fr.text(56, y + 22, "planned      43.7 min   ", 13, INK, k=summary_k)
            fr.text(56 + fr.width("planned      43.7 min   ", 13), y + 22, "$0.00", 13, ACCENT, MONO_BOLD, k=summary_k)
            fr.text(56 + fr.width("planned      43.7 min   $0.00   ", 13), y + 22,
                    "every leg under 30 min", 13, DIM, k=summary_k)

    for i in range(8):
        fr = tl.new(label)
        body(fr, ease((i + 1) / 8), 0, 0)
        tl.push(fr, 45)
    steps = 34
    for i in range(steps):
        fr = tl.new(label)
        body(fr, 1, ease((i + 1) / steps), 0)
        tl.push(fr, 40)
    for i in range(6):
        fr = tl.new(label)
        body(fr, 1, 1, ease((i + 1) / 6))
        tl.push(fr, 50)
    for _ in range(5):
        fr = tl.new(label)
        body(fr, 1, 1, 1)
        tl.push(fr, 4000 / 5)
    fade_out(tl, label, lambda fr: body(fr, 1, 1, 1))


REPOS = [
    ("avelo-route-optimizer/", "bike-share trips with no overage fees"),
    ("NexusORM/", "an orm that is really a small c++20 compiler"),
    ("OBSIDIAN/", "chess engine, alpha-beta, ~2000 elo"),
    ("nova-shell/", "a unix shell, written in c"),
    ("Acadconf/", "conference + peer review, spring boot"),
]


def scene_repos(tl):
    label = "public"
    x, y0 = 56, 84
    cmd = "ls ~/public"
    type_cmd(tl, label, lambda fr: None, x, y0, cmd, after_ms=200)

    def body(fr, shown):
        prompt(fr, x, y0, cmd, False)
        for j in range(shown):
            name, what = REPOS[j]
            fr.text(x, y0 + 42 + j * 30, name, 15, ACCENT if j == 0 else INK)
            fr.text(x + 260, y0 + 42 + j * 30, what, 14, DIM)

    for j in range(1, len(REPOS) + 1):
        for _ in range(3):
            fr = tl.new(label)
            body(fr, j)
            tl.push(fr, 60)
    for _ in range(5):
        fr = tl.new(label)
        body(fr, len(REPOS))
        tl.push(fr, 3800 / 5)
    fade_out(tl, label, lambda fr: body(fr, len(REPOS)))


def scene_outro(tl):
    label = "eof"

    def body(fr, t, cursor):
        a = ease(t * 2.5)
        word = "imranakki"
        wx = (W - fr.width(word, 44, MONO_BOLD)) / 2
        fr.text(wx, 150, word, 44, INK, MONO_BOLD, k=a)
        if cursor:
            cx = wx + fr.width(word, 44, MONO_BOLD) + 6
            fr.d.rectangle([S(cx), S(160), S(cx + 22), S(206)], fill=mix(ACCENT, a * fr.k))
        fr.ctext(232, "Imran Akki  ·  backend, systems, competitive programming", 14, DIM, k=ease((t - 0.3) * 3))
        r = ease((t - 0.45) * 3)
        fr.d.line([S(W / 2 - 120 * r), S(268), S(W / 2 + 120 * r), S(268)], fill=mix(FAINT, fr.k), width=S(1))
        fr.ctext(284, "github.com/imranakki  ·  me@imranakki.com", 14, INK, k=ease((t - 0.6) * 3))

    n = 20
    for i in range(n):
        fr = tl.new(label)
        body(fr, i / (n - 1), tl.blink)
        tl.push(fr, 55)
    for _ in range(8):
        fr = tl.new(label)
        body(fr, 1, tl.blink)
        tl.push(fr, 3200 / 8)
    fade_out(tl, label, lambda fr: body(fr, 1, False), n=12, to_black=True)


def fade_out(tl, label, draw, n=6, to_black=False):
    for i in range(n):
        k = 1 - ease((i + 1) / n)
        fr = tl.new(label, k=k)
        draw(fr)
        if to_black:
            chrome(fr.d, fr.label, fr.k)
            img = Image.blend(Image.new("RGB", fr.img.size, (0, 0, 0)), fr.img, max(k, 0.0))
            tl.frames.append((img, 60))
        else:
            tl.push(fr, 45)


# ---------------------------------------------------------------- encode

def main():
    global BACKDROP
    BACKDROP = build_backdrop()
    tl = Timeline()
    scene_power(tl)
    scene_whoami(tl)
    scene_identity(tl)
    scene_solve(tl)
    scene_avelo(tl)
    scene_repos(tl)
    scene_outro(tl)

    # One shared palette for every frame keeps colours stable and the file small.
    sample = Image.new("RGB", (S(W), S(H) * 4))
    picks = [len(tl.frames) * k // 4 + 20 for k in range(4)]
    for i, p in enumerate(picks):
        sample.paste(tl.frames[min(p, len(tl.frames) - 1)][0], (0, S(H) * i))
    pal = sample.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    imgs = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f, _ in tl.frames]
    durs = [ms for _, ms in tl.frames]
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=durs, loop=0, optimize=True, disposal=1)
    secs = sum(durs) / 1000
    print(f"{OUT.name}: {imgs[0].size[0]}x{imgs[0].size[1]}, {len(imgs)} frames, "
          f"{secs:.1f}s, {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
