#! /usr/bin/env python3
#  -*- coding: utf-8 -*-
#
# This file is part of segno_ui

"""
Shared test fixtures
"""

import FreeSimpleGUI as sg
import pytest


@pytest.fixture(autouse=True)
def no_gui_popups(monkeypatch):
    """
    Keep the suite headless

    Some of the code under test reports back to the user through a popup, which
    would block on a developer machine and fail outright on a CI runner that has
    no display server. Record the calls instead of drawing them
    """
    recorded = []

    def _record(*args, **kwargs):
        recorded.append(args[0] if args else None)

    for name in ("popup", "popup_error"):
        monkeypatch.setattr(sg, name, _record)
    return recorded
