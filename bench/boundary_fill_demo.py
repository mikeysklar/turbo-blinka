#!/usr/bin/env python3
"""Filmable before and after for bitmaptools.boundary_fill on a PiTFT.

    python3 boundary_fill_demo.py [--display ili9341] [--rings 2]
    PYTHONPATH=pr5 python3 boundary_fill_demo.py

Two seconds of black, then three yellow rings, then each ring is flood filled and
the display refreshed. Prints the time of every fill. displayio is the same in
both runs, only bitmaptools differs.
"""
import argparse
import os
import time

import bitmaptools
import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
BLACK, YELLOW, RED, GREEN, BLUE = range(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--rings", type=int, default=3, choices=[1, 2, 3],
                    help="fewer rings for a shorter take on a slow board")
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    palette = displayio.Palette(5)
    for i, c in enumerate((0x000000, 0xF2B400, 0xE0103A, 0x12A150, 0x1565D8)):
        palette[i] = c
    bitmap = displayio.Bitmap(width, height, 5)
    group = displayio.Group()
    group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, bitmaptools from %s"
          % (a.display, width, height, os.path.dirname(bitmaptools.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    unit = height // 8
    rings = [(unit * 2, unit, RED), (unit * 5, unit * 3 // 2, GREEN),
             (width - unit * 5 // 2, unit * 2, BLUE)][:a.rings]
    for x, radius, _ in rings:
        bitmaptools.draw_circle(bitmap, x, height // 2, radius, YELLOW)
    display.refresh()

    total = 0.0
    for x, radius, color in rings:
        t0 = time.perf_counter()
        bitmaptools.boundary_fill(bitmap, x, height // 2, color, BLACK)
        took = time.perf_counter() - t0
        total += took
        display.refresh()
        print("fill radius %d: %.2f s" % (radius, took))
    print("%d fills: %.2f s" % (len(rings), total))
    time.sleep(2)
    bitmap.fill(BLACK)
    display.refresh()


if __name__ == "__main__":
    main()
