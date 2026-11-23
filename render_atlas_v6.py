#!/usr/bin/env python3
"""THE MORNING ATLAS v6 - Monday 23 November 2026.

One-page newspaper poster: 35 stories, 7 regions. Built on the ATLAS v5
bones (masthead, 4-number strip, hero with a drawn scene, illustrated
cards, region chips, DATE CHECK) and extended to the playbook's 35-story
format: hero + 9 illustrated cards + a 25-line THE WIRE in two columns.

Drawn from scratch with Pillow. Deterministic: no clock, no randomness,
no network - the verification stamp below is a build-time constant.
entry.png is 1024x1024, at most 1 MiB.
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

SIZE_TITLE = 42
SIZE_DATE = 28
SIZE_STRIP_NUM = 24
SIZE_HERO_HEAD = 26
SIZE_CARD_HEAD_START = 19
SIZE_CARD_HEAD_MIN = 18
SIZE_BODY = 11
SIZE_WIRE = 12

STAMP = "Verified at 15:45 WIB"
TITLE = ("Monday 23 November 2026: 35 stories, 7 regions \u2014 COP31 talks "
         "collapse in Antalya, Kyiv strikes kill 15")

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def wrapped(d, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, start, floor, max_w):
    size = start
    while size > floor and d.textlength(text, font=font(SANS_B, size)) > max_w:
        size -= 1
    return size


def centred(d, y, text, fnt, fill=INK, x0=EDGE, x1=PAGE_W - EDGE):
    tw = d.textlength(text, font=fnt)
    d.text((x0 + (x1 - x0 - tw) / 2, y), text, font=fnt, fill=fill)


def hline(d, y, width=1, fill=INK, x0=EDGE, x1=PAGE_W - EDGE):
    d.line([(x0, y), (x1, y)], fill=fill, width=width)


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


def ledger_counts():
    counts = Counter()
    counts[HERO["region"]] += 1
    for card in CARDS:
        counts[card["region"]] += 1
    for _, region, _, _ in WIRE:
        counts[region] += 1
    return counts


def audit_ledger(d):
    counts = ledger_counts()
    if sum(counts.values()) != 35:
        raise SystemExit("ledger holds %d stories, title says 35"
                         % sum(counts.values()))
    if len(CARDS) != 9:
        raise SystemExit("grid expects exactly 9 cards")
    if len(WIRE) != 25:
        raise SystemExit("wire expects exactly 25 stories, got %d"
                         % len(WIRE))
    if set(counts) != set(REGION_LABEL) or len(counts) != 7:
        raise SystemExit("regions present: %r" % (sorted(counts),))
    expect = {"EU": 7, "APAC": 7, "ME": 5, "NA": 6, "AF": 4, "LATAM": 3,
              "GLOBAL": 3}
    if dict(counts) != expect:
        raise SystemExit("region counts %r != %r" % (dict(counts), expect))
    if [n for n, _, _, _ in WIRE] != list(range(11, 36)):
        raise SystemExit("wire numbering is not 11..35")
    by_head = {c["headline"]: c["key"] for c in CARDS}
    expected = [(HERO["key"], STRIP[0][0]),
                (by_head["KYIV STRIKES KILL 15"], STRIP[1][0]),
                (by_head["DEMOCRATS WIN HOUSE 258"], STRIP[2][0]),
                (by_head["INDONESIA FACTORY FIRE TOLL 24"], STRIP[3][0])]
    for got, want in expected:
        if got != want:
            raise SystemExit("strip/card mismatch: %r != %r" % (got, want))
    if not (SIZE_TITLE > SIZE_DATE > SIZE_HERO_HEAD > SIZE_STRIP_NUM
            > SIZE_CARD_HEAD_MIN):
        raise SystemExit("type hierarchy broken")
    for card in CARDS:
        size = fit(d, card["headline"], SIZE_CARD_HEAD_START,
                   SIZE_CARD_HEAD_MIN, 313)
        if size < SIZE_CARD_HEAD_MIN:
            raise SystemExit("headline under floor: %r" % card["headline"])
        if len(wrapped(d, card["headline"], font(SANS_B, size), 313)) > 2:
            raise SystemExit("headline wraps past 2: %r" % card["headline"])
        if len(wrapped(d, card["body"], font(SANS, SIZE_BODY), 313)) > 2:
            raise SystemExit("body wraps past 2 lines: %r" % card["headline"])
    wf = font(SANS_B, SIZE_WIRE)
    sf = font(SANS, 10)
    for n, _, head, src in WIRE:
        line = "%d \u00b7 %s (%s)" % (n, head, src)
        if d.textlength(line, font=wf) > 490:
            raise SystemExit("wire line too wide: %r" % line)
    return counts


# ---------------------------------------------------------------------------
# Shared drawing helpers
# ---------------------------------------------------------------------------

def banner(d, box, label):
    f = font(SANS_B, 11)
    tw = d.textlength(label, font=f)
    d.rectangle([box.x, box.y, box.x + tw + 10, box.y + 16], fill=RED)
    d.text((box.x + 5, box.y + 2), label, font=f, fill=(255, 255, 255))


def num_badge(d, box, n):
    f = font(SANS_B, 11)
    t = str(n)
    wdt = max(18, int(d.textlength(t, font=f)) + 8)
    d.rectangle([box.x + box.w - wdt, box.y, box.x + box.w, box.y + 16],
                fill=RED)
    d.text((box.x + box.w - wdt + (wdt - d.textlength(t, font=f)) / 2,
            box.y + 2), t, font=f, fill=(255, 255, 255))


def key_chip(d, box, num):
    """Key number on a solid PAPER chip, bottom-right of the scene."""
    size = 20 if len(num) <= 2 else (16 if len(num) <= 4 else 13)
    f = font(SANS_B, size)
    tw = d.textlength(num, font=f)
    cx1, cy1 = box.x + box.w - 4, box.y + box.h - 4
    cx0, cy0 = cx1 - tw - 10, cy1 - size - 6
    d.rectangle([cx0, cy0, cx1, cy1], fill=PAPER, outline=INK, width=1)
    d.text((cx0 + 5, cy0 + 2), num, font=f, fill=NAVY)


def flame(d, cx, base, h, wdt):
    d.polygon([(cx - wdt, base), (cx, base - h), (cx + wdt, base)],
              fill=(240, 120, 20))
    d.polygon([(cx - wdt // 2, base), (cx, base - int(h * 0.62)),
               (cx + wdt // 2, base)], fill=RED)


def smoke(d, cx, cy, r, tone=(120, 120, 128)):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tone)


# ---------------------------------------------------------------------------
# Card scenes: compact flat illustrations for a 323x46 box. No text inside.
# ---------------------------------------------------------------------------

def scene_kyiv(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(196, 202, 210))
    d.rectangle([b.x, b.y + b.h - 6, b.x + b.w, b.y + b.h], fill=(120, 112, 100))
    # intact block, left: windows lit
    d.rectangle([b.x + 14, b.y + 8, b.x + 120, b.y + b.h - 6],
                fill=(150, 142, 128), outline=INK)
    for r in range(2):
        for c in range(4):
            d.rectangle([b.x + 24 + c * 24, b.y + 14 + r * 14,
                         b.x + 36 + c * 24, b.y + 24 + r * 14],
                        fill=(255, 214, 120))
    # collapsed block, centre: jagged top, rubble
    d.polygon([(b.x + 140, b.y + b.h - 6), (b.x + 140, b.y + 22),
               (b.x + 158, b.y + 14), (b.x + 172, b.y + 26),
               (b.x + 190, b.y + 18), (b.x + 206, b.y + 30),
               (b.x + 206, b.y + b.h - 6)], fill=(110, 102, 90), outline=INK)
    d.polygon([(b.x + 206, b.y + b.h - 6), (b.x + 226, b.y + b.h - 16),
               (b.x + 246, b.y + b.h - 6)], fill=(90, 84, 74))
    flame(d, b.x + 172, b.y + 22, 14, 7)
    smoke(d, b.x + 176, b.y + 6, 5)
    smoke(d, b.x + 188, b.y + 3, 4, tone=(150, 150, 158))
    # rescuer with stretcher, right
    d.line([(b.x + 262, b.y + 18), (b.x + 262, b.y + b.h - 6)], fill=INK, width=4)
    d.ellipse([b.x + 258, b.y + 10, b.x + 266, b.y + 18], fill=INK)
    d.line([(b.x + 262, b.y + 24), (b.x + 252, b.y + 34)], fill=INK, width=3)
    d.rectangle([b.x + 276, b.y + 28, b.x + 312, b.y + 34], fill=RED, outline=INK)


def scene_iran(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + 20], fill=SKY)
    d.rectangle([b.x, b.y + 20, b.x + b.w, b.y + b.h], fill=SEA)
    for wy in (28, 38):
        for wx in range(2, b.w - 10, 26):
            d.arc([b.x + wx, b.y + wy - 3, b.x + wx + 24, b.y + wy + 5],
                  180, 360, fill=(255, 255, 255), width=2)
    # grey warship: hull, bridge, mast, flag
    d.polygon([(b.x + 60, b.y + 22), (b.x + 250, b.y + 22),
               (b.x + 238, b.y + 36), (b.x + 72, b.y + 36)],
              fill=(90, 96, 104), outline=INK)
    d.rectangle([b.x + 150, b.y + 8, b.x + 190, b.y + 22], fill=(120, 126, 134),
                outline=INK)
    d.line([(b.x + 170, b.y + 8), (b.x + 170, b.y - 2)], fill=INK, width=3)
    d.polygon([(b.x + 170, b.y - 2), (b.x + 186, b.y + 2),
               (b.x + 170, b.y + 6)], fill=RED)
    d.rectangle([b.x + 96, b.y + 14, b.x + 120, b.y + 22], fill=(70, 76, 84),
                outline=INK)
    # small patrol boat, right
    d.polygon([(b.x + 272, b.y + 30), (b.x + 312, b.y + 30),
               (b.x + 304, b.y + 38), (b.x + 280, b.y + 38)],
              fill=(60, 66, 74), outline=INK)


def scene_hormuz(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + 14], fill=SKY)
    d.rectangle([b.x, b.y + 14, b.x + b.w, b.y + b.h], fill=SEA)
    for wy in (24, 34):
        for wx in range(2, b.w - 10, 26):
            d.arc([b.x + wx, b.y + wy - 3, b.x + wx + 24, b.y + wy + 5],
                  180, 360, fill=(255, 255, 255), width=2)
    # tanker: hull, containers, bridge tower
    d.polygon([(b.x + 30, b.y + 22), (b.x + 240, b.y + 22),
               (b.x + 228, b.y + 34), (b.x + 42, b.y + 34)],
              fill=(40, 40, 44), outline=INK)
    d.rectangle([b.x + 30, b.y + 19, b.x + 240, b.y + 22], fill=RED)
    for i, c in enumerate([(200, 60, 40), (40, 120, 70), (220, 180, 40),
                           (58, 88, 132)]):
        d.rectangle([b.x + 66 + i * 28, b.y + 10, b.x + 90 + i * 28,
                     b.y + 19], fill=c, outline=INK)
    d.rectangle([b.x + 200, b.y + 4, b.x + 224, b.y + 19],
                fill=(255, 255, 255), outline=INK)
    flame(d, b.x + 110, b.y + 12, 14, 7)
    smoke(d, b.x + 114, b.y + 2, 4)
    # second tanker, distant right
    d.rectangle([b.x + 262, b.y + 20, b.x + 312, b.y + 26], fill=(40, 40, 44))
    d.rectangle([b.x + 288, b.y + 14, b.x + 298, b.y + 20], fill=(40, 40, 44))


def scene_capitol(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + 30], fill=SKY)
    d.rectangle([b.x, b.y + 30, b.x + b.w, b.y + b.h], fill=(46, 125, 60))
    # capitol dome: drum, dome, statue spike, wings
    cx = b.x + b.w // 2
    d.rectangle([cx - 52, b.y + 22, cx + 52, b.y + 30], fill=(255, 255, 255),
                outline=INK)
    for i in range(5):
        d.rectangle([cx - 46 + i * 20, b.y + 24, cx - 40 + i * 20,
                     b.y + 30], fill=NAVY)
    d.rectangle([cx - 30, b.y + 16, cx + 30, b.y + 22], fill=(255, 255, 255),
                outline=INK)
    d.pieslice([cx - 30, b.y - 6, cx + 30, b.y + 18], 180, 360,
               fill=(255, 255, 255), outline=INK)
    d.line([(cx, b.y - 6), (cx, b.y - 12)], fill=INK, width=2)
    d.ellipse([cx - 2, b.y - 14, cx + 2, b.y - 10], fill=INK)
    # flag pole, left
    d.line([(b.x + 26, b.y + 4), (b.x + 26, b.y + 30)], fill=INK, width=2)
    d.polygon([(b.x + 26, b.y + 4), (b.x + 46, b.y + 8),
               (b.x + 26, b.y + 12)], fill=RED)


def scene_chart(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(255, 255, 255))
    for gy in (12, 24, 36):
        d.line([(b.x + 12, b.y + gy), (b.x + b.w - 8, b.y + gy)],
               fill=(225, 225, 225), width=1)
    d.line([(b.x + 12, b.y + 4), (b.x + 12, b.y + b.h - 6)], fill=INK, width=2)
    d.line([(b.x + 12, b.y + b.h - 6), (b.x + b.w - 8, b.y + b.h - 6)],
           fill=INK, width=2)
    pts = [(b.x + 22, b.y + 8), (b.x + 80, b.y + 10), (b.x + 130, b.y + 9),
           (b.x + 180, b.y + 18), (b.x + 225, b.y + 28),
           (b.x + 268, b.y + 38)]
    d.line(pts, fill=RED, width=4)
    for px, py in pts:
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=RED)
    d.polygon([(b.x + 268, b.y + 42), (b.x + 259, b.y + 30),
               (b.x + 277, b.y + 31)], fill=RED)
    for bx, bh, c in [(40, 8, (46, 125, 60)), (100, 12, (46, 125, 60)),
                      (210, 6, RED), (255, 4, RED)]:
        d.rectangle([b.x + bx, b.y + b.h - 6 - bh, b.x + bx + 20,
                     b.y + b.h - 6], fill=c)


def scene_indonesia(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(238, 228, 208))
    d.rectangle([b.x, b.y + b.h - 4, b.x + b.w, b.y + b.h],
                fill=(150, 120, 80))
    # factory block with sawtooth roof + chimney
    d.rectangle([b.x + 18, b.y + 18, b.x + 160, b.y + b.h - 4],
                fill=(128, 84, 52), outline=INK)
    for i in range(3):
        d.polygon([(b.x + 18 + i * 48, b.y + 18),
                   (b.x + 42 + i * 48, b.y + 8),
                   (b.x + 66 + i * 48, b.y + 18)], fill=(96, 56, 34))
    d.rectangle([b.x + 170, b.y + 4, b.x + 182, b.y + b.h - 4],
                fill=(110, 110, 116), outline=INK)
    for wx in range(28, 150, 20):
        d.rectangle([b.x + wx, b.y + 24, b.x + wx + 11, b.y + 32],
                    fill=(255, 214, 120))
    flame(d, b.x + 88, b.y + 12, 16, 9)
    smoke(d, b.x + 178, b.y + 2, 5)
    smoke(d, b.x + 108, b.y + 2, 4, tone=(150, 150, 150))
    # fire truck with ladder
    d.rectangle([b.x + 220, b.y + 28, b.x + 300, b.y + 38], fill=RED,
                outline=INK)
    d.rectangle([b.x + 280, b.y + 22, b.x + 300, b.y + 28], fill=RED,
                outline=INK)
    d.line([(b.x + 226, b.y + 28), (b.x + 200, b.y + 14)], fill=INK, width=3)
    for wx in (234, 284):
        d.ellipse([b.x + wx, b.y + 36, b.x + wx + 11, b.y + 45], fill=INK)


def scene_tennis(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(46, 125, 60))
    d.rectangle([b.x, b.y + b.h - 8, b.x + b.w, b.y + b.h], fill=(30, 90, 44))
    d.rectangle([b.x + 30, b.y + 6, b.x + b.w - 30, b.y + b.h - 8],
                fill=(58, 140, 74), outline=(255, 255, 255), width=2)
    d.line([(b.x + b.w // 2, b.y + 6), (b.x + b.w // 2, b.y + b.h - 8)],
           fill=(255, 255, 255), width=2)
    # net across the middle
    d.line([(b.x + 30, b.y + b.h // 2), (b.x + b.w - 30, b.y + b.h // 2)],
           fill=(255, 255, 255), width=3)
    for nx in range(b.x + 34, b.x + b.w - 30, 10):
        d.line([(nx, b.y + b.h // 2 - 4), (nx, b.y + b.h // 2 + 4)],
               fill=(200, 200, 200), width=1)
    # ball mid-air + racket arc, left
    d.ellipse([b.x + 250, b.y + 8, b.x + 262, b.y + 20], fill=(220, 240, 60),
              outline=INK)
    d.arc([b.x + 40, b.y + 2, b.x + 90, b.y + 40], 300, 60, fill=(255, 255, 255),
          width=3)
    d.line([(b.x + 78, b.y + 26), (b.x + 96, b.y + 40)], fill=(255, 255, 255),
           width=3)


def scene_football(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(46, 125, 60))
    d.rectangle([b.x, b.y + b.h - 8, b.x + b.w, b.y + b.h], fill=(30, 90, 44))
    d.line([(b.x + b.w // 2, b.y), (b.x + b.w // 2, b.y + b.h - 8)],
           fill=(255, 255, 255), width=2)
    d.ellipse([b.x + b.w // 2 - 22, b.y + 6, b.x + b.w // 2 + 22,
               b.y + b.h - 14], outline=(255, 255, 255), width=2)
    # goal, right
    d.rectangle([b.x + b.w - 52, b.y + 8, b.x + b.w - 10, b.y + 34],
                outline=(255, 255, 255), width=3)
    for gx in range(b.x + b.w - 50, b.x + b.w - 10, 8):
        d.line([(gx, b.y + 8), (gx, b.y + 34)], fill=(255, 255, 255), width=1)
    # ball + boot, left
    d.ellipse([b.x + 40, b.y + 22, b.x + 56, b.y + 38], fill=(255, 255, 255),
              outline=INK)
    d.polygon([(b.x + 42, b.y + 26), (b.x + 48, b.y + 26),
               (b.x + 46, b.y + 32), (b.x + 42, b.y + 32)], fill=INK)
    d.line([(b.x + 90, b.y + 38), (b.x + 60, b.y + 32)], fill=INK, width=4)


def scene_sudan(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(24, 28, 52))
    for sx, sy in [(30, 6), (90, 10), (180, 5), (250, 9), (300, 6)]:
        d.ellipse([b.x + sx, b.y + sy, b.x + sx + 2, b.y + sy + 2],
                  fill=(255, 255, 255))
    d.ellipse([b.x + b.w - 48, b.y + 4, b.x + b.w - 28, b.y + 24],
              fill=(250, 214, 120))
    d.rectangle([b.x, b.y + b.h - 6, b.x + b.w, b.y + b.h],
                fill=(120, 100, 80))
    # damaged house, left: broken roof, smoke
    d.rectangle([b.x + 16, b.y + 22, b.x + 110, b.y + b.h - 6],
                fill=(150, 130, 100), outline=INK)
    d.polygon([(b.x + 10, b.y + 22), (b.x + 63, b.y + 8),
               (b.x + 90, b.y + 22)], fill=(120, 70, 44))
    d.polygon([(b.x + 90, b.y + 22), (b.x + 116, b.y + 22),
               (b.x + 104, b.y + 12)], fill=(90, 60, 40))
    smoke(d, b.x + 66, b.y + 4, 4, tone=(150, 150, 158))
    # quadcopter drone, centre-right, with rotor blur
    cx, cy = b.x + 210, b.y + 16
    d.rectangle([cx - 14, cy - 4, cx + 14, cy + 4], fill=(200, 200, 200),
                outline=INK)
    for ox in (-18, 18):
        d.ellipse([cx + ox - 8, cy - 3, cx + ox + 8, cy + 3],
                  fill=(180, 180, 180))
        d.line([(cx + ox - 12, cy), (cx + ox + 12, cy)], fill=(255, 255, 255),
               width=2)
    d.line([(cx - 14, cy), (cx - 20, cy - 8)], fill=(200, 200, 200), width=2)
    d.line([(cx + 14, cy), (cx + 20, cy - 8)], fill=(200, 200, 200), width=2)


SCENES = {
    "kyiv": scene_kyiv,
    "iran": scene_iran,
    "hormuz": scene_hormuz,
    "capitol": scene_capitol,
    "chart": scene_chart,
    "indonesia": scene_indonesia,
    "tennis": scene_tennis,
    "football": scene_football,
    "sudan": scene_sudan,
}


# ---------------------------------------------------------------------------
# Hero scene: the empty COP31 summit hall (compact version of v5's scene).
# ---------------------------------------------------------------------------

def _chair(d, cx, top, wdt, hgt, fill, tipped=False):
    if tipped:
        d.rectangle([cx - wdt // 2, top + hgt - 9, cx + wdt // 2,
                     top + hgt - 3], fill=fill, outline=INK)
        d.rectangle([cx + wdt // 2 - 4, top + 4, cx + wdt // 2,
                     top + hgt - 3], fill=fill, outline=INK)
        return
    back_h = int(hgt * 0.55)
    d.rectangle([cx - wdt // 2, top, cx + wdt // 2, top + back_h], fill=fill,
                outline=INK)
    d.rectangle([cx - wdt // 2, top + back_h, cx + wdt // 2, top + back_h + 4],
                fill=fill, outline=INK)
    for lx in (cx - wdt // 2 + 2, cx + wdt // 2 - 2):
        d.line([(lx, top + back_h + 4), (lx, top + hgt)], fill=INK, width=2)


def scene_summit(d, b):
    d.rectangle([b.x, b.y, b.x + b.w, b.y + b.h], fill=(188, 206, 228))
    d.rectangle([b.x, b.y + 96, b.x + b.w, b.y + b.h], fill=(168, 188, 212))
    # side screens: globe left, bars right
    d.rectangle([b.x + 10, b.y + 8, b.x + 74, b.y + 52], fill=(240, 246, 252),
                outline=INK, width=2)
    cx, cy, r = b.x + 42, b.y + 30, 16
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=NAVY, width=2)
    d.ellipse([cx - r // 2, cy - r, cx + r // 2, cy + r], outline=NAVY,
              width=1)
    d.line([(cx - r, cy), (cx + r, cy)], fill=NAVY, width=1)
    d.rectangle([b.x + b.w - 74, b.y + 8, b.x + b.w - 10, b.y + 52],
                fill=(240, 246, 252), outline=INK, width=2)
    base = b.y + 48
    d.line([(b.x + b.w - 66, base), (b.x + b.w - 16, base)], fill=INK, width=1)
    for i, bh in enumerate((10, 17, 25)):
        bx = b.x + b.w - 62 + i * 17
        d.rectangle([bx, base - bh, bx + 11, base],
                    fill=STEEL if i < 2 else RED)
    # giant 0 over the empty hall
    zf = font(SANS_B, 64)
    zw = d.textlength("0", font=zf)
    zx, zy = b.x + (b.w - zw) / 2, b.y + 0
    for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        d.text((zx + ox, zy + oy), "0", font=zf, fill=PAPER)
    d.text((zx, zy), "0", font=zf, fill=RED)
    cap = "fossil-fuel mentions in the final draft"
    cf = font(SANS_B, 11)
    cw_ = d.textlength(cap, font=cf)
    d.text((b.x + (b.w - cw_) / 2, b.y + 64), cap, font=cf, fill=NAVY)
    # long summit table with nameplates, two already knocked flat
    d.rectangle([b.x + 12, b.y + 88, b.x + b.w - 12, b.y + 97],
                fill=(146, 108, 66), outline=INK, width=1)
    for i, cx in enumerate(range(b.x + 40, b.x + b.w - 24, 52)):
        if i in (2, 5):
            d.polygon([(cx - 10, b.y + 84), (cx + 10, b.y + 86),
                       (cx + 10, b.y + 93), (cx - 10, b.y + 91)],
                      fill=(255, 255, 255), outline=INK)
        else:
            d.rectangle([cx - 10, b.y + 82, cx + 10, b.y + 90],
                        fill=(255, 255, 255), outline=INK)
    # podium at the centre, facing rows of empty chairs
    mid = b.x + b.w // 2
    d.polygon([(mid - 11, b.y + 101), (mid + 11, b.y + 101),
               (mid + 15, b.y + 122), (mid - 15, b.y + 122)], fill=NAVY,
              outline=INK)
    for i, cx in enumerate(range(b.x + 40, b.x + b.w - 24, 52)):
        if abs(cx - mid) < 30:
            continue
        _chair(d, cx, b.y + 103, 22, 20, NAVY, tipped=(i == 5))
    for i, cx in enumerate(range(b.x + 28, b.x + b.w - 12, 52)):
        _chair(d, cx, b.y + 124, 24, 15, STEEL, tipped=(i == 1))


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def draw_masthead(d, counts):
    centred(d, 4, "THE MORNING ATLAS", font(SERIF_B, SIZE_TITLE))
    hline(d, 52, width=2)
    centred(d, 56, "MONDAY 23 NOVEMBER 2026", font(SERIF_B, SIZE_DATE))
    sub = "%d stories  \u00b7  %d regions  \u00b7  one page" % (
        sum(counts.values()), len(counts))
    centred(d, 90, sub, font(SANS, 12), fill=SOFT)
    hline(d, 106, width=1, fill=LINE)


def draw_strip(d):
    cell_w, gap, y0, hh = 242, 8, 112, 38
    x = EDGE
    for num, label in STRIP:
        d.rectangle([x, y0, x + cell_w, y0 + hh], outline=LINE, width=1)
        nf = font(SANS_B, SIZE_STRIP_NUM)
        nw = d.textlength(num, font=nf)
        d.text((x + (cell_w - nw) / 2, y0 + 1), num, font=nf, fill=NAVY)
        lf = font(SANS, 11)
        if d.textlength(label, font=lf) > cell_w - 10:
            raise SystemExit("strip label too wide: %r" % label)
        centred(d, y0 + 24, label, lf, fill=SOFT, x0=x, x1=x + cell_w)
        x += cell_w + gap


def draw_hero(d):
    box = Box(EDGE, 156, SPAN, 148)
    d.rectangle([box.x, box.y, box.x + box.w, box.y + box.h], outline=INK,
                width=2)
    scene_summit(d, Box(box.x + 1, box.y + 1, 380, box.h - 2))
    banner(d, Box(box.x + 1, box.y + 1, 0, 0), "COP31 \u00b7 ANTALYA")
    num_badge(d, Box(box.x + 1, box.y + 1, 380, 0), 1)
    rx = 412
    d.text((rx, box.y + 8), "1  \u00b7  THE BIG STORY",
           font=font(SANS_B, 12), fill=RED)
    hf = font(SANS_B, SIZE_HERO_HEAD)
    lines = wrapped(d, HERO["headline"], hf, PAGE_W - EDGE - rx)
    if len(lines) > 2:
        raise SystemExit("hero headline wraps past 2 lines")
    for i, ln in enumerate(lines):
        d.text((rx, box.y + 28 + i * 32), ln, font=hf, fill=INK)
    bf = font(SANS, 13)
    blines = wrapped(d, HERO["body"], bf, PAGE_W - EDGE - rx)
    if len(blines) > 2:
        raise SystemExit("hero body too long: %d lines" % len(blines))
    for i, ln in enumerate(blines):
        d.text((rx, box.y + 96 + i * 17), ln, font=bf, fill=INK)
    d.text((rx, box.y + box.h - 16), HERO["src"], font=font(SANS_I, 11),
           fill=SOFT)


def draw_cards(d):
    y0, ch, gap, cell_w = 310, 130, 8, 325
    for i, card in enumerate(CARDS):
        row, col = divmod(i, 3)
        x = EDGE + col * (cell_w + gap)
        y = y0 + row * (ch + gap)
        d.rectangle([x, y, x + cell_w, y + ch], outline=INK, width=1)
        scene = Box(x + 1, y + 1, cell_w - 2, 46)
        SCENES[card["scene"]](d, scene)
        if card["key"] is not None:
            key_chip(d, scene, card["key"])
        banner(d, scene, card["banner"])
        num_badge(d, scene, card["n"])
        hs = fit(d, card["headline"], SIZE_CARD_HEAD_START,
                 SIZE_CARD_HEAD_MIN, cell_w - 12)
        hf = font(SANS_B, hs)
        hlines = wrapped(d, card["headline"], hf, cell_w - 12)
        if len(hlines) > 2 or hs < SIZE_CARD_HEAD_MIN:
            raise SystemExit("card headline fails floor: %r"
                             % card["headline"])
        for j, ln in enumerate(hlines):
            d.text((x + 6, y + 50 + j * 21), ln, font=hf, fill=INK)
        bf = font(SANS, SIZE_BODY)
        blines = wrapped(d, card["body"], bf, cell_w - 12)
        if len(blines) > 2:
            raise SystemExit("card body wraps past 2 lines: %r"
                             % card["headline"])
        for j, ln in enumerate(blines):
            d.text((x + 6, y + 94 + j * 13), ln, font=bf, fill=INK)
        d.text((x + 6, y + 120), card["src"], font=font(SANS_I, 9),
               fill=SOFT)


def draw_wire(d):
    y0 = 718
    d.text((EDGE, y0), "THE WIRE \u2014 THE OTHER 25 STORIES",
           font=font(SANS_B, 12), fill=RED)
    hline(d, y0 + 16, width=1, fill=LINE)
    wf = font(SANS_B, SIZE_WIRE)
    sf = font(SANS, 10)
    col_a, col_b = WIRE[:13], WIRE[13:]
    for col_idx, col in enumerate((col_a, col_b)):
        x = EDGE + col_idx * 502
        for i, (n, _, head, src) in enumerate(col):
            y = y0 + 22 + i * 14
            d.text((x, y), "%d \u00b7 " % n, font=font(SANS_B, SIZE_WIRE),
                   fill=RED)
            nx = x + d.textlength("%d \u00b7 " % n, font=wf)
            d.text((nx, y), head, font=wf, fill=INK)
            sx = nx + d.textlength(head, font=wf) + 4
            d.text((sx, y + 1), "(%s)" % src, font=sf, fill=SOFT)


def draw_regions(d, counts):
    f = font(SANS_B, 13)
    x, y, hh = EDGE, 922, 24
    for key, name in REGIONS:
        label = "%s %d" % (name, counts[key])
        tw = d.textlength(label, font=f)
        d.rounded_rectangle([x, y, x + tw + 18, y + hh], radius=6, fill=NAVY)
        d.text((x + 9, y + 4), label, font=f, fill=(255, 255, 255))
        x += tw + 18 + 8
    if x - 8 > PAGE_W - EDGE:
        raise SystemExit("region chips overflow")


def draw_datecheck(d):
    y0, hh = 952, 52
    d.rectangle([EDGE, y0, PAGE_W - EDGE, y0 + hh], outline=RED, width=2)
    d.text((EDGE + 10, y0 + 3), "DATE CHECK \u2014 WHAT WE LEFT OUT",
           font=font(SANS_B, 11), fill=RED)
    sf = font(SANS_B, 11)
    sw = d.textlength(STAMP, font=sf)
    d.text((PAGE_W - EDGE - 10 - sw, y0 + 3), STAMP, font=sf, fill=RED)
    for i, ln in enumerate(DATE_LINES):
        d.text((EDGE + 10, y0 + 19 + i * 12), ln, font=font(SANS, 10),
               fill=INK)


def draw_footer(d):
    centred(d, 1008,
            "All 35 stories happened or were first reported on Monday "
            "23 November 2026.", font(SANS_I, 10), fill=INK)


def poster():
    img = Image.new("RGB", (PAGE_W, PAGE_H), CREAM)
    d = ImageDraw.Draw(img)
    counts = audit_ledger(d)
    draw_masthead(d, counts)
    draw_strip(d)
    draw_hero(d)
    draw_cards(d)
    draw_wire(d)
    draw_regions(d, counts)
    draw_datecheck(d)
    draw_footer(d)
    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "entry.png")
    img = poster()
    img.save(out, "PNG", optimize=True)
    data = open(out, "rb").read()
    print("entry.png", len(data), "bytes", hashlib.sha256(data).hexdigest())
    if len(data) > 1048576:
        print("TOO BIG", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
