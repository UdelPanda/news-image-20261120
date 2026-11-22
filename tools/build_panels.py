#!/usr/bin/env python3
"""Panel builder for the "THE WORLD IN ONE DAY" entry (news-image-20261120).

Renders the twenty page panels with PIL at 3x supersampling and stores them
in ../assets/ as zlib-compressed raw RGB plus a manifest.json.  The stdlib
assembler in ../main.py composites those panels into the final 1024x1024
page, so everything the sandbox program needs is pre-rendered here with the
full local toolchain (real fonts, generated scene art).

Run:  python3 tools/build_panels.py
"""

import json
import math
import os
import random
import zlib

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

SS = 3  # supersampling factor

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY_DIR = os.path.dirname(HERE)
ASSETS_DIR = os.path.join(ENTRY_DIR, "assets")
ART_DIR = os.path.join(ENTRY_DIR, "assets_art")

PAGE_BG = (247, 241, 227)
CARD_BG = (253, 250, 240)
INK = (17, 19, 33)
NAVY = (16, 33, 67)
GREY_TEXT = (88, 84, 78)
SUMMARY_INK = (54, 51, 47)
RED = (176, 42, 42)
BADGE_RED = (171, 31, 31)
DECK_RED = (148, 43, 35)
RULE_SOFT = (196, 186, 166)

REGION_COLORS = {
    "apac": (198, 78, 30),
    "europe": (36, 84, 143),
    "americas": (176, 42, 42),
    "mideast": (122, 79, 163),
    "africa": (30, 138, 76),
    "oceania": (18, 147, 168),
    "world": (92, 92, 104),
}

FONT_DIR = "/usr/share/fonts/truetype"
SERIF = os.path.join(FONT_DIR, "liberation", "LiberationSerif-Regular.ttf")
SERIF_B = os.path.join(FONT_DIR, "liberation", "LiberationSerif-Bold.ttf")
SERIF_I = os.path.join(FONT_DIR, "liberation", "LiberationSerif-Italic.ttf")
SANS = os.path.join(FONT_DIR, "liberation", "LiberationSans-Regular.ttf")
SANS_B = os.path.join(FONT_DIR, "liberation", "LiberationSans-Bold.ttf")

_font_cache = {}


def font(path, size):
    """Font at a size given in final (1x) pixels."""
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, int(round(size * SS)))
    return _font_cache[key]


def U(v):
    """Scale a 1x measurement to supersampled pixels."""
    return int(round(v * SS))


# ---------------------------------------------------------------------------
# DATA — every story below happened or was first reported on Fri 20 Nov 2026.
# ---------------------------------------------------------------------------

MASTHEAD = "THE WORLD IN ONE DAY"
DATE_LINE = "Friday 20 November 2026"
TOP_LEFT = "ONE DAY OF WORLD NEWS · ONE PICTURE"
TOP_RIGHT = "37 STORIES · 7 REGIONS"
DECK = ("Akvan hits India · Missiles hit Kyiv · COP31 deadlocked · "
        "AI sell-off sinks Asia, then Wall Street")

# (figure, caption, red?)
STATS = [
    ("300,000+", "EVACUATED AHEAD OF CYCLONE AKVAN", False),
    ("~30", "BALLISTIC MISSILES FIRED AT KYIV", True),
    ("-17%", "TAIWAN'S WEEK, WORST IN 35 YEARS", True),
    ("$3,512", "GOLD'S FRIDAY CLOSE, A 14-MONTH LOW", False),
    ("118", "PHILLIPS' HISTORIC CENTURY VS INDIA", False),
    ("8 YRS", "BEPICOLOMBO'S TRIP TO MERCURY", False),
]

# (label, region, width in px) — widths sum to the 972px panel width.
TABS = [
    ("ASIA-PACIFIC 10", "apac", 164),
    ("EUROPE 7", "europe", 134),
    ("AMERICAS 8", "americas", 145),
    ("MIDEAST 4", "mideast", 137),
    ("AFRICA 1", "africa", 127),
    ("OCEANIA 4", "oceania", 138),
    ("WORLD 3", "world", 127),
]

# Top cards: num, region, art key (or "chart"), banner, kicker, source,
# headline, summary, map pin (lon, lat) or None.
TOP_STORIES = [
    (1, "apac", "cyclone", "CYCLONE AKVAN - LANDFALL",
     "ODISHA, INDIA · CYCLONE", "IMD · The Hindu",
     "Cyclone Akvan makes landfall in eastern India",
     "Morning landfall near Gopalpur: 300,000+ evacuated, winds 70-80 "
     "gusting 90 km/h, 423 rescue teams out, no deaths reported.",
     (84.9, 19.3)),
    (2, "europe", "kyiv", "KYIV - MISSILE BARRAGE",
     "KYIV, UKRAINE · WAR", "Kyiv Post · Reuters",
     "Russia fires wave of ~30 ballistic missiles at Kyiv",
     "Missiles hit three Dnipro bridges in the biggest bridge attack of "
     "the war; 3 killed and 15 hurt as ~30 missiles fall in seven waves.",
     (30.5, 50.4)),
    (3, "apac", "chart", "ASIA - AI SELL-OFF",
     "TOKYO · MARKETS", "Reuters",
     "AI sell-off sinks Asia to worst week since 2020",
     "Nikkei -5.1%, KOSPI -5.2%; Taiwan -6.6% on the day, -17% on the "
     "week. Wall Street: Nasdaq -5.2% wipes out 2026 gains.",
     (139.7, 35.7)),
]

