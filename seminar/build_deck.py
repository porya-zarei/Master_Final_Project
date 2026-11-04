# -*- coding: utf-8 -*-
"""
Seminar I deck builder (v2)
Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning
Pouria Zarei - University of Tehran
"""

import os
from lxml import etree
from pptx import Presentation
from pptx.util import Inches as In, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "Seminar_I_Pouria_Zarei.pptx")

INK = RGBColor(0x12, 0x2A, 0x40)
NAVY = RGBColor(0x0E, 0x33, 0x55)
BLUE = RGBColor(0x16, 0x63, 0x9E)
SKY = RGBColor(0x3E, 0x8F, 0xC4)
SKYL = RGBColor(0x7F, 0xB9, 0xDC)
PALE = RGBColor(0xEC, 0xF4, 0xFA)
PALE2 = RGBColor(0xF7, 0xFB, 0xFD)
LINE = RGBColor(0xD5, 0xE2, 0xEC)
GREY = RGBColor(0x4A, 0x5C, 0x6C)
GREYL = RGBColor(0x7D, 0x8E, 0x9D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xB0, 0x3F, 0x39)
REDBG = RGBColor(0xFA, 0xEC, 0xEA)
PURPLE = RGBColor(0x59, 0x49, 0x9E)
PURPBG = RGBColor(0xF0, 0xED, 0xF8)
GREEN = RGBColor(0x2C, 0x77, 0x55)
GREENBG = RGBColor(0xEA, 0xF5, 0xEF)
AMBER = RGBColor(0xA0, 0x73, 0x22)
AMBBG = RGBColor(0xFB, 0xF3, 0xE2)

FONT = "Segoe UI"
FONTL = "Segoe UI Light"
FONTSB = "Segoe UI Semibold"

M = 0.95
W, H = 13.333, 7.5
CW = W - 2 * M
TOTAL = 15

prs = Presentation()
prs.slide_width = In(W)
prs.slide_height = In(H)
BLANK = prs.slide_layouts[6]


def slide_new(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, In(W), In(H))
    r.fill.solid()
    r.fill.fore_color.rgb = bg
    r.line.fill.background()
    r.shadow.inherit = False
    return s


def _strip_style(shape):
    el = shape._element
    st = el.find(qn("p:style"))
    if st is not None:
        el.remove(st)
    shape.shadow.inherit = False


def rect(
    s,
    x,
    y,
    w,
    h,
    fill=None,
    line=None,
    lw=0.75,
    shape=MSO_SHAPE.RECTANGLE,
    radius=None,
    dash=None,
    soft=False,
):
    sh = s.shapes.add_shape(shape, In(x), In(y), In(w), In(h))
    _strip_style(sh)
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sh.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
        if dash:
            sh.line.dash_style = dash
    if soft:
        spPr = sh._element.spPr
        eff = spPr.find(qn("a:effectLst"))
        if eff is None:
            eff = etree.SubElement(spPr, qn("a:effectLst"))
        else:
            eff.clear()
        shd = etree.SubElement(eff, qn("a:outerShdw"))
        shd.set("blurRad", "152400")
        shd.set("dist", "25400")
        shd.set("dir", "5400000")
        shd.set("algn", "ctr")
        shd.set("rotWithShape", "0")
        c = etree.SubElement(shd, qn("a:srgbClr"))
        c.set("val", "0E3355")
        a = etree.SubElement(c, qn("a:alpha"))
        a.set("val", "11000")
    sh.text_frame.word_wrap = True
    return sh


def txt(
    s,
    x,
    y,
    w,
    h,
    items,
    anchor=MSO_ANCHOR.TOP,
    align=PP_ALIGN.LEFT,
    margins=(0, 0, 0, 0),
    wrap=True,
):
    box = s.shapes.add_textbox(In(x), In(y), In(w), In(h))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [
        In(v) for v in margins
    ]
    first = True
    for it in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = it.get("align", align)
        if it.get("sp_before") is not None:
            p.space_before = Pt(it["sp_before"])
        if it.get("sp_after") is not None:
            p.space_after = Pt(it["sp_after"])
        if it.get("line") is not None:
            p.line_spacing = it["line"]
        if it.get("bullet"):
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(In(0.28))))
            pPr.set("indent", str(int(-In(0.28))))
            buClr = etree.SubElement(pPr, qn("a:buClr"))
            srgb = etree.SubElement(buClr, qn("a:srgbClr"))
            srgb.set("val", str(it.get("bucolor", BLUE)))
            buSz = etree.SubElement(pPr, qn("a:buSzPct"))
            buSz.set("val", "80000")
            buFont = etree.SubElement(pPr, qn("a:buFont"))
            buFont.set("typeface", "Arial")
            buChar = etree.SubElement(pPr, qn("a:buChar"))
            buChar.set("char", it.get("buchar", "\u25aa"))
        segs = it["t"] if isinstance(it["t"], list) else [(it["t"], {})]
        for seg_text, ov in segs:
            r = p.add_run()
            r.text = seg_text
            f = r.font
            f.name = ov.get("font", it.get("font", FONT))
            f.size = Pt(ov.get("size", it.get("size", 20)))
            f.bold = ov.get("bold", it.get("bold", False))
            f.italic = ov.get("italic", it.get("italic", False))
            f.color.rgb = ov.get("color", it.get("color", GREY))
            rPr = r._r.get_or_add_rPr()
            spc = ov.get("spc", it.get("spc"))
            if spc:
                rPr.set("spc", str(int(spc)))
            base = ov.get("baseline", it.get("baseline"))
            if base:
                rPr.set("baseline", str(int(base * 1000)))
    return box


def line_h(s, x, y, w, color=LINE, h=1.0):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, In(x), In(y), In(x + w), In(y))
    c.line.color.rgb = color
    c.line.width = Pt(h)
    return c


