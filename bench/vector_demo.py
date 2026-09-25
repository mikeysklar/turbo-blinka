#!/usr/bin/env python3
"""Filmable before and after for the vectorio fast path on a PiTFT.

    PYTHONPATH=main242 python3 vector_demo.py --display hx8357
    PYTHONPATH=vec4c python3 vector_demo.py --display hx8357

Two seconds of black, then a rectangle, a circle and a polygon bounce around
for a fixed number of seconds, so the faster run simply shows more frames.
Prints the frame count.
"""
import argparse
import os
import time

import board
import displayio
import fourwire
import vectorio

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
COLORS = (0x000000, 0xE0103A, 0xF2B400, 0x1565D8)


def main():
    # pylint: disable=too-many-locals
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--step", type=int, default=6,
                    help="pixels each shape moves per frame, so the motion reads")
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]
    unit = height // 8  # so the shapes fill a similar share of either screen

    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    if a.display == "ili9341":
        from adafruit_ili9341 import ILI9341 as driver
    else:
        from adafruit_hx8357 import HX8357 as driver
    display = driver(bus, width=width, height=height, auto_refresh=False)

    palette = displayio.Palette(len(COLORS))
    for i, color in enumerate(COLORS):
        palette[i] = color
    black = displayio.Bitmap(width, height, 1)
    dark = displayio.Palette(1)
    dark[0] = 0x000000
    blank = displayio.Group()
    blank.append(displayio.TileGrid(black, pixel_shader=dark))
    display.root_group = blank
    display.refresh()

    rectangle = vectorio.Rectangle(pixel_shader=palette, width=unit * 4, height=unit * 3,
                                   x=0, y=0, color_index=1)
    circle = vectorio.Circle(pixel_shader=palette, radius=unit * 2, x=width // 2,
                             y=height // 2, color_index=2)
    polygon = vectorio.Polygon(pixel_shader=palette, x=width // 3, y=height // 3,
                               color_index=3,
                               points=[(0, 0), (unit * 5, unit), (unit * 3, unit * 4),
                                       (unit, unit * 2)])
    group = displayio.Group()
    for shape in (rectangle, circle, polygon):
        group.append(shape)

    print("# %s %dx%d, rectangle circle polygon, vectorio from %s"
          % (a.display, width, height, os.path.dirname(vectorio.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    display.root_group = group
    display.refresh()
    # each shape gets its own direction so they cross over one another
    moving = [[rectangle, a.step, a.step], [circle, -a.step, a.step],
              [polygon, a.step, -a.step]]
    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < a.seconds:
        for state in moving:
            shape, dx, dy = state
            x, y = shape.x + dx, shape.y + dy
            if not 0 <= x <= width - unit:
                dx = -dx
                x = shape.x + dx
            if not 0 <= y <= height - unit:
                dy = -dy
                y = shape.y + dy
            shape.location = (x, y)
            state[1], state[2] = dx, dy
        display.refresh()
        frames += 1
    took = time.perf_counter() - t0
    print("%d frames in %.1f s, %.2f frames per second" % (frames, took, frames / took))

    display.root_group = blank
    display.refresh()


if __name__ == "__main__":
    main()
