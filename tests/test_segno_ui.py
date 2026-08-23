#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
#
# This file is part of segno_ui

"""
Non graphical tests

Nothing here may build a real sg.Window, so the suite stays runnable on a CI
runner without any display server
"""

__intname__ = "segno_ui.tests"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2026 Orsiris de Jong - NetInvent"
__licence__ = "BSD 3 Clause"


import colorsys
import inspect
import json
import os
import random
import sys

import pytest
import segno
import segno.helpers

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from segno_ui import segno_ui as app

# The eight byte header every PNG starts with
PNG_SIGNATURE = bytes([137, 80, 78, 71, 13, 10, 26, 10])


class FakeElement:
    """
    Stands in for a FreeSimpleGUI element, recording whatever the app sets on it
    """

    def __init__(self, value=None):
        self.value = value
        self.values = None
        self.selected = False
        self.disabled = None
        self.button_color = None
        self.text_color = None
        self.image_data = None
        self.image_size = None

    def update(
        self, value=None, values=None, disabled=None, button_color=None, **kwargs
    ):
        if value is not None:
            self.value = value
        if values is not None:
            self.values = values
        if disabled is not None:
            self.disabled = disabled
        if button_color is not None:
            self.button_color = button_color
        if kwargs.get("text_color") is not None:
            self.text_color = kwargs["text_color"]
        if kwargs.get("image_data") is not None:
            self.image_data = kwargs["image_data"]
        if kwargs.get("image_size") is not None:
            self.image_size = kwargs["image_size"]

    def select(self):
        self.selected = True

    # Graph surface, so draw_preview() can be checked without a real canvas
    def erase(self):
        self.drawn = []

    def draw_image(self, data=None, location=None):
        if not hasattr(self, "drawn"):
            self.drawn = []
        self.drawn.append((data, location))
        return len(self.drawn)


class FakeWindow:
    """
    Stands in for a FreeSimpleGUI window, exposing the AllKeysDict the app looks at
    """

    def __init__(self, keys):
        self.AllKeysDict = {key: FakeElement() for key in keys}

    def __getitem__(self, key):
        return self.AllKeysDict[key]


def make_values(active_tab="Generic", overrides=None):
    """
    Build the values dict FreeSimpleGUI hands over for a freshly opened window
    """
    values = {
        "-ERROR-": "15%",
        "-DARK-": "#000000",
        "-LIGHT-": "#FFFFFF",
        "-DATA_DARK-": "#000000",
        "-DATA_LIGHT-": "#FFFFFF",
        "-SCALE-": 2,
        "-BORDER-": 1,
        "-QRCODE_FORMAT-": app.STANDARD_QRCODE_FORMAT,
        "-ACTIVE_TAB-": active_tab,
        "-EXPORT_FORMAT-": "png",
    }
    for qrcode_type, segno_function in app.QRCODE_TYPES.items():
        defaults = app.get_argument_defaults(segno_function)
        for argument in inspect.getfullargspec(segno_function).args:
            is_boolean = isinstance(defaults.get(argument), bool)
            values[f"-{qrcode_type}_{argument}-"] = False if is_boolean else ""
    values.update(overrides or {})
    return values


def make_window():
    """
    A fake window holding every key the real layout declares
    """
    keys = list(make_values().keys()) + list(app.QRCODE_TYPES.keys())
    keys.extend(("-ERROR-TEXT-", "-OUTPUT-IMAGE-"))
    keys.extend(app.color_chooser_key(key) for key in app.COLOR_INPUT_KEYS)
    return FakeWindow(keys)


def find_layout_element(layout, wanted_key):
    """
    Walk a FreeSimpleGUI layout and return the element carrying this key
    """
    for row in layout:
        for element in row:
            if getattr(element, "Key", None) == wanted_key:
                return element
            rows = getattr(element, "Rows", None)
            if rows:
                found = find_layout_element(rows, wanted_key)
                if found is not None:
                    return found
    return None


def collect_layout_keys(layout):
    """
    Walk a FreeSimpleGUI layout and return every key it declares, duplicates kept
    """
    keys = []
    for row in layout:
        for element in row:
            key = getattr(element, "Key", None)
            if key is not None:
                keys.append(key)
            rows = getattr(element, "Rows", None)
            if rows:
                keys.extend(collect_layout_keys(rows))
    return keys


TAB_SAMPLES = [
    ("Generic", {"-Generic_content-": "https://example.com"}),
    ("vCard", {"-vCard_name-": "Doe;John", "-vCard_displayname-": "John Doe"}),
    ("MeCard", {"-MeCard_name-": "Doe,John"}),
    ("Email", {"-Email_to-": "john@example.com", "-Email_subject-": "Hello"}),
    ("Geo", {"-Geo_lat-": "48.8566", "-Geo_lng-": "2.3522"}),
    (
        "Wifi",
        {
            "-Wifi_ssid-": "MyNet",
            "-Wifi_password-": "secret",
            "-Wifi_security-": "WPA",
        },
    ),
    (
        "EPC",
        {
            "-EPC_name-": "Acme",
            "-EPC_iban-": "FR7630006000011234567890189",
            "-EPC_amount-": "12.50",
            "-EPC_text-": "Invoice 1",
        },
    ),
]


@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_every_tab_generates(qrcode_type, fields):
    """
    Every QRCode type must yield PNG data, EPC included
    """
    data = app.generate_code(make_values(qrcode_type, fields))
    assert isinstance(data, str)
    assert data


def test_epc_helper_is_not_fed_back_into_make_qr():
    """
    make_epc_qr() returns a QRCode, feeding it to make_qr() raises TypeError
    """
    assert "EPC" in app.SELF_MAKING_QRCODE_TYPES
    epc = segno.helpers.make_epc_qr(
        name="Acme", iban="FR7630006000011234567890189", amount="12.50", text="Inv"
    )
    assert isinstance(epc, segno.QRCode)
    with pytest.raises(TypeError):
        segno.make_qr(epc)


