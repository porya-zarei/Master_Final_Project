# -*- coding: utf-8 -*-
"""
Seminar I deck builder - Persian (RTL) edition  v2
کنترل وضعیت خطاپذیر نانوماهواره‌ها با استفاده از یادگیری تقویتی
پوریا زارعی - دانشگاه تهران
"""

import os
from lxml import etree
from pptx import Presentation
from pptx.util import Inches as In, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "Seminar_I_Pouria_Zarei_FA.pptx")

INK = RGBColor(0x12, 0x2A, 0x40)
NAVY = RGBColor(0x0E, 0x33, 0x55)
BLUE = RGBColor(0x16, 0x63, 0x9E)
SKY = RGBColor(0x3E, 0x8F, 0xC4)
SKYL = RGBColor(0x7F, 0xB9, 0xDC)
PALE = RGBColor(0xEC, 0xF4, 0xFA)
PALE2 = RGBColor(0xF7, 0xFB, 0xFD)
LINE = RGBColor(0xD5, 0xE2, 0xEC)
GREY = RGBColor(0x46, 0x58, 0x68)
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

FA = "Dubai"
EN = "Segoe UI"

M = 0.95
R = 13.333 - M
W, H = 13.333, 7.5
CW = W - 2 * M
TOTAL = 16

prs = Presentation()
prs.slide_width = In(W)
prs.slide_height = In(H)
BLANK = prs.slide_layouts[6]

DIGITS = str.maketrans(
    "0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
)


def fa(t):
    return str(t).translate(DIGITS)


def is_fa(text):
    return any("\u0600" <= ch <= "\u06ff" for ch in text)


import re

_FA = re.compile(r"[\u0600-\u06ff]")
_LAT = re.compile(r"[A-Za-z0-9]")


def bidi_pad(text):
    """Replace spaces at Persian<->Latin boundaries with NBSP so PowerPoint
    does not swallow them in an RTL paragraph."""
    if not is_fa(text):
        return text
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            prev = text[i - 1] if i else " "
            nxt = text[i + 1] if i + 1 < len(text) else " "
            if _FA.match(prev) and _LAT.match(nxt):
                out.append("\u00a0")
                continue
            if _LAT.match(prev) and _FA.match(nxt):
                out.append("\u00a0\u00a0")
                continue
        out.append(ch)
    return "".join(out)


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
    align=PP_ALIGN.RIGHT,
    margins=(0, 0, 0, 0),
    wrap=True,
    rtl=True,
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
        pPr = p._p.get_or_add_pPr()
        plain = it["t"] if isinstance(it["t"], str) else "".join(x for x, _ in it["t"])
        if rtl and it.get("rtl", True) and is_fa(plain):
            pPr.set("rtl", "1")
        if it.get("sp_before") is not None:
            p.space_before = Pt(it["sp_before"])
        if it.get("sp_after") is not None:
            p.space_after = Pt(it["sp_after"])
        if it.get("line") is not None:
            p.line_spacing = it["line"]
        if it.get("bullet"):
            pPr.set("marL", str(int(In(0.30))))
            pPr.set("indent", str(int(-In(0.30))))
            buClr = etree.SubElement(pPr, qn("a:buClr"))
            srgb = etree.SubElement(buClr, qn("a:srgbClr"))
            srgb.set("val", str(it.get("bucolor", BLUE)))
            buSz = etree.SubElement(pPr, qn("a:buSzPct"))
            buSz.set("val", "85000")
            buFont = etree.SubElement(pPr, qn("a:buFont"))
            buFont.set("typeface", "Arial")
            buChar = etree.SubElement(pPr, qn("a:buChar"))
            buChar.set("char", it.get("buchar", "\u25aa"))
        segs = it["t"] if isinstance(it["t"], list) else [(it["t"], {})]
        for seg_text, ov in segs:
            r = p.add_run()
            r.text = bidi_pad(seg_text)
            f = r.font
            f.name = ov.get("font", it.get("font", FA))
            f.size = Pt(ov.get("size", it.get("size", 16)))
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
    size=12,
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
    tf.margin_left = tf.margin_right = In(0.08)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p._p.get_or_add_pPr().set("rtl", "1")
    r = p.add_run()
    r.text = text
    r.font.name = FA
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return sh


def kicker(s, text, color=BLUE):
    txt(s, M, 0.46, CW, 0.26, [{"t": text, "size": 10.5, "bold": True, "color": color}])


def footer(s, num, dark=False, y=7.03):
    c = RGBColor(0x9A, 0xB4, 0xC7) if dark else GREYL
    txt(
        s,
        M,
        y,
        1.4,
        0.24,
        [
            {
                "t": fa(num) + " / " + fa(TOTAL),
                "size": 8.5,
                "color": c,
                "align": PP_ALIGN.LEFT,
                "rtl": False,
            }
        ],
    )
    txt(
        s,
        W - M - 8.6,
        y,
        8.6,
        0.24,
        [
            {
                "t": "کنترل وضعیت خطاپذیر نانوماهواره‌ها با یادگیری تقویتی   \u00b7   سمینار اول",
                "size": 8.5,
                "color": c,
            }
        ],
    )


def header(s, num, kick, ttl, tsize=27, sub=None, rule=True):
    kicker(s, kick)
    txt(
        s,
        M,
        0.70,
        CW,
        0.66,
        [{"t": ttl, "size": tsize, "bold": True, "color": NAVY, "line": 1.15}],
    )
    if sub:
        txt(s, M, 1.30, CW, 0.3, [{"t": sub, "size": 12.5, "color": GREY, "line": 1.1}])
    if rule:
        line_h(s, M, 1.64, CW, LINE)
    footer(s, num)


def footnote(s, text, y=6.66, w=None, dark=False, align=PP_ALIGN.RIGHT, rtl=None):
    if rtl is None:
        rtl = is_fa(text)
    txt(
        s,
        M,
        y,
        w or (CW - 0.4),
        0.3,
        [
            {
                "t": text,
                "size": 8.5,
                "align": align,
                "rtl": rtl,
                "font": (FA if rtl else EN),
                "color": (RGBColor(0xA9, 0xC2, 0xD4) if dark else GREYL),
            }
        ],
    )


def notes(s, text):
    s.notes_slide.notes_text_frame.text = text


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


# ================================================================ 1 عنوان
s = slide_new(NAVY)
pic(s, os.path.join(ASSETS, "hero.jpg"), 0, 0, w=W, h=H)
grad(
    s,
    0,
    0,
    W,
    H,
    [(0, "08223C", 10), (30, "08223C", 55), (58, "0A2A48", 92), (100, "08223C", 97)],
)

