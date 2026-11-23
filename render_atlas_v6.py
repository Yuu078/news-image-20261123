#!/usr/bin/env python3
"""THE MORNING ATLAS v6 - Monday 23 November 2026.

A one-page newspaper poster: 35 stories, 7 regions. The hero carries
the COP31 collapse, nine illustrated cards carry the next biggest
stories, and THE WIRE carries the other 25 in two columns, with a
region chip row and a DATE CHECK box at the foot.

Everything on the page is drawn by one small shape engine: every
picture on the poster is a list of shape records (rectangles,
ellipses, polygons, lines, arcs, flames, smoke) and a single
dispatcher paints them. Coordinates inside a picture are relative to
that picture's box; a negative coordinate counts back from the far
edge, so ground strips and right-hand details stay put.

Drawn from scratch with Pillow. Deterministic: no clock, no random
numbers, no network. The verification stamp is a constant fixed at
build time, never read from the clock. The output is a 1024x1024 PNG
of at most 1 MiB.
"""

import hashlib
import math
import os
import sys
from collections import Counter, namedtuple

from PIL import Image, ImageDraw, ImageFont

Box = namedtuple("Box", "x y w h")

PAGE_W, PAGE_H = 1024, 1024
EDGE = 16
SPAN = PAGE_W - 2 * EDGE  # 992 px of content width
E = 1000  # shape-record edge marker: -(E + n) counts n back from the far edge

CREAM = (247, 242, 232)
PAPER = (250, 246, 236)
INK = (22, 22, 22)
SOFT = (74, 70, 62)
RED = (193, 39, 45)
NAVY = (31, 58, 95)
STEEL = (58, 88, 132)
LINE = (180, 172, 156)
SKY = (205, 220, 236)
SEA = (52, 110, 160)
SAND = (222, 196, 150)
DUST = (238, 226, 198)

SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS_I = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"

TITLE_SZ = 42
DATE_SZ = 28
STRIP_SZ = 24
HERO_SZ = 26
CARD_SZ = 19
CARD_MIN = 18
BODY_SZ = 11
WIRE_SZ = 12

STAMP = "Verified at 15:45 WIB"
TITLE = ("Monday 23 November 2026: 35 stories, 7 regions \u2014 COP31 talks "
         "collapse in Antalya, Kyiv strikes kill 15")

_faces = {}


def face(path, size):
    key = (path, size)
    if key not in _faces:
        _faces[key] = ImageFont.truetype(path, size)
    return _faces[key]


