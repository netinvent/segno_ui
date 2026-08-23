#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of segno_ui

# "from segno_ui import *" would resolve to this very package, which is already
# half initialized in sys.modules at that point, and would silently export nothing
from segno_ui.segno_ui import (
    __author__,
    __copyright__,
    __description__,
    __intname__,
    __licence__,
    __url__,
    __version__,
    autogen,
    generate_code,
    gui,
    main,
)

__all__ = [
    "autogen",
    "generate_code",
    "gui",
    "main",
]
