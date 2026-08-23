#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
#
# This file is part of segno_ui

"""
Generate the Segno UI application icon

The glyph is a QR Code finder pattern, the concentric square that sits in three
corners of every QR Code. It is the one part of a code that stays readable when
scaled down to a 16 pixel taskbar icon, unlike a whole code which turns to mush.

This is a maintenance script, not part of the application: it needs Pillow, which
segno_ui itself does not depend on. Run it only when the icon has to change.

    python3 -m pip install Pillow
    python3 contrib/make_icon.py

It rewrites pics/segno_ui.ico and prints the base64 payloads to paste into
segno_ui/segno_ui.py as ICON_BASE64, PIPETTE_LIGHT_BASE64 and PIPETTE_DARK_BASE64.

The pipette is the little eyedropper drawn on each colour swatch, in two shades so
that one of them always stands out against whatever colour the swatch is showing.
"""

__intname__ = "segno_ui.contrib.make_icon"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2026 Orsiris de Jong - NetInvent"
__licence__ = "BSD 3 Clause"


import base64
import io
import os
import textwrap

from PIL import Image, ImageDraw

# Same accent as the GUI theme
ACCENT = "#2563EB"
WHITE = "#FFFFFF"
# Same ink as the GUI text, so the pipette reads as part of the interface
PIPETTE_DARK = "#16202B"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICO_PATH = os.path.join(ROOT, "pics", "segno_ui.ico")
PNG_PATH = os.path.join(ROOT, "pics", "icon.png")

# Every size Windows may ask for, drawn natively rather than downscaled so the
# module edges stay crisp
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
# The size embedded in the source and handed to tkinter
EMBED_SIZE = 64
# The pipette sits on a colour swatch barely twenty pixels tall
PIPETTE_SIZE = 16
# Diagonals come out ragged at that size unless drawn big and reduced
SUPERSAMPLE = 8


def draw_icon(size: int) -> Image.Image:
    """
    A finder pattern in white on a rounded accent coloured square
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    radius = max(2, round(size * 0.2))
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=ACCENT)

    # A finder pattern is 7x7 modules: a one module ring, a one module gap, then
    # a 3x3 core. Keep the module an integer so nothing lands on a half pixel
    module = max(1, round(size * 0.11))
    block = module * 7
    offset = (size - block) // 2

    def square(modules_in, color):
        start = offset + modules_in * module
        end = offset + (7 - modules_in) * module - 1
        draw.rectangle([start, start, end, end], fill=color)

    square(0, WHITE)  # outer ring
    square(1, ACCENT)  # gap
    square(2, WHITE)  # core
    return image


def draw_pipette(size: int, color) -> Image.Image:
    """
    An eyedropper: round bulb at the top right, body tapering to a point

    The background stays transparent so the swatch colour shows around it
    """
    big = size * SUPERSAMPLE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    unit = big / 64.0

    def at(*points):
        return [(x * unit, y * unit) for x, y in points]

    draw.ellipse([40 * unit, 6 * unit, 58 * unit, 24 * unit], fill=color)
    draw.polygon(at((40, 16), (48, 24), (14, 54), (8, 58), (10, 48)), fill=color)
    return image.resize((size, size), Image.LANCZOS)


def as_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def emit(name: str, payload: str) -> None:
    """
    Print a literal ready to paste into segno_ui.py
    """
    print(f"\n{name}, {len(payload)} characters:\n")
    body = '"\n    b"'.join(textwrap.wrap(payload, 72))
    print(f'{name} = (\n    b"{body}"\n)')


def main():
    frames = [draw_icon(size) for size in ICO_SIZES]

    frames[-1].save(ICO_PATH, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    print(f"wrote {ICO_PATH} ({os.path.getsize(ICO_PATH)} bytes)")

    embedded = draw_icon(EMBED_SIZE)
    embedded.save(PNG_PATH, format="PNG", optimize=True)
    print(f"wrote {PNG_PATH} ({os.path.getsize(PNG_PATH)} bytes)")

    emit("ICON_BASE64", as_base64(embedded))

    # One shade for dark swatches, one for light ones
    emit("PIPETTE_LIGHT_BASE64", as_base64(draw_pipette(PIPETTE_SIZE, WHITE)))
    emit("PIPETTE_DARK_BASE64", as_base64(draw_pipette(PIPETTE_SIZE, PIPETTE_DARK)))


if __name__ == "__main__":
    main()
