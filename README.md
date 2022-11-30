# Segno UI

This program is a graphical user interface for the [segno library](https://github.com/heuer/segno) that allows to create QR codes.

While segno has a nice CLI interface, a graphical user interface fills the gap for quick usage.

The main goal of Segno UI is to provide a QRCode generator that doesn't need any online tools, which guarantees that the data you're encoding doesn't leave your computer.
Using online generators needs you to put your trust in developper behind the tool, hoping that your data won't be stored or reselled.

## Quick usage

You may find precompiled binaries for Windows on the [release page](https://github.com/netinvent/segno_ui/releases).

We don't provide precompiled binaries for Linux or MacOS, as those generally come with a Python interpreter already.

Install with:
```
python3 -m pip install segno_ui
```

Use with:
```
segno_ui.py
```

## Graphical user interface

![image](pics/screenshot_202211300101.png)


## Technical stuff

Basically, Segno UI is a wrapper using the excellent [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) toolkit allowing to create multiplatform GUI interfaces easily.

It should be quite future proof since all properties that go into the QR codes are dynamically generated by reading the qrcode maker function signatures.
Hence, if segno adds a new parameter, it will automatically exist in Segno UI.

## Why

I've built this tool to quickly create / store settings for some vCards / MeCards without going online.

All help is welcome ;)