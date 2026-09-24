#!/usr/bin/env python3
"""Filmable before and after for the packed display fast path on a mono OLED.

    PYTHONPATH=main240 python3 mono_demo.py
    PYTHONPATH=mono4d python3 mono_demo.py

For the Adafruit 128x64 OLED Bonnet, an SSD1306 on I2C. Two seconds of a blank
screen, then a pattern scrolls for a fixed number of seconds, so the faster run
simply shows more frames. Prints the frame count.
"""
import argparse
import os
import time

import board
import displayio
import i2cdisplaybus
from adafruit_displayio_ssd1306 import SSD1306

WIDTH, HEIGHT = 128, 64
SLIDE = 32  # how far the pattern scrolls before it repeats


def fill_pattern(bitmap):
    """Diagonal bars and a border, which read clearly on a small mono screen."""
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            edge = y < 2 or y >= bitmap.height - 2
            bitmap[x, y] = 1 if edge or ((x + y * 2) // 8) % 2 == 0 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", type=lambda v: int(v, 0), default=0x3C)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--step", type=int, default=4,
                    help="pixels the pattern moves per frame, so the motion reads")
    a = ap.parse_args()

    displayio.release_displays()
    bus = i2cdisplaybus.I2CDisplayBus(board.I2C(), device_address=a.address)
    display = SSD1306(bus, width=WIDTH, height=HEIGHT, auto_refresh=False)

    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = 0xFFFFFF
    blank_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
    blank = displayio.Group()
    blank.append(displayio.TileGrid(blank_bitmap, pixel_shader=palette))
    display.root_group = blank
    display.refresh()

    bitmap = displayio.Bitmap(WIDTH + SLIDE, HEIGHT, 2)
    fill_pattern(bitmap)
    grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(grid)

    print("# SSD1306 %dx%d, displayio from %s"
          % (WIDTH, HEIGHT, os.path.dirname(displayio.__file__)))
    time.sleep(2)  # blank: the sync mark between clips

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