@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
@pytest.mark.parametrize("export_format", ["png", "svg", "eps", "pdf"])
def test_every_tab_exports_to_every_format(
    qrcode_type, fields, export_format, tmp_path
):
    """
    Saving to disk must work for every combination the GUI offers
    """
    values = make_values(qrcode_type, fields)
    values["-EXPORT_FORMAT-"] = export_format
    target = str(tmp_path / "qrcode")
    assert app.generate_code(values, save_to=target) is None
    assert os.path.getsize(f"{target}.{export_format}") > 0


def test_data_light_falls_back_to_white():
    """
    Clearing the colour inputs must not produce a dark on dark, unreadable code
    """
    values = make_values()
    for key in ("-DARK-", "-LIGHT-", "-DATA_DARK-", "-DATA_LIGHT-"):
        values[key] = ""
    _, export_opts, _ = app.get_conf_from_gui(values)
    assert export_opts["dark"] == "#000000"
    assert export_opts["light"] == "#FFFFFF"
    assert export_opts["data_dark"] == "#000000"
    assert export_opts["data_light"] == "#FFFFFF"


@pytest.mark.parametrize(
    "filename, extension, expected",
    [
        # Nothing to do, the extension is already there
        ("qrcode.png", "png", "qrcode.png"),
        ("qrcode.PNG", "png", "qrcode.PNG"),
        # Plain append
        ("qrcode", "png", "qrcode.png"),
        ("settings", "json", "settings.json"),
        # A dot in a directory name must not truncate the path
        (
            os.path.join("C:", "Users", "John.Doe", "qrcode"),
            "json",
            os.path.join("C:", "Users", "John.Doe", "qrcode.json"),
        ),
        (
            os.path.join("C:", "proj", "v1.0", "qrcode"),
            "png",
            os.path.join("C:", "proj", "v1.0", "qrcode.png"),
        ),
        # A different extension is kept, ours is appended
        ("logo.v2", "svg", "logo.v2.svg"),
        ("my.backup.json", "json", "my.backup.json"),
    ],
)
def test_with_extension(filename, extension, expected):
    assert app.with_extension(filename, extension) == expected


def test_settings_round_trip(tmp_path):
    """
    Everything the user changed must come back after a save and load cycle
    """
    values = make_values(
        "vCard",
        {
            "-ERROR-": "25%",
            "-SCALE-": 6,
            "-BORDER-": 4,
            "-DARK-": "#112233",
            "-LIGHT-": "#EEDDCC",
            "-DATA_DARK-": "#445566",
            "-DATA_LIGHT-": "#AABBCC",
            "-QRCODE_FORMAT-": app.STANDARD_QRCODE_FORMAT,
            "-EXPORT_FORMAT-": "svg",
            "-vCard_name-": "Doe;John",
        },
    )

    config = {"software": {"name": app.__intname__, "version": app.__version__}}
    config["data"] = app.get_segno_arguments_from_gui(values)
    (
        config["segno_make_opts"],
        config["segno_export_opts"],
        config["misc_opts"],
    ) = app.get_conf_from_gui(values)

    # Must survive a trip through JSON
    config = json.loads(json.dumps(config))

    window = make_window()
    assert app.fill_gui_from_segno_arguments(config, window) is True

    assert window["-ERROR-"].value == "25%"
    assert window["-SCALE-"].value == 6
    assert window["-BORDER-"].value == 4
    assert window["-DARK-"].value == "#112233"
    assert window["-LIGHT-"].value == "#EEDDCC"
    assert window["-DATA_DARK-"].value == "#445566"
    assert window["-DATA_LIGHT-"].value == "#AABBCC"
    assert window["-vCard_name-"].value == "Doe;John"
    # The export format used to be dropped on the floor
    assert window["-EXPORT_FORMAT-"].value == "svg"
    # active_tab selects a Tab, it is not an element update
    assert window["vCard"].selected is True


def test_settings_file_from_an_older_version_still_loads():
    """
    A settings file written before EPC existed must not abort the whole import
    """
    old_config = {
        "software": {"name": "segno_ui", "version": "1.0.1"},
        "data": {
            "Generic": {"content": "hello"},
            "vCard": {},
            "MeCard": {},
            "Email": {},
            "Geo": {},
            "Wifi": {},
            # no "EPC" key, and no "export_format" in misc_opts
        },
        "segno_make_opts": {"error": "M", "boost_error": False},
        "segno_export_opts": {
            "dark": "#000000",
            "light": "#FFFFFF",
            "scale": 2,
            "border": 1,
        },
        "misc_opts": {"qrcode_format": "Standard QR Code", "active_tab": "Generic"},
    }
    window = make_window()
    assert app.fill_gui_from_segno_arguments(old_config, window) is True
    assert window["-Generic_content-"].value == "hello"
    assert window["-ERROR-"].value == "15%"


def test_settings_file_from_another_software_is_rejected():
    window = make_window()
    assert (
        app.fill_gui_from_segno_arguments({"software": {"name": "something"}}, window)
        is False
    )
    assert app.fill_gui_from_segno_arguments({}, window) is False


def test_unknown_keys_in_settings_do_not_abort_the_import():
    """
    A parameter segno has since renamed must be skipped, not crash the import
    """
    config = {
        "software": {"name": "segno_ui", "version": "9.9.9"},
        "segno_export_opts": {"dark": "#010203", "some_future_option": "whatever"},
        "misc_opts": {"active_tab": "NoSuchTab"},
        "data": {"Generic": {"content": "hi", "future_argument": "x"}},
    }
    window = make_window()
    assert app.fill_gui_from_segno_arguments(config, window) is True
    assert window["-DARK-"].value == "#010203"
    assert window["-Generic_content-"].value == "hi"


def test_wifi_hidden_is_exposed_as_a_boolean():
    """
    'hidden' has a bool default, so the GUI renders a checkbox rather than a text
    input where "false" would have been truthy
    """
    defaults = app.get_argument_defaults(segno.helpers.make_wifi_data)
    assert defaults["hidden"] is False

    base = {
        "-Wifi_ssid-": "MyNet",
        "-Wifi_password-": "secret",
        "-Wifi_security-": "WPA",
    }
    unchecked = dict(base, **{"-Wifi_hidden-": False})
    checked = dict(base, **{"-Wifi_hidden-": True})

    assert (
        "hidden"
        not in app.get_segno_arguments_from_gui(make_values("Wifi", unchecked))["Wifi"]
    )
    assert (
        app.get_segno_arguments_from_gui(make_values("Wifi", checked))["Wifi"]["hidden"]
        is True
    )


