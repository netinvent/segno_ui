#! /usr/bin/env python3
#  -*- coding: utf-8 -*-


__intname__ = "segno_ui"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2022-2026 Orsiris de Jong - NetInvent"
__description__ = (
    "Basic UI for segno QR Code generator allowing to use segno fully offline"
)
__licence__ = "BSD 3 Clause"
__version__ = "1.1.0"
__build__ = "2026082405"
__url__ = "https://github.com/netinvent/segno_ui"


from typing import Tuple, Optional
import os
import sys
import inspect
import json
import argparse
import colorsys
import random

try:
    import FreeSimpleGUI as sg
except ImportError as exc:
    print(
        "Module not found. If tkinter is missing, you need to install it from your distribution. See README.md file"
    )
    print(f"Error: {exc}")
    sys.exit(1)
import tkinter as tk
from tkinter import ttk

try:
    import segno
    import segno.helpers
except ImportError as exc:
    print("Module segno not found. Install it with 'python3 -m pip install segno'")
    print(f"Error: {exc}")
    sys.exit(1)

_DEBUG = False

# QRCode types and their respective make function in segno
QRCODE_TYPES = {
    # The following function is just a dummy function so we get a function signature
    "Generic": lambda content="": content,
    "vCard": segno.helpers.make_vcard_data,
    "MeCard": segno.helpers.make_mecard_data,
    "Email": segno.helpers.make_make_email_data,
    "Geo": segno.helpers.make_geo_data,
    "Wifi": segno.helpers.make_wifi_data,
    "EPC": segno.helpers.make_epc_qr,
}

# Unlike every other helper, make_epc_qr() returns a ready made QRCode instead of
# encodable data, the EPC specification imposing its own error correction level and
# version. Its result must not be handed over to segno.make_qr() / segno.make_micro()
SELF_MAKING_QRCODE_TYPES = ("EPC",)

# Arguments segno wants as floats, but that a text input can only give us as strings
FLOAT_ARGUMENTS = ("lat", "lng")

# Arguments holding credentials, so we may warn before writing them in clear text
SECRET_ARGUMENTS = ("password",)

# Arguments worth picking from a list rather than typing. segno validates none of
# this, it passes the value straight through and only uppercases it, so a typo
# used to travel all the way into the code. An empty first entry leaves the field
# out entirely, which is what segno does with no value at all
ARGUMENT_CHOICES = {
    "security": ("", "WPA", "WEP", "nopass", "SAE", "WPA2-EAP"),
}

# Overrides the generic "segno argument 'x'" hint where a word of help is due
ARGUMENT_TOOLTIPS = {
    "security": "WPA also covers WPA2, SAE is WPA3, WPA2-EAP is enterprise.\n"
    "'nopass' marks an open network, empty leaves the field out",
}

PNG_URL_HEADER = "data:image/png;base64,"
ecc_levels = {"7%": "L", "15%": "M", "25%": "Q", "33%": "H"}
scales = [1, 2, 3, 4, 5, 6, 7, 8]
borders = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# A scale of 2 exports a roughly 60 pixel image, too small to be of much use
DEFAULT_SCALE = 4
DEFAULT_BORDER = 1

STANDARD_QRCODE_FORMAT = "Standard QR Code"
MICRO_QRCODE_FORMAT = "Mini QR Code"
# Micro QR Codes cannot carry error correction level H
MICRO_UNSUPPORTED_ECC_LEVELS = ("33%",)

EXPORT_FORMATS = ["png", "svg", "eps", "pdf"]
# Only those two carry a separate colour for the data modules
EXPORT_FORMATS_WITH_DATA_COLORS = ("png", "svg")

COLOR_INPUT_KEYS = ("-DARK-", "-LIGHT-", "-DATA_DARK-", "-DATA_LIGHT-")
DEFAULT_COLORS = {
    "-DARK-": "#000000",
    "-LIGHT-": "#FFFFFF",
    "-DATA_DARK-": "#000000",
    "-DATA_LIGHT-": "#FFFFFF",
}


###############################################################################
# Look and feel
###############################################################################

# Tk silently falls back to a default family when the requested one is missing
FONT_FAMILY = {"win32": "Segoe UI", "darwin": "Helvetica Neue"}.get(
    sys.platform, "DejaVu Sans"
)
FONT = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = ("Consolas" if sys.platform == "win32" else "monospace", 9)
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_FRAME = (FONT_FAMILY, 9, "bold")

COLOR_BACKGROUND = "#EEF1F5"
COLOR_SURFACE = "#FFFFFF"
COLOR_TEXT = "#1B2733"
COLOR_MUTED = "#67757F"
# The dark shade the pipette is drawn in, matching contrib/make_icon.py
PIPETTE_INK = "#16202B"
COLOR_ACCENT = "#2563EB"
COLOR_ACCENT_TEXT = "#FFFFFF"
COLOR_SECONDARY = "#DDE3EA"
COLOR_DANGER = "#B3261E"
COLOR_BORDER = "#C9D2DB"
SCROLLBAR_WIDTH = 11

# Panels sitting side by side, each pair kept at a common height by align_panels()
PANEL_PAIRS = (
    ("-CONTENT_FRAME-", "-PREVIEW_FRAME-"),
    ("-CODE_FRAME-", "-COLORS_FRAME-"),
)

THEME_NAME = "SegnoUI"

# Application icon, a QR Code finder pattern: the concentric square that sits in
# three corners of every QR Code, and the only part of one still legible at 16
# pixels. Regenerate with contrib/make_icon.py, which also writes the .ico that
# the Windows build needs
ICON_BASE64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAA9klEQVR42u3bwQ3CMBBE0fWI"
    b"EqAEaAzKgsagBNIDnLgF29gisnf/nrnMk50VUSZZ5RzPz5dNNI/bIdX8LnkK3YIh7+FLWeQ9"
    b"fCmTIoTPZVOU8N8yKlL4tawpF/5+3U8f9nRZsttBFnwAiHT3154FnAAAgs/uH+tl6+lZ11wB"
    b"AAAAAADW4EBraeu1yxUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOOlqA36ApMTAAAAAAAAwCBr"
    b"0MNXpJwAAAAAQLXtKo/D5/KlNTjTv7quZ0DEa/DJrF+blt6KlGqpm3pqkaq1c+ulQque4rGH"
    b"/rB629ezl6dT9Pr8GxgwURnSC0zzAAAAAElFTkSuQmCC"
)