txt(
    s,
    3.9,
    0.72,
    R - 3.9,
    0.3,
    [
        {
            "t": "دانشگاه تهران",
            "size": 12.5,
            "bold": True,
            "color": RGBColor(0x9F, 0xC8, 0xE4),
        }
    ],
)
txt(
    s,
    3.9,
    1.06,
    R - 3.9,
    0.3,
    [
        {
            "t": "دانشکده مهندسی برق و کامپیوتر  \u00b7  کارشناسی ارشد مهندسی کنترل",
            "size": 10,
            "color": RGBColor(0x86, 0xAE, 0xCB),
        }
    ],
)
txt(
    s,
    3.9,
    2.20,
    R - 3.9,
    2.4,
    [
        {
            "t": "کنترل وضعیت خطاپذیر نانوماهواره‌ها با استفاده از یادگیری تقویتی",
            "size": 33,
            "bold": True,
            "color": WHITE,
            "line": 1.28,
        }
    ],
)
rect(s, R - 1.1, 4.86, 1.1, 0.045, fill=SKYL)
txt(
    s,
    3.9,
    5.08,
    R - 3.9,
    0.6,
    [
        {
            "t": "از مبانی کنترل وضعیت ماهواره تا مسئله پژوهشی",
            "size": 15,
            "color": RGBColor(0xBF, 0xD8, 0xE9),
        }
    ],
)
txt(
    s,
    3.9,
    5.74,
    R - 3.9,
    1.1,
    [
        {"t": "پوریا زارعی", "size": 19, "bold": True, "color": WHITE, "sp_after": 4},
        {
            "t": "استاد راهنما:  دکتر محمدجواد یزدان‌پناه",
            "size": 12.5,
            "color": RGBColor(0xD3, 0xE4, 0xF0),
            "sp_after": 3,
        },
        {
            "t": "سمینار اول  \u00b7  ۱۴۰۵",
            "size": 11,
            "color": RGBColor(0x8F, 0xB4, 0xCE),
        },
    ],
)
footnote(
    s,
    "تصویر: NASA/JPL-Caltech \u2014 ماهواره NISAR در مدار زمین (طرح هنری)، شماره PIA26285.",
    y=6.80,
    dark=True,
)
footer(s, 1, dark=True, y=7.12)
transition(s)
notes(
    s,
    "۰:۰۰  سلام. پوریا زارعی، کارشناسی ارشد مهندسی کنترل. در این ده دقیقه: چرا کنترل وضعیت "
    "نانوماهواره سخت است، پیشنهاد پژوهشی من چیست، سه مقاله اخیر چه کرده‌اند و شکاف کجاست. (~۳۰ ثانیه)",
)

# ================================================================ 2 مسیر ارائه
s = slide_new(WHITE)
header(s, 2, "مسیر ارائه", "از مسئله مهندسی تا پرسش پژوهشی", rule=False)
line_h(s, M, 2.16, CW, LINE, 1.0)

steps = [
    ("۰۱", "ماهواره و ADCS", "چه چیزی را باید در فضاپیما کنترل کنیم؟"),
    ("۰۲", "سامانه ADCS", "ماهواره‌ها امروز چگونه کنترل می‌شوند؟"),
    ("۰۳", "مسئله پژوهش", "چرا یادگیری تقویتی و تحمل خطا؟"),
    ("۰۴", "پژوهش‌های مرتبط", "در سال‌های اخیر چه کارهایی شده است؟"),
    ("۰۵", "شکاف پژوهشی", "چه مسائلی هنوز حل نشده‌اند؟"),
    ("۰۶", "جمع‌بندی", "این مسیر چه مسئله‌ای را دنبال می‌کند؟"),
]
nw, ng = 1.78, 0.135
nodes = []
for i, (num, lab, desc) in enumerate(steps):
    x = R - (i + 1) * nw - i * ng
    dot = rect(s, x + nw - 0.16, 2.09, 0.14, 0.14, fill=SKY, shape=MSO_SHAPE.OVAL)
    n = txt(s, x, 2.44, nw, 0.52, [{"t": num, "size": 25, "bold": True, "color": BLUE}])
    lab_box = txt(
        s, x, 3.02, nw, 0.42, [{"t": lab, "size": 14, "bold": True, "color": NAVY}]
    )
    d = txt(
        s, x, 3.46, nw, 0.9, [{"t": desc, "size": 10.5, "color": GREY, "line": 1.4}]
    )
    nodes.append((dot, n, lab_box, d))

txt(
    s,
    M,
    5.30,
    CW,
    0.44,
    [{"t": "ده دقیقه، شش گام \u2014 یک استدلال.", "size": 18, "color": BLUE}],
)
animate(s, [[n[0]] for n in nodes])
transition(s)
notes(
    s,
    "۰:۳۰  ارائه شش گام دارد: از سیستم فیزیکی شروع می‌کنم، به پرسش پژوهشی می‌رسم، سه مقاله را "
    "مقایسه می‌کنم و با شکاف پژوهشی تمام می‌کنم. (~۲۰ ثانیه)",
)

# ================================================================ 3 ماهواره و ADCS
s = slide_new(WHITE)
header(s, 3, "۰۱ \u00b7 مسئله", "ماهواره چیست؟ سامانه ADCS چیست؟")

txt(
    s,
    6.75,
    1.86,
    R - 6.75,
    0.32,
    [{"t": "ماهواره چیست؟", "size": 15, "bold": True, "color": BLUE}],
)
txt(
    s,
    6.75,
    2.22,
    R - 6.75,
    1.45,
    [
        {
            "t": "ماهواره برای مأموریت‌هایی مانند سنجش از دور، مخابرات، ناوبری و پژوهش علمی به مدار فرستاده می‌شود. "
            "اما فارغ از نوع مأموریت، یک مسئله تقریباً همیشه وجود دارد:",
            "size": 11.5,
            "color": GREY,
            "line": 1.5,
        }
    ],
)
rect(
    s,
    6.75,
    3.52,
    R - 6.75,
    0.84,
    fill=PALE,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    6.95,
    3.62,
    R - 7.2,
    0.66,
    [
        {
            "t": "ماهواره باید بداند در چه جهتی قرار گرفته و بتواند جهت خود را کنترل کند.",
            "size": 12,
            "bold": True,
            "color": NAVY,
            "line": 1.4,
        }
    ],
)

txt(
    s,
    M,
    1.86,
    5.5,
    0.32,
    [{"t": "سامانه ADCS چیست؟", "size": 15, "bold": True, "color": BLUE}],
)
txt(
    s,
    M,
    2.20,
    5.5,
    0.26,
    [
        {
            "t": "Attitude Determination and Control System",
            "size": 9,
            "color": GREYL,
            "font": EN,
            "rtl": False,
            "align": PP_ALIGN.RIGHT,
        }
    ],
)
ads = [
    "وضعیت و نرخ چرخش ماهواره را تعیین می‌کند",
    "وضعیت مطلوب را حفظ می‌کند",
    "در صورت نیاز ماهواره را به وضعیت جدید می‌برد",
    "اثر اغتشاشات را کاهش می‌دهد",
    "تکانه زاویه‌ای عملگرها را مدیریت می‌کند",
]
txt(
    s,
    M,
    2.54,
    5.5,
    1.85,
    [
        {"t": a, "size": 10.5, "color": INK, "bullet": True, "sp_after": 4, "line": 1.3}
        for a in ads
    ],
)

# ADCS loop, right to left
DY, BH = 4.62, 0.82
loop = [
    ("حسگرها", "ژیرو \u00b7 ستاره‌یاب \u00b7 خورشید"),
    ("تخمین وضعیت", "وضعیت و نرخ"),
    ("کنترلر", "قانون کنترل"),
    ("عملگرها", "چرخ + مغناطیسی"),
    ("ماهواره", "دینامیک صلب"),
]
BW, GAP = 2.02, 0.27
boxes = []
for i, (l1, l2) in enumerate(loop):
    x = R - (i + 1) * BW - i * GAP
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
    tf.margin_left = tf.margin_right = In(0.04)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p._p.get_or_add_pPr().set("rtl", "1")
    r = p.add_run()
    r.text = l1
    r.font.name = FA
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2._p.get_or_add_pPr().set("rtl", "1")
    r2 = p2.add_run()
    r2.text = l2
    r2.font.name = FA
    r2.font.size = Pt(7.5)
    r2.font.color.rgb = GREYL
    boxes.append(b)
    if i < 4:
        arrow(s, x + BW + GAP - 0.03, DY + BH / 2, x + BW + 0.03, DY + BH / 2, SKY, 1.0)