def test_micro_qrcode_ecc_levels_are_restricted():
    """
    segno refuses error correction level H on Micro QR Codes, so we must not offer it
    """
    for level in app.MICRO_UNSUPPORTED_ECC_LEVELS:
        with pytest.raises(ValueError):
            segno.make_micro("hi", error=app.ecc_levels[level], boost_error=False)

    window = make_window()
    values = make_values()
    values["-QRCODE_FORMAT-"] = app.MICRO_QRCODE_FORMAT
    values["-ERROR-"] = "33%"
    app.sync_ecc_levels(window, values)
    assert "33%" not in window["-ERROR-"].values
    # An unavailable selection must be pulled back to the strongest one that works
    assert values["-ERROR-"] == "25%"
    assert window["-ERROR-"].value == "25%"

    values["-QRCODE_FORMAT-"] = app.STANDARD_QRCODE_FORMAT
    app.sync_ecc_levels(window, values)
    assert window["-ERROR-"].values == list(app.ecc_levels.keys())
    # A valid selection is left alone
    assert values["-ERROR-"] == "25%"


@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_every_micro_ecc_level_offered_is_usable(qrcode_type, fields):
    """
    Whatever the mode, the GUI must never offer a level that raises
    """
    if qrcode_type in app.SELF_MAKING_QRCODE_TYPES:
        pytest.skip("EPC imposes its own error correction level")
    for level in app.ecc_levels:
        if level in app.MICRO_UNSUPPORTED_ECC_LEVELS:
            continue
        # Short payload so it fits a Micro QR Code
        segno.make_micro("hi", error=app.ecc_levels[level], boost_error=False)


def test_contains_secrets():
    values = make_values("Wifi", {"-Wifi_ssid-": "MyNet", "-Wifi_security-": "WPA"})
    config = {"data": app.get_segno_arguments_from_gui(values)}
    assert app.contains_secrets(config) is False

    values["-Wifi_password-"] = "secret"
    config = {"data": app.get_segno_arguments_from_gui(values)}
    assert app.contains_secrets(config) is True


def test_package_exports_its_public_api():
    """
    "import segno_ui" used to give an empty namespace
    """
    import segno_ui as package

    assert package.__version__ == app.__version__
    assert callable(package.gui)
    assert callable(package.generate_code)
    assert callable(package.main)


def test_geo_arguments_are_converted_to_floats():
    data = app.get_segno_arguments_from_gui(
        make_values("Geo", {"-Geo_lat-": "48.8566", "-Geo_lng-": "2.3522"})
    )
    assert data["Geo"] == {"lat": 48.8566, "lng": 2.3522}


###############################################################################
# Window layout
###############################################################################


def test_layout_builds():
    """
    Building the layout must not raise

    Every element takes a slightly different set of styling arguments, and only
    actually constructing them proves we passed the right ones
    """
    app.apply_theme()
    assert app.build_layout()


def test_layout_declares_every_key_the_settings_format_needs():
    """
    A settings file addresses elements by key, so the layout has to carry them all
    """
    app.apply_theme()
    keys = set(collect_layout_keys(app.build_layout()))

    for key in make_values():
        assert key in keys, f"{key} missing from the layout"
    for key in app.COLOR_INPUT_KEYS:
        assert app.color_chooser_key(key) in keys
    for qrcode_type, segno_function in app.QRCODE_TYPES.items():
        assert qrcode_type in keys
        for argument in inspect.getfullargspec(segno_function).args:
            assert f"-{qrcode_type}_{argument}-" in keys
    assert "-OUTPUT-IMAGE-" in keys
    assert "-ERROR-TEXT-" in keys


def test_layout_has_no_duplicate_keys():
    """
    Four colour pickers once shared a single key and FreeSimpleGUI quietly
    renamed three of them
    """
    app.apply_theme()
    keys = collect_layout_keys(app.build_layout())
    duplicates = {key for key in keys if keys.count(key) > 1}
    assert not duplicates, f"duplicate keys in layout: {duplicates}"


###############################################################################
# Presentation helpers
###############################################################################


@pytest.mark.parametrize(
    "argument, expected",
    [
        ("lat", "Latitude"),
        ("lng", "Longitude"),
        ("displayname", "Display name"),
        ("photo_uri", "Photo URI"),
        ("iban", "IBAN"),
        ("ssid", "Network name"),
        # Not in the table, so fall back to a readable default
        ("content", "Content"),
        ("reference", "Reference"),
        ("boost_error", "Boost error"),
    ],
)
def test_prettify_argument(argument, expected):
    assert app.prettify_argument(argument) == expected


def test_every_segno_argument_gets_a_label():
    for segno_function in app.QRCODE_TYPES.values():
        for argument in inspect.getfullargspec(segno_function).args:
            label = app.prettify_argument(argument)
            assert label and not label.startswith("_") and "_" not in label


def test_color_chooser_key():
    assert app.color_chooser_key("-DARK-") == "-DARK_CHOOSER-"
    assert app.color_chooser_key("-DATA_LIGHT-") == "-DATA_LIGHT_CHOOSER-"


def test_describe_qrcode():
    qrcode = segno.make_qr("hello", error="M", boost_error=False)
    description = app.describe_qrcode(qrcode)
    assert "QR Code" in description
    assert "21x21 modules" in description
    assert "error correction M" in description

    micro = segno.make_micro("hi", error="L", boost_error=False)
    assert app.describe_qrcode(micro).startswith("Micro QR Code")


def test_refresh_color_swatches_mirrors_inputs():
    window = make_window()
    values = make_values(overrides={"-DARK-": "#112233", "-LIGHT-": ""})
    app.refresh_color_swatches(window, values)
    assert window[app.color_chooser_key("-DARK-")].button_color == (
        "#112233",
        "#112233",
    )
    # An empty input falls back to the documented default rather than going blank
    assert window[app.color_chooser_key("-LIGHT-")].button_color == (
        "#FFFFFF",
        "#FFFFFF",
    )


