#!/usr/bin/env python3
"""Filmable before and after for blit copying a bitmap into itself, on a PiTFT.

    PYTHONPATH=main248:. python3 blit_overlap_demo.py [--display ili9341]
    PYTHONPATH=blitoverlap:. python3 blit_overlap_demo.py

Two seconds of black, then a strip of coloured discs across the middle of the
screen scrolls right for a fixed time: each frame blits the strip onto itself
STEP pixels to the right, draws the newly exposed columns at the left edge, and
refreshes. When blit reads pixels it has already overwritten, the strip smears
into stripes on the first frame. Prints frames shown.
"""
import argparse
import time

import bitmaptools
import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
COLORS = (0x000000, 0xE0103A, 0xF2B400, 0x12A150, 0x1565D8, 0x8A2BE2, 0xFFFFFF)
SCALE, CELL, STEP = 2, 20, 8


def pattern(x, y):
    """Discs on a grid, one colour per disc, with a white ring, 0 around them."""
    r = CELL // 2 - 1
    d = (x % CELL - CELL // 2) ** 2 + (y % CELL - CELL // 2) ** 2
    if d >= r * r:
        return 0
    if (r // 2) ** 2 <= d < (r // 2 + 2) ** 2:
        return 6
    return (x // CELL + y // CELL) % 5 + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--seconds", type=float, default=10.0)
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]
    w, h = width // SCALE, 4 * CELL

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
    strip = displayio.Bitmap(w, h, len(COLORS))
    group = displayio.Group(scale=SCALE, y=(height - h * SCALE) // 2)
    group.append(displayio.TileGrid(strip, pixel_shader=palette))
    display.root_group = group
    display.refresh()
    print("# %s %dx%d, strip %dx%d at scale %d, bitmaptools from %s"
          % (a.display, width, height, w, h, SCALE, bitmaptools.__file__))
    time.sleep(2)  # black: the sync mark between clips

    for y in range(h):
        for x in range(w):
            strip[x, y] = pattern(x, y)
    display.refresh()

    frames, shift = 0, 0
    end = time.monotonic() + a.seconds
    while time.monotonic() < end:
        bitmaptools.blit(strip, strip, STEP, 0, x2=w - STEP)
        shift += STEP
        for y in range(h):
            for x in range(STEP):
                strip[x, y] = pattern(x - shift, y)
        display.refresh()
        frames += 1
    print("%d frames in %.0f s" % (frames, a.seconds))
    time.sleep(2)
    strip.fill(0)
    display.refresh()


if __name__ == "__main__":
    main()