x_left = R - 5 * BW - 4 * GAP
arrow(
    s,
    x_left + BW / 2,
    DY + BH + 0.02,
    x_left + BW / 2,
    DY + BH + 0.38,
    SKY,
    1.0,
    head=False,
)
arrow(
    s, x_left + BW / 2, DY + BH + 0.38, R - BW / 2, DY + BH + 0.38, SKY, 1.0, head=False
)
arrow(s, R - BW / 2, DY + BH + 0.38, R - BW / 2, DY + BH + 0.04, SKY, 1.0)
txt(
    s,
    5.6,
    DY + BH + 0.42,
    2.3,
    0.24,
    [
        {
            "t": "بازخورد وضعیت",
            "size": 8.5,
            "color": GREYL,
            "italic": True,
            "align": PP_ALIGN.CENTER,
        }
    ],
)

txt(
    s,
    M,
    6.36,
    CW,
    0.34,
    [
        {
            "t": "ADCS فقط «فرمان دادن به موتور» نیست؛ یک حلقه بسته با دینامیک غیرخطی، عدم‌قطعیت و محدودیت سخت‌افزاری است.",
            "size": 11,
            "color": INK,
            "italic": True,
        }
    ],
)
footnote(
    s,
    "Source: NASA, State-of-the-Art of Small Spacecraft Technology \u2014 GNC (2026); "
    "NASA SSRI Knowledge Base \u2014 ADCS.",
    y=6.74,
    align=PP_ALIGN.LEFT,
)
animate(s, [[boxes[i]] for i in range(5)])
transition(s)
notes(
    s,
    "۱:۰۰  ماهواره باید بداند کجاست و بتواند خودش را بچرخاند. ADCS این حلقه را می‌بندد: حسگر، تخمین، "
    "کنترلر، عملگر. نکته مهم: این یک مسئله کنترل بسته در محیط غیرخطی و نامعین است. (~۶۰ ثانیه)",
)

# ================================================================ 4 یک نسخه برای همه
s = slide_new(WHITE)
header(s, 4, "۰۱ \u00b7 مسئله", "یک نسخه برای همه وجود ندارد")

rows = [
    ("آموزشی یا ساده (CubeSat)", "پایدارسازی اولیه", "کنترل مغناطیسی، B-dot، PD/PID"),
    ("دقیق (CubeSat / SmallSat)", "کنترل سه‌محوره", "PD/PID، LQR، کنترل کواترنیون"),
    ("سنجش از دور چابک", "مانور سریع و دقت بالا", "LQR، کنترل غیرخطی، MPC"),
    ("علمی / تصویربرداری دقیق", "دقت بسیار بالا", "کنترل بهینه و مدل‌محور"),
    ("ردیابی هدف غیرهمکار", "چابکی، محدودیت، خودمختاری", "MPC، Safe / Hybrid RL"),
    ("مأموریت پرارزش", "اطمینان و عمر بالا", "کنترل مقاوم + افزونگی"),
]
tx, ty = M, 1.86
colw = [3.55, 3.15, 4.73]
rect(s, tx, ty, sum(colw), 0.44, fill=NAVY, line=None)
heads = ["نوع مأموریت / ماهواره", "نیاز اصلی", "روش‌های متداول"]
cx = tx + sum(colw)
for cw_, ht in zip(colw, heads):
    cx -= cw_
    txt(
        s,
        cx + 0.16,
        ty + 0.10,
        cw_ - 0.24,
        0.26,
        [{"t": ht, "size": 10.5, "bold": True, "color": WHITE}],
    )
for i, row in enumerate(rows):
    ry = ty + 0.44 + i * 0.50
    if i % 2 == 0:
        rect(s, tx, ry, sum(colw), 0.50, fill=PALE2, line=None)
    cx = tx + sum(colw)
    for cw_, val in zip(colw, row):
        cx -= cw_
        txt(
            s,
            cx + 0.16,
            ry + 0.13,
            cw_ - 0.24,
            0.3,
            [
                {
                    "t": val,
                    "size": 10.5,
                    "color": INK if cw_ == colw[0] else GREY,
                    "bold": cw_ == colw[0],
                }
            ],
        )
line_h(s, tx, ty + 0.44 + len(rows) * 0.50, sum(colw), LINE)

q1 = txt(
    s,
    M,
    5.56,
    3.3,
    0.32,
    [
        {
            "t": "آیا کنترلر پیچیده‌تر همیشه بهتر است؟",
            "size": 12,
            "bold": True,
            "color": NAVY,
        }
    ],
)
no = chip(
    s, M + 3.80, 5.54, 1.0, 0.34, "خیر", fill=REDBG, color=RED, size=10.5, radius=0.4
)
txt(
    s,
    M,
    5.96,
    7.0,
    0.7,
    [
        {
            "t": "پیچیدگی بیشتر یعنی محاسبات بیشتر، راستی‌آزمایی سخت‌تر و حساسیت بیشتر به فرضیات. "
            "کنترلر باید به اندازه مأموریت پیشرفته باشد، نه به اندازه ممکن.",
            "size": 10.5,
            "color": GREY,
            "line": 1.45,
        }
    ],
)
note2 = txt(
    s,
    7.85,
    5.86,
    R - 7.85,
    0.9,
    [
        {
            "t": "اندازه ماهواره، پیچیدگی کنترلر را تعیین نمی‌کند؛ مأموریت تعیین می‌کند.",
            "size": 11.5,
            "bold": True,
            "color": BLUE,
            "line": 1.4,
        }
    ],
)
footer(s, 4)
animate(s, [[q1, no]])
transition(s)
notes(
    s,
    "۲:۰۰  جدول نشان می‌دهد انتخاب کنترلر تابع مأموریت است، نه اندازه ماهواره. یک CubeSat کوچک هم "
    "اگر دقت بالا بخواهد، کنترل پیچیده لازم دارد. (~۵۰ ثانیه)",
)

# ================================================================ 5 کنترلرها و پردازنده‌ها
s = slide_new(WHITE)
header(s, 5, "۰۱ \u00b7 مسئله", "از کنترل ساده تا کنترل یادگیری‌محور")