def test_sync_mode_availability_greys_out_what_epc_imposes():
    window = make_window()
    app.sync_mode_availability(window, make_values("EPC"))
    assert window["-QRCODE_FORMAT-"].disabled is True
    assert window["-ERROR-"].disabled is True

    app.sync_mode_availability(window, make_values("Generic"))
    assert window["-QRCODE_FORMAT-"].disabled is False
    assert window["-ERROR-"].disabled is False


def test_set_status():
    window = make_window()
    app.set_status(window)
    assert window["-ERROR-TEXT-"].value == app.STATUS_READY
    assert window["-ERROR-TEXT-"].text_color == app.COLOR_MUTED

    app.set_status(window, "it broke", error=True)
    assert window["-ERROR-TEXT-"].value == "it broke"
    assert window["-ERROR-TEXT-"].text_color == app.COLOR_DANGER


###############################################################################
# Settings files
###############################################################################


def test_export_then_import_settings(tmp_path, no_gui_popups):
    """
    A settings file written by the app must load back into it
    """
    window = make_window()
    values = make_values(
        "Wifi",
        {
            "-ERROR-": "25%",
            "-SCALE-": 6,
            "-DARK-": "#112233",
            "-EXPORT_FORMAT-": "svg",
            "-Wifi_ssid-": "MyNet",
            "-Wifi_password-": "secret",
            "-Wifi_security-": "WPA",
        },
    )
    target = str(tmp_path / "preset")

    assert app.export_settings(window, values, target) is True
    written = tmp_path / "preset.json"
    assert written.is_file()
    # A password in the preset must be called out before it lands on disk
    assert any("clear text" in str(message) for message in no_gui_popups)

    saved = json.loads(written.read_text(encoding="utf-8"))
    assert saved["software"]["name"] == "segno_ui"
    assert saved["data"]["Wifi"]["ssid"] == "MyNet"

    fresh = make_window()
    assert app.import_settings(fresh, str(written)) is True
    assert fresh["-ERROR-"].value == "25%"
    assert fresh["-SCALE-"].value == 6
    assert fresh["-DARK-"].value == "#112233"
    assert fresh["-EXPORT_FORMAT-"].value == "svg"
    assert fresh["-Wifi_ssid-"].value == "MyNet"
    assert fresh["Wifi"].selected is True


def test_export_settings_without_password_does_not_warn(tmp_path, no_gui_popups):
    window = make_window()
    values = make_values("Generic", {"-Generic_content-": "https://example.com"})
    assert app.export_settings(window, values, str(tmp_path / "preset.json")) is True
    assert not any("clear text" in str(message) for message in no_gui_popups)


def test_import_settings_reports_a_missing_file(tmp_path, no_gui_popups):
    window = make_window()
    assert app.import_settings(window, str(tmp_path / "nope.json")) is False
    assert no_gui_popups


def test_import_settings_reports_broken_json(tmp_path, no_gui_popups):
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")
    window = make_window()
    assert app.import_settings(window, str(broken)) is False
    assert no_gui_popups


###############################################################################
# Preview
###############################################################################


def preview_case(qrcode_type, fields, scale, border=1):
    """
    Build a code the way the GUI would, then draw it into a fake canvas
    """
    window = make_window()
    values = make_values(
        qrcode_type, dict(fields, **{"-SCALE-": scale, "-BORDER-": border})
    )
    qrcode, export_opts = app.build_qrcode(values)
    used_scale = app.draw_preview(window, qrcode, export_opts)
    _, location = window["-OUTPUT-IMAGE-"].drawn[-1]
    width, height = qrcode.symbol_size(scale=used_scale, border=border)
    return used_scale, location, (width, height)


@pytest.mark.parametrize("scale", app.scales)
@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_preview_stays_centred_at_every_scale(qrcode_type, fields, scale):
    """
    The preview used to drift into the top left corner once the code outgrew the
    canvas, because the offsets were clamped to zero
    """
    canvas_width, canvas_height = app.PREVIEW_SIZE
    _, (left, top), (width, height) = preview_case(qrcode_type, fields, scale)

    # draw_image places the top left corner, graph coordinates start bottom left
    centre_x = left + width / 2
    centre_y = top - height / 2
    assert (
        abs(centre_x - canvas_width / 2) <= 0.5
    ), f"off centre horizontally at scale {scale}"
    assert (
        abs(centre_y - canvas_height / 2) <= 0.5
    ), f"off centre vertically at scale {scale}"


@pytest.mark.parametrize("scale", app.scales)
@pytest.mark.parametrize("border", [1, 5, 10])
@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_preview_is_never_clipped(qrcode_type, fields, scale, border):
    """
    Whatever the scale and border, the whole code has to be visible
    """
    canvas_width, canvas_height = app.PREVIEW_SIZE
    _, (left, top), (width, height) = preview_case(qrcode_type, fields, scale, border)
    assert left >= 0
    assert top <= canvas_height
    assert left + width <= canvas_width
    assert top - height >= 0


def test_preview_only_shrinks_never_enlarges():
    """
    A code that already fits must be drawn at the scale the user asked for
    """
    fields = {"-Generic_content-": "hi"}
    for scale in app.scales:
        used, _, _ = preview_case("Generic", fields, scale)
        assert used == scale, f"a tiny code should not be rescaled, {scale} -> {used}"


def test_preview_shrinks_an_oversized_code():
    """
    A big vCard at the largest scale does not fit, and must come back smaller
    """
    fields = dict(TAB_SAMPLES[1][1])
    fields["-vCard_email-"] = "orsiris.de.jong@netinvent.example.org"
    fields["-vCard_memo-"] = "A memo long enough to push the version up a notch"
    used, _, (width, height) = preview_case("vCard", fields, 8)
    assert used < 8
    assert width <= app.PREVIEW_SIZE[0] and height <= app.PREVIEW_SIZE[1]


def test_fit_preview_scale_never_goes_below_one():
    """
    Scale 1 always fits, the biggest symbol being 177 modules wide
    """
    qrcode = segno.make_qr("x" * 1200, error="L", boost_error=False)
    assert qrcode.symbol_size(scale=1, border=0)[0] > 100
    assert app.fit_preview_scale(qrcode, 8, 10) >= 1


