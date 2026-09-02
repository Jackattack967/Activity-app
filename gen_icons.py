"""Generate the app icons and store artwork.

Run with:  python gen_icons.py
Needs Pillow, which is not a runtime dependency:  pip install pillow

The mark is the app in miniature: a short list of schedule rows with one
showing an open spot in green — the same green "N spots left" badge the
dashboard uses. It reads as a list at large sizes and as a distinctive
shape at 48px, which a clock or generic calendar glyph does not.
"""

from PIL import Image, ImageDraw, ImageFont

BRAND = (37, 99, 235)       # --brand
BRAND_DEEP = (29, 78, 216)  # --brand-dark
WHITE = (255, 255, 255)
GREEN = (34, 197, 94)

SUPERSAMPLE = 4  # draw big, downscale: cheap anti-aliasing


def draw_mark(draw, size, cx, cy, scale=1.0):
    """The schedule-rows mark, centred on (cx, cy)."""
    unit = size * scale

    row_w = unit * 0.46
    row_h = unit * 0.105
    gap = unit * 0.075
    radius = row_h / 2

    dot_r = unit * 0.075
    dot_cx = cx + unit * 0.30

    # Three rows, stacked and centred.
    total_h = row_h * 3 + gap * 2
    top = cy - total_h / 2
    left = cx - unit * 0.34

    for i in range(3):
        y0 = top + i * (row_h + gap)
        # The last row is shorter, so the block doesn't read as a solid square.
        w = row_w if i < 2 else row_w * 0.62
        draw.rounded_rectangle(
            [left, y0, left + w, y0 + row_h], radius=radius, fill=WHITE
        )

    # The open spot: aligned to the first row.
    dot_cy = top + row_h / 2
    draw.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=GREEN,
    )


def make_icon(size, maskable=False, opaque=False):
    """maskable: full-bleed background with the mark inset into the safe zone,
    so Android's circular/squircle crop can't clip it."""
    s = size * SUPERSAMPLE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    if maskable:
        d.rectangle([0, 0, s, s], fill=BRAND)
        scale = 0.62  # keep the mark inside the 80% safe circle
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=BRAND)
        scale = 1.0

    draw_mark(d, s, s / 2, s / 2, scale=scale)

    img = img.resize((size, size), Image.LANCZOS)
    if opaque:
        flat = Image.new("RGB", img.size, BRAND)
        flat.paste(img, mask=img.split()[3])
        return flat
    return img


# Play shows the feature graphic small and often cropped, so the wordmark is
# set large. Any of these is fine; the first one present wins.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def load_font(px):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, px)
        except OSError:
            continue
    return None


def make_feature_graphic(width=1024, height=500):
    """Play store listing banner."""
    s = SUPERSAMPLE
    img = Image.new("RGB", (width * s, height * s), BRAND_DEEP)
    d = ImageDraw.Draw(img)

    # Diagonal wash so it isn't a flat rectangle.
    for i in range(height * s):
        t = i / (height * s)
        d.line(
            [(0, i), (width * s, i)],
            fill=(
                int(BRAND_DEEP[0] + (BRAND[0] - BRAND_DEEP[0]) * t),
                int(BRAND_DEEP[1] + (BRAND[1] - BRAND_DEEP[1]) * t),
                int(BRAND_DEEP[2] + (BRAND[2] - BRAND_DEEP[2]) * t),
            ),
        )

    cy = height * s * 0.5
    draw_mark(d, height * s, width * s * 0.20, cy, scale=0.62)

    title_font = load_font(int(74 * s))
    sub_font = load_font(int(34 * s))
    if title_font is None:
        print("  ! no usable TrueType font found; feature graphic has no text")
        return img.resize((width, height), Image.LANCZOS)

    text_x = width * s * 0.36
    # Two lines, optically centred as a block against the mark.
    d.text((text_x, cy - 40 * s), "Drop-in", font=title_font, fill=WHITE, anchor="ls")
    d.text((text_x, cy + 40 * s), "Schedules", font=title_font, fill=WHITE, anchor="ls")
    d.text(
        (text_x, cy + 98 * s),
        "Skating & swimming, all in one place",
        font=sub_font,
        fill=(203, 218, 250),
        anchor="ls",
    )
    return img.resize((width, height), Image.LANCZOS)


def main() -> None:
    out = "static/icons"
    jobs = [
        (make_icon(192), f"{out}/icon-192.png"),
        (make_icon(512), f"{out}/icon-512.png"),
        (make_icon(512, maskable=True), f"{out}/icon-512-maskable.png"),
        (make_icon(180, opaque=True), f"{out}/apple-touch-icon.png"),
        # Play requires a 512x512 icon for the listing.
        (make_icon(512, opaque=True), f"{out}/play-icon-512.png"),
        (make_feature_graphic(), f"{out}/play-feature-graphic.png"),
    ]
    for img, path in jobs:
        img.save(path)
        print(f"wrote {path}  ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
