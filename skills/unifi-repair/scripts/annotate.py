# /// script
# dependencies = ["pillow"]
# ///
"""Annotate a real board photo, or cut a coordinate-grid crop to find where to annotate.

  uv run annotate.py grid  PHOTO OUT.png [X0 Y0 X1 Y1] [--step N]
  uv run annotate.py draw  PHOTO SPEC.json OUT.jpg
  uv run annotate.py --selftest

All coordinates are ORIGINAL-photo pixels. Grid labels are printed in original pixels,
so numbers read off a grid crop go straight into the spec, however the viewer scaled it.

SPEC.json:
{
  "title": "TOP SIDE - U16 rail",                 # optional, top-left
  "crop": [x0, y0, x1, y1],                        # optional, crop the output to this region
  "zoom": 1.5,                                     # optional, enlarge the (cropped) output
  "marks": [
    {"at": [x, y], "r": 30, "label": "1  C123 +  (inject here)", "color": "red",
     "label_at": [x, y]},                          # ring; label_at optional (auto-placed if absent)
    {"box": [x0, y0, x1, y1], "label": "2  Q17: G-S, D-S", "color": "yellow"}
  ],
  "notes": ["green = pad A, red = pad B", "A = end toward the 'F50' silkscreen"]   # optional, bottom-left
}
Colors: red yellow cyan magenta white green grey, or any "#rrggbb".
"""
import json
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

COLORS = {"red": "#ff2a2a", "yellow": "#ffd400", "cyan": "#00e5ff", "magenta": "#ff4dff",
          "white": "#ffffff", "green": "#5dff5d", "grey": "#9a9a9a"}
FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, int(size))
        except OSError:
            pass
    return ImageFont.load_default()


