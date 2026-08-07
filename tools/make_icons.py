"""Generate the PWA PNG icons without any image library.

Run:  python tools/make_icons.py
Writes app/static/icons/icon-192.png, icon-512.png, icon-maskable-512.png.
The vector source of truth is app/static/icons/icon.svg — this script draws the
same mark (blue rounded tile, gold alarm bell, white signal arcs) with plain
maths so the repo has no image dependency.

The hexes are Esicia's, shared with the Android app: blue #0F5C92, gold #CCAE3A.
"""

import math
import os
import struct
import zlib

OUT_DIR = os.path.join("app", "static", "icons")

BG_OUTER = (15, 92, 146)  # #0F5C92 brand blue
BG_INNER = (18, 106, 168)  # a touch lighter, for the diagonal sheen
BELL_TOP = (219, 191, 79)
BELL_BOTTOM = (198, 168, 56)  # #C6A838 gold dark
ACCENT = (255, 255, 255)
LIGHT = (232, 209, 122)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blend(dst, src, alpha):
    return tuple(round(dst[i] * (1 - alpha) + src[i] * alpha) for i in range(3))


def coverage(distance, feather=1.2):
    """Anti-aliased coverage from a signed distance (negative = inside)."""
    if distance <= -feather:
        return 1.0
    if distance >= feather:
        return 0.0
    return (feather - distance) / (2 * feather)


def rounded_rect_distance(x, y, left, top, right, bottom, radius):
    cx = max(left + radius, min(x, right - radius))
    cy = max(top + radius, min(y, bottom - radius))
    inside_x = left <= x <= right
    inside_y = top <= y <= bottom
    dx, dy = x - cx, y - cy
    corner = math.hypot(dx, dy) - radius
    if inside_x and inside_y:
        edge = -min(x - left, right - x, y - top, bottom - y)
        return max(edge, corner) if (dx or dy) else edge
    return corner


def draw(size, padding_ratio=0.0):
    """Return a size×size list of RGB rows.

    padding_ratio > 0 shrinks the artwork for the maskable icon so Android can
    crop it to a circle without clipping the bell.
    """
    pixels = [[BG_OUTER] * size for _ in range(size)]
    s = size / 512.0
    inset = size * padding_ratio

    art_size = size - 2 * inset
    def sx(v):  # scale an SVG-space coordinate into the padded artwork
        return inset + v * (art_size / 512.0)

    radius = 112 * s

    for py in range(size):
        for px in range(size):
            x, y = px + 0.5, py + 0.5

            # Background tile with a soft diagonal gradient.
            distance = rounded_rect_distance(x, y, 0, 0, size, size, radius)
            tile_alpha = coverage(distance)
            if tile_alpha <= 0:
                continue
            gradient = lerp(BG_INNER, BG_OUTER, (x + y) / (2 * size))
            pixels[py][px] = blend(pixels[py][px], gradient, tile_alpha)

            colour = None
            alpha = 0.0

            # Bell body: rounded dome + skirt.
            dome_cx, dome_cy, dome_r = sx(256), sx(212), 110 * (art_size / 512.0)
            dome_d = math.hypot(x - dome_cx, y - dome_cy) - dome_r
            body_d = rounded_rect_distance(
                x, y, sx(146), sx(212), sx(366), sx(292), 18 * (art_size / 512.0)
            )
            skirt_d = rounded_rect_distance(
                x, y, sx(116), sx(292), sx(396), sx(340), 22 * (art_size / 512.0)
            )
            bell_d = min(dome_d, body_d, skirt_d)
            bell_alpha = coverage(bell_d)
            if bell_alpha > 0:
                t = max(0.0, min(1.0, (y - sx(92)) / max(1.0, sx(416) - sx(92))))
                colour, alpha = lerp(BELL_TOP, BELL_BOTTOM, t), bell_alpha

            # Clapper under the bell.
            clapper_d = math.hypot(x - sx(256), y - sx(372)) - 44 * (art_size / 512.0)
            clapper_alpha = coverage(clapper_d) if y >= sx(372) else 0.0
            if clapper_alpha > alpha:
                colour, alpha = lerp(BELL_TOP, BELL_BOTTOM, 0.95), clapper_alpha

            # Top button.
            button_d = rounded_rect_distance(
                x, y, sx(236), sx(60), sx(276), sx(100), 20 * (art_size / 512.0)
            )
            button_alpha = coverage(button_d)
            if button_alpha > alpha:
                colour, alpha = LIGHT, button_alpha

            # Signal arcs on both sides.
            for centre_x in (sx(256),):
                ring = abs(math.hypot(x - centre_x, y - sx(226)) - 168 * (art_size / 512.0))
                arc_alpha = coverage(ring - 8 * (art_size / 512.0))
                above = y < sx(200)
                horizontal = abs(x - centre_x) > 96 * (art_size / 512.0)
                if arc_alpha > 0 and above and horizontal and arc_alpha > alpha:
                    colour, alpha = ACCENT, arc_alpha * 0.9

            if colour and alpha > 0:
                pixels[py][px] = blend(pixels[py][px], colour, min(1.0, alpha) * tile_alpha)

    return pixels


def write_png(path, pixels):
    size = len(pixels)
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0
        for r, g, b in row:
            raw += bytes((r, g, b))

    def chunk(tag, data):
        payload = tag + data
        return (
            struct.pack(">I", len(data))
            + payload
            + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(png)
    print(f"wrote {path} ({size}x{size}, {len(png)} bytes)")


if __name__ == "__main__":
    write_png(os.path.join(OUT_DIR, "icon-192.png"), draw(192))
    write_png(os.path.join(OUT_DIR, "icon-512.png"), draw(512))
    write_png(os.path.join(OUT_DIR, "icon-maskable-512.png"), draw(512, padding_ratio=0.14))
