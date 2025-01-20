#! /usr/bin/env python3
#  -*- coding: utf-8 -*-


__intname__ = "segno_ui"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2022-2025 Orsiris de Jong - NetInvent"
__description__ = (
    "Basic UI for segno QR Code generator allowing to use segno fully offline"
)
__licence__ = "BSD 3 Clause"
__version__ = "1.0.5"
__build__ = "2025012001"
__url__ = "https://github.com/netinvent/segno_ui"


from typing import Tuple, Optional
import sys

try:
    import FreeSimpleGUI as sg
except ImportError as exc:
    print(
        "Module not found. If tkinter is missing, you need to install it from your distribution. See README.md file"
    )
    print("Error: {}".format(exc))
    sys.exit()
import segno
import segno.helpers
import inspect
import json


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

PNG_URL_HEADER = "data:image/png;base64,"
ecc_levels = {"7%": "L", "15%": "M", "25%": "Q", "33%": "H"}
scales = [1, 2, 3, 4, 5, 6, 7, 8]
borders = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

CONFIG_FILENAME = "{}-settings.json".format(__intname__)


def get_conf_from_gui(values: dict) -> Tuple[dict, dict, dict]:
    """
    Export PySimpleGUI output configuration to dicts
    """
    # Let's make sure we use L, M, Q, H instead of percentages
    error = ecc_levels[values["-ERROR-"]]
    dark = values["-DARK-"] if values["-DARK-"] else "#000000"
    light = values["-LIGHT-"] if values["-LIGHT-"] else "#FFFFFF"
    data_dark = values["-DATA_DARK-"] if values["-DATA_DARK-"] else "#000000"
    data_light = values["-DATA_LIGHT-"] if values["-DATA_LIGHT-"] else "#000000"
    scale = values["-SCALE-"]
    border = values["-BORDER-"]
    qrcode_format = values["-QRCODE_FORMAT-"]
    active_tab = values["-ACTIVE_TAB-"]

    segno_make_opts = {"error": error, "boost_error": False}

    # Export parameters
    segno_export_opts = {
        "dark": dark,
        "light": light,
        "scale": scale,
        "border": border,
    }

    # Add data_dark and data_light if export is SVG or PNG since EPS and PDF don't support them
    if values["-EXPORT_FORMAT-"] in ["svg", "png"]:
        segno_export_opts["data_dark"] = data_dark
        segno_export_opts["data_light"] = data_light

    misc_options = {"qrcode_format": qrcode_format, "active_tab": active_tab}

    return (segno_make_opts, segno_export_opts, misc_options)


def get_segno_arguments_from_gui(values: dict) -> dict:
    """
    Transform PySimpleGUI values into dict
    """
    # Get all arguments for the given qrcode helper function
    data = {}
    for qrcode_type in QRCODE_TYPES.keys():

        segno_function = QRCODE_TYPES[qrcode_type]
        segno_arguments = inspect.getfullargspec(segno_function).args
        data[qrcode_type] = {}
        for segno_argument in segno_arguments:
            value = values["-{}_{}-".format(qrcode_type, segno_argument)]
            if value:
                # special case for Geo QRCode which requires floats
                if segno_argument in ["lat", "lng"]:
                    value = float(value)
                data[qrcode_type][segno_argument] = value
    return data


def fill_gui_from_segno_arguments(config: dict, window: sg.Window):
    try:
        if config["software"]["name"] != __intname__:
            raise EnvironmentError
    except Exception:
        sg.Popup("Invalid configuation file")
        return
    for key, value in config["segno_make_opts"].items():
        # Special handling for some variables

        # We don't have a boost_error parameter in gui
        if key == "boost_error":
            continue
        # Transform error parameter from percentage into letter according to dict
        if key == "error":
            value = [i for i in ecc_levels if ecc_levels[i] == value][0]
        pysimplegui_key = "-{}-".format(key.upper())
        window[pysimplegui_key].update(value)

    for key, value in config["segno_export_opts"].items():
        pysimplegui_key = "-{}-".format(key.upper())
        window[pysimplegui_key].update(value)

    for key, value in config["misc_opts"].items():
        pysimplegui_key = "-{}-".format(key.upper())
        if key == "active_tab":
            window[value].select()
        window[pysimplegui_key].update(value)

    for qrcode_type in QRCODE_TYPES.keys():
        for key, value in config["data"][qrcode_type].items():
            pysimplegui_key = "-{}_{}-".format(qrcode_type, key)
            window[pysimplegui_key].update(value)