def wrap(pen, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if pen.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def shrink(pen, text, start, floor, max_w):
    size = start
    while size > floor and pen.textlength(text, font=face(SANS_B, size)) > max_w:
        size -= 1
    return size


def txt(pen, x, y, s, fnt, fill=INK):
    pen.text((x, y), s, font=fnt, fill=fill)


def center(pen, y, text, fnt, fill=INK, x0=EDGE, x1=PAGE_W - EDGE):
    tw = pen.textlength(text, font=fnt)
    pen.text((x0 + (x1 - x0 - tw) / 2, y), text, font=fnt, fill=fill)


def rule(pen, y, width=1, fill=INK, x0=EDGE, x1=PAGE_W - EDGE):
    pen.line([(x0, y), (x1, y)], fill=fill, width=width)


def frame(pen, box, width=1, outline=INK):
    pen.rectangle([box.x, box.y, box.x + box.w, box.y + box.h],
                  outline=outline, width=width)


# ---------------------------------------------------------------------------
# Shape engine: one dispatcher paints every picture from shape records.
# A record is a tuple whose first item names its kind; coordinates are
# relative to the picture box, negative ones counting from the far edge.
# ---------------------------------------------------------------------------

def _rx(box, v):
    if v <= -E:
        return box.w + v + E
    return v


def _ry(box, v):
    if v <= -E:
        return box.h + v + E
    return v


def _pt(box, p):
    return (box.x + _rx(box, p[0]), box.y + _ry(box, p[1]))


def _box4(box, x0, y0, x1, y1):
    return [box.x + _rx(box, x0), box.y + _ry(box, y0),
            box.x + _rx(box, x1), box.y + _ry(box, y1)]


def _flame(pen, box, cx, base, h, wdt):
    cx = box.x + _rx(box, cx)
    base = box.y + _ry(box, base)
    pen.polygon([(cx - wdt, base), (cx, base - h), (cx + wdt, base)],
                fill=(240, 120, 20))
    pen.polygon([(cx - wdt // 2, base), (cx, base - int(h * 0.62)),
                 (cx + wdt // 2, base)], fill=RED)


def _smoke(pen, box, cx, cy, r, tone=(120, 120, 128)):
    cx = box.x + _rx(box, cx)
    cy = box.y + _ry(box, cy)
    pen.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tone)


def _seat(pen, box, cx, top, wdt, hgt, fill, tipped=False):
    cx = box.x + _rx(box, cx)
    top = box.y + _ry(box, top)
    if tipped:
        pen.rectangle([cx - wdt // 2, top + hgt - 9, cx + wdt // 2,
                       top + hgt - 3], fill=fill, outline=INK)
        pen.rectangle([cx + wdt // 2 - 4, top + 4, cx + wdt // 2,
                       top + hgt - 3], fill=fill, outline=INK)
        return
    back_h = int(hgt * 0.55)
    pen.rectangle([cx - wdt // 2, top, cx + wdt // 2, top + back_h], fill=fill,
                  outline=INK)
    pen.rectangle([cx - wdt // 2, top + back_h, cx + wdt // 2,
                   top + back_h + 4], fill=fill, outline=INK)
    for lx in (cx - wdt // 2 + 2, cx + wdt // 2 - 2):
        pen.line([(lx, top + back_h + 4), (lx, top + hgt)], fill=INK, width=2)


def paint(pen, box, specs):
    """Paint a list of shape records into box, in order."""
    for spec in specs:
        kind = spec[0]
        if kind == "rect":
            _, x0, y0, x1, y1, fill = spec[:6]
            outl = spec[6] if len(spec) > 6 else None
            wd = spec[7] if len(spec) > 7 else 1
            kw = {"fill": fill}
            if outl is not None:
                kw["outline"] = outl
                kw["width"] = wd
            pen.rectangle(_box4(box, x0, y0, x1, y1), **kw)
        elif kind == "ell":
            _, x0, y0, x1, y1, fill = spec[:6]
            outl = spec[6] if len(spec) > 6 else None
            wd = spec[7] if len(spec) > 7 else 1
            kw = {"fill": fill}
            if outl is not None:
                kw["outline"] = outl
                kw["width"] = wd
            pen.ellipse(_box4(box, x0, y0, x1, y1), **kw)
        elif kind == "poly":
            _, pts, fill = spec[:3]
            outl = spec[3] if len(spec) > 3 else None
            kw = {"fill": fill}
            if outl is not None:
                kw["outline"] = outl
            pen.polygon([_pt(box, p) for p in pts], **kw)
        elif kind == "line":
            _, pts, fill, wd = spec
            pen.line([_pt(box, p) for p in pts], fill=fill, width=wd)
        elif kind == "arc":
            _, x0, y0, x1, y1, a0, a1, fill, wd = spec
            pen.arc(_box4(box, x0, y0, x1, y1), a0, a1, fill=fill, width=wd)
        elif kind == "pie":
            _, x0, y0, x1, y1, a0, a1, fill = spec[:8]
            outl = spec[8] if len(spec) > 8 else None
            kw = {"fill": fill}
            if outl is not None:
                kw["outline"] = outl
            pen.pieslice(_box4(box, x0, y0, x1, y1), a0, a1, **kw)
        elif kind == "flame":
            _, cx, base, h, wdt = spec
            _flame(pen, box, cx, base, h, wdt)
        elif kind == "smoke":
            _, cx, cy, r = spec[:4]
            tone = spec[4] if len(spec) > 4 else (120, 120, 128)
            _smoke(pen, box, cx, cy, r, tone)
        elif kind == "seat":
            _, cx, top, wdt, hgt, fill = spec[:6]
            tipped = spec[6] if len(spec) > 6 else False
            _seat(pen, box, cx, top, wdt, hgt, fill, tipped)
        elif kind == "text":
            _, x, y, s, size, fill = spec[:6]
            bold = spec[6] if len(spec) > 6 else True
            fnt = face(SANS_B if bold else SANS, size)
            pen.text((box.x + _rx(box, x), box.y + _ry(box, y)), s,
                     font=fnt, fill=fill)
        else:
            raise SystemExit("unknown shape kind: %r" % (kind,))


def flag(pen, box, label):
    f = face(SANS_B, 11)
    tw = pen.textlength(label, font=f)
    pen.rectangle([box.x, box.y, box.x + tw + 10, box.y + 16], fill=RED)
    txt(pen, box.x + 5, box.y + 2, label, f, fill=(255, 255, 255))


def ntag(pen, box, n):
    f = face(SANS_B, 11)
    t = str(n)
    wdt = max(18, int(pen.textlength(t, font=f)) + 8)
    pen.rectangle([box.x + box.w - wdt, box.y, box.x + box.w, box.y + 16],
                  fill=RED)
    txt(pen, box.x + box.w - wdt + (wdt - pen.textlength(t, font=f)) / 2,
        box.y + 2, t, f, fill=(255, 255, 255))


def plate(pen, box, num):
    """Key number on a solid PAPER plate, bottom-right of the picture."""
    size = 20 if len(num) <= 2 else (16 if len(num) <= 4 else 13)
    f = face(SANS_B, size)
    tw = pen.textlength(num, font=f)
    cx1, cy1 = box.x + box.w - 4, box.y + box.h - 4
    cx0, cy0 = cx1 - tw - 10, cy1 - size - 6
    pen.rectangle([cx0, cy0, cx1, cy1], fill=PAPER, outline=INK, width=1)
    txt(pen, cx0 + 5, cy0 + 2, num, f, fill=NAVY)


# ---------------------------------------------------------------------------
# The ledger: every story on the poster, hero first. Region counts, the
# masthead line, the chip row and the strip are all DERIVED from this
# table and asserted against the submission title.
# ---------------------------------------------------------------------------

REGIONS = [
    ("EU", "EUROPE"),
    ("APAC", "ASIA-PACIFIC"),
    ("ME", "MIDDLE EAST"),
    ("NA", "NORTH AMERICA"),
    ("AF", "AFRICA"),
    ("LATAM", "LATIN AMERICA"),
    ("GLOBAL", "GLOBAL"),
]
REGION_LABEL = dict(REGIONS)

HERO = {
    "region": "GLOBAL",
    "headline": "COP31 TALKS COLLAPSE IN ANTALYA \u2014 NO DEAL",
    "body": ("COP31 ends with no agreement after nearly 200 countries fail "
             "to agree. The EU and about 130 parties rejected a text that "
             "omitted fossil fuels."),
    "src": "Antalya, Turkey  \u00b7  (Reuters; BBC; Xinhua)",
    "key": "0",
}

CARDS = [
    dict(n=2, region="EU", banner="KYIV", scene="kyiv",
         headline="KYIV STRIKES KILL 15",
         body="Russian strikes kill at least 15 in the Kyiv region; a boy, "
              "7, is pulled alive from the Dymer rubble.",
         src="(BBC; Euronews; AP)", key="15"),
    dict(n=3, region="ME", banner="IRAN", scene="iran",
         headline="IRAN VOWS TO FIGHT BLOCKADE",
         body="Tehran says it will use all available tools to confront the "
              "US naval blockade, its ministry says.",
         src="(Reuters)", key=None),
    dict(n=4, region="ME", banner="HORMUZ", scene="hormuz",
         headline="TANKERS HIT IN HORMUZ",
         body="Two supertankers hit explosive devices near the Strait of "
              "Hormuz; Iran airs missile-site footage.",
         src="(wires)", key="2"),
    dict(n=5, region="NA", banner="WASHINGTON", scene="capitol",
         headline="DEMOCRATS WIN HOUSE 258",
         body="Democrats clinch at least 258 House seats \u2014 the largest "
              "majority for either party since 1992.",
         src="(AP)", key="258"),
    dict(n=6, region="GLOBAL", banner="MARKETS", scene="chart",
         headline="AI SELL-OFF HITS MARKETS",
         body="Nikkei falls 5.06% and the S&P 500 drops 3.7% as the AI "
              "sell-off spreads; gold rises.",
         src="(Reuters; One Turn)", key="5.06%"),
    dict(n=7, region="APAC", banner="INDONESIA", scene="indonesia",
         headline="INDONESIA FACTORY FIRE TOLL 24",
         body="24 dead, about 30 unaccounted after the candy-factory fire "
              "in Banten; the blaze is not yet out.",
         src="(Xinhua; Reuters)", key="24"),
    dict(n=8, region="EU", banner="TURIN", scene="tennis",
         headline="ALCARAZ WINS ATP FINALS",
         body="Alcaraz beats world No. 1 Zverev 6-2, 7-6 in Turin for his "
              "first ATP Finals title.",
         src="(Reuters; BBC)", key="6-2"),
    dict(n=9, region="EU", banner="LIVERPOOL", scene="football",
         headline="LIVERPOOL ROUT UNITED 4-0",
         body="Liverpool thrash 10-man Manchester United 4-0 in "
              "Pochettino's first match as manager.",
         src="(Reuters; BBC)", key="4-0"),
    dict(n=10, region="AF", banner="SUDAN", scene="sudan",
         headline="SUDAN DRONES KILL 5 CHILDREN",
         body="Drones hit Khartoum and Omdurman, killing five children; a "
              "UN building is damaged.",
         src="(One Turn; AFP)", key="5"),
]

# THE WIRE: stories 11-35, one line each, two columns (13 + 12).
WIRE = [
    (11, "EU", "France PMI falls to 46.2, six-month low", "Reuters"),
    (12, "EU", "Burnham: EU deal 'could make decade better'", "BBC"),
    (13, "EU", "Thousands rally in Istanbul over media takeover", "One Turn"),
    (14, "EU", "M\u00e1rquez wins eighth MotoGP title, ties Agostini", "One Turn"),
    (15, "APAC", "Prabowo to name two VP candidates on Monday", "Reuters"),
    (16, "APAC", "India PMI 56.3 as factories offset services", "Reuters"),
    (17, "APAC", "Seoul sees solid growth, flags chip risks", "Reuters"),
    (18, "APAC", "Nepal PM Balen Shah holds talks with Modi", "ANI"),
    (19, "APAC", "Taiwan warns Canada over China trade ties", "Euronews"),
    (20, "APAC", "SoftBank to invest $2b in Intel", "Access24"),
    (21, "ME", "Houthis claim Saudi refinery hit", "One Turn"),
    (22, "ME", "Gaza war left widespread contamination", "One Turn"),
    (23, "ME", "Trump 'inclined' to hit Iran if no deal by New Year", "ET"),
    (24, "NA", "Delta delays 1,000+ flights at Atlanta hub", "Xinhua"),
    (25, "NA", "49ers win in Mexico; Bills stay top in NFL", "BBC"),
    (26, "NA", "US energy exports hit records", "One Turn"),
    (27, "NA", "US reveals citizenship-test, H-1B changes", "Access24"),
    (28, "NA", "US restricts defence cooperation with Canada", "wires"),
    (29, "AF", "Paramilitary attack kills 24 in South Sudan", "wires"),
    (30, "AF", "Fighting near Ebola area disrupts response", "One Turn"),
    (31, "AF", "UN urges probe of drone hit on ship off Libya", "Euronews"),
    (32, "LATAM", "Bolsonaro in intensive care, bowel obstruction", "One Turn"),
    (33, "LATAM", "Soldier killed in Colombia base attack", "Rio Times"),
    (34, "LATAM", "Caro Quintero's nephew shot dead in Puebla", "Rio Times"),
    (35, "GLOBAL", "Sweetener erythritol linked to stroke risk", "ScienceAlert"),
]

STRIP = [
    ("0", "fossil fuels in the final draft"),
    ("15", "killed in Kyiv region strikes"),
    ("258", "Democrats' House seats"),
    ("24", "dead in Indonesia factory fire"),
]

DATE_LINES = [
    "\u00d7 Mongolia's president resigned \u2014 parliament approved 19/20 "
    "Nov (Reuters). Not 23 Nov.",
    "\u00d7 \u201cEl Chapo Isidro\u201d captured \u2014 arrested 20 Nov, "
    "announced 21 Nov (Reuters/AP). Not 23 Nov.",
]


def tally():
    counts = Counter()
    counts[HERO["region"]] += 1
    for card in CARDS:
        counts[card["region"]] += 1
    for _, region, _, _ in WIRE:
        counts[region] += 1
    return counts


def need(cond, msg):
    if not cond:
        raise SystemExit(msg)


def audit(pen):
    counts = tally()
    need(sum(counts.values()) == 35,
         "ledger holds %d stories, title says 35" % sum(counts.values()))
    need(len(CARDS) == 9, "grid expects exactly 9 cards")
    need(len(WIRE) == 25,
         "wire expects exactly 25 stories, got %d" % len(WIRE))
    need(set(counts) == set(REGION_LABEL) and len(counts) == 7,
         "regions present: %r" % (sorted(counts),))
    expect = {"EU": 7, "APAC": 7, "ME": 5, "NA": 6, "AF": 4, "LATAM": 3,
              "GLOBAL": 3}
    need(dict(counts) == expect,
         "region counts %r != %r" % (dict(counts), expect))
    need([n for n, _, _, _ in WIRE] == list(range(11, 36)),
         "wire numbering is not 11..35")
    by_head = {c["headline"]: c["key"] for c in CARDS}
    pairs = [(HERO["key"], STRIP[0][0]),
             (by_head["KYIV STRIKES KILL 15"], STRIP[1][0]),
             (by_head["DEMOCRATS WIN HOUSE 258"], STRIP[2][0]),
             (by_head["INDONESIA FACTORY FIRE TOLL 24"], STRIP[3][0])]
    for got, want in pairs:
        need(got == want, "strip/card mismatch: %r != %r" % (got, want))
    need(TITLE_SZ > DATE_SZ > HERO_SZ > STRIP_SZ > CARD_MIN,
         "type hierarchy broken")
    for card in CARDS:
        size = shrink(pen, card["headline"], CARD_SZ, CARD_MIN, 313)
        need(size >= CARD_MIN, "headline under floor: %r" % card["headline"])
        need(len(wrap(pen, card["headline"], face(SANS_B, size), 313)) <= 2,
             "headline wraps past 2: %r" % card["headline"])
        need(len(wrap(pen, card["body"], face(SANS, BODY_SZ), 313)) <= 2,
             "body wraps past 2 lines: %r" % card["headline"])
    wf = face(SANS_B, WIRE_SZ)
    for n, _, head, src in WIRE:
        line = "%d \u00b7 %s (%s)" % (n, head, src)
        need(pen.textlength(line, font=wf) <= 490,
             "wire line too wide: %r" % line)
    return counts


# ---------------------------------------------------------------------------
# Card pictures, as shape records. Each function returns the records for
# one 323x46 picture; paint() draws them in order. E counts back from
# the far edge (see _rx/_ry): -(E+6) is six pixels up from the bottom.
# ---------------------------------------------------------------------------

def _kyiv():
    art = [
        ("rect", 0, 0, -E, -E, (196, 202, 210)),
        ("rect", 0, -(E + 6), -E, -E, (120, 112, 100)),
        ("rect", 14, 8, 120, -(E + 6), (150, 142, 128), INK),
        ("poly", [(140, -(E + 6)), (140, 22), (158, 14), (172, 26),
                  (190, 18), (206, 30), (206, -(E + 6))], (110, 102, 90),
         INK),
        ("poly", [(206, -(E + 6)), (226, 30), (246, -(E + 6))], (90, 84, 74)),
        ("flame", 172, 22, 14, 7),
        ("smoke", 176, 6, 5),
        ("smoke", 188, 3, 4, (150, 150, 158)),
        ("line", [(262, 18), (262, -(E + 6))], INK, 4),
        ("ell", 258, 10, 266, 18, INK),
        ("line", [(262, 24), (252, 34)], INK, 3),
        ("rect", 276, 28, 312, 34, RED, INK),
    ]
    for r in range(2):
        for c in range(4):
            art.append(("rect", 24 + c * 24, 14 + r * 14, 36 + c * 24,
                        24 + r * 14, (255, 214, 120)))
    return art


def _iran():
    art = [
        ("rect", 0, 0, -E, 20, SKY),
        ("rect", 0, 20, -E, -E, SEA),
    ]
    for wy in (28, 38):
        for wx in range(2, 313, 26):
            art.append(("arc", wx, wy - 3, wx + 24, wy + 5, 180, 360,
                        (255, 255, 255), 2))
    art += [
        ("poly", [(60, 22), (250, 22), (238, 36), (72, 36)], (90, 96, 104),
         INK),
        ("rect", 150, 8, 190, 22, (120, 126, 134), INK),
        ("line", [(170, 8), (170, -2)], INK, 3),
        ("poly", [(170, -2), (186, 2), (170, 6)], RED),
        ("rect", 96, 14, 120, 22, (70, 76, 84), INK),
        ("poly", [(272, 30), (312, 30), (304, 38), (280, 38)], (60, 66, 74),
         INK),
    ]
    return art


def _hormuz():
    art = [
        ("rect", 0, 0, -E, 14, SKY),
        ("rect", 0, 14, -E, -E, SEA),
    ]
    for wy in (24, 34):
        for wx in range(2, 313, 26):
            art.append(("arc", wx, wy - 3, wx + 24, wy + 5, 180, 360,
                        (255, 255, 255), 2))
    art += [
        ("poly", [(30, 22), (240, 22), (228, 34), (42, 34)], (40, 40, 44),
         INK),
        ("rect", 30, 19, 240, 22, RED),
    ]
    for i, c in enumerate([(200, 60, 40), (40, 120, 70), (220, 180, 40),
                           (58, 88, 132)]):
        art.append(("rect", 66 + i * 28, 10, 90 + i * 28, 19, c, INK))
    art += [
        ("rect", 200, 4, 224, 19, (255, 255, 255), INK),
        ("flame", 110, 12, 14, 7),
        ("smoke", 114, 2, 4),
        ("rect", 262, 20, 312, 26, (40, 40, 44)),
        ("rect", 288, 14, 298, 20, (40, 40, 44)),
    ]
    return art


def _capitol():
    art = [
        ("rect", 0, 0, -E, 30, SKY),
        ("rect", 0, 30, -E, -E, (46, 125, 60)),
        ("rect", 109, 22, 213, 30, (255, 255, 255), INK),
        ("rect", 131, 16, 191, 22, (255, 255, 255), INK),
        ("pie", 131, -6, 191, 18, 180, 360, (255, 255, 255), INK),
        ("line", [(161, -6), (161, -12)], INK, 2),
        ("ell", 159, -14, 163, -10, INK),
        ("line", [(26, 4), (26, 30)], INK, 2),
        ("poly", [(26, 4), (46, 8), (26, 12)], RED),
    ]
    for i in range(5):
        art.append(("rect", 115 + i * 20, 24, 121 + i * 20, 30, NAVY))
    return art


def _chart():
    art = [
        ("rect", 0, 0, -E, -E, (255, 255, 255)),
    ]
    for gy in (12, 24, 36):
        art.append(("line", [(12, gy), (-(E + 8), gy)], (225, 225, 225), 1))
    art += [
        ("line", [(12, 4), (12, -(E + 6))], INK, 2),
        ("line", [(12, -(E + 6)), (-(E + 8), -(E + 6))], INK, 2),
        ("line", [(22, 8), (80, 10), (130, 9), (180, 18), (225, 28),
                  (268, 38)], RED, 4),
    ]
    for px, py in [(22, 8), (80, 10), (130, 9), (180, 18), (225, 28),
                   (268, 38)]:
        art.append(("ell", px - 3, py - 3, px + 3, py + 3, RED))
    art.append(("poly", [(268, 42), (259, 30), (277, 31)], RED))
    for bx, bh, c in [(40, 8, (46, 125, 60)), (100, 12, (46, 125, 60)),
                      (210, 6, RED), (255, 4, RED)]:
        art.append(("rect", bx, 40 - bh, bx + 20, -(E + 6), c))
    return art


def _indonesia():
    art = [
        ("rect", 0, 0, -E, -E, (238, 228, 208)),
        ("rect", 0, -(E + 4), -E, -E, (150, 120, 80)),
        ("rect", 18, 18, 160, -(E + 4), (128, 84, 52), INK),
    ]
    for i in range(3):
        art.append(("poly", [(18 + i * 48, 18), (42 + i * 48, 8),
                             (66 + i * 48, 18)], (96, 56, 34)))
    art.append(("rect", 170, 4, 182, -(E + 4), (110, 110, 116), INK))
    for wx in range(28, 150, 20):
        art.append(("rect", wx, 24, wx + 11, 32, (255, 214, 120)))
    art += [
        ("flame", 88, 12, 16, 9),
        ("smoke", 178, 2, 5),
        ("smoke", 108, 2, 4, (150, 150, 150)),
        ("rect", 220, 28, 300, 38, RED, INK),
        ("rect", 280, 22, 300, 28, RED, INK),
        ("line", [(226, 28), (200, 14)], INK, 3),
    ]
    for wx in (234, 284):
        art.append(("ell", wx, 36, wx + 11, 45, INK))
    return art


def _tennis():
    art = [
        ("rect", 0, 0, -E, -E, (46, 125, 60)),
        ("rect", 0, -(E + 8), -E, -E, (30, 90, 44)),
        ("rect", 30, 6, -(E + 30), -(E + 8), (58, 140, 74),
         (255, 255, 255), 2),
        ("line", [(161, 6), (161, -(E + 8))], (255, 255, 255), 2),
        ("line", [(30, 23), (293, 23)], (255, 255, 255), 3),
    ]
    for nx in range(34, 293, 10):
        art.append(("line", [(nx, 19), (nx, 27)], (200, 200, 200), 1))
    art += [
        ("ell", 250, 8, 262, 20, (220, 240, 60), INK),
        ("arc", 40, 2, 90, 40, 300, 60, (255, 255, 255), 3),
        ("line", [(78, 26), (96, 40)], (255, 255, 255), 3),
    ]
    return art


def _football():
    art = [
        ("rect", 0, 0, -E, -E, (46, 125, 60)),
        ("rect", 0, -(E + 8), -E, -E, (30, 90, 44)),
        ("line", [(161, 0), (161, -(E + 8))], (255, 255, 255), 2),
        ("ell", 139, 6, 183, -(E + 14), None, (255, 255, 255), 2),
        ("rect", 271, 8, 313, 34, None, (255, 255, 255), 3),
        ("ell", 40, 22, 56, 38, (255, 255, 255), INK),
        ("poly", [(42, 26), (48, 26), (46, 32), (42, 32)], INK),
        ("line", [(90, 38), (60, 32)], INK, 4),
    ]
    for gx in range(273, 313, 8):
        art.append(("line", [(gx, 8), (gx, 34)], (255, 255, 255), 1))
    return art


def _sudan():
    art = [
        ("rect", 0, 0, -E, -E, (24, 28, 52)),
    ]
    for sx, sy in [(30, 6), (90, 10), (180, 5), (250, 9), (300, 6)]:
        art.append(("ell", sx, sy, sx + 2, sy + 2, (255, 255, 255)))
    art += [
        ("ell", 275, 4, 295, 24, (250, 214, 120)),
        ("rect", 0, -(E + 6), -E, -E, (120, 100, 80)),
        ("rect", 16, 22, 110, -(E + 6), (150, 130, 100), INK),
        ("poly", [(10, 22), (63, 8), (90, 22)], (120, 70, 44)),
        ("poly", [(90, 22), (116, 22), (104, 12)], (90, 60, 40)),
        ("smoke", 66, 4, 4, (150, 150, 158)),
        ("rect", 196, 12, 224, 20, (200, 200, 200), INK),
    ]
    for ox in (-18, 18):
        art.append(("ell", 210 + ox - 8, 13, 210 + ox + 8, 19,
                    (180, 180, 180)))
        art.append(("line", [(210 + ox - 12, 16), (210 + ox + 12, 16)],
                    (255, 255, 255), 2))
    art += [
        ("line", [(196, 16), (190, 8)], (200, 200, 200), 2),
        ("line", [(224, 16), (230, 8)], (200, 200, 200), 2),
    ]
    return art


ART = {
    "kyiv": _kyiv(),
    "iran": _iran(),
    "hormuz": _hormuz(),
    "capitol": _capitol(),
    "chart": _chart(),
    "indonesia": _indonesia(),
    "tennis": _tennis(),
    "football": _football(),
    "sudan": _sudan(),
}


# ---------------------------------------------------------------------------
# Hero picture: the empty COP31 summit hall, as shape records plus two
# small loops (nameplates, chairs) and the giant 0 drawn as text.
# ---------------------------------------------------------------------------

def _summit():
    art = [
        ("rect", 0, 0, -E, -E, (188, 206, 228)),
        ("rect", 0, 96, -E, -E, (168, 188, 212)),
        ("rect", 10, 8, 74, 52, (240, 246, 252), INK, 2),
        ("ell", 26, 14, 58, 46, None, NAVY, 2),
        ("ell", 34, 14, 50, 46, None, NAVY, 1),
        ("line", [(26, 30), (58, 30)], NAVY, 1),
        ("rect", 306, 8, 370, 52, (240, 246, 252), INK, 2),
        ("line", [(314, 48), (364, 48)], INK, 1),
        ("rect", 12, 88, 368, 97, (146, 108, 66), INK, 1),
        ("poly", [(179, 101), (201, 101), (205, 122), (175, 122)], NAVY,
         INK),
    ]
    for i, bh in enumerate((10, 17, 25)):
        bx = 318 + i * 17
        art.append(("rect", bx, 48 - bh, bx + 11, 48,
                    STEEL if i < 2 else RED))
    for i, cx in enumerate(range(40, 356, 52)):
        if i in (2, 5):
            art.append(("poly", [(cx - 10, 84), (cx + 10, 86),
                                 (cx + 10, 93), (cx - 10, 91)],
                        (255, 255, 255), INK))
        else:
            art.append(("rect", cx - 10, 82, cx + 10, 90,
                        (255, 255, 255), INK))
    for i, cx in enumerate(range(40, 356, 52)):
        if abs(cx - 190) < 30:
            continue
        art.append(("seat", cx, 103, 22, 20, NAVY, i == 5))
    for i, cx in enumerate(range(28, 368, 52)):
        art.append(("seat", cx, 124, 24, 15, STEEL, i == 1))
    return art


def _zero(pen, box):
    """The giant red 0 with a paper halo, and its caption line."""
    zf = face(SANS_B, 64)
    zw = pen.textlength("0", font=zf)
    zx = box.x + (box.w - zw) / 2
    zy = box.y + 0
    for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        txt(pen, zx + ox, zy + oy, "0", zf, fill=PAPER)
    txt(pen, zx, zy, "0", zf, fill=RED)
    cap = "fossil-fuel mentions in the final draft"
    cf = face(SANS_B, 11)
    cw_ = pen.textlength(cap, font=cf)
    txt(pen, box.x + (box.w - cw_) / 2, box.y + 64, cap, cf, fill=NAVY)


# ---------------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------------

def masthead(pen, counts):
    center(pen, 4, "THE MORNING ATLAS", face(SERIF_B, TITLE_SZ))
    rule(pen, 52, width=2)
    center(pen, 56, "MONDAY 23 NOVEMBER 2026", face(SERIF_B, DATE_SZ))
    sub = "%d stories  \u00b7  %d regions  \u00b7  one page" % (
        sum(counts.values()), len(counts))
    center(pen, 90, sub, face(SANS, 12), fill=SOFT)
    rule(pen, 106, width=1, fill=LINE)


def strip(pen):
    cell_w, gap, y0, hh = 242, 8, 112, 38
    x = EDGE
    for num, label in STRIP:
        pen.rectangle([x, y0, x + cell_w, y0 + hh], outline=LINE, width=1)
        nf = face(SANS_B, STRIP_SZ)
        nw = pen.textlength(num, font=nf)
        txt(pen, x + (cell_w - nw) / 2, y0 + 1, num, nf, fill=NAVY)
        lf = face(SANS, 11)
        if pen.textlength(label, font=lf) > cell_w - 10:
            raise SystemExit("strip label too wide: %r" % label)
        center(pen, y0 + 24, label, lf, fill=SOFT, x0=x, x1=x + cell_w)
        x += cell_w + gap


def hero(pen):
    box = Box(EDGE, 156, SPAN, 148)
    frame(pen, box, width=2)
    hall = Box(box.x + 1, box.y + 1, 380, box.h - 2)
    paint(pen, hall, _summit())
    _zero(pen, hall)
    flag(pen, Box(box.x + 1, box.y + 1, 0, 0), "COP31 \u00b7 ANTALYA")
    ntag(pen, Box(box.x + 1, box.y + 1, 380, 0), 1)
    rx = 412
    txt(pen, rx, box.y + 8, "1  \u00b7  THE BIG STORY", face(SANS_B, 12),
        fill=RED)
    hf = face(SANS_B, HERO_SZ)
    lines = wrap(pen, HERO["headline"], hf, PAGE_W - EDGE - rx)
    if len(lines) > 2:
        raise SystemExit("hero headline wraps past 2 lines")
    for i, ln in enumerate(lines):
        txt(pen, rx, box.y + 28 + i * 32, ln, hf)
    bf = face(SANS, 13)
    blines = wrap(pen, HERO["body"], bf, PAGE_W - EDGE - rx)
    if len(blines) > 2:
        raise SystemExit("hero body too long: %d lines" % len(blines))
    for i, ln in enumerate(blines):
        txt(pen, rx, box.y + 96 + i * 17, ln, bf)
    txt(pen, rx, box.y + box.h - 16, HERO["src"], face(SANS_I, 11),
        fill=SOFT)


def cards(pen):
    y0, ch, gap, cell_w = 310, 130, 8, 325
    for i, card in enumerate(CARDS):
        row, col = divmod(i, 3)
        x = EDGE + col * (cell_w + gap)
        y = y0 + row * (ch + gap)
        frame(pen, Box(x, y, cell_w, ch), width=1)
        scene = Box(x + 1, y + 1, cell_w - 2, 46)
        paint(pen, scene, ART[card["scene"]])
        if card["key"] is not None:
            plate(pen, scene, card["key"])
        flag(pen, scene, card["banner"])
        ntag(pen, scene, card["n"])
        hs = shrink(pen, card["headline"], CARD_SZ, CARD_MIN, cell_w - 12)
        hf = face(SANS_B, hs)
        hlines = wrap(pen, card["headline"], hf, cell_w - 12)
        if len(hlines) > 2 or hs < CARD_MIN:
            raise SystemExit("card headline fails floor: %r"
                             % card["headline"])
        for j, ln in enumerate(hlines):
            txt(pen, x + 6, y + 50 + j * 21, ln, hf)
        bf = face(SANS, BODY_SZ)
        blines = wrap(pen, card["body"], bf, cell_w - 12)
        if len(blines) > 2:
            raise SystemExit("card body wraps past 2 lines: %r"
                             % card["headline"])
        for j, ln in enumerate(blines):
            txt(pen, x + 6, y + 94 + j * 13, ln, bf)
        txt(pen, x + 6, y + 120, card["src"], face(SANS_I, 9), fill=SOFT)


def wire(pen):
    y0 = 718
    txt(pen, EDGE, y0, "THE WIRE \u2014 THE OTHER 25 STORIES",
        face(SANS_B, 12), fill=RED)
    rule(pen, y0 + 16, width=1, fill=LINE)
    wf = face(SANS_B, WIRE_SZ)
    sf = face(SANS, 10)
    for col_idx, col in enumerate((WIRE[:13], WIRE[13:])):
        x = EDGE + col_idx * 502
        for i, (n, _, head, src) in enumerate(col):
            y = y0 + 22 + i * 14
            num = "%d \u00b7 " % n
            txt(pen, x, y, num, wf, fill=RED)
            nx = x + pen.textlength(num, font=wf)
            txt(pen, nx, y, head, wf)
            sx = nx + pen.textlength(head, font=wf) + 4
            txt(pen, sx, y + 1, "(%s)" % src, sf, fill=SOFT)


def regions(pen, counts):
    f = face(SANS_B, 13)
    x, y, hh = EDGE, 922, 24
    for key, name in REGIONS:
        label = "%s %d" % (name, counts[key])
        tw = pen.textlength(label, font=f)
        pen.rounded_rectangle([x, y, x + tw + 18, y + hh], radius=6, fill=NAVY)
        txt(pen, x + 9, y + 4, label, f, fill=(255, 255, 255))
        x += tw + 18 + 8
    if x - 8 > PAGE_W - EDGE:
        raise SystemExit("region chips overflow")


def datecheck(pen):
    y0, hh = 952, 52
    pen.rectangle([EDGE, y0, PAGE_W - EDGE, y0 + hh], outline=RED, width=2)
    txt(pen, EDGE + 10, y0 + 3, "DATE CHECK \u2014 WHAT WE LEFT OUT",
        face(SANS_B, 11), fill=RED)
    sf = face(SANS_B, 11)
    sw = pen.textlength(STAMP, font=sf)
    txt(pen, PAGE_W - EDGE - 10 - sw, y0 + 3, STAMP, sf, fill=RED)
    for i, ln in enumerate(DATE_LINES):
        txt(pen, EDGE + 10, y0 + 19 + i * 12, ln, face(SANS, 10))


def footer(pen):
    center(pen, 1008,
           "All 35 stories happened or were first reported on Monday "
           "23 November 2026.", face(SANS_I, 10), fill=INK)


def build_poster():
    img = Image.new("RGB", (PAGE_W, PAGE_H), CREAM)
    pen = ImageDraw.Draw(img)
    counts = audit(pen)
    masthead(pen, counts)
    strip(pen)
    hero(pen)
    cards(pen)
    wire(pen)
    regions(pen, counts)
    datecheck(pen)
    footer(pen)
    return img


def check_output(path):
    """Re-open a written poster and confirm it is what we meant to draw."""
    with Image.open(path) as im:
        if im.size != (PAGE_W, PAGE_H):
            raise SystemExit("poster is %r, not 1024x1024" % (im.size,))
        if im.mode != "RGB":
            raise SystemExit("poster mode is %s, not RGB" % im.mode)
    blob = open(path, "rb").read()
    if len(blob) > 1048576:
        raise SystemExit("poster is %d bytes, over the 1 MiB cap"
                         % len(blob))
    return len(blob), hashlib.sha256(blob).hexdigest()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "entry.png")
    build_poster().save(out, "PNG", optimize=True)
    size, digest = check_output(out)
    print("poster written: %s (%d bytes, sha256 %s)" % (out, size, digest))


if __name__ == "__main__":
    main()