# The eyedropper drawn on every colour swatch, in two shades so one of them
# always stands out against the colour underneath. Both come from
# contrib/make_icon.py, same as the application icon
PIPETTE_LIGHT_BASE64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA+UlEQVR42pWTMUoDQRSG/7cb"
    b"RUQEe6sgW6TWzkIPYKl4AHuvkMYTWKQUr5BC8BiB5AIhhbVRRDT72fzBZWCzkwfDz8zwvTfv"
    b"f4yUGUAk+0KSIheOCIAbSSeSxhExTZO2wSVQAA/8xydw1pkACMMl8A6sgA8neZKkouMBvYio"
    b"Jd1L2pe0krTnu3lX9R3rrSv+WH+BF+BwbeQm+BqogW/DI6Bqm8z6sGe9AL7cN8Aw8WYjfA4s"
    b"DdbAXXMireOyDoA3w0vgqpm8DS6sFbAwvABOs2CvY2BmeAL0O+Gk70fDr8BRFtxwtHT1Z2C3"
    b"6UnuTzsALlNPtg57Edswf/EtQsB70DQ9AAAAAElFTkSuQmCC"
)

PIPETTE_DARK_BASE64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABnUlEQVR42p2Tv09TURTHv+fc"
    b"95oGO0FfK6nSVwcD9wELq6H1DzC6PMM/wGJiHE2cNM6ElZWRiYGBhMHEHRagCwMEiIkgjYmm"
    b"Jva9ew5DW22aQgvf5A53+Hzv/Z4fwOiivjsDgLkDrPlw5nVuYvJl7sH4z+avqwsARCPABoAG"
    b"of1sjP8BAETcHwetNU7quzzKy0BMpHgr4sSlSZOJx4zKGwA6xGDBAyCFcv0dMY9BxRGQJWao"
    b"8tm/QtwA+8Beki9HS8RmRVWVyPhghkuTbef/XQHAdBscVGzM4A1VJMycceLWlMzq1cn+UTfi"
    b"AIOqB3xNJ8pRzTBtQzVDzCxOPv04rX/sa2l/Ddpw8Ng+84i2CMgSEWkqy204Np3Y2jm9ig0A"
    b"PJyythhG34tP5rUQzv4uVqIX/81vni4GIPnK9FNW84WNVxKXfnOOXjXOD3e7PxtkwN1OjJfm"
    b"HrGaTfb8knPpPoQXh8Ftg2qVAYjny3svk7WStHZawrXLs4PjYXBPjNgEYVQvVGbXYW2mtyYj"
    b"KQhsrliOnvdv2n3EA9b2Vl0DNyiUL3LMCMwAAAAASUVORK5CYII="
)

# A QR Code is read by telling dark modules from light ones. ISO/IEC 18004 puts
# this in terms of reflectance rather than contrast ratio, so the ranges below
# were settled by decoding rendered codes through simulated camera noise rather
# than by picking a number off a chart. What limits a coloured code is the light
# end: a tinted background loses luminance headroom far faster than a saturated
# dark colour gains it, hence the pale light range against the free dark one
MIN_CONTRAST_RATIO = 8.0
RANDOM_COLOR_ATTEMPTS = 60
RANDOM_DARK_SATURATION = (0.60, 0.98)
RANDOM_LIGHT_LIGHTNESS = (0.96, 0.995)
RANDOM_LIGHT_SATURATION = (0.05, 0.25)
# Luminance is nowhere near evenly spread across the hues. Against a white
# background a blue can sit at half lightness and still read, while a yellow is
# spent by about 0.17. So this is a limit rather than a target: every hue is
# taken as far towards it as that particular hue can go
RANDOM_DARK_LIGHTNESS_CEILING = 0.55
RANDOM_DARK_LIGHTNESS_FLOOR = 0.10
# How far below its own ceiling a colour may land, so successive rolls differ
RANDOM_DARK_LIGHTNESS_SPREAD = 0.12
# Drawing hues evenly means most rolls land on a hue with no headroom, so hues
# are drawn several times over and kept in proportion to how bright they may go.
# The exponent sets how hard that leans, 0 being an even draw
RANDOM_HUE_DRAWS = 12
RANDOM_HUE_BRIGHTNESS_BIAS = 3

LABEL_SIZE = (15, 1)
COLOR_LABEL_SIZE = (11, 1)
# Wide enough that the colour still reads around the pipette sitting on it
SWATCH_SIZE = (46, 22)
FIELD_SIZE = (22, 1)
COLOR_FIELD_SIZE = (11, 1)
FRAME_PAD = ((0, 0), (0, 10))
# Every tab gets the same canvas so switching tabs never resizes the window
TAB_CONTENT_SIZE = (415, 296)
VISIBLE_TAB_ROWS = 9
PREVIEW_SIZE = (330, 336)

STATUS_READY = "Ready"
STATUS_EMPTY = "Nothing to encode yet"

BUTTON_PRIMARY = {"button_color": (COLOR_ACCENT_TEXT, COLOR_ACCENT), "border_width": 0}
BUTTON_SECONDARY = {"button_color": (COLOR_TEXT, COLOR_SECONDARY), "border_width": 0}
# SaveAs / FileBrowse take a button_color but no border_width
BUTTON_SECONDARY_COLOR = {"button_color": (COLOR_TEXT, COLOR_SECONDARY)}

MENU_IMPORT_SETTINGS = "Import settings..."
MENU_EXPORT_SETTINGS = "Export settings..."
MENU_EXIT = "Exit"
MENU_ABOUT = "About"
MENU_DEFINITION = [
    ["&File", [f"&{MENU_IMPORT_SETTINGS}", f"&{MENU_EXPORT_SETTINGS}", "---", "E&xit"]],
    ["&Help", [f"&{MENU_ABOUT}"]],
]

SETTINGS_FILE_TYPES = (("Segno UI settings", "*.json"), ("All files", "*.*"))

# segno argument names are terse and lowercase, these read better as GUI labels
ARGUMENT_LABELS = {
    "bcc": "Bcc",
    "bic": "BIC",
    "cc": "Cc",
    "cellphone": "Cell phone",
    "displayname": "Display name",
    "homephone": "Home phone",
    "houseno": "House number",
    "iban": "IBAN",
    "lat": "Latitude",
    "lng": "Longitude",
    "memo": "Memo",
    "org": "Organisation",
    "photo_uri": "Photo URI",
    "pobox": "PO box",
    "prefecture": "Prefecture",
    "rev": "Revision",
    "roomno": "Room number",
    "ssid": "Network name",
    "to": "To",
    "url": "URL",
    "videophone": "Video phone",
    "workphone": "Work phone",
    "zipcode": "Zip code",
}

