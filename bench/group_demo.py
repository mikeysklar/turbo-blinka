#!/usr/bin/env python3
"""Filmable before and after for removing layers from a Group on a PiTFT.

    PYTHONPATH=main247:. python3 group_demo.py [--display ili9341]
    PYTHONPATH=grouperase:. python3 group_demo.py

Two seconds of black, then a grid of coloured squares appears one at a time, one
TileGrid and one refresh each. Then the squares are taken out again one at a
time, in a scattered order, with pop(), remove() and del in turn and a refresh
after each. The screen should end black. Prints how long each half took, not
counting the pause between steps that lets the camera follow.
"""
import argparse
import random
import time

import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
COLORS = (0xE0103A, 0xF2B400, 0x12A150, 0x1565D8, 0x8A2BE2, 0x00B8C4)
COLS, ROWS = 8, 6


def square(x, y, size, color):
    bitmap = displayio.Bitmap(size, size, 1)
    palette = displayio.Palette(1)
    palette[0] = color
    return displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--pause", type=float, default=0.08,
                    help="seconds between steps, so the camera can follow; not timed")
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]
    cell_w, cell_h = width // COLS, height // ROWS
    size = min(cell_w, cell_h) - 6

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
    print("# %s %dx%d, %d squares, displayio from %s"
          % (a.display, width, height, COLS * ROWS, displayio.__file__))
    time.sleep(2)  # black: the sync mark between clips

    added = 0.0
    squares = []
    for row in range(ROWS):
        for col in range(COLS):
            t0 = time.perf_counter()
            sq = square(col * cell_w + 3, row * cell_h + 3, size,
                        COLORS[(row + col) % len(COLORS)])
            group.append(sq)
            squares.append(sq)
            display.refresh()
            added += time.perf_counter() - t0
            time.sleep(a.pause)

    order = list(squares)
    random.Random(4).shuffle(order)
    removed = 0.0
    for i, sq in enumerate(order):
        t0 = time.perf_counter()
        index = group.index(sq)
        if i % 3 == 0:
            group.pop(index)
        elif i % 3 == 1:
            group.remove(sq)
        else:
            del group[index]
        display.refresh()
        removed += time.perf_counter() - t0
        time.sleep(a.pause)
    print("added %d squares in %.2f s, removed them in %.2f s, %d left in the group"
          % (len(squares), added, removed, len(group)))
    time.sleep(2)
    display.root_group = displayio.Group()
    display.refresh()


if __name__ == "__main__":
    main()