def arrow(s, x1, y1, x2, y2, color=SKY, width=1.1, head=True, dash=None):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, In(x1), In(y1), In(x2), In(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = dash
    if head:
        ln = c.line._get_or_add_ln()
        te = etree.SubElement(ln, qn("a:tailEnd"))
        te.set("type", "triangle")
        te.set("w", "med")
        te.set("len", "med")
    return c


def pic(s, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = In(w)
    if h:
        kw["height"] = In(h)
    return s.shapes.add_picture(path, In(x), In(y), **kw)


def pic_contain(s, path, x, y, w, h):
    from PIL import Image

    iw, ih = Image.open(path).size
    r_box, r_img = w / h, iw / ih
    if r_img > r_box:
        return pic(s, path, x, y, w=w, h=w / r_img)
    return pic(s, path, x + (w - h * r_img) / 2, y, h=h)


def grad(s, x, y, w, h, stops, ang=0):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, In(x), In(y), In(w), In(h))
    _strip_style(sh)
    sh.line.fill.background()
    spPr = sh._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:gradFill", "a:pattFill"):
        el = spPr.find(qn(tag))
        if el is not None:
            spPr.remove(el)
    gf = etree.SubElement(spPr, qn("a:gradFill"))
    gf.set("rotWithShape", "1")
    gsLst = etree.SubElement(gf, qn("a:gsLst"))
    for pos, col, alpha in stops:
        gs = etree.SubElement(gsLst, qn("a:gs"))
        gs.set("pos", str(int(pos * 1000)))
        c = etree.SubElement(gs, qn("a:srgbClr"))
        c.set("val", col)
        a = etree.SubElement(c, qn("a:alpha"))
        a.set("val", str(int(alpha * 1000)))
    lin = etree.SubElement(gf, qn("a:lin"))
    lin.set("ang", str(int(ang * 60000)))
    lin.set("scaled", "0")
    spPr.remove(gf)
    idx = 0
    for i, child in enumerate(spPr):
        if child.tag in (qn("a:xfrm"), qn("a:prstGeom"), qn("a:custGeom")):
            idx = i + 1
    spPr.insert(idx, gf)
    return sh


def chip(
    s,
    x,
    y,
    w,
    h,
    text,
    fill=PALE,
    color=BLUE,
    size=13,
    bold=True,
    radius=0.5,
    border=None,
):
    sh = rect(
        s,
        x,
        y,
        w,
        h,
        fill=fill,
        line=border,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        radius=radius,
    )
    tf = sh.text_frame
    tf.margin_left = tf.margin_right = In(0.06)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return sh


def kicker(s, text, color=BLUE):
    txt(
        s,
        M,
        0.46,
        CW,
        0.26,
        [
            {
                "t": text,
                "size": 10,
                "bold": True,
                "color": color,
                "font": FONTSB,
                "spc": 180,
            }
        ],
    )


def footer(s, num, dark=False, y=7.03):
    c = RGBColor(0x9A, 0xB4, 0xC7) if dark else GREYL
    txt(
        s,
        M,
        y,
        9.6,
        0.24,
        [
            {
                "t": "Fault-Tolerant Attitude Control of Nanosatellites Using RL   \u00b7   Seminar I",
                "size": 8.5,
                "color": c,
            }
        ],
    )
    txt(
        s,
        W - M - 1.2,
        y,
        1.2,
        0.24,
        [{"t": f"{num} / {TOTAL}", "size": 8.5, "color": c, "align": PP_ALIGN.RIGHT}],
    )


def header(s, num, kick, ttl, tsize=28, sub=None, rule=True):
    kicker(s, kick)
    txt(
        s,
        M,
        0.70,
        CW,
        0.62,
        [
            {
                "t": ttl,
                "size": tsize,
                "bold": True,
                "color": NAVY,
                "font": FONTSB,
                "line": 1.02,
            }
        ],
    )
    if sub:
        txt(
            s,
            M,
            1.26,
            CW,
            0.3,
            [{"t": sub, "size": 13.5, "color": GREY, "font": FONTL}],
        )
    if rule:
        line_h(s, M, 1.62, CW, LINE)
    footer(s, num)


def footnote(s, text, y=6.66, w=None, dark=False, x=None):
    txt(
        s,
        x if x is not None else M,
        y,
        w or (CW - 0.4),
        0.3,
        [
            {
                "t": text,
                "size": 8.5,
                "color": (RGBColor(0xA9, 0xC2, 0xD4) if dark else GREYL),
            }
        ],
    )


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


def measure_lines(text, size, width_in, font="segoeui.ttf"):
    """Approximate wrapped line count using the real font metrics."""
    from PIL import ImageFont

    f = ImageFont.truetype(
        os.path.join(os.environ["WINDIR"], "Fonts", font), int(size * 96 / 72)
    )
    maxw = width_in * 96
    lines, cur = 1, ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) <= maxw:
            cur = trial
        else:
            lines += 1
            cur = word
    return lines


def animate(s, click_groups, dur=550):
    counter = [2]

    def nid():
        counter[0] += 1
        return counter[0]

    steps_xml = []
    for group in click_groups:
        inner = []
        items = [(g, 0) if not isinstance(g, tuple) else g for g in group]
        for i, (shape, delay) in enumerate(items):
            ntype = "clickEffect" if i == 0 else "withEffect"
            sid = shape.shape_id
            inner.append(
                f'<p:par><p:cTn id="{nid()}" presetID="10" presetClass="entr" presetSubtype="0" '
                f'fill="hold" grpId="0" nodeType="{ntype}"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>'
                f'<p:childTnLst><p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold">'
                f'<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl>'
                f"<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>"
                f'</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{nid()}" dur="{dur}"/>'
                f'<p:tgtEl><p:spTgt spid="{sid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                f"</p:childTnLst></p:cTn></p:par>"
            )
        steps_xml.append(
            f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
            f'<p:childTnLst><p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
            f"<p:childTnLst>{''.join(inner)}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"
        )

    xml = (
        '<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:tnLst><p:par>'
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
        f"<p:childTnLst>{''.join(steps_xml)}</p:childTnLst></p:cTn>"
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        "</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"
    )
    sld = s._element
    old = sld.find(qn("p:timing"))
    if old is not None:
        sld.remove(old)
    sld.append(etree.fromstring(xml))


def transition(s, kind="fade", speed="med"):
    sld = s._element
    old = sld.find(qn("p:transition"))
    if old is not None:
        sld.remove(old)
    xml = (
        f'<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        f'spd="{speed}"><p:{kind}/></p:transition>'
    )
    tr = etree.fromstring(xml)
    timing = sld.find(qn("p:timing"))
    if timing is not None:
        timing.addprevious(tr)
    else:
        sld.append(tr)


# ================================================================ 1 TITLE
s = slide_new(NAVY)
pic(s, os.path.join(ASSETS, "hero.jpg"), 0, 0, w=W, h=H)
grad(
    s,
    0,
    0,
    W,
    H,
    [(0, "08223C", 97), (46, "0A2A48", 92), (72, "0A2A48", 55), (100, "08223C", 12)],
)

txt(
    s,
    M,
    0.70,
    6.0,
    0.28,
    [
        {
            "t": "UNIVERSITY OF TEHRAN",
            "size": 11,
            "bold": True,
            "color": RGBColor(0x9F, 0xC8, 0xE4),
            "spc": 260,
        }
    ],
)
txt(
    s,
    M,
    1.00,
    7.0,
    0.28,
    [
        {
            "t": "Faculty of Electrical & Computer Engineering  \u00b7  M.Sc. Control Engineering",
            "size": 9.5,
            "color": RGBColor(0x86, 0xAE, 0xCB),
        }
    ],
)
txt(
    s,
    M,
    2.14,
    8.05,
    2.55,
    [
        {
            "t": "Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning",
            "size": 37,
            "bold": True,
            "color": WHITE,
            "font": FONTSB,
            "line": 1.03,
        }
    ],
)
rect(s, M, 4.80, 1.05, 0.045, fill=SKYL)
txt(
    s,
    M,
    5.00,
    7.4,
    0.6,
    [
        {
            "t": "From spacecraft attitude-control fundamentals to the research gap",
            "size": 16,
            "color": RGBColor(0xBF, 0xD8, 0xE9),
            "font": FONTL,
        }
    ],
)
txt(
    s,
    M,
    5.72,
    7.2,
    0.95,
    [
        {"t": "Pouria Zarei", "size": 20, "bold": True, "color": WHITE, "sp_after": 3},
        {
            "t": "Supervisor:  Prof. Mohammad Javad Yazdanpanah",
            "size": 12.5,
            "color": RGBColor(0xD3, 0xE4, 0xF0),
            "sp_after": 3,
        },
        {
            "t": "Seminar I  \u00b7  2026",
            "size": 11,
            "color": RGBColor(0x8F, 0xB4, 0xCE),
        },
    ],
)
footnote(
    s,
    "Image: NASA/JPL-Caltech, NISAR in Earth orbit (artist\u2019s concept), image PIA26285.",
    y=6.80,
    dark=True,
)
footer(s, 1, dark=True, y=7.12)
transition(s)
notes(
    s,
    "0:00  Good morning. I am Pouria Zarei, M.Sc. control engineering. Today: why attitude control "
    "of a nanosatellite is hard, what my thesis proposes, three recent papers, and where the gap is. (~30 s)",
)