def grid(src, out, region=None, step=None):
    im = Image.open(src).convert("RGB")
    x0, y0, x1, y1 = region or (0, 0, im.width, im.height)
    crop = im.crop((x0, y0, x1, y1))
    scale = max(1, round(1400 / max(crop.size)))          # upscale small crops so pins are visible
    crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
    step = step or max(10, round(max(x1 - x0, y1 - y0) / 12 / 10) * 10)
    d, f = ImageDraw.Draw(crop), font(18)
    for x in range(x0 - x0 % step + step, x1, step):
        px = (x - x0) * scale
        d.line((px, 0, px, crop.height), fill="#ff2a2a", width=1)
        d.rectangle((px + 2, 2, px + 2 + d.textlength(str(x), font=f) + 4, 22), fill="black")
        d.text((px + 4, 2), str(x), fill="#ffd400", font=f)
    for y in range(y0 - y0 % step + step, y1, step):
        py = (y - y0) * scale
        d.line((0, py, crop.width, py), fill="#ff2a2a", width=1)
        d.rectangle((2, py + 2, 2 + d.textlength(str(y), font=f) + 4, py + 22), fill="black")
        d.text((4, py + 2), str(y), fill="#ffd400", font=f)
    crop.save(out)
    print(f"{out}: region {x0},{y0}-{x1},{y1} step {step}px, shown at {scale}x (photo is {im.width}x{im.height})")


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def draw(src, spec, out):
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    fx0, fy0, fx1, fy1 = spec.get("crop", (0, 0, im.width, im.height))   # output frame, in photo pixels
    u = max(fx1 - fx0, fy1 - fy0) / 1200                   # text and line sizes follow the output frame
    f, big, pad = font(30 * u), font(40 * u), round(7 * u)
    taken = []                                             # mark + label boxes, to keep labels off them
    marks = spec.get("marks", [])
    for m in marks:                                        # shapes first, so labels can avoid all of them
        col = COLORS.get(m.get("color", "yellow"), m.get("color", "yellow"))
        if "box" in m:
            m["_bb"] = tuple(m["box"])
            d.rectangle(m["_bb"], outline=col, width=round(6 * u))
        else:
            x, y = m["at"]
            r = m.get("r", 30 * u)
            m["_bb"] = (x - r, y - r, x + r, y + r)
            d.ellipse(m["_bb"], outline=col, width=round(6 * u))
        m["_col"] = col
        taken.append(m["_bb"])
    for m in marks:
        if not m.get("label"):
            continue
        bb, col = m["_bb"], m["_col"]
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        tw, th = d.textbbox((0, 0), m["label"], font=f)[2:]
        if "label_at" in m:
            spots = [tuple(m["label_at"])]
        else:                                              # try right, left, below, above, then further out
            g = 40 * u
            spots = [(bb[2] + k * g, cy - th / 2) for k in (1, 3)] + [(bb[0] - k * g - tw, cy - th / 2) for k in (1, 3)] \
                + [(cx - tw / 2, bb[3] + k * g) for k in (1, 3)] + [(cx - tw / 2, bb[1] - k * g - th) for k in (1, 3)]
        for lx, ly in spots:
            lb = (lx - pad, ly - pad, lx + tw + pad, ly + th + pad)
            inside = lb[0] >= fx0 and lb[1] >= fy0 and lb[2] <= fx1 and lb[3] <= fy1
            if inside and not any(overlaps(lb, t) for t in taken):
                break
        else:
            lx, ly = spots[0]
            lb = (lx - pad, ly - pad, lx + tw + pad, ly + th + pad)
            print(f"WARNING: label {m['label']!r} overlaps something; set label_at", file=sys.stderr)
        # leader: nearest point on the label box -> nearest point on the mark's edge (never through the part)
        ax, ay = min(max(cx, lb[0]), lb[2]), min(max(cy, lb[1]), lb[3])
        ex, ey = min(max(ax, bb[0]), bb[2]), min(max(ay, bb[1]), bb[3])
        d.line((ax, ay, ex, ey), fill=col, width=round(4 * u))
        d.rectangle(lb, fill="black")
        d.text((lx, ly), m["label"], fill=col, font=f)
        taken.append(lb)
    if "crop" in spec:
        im = im.crop(tuple(spec["crop"]))
    if spec.get("zoom", 1) != 1:
        im = im.resize((round(im.width * spec["zoom"]), round(im.height * spec["zoom"])), Image.LANCZOS)
    d = ImageDraw.Draw(im)                                 # title and notes go on the final frame
    def boxed(xy, text, col, fnt):
        b = d.textbbox(xy, text, font=fnt)
        d.rectangle((b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad), fill="black")
        d.text(xy, text, fill=col, font=fnt)
    if spec.get("title"):
        boxed((20 * u, 20 * u), spec["title"], COLORS["yellow"], big)
    z = spec.get("zoom", 1)
    f, big, pad = font(30 * u * z), font(40 * u * z), round(7 * u * z)
    u *= z
    wrap = max(20, int((im.width - 40 * u) / (f.getlength("n") or 1)))
    notes = [line for n in spec.get("notes", []) for line in textwrap.wrap(n, wrap)]
    for i, n in enumerate(notes):
        boxed((20 * u, im.height - (len(notes) - i) * 46 * u - 10 * u), n, COLORS["white"], f)
    im.save(out, quality=90)
    print(f"{out}: {im.width}x{im.height}, {len(marks)} marks")


def selftest():
    import os, tempfile
    t = tempfile.mkdtemp()
    src = os.path.join(t, "s.jpg")
    Image.new("RGB", (2000, 1500), "#225533").save(src)
    grid(src, os.path.join(t, "g.png"), (400, 300, 900, 700))
    draw(src, {"title": "t", "notes": ["n"], "marks": [
        {"at": [500, 500], "r": 30, "label": "1 ring"}, {"box": [900, 400, 1100, 600], "label": "2 box", "color": "red"}]},
        os.path.join(t, "o.jpg"))
    px = Image.open(os.path.join(t, "o.jpg")).getpixel((500 - 30, 500))    # left edge of the ring
    assert px[0] > 180 and px[2] < 120, px                                 # yellow ring drawn where asked
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]:
        selftest()
    elif a[:1] == ["grid"] and len(a) >= 3:
        step = int(a[a.index("--step") + 1]) if "--step" in a else None
        nums = [int(v) for v in a[3:7]] if len(a) >= 7 and a[3].isdigit() else None
        grid(a[1], a[2], nums, step)
    elif a[:1] == ["draw"] and len(a) == 4:
        draw(a[1], json.load(open(a[2])), a[3])
    else:
        sys.exit(__doc__)
