"""One-off utility to (re)generate the PWA app icons in static/icons/.

Run with: python gen_icons.py
Only needs Pillow, which isn't a runtime dependency of the app itself
(not listed in requirements.txt) — install it ad hoc if you need to
regenerate icons: pip install pillow
"""

from PIL import Image, ImageDraw

BRAND_BLUE = (37, 99, 235)
WHITE = (255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    corner_radius = int(size * 0.22)
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=corner_radius, fill=BRAND_BLUE
    )

    # Simple clock glyph: circle + two hands, standing in for "schedule".
    center = size / 2
    clock_radius = size * 0.30
    ring_width = max(2, int(size * 0.035))
    draw.ellipse(
        [center - clock_radius, center - clock_radius, center + clock_radius, center + clock_radius],
        outline=WHITE,
        width=ring_width,
    )

    hand_width = max(2, int(size * 0.045))
    # Hour hand (pointing up-right)
    draw.line(
        [center, center, center, center - clock_radius * 0.55],
        fill=WHITE,
        width=hand_width,
    )
    # Minute hand (pointing right)
    draw.line(
        [center, center, center + clock_radius * 0.72, center],
        fill=WHITE,
        width=hand_width,
    )
    draw.ellipse(
        [center - hand_width, center - hand_width, center + hand_width, center + hand_width],
        fill=WHITE,
    )

    return img


def main() -> None:
    out_dir = "static/icons"
    for size, name in [
        (192, "icon-192.png"),
        (512, "icon-512.png"),
        (180, "apple-touch-icon.png"),
    ]:
        icon = draw_icon(size)
        if name == "apple-touch-icon.png":
            # iOS ignores transparency and expects an opaque icon.
            flat = Image.new("RGB", icon.size, BRAND_BLUE)
            flat.paste(icon, mask=icon.split()[3])
            flat.save(f"{out_dir}/{name}")
        else:
            icon.save(f"{out_dir}/{name}")
        print(f"wrote {out_dir}/{name}")


if __name__ == "__main__":
    main()