# ================================================================ 2 ROADMAP
s = slide_new(WHITE)
header(
    s, 2, "ROADMAP", "From the engineering problem to the research question", rule=False
)
line_h(s, M, 2.14, CW - 0.1, LINE, 1.0)

steps = [
    ("01", "The problem", "What a spacecraft must control, and why it fails"),
    ("02", "The proposal", "A learned controller that is allowed to fail safely"),
    ("03", "Related research", "Three recent directions of the state of the art"),
    ("04", "Gaps & new ideas", "What is still missing, and what this thesis adds"),
    ("05", "Conclusion", "Why the direction is worth pursuing"),
]
gx = [1.0, 3.44, 5.88, 8.32, 10.76]
nodes = []
for (num, lab, desc), x in zip(steps, gx):
    dot = rect(s, x + 0.02, 2.07, 0.14, 0.14, fill=SKY, shape=MSO_SHAPE.OVAL)
    n = txt(
        s,
        x,
        2.44,
        2.2,
        0.52,
        [
            {
                "t": num,
                "size": 25,
                "bold": True,
                "color": SKYL,
                "font": FONTSB,
                "spc": 40,
            }
        ],
    )
    lab_box = txt(
        s,
        x,
        3.02,
        2.3,
        0.42,
        [{"t": lab, "size": 19, "bold": True, "color": NAVY, "font": FONTSB}],
    )
    d = txt(
        s, x, 3.48, 2.25, 0.86, [{"t": desc, "size": 12.5, "color": GREY, "line": 1.25}]
    )
    nodes.append((dot, n, lab_box, d))

txt(
    s,
    M,
    5.35,
    9.4,
    0.44,
    [
        {
            "t": "Ten minutes, five questions \u2014 one argument.",
            "size": 20,
            "color": BLUE,
            "font": FONTL,
        }
    ],
)
animate(s, [[n[0]] for n in nodes] + [[nodes[-1][3]]])
transition(s)
notes(
    s,
    "0:30  The talk follows five questions: the physical problem, the proposal, three papers, the gap, "
    "and the conclusion. (~20 s)",
)

# ================================================================ 3 THE LOOP
s = slide_new(WHITE)
header(s, 3, "01 \u00b7 THE PROBLEM", "Attitude control: a loop that never stops")

blocks = [
    (
        "Point",
        "hold the payload axis on its target \u2014 nadir, a star, a ground station.",
    ),
    ("Rotate", "slew between targets inside torque and rate limits."),
    ("Reject", "gravity gradient, drag, solar pressure, residual magnetic dipole."),
]
yy = 1.96
for i, (h_, b_) in enumerate(blocks):
    rect(s, M, yy, 0.055, 0.78, fill=SKY if i < 2 else RED)
    txt(
        s,
        M + 0.22,
        yy - 0.04,
        5.6,
        0.34,
        [{"t": h_, "size": 20, "bold": True, "color": NAVY, "font": FONTSB}],
    )
    txt(
        s,
        M + 0.22,
        yy + 0.30,
        5.6,
        0.6,
        [{"t": b_, "size": 14, "color": GREY, "line": 1.14}],
    )
    yy += 1.06

rect(
    s,
    M,
    5.30,
    5.75,
    1.06,
    fill=PALE,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.26,
    5.44,
    5.25,
    0.95,
    [
        {
            "t": [
                ("ADCS", {"bold": True, "color": BLUE}),
                (
                    " estimates the attitude and acts on it \u2014 continuously, onboard, with limited power and computing.",
                    {},
                ),
            ],
            "size": 14,
            "color": INK,
            "line": 1.2,
        }
    ],
)

DX, DY, BW, GAP, BH = 6.95, 2.40, 1.03, 0.16, 1.05
labels = [
    ("Sensors", "gyro \u00b7 ST \u00b7 sun \u00b7 mag"),
    ("Estimation", "attitude & rate"),
    ("Controller", "control law"),
    ("Actuators", "3 RW + 3 MTQ"),
    ("Spacecraft", "rigid-body dynamics"),
]
boxes = []
for i, (l1, l2) in enumerate(labels):
    x = DX + i * (BW + GAP)
    b = rect(
        s,
        x,
        DY,
        BW,
        BH,
        fill=WHITE,
        line=LINE,
        radius=0.08,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        soft=True,
    )
    tf = b.text_frame
    tf.margin_left = tf.margin_right = In(0.02)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = l1
    r.font.name = FONTSB
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = l2
    r2.font.name = FONT
    r2.font.size = Pt(7.5)
    r2.font.color.rgb = GREYL
    boxes.append(b)
    if i < 4:
        arrow(
            s, x + BW + 0.015, DY + BH / 2, x + BW + GAP - 0.015, DY + BH / 2, SKY, 1.0
        )

# fault / disturbance tags under the loop
tag_style = {"size": 8.5, "align": PP_ALIGN.CENTER, "font": FONTSB}
txt(s, DX, DY + BH + 0.06, BW, 0.26, [dict(t="sensor faults", color=RED, **tag_style)])
txt(
    s,
    DX + 3 * (BW + GAP),
    DY + BH + 0.06,
    BW,
    0.26,
    [dict(t="actuator faults", color=RED, **tag_style)],
)
txt(
    s,
    DX + 4 * (BW + GAP),
    DY + BH + 0.06,
    BW,
    0.26,
    [dict(t="disturbances", color=AMBER, **tag_style)],
)

x_end = DX + 4 * (BW + GAP) + BW / 2
arrow(s, x_end, DY + BH + 0.34, x_end, DY + BH + 0.72, SKY, 1.0, head=False)
arrow(s, x_end, DY + BH + 0.72, DX + BW / 2, DY + BH + 0.72, SKY, 1.0, head=False)
arrow(s, DX + BW / 2, DY + BH + 0.72, DX + BW / 2, DY + BH + 0.36, SKY, 1.0)
txt(
    s,
    DX + 0.62,
    DY + BH + 0.76,
    4.2,
    0.28,
    [{"t": "state feedback", "size": 9.5, "color": GREYL, "italic": True}],
)

txt(
    s,
    DX - 0.05,
    5.35,
    5.95,
    1.0,
    [
        {
            "t": [
                ("Faults enter the loop in two places: ", {"color": INK}),
                ("the measurements", {"color": RED, "bold": True}),
                (" and ", {"color": INK}),
                ("the torque", {"color": RED, "bold": True}),
                (". A fault-tolerant ADCS has to survive both.", {"color": INK}),
            ],
            "size": 15,
            "line": 1.2,
        }
    ],
)

animate(s, [[boxes[i]] for i in range(5)])
footnote(
    s,
    "Sources: NASA, State-of-the-Art of Small Spacecraft Technology \u2014 Guidance, Navigation and Control (2026); "
    "NASA SSRI Knowledge Base, Attitude Determination and Control.",
    y=6.64,
)
transition(s)
notes(
    s,
    "1:00  Three jobs: point, rotate, reject disturbances. The ADCS closes the loop. Faults enter at two "
    "places - measurements and torque. That picture is the thesis. (~60 s)",
)