def test_scale_and_border_are_coerced_to_numbers():
    """
    A hand edited settings file may spell them as strings
    """
    values = make_values(
        "Generic", {"-Generic_content-": "hi", "-SCALE-": "3", "-BORDER-": "2"}
    )
    _, export_opts, _ = app.get_conf_from_gui(values)
    assert export_opts["scale"] == 3
    assert export_opts["border"] == 2


###############################################################################
# Application icon
###############################################################################


def test_icon_is_a_valid_png():
    """
    tkinter refuses anything it cannot decode, so the payload has to be sound
    """
    import base64

    raw = base64.b64decode(app.ICON_BASE64)
    assert raw.startswith(PNG_SIGNATURE), "not a PNG"
    # IHDR carries the dimensions, big endian, right after the 8 byte signature
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    assert width == height, f"icon should be square, got {width}x{height}"
    assert width >= 32, f"icon too small to scale down nicely: {width}px"


def test_panel_pairs_are_declared_in_the_layout():
    """
    align_panels() looks these four up by key once the window exists, so a rename
    would surface as a KeyError in front of the user rather than at build time
    """
    app.apply_theme()
    keys = set(collect_layout_keys(app.build_layout()))
    for pair in app.PANEL_PAIRS:
        assert len(pair) == 2
        for key in pair:
            assert key in keys, f"{key} missing from the layout"


def test_panel_pairs_cover_all_four_panels():
    flat = [key for pair in app.PANEL_PAIRS for key in pair]
    assert sorted(flat) == [
        "-CODE_FRAME-",
        "-COLORS_FRAME-",
        "-CONTENT_FRAME-",
        "-PREVIEW_FRAME-",
    ]
    assert len(set(flat)) == 4


###############################################################################
# Wifi security selector
###############################################################################


def test_wifi_security_is_a_selector_not_a_text_field():
    """
    segno forwards whatever it is given, only uppercasing it, so a typo used to
    travel straight into the code
    """
    app.apply_theme()
    element = find_layout_element(app.build_layout(), "-Wifi_security-")
    assert element is not None
    assert type(element).__name__ == "Combo", type(element).__name__
    assert element.Readonly is True
    assert tuple(element.Values) == app.ARGUMENT_CHOICES["security"]


def test_security_selector_defaults_to_leaving_the_field_out():
    """
    Same as before the selector existed: nothing chosen means no T: in the code
    """
    app.apply_theme()
    element = find_layout_element(app.build_layout(), "-Wifi_security-")
    assert element.DefaultValue == ""


@pytest.mark.parametrize("security", app.ARGUMENT_CHOICES["security"])
def test_every_offered_security_value_is_usable(security):
    """
    Every entry in the list has to produce a code, and the token a scanner expects
    """
    values = make_values(
        "Wifi",
        {
            "-Wifi_ssid-": "MyNet",
            "-Wifi_password-": "s3cret",
            "-Wifi_security-": security,
        },
    )
    arguments = app.get_segno_arguments_from_gui(values)["Wifi"]
    payload = segno.helpers.make_wifi_data(**arguments)
    if security:
        # segno uppercases everything except the literal "nopass"
        expected = security if security == "nopass" else security.upper()
        assert f"T:{expected};" in payload
    else:
        assert "T:" not in payload
    assert app.generate_code(values)


def test_other_free_text_fields_are_left_alone():
    """
    Only the arguments listed in ARGUMENT_CHOICES become selectors
    """
    app.apply_theme()
    layout = app.build_layout()
    assert type(find_layout_element(layout, "-Wifi_ssid-")).__name__ == "Input"
    assert type(find_layout_element(layout, "-Wifi_password-")).__name__ == "Input"
    assert type(find_layout_element(layout, "-Wifi_hidden-")).__name__ == "Checkbox"


def test_security_from_an_older_preset_is_still_restored():
    """
    A preset written when the field was free text may hold anything at all
    """
    config = {
        "software": {"name": "segno_ui", "version": "1.0.5"},
        "data": {"Wifi": {"ssid": "MyNet", "security": "wpa-legacy"}},
    }
    window = make_window()
    assert app.fill_gui_from_segno_arguments(config, window) is True
    assert window["-Wifi_security-"].value == "wpa-legacy"


def test_argument_choices_only_names_real_segno_arguments():
    """
    A renamed segno argument would leave a selector wired to nothing
    """
    every_argument = set()
    for segno_function in app.QRCODE_TYPES.values():
        every_argument.update(inspect.getfullargspec(segno_function).args)
    for argument in app.ARGUMENT_CHOICES:
        assert argument in every_argument, f"{argument} is not a segno argument"
    for argument in app.ARGUMENT_TOOLTIPS:
        assert argument in every_argument, f"{argument} is not a segno argument"


###############################################################################
# Empty tabs stay quiet
###############################################################################


@pytest.mark.parametrize("qrcode_type", list(app.QRCODE_TYPES))
def test_untouched_tab_has_no_content(qrcode_type):
    assert app.has_content(make_values(qrcode_type)) is False


@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_a_filled_tab_has_content(qrcode_type, fields):
    assert app.has_content(make_values(qrcode_type, fields)) is True


def test_a_ticked_checkbox_counts_as_content():
    assert app.has_content(make_values("Wifi", {"-Wifi_hidden-": True})) is True


def test_a_chosen_security_counts_as_content():
    assert app.has_content(make_values("Wifi", {"-Wifi_security-": "WPA"})) is True


@pytest.mark.parametrize("qrcode_type", list(app.QRCODE_TYPES))
def test_switching_to_an_untouched_tab_reports_no_error(qrcode_type):
    """
    Every segno helper but the Generic one raises a TypeError when called with
    nothing, and that used to land in the status bar on a mere tab change
    """
    window = make_window()
    app.autogen(window, make_values(qrcode_type), errors=False)
    status = window["-ERROR-TEXT-"]
    assert status.value == app.STATUS_EMPTY
    # Muted, not the red used for real problems
    assert status.text_color == app.COLOR_MUTED


