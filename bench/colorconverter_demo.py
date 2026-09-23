#!/usr/bin/env python3
"""Filmable before and after for the ColorConverter fast path on a PiTFT.

    PYTHONPATH=ccfix python3 colorconverter_demo.py --display hx8357
    PYTHONPATH=cc4a python3 colorconverter_demo.py --display hx8357

Two seconds of black, then a full screen image drawn through a ColorConverter
scrolls for a fixed number of seconds, so the faster run simply shows more
frames. Prints the frame count. Everything but displayio is the same in both
runs.
"""
import argparse
import os
import time

import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
SLIDE = 50  # how far the image scrolls before it repeats


def fill_pattern(bitmap, width, height):
    """Bands of colour as 16 bit RGB565 values, which is what the converter reads."""
    for y in range(height):
        green = (y * 63) // height
        for x in range(bitmap.width):
            red = (x * 31) // bitmap.width
            blue = 31 - ((x + y) * 31 // (bitmap.width + height))
            bitmap[x, y] = red << 11 | green << 5 | blue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--step", type=int, default=10,
                    help="pixels the image moves per frame, so the motion reads on video")
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    black = displayio.Bitmap(width, height, 1)
    dark = displayio.Palette(1)
    dark[0] = 0x000000
    blank = displayio.Group()
    blank.append(displayio.TileGrid(black, pixel_shader=dark))
    display.root_group = blank
    display.refresh()

    bitmap = displayio.Bitmap(width + SLIDE, height, 65536)
    fill_pattern(bitmap, width, height)
    converter = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)
    grid = displayio.TileGrid(bitmap, pixel_shader=converter)
    group = displayio.Group()
    group.append(grid)

    print("# %s %dx%d, displayio from %s"
          % (a.display, width, height, os.path.dirname(displayio.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    display.root_group = group
    display.refresh()
    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < a.seconds:
        grid.x = -((frames * a.step) % SLIDE)
        display.refresh()
        frames += 1
    took = time.perf_counter() - t0
    print("%d frames in %.1f s, %.2f frames per second" % (frames, took, frames / took))

    display.root_group = blank
    display.refresh()


if __name__ == "__main__":
    main()