# ================================================================ 4 WHY FAULTS
s = slide_new(WHITE)
header(
    s,
    4,
    "01 \u00b7 THE PROBLEM",
    "Why fault tolerance is the hard part",
    sub="Nanosatellites cannot be repaired, and they fly on commercial off-the-shelf parts.",
)

facts = [
    (
        "1\u201312 kg",
        "Mass and volume budgets shrink actuators, computing and redundancy.",
    ),
    ("COTS", "Commercial parts cut cost, but widen uncertainty and failure rates."),
    (
        "No servicing",
        "A fault in orbit must be survived by software, not by a repair crew.",
    ),
]
yy = 1.90
fact_cards = []
for k, v in facts:
    fc = rect(
        s,
        M,
        yy,
        6.5,
        0.94,
        fill=PALE2,
        line=None,
        radius=0.08,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M + 0.22,
        yy + 0.14,
        1.8,
        0.4,
        [{"t": k, "size": 15, "bold": True, "color": BLUE, "font": FONTSB}],
    )
    txt(
        s,
        M + 1.98,
        yy + 0.13,
        4.35,
        0.72,
        [{"t": v, "size": 13, "color": GREY, "line": 1.12}],
    )
    fact_cards.append(fc)
    yy += 1.04

band = rect(
    s,
    M,
    4.98,
    6.5,
    1.10,
    fill=NAVY,
    line=None,
    radius=0.08,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.24,
    5.07,
    1.9,
    0.24,
    [
        {
            "t": "FAULT MODEL",
            "size": 8,
            "bold": True,
            "color": RGBColor(0x8C, 0xBC, 0xDF),
            "spc": 160,
        }
    ],
)
txt(
    s,
    M + 0.24,
    5.28,
    6.0,
    0.36,
    [
        {
            "t": [
                ("\u03c4", {"size": 17, "italic": True, "color": WHITE}),
                (
                    "applied",
                    {"size": 9.5, "baseline": -25, "color": RGBColor(0x9C, 0xC4, 0xE2)},
                ),
                (" = h \u00b7 \u03c4", {"size": 17, "italic": True, "color": WHITE}),
                (
                    "cmd,",
                    {"size": 9.5, "baseline": -25, "color": RGBColor(0x9C, 0xC4, 0xE2)},
                ),
                ("      h \u2208 [0, 1]", {"size": 17, "italic": True, "color": WHITE}),
            ]
        }
    ],
)
txt(
    s,
    M + 0.24,
    5.68,
    6.0,
    0.3,
    [
        {
            "t": "continuous loss of authority \u2014 20 %, 50 % or total \u2014 not a binary switch",
            "size": 10,
            "color": RGBColor(0xBF, 0xD8, 0xE9),
            "line": 1.08,
        }
    ],
)

txt(
    s,
    M,
    6.20,
    6.55,
    0.38,
    [
        {
            "t": "Wheel friction  \u00b7  torque loss  \u00b7  encoder fault  \u00b7  wheel lock  \u00b7  sensor bias  \u00b7  dropout",
            "size": 10.5,
            "color": RED,
        }
    ],
)

card = rect(
    s,
    7.95,
    1.90,
    4.42,
    4.05,
    fill=WHITE,
    line=LINE,
    radius=0.04,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    soft=True,
)
pic_contain(s, os.path.join(ASSETS, "cubesat.jpg"), 8.12, 2.00, 4.08, 3.85)
txt(
    s,
    7.95,
    6.03,
    4.42,
    0.5,
    [
        {
            "t": "6U CubeSat (RainCube) \u2014 the class this thesis targets.",
            "size": 10.5,
            "color": GREY,
            "line": 1.1,
        }
    ],
)
footnote(
    s, "Image: NASA/JPL-Caltech, RainCube 6U CubeSat, image PIA22457.", y=6.66, w=4.5
)

animate(s, [[fact_cards[0]], [fact_cards[1]], [fact_cards[2]], [band], [card]])
transition(s)
notes(
    s,
    "1:55  Three reasons why fault tolerance is the hard part: tiny mass and power budgets, commercial "
    "parts, and no servicing. The fault is continuous - h between 0 and 1 - which is the model used here. "
    "(~55 s)",
)

# ================================================================ 5 RESEARCH QUESTION
s = slide_new(WHITE)
kicker(s, "01 \u00b7 THE PROBLEM   \u2192   02 \u00b7 THE PROPOSAL")
q = txt(
    s,
    M,
    1.55,
    10.85,
    2.7,
    [
        {
            "t": [
                ("Can reinforcement learning deliver ", {}),
                ("adaptive, fault-tolerant", {"bold": True, "color": BLUE}),
                (
                    " attitude control for a nanosatellite \u2014 and still keep pointing accurate when the system ",
                    {},
                ),
                ("is not the one it trained on", {"bold": True, "color": PURPLE}),
                ("?", {}),
            ],
            "size": 27,
            "color": NAVY,
            "line": 1.24,
        }
    ],
)

chips = []
cw_, ch_ = 2.55, 0.58
cy = 5.02
for i, (t_, c_) in enumerate(
    [
        ("Unseen faults", RED),
        ("Safety guarantees", AMBER),
        ("Onboard feasibility", BLUE),
        ("Verifiable behaviour", GREEN),
    ]
):
    cchip = chip(
        s,
        M + i * (cw_ + 0.28),
        cy,
        cw_,
        ch_,
        t_,
        fill=PALE2,
        color=c_,
        size=13,
        radius=0.28,
        border=LINE,
    )
    chips.append(cchip)

txt(
    s,
    M,
    5.95,
    10.4,
    0.5,
    [
        {
            "t": "A controller is only useful if it survives the fault it did not expect.",
            "size": 15,
            "color": GREY,
            "font": FONTL,
            "italic": True,
        }
    ],
)
footer(s, 5)

animate(s, [[q], [chips[0]], [chips[1]], [chips[2]], [chips[3]]])
transition(s)
notes(
    s,
    "2:50  This is the question. Not 'can RL control a satellite' - that is established. The question is "
    "whether it stays accurate when the system is not the one it trained on. (~45 s)",
)

# ================================================================ 6 PROPOSAL
s = slide_new(WHITE)
header(
    s,
    6,
    "02 \u00b7 THE PROPOSAL",
    "A learned controller that is allowed to fail safely",
)

txt(
    s,
    M,
    1.90,
    5.35,
    2.1,
    [
        {
            "t": [
                ("Objective. ", {"bold": True, "color": NAVY}),
                (
                    "Drive a nanosatellite from a random attitude and rate to nadir pointing \u2014 fast and "
                    "precisely \u2014 and keep that performance when a reaction wheel degrades, locks, or fails "
                    "in a way the policy never saw.",
                    {},
                ),
            ],
            "size": 15,
            "color": GREY,
            "line": 1.26,
        }
    ],
)

