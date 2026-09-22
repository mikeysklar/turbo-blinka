#!/usr/bin/env python3
"""Filmable before and after for bitmaptools.fill_region on a PiTFT.

    python3 fill_region_demo.py [--display ili9341] [--passes 3]
    PYTHONPATH=fr5b python3 fill_region_demo.py

Two seconds of black, then the screen is covered in a grid of rectangles, one
fill_region and one display refresh per rectangle, in a new colour each pass.
Prints the time of every pass. displayio is the same in both runs, only
bitmaptools differs.
"""
import argparse
import os
import time

import bitmaptools
import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
COLORS = (0x000000, 0xE0103A, 0xF2B400, 0x12A150, 0x1565D8, 0x8A2BE2, 0xFFFFFF)
COLS, ROWS = 8, 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--passes", type=int, default=3)
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    palette = displayio.Palette(len(COLORS))
    for i, c in enumerate(COLORS):
        palette[i] = c
    bitmap = displayio.Bitmap(width, height, len(COLORS))
    group = displayio.Group()
    group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, bitmaptools from %s"
          % (a.display, width, height, os.path.dirname(bitmaptools.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    total = 0.0
    for p in range(a.passes):
        t0 = time.perf_counter()
        for row in range(ROWS):
            for col in range(COLS):
                # checkerboard of two colours per pass, so each rectangle shows
                color = 1 + (2 * p + (row + col) % 2) % (len(COLORS) - 1)
                bitmaptools.fill_region(bitmap, col * width // COLS, row * height // ROWS,
                                        (col + 1) * width // COLS, (row + 1) * height // ROWS,
                                        color)
                display.refresh()
        took = time.perf_counter() - t0
        total += took
        print("pass %d: %.2f s" % (p + 1, took))
    print("%d passes, %d rectangles: %.2f s" % (a.passes, a.passes * ROWS * COLS, total))
    time.sleep(2)
    bitmap.fill(0)
    display.refresh()


if __name__ == "__main__":
    main()