TOOLTIPS = {
    "-QRCODE_FORMAT-": "Mini (Micro) QR Codes are smaller but hold far less data",
    "-ERROR-": "How much of the code may be damaged and still be readable.\n"
    "Higher levels need a bigger code",
    "-SCALE-": "Size of a single module, in pixels",
    "-BORDER-": "Width of the quiet zone around the code, in modules",
    "-DARK-": "Colour of the dark modules",
    "-LIGHT-": "Background colour",
    "-DATA_DARK-": "Colour of the dark data modules only.\nPNG and SVG exports only",
    "-DATA_LIGHT-": "Colour of the light data modules only.\nPNG and SVG exports only",
    "-EXPORT_FORMAT-": "EPS and PDF exports ignore the data colours",
}


def apply_theme() -> None:
    """
    Register and select our own theme

    FreeSimpleGUI ships 160 themes but none of them is quiet enough for a form
    heavy window, so let's define a light neutral one with a single accent colour
    """
    sg.LOOK_AND_FEEL_TABLE[THEME_NAME] = {
        "BACKGROUND": COLOR_BACKGROUND,
        "TEXT": COLOR_TEXT,
        "INPUT": COLOR_SURFACE,
        "TEXT_INPUT": COLOR_TEXT,
        "SCROLL": COLOR_BORDER,
        "BUTTON": (COLOR_ACCENT_TEXT, COLOR_ACCENT),
        "PROGRESS": (COLOR_ACCENT, COLOR_SECONDARY),
        "BORDER": 1,
        "SLIDER_DEPTH": 0,
        "PROGRESS_DEPTH": 0,
    }
    sg.theme(THEME_NAME)
    # Setting the icon here rather than on the Window means the popups get it too
    sg.set_options(
        font=FONT,
        element_padding=(5, 4),
        margins=(0, 0),
        icon=ICON_BASE64,
        # Without this Windows upscales the whole window into a blur on any
        # display running above 100%
        dpi_awareness=True,
    )


def iter_widgets(widget):
    """
    Every widget under this one, depth first
    """
    for child in widget.winfo_children():
        yield child
        for grand_child in iter_widgets(child):
            yield grand_child


def flatten_scrollbars(window: sg.Window) -> None:
    """
    Reduce the scrollable tabs' scrollbars to a bare thumb

    The arrow buttons at either end are part of the widget layout, so they have
    to be laid out away rather than recoloured. A scrollable Column owns its
    scrollbars privately and they are not elements of their own, so the widget
    tree has to be walked to reach them. Runs once the window is finalized
    """
    style = ttk.Style(window.TKroot)
    for widget in iter_widgets(window.TKroot):
        if not isinstance(widget, ttk.Scrollbar):
            continue
        try:
            restyle_scrollbar(style, widget.cget("style"))
        except tk.TclError:
            # A Tk build whose theme lays scrollbars out under different element
            # names keeps its own. Losing the arrows is worth nothing measured
            # against failing to open the window at all
            pass


def restyle_scrollbar(style: "ttk.Style", name: str) -> None:
    """
    Strip the arrows off one scrollbar and recolour what is left
    """
    style.layout(
        name,
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "nswe",
                    "children": [
                        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})
                    ],
                },
            )
        ],
    )
    style.configure(
        name,
        troughcolor=COLOR_SURFACE,
        background=COLOR_BORDER,
        bordercolor=COLOR_SURFACE,
        lightcolor=COLOR_BORDER,
        darkcolor=COLOR_BORDER,
        relief=sg.RELIEF_FLAT,
        borderwidth=0,
        # It is arrowsize, not width, that gives a vertical scrollbar its
        # thickness. Leave it at zero and the whole widget collapses to a one
        # pixel line, arrows or no arrows
        arrowsize=SCROLLBAR_WIDTH,
        width=SCROLLBAR_WIDTH,
    )
    # FreeSimpleGUI maps the thumb colour per state, and a map beats configure
    style.map(
        name,
        background=[("active", COLOR_MUTED), ("!active", COLOR_BORDER)],
        troughcolor=[("!disabled", COLOR_SURFACE)],
    )


def align_panels(window: sg.Window) -> None:
    """
    Give each side by side pair of panels exactly the same height

    Content carries a tab strip that Preview does not, and the Colours rows are
    taller than the Code rows because a tk Button is taller than a Combobox. Both
    gaps depend on font metrics, so rather than hard code a spacer, measure once
    the window exists and grow the shorter panel of each pair to match.

    A Tk frame shrinks to fit its children unless propagation is turned off, and
    once it is off the frame uses its own width and height, hence setting both
    """
    window.TKroot.update_idletasks()
    for left_key, right_key in PANEL_PAIRS:
        try:
            frames = [window[left_key].Widget, window[right_key].Widget]
            target = max(frame.winfo_reqheight() for frame in frames)
            for frame in frames:
                frame.configure(width=frame.winfo_reqwidth(), height=target)
                frame.pack_propagate(False)
                frame.grid_propagate(False)
        except (tk.TclError, KeyError, AttributeError):
            # Same bargain as above, tidiness is not worth a window that will
            # not open
            pass


def prettify_argument(argument: str) -> str:
    """
    Turn a segno argument name into something worth showing next to an input
    """
    if argument in ARGUMENT_LABELS:
        return ARGUMENT_LABELS[argument]
    return argument.replace("_", " ").capitalize()


def parse_color(color: str) -> Tuple[int, int, int]:
    """
    Turn "#RRGGBB" or "#RGB" into its three components
    """
    value = str(color).strip().lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    if len(value) != 6:
        raise ValueError(f"not a hex colour: {color!r}")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def relative_luminance(color: str) -> float:
    """
    WCAG relative luminance, 0 for black and 1 for white
    """
    channels = []
    for value in parse_color(color):
        channel = value / 255
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(one: str, other: str) -> float:
    """
    WCAG contrast ratio, 1 for two identical colours and 21 for black on white
    """
    first = relative_luminance(one)
    second = relative_luminance(other)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def hsl_to_hex(hue: float, saturation: float, lightness: float) -> str:
    """
    colorsys works in HLS, and in floats, we want "#RRGGBB"
    """
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#{:02X}{:02X}{:02X}".format(
        round(red * 255), round(green * 255), round(blue * 255)
    )