principles = [
    (
        "1",
        "Learn",
        "PPO / SAC on a nonlinear plant with random inertia, disturbances and noise.",
    ),
    (
        "2",
        "Never assume health",
        "The policy sees the estimate \u0125 \u2014 never the true health h.",
    ),
    (
        "3",
        "Fail safely",
        "A physics-based governor plus an LQR fallback \u2014 never a second network.",
    ),
]
yy = 3.86
princ_shapes = []
for num, hd, bd in principles:
    badge = rect(
        s, M, yy + 0.02, 0.34, 0.34, fill=PALE, line=None, shape=MSO_SHAPE.OVAL
    )
    txt(
        s,
        M,
        yy + 0.05,
        0.34,
        0.3,
        [
            {
                "t": num,
                "size": 11,
                "bold": True,
                "color": BLUE,
                "align": PP_ALIGN.CENTER,
                "font": FONTSB,
            }
        ],
    )
    txt(
        s,
        M + 0.52,
        yy - 0.04,
        4.85,
        0.32,
        [{"t": hd, "size": 14.5, "bold": True, "color": NAVY, "font": FONTSB}],
    )
    txt(
        s,
        M + 0.52,
        yy + 0.28,
        4.85,
        0.58,
        [{"t": bd, "size": 12, "color": GREY, "line": 1.12}],
    )
    princ_shapes.append(badge)
    yy += 0.93

AX, AY, AW, AH, AG = 7.05, 1.96, 2.66, 0.64, 0.30
arch = [
    ("Sensors & estimator", "attitude, rate and health estimate", WHITE, LINE, NAVY),
    ("RL policy  \u03c0\u03b8(s)", "desired body torque", PURPBG, PURPLE, PURPLE),
    (
        "Safety governor",
        "physics-based check",
        AMBBG,
        RGBColor(0xE8, 0xD3, 0xA6),
        AMBER,
    ),
    ("Fault-tolerant allocator", "redistributes the torque", PALE, None, NAVY),
    ("3 RW  +  3 MTQ", "actuation", WHITE, LINE, NAVY),
]
arch_boxes = []
for i, (l1, l2, fill, ln, col) in enumerate(arch):
    y = AY + i * (AH + AG)
    b = rect(
        s,
        AX,
        y,
        AW,
        AH,
        fill=fill,
        line=ln,
        radius=0.1,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        soft=(ln is not None),
    )
    tf = b.text_frame
    tf.margin_left = tf.margin_right = In(0.04)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = l1
    r.font.name = FONTSB
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = col
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = l2
    r2.font.name = FONT
    r2.font.size = Pt(7.5)
    r2.font.color.rgb = GREYL
    arch_boxes.append(b)
    if i < 4:
        arrow(s, AX + AW / 2, y + AH + 0.02, AX + AW / 2, y + AH + AG - 0.02, SKY, 1.2)

y_last = AY + 4 * (AH + AG)
lx = AX - 0.30
arrow(s, AX, y_last + AH / 2, lx, y_last + AH / 2, SKY, 1.0, head=False)
arrow(s, lx, y_last + AH / 2, lx, AY + AH / 2, SKY, 1.0, head=False)
arrow(s, lx, AY + AH / 2, AX - 0.02, AY + AH / 2, SKY, 1.0)

txt(
    s,
    AX + AW + 0.16,
    AY + 2 * (AH + AG) + 0.04,
    2.3,
    0.55,
    [
        {
            "t": "rejects unsafe actions, hands over to LQR",
            "size": 8.5,
            "color": AMBER,
            "line": 1.05,
        }
    ],
)
txt(
    s,
    AX + AW + 0.16,
    AY + 3 * (AH + AG) + 0.04,
    2.3,
    0.55,
    [
        {
            "t": "redistributes torque over healthy wheels + MTQs",
            "size": 8.5,
            "color": BLUE,
            "line": 1.05,
        }
    ],
)

animate(s, [[arch_boxes[i]] for i in range(5)])
transition(s)
notes(
    s,
    "3:35  The proposal in one architecture. The policy outputs a desired torque, never actuator commands. "
    "A physics-based governor can veto it and hand over to LQR. An allocator maps torque onto wheels and "
    "magnetorquers, so a dead wheel becomes a redistribution problem. (~60 s)",
)

# ================================================================ 7 VALIDATION
s = slide_new(WHITE)
header(
    s,
    7,
    "02 \u00b7 THE PROPOSAL",
    "Validated in four stages \u2014 and tested on faults it never saw",
)

stages = [
    ("MIL", "model-in-the-loop\nsimulation", NAVY),
    ("Fault-aware\ntraining", "random inertia, noise,\ndegraded wheels", BLUE),
    ("SIL / compression", "quantise, prune,\nmeasure latency", SKY),
    ("HIL", "ESP32-S3 + real\nsensors and actuators", RGBColor(0x5C, 0x9E, 0xC8)),
]
sx, sw = M, 2.95
chev = []
for i, (hd, cap, col) in enumerate(stages):
    x = sx + i * (sw - 0.16)
    ch = rect(s, x, 1.90, sw, 0.74, fill=col, line=None, shape=MSO_SHAPE.CHEVRON)
    tf = ch.text_frame
    tf.margin_left = In(0.3)
    tf.margin_right = In(0.12)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = hd
    r.font.name = FONTSB
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = WHITE
    txt(
        s,
        x + 0.18,
        2.74,
        sw - 0.5,
        0.6,
        [
            {
                "t": cap,
                "size": 9.5,
                "color": GREY,
                "align": PP_ALIGN.CENTER,
                "line": 1.08,
            }
        ],
    )
    chev.append(ch)

mrows = [
    ("Healthy spacecraft", "trained", "tested"),
    ("Wheel at 50 % torque", "trained", "tested"),
    ("Wheel dead / locked", "\u2014", "key test"),
    ("Unseen severity & combinations", "\u2014", "key test"),
]
tx, ty = M, 3.72
colw = [3.05, 1.55, 1.55]
rect(s, tx, ty, sum(colw), 0.40, fill=NAVY, line=None)
for cx, cwid, ct in zip(
    [tx, tx + colw[0], tx + colw[0] + colw[1]],
    colw,
    ["Scenario", "In training", "Held out"],
):
    txt(
        s,
        cx + 0.14,
        ty + 0.09,
        cwid - 0.1,
        0.26,
        [{"t": ct, "size": 9.5, "bold": True, "color": WHITE, "spc": 60}],
    )
for i, (a, b, c) in enumerate(mrows):
    ry = ty + 0.40 + i * 0.46
    if i % 2 == 0:
        rect(s, tx, ry, sum(colw), 0.46, fill=PALE2, line=None)
    txt(
        s,
        tx + 0.14,
        ry + 0.12,
        colw[0] - 0.12,
        0.3,
        [{"t": a, "size": 12, "color": INK}],
    )
    txt(
        s,
        tx + colw[0] + 0.14,
        ry + 0.12,
        colw[1] - 0.12,
        0.3,
        [{"t": b, "size": 12, "color": GREEN if b != "\u2014" else GREYL}],
    )
    txt(
        s,
        tx + colw[0] + colw[1] + 0.14,
        ry + 0.12,
        colw[2] - 0.12,
        0.3,
        [{"t": c, "size": 12, "color": RED if c == "key test" else GREEN}],
    )
line_h(s, tx, ty + 0.40 + 4 * 0.46, sum(colw), LINE)

