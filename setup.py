#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of command_runner package


__intname__ = "segno_ui.setup"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2022 Orsiris de Jong"
__licence__ = "BSD 3 Clause"
__build__ = "2022113001"


PACKAGE_NAME = "segno_ui"
DESCRIPTION = "Monitor udev events like usb devices being connected, and execute actions upon evnet"

import sys
import os

import pkg_resources
import setuptools


def _read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    if sys.version_info[0] < 3:
        # With python 2.7, open has no encoding parameter, resulting in TypeError
        # Fix with io.open (slow but works)
        from io import open as io_open

        try:
            with io_open(
                os.path.join(here, filename), "r", encoding="utf-8"
            ) as file_handle:
                return file_handle.read()
        except IOError:
            # Ugly fix for missing requirements.txt file when installing via pip under Python 2
            return "\n"
    else:
        with open(os.path.join(here, filename), "r", encoding="utf-8") as file_handle:
            return file_handle.read()


def get_metadata(package_file):
    """
    Read metadata from package file
    """

    _metadata = {}

    for line in _read_file(package_file).splitlines():
        if line.startswith("__version__") or line.startswith("__description__"):
            delim = "="
            _metadata[line.split(delim)[0].strip().strip("__")] = (
                line.split(delim)[1].strip().strip("'\"")
            )
    return _metadata


def parse_requirements(filename):
    """
    There is a parse_requirements function in pip but it keeps changing import path
    Let's build a simple one
    """
    try:
        requirements_txt = _read_file(filename)
        install_requires = [
            str(requirement)
            for requirement in pkg_resources.parse_requirements(requirements_txt)
        ]
        print('Found requirements:')
        print(install_requires)
        return install_requires
    except OSError:
        print(
            'WARNING: No requirements.txt file found as "{}". Please check path or create an empty one'.format(
                filename
            )
        )
        sys.exit(1)


package_path = os.path.abspath(PACKAGE_NAME)
package_file = os.path.join(package_path, "segno_ui.py")
metadata = get_metadata(package_file)
requirements = parse_requirements(os.path.join(package_path, "requirements.txt"))
long_description = _read_file("README.md")

setuptools.setup(
    name=PACKAGE_NAME,
    # We may use find_packages in order to not specify each package manually
    # packages = ['command_runner'],
    packages=setuptools.find_packages(),
    version=metadata["version"],
    install_requires=requirements,
    classifiers=[
        # command_runner is mature
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Printing",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    description=DESCRIPTION,
    license="BSD",
    author="NetInvent - Orsiris de Jong",
    author_email="contact@netinvent.fr",
    url="https://github.com/netinvent/segno_ui",
    keywords=[
        "segnp",
        "qrcode",
        "gui",
        "event",
        "connect",
        "plugged",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    scripts=['segno_ui/segno_ui.py']
)