def brightest_dark_lightness(hue: float, saturation: float, light: str) -> float:
    """
    How light this hue may be drawn and still clear MIN_CONTRAST_RATIO

    There is no closed form for this, luminance being a weighted sum of channels
    that HSL lightness moves unevenly, so bisect it. Twenty rounds lands well
    inside a single step of eight bit colour
    """
    low = RANDOM_DARK_LIGHTNESS_FLOOR
    high = RANDOM_DARK_LIGHTNESS_CEILING
    if contrast_ratio(hsl_to_hex(hue, saturation, high), light) >= MIN_CONTRAST_RATIO:
        return high
    for _ in range(20):
        middle = (low + high) / 2
        if (
            contrast_ratio(hsl_to_hex(hue, saturation, middle), light)
            >= MIN_CONTRAST_RATIO
        ):
            low = middle
        else:
            high = middle
    return low


def pick_bright_hue(rng, saturation: float, light: str) -> Tuple[float, float]:
    """
    A hue, favouring those that can carry a bright colour, and its own ceiling

    Blue holds its contrast against white up to about half lightness while yellow
    is spent by a fifth of it. Drawing hues evenly therefore makes most rolls come
    out near black. Drawing several and keeping one in proportion to its headroom
    leans towards the roomy hues while still letting a deep olive through now and
    then. Returns the hue together with the ceiling already computed for it
    """
    hue = rng.random()
    ceiling = brightest_dark_lightness(hue, saturation, light)
    for _ in range(RANDOM_HUE_DRAWS):
        odds = (ceiling / RANDOM_DARK_LIGHTNESS_CEILING) ** RANDOM_HUE_BRIGHTNESS_BIAS
        if rng.random() < odds:
            break
        hue = rng.random()
        ceiling = brightest_dark_lightness(hue, saturation, light)
    return hue, ceiling


def random_color_scheme(rng=None) -> dict:
    """
    A random set of colours that still scans

    Random RGB would cheerfully hand back mid grey on mid grey. Instead the hue is
    picked freely and then driven as bright as that hue can manage against the
    background, which is what keeps the results colourful rather than a parade of
    near blacks. The pair is handed back only once it clears MIN_CONTRAST_RATIO.
    Should the dice somehow never oblige, plain black on white always does
    """
    rng = rng or random

    def at_ceiling(hue, saturation, light, ceiling=None):
        if ceiling is None:
            ceiling = brightest_dark_lightness(hue, saturation, light)
        floor = max(RANDOM_DARK_LIGHTNESS_FLOOR, ceiling - RANDOM_DARK_LIGHTNESS_SPREAD)
        return hsl_to_hex(hue, saturation, rng.uniform(floor, ceiling))

    for _ in range(RANDOM_COLOR_ATTEMPTS):
        saturation = rng.uniform(*RANDOM_DARK_SATURATION)
        light = hsl_to_hex(
            rng.random(),
            rng.uniform(*RANDOM_LIGHT_SATURATION),
            rng.uniform(*RANDOM_LIGHT_LIGHTNESS),
        )
        hue, ceiling = pick_bright_hue(rng, saturation, light)
        dark = at_ceiling(hue, saturation, light, ceiling)
        # A neighbouring hue for the data modules, so the code has two tones
        data_dark = at_ceiling((hue + rng.uniform(0.03, 0.13)) % 1.0, saturation, light)
        if (
            min(contrast_ratio(dark, light), contrast_ratio(data_dark, light))
            >= MIN_CONTRAST_RATIO
        ):
            return {
                "-DARK-": dark,
                "-LIGHT-": light,
                "-DATA_DARK-": data_dark,
                "-DATA_LIGHT-": light,
            }
    return dict(DEFAULT_COLORS)


def pipette_for(color: str) -> bytes:
    """
    Whichever shade of the eyedropper stands out best on this colour
    """
    if contrast_ratio(color, PIPETTE_INK) >= contrast_ratio(color, COLOR_SURFACE):
        return PIPETTE_DARK_BASE64
    return PIPETTE_LIGHT_BASE64


def color_chooser_key(input_key: str) -> str:
    """
    The picker button that goes with a colour input, "-DARK-" -> "-DARK_CHOOSER-"
    """
    return f"{input_key[:-1]}_CHOOSER-"


def get_argument_defaults(segno_function) -> dict:
    """
    Map argument names to their default value for a given segno helper function
    """
    argspec = inspect.getfullargspec(segno_function)
    if not argspec.defaults:
        return {}
    return dict(zip(argspec.args[-len(argspec.defaults) :], argspec.defaults))


def with_extension(filename: str, extension: str) -> str:
    """
    Make sure filename ends with .extension

    We cannot just append it, or a user picking "qrcode.png" would end up with a
    "qrcode.png.png" file. We cannot split on dots either, or any directory holding
    a dot (a "John.Doe" profile directory being the obvious one) would make us
    write somewhere else entirely
    """
    extension = "." + extension.lstrip(".")
    if os.path.splitext(filename)[1].lower() == extension.lower():
        return filename
    return f"{filename}{extension}"


def contains_secrets(config: dict) -> bool:
    """
    Tell whether a settings file we're about to write holds credentials
    """
    for arguments in config.get("data", {}).values():
        for argument in arguments:
            if argument in SECRET_ARGUMENTS:
                return True
    return False


def get_conf_from_gui(values: dict) -> Tuple[dict, dict, dict]:
    """
    Export SimpleGUI output configuration to dicts
    """
    # Let's make sure we use L, M, Q, H instead of percentages
    error = ecc_levels[values["-ERROR-"]]
    colors = {key: values[key] or DEFAULT_COLORS[key] for key in COLOR_INPUT_KEYS}
    scale = int(values["-SCALE-"])
    border = int(values["-BORDER-"])
    qrcode_format = values["-QRCODE_FORMAT-"]
    active_tab = values["-ACTIVE_TAB-"]
    export_format = values["-EXPORT_FORMAT-"]

    segno_make_opts = {"error": error, "boost_error": False}

    # Export parameters
    segno_export_opts = {
        "dark": colors["-DARK-"],
        "light": colors["-LIGHT-"],
        "scale": scale,
        "border": border,
    }

    # Add data_dark and data_light if export is SVG or PNG since EPS and PDF don't support them
    if export_format in EXPORT_FORMATS_WITH_DATA_COLORS:
        segno_export_opts["data_dark"] = colors["-DATA_DARK-"]
        segno_export_opts["data_light"] = colors["-DATA_LIGHT-"]

    misc_options = {
        "qrcode_format": qrcode_format,
        "active_tab": active_tab,
        "export_format": export_format,
    }

    return (segno_make_opts, segno_export_opts, misc_options)