rect(
    s,
    7.55,
    3.72,
    4.85,
    2.28,
    fill=PALE,
    line=None,
    radius=0.05,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    7.82,
    3.88,
    4.3,
    0.26,
    [{"t": "WHAT IS MEASURED", "size": 8.5, "bold": True, "color": BLUE, "spc": 160}],
)
txt(
    s,
    7.82,
    4.18,
    4.35,
    1.65,
    [
        {
            "t": "settling time to nadir lock",
            "size": 12,
            "color": INK,
            "bullet": True,
            "sp_after": 5,
            "buchar": "\u2013",
            "line": 1.1,
        },
        {
            "t": "pointing error and success rate",
            "size": 12,
            "color": INK,
            "bullet": True,
            "sp_after": 5,
            "buchar": "\u2013",
            "line": 1.1,
        },
        {
            "t": "control effort and wheel saturation",
            "size": 12,
            "color": INK,
            "bullet": True,
            "sp_after": 5,
            "buchar": "\u2013",
            "line": 1.1,
        },
        {
            "t": "inference latency and memory on the target MCU",
            "size": 12,
            "color": INK,
            "bullet": True,
            "buchar": "\u2013",
            "line": 1.1,
        },
    ],
)

txt(
    s,
    M,
    6.22,
    11.5,
    0.45,
    [
        {
            "t": [
                (
                    "The claim is not \u201cRL beats LQR\u201d. ",
                    {"bold": True, "color": NAVY},
                ),
                (
                    "The claim is graceful degradation where classical control has none.",
                    {"italic": True},
                ),
            ],
            "size": 15,
            "color": GREY,
        }
    ],
)
footer(s, 7)
animate(s, [[c] for c in chev])
transition(s)
notes(
    s,
    "4:35  Four stages: simulation, fault-aware training, compression for the target processor, then "
    "hardware-in-the-loop. The evaluation is deliberately split: faults seen in training versus held out. "
    "The dead-wheel row is the one that matters. (~55 s)",
)

# ================================================================ 8 RELATED OVERVIEW
s = slide_new(WHITE)
header(s, 8, "03 \u00b7 RELATED RESEARCH", "Three papers, three complementary answers")

cards = [
    (
        "PAPER 1",
        "Yang, Jin & Rao",
        "2025",
        "Journal of the Franklin Institute",
        "RL adapts online when the spacecraft model is unknown and actuators fail.",
        "Adaptation",
        PURPLE,
        PURPBG,
    ),
    (
        "PAPER 2",
        "Lu et al.",
        "2026",
        "Aerospace Science and Technology",
        "Safe RL keeps agile tracking inside operational constraints and actuator faults.",
        "Safety",
        AMBER,
        AMBBG,
    ),
    (
        "PAPER 3",
        "Nagano & Schaub",
        "2025",
        "AAS 25-637",
        "Fault-aware training keeps mission scheduling resilient after wheel failures.",
        "Resilience",
        GREEN,
        GREENBG,
    ),
]
cxs = [M, M + 3.9, M + 7.8]
card_shapes = []
for (tag, auth, year, venue, idea, key, col, bg), cx in zip(cards, cxs):
    c = rect(
        s,
        cx,
        1.90,
        3.62,
        3.62,
        fill=WHITE,
        line=LINE,
        radius=0.05,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        soft=True,
    )
    rect(s, cx, 1.90, 3.62, 0.1, fill=col, line=None)
    txt(
        s,
        cx + 0.28,
        2.16,
        3.1,
        0.26,
        [{"t": tag, "size": 8.5, "bold": True, "color": col, "spc": 170}],
    )
    txt(
        s,
        cx + 0.28,
        2.42,
        3.1,
        0.55,
        [
            {
                "t": auth,
                "size": 16,
                "bold": True,
                "color": NAVY,
                "font": FONTSB,
                "line": 1.05,
            }
        ],
    )
    txt(
        s,
        cx + 0.28,
        2.96,
        3.1,
        0.5,
        [{"t": f"{venue}, {year}", "size": 9, "color": GREYL, "line": 1.1}],
    )
    line_h(s, cx + 0.28, 3.46, 3.05, LINE)
    txt(
        s,
        cx + 0.28,
        3.60,
        3.06,
        1.0,
        [{"t": idea, "size": 12.5, "color": INK, "line": 1.2}],
    )
    chip(s, cx + 0.28, 4.82, 1.85, 0.42, key, fill=bg, color=col, size=11, radius=0.3)
    card_shapes.append(c)

txt(
    s,
    M,
    5.82,
    11.4,
    0.45,
    [
        {
            "t": [
                ("Common question: ", {"bold": True, "color": NAVY}),
                (
                    "how can a learned controller remain useful when the real spacecraft does not behave as modelled?",
                    {"italic": True},
                ),
            ],
            "size": 14.5,
            "color": GREY,
        }
    ],
)
footer(s, 8)
animate(s, [[card_shapes[0]], [card_shapes[1]], [card_shapes[2]]])
footnote(
    s,
    "Papers: Yang, Jin & Rao, J. Franklin Inst. 362 (2025); Lu et al., Aerosp. Sci. Technol. 168 (2026); "
    "Nagano & Schaub, AAS 25-637 (2025).",
    y=6.42,
)
transition(s)
notes(
    s,
    "5:30  Three papers, each answering a different part: adaptation, safety, resilience. (~30 s)",
)


# ================================================================ 9-11 PAPERS
def paper_slide(
    num,
    tag,
    ttl,
    problem,
    method,
    contribution,
    opens,
    relevance,
    citation,
    accent=PURPLE,
    bg=PURPBG,
):
    s = slide_new(WHITE)
    kicker(s, f"03 \u00b7 RELATED RESEARCH   |   {tag}", accent)
    txt(
        s,
        M,
        0.72,
        11.4,
        0.92,
        [
            {
                "t": ttl,
                "size": 19,
                "bold": True,
                "color": NAVY,
                "font": FONTSB,
                "line": 1.1,
            }
        ],
    )
    line_h(s, M, 1.62, CW, LINE)

    txt(
        s,
        M,
        1.84,
        6.2,
        0.26,
        [{"t": "PROBLEM", "size": 8.5, "bold": True, "color": accent, "spc": 170}],
    )
    txt(
        s,
        M,
        2.10,
        6.25,
        0.95,
        [{"t": problem, "size": 14.5, "color": INK, "line": 1.22}],
    )

    txt(
        s,
        M,
        3.18,
        6.2,
        0.26,
        [{"t": "METHOD", "size": 8.5, "bold": True, "color": accent, "spc": 170}],
    )
    meth = [
        {
            "t": m,
            "size": 13,
            "color": GREY,
            "bullet": True,
            "bucolor": accent,
            "sp_after": 7,
            "line": 1.12,
        }
        for m in method
    ]
    txt(s, M, 3.44, 6.25, 1.75, meth)

    rect(
        s,
        M,
        5.28,
        6.25,
        0.90,
        fill=bg,
        line=None,
        radius=0.06,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M + 0.24,
        5.40,
        5.8,
        0.7,
        [{"t": contribution, "size": 13, "color": accent, "bold": True, "line": 1.15}],
    )

    rect(
        s,
        7.7,
        1.84,
        4.7,
        4.34,
        fill=PALE2,
        line=None,
        radius=0.05,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        7.95,
        2.00,
        4.2,
        0.26,
        [
            {
                "t": "WHAT IT LEAVES OPEN",
                "size": 8.5,
                "bold": True,
                "color": RED,
                "spc": 160,
            }
        ],
    )
    txt(
        s,
        7.95,
        2.28,
        4.25,
        2.0,
        [
            {
                "t": o,
                "size": 12,
                "color": GREY,
                "bullet": True,
                "bucolor": RED,
                "sp_after": 8,
                "line": 1.1,
            }
            for o in opens
        ],
    )
    line_h(s, 7.95, 4.42, 4.2, LINE)
    txt(
        s,
        7.95,
        4.56,
        4.2,
        0.26,
        [
            {
                "t": "RELEVANCE TO THIS THESIS",
                "size": 8.5,
                "bold": True,
                "color": BLUE,
                "spc": 150,
            }
        ],
    )
    txt(
        s,
        7.95,
        4.84,
        4.25,
        0.95,
        [{"t": relevance, "size": 12, "color": INK, "italic": True, "line": 1.16}],
    )
    footnote(s, citation, y=6.48)
    footer(s, num)
    transition(s)
    return s