@pytest.mark.parametrize("qrcode_type", list(app.QRCODE_TYPES))
def test_an_untouched_tab_clears_the_preview(qrcode_type):
    """
    Otherwise the preview keeps showing the code belonging to the previous tab
    """
    window = make_window()
    # Draw something first, the way the tab we are leaving would have
    app.autogen(window, make_values("Generic", {"-Generic_content-": "hi"}))
    assert window["-OUTPUT-IMAGE-"].drawn

    app.autogen(window, make_values(qrcode_type), errors=False)
    assert window["-OUTPUT-IMAGE-"].drawn == []


def test_the_error_comes_back_once_something_is_typed():
    """
    A half filled tab is a real problem the user can act on, so it must be shown
    """
    window = make_window()
    app.autogen(window, make_values("vCard", {"-vCard_name-": "D"}), errors=False)
    status = window["-ERROR-TEXT-"]
    assert "displayname" in status.value
    assert status.text_color == app.COLOR_DANGER


def test_generate_on_an_empty_tab_says_why_nothing_happened(no_gui_popups):
    """
    Pressing Generate deserves an answer rather than silence
    """
    window = make_window()
    app.autogen(window, make_values("vCard"), errors=True)
    assert any(app.STATUS_EMPTY in str(message) for message in no_gui_popups)


def test_an_empty_generic_tab_no_longer_encodes_the_empty_string():
    """
    Generic has no required argument, so it used to happily build a QR Code of
    nothing at all
    """
    window = make_window()
    app.autogen(window, make_values("Generic"), errors=False)
    assert window["-ERROR-TEXT-"].value == app.STATUS_EMPTY
    assert window["-OUTPUT-IMAGE-"].drawn == []


###############################################################################
# Colours
###############################################################################


@pytest.mark.parametrize(
    "color, expected",
    [
        ("#000000", (0, 0, 0)),
        ("#FFFFFF", (255, 255, 255)),
        ("#2563EB", (0x25, 0x63, 0xEB)),
        ("2563EB", (0x25, 0x63, 0xEB)),
        ("#abc", (0xAA, 0xBB, 0xCC)),
        ("  #FFFFFF  ", (255, 255, 255)),
    ],
)
def test_parse_color(color, expected):
    assert app.parse_color(color) == expected


@pytest.mark.parametrize("color", ["", "#12", "#GGGGGG", "nonsense", "#1234567"])
def test_parse_color_rejects_rubbish(color):
    with pytest.raises(ValueError):
        app.parse_color(color)


def test_relative_luminance_endpoints():
    assert app.relative_luminance("#000000") == pytest.approx(0.0)
    assert app.relative_luminance("#FFFFFF") == pytest.approx(1.0)


def test_contrast_ratio_endpoints():
    # The two extremes of the WCAG scale
    assert app.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert app.contrast_ratio("#2563EB", "#2563EB") == pytest.approx(1.0)
    # Order must not matter
    assert app.contrast_ratio("#000000", "#FFFFFF") == app.contrast_ratio(
        "#FFFFFF", "#000000"
    )


def test_hsl_to_hex():
    assert app.hsl_to_hex(0.0, 0.0, 0.0) == "#000000"
    assert app.hsl_to_hex(0.0, 0.0, 1.0) == "#FFFFFF"
    assert app.hsl_to_hex(0.0, 1.0, 0.5) == "#FF0000"


def test_random_scheme_always_clears_the_contrast_floor():
    """
    Random RGB would hand back mid grey on mid grey. Every draw has to be a code
    that can actually be read
    """
    rng = random.Random(20260824)
    for _ in range(2000):
        scheme = app.random_color_scheme(rng)
        assert set(scheme) == set(app.COLOR_INPUT_KEYS)
        for key in app.COLOR_INPUT_KEYS:
            app.parse_color(scheme[key])
        for dark_key in ("-DARK-", "-DATA_DARK-"):
            ratio = app.contrast_ratio(scheme[dark_key], scheme["-LIGHT-"])
            assert ratio >= app.MIN_CONTRAST_RATIO, f"{scheme} only reached {ratio:.2f}"


def test_random_scheme_keeps_the_light_end_pale():
    """
    A tinted background is what actually limits a coloured code, so the light end
    stays close to white while the dark end may be as saturated as it likes
    """
    rng = random.Random(4)
    for _ in range(500):
        scheme = app.random_color_scheme(rng)
        assert app.relative_luminance(scheme["-LIGHT-"]) > 0.85
        assert app.relative_luminance(scheme["-DARK-"]) < 0.20


def test_random_scheme_is_reproducible_from_a_seed():
    assert app.random_color_scheme(random.Random(99)) == app.random_color_scheme(
        random.Random(99)
    )


def test_random_scheme_actually_varies():
    rng = random.Random(5)
    seen = {app.random_color_scheme(rng)["-DARK-"] for _ in range(200)}
    assert len(seen) > 150, f"only {len(seen)} distinct dark colours in 200 draws"


def test_random_scheme_paints_both_light_fields_the_same():
    """
    The two tone effect is in the dark modules, a second background colour would
    only eat into the contrast budget
    """
    rng = random.Random(11)
    for _ in range(100):
        scheme = app.random_color_scheme(rng)
        assert scheme["-LIGHT-"] == scheme["-DATA_LIGHT-"]
        assert scheme["-DARK-"] != scheme["-DATA_LIGHT-"]


def test_pipette_shade_follows_the_swatch():
    """
    The eyedropper has to stay visible whatever colour it is sitting on
    """
    assert app.pipette_for("#FFFFFF") == app.PIPETTE_DARK_BASE64
    assert app.pipette_for("#000000") == app.PIPETTE_LIGHT_BASE64
    for _ in range(200):
        scheme = app.random_color_scheme(random.Random())
        for key in app.COLOR_INPUT_KEYS:
            color = scheme[key]
            glyph = app.pipette_for(color)
            ink = app.PIPETTE_INK if glyph == app.PIPETTE_DARK_BASE64 else "#FFFFFF"
            other = "#FFFFFF" if ink == app.PIPETTE_INK else app.PIPETTE_INK
            assert app.contrast_ratio(color, ink) >= app.contrast_ratio(color, other)