def get_segno_arguments_from_gui(
    values: dict, only: str = None, strict: bool = True
) -> dict:
    """
    Transform SimpleGUI values into dict

    `only` narrows the work to a single QRCode type. Building a code reads just
    the tab in front of the user: a half typed latitude left behind in the Geo
    tab has no business breaking the Generic tab they moved on to. Exporting
    settings still wants the lot, so the default stays every type.

    `strict` decides what to do with a value that will not convert. Generation
    wants the complaint, since segno would otherwise happily encode "geo:north,2"
    without a murmur. A preset only records what is on screen, so it keeps the
    text as typed and leaves the complaining to the tab that owns it
    """
    # Get all arguments for the given qrcode helper function
    data = {}
    wanted = QRCODE_TYPES if only is None else {only: QRCODE_TYPES[only]}
    for qrcode_type, segno_function in wanted.items():

        segno_arguments = inspect.getfullargspec(segno_function).args
        data[qrcode_type] = {}
        for segno_argument in segno_arguments:
            value = values[f"-{qrcode_type}_{segno_argument}-"]
            if value:
                # special case for Geo QRCode which requires floats
                if segno_argument in FLOAT_ARGUMENTS:
                    try:
                        value = float(value)
                    except ValueError:
                        if strict:
                            raise
                data[qrcode_type][segno_argument] = value
    return data


def has_content(values: dict) -> bool:
    """
    Tell whether the active tab holds anything worth encoding

    Every segno helper but the Generic one takes required arguments, so calling
    them with an untouched tab raises a TypeError naming arguments the user has
    not been given a chance to fill in yet. Reporting that on a mere tab change
    is noise, so ask first and stay quiet until there is something to work with
    """
    qrcode_type = values["-ACTIVE_TAB-"]
    segno_function = QRCODE_TYPES[qrcode_type]
    for segno_argument in inspect.getfullargspec(segno_function).args:
        # Checkboxes give a bool and unset combos an empty string, both of which
        # read correctly here without any special casing
        if values.get(f"-{qrcode_type}_{segno_argument}-"):
            return True
    return False


def update_element(window: sg.Window, key: str, value) -> None:
    """
    Update a GUI element, silently ignoring keys that don't exist

    A settings file written by another version may hold parameters that segno has
    since renamed or dropped, and those shouldn't abort the whole import
    """
    if key in window.AllKeysDict:
        window[key].update(value)


def fill_gui_from_segno_arguments(config: dict, window: sg.Window) -> bool:
    """
    Restore a settings file into the GUI

    Missing sections and unknown QRCode types are tolerated so settings files
    written by earlier versions keep working
    """
    try:
        if config["software"]["name"] != __intname__:
            raise EnvironmentError
    except Exception:
        sg.popup("Invalid configuration file")
        return False

    for key, value in config.get("segno_make_opts", {}).items():
        # Special handling for some variables

        # We don't have a boost_error parameter in gui
        if key == "boost_error":
            continue
        # Transform error parameter from percentage into letter according to dict
        if key == "error":
            percentages = [i for i in ecc_levels if ecc_levels[i] == value]
            if not percentages:
                continue
            value = percentages[0]
        update_element(window, f"-{key.upper()}-", value)

    for key, value in config.get("segno_export_opts", {}).items():
        update_element(window, f"-{key.upper()}-", value)

    for key, value in config.get("misc_opts", {}).items():
        # active_tab is not an element of its own but the selected tab of the
        # -ACTIVE_TAB- TabGroup, whose update() only knows about visibility
        if key == "active_tab":
            if value in QRCODE_TYPES:
                window[value].select()
            continue
        update_element(window, f"-{key.upper()}-", value)

    for qrcode_type in QRCODE_TYPES.keys():
        for key, value in config.get("data", {}).get(qrcode_type, {}).items():
            update_element(window, f"-{qrcode_type}_{key}-", value)
    return True


def sync_ecc_levels(window: sg.Window, values: dict) -> None:
    """
    Only offer error correction levels the current mode can actually produce,
    Micro QR Codes having no level H
    """
    if values["-QRCODE_FORMAT-"] == MICRO_QRCODE_FORMAT:
        available = [
            level for level in ecc_levels if level not in MICRO_UNSUPPORTED_ECC_LEVELS
        ]
    else:
        available = list(ecc_levels.keys())

    current = values["-ERROR-"]
    if current not in available:
        current = available[-1]
    window["-ERROR-"].update(value=current, values=available)
    # Keep values in sync so the caller may generate right away
    values["-ERROR-"] = current


def sync_mode_availability(window: sg.Window, values: dict) -> None:
    """
    Grey out the settings the active QRCode type does not honour

    EPC codes carry the mode and the error correction level their specification
    imposes, so offering those two controls on that tab is only misleading
    """
    imposed = values["-ACTIVE_TAB-"] in SELF_MAKING_QRCODE_TYPES
    window["-QRCODE_FORMAT-"].update(disabled=imposed)
    window["-ERROR-"].update(disabled=imposed)


def refresh_color_swatches(window: sg.Window, values: dict) -> None:
    """
    Mirror every colour input into its picker button, turning it into a swatch
    """
    for key in COLOR_INPUT_KEYS:
        color = values.get(key) or DEFAULT_COLORS[key]
        try:
            glyph = pipette_for(color)
        except ValueError:
            # Half typed, "#12" and the like, leave the swatch as it was
            continue
        try:
            # image_size has to be repeated here, an update that leaves it out
            # shrinks the button back to the bare size of the glyph
            window[color_chooser_key(key)].update(
                button_color=(color, color),
                image_data=glyph,
                image_size=SWATCH_SIZE,
            )
        except Exception:
            # tkinter rejects colours it cannot parse either
            pass


def build_qrcode(values: dict) -> Tuple["segno.QRCode", dict]:
    """
    Build the QRCode described by the GUI, along with its export options
    """
    segno_make_opts, segno_export_opts, misc_options = get_conf_from_gui(values)

    qrcode_type = values["-ACTIVE_TAB-"]
    data_arguments = get_segno_arguments_from_gui(values, only=qrcode_type)
    segno_function = QRCODE_TYPES[qrcode_type]

    if qrcode_type in SELF_MAKING_QRCODE_TYPES:
        # Helper already gives us a QRCode, mode and error correction being imposed
        # by the specification it implements
        qrcode = segno_function(**data_arguments[qrcode_type])
    else:
        qrcode_generate_fn = (
            segno.make_micro
            if misc_options["qrcode_format"] == MICRO_QRCODE_FORMAT
            else segno.make_qr
        )
        # Run helper function
        content = segno_function(**data_arguments[qrcode_type])
        # Create QRCode from content made by helper
        qrcode = qrcode_generate_fn(content, **segno_make_opts)

    return qrcode, segno_export_opts


