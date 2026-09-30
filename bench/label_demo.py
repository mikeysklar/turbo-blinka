#!/usr/bin/env python3
"""Filmable before and after for a label's first text on a PiTFT.

    PYTHONPATH=main247:bf-243:dt-main:. python3 label_demo.py [--display ili9341]
    PYTHONPATH=main247:bf-243:dt-batch2:. python3 label_demo.py

Two seconds of black, then the screen fills with lines of text, one label and
one display refresh per line. Every line gets a freshly loaded font, so none of
its glyphs are loaded yet, which is what a program's first label sees. Lines
alternate between a BDF and a PCF font. Prints the time of every pass. displayio
and adafruit_bitmap_font are the same in both runs, only adafruit_display_text
differs.
"""
import argparse
import os
import time

import board
import displayio
import fourwire
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
COLORS = (0xE0103A, 0xF2B400, 0x12A150, 0x1565D8, 0x8A2BE2, 0x00B8C4)
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = ("fonts/LeagueSpartan-Bold-16.bdf", "fonts/Junction-regular-24.pcf")
LINES = (
    "Pack my box with five",
    "dozen liquor jugs now",
    "Sphinx of black quartz",
    "judge my vow quickly",
    "How vexingly quick",
    "daft zebras jump high",
    "The five boxing wizards",
    "jump quickly at dawn",
    "Waltz, bad nymph, for",
    "quick jigs vex me too",
)
ROW = 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--passes", type=int, default=2)
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]
    rows = min(height // ROW, len(LINES))

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    group = displayio.Group()
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, %d lines a pass, display_text from %s"
          % (a.display, width, height, rows, os.path.dirname(label.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    total = 0.0
    for p in range(a.passes):
        # A new root group, not group.pop(): Blinka does not erase a removed layer
        group = displayio.Group()
        display.root_group = group
        display.refresh()
        t0 = time.perf_counter()
        for row in range(rows):
            font = bitmap_font.load_font(os.path.join(HERE, FONTS[row % len(FONTS)]))
            group.append(label.Label(font, text=LINES[(row + p * 3) % len(LINES)],
                                     color=COLORS[(row + p) % len(COLORS)],
                                     x=6, y=row * ROW + ROW // 2))
            display.refresh()
        took = time.perf_counter() - t0
        total += took
        print("pass %d: %.2f s" % (p + 1, took))
    print("%d passes, %d labels: %.2f s" % (a.passes, a.passes * rows, total))
    time.sleep(2)
    display.root_group = displayio.Group()
    display.refresh()


if __name__ == "__main__":
    main()