# Mid cards: num, region, scene key, tag, headline, summary (source folded in).
MID_STORIES = [
    (4, "europe", "cop31", "ANTALYA · CLIMATE",
     "COP31 endgame: no deal in sight",
     "Final day of the summit; the draft still names no fossil fuels and "
     "Panama threatens a block. (AFP)",
     (30.7, 36.9)),
    (5, "mideast", "iraq", "BAGHDAD · IRAQ",
     "Iraqi troops enter militia stronghold",
     "Forces deploy in Jurf al-Sakhar to curb Kataib Hezbollah and its "
     "oil-smuggling ring. (Reuters)",
     (44.2, 32.9)),
    (6, "world", "mercury", "SPACE · MERCURY",
     "BepiColombo reaches Mercury after 8 years",
     "ESA/JAXA probe ends a 6bn-mile trip; orbit insertion set for "
     "Saturday. (ESA · BBC)",
     None),
    (7, "mideast", "hormuz", "HORMUZ · SEA",
     "Tanker ablaze after projectile strike",
     "Outbound tanker hit 8nm north of Khasab; fire aboard, no "
     "casualties. Iran claims a mine. (UKMTO)",
     (56.3, 26.6)),
    (8, "europe", "paris", "PARIS · DIPLOMACY",
     "Harris meets Macron at the Élysée",
     "Ex-VP holds a brief courtesy meeting with the French president, "
     "her husband at her side. (Politico)",
     (2.35, 48.86)),
    (9, "oceania", "quake", "PACIFIC · QUAKE",
     "5.6 quake rattles New Caledonia",
     "Shaking near the Loyalty Islands; no tsunami threat is issued. "
     "(USGS)",
     (171.2, -24.7)),
    (10, "europe", "youth", "EUROPE · STUDENTS",
     "Students march across Europe",
     "Youth march in Germany, France, Britain and more over living "
     "costs and military spending. (AP)",
     (13.4, 52.5)),
    (11, "apac", "japan", "TOKYO · ECONOMY",
     "Japan inflation 2.2%; BoJ hike eyed",
     "Oct core CPI quickens from 2.1%; a December hike is in play. "
     "(CNBC)",
     (139.7, 35.7)),
    (12, "apac", "china", "BEIJING · RATES",
     "China holds lending rates again",
     "1-year LPR stays 3.0% and 5-year 3.5% for an 18th straight month. "
     "(Reuters)",
     (116.4, 39.9)),
    (13, "world", "pill", "BARCELONA · HEALTH",
     "Cancer pill shrinks tumours 60.7%",
     "Daraxonrasib plus chemo helps 61 patients with pancreatic "
     "cancer; tumours vanish in 8.2%. (EORTC)",
     (2.17, 41.4)),
    (14, "africa", "malawi", "MALAWI · FUEL",
     "Fuel crisis: queues, 20-litre cap",
     "Petrol at $3.24 a litre; the ministry blames a forex shortage. "
     "(Al Jazeera)",
     (35.0, -13.5)),
    (15, "europe", "italy", "ROME · LABOUR",
     "CGIL calls 24-hour general strike",
     "1m+ march in 100+ cities; students clash with police in Rome. "
     "(AFP)",
     (12.5, 41.9)),
]

# (num, place, text, source) — rendered as "num PLACE - text (source)".
ALSO_STORIES = [
    (16, "SEOUL", "Samsung puts Choi over mobile", "Reuters"),
    (17, "NEW YORK", "Nasdaq -5.2%, wipes out 2026 gains", "Reuters"),
    (18, "NEW YORK", "S&P -3.7%, seventh straight loss", "AP"),
    (19, "NEW YORK", "Dow -1.9%, enters correction", "Reuters"),
    (20, "NEW YORK", "Anthropic -9% to $88.30 on day two", "CNN"),
    (21, "NEW YORK", "PHLX chip index sinks 9.2%", "Reuters"),
    (22, "NEW YORK", "Silver -7.4% to $41.04", "WSJ"),
    (23, "WASHINGTON", "Vance won't say he'd order Iran strikes", "Reuters"),
    (24, "LONDON", "FTSE heads for worst week in 8 months", "Reuters"),
    (25, "ROME", "Italian rail freight halts 23 hours", "ANSA"),
    (26, "HORMUZ", "Brent settles $92.57, week -3.4%", "Reuters"),
    (27, "SANAA", "Houthis warn Saudi Red Sea ports", "Reuters"),
    (28, "TAIPEI", "Taiwan curbs in force as Taiex sheds 2,394 pts", "AFP"),
    (29, "MUMBAI", "RBI seen hiking to 5.75% in Dec", "Reuters"),
    (30, "NEW DELHI", "Forex reserves fall to $705bn", "Reuters"),
    (31, "WELLINGTON", "Phillips' historic 118 vs India", "ICC"),
    (32, "FIJI", "Xavier weakens to Cat 2, gales hit N. Cooks", "RSMC Nadi"),
    (33, "VANUATU", "M5.1 quake off Port-Olry", "USGS"),
    (34, "NEW YORK", "Gold ends at $3,512, week -9.5%", "WSJ"),
    (35, "SEOUL", "Kospi falls 5.2% in the AI sell-off", "Reuters"),
    (36, "ANTALYA", "Panama-led bloc demands fossil-fuel text", "Reports"),
    (37, "TOKYO", "SoftBank slides 14.5%", "Reuters"),
]

DATE_CHECK = ("DATE CHECK - All 37 stories happened or were first reported "
              "Fri 20 Nov 2026. Left out: Shenzhen summit, ICJ ruling, Kyiv "
              "embassy damage, Pete Rose pardon, Florida execution, UK drone "
              "pledge, Senate bill (all Thu); Kenya Ebola discharge (11 Nov).")