def describe_qrcode(qrcode: "segno.QRCode") -> str:
    """
    One line summary of what we just produced, for the status bar
    """
    width, height = qrcode.symbol_size(scale=1, border=0)
    kind = "Micro QR Code" if qrcode.is_micro else "QR Code"
    description = f"{kind} version {qrcode.version}, {width}x{height} modules"
    if qrcode.error:
        description += f", error correction {qrcode.error}"
    return description


def generate_code(values: dict, save_to: str = None) -> Optional[str]:
    """
    Create QRCodes

    Returns base64 encoded PNG data unless save_to is given, in which case the
    QRCode is written to disk and None is returned
    """
    qrcode, segno_export_opts = build_qrcode(values)

    # Make PNG and print it in SimpleGUI
    if not save_to:
        qrcode_data = qrcode.png_data_uri(**segno_export_opts)
        return qrcode_data[len(PNG_URL_HEADER) :]

    # Add file extension to filename unless the user already typed it
    save_to = with_extension(save_to, values["-EXPORT_FORMAT-"])
    qrcode.save(save_to, kind=values["-EXPORT_FORMAT-"], **segno_export_opts)
    return None


def fit_preview_scale(qrcode: "segno.QRCode", scale: int, border: int) -> int:
    """
    Largest scale, up to the requested one, that still fits the preview canvas

    Drawing a code bigger than the canvas would clip it, and a clipped QR Code
    loses the finder patterns in its corners, which is most of what makes a
    preview worth looking at. Scale 1 always fits, the biggest symbol there is
    being 177 modules wide
    """
    while scale > 1:
        width, height = qrcode.symbol_size(scale=scale, border=border)
        if width <= PREVIEW_SIZE[0] and height <= PREVIEW_SIZE[1]:
            break
        scale -= 1
    return scale


def draw_preview(
    window: sg.Window, qrcode: "segno.QRCode", segno_export_opts: dict
) -> int:
    """
    Draw the code centred in the preview canvas, shrunk if it would not fit

    Returns the scale the preview was drawn at, which may be smaller than the
    one the export will use
    """
    border = segno_export_opts["border"]
    scale = fit_preview_scale(qrcode, segno_export_opts["scale"], border)
    data_uri = qrcode.png_data_uri(**dict(segno_export_opts, scale=scale))

    graph = window["-OUTPUT-IMAGE-"]
    graph.erase()
    canvas_width, canvas_height = PREVIEW_SIZE
    width, height = qrcode.symbol_size(scale=scale, border=border)
    # Graph coordinates start bottom left, draw_image places the top left corner.
    # Nothing is clamped here on purpose: pinning these offsets to the canvas
    # edge is exactly what used to shove an oversized code out of centre
    left = (canvas_width - width) // 2
    top = (canvas_height + height) // 2
    graph.draw_image(data=data_uri[len(PNG_URL_HEADER) :], location=(left, top))
    return scale


def set_status(window: sg.Window, message: str = "", error: bool = False) -> None:
    """
    Write to the status bar, in red when something went wrong
    """
    window["-ERROR-TEXT-"].update(
        message or STATUS_READY,
        text_color=COLOR_DANGER if error else COLOR_MUTED,
    )


def export_settings(window: sg.Window, values: dict, config_filename: str) -> bool:
    """
    Write the current GUI state into a json settings file
    """
    config_filename = with_extension(config_filename, "json")
    config = {
        "software": {"name": __intname__, "version": __version__},
    }
    try:
        config["data"] = get_segno_arguments_from_gui(values, strict=False)
        (
            config["segno_make_opts"],
            config["segno_export_opts"],
            config["misc_opts"],
        ) = get_conf_from_gui(values)
        with open(config_filename, "w", encoding="utf-8") as file_handle:
            json.dump(config, file_handle, indent=2)
    except OSError as exc:
        sg.popup_error(f"Cannot write file {config_filename}: {exc}")
        if _DEBUG:
            raise
        return False
    except Exception as exc:
        sg.popup_error(f"Could not export config: {exc}")
        if _DEBUG:
            raise
        return False

    message = f"Configuration written to {config_filename}"
    if contains_secrets(config):
        message += "\n\nThis file holds passwords in clear text.\nStore it accordingly."
    sg.popup(message, title="Settings exported")
    set_status(window, f"Settings written to {os.path.basename(config_filename)}")
    return True


def import_settings(window: sg.Window, config_filename: str) -> bool:
    """
    Load a json settings file back into the GUI
    """
    try:
        with open(config_filename, "r", encoding="utf-8") as file_handle:
            config = json.load(file_handle)
    except Exception as exc:
        sg.popup_error(f"Could not import config file {config_filename}: {exc}")
        if _DEBUG:
            raise
        return False

    if not fill_gui_from_segno_arguments(config, window):
        return False
    set_status(window, f"Settings loaded from {os.path.basename(config_filename)}")
    return True


def show_about() -> None:
    """
    Small about box
    """
    sg.popup(
        f"{__description__}\n\n"
        f"Version {__version__}-{__build__}\n"
        f"{__copyright__}\n"
        f"Licensed under {__licence__}\n\n"
        f"{__url__}",
        title=f"About Segno UI {__version__}",
    )