fam = [
    ("ساده و مقاوم", "B-dot \u2192 PD / PID", NAVY, PALE2),
    ("مدل‌محور", "LQR \u2192 کواترنیون \u2192 غیرخطی", BLUE, PALE2),
    ("بهینه‌سازی", "MPC \u2192 Optimal Control", SKY, PALE2),
    ("یادگیری‌محور", "RL \u2192 تطبیقی عصبی \u2192 Safe RL", PURPLE, PURPBG),
]
fw = 2.72
for i, (hd, body, col, bg) in enumerate(fam):
    x = R - (i + 1) * fw - i * 0.2
    rect(
        s,
        x,
        1.86,
        fw,
        1.30,
        fill=bg,
        line=None,
        radius=0.07,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    rect(s, x + fw - 0.05, 1.86, 0.05, 1.30, fill=col)
    txt(
        s,
        x + 0.18,
        2.00,
        fw - 0.36,
        0.3,
        [{"t": hd, "size": 12, "bold": True, "color": col}],
    )
    txt(
        s,
        x + 0.18,
        2.38,
        fw - 0.36,
        0.7,
        [{"t": body, "size": 9.5, "color": GREY, "line": 1.35, "rtl": False}],
    )

txt(
    s,
    7.0,
    3.42,
    R - 7.0,
    0.3,
    [{"t": "پردازنده چه نقشی دارد؟", "size": 14, "bold": True, "color": NAVY}],
)
procs = [
    ("ریزکنترل‌گر MCU", "کنترل و تخمین"),
    ("پردازنده مقاوم به تشعشع", "قابلیت اطمینان بالاتر"),
    ("پردازنده FPGA", "پردازش سریع و قطعی"),
    ("تراشه SoC ناهمگن", "خودمختاری و پردازش سنگین"),
    ("ایستگاه زمینی CPU / GPU", "آموزش و توسعه"),
]
yy = 3.74
for k, v in procs:
    txt(
        s,
        7.0,
        yy,
        R - 7.0,
        0.28,
        [
            {
                "t": [
                    (k, {"bold": True, "color": NAVY}),
                    (" \u2014 " + v, {"color": GREY}),
                ],
                "size": 10.5,
            }
        ],
    )
    yy += 0.30

rect(
    s,
    M,
    3.42,
    5.55,
    1.20,
    fill=AMBBG,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.22,
    3.52,
    5.1,
    0.28,
    [{"t": "جایگاه Raspberry Pi", "size": 11, "bold": True, "color": AMBER}],
)
txt(
    s,
    M + 0.22,
    3.82,
    5.1,
    0.72,
    [
        {
            "t": "در این پژوهش فقط بستر نمونه‌سازی و ارزیابی امکان‌پذیری محاسباتی است \u2014 نه سخت‌افزار پروازی.",
            "size": 10,
            "color": GREY,
            "line": 1.35,
        }
    ],
)

rect(
    s,
    M,
    5.02,
    CW,
    0.84,
    fill=PALE,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.3,
    5.14,
    CW - 0.6,
    0.64,
    [
        {
            "t": [
                ("پرسش:  ", {"bold": True, "color": BLUE}),
                (
                    "اگر الگوریتم روی GPU زمینی خوب کار کند، روی سخت‌افزار محدود و پرتاب‌شده هم قابل اجرا و "
                    "قابل اتکا خواهد بود؟",
                    {"color": INK},
                ),
            ],
            "size": 11.5,
            "line": 1.4,
        }
    ],
)

txt(
    s,
    M,
    5.96,
    CW,
    0.36,
    [
        {
            "t": "کنترلر باید به اندازه‌ای پیشرفته باشد که مأموریت می‌خواهد؛ نه به اندازه‌ای که از نظر تئوری ممکن است.",
            "size": 11.5,
            "color": NAVY,
            "bold": True,
        }
    ],
)
footer(s, 5)
animate(s, [[s.shapes[-2]]])
transition(s)
notes(
    s,
    "۳:۰۰  چهار خانواده کنترلر، از B-dot تا یادگیری تقویتی. تفسیر من از پردازنده و Raspberry Pi هم "
    "مهم است: RPi فقط بستر نمونه‌سازی است. سؤال کلیدی: اجراپذیری روی سخت‌افزار محدود. (~۵۰ ثانیه)",
)

# ================================================================ 6 حسگرها
s = slide_new(WHITE)
header(s, 6, "۰۱ \u00b7 مسئله", "حسگرهای لازم برای کنترل وضعیت")

sens = [
    ("ژیروسکوپ / IMU", "نرخ زاویه‌ای", "انتشار سریع وضعیت"),
    ("مغناطیس‌سنج", "میدان مغناطیسی زمین", "مرجع وضعیت"),
    ("حسگر خورشید", "جهت خورشید", "حالت امن و تخمین اولیه"),
    ("ستاره‌یاب", "وضعیت مطلق دقیق", "تعیین دقیق وضعیت"),
    ("GPS / GNSS", "موقعیت و زمان", "اطلاعات مدار"),
    ("حسگر افق", "جهت زمین", "مأموریت زمین‌نگر"),
    ("دوربین / حسگر نوری", "جهت نسبی هدف", "ردیابی و نزدیک‌شدن"),
]
tx, ty = 5.55, 1.86
colw = [2.55, 2.45, 2.28]
rect(s, tx, ty, sum(colw), 0.44, fill=NAVY, line=None)
heads = ["حسگر", "اطلاعات اصلی", "کاربرد"]
cx = tx + sum(colw)
for cw_, ht in zip(colw, heads):
    cx -= cw_
    txt(
        s,
        cx + 0.14,
        ty + 0.10,
        cw_ - 0.2,
        0.26,
        [{"t": ht, "size": 10, "bold": True, "color": WHITE}],
    )
for i, row in enumerate(sens):
    ry = ty + 0.44 + i * 0.50
    if i % 2 == 0:
        rect(s, tx, ry, sum(colw), 0.50, fill=PALE2, line=None)
    cx = tx + sum(colw)
    for j, (cw_, val) in enumerate(zip(colw, row)):
        cx -= cw_
        txt(
            s,
            cx + 0.14,
            ry + 0.13,
            cw_ - 0.2,
            0.3,
            [
                {
                    "t": val,
                    "size": 9.5,
                    "color": NAVY if j == 0 else (GREY if j == 1 else BLUE),
                    "bold": j == 0,
                    "rtl": is_fa(val),
                }
            ],
        )
line_h(s, tx, ty + 0.44 + len(sens) * 0.50, sum(colw), LINE)

txt(
    s,
    M,
    1.86,
    4.3,
    0.32,
    [{"t": "هیچ حسگری به‌تنهایی کافی نیست", "size": 13, "bold": True, "color": NAVY}],
)
txt(
    s,
    M,
    2.24,
    4.35,
    2.0,
    [
        {
            "t": [
                ("ژیروسکوپ", {"bold": True, "color": BLUE}),
                (" سریع است، ولی Drift دارد.", {}),
            ],
            "size": 10,
            "color": GREY,
            "line": 1.35,
            "sp_after": 6,
        },
        {
            "t": [
                ("مغناطیس‌سنج و حسگر خورشید", {"bold": True, "color": BLUE}),
                (" مرجع می‌دهند، ولی دقت محدودی دارند.", {}),
            ],
            "size": 10,
            "color": GREY,
            "line": 1.35,
            "sp_after": 6,
        },
        {
            "t": [
                ("ستاره‌یاب", {"bold": True, "color": BLUE}),
                (" دقیق است، ولی پیچیده و همیشه در دسترس نیست.", {}),
            ],
            "size": 10,
            "color": GREY,
            "line": 1.35,
        },
    ],
)
rect(
    s,
    M,
    4.42,
    4.35,
    0.9,
    fill=PALE,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.2,
    4.54,
    3.95,
    0.72,
    [
        {
            "t": "در نتیجه، تعیین وضعیت ذاتاً یک مسئله Sensor Fusion است.",
            "size": 10.5,
            "bold": True,
            "color": NAVY,
            "line": 1.4,
        }
    ],
)
footer(s, 6)
transition(s)
notes(
    s,
    "۴:۰۰  هیچ حسگری تنها کافی نیست: ژیرو سریع اما Drift دارد، مراجع مطلق کم‌دقت‌اند، ستاره‌یاب دقیق "
    "اما همیشه در دسترس نیست. پس تعیین وضعیت یک مسئله ادغام حسگر است. (~۵۰ ثانیه)",
)

# ================================================================ 7 موضوع پژوهش
s = slide_new(WHITE)
header(s, 7, "۰۲ \u00b7 پژوهش من", "چرا تحمل‌پذیری خطا با یادگیری تقویتی؟")

txt(
    s,
    6.35,
    1.86,
    R - 6.35,
    0.85,
    [
        {
            "t": "سامانه ADCS به حسگرها، عملگرها، مدل دینامیکی و کنترلر وابسته است. در سیستم واقعی نمی‌توان همیشه "
            "فرض کرد همه‌چیز دقیقاً مطابق طراحی اولیه کار می‌کند.",
            "size": 11,
            "color": GREY,
            "line": 1.5,
        }
    ],
)

rect(
    s,
    9.55,
    2.80,
    R - 9.55,
    2.24,
    fill=REDBG,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    9.72,
    2.90,
    R - 9.9,
    0.3,
    [{"t": "خطاهای حسگر", "size": 11, "bold": True, "color": RED}],
)
txt(
    s,
    9.72,
    3.22,
    R - 9.9,
    1.7,
    [
        {
            "t": v,
            "size": 9.5,
            "color": GREY,
            "bullet": True,
            "bucolor": RED,
            "sp_after": 4,
            "line": 1.3,
        }
        for v in ["بایاس (Bias)", "قطع سیگنال", "خطای اندازه‌گیری", "افزایش نویز"]
    ],
)

rect(
    s,
    6.35,
    2.80,
    3.05,
    2.24,
    fill=AMBBG,
    line=None,
    radius=0.06,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    6.52,
    2.90,
    2.7,
    0.3,
    [{"t": "خطاهای عملگر", "size": 11, "bold": True, "color": AMBER}],
)
txt(
    s,
    6.52,
    3.22,
    2.72,
    1.7,
    [
        {
            "t": v,
            "size": 9.5,
            "color": GREY,
            "bullet": True,
            "bucolor": AMBER,
            "sp_after": 4,
            "line": 1.3,
        }
        for v in ["کاهش کارایی", "گشتاور ناخواسته", "افت چرخ واکنشی", "قفل شدن عملگر"]
    ],
)

chain = ["ماهواره سالم", "وقوع خطا", "کاهش قابلیت کنترل", "تطبیق کنترلر", "حفظ عملکرد"]
cy = 1.90
for i, c in enumerate(chain):
    col = [GREEN, RED, AMBER, PURPLE, GREEN][i]
    bg = [GREENBG, REDBG, AMBBG, PURPBG, GREENBG][i]
    rect(
        s,
        M,
        cy,
        4.85,
        0.56,
        fill=bg,
        line=None,
        radius=0.1,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M + 0.2,
        cy + 0.12,
        4.4,
        0.32,
        [{"t": c, "size": 10, "bold": True, "color": col}],
    )
    if i < 4:
        arrow(s, M + 2.42, cy + 0.58, M + 2.42, cy + 0.70, SKY, 1.0)
    cy += 0.72

txt(
    s,
    M,
    6.42,
    4.9,
    0.28,
    [
        {
            "t": "\u03c4applied = h \u00b7 \u03c4cmd ,    h \u2208 [0, 1]",
            "size": 9,
            "color": GREYL,
            "italic": True,
            "rtl": False,
            "align": PP_ALIGN.LEFT,
            "font": EN,
        }
    ],
)

rect(
    s,
    M,
    5.46,
    CW,
    0.80,
    fill=NAVY,
    line=None,
    radius=0.05,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.35,
    5.56,
    CW - 0.7,
    0.60,
    [
        {
            "t": "آیا یادگیری تقویتی می‌تواند یک کنترلر وضعیت تطبیقی و خطاپذیر بسازد، بی‌آنکه عملکرد وضعیت "
            "غیرقابل‌اعتماد شود؟",
            "size": 12,
            "bold": True,
            "color": WHITE,
            "line": 1.35,
        }
    ],
)
animate(s, [[s.shapes[-2]]])
transition(s)
notes(
    s,
    "۴:۵۰  خطاها دو دسته‌اند: حسگر و عملگر. وقتی خطا رخ می‌دهد، قابلیت کنترل تغییر می‌کند. پرسش من "
    "این است که آیا یادگیری می‌تواند این تغییر را جبران کند. (~۵۰ ثانیه)",
)

# ================================================================ 8 معماری
s = slide_new(WHITE)
header(s, 8, "۰۲ \u00b7 پژوهش من", "یک کنترلر، سه تضمین")

txt(
    s,
    6.55,
    1.86,
    R - 6.55,
    1.3,
    [
        {
            "t": [
                ("هدف.  ", {"bold": True, "color": NAVY}),
                (
                    "رساندن ماهواره از وضعیت و نرخ اولیه تصادفی به نشانه‌روی به سمت زمین \u2014 یعنی حالت Nadir \u2014 "
                    "سریع و دقیق، و حفظ همین عملکرد وقتی چرخ واکنشی افت می‌کند یا از کار می‌افتد.",
                    {},
                ),
            ],
            "size": 11,
            "color": GREY,
            "line": 1.45,
        }
    ],
)

principles = [
    (
        "۱",
        "یاد بگیرد",
        "آموزش با PPO / SAC روی پلنت غیرخطی با اینرسی، اغتشاش و نویز تصادفی.",
    ),
    ("۲", "سلامت را فرض نکند", "سیاست فقط تخمین ĥ را می‌بیند، نه سلامت واقعی h."),
    (
        "۳",
        "ایمن شکست بخورد",
        "گاورنر فیزیکی و بازگشت به LQR \u2014 نه یک شبکه عصبی دوم.",
    ),
]
yy = 3.34
for num, hd, bd in principles:
    rect(s, R - 0.36, yy + 0.02, 0.34, 0.34, fill=PALE, line=None, shape=MSO_SHAPE.OVAL)
    txt(
        s,
        R - 0.36,
        yy + 0.05,
        0.34,
        0.3,
        [
            {
                "t": num,
                "size": 10.5,
                "bold": True,
                "color": BLUE,
                "align": PP_ALIGN.CENTER,
            }
        ],
    )
    txt(
        s,
        6.55,
        yy - 0.04,
        R - 6.55 - 0.48,
        0.3,
        [{"t": hd, "size": 12, "bold": True, "color": NAVY}],
    )
    txt(
        s,
        6.55,
        yy + 0.27,
        R - 6.55 - 0.48,
        0.6,
        [{"t": bd, "size": 9.5, "color": GREY, "line": 1.35}],
    )
    yy += 0.90

AX, AY, AW, AH, AG = 0.95, 1.92, 3.55, 0.62, 0.30
arch = [
    ("حسگرها و تخمین‌گر", "وضعیت، نرخ و تخمین سلامت", WHITE, LINE, NAVY),
    ("سیاست یادگیری تقویتی", "گشتاور مطلوب بدنه", PURPBG, PURPLE, PURPLE),
    ("گاورنر ایمنی", "بررسی فیزیکی فرمان", AMBBG, RGBColor(0xE8, 0xD3, 0xA6), AMBER),
    ("تخصیص‌گر خطاپذیر", "بازتوزیع گشتاور", PALE, None, NAVY),
    ("۳ چرخ واکنشی + ۳ گشتاورساز", "عملگرها", WHITE, LINE, NAVY),
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
    tf.margin_left = tf.margin_right = In(0.05)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p._p.get_or_add_pPr().set("rtl", "1")
    r = p.add_run()
    r.text = l1
    r.font.name = FA
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = col
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2._p.get_or_add_pPr().set("rtl", "1")
    r2 = p2.add_run()
    r2.text = l2
    r2.font.name = FA
    r2.font.size = Pt(7.5)
    r2.font.color.rgb = GREYL
    arch_boxes.append(b)
    if i < 4:
        arrow(s, AX + AW / 2, y + AH + 0.02, AX + AW / 2, y + AH + AG - 0.02, SKY, 1.2)

y_last = AY + 4 * (AH + AG)
rx = AX + AW + 0.30
arrow(s, AX + AW, y_last + AH / 2, rx, y_last + AH / 2, SKY, 1.0, head=False)
arrow(s, rx, y_last + AH / 2, rx, AY + AH / 2, SKY, 1.0, head=False)
arrow(s, rx, AY + AH / 2, AX + AW + 0.02, AY + AH / 2, SKY, 1.0)
txt(s, rx + 0.02, 3.24, 0.62, 0.44, [{"t": "وضعیت", "size": 6.5, "color": GREYL}])

animate(s, [[arch_boxes[i]] for i in range(5)])
transition(s)
notes(
    s,
    "۵:۴۰  این معماری پیشنهادی است: سیاست فقط گشتاور مطلوب می‌دهد، گاورنر فیزیکی می‌تواند وتو کند و "
    "به LQR برگردد، تخصیص‌گر گشتاور را روی چرخ‌های سالم و مغناطیسی‌ها پخش می‌کند. (~۵۰ ثانیه)",
)

# ================================================================ 9 سه مقاله
s = slide_new(WHITE)
header(s, 9, "۰۳ \u00b7 پژوهش‌های مرتبط", "سه مقاله، سه پاسخ مکمل")

cards = [
    (
        "مقاله اول",
        "Yang, Jin & Rao",
        "2025",
        "Journal of the Franklin Institute",
        "یادگیری آنلاین وقتی مدل ماهواره ناشناخته است و عملگر خراب می‌شود.",
        "تطبیق‌پذیری",
        PURPLE,
        PURPBG,
    ),
    (
        "مقاله دوم",
        "Lu et al.",
        "2026",
        "Aerospace Science and Technology",
        "یادگیری ایمن، ردیابی چابک را داخل محدودیت‌ها و با خطای عملگر نگه می‌دارد.",
        "ایمنی",
        AMBER,
        AMBBG,
    ),
    (
        "مقاله سوم",
        "Nagano & Schaub",
        "2025",
        "AAS 25-637",
        "آموزش آگاه از خطا، زمان‌بندی مأموریت را پس از خرابی چرخ مقاوم نگه می‌دارد.",
        "تاب‌آوری",
        GREEN,
        GREENBG,
    ),
]
cw_, gap = 3.62, 0.28
card_shapes = []
for i, (tag, auth, year, venue, idea, key, col, bg) in enumerate(cards):
    cx = R - (i + 1) * cw_ - i * gap
    c = rect(
        s,
        cx,
        1.88,
        cw_,
        3.60,
        fill=WHITE,
        line=LINE,
        radius=0.05,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        soft=True,
    )
    rect(s, cx, 1.88, cw_, 0.1, fill=col, line=None)
    txt(
        s,
        cx + 0.26,
        2.14,
        cw_ - 0.52,
        0.26,
        [{"t": tag, "size": 9, "bold": True, "color": col}],
    )
    txt(
        s,
        cx + 0.26,
        2.40,
        cw_ - 0.52,
        0.45,
        [
            {
                "t": auth,
                "size": 13,
                "bold": True,
                "color": NAVY,
                "font": EN,
                "rtl": False,
                "align": PP_ALIGN.RIGHT,
                "line": 1.1,
            }
        ],
    )
    txt(
        s,
        cx + 0.26,
        2.88,
        cw_ - 0.52,
        0.5,
        [
            {
                "t": f"{venue}, {year}",
                "size": 8.5,
                "color": GREYL,
                "font": EN,
                "rtl": False,
                "align": PP_ALIGN.RIGHT,
                "line": 1.15,
            }
        ],
    )
    line_h(s, cx + 0.26, 3.46, cw_ - 0.52, LINE)
    txt(
        s,
        cx + 0.26,
        3.60,
        cw_ - 0.52,
        1.15,
        [{"t": idea, "size": 10.5, "color": INK, "line": 1.5}],
    )
    chip(
        s,
        cx + cw_ - 1.9,
        4.78,
        1.66,
        0.42,
        key,
        fill=bg,
        color=col,
        size=10,
        radius=0.3,
    )
    card_shapes.append(c)

txt(
    s,
    M,
    5.80,
    CW,
    0.45,
    [
        {
            "t": [
                ("پرسش مشترک:  ", {"bold": True, "color": NAVY}),
                (
                    "اگر ماهواره دقیقاً مطابق مدل و شرایطی که برای آن آموزش دیده رفتار نکند، سیستم یادگیری‌محور "
                    "چگونه باید قابل اتکا بماند؟",
                    {"italic": True},
                ),
            ],
            "size": 11,
            "color": GREY,
            "line": 1.4,
        }
    ],
)
footer(s, 9)
animate(s, [[card_shapes[0]], [card_shapes[1]], [card_shapes[2]]])
footnote(
    s,
    "[1] Yang, Jin & Rao \u2014 J. Franklin Inst. 362 (2025)   \u00b7   "
    "[2] Lu et al. \u2014 Aerosp. Sci. Technol. 168 (2026)   \u00b7   "
    "[3] Nagano & Schaub \u2014 AAS 25-637 (2025)",
    y=6.38,
    align=PP_ALIGN.LEFT,
)
transition(s)
notes(s, "۶:۲۰  سه مقاله، هر کدام یک بُعد: تطبیق‌پذیری، ایمنی، تاب‌آوری. (~۳۰ ثانیه)")


# ================================================================ 10-12 مقاله‌ها
def paper_slide(
    num,
    tag,
    ttl_en,
    problem,
    method,
    idea,
    opens,
    relevance,
    citation,
    accent=PURPLE,
    bg=PURPBG,
):
    s = slide_new(WHITE)
    kicker(s, "۰۳ \u00b7 پژوهش‌های مرتبط   |   " + tag, accent)
    txt(
        s,
        M,
        0.72,
        CW,
        0.6,
        [
            {
                "t": ttl_en,
                "size": 12,
                "bold": True,
                "color": NAVY,
                "font": EN,
                "rtl": False,
                "align": PP_ALIGN.RIGHT,
                "line": 1.15,
            }
        ],
    )
    line_h(s, M, 1.62, CW, LINE)

    txt(
        s,
        6.5,
        1.84,
        R - 6.5,
        0.26,
        [{"t": "مسئله", "size": 9.5, "bold": True, "color": accent}],
    )
    txt(
        s,
        6.5,
        2.10,
        R - 6.5,
        0.95,
        [{"t": problem, "size": 11, "color": INK, "line": 1.45}],
    )

    txt(
        s,
        6.5,
        3.14,
        R - 6.5,
        0.26,
        [{"t": "روش", "size": 9.5, "bold": True, "color": accent}],
    )
    meth = [
        {
            "t": m,
            "size": 10,
            "color": GREY,
            "bullet": True,
            "bucolor": accent,
            "sp_after": 6,
            "line": 1.35,
        }
        for m in method
    ]
    txt(s, 6.5, 3.40, R - 6.5, 1.5, meth)

    rect(
        s,
        6.5,
        5.10,
        R - 6.5,
        0.95,
        fill=bg,
        line=None,
        radius=0.06,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        6.7,
        5.22,
        R - 6.9,
        0.75,
        [{"t": idea, "size": 10, "color": accent, "bold": True, "line": 1.4}],
    )

    rect(
        s,
        M,
        1.84,
        5.3,
        4.21,
        fill=PALE2,
        line=None,
        radius=0.05,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M + 0.24,
        2.00,
        4.85,
        0.26,
        [{"t": "چه چیزی باز مانده", "size": 9.5, "bold": True, "color": RED}],
    )
    txt(
        s,
        M + 0.24,
        2.28,
        4.85,
        1.85,
        [
            {
                "t": o,
                "size": 9.5,
                "color": GREY,
                "bullet": True,
                "bucolor": RED,
                "sp_after": 6,
                "line": 1.35,
            }
            for o in opens
        ],
    )
    line_h(s, M + 0.24, 4.18, 4.8, LINE)
    txt(
        s,
        M + 0.24,
        4.32,
        4.8,
        0.26,
        [{"t": "ارتباط با این پژوهش", "size": 9.5, "bold": True, "color": BLUE}],
    )
    txt(
        s,
        M + 0.24,
        4.60,
        4.85,
        1.2,
        [{"t": relevance, "size": 9.5, "color": INK, "italic": True, "line": 1.45}],
    )
    footnote(s, citation, y=6.42, align=PP_ALIGN.LEFT)
    footer(s, num)
    transition(s)
    return s


s = paper_slide(
    10,
    "مقاله ۱ از ۳",
    "Reinforcement Learning Based Attitude Fault-Tolerant Control of Spacecraft with Unknown System Model",
    "روش‌های کلاسیک تحمل خطا به مدل دقیق دینامیک و رفتار معلوم عملگر وابسته‌اند؛ چیزی که نانوماهواره واقعی "
    "در اختیار نمی‌گذارد.",
    [
        "آفلاین: RL به‌همراه کنترل بهینه یک سیاست اولیه می‌سازد.",
        "آنلاین: مشاهده‌گر عصبی، دینامیک و بهره ورودی ناشناخته را تخمین می‌زند.",
        "به‌روزرسانی Critic با RLS و جبران پیش‌رو خطای افزایشی عملگر.",
    ],
    "سیاست بدون داشتن مدل سیستم، به‌صورت آنلاین خود را با خطای عملگر تطبیق می‌دهد.",
    [
        "شدت‌های خطای دیده‌نشده",
        "خطای حسگر، نه فقط عملگر",
        "ایمنی خودِ خروجی یادگرفته",
        "هزینه اجرای تطبیق روی سخت‌افزار",
    ],
    "نزدیک‌ترین مقاله به مسئله این پایان‌نامه \u2014 و دورترین به ادعای استقرار عملی.",
    "Yang, S., Jin, L. & Rao, J. (2025). Journal of the Franklin Institute, 362, 107741. "
    "doi:10.1016/j.jfranklin.2025.107741",
)
notes(
    s,
    "۶:۵۰  مقاله اول: RL آفلاین به‌همراه مشاهده‌گر عصبی و RLS، پس سیاست وقتی مدل ناشناخته است تطبیق "
    "می‌یابد. قوی در تطبیق، ولی مجموعه خطا همان خطاهای شبیه‌سازی است. (~۵۰ ثانیه)",
)

s = paper_slide(
    11,
    "مقاله ۲ از ۳",
    "Safe Reinforcement Learning Based Agile Satellite Attitude Control for Non-Cooperative Target Tracking "
    "with Operation Constraints and Actuator Faults",
    "ردیابی چابک باید نواحی ممنوعه، محدودیت نرخ و گشتاور را رعایت کند \u2014 در حالی که یک عملگر کارایی "
    "خود را از دست می‌دهد.",
    [
        "شناسایی خطا، کاهش کارایی و خطای افزایشی را تخمین می‌زند.",
        "مسئله به‌صورت یک فرایند تصمیم مارکوف مقید فرمول‌بندی می‌شود.",
        "الگوریتم WCSAC آن را با خطاها داخل مجموعه قیود حل می‌کند.",
    ],
    "تحمل خطا، قیود عملیاتی و ایمنی، هر سه در یک کنترلر یادگیری‌محور.",
    [
        "بار محاسباتی برای هدف نهفته",
        "راستی‌آزمایی ادعای ایمنی",
        "خطاهای بیرون از توزیع آموزش",
        "انتقال از ایستگاه کاری به سخت‌افزار پرواز",
    ],
    "نشان می‌دهد عملکرد بدون قید، نتیجه نیست؛ قیود باید در طراحی باشند.",
    "Lu, W. et al. (2026). Aerospace Science and Technology, 168, 111238. doi:10.1016/j.ast.2025.111238",
    accent=AMBER,
    bg=AMBBG,
)
notes(
    s,
    "۷:۴۰  مقاله دوم از «آیا RL می‌تواند کنترل کند» به «آیا می‌تواند با رعایت قیود کنترل کند» می‌رود: "
    "MDP مقید و WCSAC. این استدلال ایمنی را از آن می‌گیرم. (~۵۰ ثانیه)",
)

s = paper_slide(
    12,
    "مقاله ۳ از ۳",
    "Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling",
    "در سطح مأموریت، خرابی چرخ واکنشی چابکی را کم می‌کند: مانور کمتر، ورود به حالت امن و از دست رفتن فرصت "
    "تصویربرداری.",
    [
        "آموزش با تزریق خطا: سیاست در محیط معیوب آموزش می‌بیند.",
        "اطلاعات خطا به بردار مشاهده اضافه می‌شود.",
        "شبکه بازگشتی از تاریخچه زمانی برای تشخیص الگوی خطا استفاده می‌کند.",
    ],
    "تحمل خطا باید از ابتدا در فرایند یادگیری طراحی شود، نه بعداً اضافه.",
    [
        "یک زمان‌بند است، نه کنترلر وضعیت",
        "بدون استدلال پایداری کنترل پیوسته",
        "شواهد فقط در شبیه‌سازی",
    ],
    "دقیقاً همان تقسیم‌بندی آزمون این پایان‌نامه را توجیه می‌کند: آموزش عادی، آموزش آگاه از خطا، سپس خطای دیده‌نشده.",
    "Nagano, Y. & Schaub, H. (2025). AAS 25-637, Enhancing Fault Resilience in RL-Based Satellite Autonomous "
    "Task Scheduling.",
    accent=GREEN,
    bg=GREENBG,
)
notes(
    s,
    "۸:۳۰  مقاله سوم کنترلر وضعیت نیست؛ زمان‌بندی تصویربرداری است. اما پیامش را می‌پذیرم: تاب‌آوری باید "
    "داخل آموزش باشد. (~۴۵ ثانیه)",
)

# ================================================================ 13 شکاف‌ها
s = slide_new(WHITE)
header(
    s,
    13,
    "۰۴ \u00b7 شکاف و ایده",
    "از RL خطاپذیر به RL قابل اعتماد و قابل استقرار",
    tsize=24,
)

gaps = [
    (
        "خطاهای دیده‌نشده",
        "آموزش روی یک توزیع خطا، عملکرد روی خطاهای جدید را تضمین نمی‌کند.",
        "توزیع آموزش و آزمون جدا: شدت، زمان وقوع و ترکیب خطاها.",
    ),
    (
        "خروجی تأییدنشده",
        "یک شبکه عصبی می‌تواند از ناحیه معتبر خود خارج شود.",
        "گاورنر فیزیکی: فرمان بررسی شود، وگرنه تحویل به LQR.",
    ),
    (
        "تشخیص و کنترل جدا",
        "تخمین سلامت و قانون کنترل مستقل طراحی می‌شوند.",
        "تخمین سلامت ĥ داخل مشاهده \u2014 بدون دسترسی به h واقعی.",
    ),
    (
        "استقرار فرض‌شده",
        "مدلی که روی GPU اجرا می‌شود، کنترلر پروازی نیست.",
        "بودجه تأخیر، کوانتیزه‌سازی و آزمون سخت‌افزار در حلقه.",
    ),
]
yy = 1.84
row_shapes = []
for i, (g, why, idea) in enumerate(gaps):
    txt(s, 6.35, yy, R - 6.75, 0.34, [{"t": g, "size": 12, "bold": True, "color": NAVY}])
    txt(
        s,
        6.35,
        yy + 0.34,
        R - 6.75,
        0.62,
        [{"t": why, "size": 9.5, "color": GREY, "line": 1.35}],
    )

    card = rect(
        s,
        M,
        yy,
        5.15,
        1.04,
        fill=PALE2,
        line=None,
        radius=0.06,
        shape=MSO_SHAPE.ROUNDED_RECTANGLE,
    )
    txt(
        s,
        M + 0.22,
        yy + 0.04,
        4.7,
        0.96,
        [
            {
                "t": idea,
                "size": 10,
                "color": INK,
                "bullet": True,
                "buchar": "\u2190",
                "bucolor": SKY,
                "line": 1.4,
            }
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    row_shapes.append(card)
    yy += 1.16

footer(s, 13)
animate(s, [[rr] for rr in row_shapes])
transition(s)
notes(
    s,
    "۹:۱۰  چهار شکاف: خطای دیده‌نشده آزمون نمی‌شود؛ خروجی شبکه تأیید نمی‌شود؛ تشخیص و کنترل جدا طراحی "
    "می‌شوند؛ و استقرار فرض می‌شود نه اندازه‌گیری. هر شکاف یک تصمیم مشخص در روش من است. (~۵۰ ثانیه)",
)

# ================================================================ 14 جمع‌بندی
s = slide_new(WHITE)
header(s, 14, "۰۵ \u00b7 جمع‌بندی", "پنج نکته \u2014 و یک هدف")

takeaways = [
    ("سامانه ADCS حیاتی است", "ماهواره باید دائماً وضعیت خود را تعیین و کنترل کند."),
    ("پیچیدگی تابع مأموریت است", "پیچیده‌تر بودن همیشه بهتر بودن نیست."),
    ("خطا، محرک طراحی است", "روی نانوماهواره، بقا یک ویژگی نرم‌افزاری است."),
    ("یادگیری تقویتی تطبیق‌پذیری می‌آورد", "و پرسش‌های تازه: تعمیم، ایمنی، هزینه نهفته."),
    ("اما RL به‌تنهایی کافی نیست", "باید تعمیم دهد، ایمن بماند و اجرا شود."),
]
pos = [(M + 5.75, 1.82), (M, 1.82), (M + 5.75, 2.92), (M, 2.92), (M + 5.75, 4.02)]
concl_shapes = []
for i, ((hd, bd), (x, y)) in enumerate(zip(takeaways, pos)):
    bar = rect(s, x + 5.28, y + 0.04, 0.045, 0.76, fill=SKY)
    txt(
        s,
        x,
        y,
        5.2,
        0.32,
        [{"t": fa(i + 1) + ".  " + hd, "size": 12, "bold": True, "color": NAVY}],
    )
    txt(s, x, y + 0.32, 5.2, 0.55, [{"t": bd, "size": 9.5, "color": GREY, "line": 1.3}])
    concl_shapes.append(bar)

rect(
    s,
    M,
    5.00,
    CW,
    1.45,
    fill=NAVY,
    line=None,
    radius=0.05,
    shape=MSO_SHAPE.ROUNDED_RECTANGLE,
)
txt(
    s,
    M + 0.45,
    5.12,
    CW - 0.9,
    0.24,
    [{"t": "هدف", "size": 8.5, "bold": True, "color": RGBColor(0x8C, 0xBC, 0xDF)}],
)
txt(
    s,
    M + 0.45,
    5.40,
    CW - 0.9,
    0.95,
    [
        {
            "t": [
                (
                    "جایگزین کردن کنترلر کلاسیک با یک شبکه نیست \u2014 ",
                    {"color": RGBColor(0xBF, 0xD8, 0xE9)},
                ),
                (
                    "بررسی این است که آیا یادگیری می‌تواند کنترل وضعیت را تطبیقی‌تر و خطاپذیرتر کند، بی‌آنکه ایمنی، "
                    "اطمینان و امکان استقرار قربانی شود.",
                    {"color": WHITE, "bold": True},
                ),
            ],
            "size": 12,
            "line": 1.45,
        }
    ],
)
footer(s, 14)
animate(s, [[c] for c in concl_shapes] + [[s.shapes[-1]]])
transition(s)
notes(
    s,
    "۹:۴۵  پنج نکته: ADCS حیاتی است؛ پیچیدگی تابع مأموریت؛ خطا محرک طراحی؛ RL تطبیق‌پذیری و پرسش "
    "می‌آورد؛ و RL به‌تنهایی کافی نیست. (~۲۵ ثانیه)",
)

# ================================================================ 15 سپاسگزاری
s = slide_new(NAVY)
pic(s, os.path.join(ASSETS, "closing.jpg"), 0, 0, w=W, h=H)
grad(s, 0, 0, W, H, [(0, "071F36", 22), (45, "082239", 62), (100, "071F36", 95)])
txt(
    s,
    3.5,
    2.10,
    R - 3.5,
    0.3,
    [{"t": "سمینار اول", "size": 11, "color": RGBColor(0x9F, 0xC8, 0xE4)}],
)
txt(
    s,
    3.5,
    2.44,
    R - 3.5,
    0.95,
    [{"t": "سپاسگزارم", "size": 38, "bold": True, "color": WHITE}],
)
rect(s, R - 1.1, 3.52, 1.1, 0.045, fill=SKYL)
txt(
    s,
    3.5,
    3.76,
    R - 3.5,
    0.42,
    [{"t": "سؤالات و بحث", "size": 17, "color": RGBColor(0xBF, 0xD8, 0xE9)}],
)
txt(
    s,
    3.5,
    4.60,
    R - 3.5,
    1.2,
    [
        {"t": "پوریا زارعی", "size": 16, "bold": True, "color": WHITE, "sp_after": 4},
        {
            "t": "کارشناسی ارشد مهندسی کنترل  \u00b7  دانشگاه تهران",
            "size": 11.5,
            "color": RGBColor(0xC9, 0xDD, 0xEC),
            "sp_after": 3,
        },
        {
            "t": "استاد راهنما: دکتر محمدجواد یزدان‌پناه",
            "size": 11.5,
            "color": RGBColor(0xC9, 0xDD, 0xEC),
            "sp_after": 3,
        },
        {
            "t": "Pouria.zarei@ut.ac.ir",
            "size": 11,
            "color": RGBColor(0x9F, 0xC8, 0xE4),
            "rtl": False,
            "font": EN,
            "align": PP_ALIGN.RIGHT,
        },
    ],
)
footnote(
    s,
    "تصویر: NASA/JPL-Caltech \u2014 ماهواره NISAR در مدار زمین (طرح هنری)، شماره PIA26285.",
    y=6.72,
    dark=True,
)
footer(s, 15, dark=True)
transition(s)
notes(s, "۱۰:۰۰  سپاسگزارم؛ آماده پرسش‌ها هستم.")

# ================================================================ 16 منابع
s = slide_new(WHITE)
header(s, 16, "پیوست", "منابع")

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
        "Blue Canyon Technologies. Attitude Determination & Control Systems \u2014 XACT / FleXcore.",
    ),
    (
        "7",
        "AAC Clyde Space. iADCS200 \u2014 Integrated Attitude Determination & Control System.",
    ),
]
yy = 1.82
for n, t in refs:
    lines = max(1, -(-len(t) // 118))
    txt(
        s,
        M,
        yy,
        11.4,
        0.18 * lines + 0.1,
        [
            {
                "t": f"[{n}]  " + t,
                "size": 9.5,
                "color": GREY,
                "line": 1.2,
                "font": EN,
                "rtl": False,
                "align": PP_ALIGN.LEFT,
            }
        ],
    )
    yy += 0.155 * lines + 0.24

txt(
    s,
    M,
    yy + 0.05,
    11.4,
    0.6,
    [
        {
            "t": "[۸]  پوریا زارعی (۱۴۰۵). پیشنهاد پایان‌نامه: کنترل وضعیت خطاپذیر نانوماهواره‌ها با یادگیری تقویتی. "
            "دانشگاه تهران.",
            "size": 9.5,
            "color": GREY,
            "line": 1.3,
        }
    ],
)

line_h(s, M, 6.28, CW, LINE)
txt(
    s,
    M,
    6.42,
    5.9,
    0.26,
    [{"t": "اعتبار تصاویر", "size": 8, "bold": True, "color": BLUE}],
)
txt(
    s,
    M,
    6.62,
    7.0,
    0.4,
    [
        {
            "t": "تصاویر ماهواره: NASA / JPL-Caltech، مالکیت عمومی، شماره‌های PIA26285 و PIA22457.",
            "size": 8.5,
            "color": GREYL,
        }
    ],
)
footer(s, 16)
transition(s)
notes(s, "اسلاید پشتیبان \u2014 منابع و اعتبار تصاویر.")

prs.save(OUT)
print("saved", OUT, len(prs.slides._sldIdLst), "slides")