FOOTER_LINE = ("Sources: Reuters · AP · AFP · BBC · Al Jazeera · IMD · USGS · "
               "ESA · ANSA · ICC · Kyiv Post · The Hindu · RSMC Nadi · EORTC · "
               "Politico - original illustrations, drawn from the day's wire "
               "reports.")

# Where each numbered pin sits on the dotted map: num -> (lon, lat, dx, dy).
PIN_NUDGE = {
    1: (0, 0), 2: (0, -2), 3: (-4, 0), 4: (-7, 5), 5: (9, 3),
    7: (4, 8), 8: (-8, 1), 9: (0, 0), 10: (3, -6), 11: (8, 8),
    12: (0, 0), 13: (-9, 8), 14: (0, 0), 15: (6, 7),
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def tracked_width(text, fnt, tracking):
    """Width (1x px) of text drawn with per-character tracking."""
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    w = 0.0
    for ch in text:
        w += d.textlength(ch, font=fnt) / SS + tracking
    return w - (tracking if text else 0)


def draw_tracked(d, x, y, text, fnt, fill, tracking):
    """Draw letter-spaced text with its left edge / top at (x, y) in 1x px."""
    cx = x
    for ch in text:
        d.text((U(cx), U(y)), ch, font=fnt, fill=fill)
        cx += d.textlength(ch, font=fnt) / SS + tracking
    return cx


def draw_centered(d, cx, y, text, fnt, fill, tracking=0.0):
    w = tracked_width(text, fnt, tracking)
    draw_tracked(d, cx - w / 2, y, text, fnt, fill, tracking)


def draw_right(d, xr, y, text, fnt, fill, tracking=0.0):
    w = tracked_width(text, fnt, tracking)
    draw_tracked(d, xr - w, y, text, fnt, fill, tracking)


def wrap_text(text, fnt, max_w):
    """Greedy word wrap; widths measured in 1x px."""
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=fnt) / SS <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Scene art: generated illustrations, graded as one set; a hand-drawn chart;
# four small PIL scenes for the replacement mid cards.
# ---------------------------------------------------------------------------

# Anchor (fx, fy) = the point of the source image kept at the crop centre.
ART_ANCHORS = {
    "cyclone": (0.42, 0.38),
    "kyiv": (0.50, 0.52),
    "cop31": (0.50, 0.42),
    "mercury": (0.50, 0.40),
    "hormuz": (0.50, 0.45),
    "quake": (0.50, 0.50),
    "japan": (0.50, 0.30),
    "china": (0.50, 0.30),
    "malawi": (0.50, 0.55),
    "italy": (0.50, 0.42),
}


def _grade(img, seed):
    img = ImageEnhance.Color(img).enhance(0.94)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Brightness(img).enhance(1.01)
    rng = random.Random(seed)
    noise = Image.frombytes("L", img.size, rng.randbytes(img.size[0] * img.size[1]))
    noise = noise.point(lambda v: 118 + (v % 21))
    img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.05)
    return img