def test_pipette_glyphs_are_valid_pngs():
    import base64

    for payload in (app.PIPETTE_LIGHT_BASE64, app.PIPETTE_DARK_BASE64):
        raw = base64.b64decode(payload)
        # Spelled out rather than escaped, so no amount of quoting can bend it
        assert raw.startswith(PNG_SIGNATURE)
        width = int.from_bytes(raw[16:20], "big")
        height = int.from_bytes(raw[20:24], "big")
        assert width == height, f"pipette should be square, got {width}x{height}"
        assert width >= 12, f"pipette too small to read: {width}px"
    assert app.PIPETTE_LIGHT_BASE64 != app.PIPETTE_DARK_BASE64


def test_swatches_are_built_wide_enough_to_show_the_colour():
    """
    An 18 pixel button is entirely covered by the glyph, leaving no colour to see
    """
    app.apply_theme()
    layout = app.build_layout()
    for key in app.COLOR_INPUT_KEYS:
        element = find_layout_element(layout, app.color_chooser_key(key))
        assert element is not None
        assert element.ImageSize == app.SWATCH_SIZE
    assert app.SWATCH_SIZE[0] >= 40


def test_refresh_color_swatches_sets_colour_glyph_and_size():
    """
    An update that omits image_size shrinks the button back to the bare glyph
    """
    window = make_window()
    values = make_values(overrides={"-DARK-": "#112233"})
    app.refresh_color_swatches(window, values)
    swatch = window[app.color_chooser_key("-DARK-")]
    assert swatch.button_color == ("#112233", "#112233")
    assert swatch.image_data == app.PIPETTE_LIGHT_BASE64
    assert swatch.image_size == app.SWATCH_SIZE


def test_a_half_typed_colour_leaves_the_swatch_alone():
    window = make_window()
    app.refresh_color_swatches(window, make_values(overrides={"-DARK-": "#12"}))
    assert window[app.color_chooser_key("-DARK-")].button_color is None


def hsl_lightness(color):
    """
    The L of HSL, which is what "brightness" means when picking a colour
    """
    red, green, blue = app.parse_color(color)
    return colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)[1]


def sample_darks(count=1500, seed=20260824):
    rng = random.Random(seed)
    return [hsl_lightness(app.random_color_scheme(rng)["-DARK-"]) for _ in range(count)]


def test_random_darks_are_not_all_near_black():
    """
    Drawing hues evenly used to bury every roll below a fifth of full lightness,
    because most of the hue circle has no headroom against a white background
    """
    lightnesses = sorted(sample_darks())
    median = lightnesses[len(lightnesses) // 2]
    assert median > 0.24, f"median lightness only {median:.2f}"
    assert max(lightnesses) > 0.45, f"nothing brighter than {max(lightnesses):.2f}"
    bright = sum(1 for value in lightnesses if value > 0.30) / len(lightnesses)
    assert bright > 0.35, f"only {bright:.0%} of rolls above 0.30"


def test_random_darks_still_span_a_range():
    """
    Bright is the aim, uniformly bright is not, the rolls should still differ
    """
    lightnesses = sorted(sample_darks())
    assert lightnesses[0] < 0.20, "no deep colours at all"
    assert lightnesses[-1] - lightnesses[0] > 0.25, "lightness barely varies"


def test_brightness_never_costs_the_contrast_floor():
    """
    Whatever the hue is allowed to reach, the pair still has to be readable
    """
    rng = random.Random(31337)
    for _ in range(1500):
        scheme = app.random_color_scheme(rng)
        for dark_key in ("-DARK-", "-DATA_DARK-"):
            ratio = app.contrast_ratio(scheme[dark_key], scheme["-LIGHT-"])
            assert ratio >= app.MIN_CONTRAST_RATIO, f"{scheme} only reached {ratio:.2f}"


def test_ceiling_follows_the_hue():
    """
    Blue carries far more lightness than yellow at the same contrast, which is the
    whole reason the ceiling is computed per hue instead of fixed
    """
    blue = app.brightest_dark_lightness(4 / 6, 0.8, "#FFFFFF")
    red = app.brightest_dark_lightness(0.0, 0.8, "#FFFFFF")
    yellow = app.brightest_dark_lightness(1 / 6, 0.8, "#FFFFFF")
    assert blue > red > yellow
    assert yellow >= app.RANDOM_DARK_LIGHTNESS_FLOOR
    assert blue <= app.RANDOM_DARK_LIGHTNESS_CEILING


@pytest.mark.parametrize("hue", [index / 12 for index in range(12)])
def test_ceiling_is_actually_at_the_limit(hue):
    """
    The value handed back must clear the floor, and going any brighter must not
    """
    light = "#FFFFFF"
    ceiling = app.brightest_dark_lightness(hue, 0.8, light)
    assert (
        app.contrast_ratio(app.hsl_to_hex(hue, 0.8, ceiling), light)
        >= app.MIN_CONTRAST_RATIO
    )
    if ceiling < app.RANDOM_DARK_LIGHTNESS_CEILING - 0.01:
        beyond = app.hsl_to_hex(hue, 0.8, ceiling + 0.02)
        assert app.contrast_ratio(beyond, light) < app.MIN_CONTRAST_RATIO


def test_every_hue_can_still_come_up():
    """
    Leaning towards the roomy hues must not rule the others out entirely
    """
    rng = random.Random(7)
    buckets = set()
    for _ in range(3000):
        red, green, blue = app.parse_color(app.random_color_scheme(rng)["-DARK-"])
        hue = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)[0]
        buckets.add(int(hue * 12) % 12)
    assert len(buckets) == 12, f"only {sorted(buckets)} of the twelve hue sectors"


###############################################################################
# Only the tab in front of the user feeds segno
###############################################################################


def values_with_rubbish_elsewhere(active_tab, fields):
    """
    A good active tab, with unusable leftovers parked in the tabs behind it
    """
    overrides = dict(fields)
    overrides["-Geo_lat-"] = "north"
    overrides["-EPC_amount-"] = "twelve"
    return make_values(active_tab, overrides)