def build_settings_frames() -> Tuple[sg.Frame, sg.Frame]:
    """
    The "Code" and "Colours" frames of the right hand column
    """

    def labelled(label: str, element) -> list:
        return [sg.Text(label, size=LABEL_SIZE, tooltip=element.Tooltip), element]

    code_frame = sg.Frame(
        " Code ",
        [
            labelled(
                "Mode",
                sg.Combo(
                    [STANDARD_QRCODE_FORMAT, MICRO_QRCODE_FORMAT],
                    default_value=STANDARD_QRCODE_FORMAT,
                    key="-QRCODE_FORMAT-",
                    size=FIELD_SIZE,
                    readonly=True,
                    enable_events=True,
                    tooltip=TOOLTIPS["-QRCODE_FORMAT-"],
                ),
            ),
            labelled(
                "Error correction",
                sg.Combo(
                    list(ecc_levels.keys()),
                    default_value="15%",
                    key="-ERROR-",
                    size=FIELD_SIZE,
                    readonly=True,
                    enable_events=True,
                    tooltip=TOOLTIPS["-ERROR-"],
                ),
            ),
            labelled(
                "Scale",
                sg.Spin(
                    scales,
                    initial_value=DEFAULT_SCALE,
                    key="-SCALE-",
                    size=FIELD_SIZE,
                    readonly=True,
                    enable_events=True,
                    tooltip=TOOLTIPS["-SCALE-"],
                ),
            ),
            labelled(
                "Border",
                sg.Spin(
                    borders,
                    initial_value=DEFAULT_BORDER,
                    key="-BORDER-",
                    size=FIELD_SIZE,
                    readonly=True,
                    enable_events=True,
                    tooltip=TOOLTIPS["-BORDER-"],
                ),
            ),
        ],
        font=FONT_FRAME,
        title_color=COLOR_MUTED,
        relief=sg.RELIEF_SOLID,
        border_width=1,
        expand_x=True,
        pad=FRAME_PAD,
        key="-CODE_FRAME-",
    )

    def color_row(label: str, key: str, trailing=None) -> list:
        """
        A label, its swatch and its hex field, optionally followed by a control
        parked in the slack at the right of the row
        """
        default = DEFAULT_COLORS[key]
        row = [
            sg.Text(label, size=COLOR_LABEL_SIZE, tooltip=TOOLTIPS[key]),
            sg.ColorChooserButton(
                "",
                target=key,
                key=color_chooser_key(key),
                image_data=pipette_for(default),
                image_size=SWATCH_SIZE,
                button_color=(default, default),
                border_width=1,
                tooltip=f"Click to pick the {label.lower()} colour",
            ),
            sg.Input(
                default,
                key=key,
                size=COLOR_FIELD_SIZE,
                font=FONT_MONO,
                enable_events=True,
                tooltip=TOOLTIPS[key],
            ),
        ]
        if trailing is not None:
            row.extend([sg.Push(), trailing])
        return row

    colors_frame = sg.Frame(
        " Colours ",
        [
            # The hex fields leave close to a hundred pixels spare on every row,
            # which is room enough for the button without a row of its own
            color_row(
                "Dark",
                "-DARK-",
                trailing=sg.Button(
                    "Random",
                    key="-RANDOM_COLORS-",
                    size=(10, 1),
                    tooltip="Pick a random colour scheme that still scans",
                    **BUTTON_SECONDARY,
                ),
            ),
            color_row("Light", "-LIGHT-"),
            color_row("Data dark", "-DATA_DARK-"),
            color_row("Data light", "-DATA_LIGHT-"),
        ],
        font=FONT_FRAME,
        title_color=COLOR_MUTED,
        relief=sg.RELIEF_SOLID,
        border_width=1,
        expand_x=True,
        pad=FRAME_PAD,
        key="-COLORS_FRAME-",
    )
    return code_frame, colors_frame


def build_content_tabs() -> sg.Frame:
    """
    One tab per QRCode type, every input generated from the segno signature
    """
    tabs = []
    for qrcode_type, segno_function in QRCODE_TYPES.items():
        segno_arguments = inspect.getfullargspec(segno_function).args
        argument_defaults = get_argument_defaults(segno_function)

        tab_layout = []
        for segno_argument in segno_arguments:
            element_key = f"-{qrcode_type}_{segno_argument}-"
            tooltip = ARGUMENT_TOOLTIPS.get(
                segno_argument, f"segno argument '{segno_argument}'"
            )
            choices = ARGUMENT_CHOICES.get(segno_argument)
            if choices is not None:
                # A free text field here just invites typos segno would forward
                input_element = sg.Combo(
                    list(choices),
                    default_value=choices[0],
                    key=element_key,
                    size=(28, 1),
                    readonly=True,
                    enable_events=True,
                    tooltip=tooltip,
                )
            elif isinstance(argument_defaults.get(segno_argument), bool):
                # A boolean in a text input would make every typed value truthy,
                # "false" and "no" included
                input_element = sg.Checkbox(
                    "",
                    default=argument_defaults[segno_argument],
                    key=element_key,
                    enable_events=True,
                )
            else:
                input_element = sg.InputText(
                    key=element_key,
                    size=(30, 1),
                    enable_events=True,
                )
            tab_layout.append(
                [
                    sg.Text(
                        prettify_argument(segno_argument),
                        size=LABEL_SIZE,
                        tooltip=tooltip,
                    ),
                    input_element,
                ]
            )

        # Key QRCODE_TYPE will be set in -ACTIVE_TAB- key
        tabs.append(
            sg.Tab(
                f" {qrcode_type} ",
                [
                    [
                        sg.Column(
                            tab_layout,
                            size=TAB_CONTENT_SIZE,
                            # Only the long forms need to scroll, but every tab keeps
                            # the same canvas so the window never jumps around
                            scrollable=len(segno_arguments) > VISIBLE_TAB_ROWS,
                            vertical_scroll_only=True,
                            pad=(8, 8),
                            background_color=COLOR_SURFACE,
                        )
                    ]
                ],
                key=f"{qrcode_type}",
                background_color=COLOR_SURFACE,
            )
        )

    return sg.Frame(
        " Content ",
        [
            [
                sg.TabGroup(
                    [tabs],
                    key="-ACTIVE_TAB-",
                    enable_events=True,
                    font=FONT,
                    border_width=0,
                    tab_background_color=COLOR_SECONDARY,
                    selected_background_color=COLOR_SURFACE,
                    selected_title_color=COLOR_ACCENT,
                    background_color=COLOR_BACKGROUND,
                    pad=(0, 0),
                )
            ]
        ],
        font=FONT_FRAME,
        title_color=COLOR_MUTED,
        relief=sg.RELIEF_SOLID,
        border_width=1,
        vertical_alignment="top",
        pad=((0, 0), (0, 10)),
        key="-CONTENT_FRAME-",
    )


