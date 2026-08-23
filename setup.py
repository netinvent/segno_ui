#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of segno_ui package


__intname__ = "segno_ui.setup"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2022-2026 Orsiris de Jong"
__licence__ = "BSD 3 Clause"
__build__ = "2026082301"


PACKAGE_NAME = "segno_ui"

import ast
import sys
import os

import setuptools


def _read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, filename), "r", encoding="utf-8") as file_handle:
        return file_handle.read()


def get_metadata(package_file):
    """
    Read metadata from package file

    We parse the file instead of matching on line prefixes, so that dunders black
    had to wrap over multiple lines are still readable
    """

    _metadata = {}

    for node in ast.parse(_read_file(package_file)).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in (
                "__version__",
                "__description__",
            ):
                _metadata[target.id.strip("_")] = ast.literal_eval(node.value)
    return _metadata


def parse_requirements(filename):
    """
    There is a parse_requirements function in pip but it keeps changing import path
    pkg_resources used to provide one too, but it is gone from setuptools 81 onwards
    Let's build a simple one
    """
    try:
        requirements_txt = _read_file(filename)
    except OSError:
        print(
            'WARNING: No requirements.txt file found as "{}". Please check path or create an empty one'.format(
                filename
            )
        )
        sys.exit(1)
    install_requires = []
    for line in requirements_txt.splitlines():
        # Drop comments, whether they are on their own line or trailing
        line = line.split("#", 1)[0].strip()
        if line:
            install_requires.append(line)
    print("Found requirements:")
    print(install_requires)
    return install_requires


package_path = os.path.abspath(PACKAGE_NAME)
package_file = os.path.join(package_path, "segno_ui.py")
metadata = get_metadata(package_file)
requirements = parse_requirements(os.path.join(package_path, "requirements.txt"))
long_description = _read_file("README.md")

setuptools.setup(
    name=PACKAGE_NAME,
    # We may use find_packages in order to not specify each package manually
    packages=setuptools.find_packages(),
    version=metadata["version"],
    install_requires=requirements,
    classifiers=[
        # segno_ui is mature
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Printing",
        "Topic :: Utilities",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    description=metadata["description"],
    license="BSD",
    author="NetInvent - Orsiris de Jong",
    author_email="contact@netinvent.fr",
    url="https://github.com/netinvent/segno_ui",
    keywords=[
        "segno",
        "qrcode",
        "generator",
        "offline",
        "gui",
        "vcard",
        "mecard",
        "wifi",
        "epc",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "segno_ui=segno_ui.segno_ui:main",
        ],
    },
)