def generate_code(values: dict, save_to: str = None) -> Optional[bytes]:
    """
    Create QRCodes

    """
    segno_make_opts, segno_export_opts, misc_options = get_conf_from_gui(values)
    data_arguments = get_segno_arguments_from_gui(values)

    qrcode_type = values["-ACTIVE_TAB-"]
    qrcode_generate_fn = (
        segno.make_qr
        if misc_options["qrcode_format"] == "Standard QR Code"
        else segno.make_micro
    )
    segno_function = QRCODE_TYPES[qrcode_type]

    # Run helper function
    content = segno_function(**data_arguments[qrcode_type])
    # Create QRCode from content made by helper

    qrcode = qrcode_generate_fn(content, **segno_make_opts)

    # Make PNG and print it in PySimpleGUI
    if not save_to:
        qrcode_data = qrcode.png_data_uri(**segno_export_opts)
        data = qrcode_data[len(PNG_URL_HEADER) :]
        return data

    # Add file extension to filename
    save_to = "{}.{}".format(save_to, values["-EXPORT_FORMAT-"])
    qrcode.save(save_to, kind=values["-EXPORT_FORMAT-"], **segno_export_opts)
    return None

def gui():
    """
    Main GUI
    """

    # We need to set the theme before calling any sg items
    sg.theme("LightGrey1")

    settings_col = [
        [
            sg.Text("Mode", size=(15, 1)),
            sg.Combo(
                ["Standard QR Code", "Mini QR Code"],
                default_value="Standard QR Code",
                key="-QRCODE_FORMAT-",
                size=(20, 1),
                enable_events=True,
            ),
        ],
        [
            sg.Text("Error correction", size=(15, 1)),
            sg.Combo(
                list(ecc_levels.keys()),
                default_value="15%",
                key="-ERROR-",
                size=(20, 1),
                enable_events=True,
            ),
        ],
        [
            sg.Text("Scale", size=(15, 1)),
            sg.Spin(
                scales,
                initial_value="2",
                key="-SCALE-",
                size=(20, 1),
                enable_events=True,
            ),
        ],
        [
            sg.Text("Border", size=(15, 1)),
            sg.Spin(
                borders,
                initial_value="1",
                key="-BORDER-",
                size=(20, 1),
                enable_events=True,
            ),
        ],
        [
            sg.ColorChooserButton(
                "Dark", target="-DARK-", key="-CHOOSER BUTTON-", size=(15, 1)
            ),
            sg.Input("#000000", key="-DARK-", size=(20, 1), enable_events=True),
        ],
        [
            sg.ColorChooserButton(
                "Light", target="-LIGHT-", key="-CHOOSER BUTTON-", size=(15, 1)
            ),
            sg.Input("#FFFFFF", key="-LIGHT-", size=(20, 1), enable_events=True),
        ],
        [
            sg.ColorChooserButton(
                "Data dark", target="-DATA_DARK-", key="-CHOOSER BUTTON-", size=(15, 1)
            ),
            sg.Input("#000000", key="-DATA_DARK-", size=(20, 1), enable_events=True),
        ],
        [
            sg.ColorChooserButton(
                "Data light",
                target="-DATA_LIGHT-",
                key="-CHOOSER BUTTON-",
                size=(15, 1),
            ),
            sg.Input("#FFFFFF", key="-DATA_LIGHT-", size=(20, 1), enable_events=True),
        ],
        [
            sg.Button("Generate", button_color="darkblue"),
            sg.Text("  Export as"),
            sg.Combo(
                ["png", "svg", "eps", "pdf"], default_value="png", key="-EXPORT_FORMAT-"
            ),
            sg.SaveAs("Export as", target="-EXPORT_FILENAME-"),
            sg.Input("", key="-EXPORT_FILENAME-", enable_events=True, visible=False),
        ],
        [
            sg.SaveAs("Export settings", target="-EXPORT_SETTINGS_FILENAME-"),
            sg.Input(
                "", key="-EXPORT_SETTINGS_FILENAME-", enable_events=True, visible=False
            ),
            sg.FileBrowse("Import settings", target="-IMPORT_SETTINGS_FILENAME-"),
            sg.Input(
                "", key="-IMPORT_SETTINGS_FILENAME-", enable_events=True, visible=False
            ),
            sg.Button("Exit"),
        ],
        [sg.Text("Resulting Image", text_color="grey", font=(None, 12, "bold"))],
        [
            sg.Column(
                [[sg.Image(key="-OUTPUT-IMAGE-", size=(100, 100))]],
                background_color="#AAAAAA",
                element_justification="c",
            )
        ],
    ]

    dynamic_layouts = []
    for qrcode_type, fn in QRCODE_TYPES.items():
        segno_arguments = inspect.getfullargspec(fn).args

        tab_layout = []
        for segno_argument in segno_arguments:
            tab_layout.append(
                [
                    sg.Text(text=segno_argument.capitalize(), size=(15, 1)),
                    sg.InputText(
                        key="-{}_{}-".format(qrcode_type, segno_argument),
                        enable_events=True,
                    ),
                ]
            )

        # Key QRCODE_TYPE will be set in -ACTIVE_TAB- key
        dynamic_layouts.append(
            sg.Tab(
                qrcode_type,
                [
                    [
                        sg.Column(
                            tab_layout,
                            scrollable=(qrcode_type == "vCard"),
                            vertical_scroll_only=True,
                        )
                    ]
                ],
                key="{}".format(qrcode_type),
            )
        )

    full_tabbed_layout = [
        [sg.Text("", text_color="red", key="-ERROR-TEXT-")],
        [
            sg.Column(
                [[sg.TabGroup([dynamic_layouts], key="-ACTIVE_TAB-")]],
                vertical_alignment="top",
            ),
            sg.Column(
                settings_col, vertical_alignment="top", element_justification="c"
            ),
        ],
    ]

    window = sg.Window(
        "Segno UI Offline QRCode Generator {}".format(__version__), full_tabbed_layout
    )

    while True:
        event, values = window.read()
        if _DEBUG:
            print(event)
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "Generate":
            autogen(window, values, errors=True)
        elif event == "-EXPORT_FILENAME-":
            try:
                generate_code(values, save_to=values["-EXPORT_FILENAME-"])
                sg.Popup("File exported")
            except Exception as exc:
                sg.PopupError(exc)
                if _DEBUG:
                    raise
        elif event == "-EXPORT_SETTINGS_FILENAME-":
            try:
                config_filename = values["-EXPORT_SETTINGS_FILENAME-"]
                if config_filename.split(".")[0] != "json":
                    config_filename = config_filename.split(".")[0] + ".json"
                config = {}
                config["software"] = {
                    "name": __intname__,
                    "version": __version__,
                }
                config["data"] = get_segno_arguments_from_gui(values)
                (
                    config["segno_make_opts"],
                    config["segno_export_opts"],
                    config["misc_opts"],
                ) = get_conf_from_gui(values)
                with open(config_filename, "w", encoding="utf-8") as file_handle:
                    json.dump(config, file_handle)
                sg.Popup("Configuration written to {}".format(config_filename))
            except OSError as exc:
                sg.PopupError("Cannot write file {}: {}".format(config_filename, exc))
                if _DEBUG:
                    raise
            except Exception as exc:
                sg.PopupError("Could not export config: {}".format(exc))
                if _DEBUG:
                    raise
        elif event == "-IMPORT_SETTINGS_FILENAME-":
            try:
                with open(
                    values["-IMPORT_SETTINGS_FILENAME-"], "r", encoding="utf-8"
                ) as file_handle:
                    config = json.load(file_handle)
                    fill_gui_from_segno_arguments(config, window)
                    # Reload values so we may generate the qrcode
                    _, values = window.read(timeout=1)
                    autogen(window, values)
            except Exception as exc:
                sg.PopupError(
                    "Could not import config file {}: {}".format(
                        values["-IMPORT_SETTINGS_FILENAME-"], exc
                    )
                )
                if _DEBUG:
                    raise
        else:
            # Let's just try to wildly "autogenerate" when an event happens, and not do anything if generation is not succesful
            autogen(window, values, errors=False)
    window.close()


def autogen(window, values, errors=False):
    """
    Generate QRCode and update GUI
    """
    try:
        data = generate_code(values)
        window["-OUTPUT-IMAGE-"].update(data=data)
        window["-ERROR-TEXT-"].update("")
    except Exception as exc:
        if errors:
            sg.PopupError(exc)
            if _DEBUG:
                raise
        else:
            print("Autogen: {}".format(exc))
            window["-ERROR-TEXT-"].update(exc)


if __name__ == "__main__":
    gui()