s = paper_slide(
    9,
    "PAPER 1 OF 3",
    "Reinforcement Learning Based Attitude Fault-Tolerant Control of Spacecraft with Unknown System Model",
    "Classical fault-tolerant control needs an accurate model and known actuator behaviour \u2014 which real "
    "nanosatellites do not provide.",
    [
        "Offline: RL with optimal control gives a nominal policy.",
        "Online: a neural observer estimates the unknown dynamics and input gain.",
        "Recursive least squares updates the critic; a feed-forward term compensates additive faults.",
    ],
    "The policy adapts online to actuator faults without a known system model.",
    [
        "fault severities never seen in training",
        "sensor faults, not only actuator faults",
        "safety of the learned action itself",
        "cost of running the adaptation onboard",
    ],
    "Closest to this thesis in problem statement \u2014 and furthest from its deployment claim.",
    "Yang, S., Jin, L. & Rao, J. (2025). Journal of the Franklin Institute, 362, 107741. doi:10.1016/j.jfranklin.2025.107741",
)
notes(
    s,
    "6:00  Paper one. Offline RL plus an online neural observer and RLS, so the policy adapts when the model "
    "is unknown. Strong on adaptation, but the fault set is the simulated one, and nothing is said about a "
    "flight processor. (~50 s)",
)

s = paper_slide(
    10,
    "PAPER 2 OF 3",
    "Safe Reinforcement Learning Based Agile Satellite Attitude Control for Non-Cooperative Target Tracking with "
    "Operation Constraints and Actuator Faults",
    "Agile tracking must respect forbidden pointing zones, rate and torque limits \u2014 while an actuator is "
    "losing effectiveness.",
    [
        "Fault identification estimates effectiveness loss and additive fault.",
        "The task is written as a constrained Markov decision process.",
        "A worst-case soft actor-critic solves it, with faults inside the constraint set.",
    ],
    "Fault tolerance, operational constraints and safety in one learned controller.",
    [
        "computational weight for an embedded target",
        "verification of the safety claim",
        "faults outside the training distribution",
        "migration from workstation to flight hardware",
    ],
    "Shows that performance without constraints is not a result \u2014 constraints belong in the design.",
    "Lu, W. et al. (2026). Aerospace Science and Technology, 168, 111238. doi:10.1016/j.ast.2025.111238",
    accent=AMBER,
    bg=AMBBG,
)
notes(
    s,
    "6:50  Paper two moves from 'can RL control it' to 'can it obey constraints while doing so'. Constrained "
    "MDP, worst-case SAC, with fault identification. This is the safety argument I borrow. (~50 s)",
)

s = paper_slide(
    11,
    "PAPER 3 OF 3",
    "Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling",
    "At mission level, wheel faults cut agility: reduced manoeuvres, safe-mode transitions and missed imaging "
    "targets.",
    [
        "Fault-injected training: policies are trained inside a faulty environment.",
        "Fault information is added to the observation vector.",
        "Recurrent networks use temporal history to infer fault signatures.",
    ],
    "Resilience must be designed into training \u2014 not added after it.",
    [
        "it is a scheduler, not an attitude controller",
        "no continuous-control stability argument",
        "simulation-only evidence",
    ],
    "Directly motivates this thesis\u2019s train/test split: nominal vs fault-aware training, then unseen faults.",
    "Nagano, Y. & Schaub, H. (2025). AAS 25-637, Enhancing Fault Resilience in RL-Based Satellite Autonomous "
    "Task Scheduling.",
    accent=GREEN,
    bg=GREENBG,
)
notes(
    s,
    "7:40  Paper three is not an attitude controller - it schedules imaging tasks. But its message is the one "
    "I adopt: resilience must be inside the training. That gives the train/test split of my evaluation. (~45 s)",
)

# ================================================================ 12 GAPS
s = slide_new(WHITE)
header(
    s,
    12,
    "04 \u00b7 GAPS & NEW IDEAS",
    "From fault-tolerant RL to trustworthy fault-tolerant RL",
    tsize=27,
)