def build_layout() -> list:
    """
    Whole window layout
    """
    code_frame, colors_frame = build_settings_frames()

    # A Graph rather than an Image: a fixed canvas we can draw the code into at
    # a computed position, so the preview stays centred and an oversized code is
    # clipped instead of resizing the whole window
    preview_frame = sg.Frame(
        " Preview ",
        [
            [
                sg.Graph(
                    canvas_size=PREVIEW_SIZE,
                    graph_bottom_left=(0, 0),
                    graph_top_right=PREVIEW_SIZE,
                    key="-OUTPUT-IMAGE-",
                    background_color=COLOR_SURFACE,
                    pad=(0, 0),
                )
            ]
        ],
        font=FONT_FRAME,
        title_color=COLOR_MUTED,
        relief=sg.RELIEF_SOLID,
        border_width=1,
        pad=((0, 0), (0, 10)),
        key="-PREVIEW_FRAME-",
    )

    header = [
        sg.Text("Segno UI", font=FONT_TITLE, pad=((0, 12), (10, 6))),
        sg.Text(
            f"offline QR Code generator   ·   v{__version__}",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
            pad=((0, 0), (18, 6)),
        ),
    ]

    actions = [
        sg.Button(
            "Generate",
            key="-GENERATE-",
            size=(13, 1),
            font=(FONT_FAMILY, 10, "bold"),
            tooltip="Regenerate now and report any problem",
            **BUTTON_PRIMARY,
        ),
        sg.Push(),
        sg.Text("Export as", pad=((0, 4), (0, 0))),
        sg.Combo(
            EXPORT_FORMATS,
            default_value="png",
            key="-EXPORT_FORMAT-",
            size=(7, 1),
            readonly=True,
            enable_events=True,
            tooltip=TOOLTIPS["-EXPORT_FORMAT-"],
        ),
        sg.SaveAs(
            "Save image...",
            target="-EXPORT_FILENAME-",
            size=(13, 1),
            tooltip="Write the code to disk in the format selected on the left",
            **BUTTON_SECONDARY_COLOR,
        ),
        sg.Input("", key="-EXPORT_FILENAME-", enable_events=True, visible=False),
        sg.Button("Quit", key="-EXIT-", size=(8, 1), **BUTTON_SECONDARY),
    ]

    body = [
        sg.Column(
            [[build_content_tabs()], [code_frame]],
            vertical_alignment="top",
            pad=((0, 12), (0, 0)),
        ),
        sg.Column(
            [[preview_frame], [colors_frame]],
            vertical_alignment="top",
            pad=(0, 0),
        ),
    ]

    return [
        [sg.Menu(MENU_DEFINITION, key="-MENU-", font=FONT)],
        [
            sg.Column(
                [header, body, actions],
                pad=((16, 16), (0, 10)),
                expand_x=True,
            )
        ],
        [
            sg.StatusBar(
                STATUS_READY,
                key="-ERROR-TEXT-",
                # StatusBar sizes itself on its initial text, which would clip
                # every message longer than "Ready"
                size=(95, 1),
                text_color=COLOR_MUTED,
                font=FONT_SMALL,
                relief=sg.RELIEF_FLAT,
                justification="left",
                expand_x=True,
                pad=((16, 16), (4, 6)),
            )
        ],
    ]


def gui():
    """
    Main GUI
    """
    apply_theme()

    window = sg.Window(
        f"Segno UI {__version__} - Offline QRCode Generator",
        build_layout(),
        finalize=True,
        resizable=False,
    )
    flatten_scrollbars(window)
    align_panels(window)
    _, values = window.read(timeout=1)
    refresh_color_swatches(window, values)
    sync_mode_availability(window, values)

    while True:
        event, values = window.read()
        if _DEBUG:
            print(event)
        if event in (sg.WIN_CLOSED, "-EXIT-", MENU_EXIT):
            break
        if event == "-GENERATE-":
            autogen(window, values, errors=True)
        elif event == MENU_ABOUT:
            show_about()
        elif event == "-EXPORT_FILENAME-":
            try:
                generate_code(values, save_to=values["-EXPORT_FILENAME-"])
                saved_as = with_extension(
                    values["-EXPORT_FILENAME-"], values["-EXPORT_FORMAT-"]
                )
                set_status(window, f"Image written to {os.path.basename(saved_as)}")
                sg.popup(f"File exported as\n{saved_as}", title="Image exported")
            except Exception as exc:
                sg.popup_error(exc)
                if _DEBUG:
                    raise
        elif event == "-RANDOM_COLORS-":
            for key, color in random_color_scheme().items():
                window[key].update(color)
                values[key] = color
            refresh_color_swatches(window, values)
            autogen(window, values, errors=False)
        elif event == MENU_EXPORT_SETTINGS:
            config_filename = sg.popup_get_file(
                "Export settings",
                save_as=True,
                no_window=True,
                file_types=SETTINGS_FILE_TYPES,
                default_extension=".json",
            )
            if config_filename:
                export_settings(window, values, config_filename)
        elif event == MENU_IMPORT_SETTINGS:
            config_filename = sg.popup_get_file(
                "Import settings",
                no_window=True,
                file_types=SETTINGS_FILE_TYPES,
            )
            if config_filename and import_settings(window, config_filename):
                # Reload values so we may generate the qrcode
                _, values = window.read(timeout=1)
                sync_ecc_levels(window, values)
                sync_mode_availability(window, values)
                refresh_color_swatches(window, values)
                autogen(window, values)
        else:
            if event == "-QRCODE_FORMAT-":
                sync_ecc_levels(window, values)
            elif event == "-ACTIVE_TAB-":
                sync_mode_availability(window, values)
            elif event in COLOR_INPUT_KEYS:
                refresh_color_swatches(window, values)
            # Let's just try to wildly "autogenerate" when an event happens, and not do anything if generation is not succesful
            autogen(window, values, errors=False)
    window.close()


def autogen(window, values, errors=False):
    """
    Generate QRCode and update GUI
    """
    if not has_content(values):
        # An empty tab has nothing to show and nothing to complain about. Clear
        # the preview too, or it keeps showing the code of the tab we just left
        window["-OUTPUT-IMAGE-"].erase()
        set_status(window, STATUS_EMPTY)
        if errors:
            sg.popup(STATUS_EMPTY, title="Nothing to encode")
        return
    try:
        qrcode, segno_export_opts = build_qrcode(values)
        preview_scale = draw_preview(window, qrcode, segno_export_opts)
        status = describe_qrcode(qrcode)
        if preview_scale != segno_export_opts["scale"]:
            # The export still uses the scale that was asked for, say so rather
            # than letting the preview quietly lie about the size
            status += f"  -  preview shrunk to scale {preview_scale} to fit"
        set_status(window, status)
    except Exception as exc:
        if errors:
            sg.popup_error(exc)
            if _DEBUG:
                raise
        else:
            print(f"Autogen: {exc}")
            set_status(window, str(exc), error=True)


def main():
    """
    Parse command line and launch the GUI
    """
    global _DEBUG

    parser = argparse.ArgumentParser(
        prog=__intname__,
        description=__description__,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{__intname__} v{__version__}-{__build__} - {__licence__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Log events and re-raise errors instead of only showing them",
    )
    args = parser.parse_args()
    _DEBUG = args.debug
    gui()


if __name__ == "__main__":
    main()
