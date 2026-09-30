#!/usr/bin/env python3
"""Filmable before and after for bitmaptools.blit on a PiTFT.

    python3 blit_demo.py [--display ili9341] [--passes 3]
    PYTHONPATH=blitdirty:. python3 blit_demo.py

Two seconds of black, then the screen is stamped with a grid of round sprites,
one blit and one display refresh per sprite. The sprites come from a sheet, one
per colour, picked with x1 and y1, and index 0 is skipped so the corners stay
transparent. Prints the time of every pass. displayio is the same in both runs,
only bitmaptools differs.
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


def sprite_sheet(size):
    """One row of round sprites, one per colour after black, 0 around each circle."""
    count = len(COLORS) - 1
    sheet = displayio.Bitmap(size * count, size, len(COLORS))
    r = size // 2
    for i in range(count):
        for y in range(size):
            for x in range(size):
                d = (x - r) ** 2 + (y - r) ** 2
                if d < r * r:
                    # a ring of white inside each disc, so a wrong column shows
                    sheet[i * size + x, y] = 6 if (r // 2) ** 2 <= d < (r // 2 + 2) ** 2 else i + 1
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--passes", type=int, default=3)
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]
    size = min(width // COLS, height // ROWS)

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
    sheet = sprite_sheet(size)
    bitmap = displayio.Bitmap(width, height, len(COLORS))
    group = displayio.Group()
    group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, %d px sprites, bitmaptools from %s"
          % (a.display, width, height, size, os.path.dirname(bitmaptools.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    total = 0.0
    for p in range(a.passes):
        t0 = time.perf_counter()
        for row in range(ROWS):
            for col in range(COLS):
                pick = (p + row + col) % (len(COLORS) - 1)
                bitmaptools.blit(bitmap, sheet, col * width // COLS, row * height // ROWS,
                                 x1=pick * size, y1=0, x2=(pick + 1) * size, y2=size,
                                 skip_source_index=0)
                display.refresh()
        took = time.perf_counter() - t0
        total += took
        print("pass %d: %.2f s" % (p + 1, took))
    print("%d passes, %d sprites: %.2f s" % (a.passes, a.passes * ROWS * COLS, total))
    time.sleep(2)
    bitmap.fill(0)
    display.refresh()


if __name__ == "__main__":
    main()
