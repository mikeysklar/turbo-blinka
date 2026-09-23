#!/usr/bin/env python3
"""Filmable before and after for the ColorConverter cache bug, on a PiTFT.

    python3 cache_bug_demo.py [--display ili9341]
    PYTHONPATH=ccfix python3 cache_bug_demo.py

Two seconds of black, then vertical stripes of two colours drawn through a
ColorConverter: cyan 0x07FF and orange 0xFCF8. On main the whole screen comes out cyan,
because 0xFCF8 is the RGB888 form of 0x07FF and the converter's cache is keyed
on the converted colour instead of the one it was given. With the fix the
stripes appear.
"""
import argparse
import os
import time

import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
CYAN, ORANGE = 0x07FF, 0xFCF8  # 0xFCF8 is the RGB888 form of 0x07FF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--stripe", type=int, default=16)
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    bitmap = displayio.Bitmap(width, height, 65536)
    converter = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)
    grid = displayio.TileGrid(bitmap, pixel_shader=converter)
    group = displayio.Group()
    group.append(grid)
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, displayio from %s"
          % (a.display, width, height, os.path.dirname(displayio.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    for y in range(height):
        for x in range(width):
            bitmap[x, y] = CYAN if (x // a.stripe) % 2 == 0 else ORANGE
    display.refresh()
    print("stripes drawn: %#06x and %#06x, %d px wide" % (CYAN, ORANGE, a.stripe))
    time.sleep(6)
    bitmap.fill(0)
    display.refresh()


if __name__ == "__main__":
    main()
