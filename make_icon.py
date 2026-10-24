# -*- coding: utf-8 -*-
"""Icoon voor DraveOnion. Gebruikt het Dravenlock-draaklogo (assets/logo.png).
Valt terug op een getekende ui/onion als het logo ontbreekt -> geldig ICO."""
import os
from PIL import Image, ImageDraw

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS, exist_ok=True)
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def from_logo():
    """Bouw het icoon uit het draaklogo als dat aanwezig is."""
    for n in ("logo.png", "logo_t.png"):
        p = os.path.join(ASSETS, n)
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2,
                          (w - s) // 2 + s, (h - s) // 2 + s))
            return im.resize((256, 256), Image.LANCZOS)
    return None


def draw(sz):
    k = sz / 256.0
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, sz - 1, sz - 1], int(46 * k),
                        fill=(26, 20, 38, 255), outline=(150, 120, 210, 255),
                        width=int(6 * k))
    cx, cy = int(128 * k), int(140 * k)
    d.ellipse([cx - int(64 * k), cy - int(60 * k), cx + int(64 * k),
               cy + int(70 * k)], fill=(150, 90, 210, 255))
    for r in (44, 26):
        rr = int(r * k)
        d.arc([cx - rr, cy - int((r + 14) * k), cx + rr, cy + int((r + 10) * k)],
              200, 340, fill=(210, 180, 245, 255), width=int(5 * k))
    d.line([(cx, int(82 * k)), (cx - int(14 * k), int(58 * k))],
           fill=(120, 200, 120, 255), width=int(7 * k))
    d.line([(cx, int(82 * k)), (cx + int(16 * k), int(60 * k))],
           fill=(120, 200, 120, 255), width=int(7 * k))
    return im


base = from_logo()
if base is not None:
    base.save(os.path.join(ASSETS, "icon-256.png"))
    base.resize((64, 64), Image.LANCZOS).save(
        os.path.join(ASSETS, "icon-64.png"))
    base.save(os.path.join(ASSETS, "icon.ico"), format="ICO", sizes=SIZES)
    print("icons done (uit logo)")
else:
    for n in (256, 64):
        draw(n).save(os.path.join(ASSETS, "icon-%d.png" % n))
    draw(256).save(os.path.join(ASSETS, "icon.ico"), format="ICO", sizes=SIZES)
    print("icons done (getekend)")
