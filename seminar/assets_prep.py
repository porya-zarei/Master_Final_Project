# -*- coding: utf-8 -*-
"""Prepare image assets for the Seminar I deck."""

import os
from PIL import Image, ImageDraw, ImageFilter

SRC = os.path.join(os.environ["TEMP"], "imgs")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(DST, exist_ok=True)


def crop_cover(im, ratio):
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio)
    y = (h - nh) // 2
    return im.crop((0, y, w, y + nh))


# 1) Hero: NISAR over Earth, 16:9 full bleed
hero = Image.open(os.path.join(SRC, "PIA26285.jpg")).convert("RGB")
hero = crop_cover(hero, 16 / 9).resize((2400, 1350), Image.LANCZOS)
hero.save(os.path.join(DST, "hero.jpg"), quality=92)

# 2) Closing: same scene, mirrored + darkened for the thank-you slide
close = Image.open(os.path.join(DST, "hero.jpg")).transpose(Image.FLIP_LEFT_RIGHT)
close = close.filter(ImageFilter.GaussianBlur(0.6))
px = close.load()
dark = Image.new("RGB", close.size, (10, 28, 48))
close = Image.blend(close, dark, 0.35)
close.save(os.path.join(DST, "closing.jpg"), quality=90)

# 3) Earth disc (Blue Marble) with alpha
earth = Image.open(os.path.join(SRC, "GSFC_20171208_Archive_e001386.jpg")).convert(
    "RGB"
)
earth = crop_cover(earth, 1.0).resize((1200, 1200), Image.LANCZOS)
mask = Image.new("L", (1200, 1200), 0)
ImageDraw.Draw(mask).ellipse((6, 6, 1194, 1194), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(1.2))
earth.putalpha(mask)
earth.save(os.path.join(DST, "earth.png"))

# 4) CubeSat (RainCube 6U) on its native white background
sat = Image.open(os.path.join(SRC, "PIA22457.jpg")).convert("RGB")
sat = crop_cover(sat, 1684 / 1920)
sat = sat.resize((1100, 1254), Image.LANCZOS)
sat.save(os.path.join(DST, "cubesat.jpg"), quality=94)

# 5) Reaction-wheel hardware (Europa Clipper) cropped to the wheel face
rw = Image.open(os.path.join(SRC, "PIA25494.jpg")).convert("RGB")
rw = crop_cover(rw, 16 / 10).resize((1400, 875), Image.LANCZOS)
rw.save(os.path.join(DST, "reaction_wheel.jpg"), quality=92)

print("assets ready:", sorted(os.listdir(DST)))
for f in sorted(os.listdir(DST)):
    print(f, Image.open(os.path.join(DST, f)).size)