def art_scene(key, w, h, seed):
    """Crop the generated art for `key` to a w x h (1x) slot, graded."""
    src = Image.open(os.path.join(ART_DIR, key + ".webp")).convert("RGB")
    sw, sh = src.size
    target = (w * SS) / (h * SS)
    fx, fy = ART_ANCHORS[key]
    if sw / sh > target:  # too wide: crop the width
        cw = int(sh * target)
        cx = min(max(int(fx * sw), cw // 2), sw - cw // 2)
        box = (cx - cw // 2, 0, cx + cw // 2, sh)
    else:                 # too tall: crop the height
        ch = int(sw / target)
        cy = min(max(int(fy * sh), ch // 2), sh - ch // 2)
        box = (0, cy - ch // 2, sw, cy + ch // 2)
    img = src.crop(box).resize((U(w), U(h)), Image.LANCZOS)
    return _grade(img, seed)


def chart_scene(w, h):
    """Markets panel: descending candlesticks on a dark exchange screen."""
    img = Image.new("RGB", (U(w), U(h)), (12, 19, 43))
    d = ImageDraw.Draw(img)
    # faint grid
    for gy in range(18, h, 24):
        d.line([(0, U(gy)), (U(w), U(gy))], fill=(38, 52, 92), width=U(1))
    for gx in range(20, w, 38):
        d.line([(U(gx), 0), (U(gx), U(h))], fill=(30, 43, 80), width=U(1))
    # candles sliding down to the right
    rng = random.Random(41)
    n = 13
    tops = []
    for i in range(n):
        cx = 16 + i * 17.5
        top = 26 + i * 5.6 + rng.uniform(-3, 3)
        body = rng.uniform(9, 15)
        col = (203, 55, 45) if i % 3 else (232, 92, 55)
        d.line([(U(cx), U(top - 6)), (U(cx), U(top + body + 6))],
               fill=(235, 120, 95), width=U(1.4))
        d.rectangle([U(cx - 5.5), U(top), U(cx + 5.5), U(top + body)], fill=col)
        tops.append((cx, top + body / 2))
    d.line([(U(x), U(y)) for x, y in tops], fill=(255, 96, 74), width=U(2))
    # big down arrow, lower right: thick shaft + triangular head
    ax, ay = w - 88, h - 66
    d.line([(U(ax), U(ay)), (U(ax + 40), U(ay + 40))], fill=(214, 48, 40),
           width=U(13))
    d.polygon([(U(ax + 18), U(ay + 30)), (U(ax + 66), U(ay + 44)),
               (U(ax + 52), U(ay + 66))], fill=(214, 48, 40))
    # ticker chips (first chip clears the number badge)
    chips = ["NIKKEI -5.1%", "TAIEX -6.6%", "KOSPI -5.2%"]
    fnt = font(SANS_B, 9.5)
    cx = 44
    for chip in chips:
        tw = d.textlength(chip, font=fnt) / SS
        d.rounded_rectangle([U(cx), U(6), U(cx + tw + 14), U(24)],
                            radius=U(3), fill=(92, 22, 26))
        d.text((U(cx + 7), U(9.5)), chip, font=fnt, fill=(255, 224, 214))
        cx += tw + 22
    return img


def _gradient(w, h, top, bottom):
    img = Image.new("RGB", (U(w), U(h)))
    d = ImageDraw.Draw(img)
    for i in range(U(h)):
        t = i / max(1, U(h) - 1)
        col = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        d.line([(0, i), (U(w), i)], fill=col)
    return img


def scene_iraq(w, h):
    """Checkpoint on a desert road: barrier arm, guard post, sun."""
    img = _gradient(w, h, (219, 168, 99), (240, 210, 156))
    d = ImageDraw.Draw(img)
    d.ellipse([U(w - 52), U(3), U(w - 38), U(17)], fill=(252, 228, 164))
    d.rectangle([0, U(h - 10), U(w), U(h)], fill=(172, 132, 86))
    # road converging to the checkpoint
    d.polygon([(U(98), U(h)), (U(140), U(h)), (U(126), U(h - 11)),
               (U(112), U(h - 11))], fill=(74, 70, 62))
    # armoured vehicle silhouette, left
    d.rounded_rectangle([U(14), U(h - 13), U(48), U(h - 4)], radius=U(2),
                        fill=(56, 52, 46))
    d.rectangle([U(24), U(h - 17), U(38), U(h - 12)], fill=(56, 52, 46))
    d.ellipse([U(18), U(h - 6), U(25), U(h + 1)], fill=(30, 28, 26))
    d.ellipse([U(37), U(h - 6), U(44), U(h + 1)], fill=(30, 28, 26))
    # guard hut
    d.rectangle([U(158), U(h - 16), U(178), U(h - 4)], fill=(92, 80, 64))
    d.polygon([(U(155), U(h - 16)), (U(181), U(h - 16)), (U(168), U(h - 21))],
              fill=(70, 60, 48))
    # barrier post + striped arm
    d.rectangle([U(58), U(h - 20), U(62), U(h - 3)], fill=(60, 54, 48))
    arm = [(60, h - 19), (122, h - 15.5)]
    d.line([(U(arm[0][0]), U(arm[0][1])), (U(arm[1][0]), U(arm[1][1]))],
           fill=(245, 242, 236), width=U(3.4))
    for i in range(4):
        t0 = i / 4
        x0 = arm[0][0] + (arm[1][0] - arm[0][0]) * t0
        y0 = arm[0][1] + (arm[1][1] - arm[0][1]) * t0
        x1 = arm[0][0] + (arm[1][0] - arm[0][0]) * (t0 + 0.13)
        y1 = arm[0][1] + (arm[1][1] - arm[0][1]) * (t0 + 0.13)
        d.line([(U(x0), U(y0)), (U(x1), U(y1))], fill=(198, 48, 40),
               width=U(3.4))
    return img


def scene_paris(w, h):
    """Dusk over Paris rooftops: palace facade, tower, tricolore, moon."""
    img = _gradient(w, h, (34, 44, 88), (122, 92, 112))
    d = ImageDraw.Draw(img)
    d.ellipse([U(w - 34), U(3), U(w - 23), U(14)], fill=(246, 238, 205))
    sil = (22, 24, 42)
    # rooftop band
    d.rectangle([0, U(h - 13), U(w), U(h)], fill=sil)
    for rx, rw, rh in [(4, 26, 6), (36, 20, 9), (150, 24, 7), (182, 30, 10),
                       (216, 18, 6)]:
        d.rectangle([U(rx), U(h - 13 - rh), U(rx + rw), U(h - 13)], fill=sil)
    # Eiffel-style tower
    tx = 66
    d.polygon([(U(tx), U(h - 4)), (U(tx + 9), U(6)), (U(tx + 18), U(h - 4))],
              outline=(16, 18, 34), width=U(2.2))
    d.line([(U(tx + 3.4), U(h - 15)), (U(tx + 14.6), U(h - 15))],
           fill=(16, 18, 34), width=U(1.6))
    d.line([(U(tx + 5.6), U(h - 23)), (U(tx + 12.4), U(h - 23))],
           fill=(16, 18, 34), width=U(1.4))
    # palace facade, centre
    d.rectangle([U(102), U(h - 17), U(146), U(h - 3)], fill=(216, 200, 170))
    d.polygon([(U(100), U(h - 17)), (U(148), U(h - 17)), (U(124), U(h - 23))],
              fill=(196, 178, 148))
    for i in range(5):
        cx = 107 + i * 8
        d.line([(U(cx), U(h - 15)), (U(cx), U(h - 5))], fill=(120, 104, 82),
               width=U(1.4))
    # tricolore on a pole
    d.line([(U(196), U(h - 26)), (U(196), U(h - 8))], fill=(230, 228, 220),
           width=U(1.2))
    for i, col in enumerate([(40, 70, 160), (245, 245, 245), (200, 50, 50)]):
        d.rectangle([U(196 + i * 4), U(h - 26), U(200 + i * 4), U(h - 19)],
                    fill=col)
    return img


def scene_youth(w, h):
    """Student march: placards on sticks above a row of heads."""
    img = Image.new("RGB", (U(w), U(h)), (243, 238, 222))
    d = ImageDraw.Draw(img)
    cards = [(18, 8, "circle", (198, 48, 40)), (52, 5, "star", (36, 84, 143)),
             (88, 9, "sun", (226, 140, 40)), (124, 6, "house", (30, 138, 76)),
             (160, 8, "flag", (122, 79, 163)), (196, 5, "circle", (18, 147, 168))]
    for x, y, kind, col in cards:
        d.line([(U(x + 9), U(h)), (U(x + 9), U(y + 13))], fill=(120, 100, 80),
               width=U(1.4))
        d.rectangle([U(x), U(y), U(x + 18), U(y + 13)], fill=(252, 250, 244),
                    outline=(150, 140, 120), width=U(1))
        if kind == "circle":
            d.ellipse([U(x + 5), U(y + 2.5), U(x + 13), U(y + 10.5)], fill=col)
        elif kind == "star":
            pts = []
            for k in range(10):
                ang = -math.pi / 2 + k * math.pi / 5
                r = 4.6 if k % 2 == 0 else 2.0
                pts.append((U(x + 9 + r * math.cos(ang)),
                            U(y + 6.5 + r * math.sin(ang))))
            d.polygon(pts, fill=col)
        elif kind == "sun":
            d.ellipse([U(x + 6), U(y + 3.5), U(x + 12), U(y + 9.5)], fill=col)
            for k in range(8):
                ang = k * math.pi / 4
                d.line([(U(x + 9 + 4.4 * math.cos(ang)),
                         U(y + 6.5 + 4.4 * math.sin(ang))),
                        (U(x + 9 + 6 * math.cos(ang)),
                         U(y + 6.5 + 6 * math.sin(ang)))],
                       fill=col, width=U(1))
        elif kind == "house":
            d.polygon([(U(x + 4), U(y + 6)), (U(x + 9), U(y + 2)),
                       (U(x + 14), U(y + 6))], fill=col)
            d.rectangle([U(x + 5.5), U(y + 6), U(x + 12.5), U(y + 11)],
                        fill=col)
        else:
            d.polygon([(U(x + 3), U(y + 2)), (U(x + 15), U(y + 4)),
                       (U(x + 3), U(y + 7))], fill=col)
    # crowd heads along the bottom
    tones = [(146, 102, 72), (198, 150, 110), (110, 76, 52), (226, 184, 140),
             (88, 60, 44), (172, 128, 92)]
    rng = random.Random(9)
    x = 2
    while x < w - 6:
        tone = tones[rng.randrange(len(tones))]
        r = rng.uniform(3.4, 4.6)
        d.ellipse([U(x), U(h - 2 * r - 1), U(x + 2 * r), U(h - 1)], fill=tone)
        x += 2 * r + rng.uniform(0.5, 2.5)
    return img


def scene_pill(w, h):
    """Oversized capsule and friends on a clean clinical ground."""
    img = Image.new("RGB", (U(w), U(h)), (250, 248, 240))
    d = ImageDraw.Draw(img)
    for gx in range(12, w, 26):
        for gy in range(6, h, 12):
            d.ellipse([U(gx), U(gy), U(gx + 1.6), U(gy + 1.6)],
                      fill=(226, 222, 210))

    def capsule(cx, cy, length, thick, angle, col_a, col_b):
        layer = Image.new("RGBA", (U(length + 8), U(thick + 8)),
                          (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([U(3), U(3), U(length + 3), U(thick + 3)],
                             radius=U(thick / 2 + 3), fill=col_b + (255,),
                             outline=(70, 70, 82, 255), width=U(1.4))
        ld.rounded_rectangle([U(3), U(3), U(length / 2 + 3), U(thick + 3)],
                             radius=U(thick / 2 + 3), fill=col_a + (255,))
        ld.rectangle([U(length / 2 - 2), U(3), U(length / 2 + 3),
                      U(thick + 3)], fill=col_a + (255,))
        layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
        img.paste(layer, (U(cx) - layer.size[0] // 2,
                          U(cy) - layer.size[1] // 2), layer)

    capsule(52, h / 2, 74, 24, 24, (198, 52, 44), (252, 250, 246))
    capsule(150, 11, 30, 11, -18, (240, 190, 60), (252, 250, 246))
    capsule(178, 27, 26, 10, 32, (70, 120, 200), (252, 250, 246))
    # green cross badge
    bx, by, br = w - 18, 10, 8
    d.ellipse([U(bx - br), U(by - br), U(bx + br), U(by + br)],
              fill=(28, 148, 78))
    d.rectangle([U(bx - 1.6), U(by - 5), U(bx + 1.6), U(by + 5)],
                fill=(255, 255, 255))
    d.rectangle([U(bx - 5), U(by - 1.6), U(bx + 5), U(by + 1.6)],
                fill=(255, 255, 255))
    return img


SCENE_PAINTERS = {"iraq": scene_iraq, "paris": scene_paris,
                  "youth": scene_youth, "pill": scene_pill}


def make_scene(key, w, h, seed):
    if key == "chart":
        return chart_scene(w, h)
    if key in SCENE_PAINTERS:
        return SCENE_PAINTERS[key](w, h)
    return art_scene(key, w, h, seed)


# ---------------------------------------------------------------------------
# Shared card furniture
# ---------------------------------------------------------------------------

def draw_badge(d, cx, cy, r, num, fsize):
    d.ellipse([U(cx - r), U(cy - r), U(cx + r), U(cy + r)], fill=BADGE_RED,
              outline=(255, 255, 255), width=U(1.6))
    fnt = font(SANS_B, fsize)
    label = str(num)
    tw = d.textlength(label, font=fnt) / SS
    th = fsize * 0.72
    d.text((U(cx - tw / 2), U(cy - th / 2)), label, font=fnt,
           fill=(255, 255, 255))


def panel_header(w, h):
    img = Image.new("RGB", (U(w), U(h)), PAGE_BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, U(1), U(w), U(3)], fill=RED)
    d.rectangle([0, U(4), U(w), U(6)], fill=INK)
    small = font(SANS_B, 10.5)
    draw_tracked(d, 0, 7, TOP_LEFT, small, (96, 86, 74), 1.1)
    draw_right(d, w, 7, TOP_RIGHT, small, (96, 86, 74), 1.1)
    d.line([(0, U(20)), (U(w), U(20))], fill=RULE_SOFT, width=U(1))
    draw_centered(d, w / 2, 26, MASTHEAD, font(SERIF_B, 33), INK, 6.5)
    draw_centered(d, w / 2, 59, DATE_LINE, font(SERIF_B, 53), INK, 0.4)
    draw_centered(d, w / 2, 110, DECK, font(SERIF_I, 15.5), DECK_RED, 0.2)
    d.rectangle([0, U(128), U(w), U(131)], fill=INK)
    d.rectangle([0, U(132), U(w), U(133)], fill=INK)
    return img


def panel_stats(w, h):
    img = Image.new("RGB", (U(w), U(h)), PAGE_BG)
    d = ImageDraw.Draw(img)
    col_w = w / len(STATS)
    num_f = font(SERIF_B, 29)
    lab_f = font(SANS_B, 8.2)
    for i, (figure, caption, is_red) in enumerate(STATS):
        cx = col_w * i + col_w / 2
        if i:
            d.line([(U(col_w * i), U(9)), (U(col_w * i), U(45))],
                   fill=RULE_SOFT, width=U(1))
        draw_centered(d, cx, 5, figure, num_f, RED if is_red else INK, 0.2)
        lines = wrap_text(caption, lab_f, col_w - 4)
        for j, line in enumerate(lines[:2]):
            draw_centered(d, cx, 37 + j * 10, line, lab_f, (74, 66, 56), 0.2)
    return img


def panel_tabs(w, h):
    img = Image.new("RGB", (U(w), U(h)), PAGE_BG)
    d = ImageDraw.Draw(img)
    fnt = font(SANS_B, 11.5)
    x = 0
    for label, region, seg_w in TABS:
        d.rectangle([U(x), 0, U(x + seg_w), U(h)],
                    fill=REGION_COLORS[region])
        draw_centered(d, x + seg_w / 2, 5.5, label, fnt,
                      (255, 255, 255), 0.4)
        x += seg_w
    return img


def panel_top_card(story):
    num, region, art, banner, kicker, source, headline, summary, _pin = story
    w, h = 316, 258
    img = Image.new("RGB", (U(w), U(h)), CARD_BG)
    img.paste(make_scene(art, w, 130, seed=num * 17), (0, 0))
    d = ImageDraw.Draw(img)
    # navy banner with its red leading edge, foot of the art
    ban_f = font(SANS_B, 12.5)
    ban_w = d.textlength(banner, font=ban_f) / SS + 30
    d.rectangle([0, U(106), U(ban_w), U(130)], fill=NAVY)
    d.rectangle([0, U(106), U(7), U(130)], fill=RED)
    d.text((U(15), U(112)), banner, font=ban_f, fill=(255, 255, 255))
    draw_badge(d, 19, 19, 16.5, num, 15)
    kick_f = font(SANS_B, 11.5)
    draw_tracked(d, 10, 139, kicker, kick_f, REGION_COLORS[region], 0.3)
    draw_right(d, w - 10, 140, source, font(SANS, 11), GREY_TEXT, 0.2)
    head_f = font(SERIF_B, 26)
    y = 159
    for line in wrap_text(headline, head_f, w - 20):
        d.text((U(10), U(y)), line, font=head_f, fill=INK)
        y += 30
    sum_f = font(SERIF, 14)
    for line in wrap_text(summary, sum_f, w - 20):
        d.text((U(10), U(y + 3)), line, font=sum_f, fill=SUMMARY_INK)
        y += 17.5
    d.rectangle([0, 0, U(w) - 1, U(h) - 1], outline=(18, 20, 36),
                width=U(2))
    return img


def panel_mid_card(story):
    num, region, scene, tag, headline, summary, _pin = story
    w, h = 237, 110
    img = Image.new("RGB", (U(w), U(h)), CARD_BG)
    img.paste(make_scene(scene, w, 37, seed=num * 23), (0, 0))
    d = ImageDraw.Draw(img)
    # region tag at the foot of the art strip, right side
    tag_f = font(SANS_B, 8)
    tw = d.textlength(tag, font=tag_f) / SS
    d.rectangle([U(w - tw - 13), U(24), U(w), U(37)],
                fill=REGION_COLORS[region])
    d.text((U(w - tw - 6), U(26.5)), tag, font=tag_f, fill=(255, 255, 255))
    draw_badge(d, 11, 11, 9.5, num, 10)
    head_f = font(SERIF_B, 15)
    y = 42
    for line in wrap_text(headline, head_f, w - 14):
        d.text((U(7), U(y)), line, font=head_f, fill=INK)
        y += 17.5
    sum_f = font(SANS, 10)
    for line in wrap_text(summary, sum_f, w - 14):
        d.text((U(7), U(y + 4)), line, font=sum_f, fill=SUMMARY_INK)
        y += 12.5
    d.rectangle([0, 0, U(w) - 1, U(h) - 1], outline=(18, 20, 36),
                width=U(2))
    return img


# ---------------------------------------------------------------------------
# Dotted world map (rough continent outlines, lon/lat)
# ---------------------------------------------------------------------------

LAND = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 69), (-85, 66),
     (-80, 62), (-76, 58), (-70, 55), (-65, 50), (-70, 45), (-74, 40),
     (-76, 35), (-80, 32), (-80, 26), (-84, 22), (-87, 16), (-92, 15),
     (-97, 16), (-105, 20), (-110, 24), (-114, 29), (-120, 34), (-124, 40),
     (-124, 46), (-130, 54), (-140, 60), (-155, 60), (-165, 60)],
    # Central America
    [(-97, 16), (-92, 15), (-86, 13), (-83, 9), (-79, 9), (-83, 15),
     (-90, 14)],
    # South America
    [(-79, 9), (-72, 12), (-64, 10), (-55, 6), (-50, 0), (-44, -3),
     (-38, -8), (-40, -15), (-42, -22), (-48, -26), (-52, -32), (-57, -38),
     (-62, -41), (-65, -45), (-67, -50), (-68, -54), (-71, -54), (-73, -50),
     (-73, -44), (-72, -38), (-71, -30), (-70, -20), (-75, -15), (-79, -8),
     (-80, -4), (-80, 1), (-77, 4)],
    # Greenland
    [(-45, 60), (-40, 62), (-32, 68), (-22, 70), (-20, 74), (-25, 78),
     (-35, 80), (-50, 76), (-55, 70), (-53, 64)],
    # Europe
    [(-9, 37), (-9, 43), (-2, 44), (0, 46), (-2, 49), (1, 51), (5, 53),
     (7, 54), (8, 57), (10, 58), (13, 56), (18, 56), (20, 54), (24, 57),
     (27, 59), (30, 60), (29, 64), (31, 70), (40, 68), (48, 66), (45, 60),
     (40, 55), (35, 52), (32, 50), (30, 46), (28, 41), (23, 40), (22, 37),
     (19, 40), (15, 38), (12, 40), (10, 44), (7, 44), (3, 43), (0, 40),
     (-2, 37)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 55), (-6, 58), (-4, 58), (-2, 56), (-1, 53),
     (0, 51)],
    # Africa
    [(-6, 35), (0, 36), (10, 37), (11, 34), (20, 32), (30, 31), (32, 31),
     (34, 28), (35, 24), (38, 22), (40, 15), (43, 12), (48, 11), (51, 12),
     (48, 5), (42, -2), (40, -8), (38, -15), (36, -20), (33, -26),
     (28, -33), (20, -35), (17, -32), (15, -27), (13, -20), (12, -15),
     (13, -10), (9, -5), (9, 0), (6, 4), (-2, 5), (-8, 5), (-13, 8),
     (-17, 12), (-17, 17), (-16, 21), (-15, 25), (-13, 28), (-9, 31)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (49, -20), (47, -24), (45, -25),
     (44, -20)],
    # Arabia + Asia
    [(34, 31), (36, 36), (40, 38), (42, 38), (48, 30), (50, 26), (52, 25),
     (55, 24), (58, 22), (59, 19), (55, 17), (52, 15), (48, 14), (44, 13),
     (42, 15), (40, 20), (38, 24), (36, 28)],
    [(40, 55), (48, 66), (60, 69), (80, 70), (100, 72), (120, 73),
     (140, 72), (160, 70), (178, 66), (178, 62), (162, 60), (155, 55),
     (150, 50), (142, 45), (140, 40), (135, 35), (130, 32), (127, 35),
     (122, 31), (120, 25), (115, 23), (108, 20), (105, 15), (103, 8),
     (100, 6), (97, 10), (95, 16), (92, 16), (89, 22), (86, 20), (80, 15),
     (77, 8), (80, 13), (84, 18), (88, 22), (91, 22), (89, 24), (85, 28),
     (80, 30), (75, 35), (72, 38), (68, 38), (66, 42), (61, 44), (57, 46),
     (52, 48), (48, 50)],
    # Indonesia / New Guinea
    [(95, 5), (105, 0), (112, -2), (118, -3), (125, -2), (132, -3),
     (138, -4), (145, -6), (148, -8), (140, -8), (132, -7), (125, -7),
     (118, -8), (110, -7), (102, -4), (96, 2)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 36), (141, 40), (142, 44),
     (143, 44), (141, 42), (140, 38), (138, 36), (135, 34), (132, 33),
     (130, 32)],
    # Australia
    [(113, -22), (114, -28), (115, -33), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (138, -36), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (151, -24), (146, -19), (142, -15), (142, -11),
     (137, -12), (135, -14), (132, -11), (130, -13), (126, -14),
     (122, -17), (118, -20)],
    # New Zealand
    [(167, -45), (170, -43), (173, -41), (174, -39), (176, -38), (174, -41),
     (172, -43), (169, -46)],
]


def _in_land(lon, lat):
    for poly in LAND:
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > lat) != (yj > lat):
                x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
                if lon < x_cross:
                    inside = not inside
            j = i
        if inside:
            return True
    return False


def panel_bottom(w, h):
    img = Image.new("RGB", (U(w), U(h)), PAGE_BG)
    d = ImageDraw.Draw(img)
    head_f = font(SANS_B, 12.5)
    draw_tracked(d, 0, 4, "WHERE IT HAPPENED", head_f, INK, 0.5)
    draw_tracked(d, 330, 4, "ALSO ON FRIDAY 20 NOVEMBER - 22 MORE STORIES",
                 head_f, INK, 0.5)
    # dotted map
    map_x, map_y, map_w, map_h = 0, 22, 306, 92
    d.rectangle([U(map_x), U(map_y), U(map_x + map_w), U(map_y + map_h)],
                fill=(233, 238, 239), outline=(188, 196, 198), width=U(1))
    lon0, lon1, lat0, lat1 = -168.0, 192.0, 84.0, -58.0
    step = 4.4
    gy = map_y + 3
    while gy < map_y + map_h - 2:
        gx = map_x + 3
        while gx < map_x + map_w - 2:
            lon = lon0 + (gx - map_x) / map_w * (lon1 - lon0)
            lat = lat0 - (gy - map_y) / map_h * (lat0 - lat1)
            if _in_land(lon, lat):
                d.ellipse([U(gx - 1.1), U(gy - 1.1), U(gx + 1.1),
                           U(gy + 1.1)], fill=(104, 126, 148))
            gx += step
        gy += step

    def pin_xy(lon, lat):
        return (map_x + (lon - lon0) / (lon1 - lon0) * map_w,
                map_y + (lat0 - lat) / (lat0 - lat1) * map_h)

    pins = {}
    for story in TOP_STORIES:
        if story[8]:
            pins[story[0]] = story[8]
    for story in MID_STORIES:
        if story[6]:
            pins[story[0]] = story[6]
    for num in sorted(pins):
        lon, lat = pins[num]
        dx, dy = PIN_NUDGE.get(num, (0, 0))
        px_, py_ = pin_xy(lon, lat)
        draw_badge(d, px_ + dx, py_ + dy, 8, num, 8.5)
    # space inset strip
    d.rectangle([U(map_x), U(map_y + map_h - 18), U(map_x + 150),
                 U(map_y + map_h)], fill=NAVY)
    d.text((U(map_x + 8), U(map_y + map_h - 13.5)), "6 · IN SPACE - MERCURY",
           font=font(SANS_B, 8.5), fill=(255, 255, 255))
    # ALSO columns
    item_f = font(SANS, 9.5)
    item_fb = font(SANS_B, 9.5)
    num_f = font(SANS_B, 9.5)
    columns = [(330, ALSO_STORIES[:11]), (664, ALSO_STORIES[11:])]
    for col_x, items in columns:
        y = 21
        for num, place, text, source in items:
            x = col_x
            label = str(num) + " "
            d.text((U(x), U(y)), label, font=num_f, fill=RED)
            x += d.textlength(label, font=num_f) / SS
            head = place + " - "
            d.text((U(x), U(y)), head, font=item_fb, fill=INK)
            x += d.textlength(head, font=item_fb) / SS
            tail = text + " (" + source + ")"
            d.text((U(x), U(y)), tail, font=item_f, fill=(40, 38, 36))
            y += 9.2
    # date check, foot of the panel
    d.text((U(10), U(122)), DATE_CHECK, font=font(SERIF_I, 9.5),
           fill=DECK_RED)
    return img


def panel_footer(w, h):
    img = Image.new("RGB", (U(w), U(h)), PAGE_BG)
    d = ImageDraw.Draw(img)
    draw_centered(d, w / 2, 5, FOOTER_LINE, font(SERIF, 10.5),
                  (96, 90, 80), 0.1)
    return img


# ---------------------------------------------------------------------------
# Assembly: render every panel, downsample, store raw RGB + manifest.
# ---------------------------------------------------------------------------

PANELS = [
    ("header", 26, 12, 972, 134),
    ("stats", 26, 150, 972, 54),
    ("tabs", 26, 208, 972, 24),
    ("top1", 26, 238, 316, 258),
    ("top2", 354, 238, 316, 258),
    ("top3", 682, 238, 316, 258),
    ("mid4", 26, 502, 237, 110),
    ("mid5", 271, 502, 237, 110),
    ("mid6", 516, 502, 237, 110),
    ("mid7", 761, 502, 237, 110),
    ("mid8", 26, 618, 237, 110),
    ("mid9", 271, 618, 237, 110),
    ("mid10", 516, 618, 237, 110),
    ("mid11", 761, 618, 237, 110),
    ("mid12", 26, 734, 237, 110),
    ("mid13", 271, 734, 237, 110),
    ("mid14", 516, 734, 237, 110),
    ("mid15", 761, 734, 237, 110),
    ("bottom", 26, 852, 972, 132),
    ("footer", 26, 988, 972, 22),
]


def render_panel(name):
    if name == "header":
        return panel_header(972, 134)
    if name == "stats":
        return panel_stats(972, 54)
    if name == "tabs":
        return panel_tabs(972, 24)
    if name.startswith("top"):
        return panel_top_card(TOP_STORIES[int(name[3]) - 1])
    if name.startswith("mid"):
        return panel_mid_card(MID_STORIES[int(name[3:]) - 4])
    if name == "bottom":
        return panel_bottom(972, 132)
    if name == "footer":
        return panel_footer(972, 22)
    raise ValueError(name)


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    manifest = {"canvas": [1024, 1024], "background": list(PAGE_BG),
                "panels": []}
    for name, x, y, w, h in PANELS:
        img = render_panel(name)
        img = img.resize((w, h), Image.LANCZOS)
        fname = name + ".rgb"
        with open(os.path.join(ASSETS_DIR, fname), "wb") as fh:
            fh.write(zlib.compress(img.tobytes(), 9))
        manifest["panels"].append(
            {"file": fname, "x": x, "y": y, "w": w, "h": h})
        print("panel", fname, w, "x", h)
    with open(os.path.join(ASSETS_DIR, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("wrote", len(PANELS), "panels + manifest.json")


if __name__ == "__main__":
    main()