@pytest.mark.parametrize("qrcode_type, fields", TAB_SAMPLES)
def test_generation_ignores_the_other_tabs(qrcode_type, fields):
    """
    A half typed latitude left behind in Geo used to break every other tab,
    because the arguments for all seven types were built on every keystroke
    """
    if qrcode_type in ("Geo", "EPC"):
        pytest.skip("this tab owns the rubbish")
    values = values_with_rubbish_elsewhere(qrcode_type, fields)
    assert app.generate_code(values)


def test_the_offending_tab_still_reports_it():
    """
    Scoping must not turn a real problem into silence on the tab that owns it
    """
    values = make_values("Geo", {"-Geo_lat-": "north", "-Geo_lng-": "2.35"})
    with pytest.raises(ValueError):
        app.generate_code(values)

    window = make_window()
    app.autogen(window, values, errors=False)
    assert window["-ERROR-TEXT-"].text_color == app.COLOR_DANGER


def test_only_filter_returns_just_that_type():
    values = make_values("Wifi", {"-Wifi_ssid-": "MyNet", "-Generic_content-": "hi"})
    scoped = app.get_segno_arguments_from_gui(values, only="Wifi")
    assert set(scoped) == {"Wifi"}
    assert scoped["Wifi"]["ssid"] == "MyNet"

    everything = app.get_segno_arguments_from_gui(values)
    assert set(everything) == set(app.QRCODE_TYPES)
    assert everything["Generic"]["content"] == "hi"


def test_strict_conversion_is_the_default():
    values = make_values("Geo", {"-Geo_lat-": "north"})
    with pytest.raises(ValueError):
        app.get_segno_arguments_from_gui(values, only="Geo")


def test_a_preset_keeps_text_that_will_not_convert():
    """
    A settings file records what is on screen. Refusing to save because a field
    is still half typed would lose everything else the user had set up
    """
    values = make_values("Geo", {"-Geo_lat-": "north", "-Geo_lng-": "2.35"})
    data = app.get_segno_arguments_from_gui(values, strict=False)
    assert data["Geo"]["lat"] == "north"
    assert data["Geo"]["lng"] == 2.35


def test_export_survives_a_half_typed_value(tmp_path, no_gui_popups):
    window = make_window()
    values = make_values(
        "Generic", {"-Generic_content-": "https://example.com", "-Geo_lat-": "north"}
    )
    target = str(tmp_path / "preset")
    assert app.export_settings(window, values, target) is True

    saved = json.loads((tmp_path / "preset.json").read_text(encoding="utf-8"))
    assert saved["data"]["Geo"]["lat"] == "north"
    assert saved["data"]["Generic"]["content"] == "https://example.com"


def test_an_empty_tab_stays_quiet_even_with_rubbish_elsewhere():
    """
    Switching to an untouched tab must not surface someone else's problem
    """
    window = make_window()
    values = values_with_rubbish_elsewhere("Wifi", {})
    app.autogen(window, values, errors=False)
    assert window["-ERROR-TEXT-"].value == app.STATUS_EMPTY
    assert window["-ERROR-TEXT-"].text_color == app.COLOR_MUTED


###############################################################################
# Random button placement
###############################################################################


def colors_frame_rows():
    app.apply_theme()
    frame = find_layout_element(app.build_layout(), "-COLORS_FRAME-")
    assert frame is not None
    return [[getattr(element, "Key", None) for element in row] for row in frame.Rows]


def test_random_button_shares_the_first_colour_row():
    """
    The hex fields leave enough slack on the row to carry it, so it costs no
    height of its own
    """
    rows = colors_frame_rows()
    assert "-RANDOM_COLORS-" in rows[0], rows
    assert app.color_chooser_key("-DARK-") in rows[0], rows


def test_colours_panel_has_exactly_one_row_per_colour():
    """
    Four colours, four rows, nothing spent on a row that holds only a button
    """
    rows = colors_frame_rows()
    assert len(rows) == len(app.COLOR_INPUT_KEYS), rows
    for key, row in zip(app.COLOR_INPUT_KEYS, rows):
        assert key in row, f"{key} not on its own row: {row}"


def test_random_button_appears_once():
    rows = colors_frame_rows()
    flat = [key for row in rows for key in row]
    assert flat.count("-RANDOM_COLORS-") == 1


def test_embedded_artwork_still_matches_the_generator():
    """
    The icon and the two pipettes are pasted into the source as base64. Nothing
    stops the drawing code and the paste drifting apart, so regenerate and
    compare. Needs Pillow, which segno_ui does not depend on, so it simply does
    not run where Pillow is absent
    """
    pytest.importorskip("PIL", reason="Pillow is only needed to redraw the artwork")
    contrib = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contrib"
    )
    sys.path.insert(0, contrib)
    try:
        import make_icon
    finally:
        sys.path.remove(contrib)

    assert (
        make_icon.as_base64(make_icon.draw_icon(make_icon.EMBED_SIZE)).encode()
        == app.ICON_BASE64
    ), "ICON_BASE64 is stale, rerun contrib/make_icon.py"
    assert (
        make_icon.as_base64(
            make_icon.draw_pipette(make_icon.PIPETTE_SIZE, make_icon.WHITE)
        ).encode()
        == app.PIPETTE_LIGHT_BASE64
    ), "PIPETTE_LIGHT_BASE64 is stale"
    assert (
        make_icon.as_base64(
            make_icon.draw_pipette(make_icon.PIPETTE_SIZE, make_icon.PIPETTE_DARK)
        ).encode()
        == app.PIPETTE_DARK_BASE64
    ), "PIPETTE_DARK_BASE64 is stale"


def test_the_pipette_ink_matches_the_generator():
    """
    pipette_for() decides which glyph to use by measuring against PIPETTE_INK, so
    that constant has to be the colour the dark glyph is actually drawn in
    """
    pytest.importorskip("PIL", reason="Pillow is only needed to redraw the artwork")
    contrib = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contrib"
    )
    sys.path.insert(0, contrib)
    try:
        import make_icon
    finally:
        sys.path.remove(contrib)
    assert make_icon.PIPETTE_DARK.upper() == app.PIPETTE_INK.upper()