gaps = [
    (
        "Unseen faults",
        "Most results are evaluated on the fault set used for training.",
        "Disjoint train / test fault distributions: severity, timing, combinations.",
    ),
    (
        "Unverified actions",
        "A neural policy can leave the region where it was validated.",
        "Physics-based governor: vet the action, otherwise hand over to LQR.",
    ),
    (
        "Detection and control are separate",
        "Health estimation and the control law are designed apart.",
        "Health estimate \u0125 inside the observation \u2014 no access to the true h.",
    ),
    (
        "Deployment is assumed",
        "A policy that runs on a GPU is not a flight controller.",
        "Latency budget, quantisation, and HIL on an MCU.",
    ),
]
yy = 1.86
row_shapes = []
for i, (g, why, idea) in enumerate(gaps):
    r = rect(
        s,
        6.35,
        yy,
        5.95,
        1.04,
        fill=PALE2,
        line=None,
        radius=0.06,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M,
        yy + 0.04,
        0.42,
        0.3,
        [{"t": f"0{i + 1}", "size": 11, "bold": True, "color": SKYL, "font": FONTSB}],
    )
    txt(
        s,
        M + 0.42,
        yy,
        4.55,
        0.34,
        [{"t": g, "size": 14, "bold": True, "color": NAVY, "font": FONTSB}],
    )
    txt(
        s,
        M + 0.42,
        yy + 0.36,
        4.6,
        0.64,
        [{"t": why, "size": 11, "color": GREY, "line": 1.1}],
    )
    txt(
        s,
        6.62,
        yy + 0.04,
        5.5,
        0.96,
        [
            {
                "t": idea,
                "size": 12.5,
                "color": INK,
                "bullet": True,
                "buchar": "\u2192",
                "bucolor": SKY,
                "line": 1.14,
            }
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    row_shapes.append(r)
    yy += 1.16

footer(s, 12)
animate(s, [[rr] for rr in row_shapes])
transition(s)
notes(
    s,
    "8:25  Four gaps. First, unseen faults are usually not tested. Second, a learned action is not verified. "
    "Third, detection and control are designed apart. Fourth, deployment is assumed rather than measured. "
    "Each gap maps to one concrete decision in my method. (~55 s)",
)

# ================================================================ 13 CONCLUSION
s = slide_new(WHITE)
header(
    s, 13, "05 \u00b7 CONCLUSION", "What I take away \u2014 and what I intend to prove"
)

takeaways = [
    (
        "ADCS is mission-critical",
        "The spacecraft must know and control its orientation, continuously.",
    ),
    (
        "Complexity follows the mission",
        "Not every satellite needs the most advanced controller.",
    ),
    (
        "Faults are the design driver",
        "On a nanosatellite, survival is a software property.",
    ),
    (
        "RL adds adaptability \u2014 and questions",
        "Generalisation, safety, unseen faults, embedded cost.",
    ),
]
pos = [(M, 1.86), (M + 5.7, 1.86), (M, 3.06), (M + 5.7, 3.06)]
concl_shapes = []
for i, ((hd, bd), (x, y)) in enumerate(zip(takeaways, pos)):
    bar = rect(s, x, y + 0.04, 0.045, 0.82, fill=SKY)
    txt(
        s,
        x + 0.22,
        y,
        5.05,
        0.34,
        [
            {
                "t": f"{i + 1}.  {hd}",
                "size": 14.5,
                "bold": True,
                "color": NAVY,
                "font": FONTSB,
            }
        ],
    )
    txt(
        s,
        x + 0.22,
        y + 0.36,
        5.1,
        0.62,
        [{"t": bd, "size": 11.5, "color": GREY, "line": 1.12}],
    )
    concl_shapes.append(bar)

band = rect(
    s,
    M,
    4.42,
    11.43,
    1.58,
    fill=NAVY,
    line=None,
    radius=0.05,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.45,
    4.62,
    10.6,
    0.24,
    [
        {
            "t": "THE GOAL",
            "size": 8.5,
            "bold": True,
            "color": RGBColor(0x8C, 0xBC, 0xDF),
            "spc": 200,
        }
    ],
)
txt(
    s,
    M + 0.45,
    4.92,
    10.55,
    1.15,
    [
        {
            "t": [
                (
                    "Not to replace a classical controller with a network \u2014 ",
                    {"color": RGBColor(0xBF, 0xD8, 0xE9)},
                ),
                (
                    "but to find out whether learning can make attitude control more adaptive and fault-tolerant "
                    "without giving up safety, reliability and deployability.",
                    {"color": WHITE, "bold": True},
                ),
            ],
            "size": 15.5,
            "line": 1.25,
        }
    ],
)
footer(s, 13)
animate(s, [[c] for c in concl_shapes] + [[band]])
transition(s)
notes(
    s,
    "9:20  Four takeaways: the loop is mission-critical; complexity follows the mission; faults drive the "
    "design; RL adds adaptability and new questions. The goal is not to replace LQR - it is to find out "
    "whether learning can be made trustworthy enough to fly. (~40 s)",
)

# ================================================================ 14 THANK YOU
s = slide_new(NAVY)
pic(s, os.path.join(ASSETS, "closing.jpg"), 0, 0, w=W, h=H)
grad(s, 0, 0, W, H, [(0, "071F36", 94), (60, "082239", 72), (100, "071F36", 34)])
txt(
    s,
    M,
    2.05,
    8.0,
    0.3,
    [
        {
            "t": "SEMINAR I",
            "size": 11,
            "bold": True,
            "color": RGBColor(0x9F, 0xC8, 0xE4),
            "spc": 260,
        }
    ],
)
txt(
    s,
    M,
    2.42,
    8.4,
    0.95,
    [
        {
            "t": "Thank you for your attention",
            "size": 40,
            "bold": True,
            "color": WHITE,
            "font": FONTSB,
        }
    ],
)
rect(s, M, 3.55, 1.05, 0.045, fill=SKYL)
txt(
    s,
    M,
    3.78,
    7.0,
    0.42,
    [
        {
            "t": "Questions and discussion",
            "size": 18,
            "color": RGBColor(0xBF, 0xD8, 0xE9),
            "font": FONTL,
        }
    ],
)
txt(
    s,
    M,
    4.62,
    7.4,
    1.2,
    [
        {"t": "Pouria Zarei", "size": 17, "bold": True, "color": WHITE, "sp_after": 3},
        {
            "t": "M.Sc. Control Engineering  \u00b7  University of Tehran",
            "size": 12,
            "color": RGBColor(0xC9, 0xDD, 0xEC),
            "sp_after": 2,
        },
        {
            "t": "Supervisor: Prof. Mohammad Javad Yazdanpanah",
            "size": 12,
            "color": RGBColor(0xC9, 0xDD, 0xEC),
            "sp_after": 2,
        },
        {"t": "Pouria.zarei@ut.ac.ir", "size": 12, "color": RGBColor(0x9F, 0xC8, 0xE4)},
    ],
)
footnote(
    s,
    "Image: NASA/JPL-Caltech, NISAR in Earth orbit (artist\u2019s concept), image PIA26285.",
    y=6.72,
    dark=True,
)
footer(s, 14, dark=True)
transition(s)
notes(
    s,
    "10:00  Thank you - happy to take questions. Be ready for: why not MPC? what about the estimator? "
    "how do you guarantee safety?",
)

# ================================================================ 15 REFERENCES
s = slide_new(WHITE)
header(s, 15, "APPENDIX", "References")

refs = [
    (
        "1",
        "Yang, S., Jin, L. & Rao, J. (2025). Reinforcement learning based attitude fault-tolerant control "
        "of spacecraft with unknown system model. Journal of the Franklin Institute, 362, 107741. "
        "doi:10.1016/j.jfranklin.2025.107741",
    ),
    (
        "2",
        "Lu, W., Zhuang, H., Geng, Z., Shen, Q., Mu, Z., Wu, S., Razoumny, V. Y. & Razoumny, Y. N. (2026). "
        "Safe reinforcement learning based agile satellite attitude control for non-cooperative target "
        "tracking with operation constraints and actuator faults. Aerospace Science and Technology, 168, "
        "111238. doi:10.1016/j.ast.2025.111238",
    ),
    (
        "3",
        "Nagano, Y. & Schaub, H. (2025). Enhancing fault resilience in RL-based satellite autonomous task "
        "scheduling. AAS 25-637.",
    ),
    (
        "4",
        "NASA Small Spacecraft Systems Virtual Institute (2026). State-of-the-Art of Small Spacecraft "
        "Technology \u2014 Guidance, Navigation, and Control.",
    ),
    (
        "5",
        "NASA SSRI Knowledge Base. Attitude Determination and Control \u2014 Small Satellite Systems "
        "Engineering.",
    ),
    (
        "6",
        "Pouria Zarei (2026). M.Sc. thesis proposal: Fault-Tolerant Attitude Control of Nanosatellites "
        "Using Reinforcement Learning \u2014 From Simulation to Hardware-in-the-Loop Implementation. "
        "University of Tehran.",
    ),
]
yy = 1.84
for n, t in refs:
    lines = measure_lines(t, 11, 10.0)
    txt(
        s, M, yy, 0.4, 0.3, [{"t": f"[{n}]", "size": 10.5, "bold": True, "color": BLUE}]
    )
    txt(
        s,
        M + 0.5,
        yy,
        10.55,
        0.20 * lines + 0.1,
        [{"t": t, "size": 11, "color": GREY, "line": 1.15}],
    )
    yy += 0.185 * lines + 0.30

line_h(s, M, 6.28, 5.6, LINE)
txt(
    s,
    M,
    6.36,
    5.9,
    0.26,
    [{"t": "IMAGE CREDITS", "size": 8, "bold": True, "color": BLUE, "spc": 160}],
)
txt(
    s,
    M,
    6.56,
    6.2,
    0.4,
    [
        {
            "t": "All spacecraft imagery: NASA / JPL-Caltech, public domain (PIA26285, PIA22457).",
            "size": 9,
            "color": GREYL,
        }
    ],
)
footer(s, 15)
transition(s)
notes(s, "Backup slide - references and image credits, in case of questions.")

prs.save(OUT)
print("saved", OUT, len(prs.slides._sldIdLst), "slides")
