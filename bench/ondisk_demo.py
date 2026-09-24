#!/usr/bin/env python3
"""Filmable before and after for the OnDiskBitmap fast path on a PiTFT.

    PYTHONPATH=main242 python3 ondisk_demo.py --display hx8357
    PYTHONPATH=odb4b python3 ondisk_demo.py --display hx8357

Two seconds of black, then a BMP read straight off the disk scrolls for a fixed
number of seconds, so the faster run simply shows more frames. Prints the frame
count. The file is written once and kept, so making it is not part of the timing.

With no --image it draws a generated file. The video in PR #187 used the Blinka
artwork from Adafruit's own examples, one file of each depth:

    Blinka_CLUE.bmp     240x240 16 bit   Adafruit_CircuitPython_PyBadger
    ra8875_blinka.bmp   224x224 24 bit   Adafruit_CircuitPython_RA8875
    Blinka_PyPortal.bmp 320x128  8 bit   Adafruit_CircuitPython_PyBadger

    python3 ondisk_demo.py --display hx8357 --seconds 15 \
        --image images/Blinka_CLUE.bmp --image images/ra8875_blinka.bmp \
        --image images/Blinka_PyPortal.bmp
"""
import argparse
import os
import struct
import time

import board
import displayio
import fourwire

DISPLAYS = {"hx8357": (480, 320), "ili9341": (320, 240)}
SLIDE = 32  # how far the picture scrolls before it repeats


def write_bmp(path, w, h, bpp):
    """An uncompressed BMP, bottom-up rows padded to 4 bytes, in bands of color."""
    colors = 256 if bpp == 8 else 0
    offset = 14 + 40 + colors * 4
    stride = (w * bpp // 8 + 3) & ~3
    rows = []
    for y in range(h - 1, -1, -1):
        row = bytearray(stride)
        for x in range(w):
            v = (x * 5 + y * 3) & 0xFF
            if bpp == 8:
                row[x] = v
            elif bpp == 16:  # 5:5:5
                struct.pack_into("<H", row, x * 2,
                                 ((v >> 3) << 10) | (((255 - v) >> 3) << 5) | (x & 31))
            else:
                row[x * 3:x * 3 + 3] = bytes((x & 0xFF, 255 - v, v))
        rows.append(bytes(row))
    data = b"".join(rows)
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", offset + len(data), 0, 0, offset))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, bpp, 0, len(data), 2835, 2835,
                            colors, 0))
        for i in range(colors):
            f.write(bytes(((i * 5) & 0xFF, (255 - i * 11) & 0xFF, (i * 37) & 0xFF, 0)))
        f.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--display", choices=sorted(DISPLAYS), default="hx8357")
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--bpp", type=int, choices=(8, 16, 24), default=8)
    ap.add_argument("--image", action="append", default=[],
                    help="a BMP to show instead of the generated one, repeatable")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--step", type=int, default=8,
                    help="pixels the picture moves per frame, so the motion reads")
    a = ap.parse_args()
    width, height = DISPLAYS[a.display]

    path = "/tmp/turbo-demo-%dx%d-%dbpp.bmp" % (width + SLIDE, height, a.bpp)
    if not os.path.exists(path):
        write_bmp(path, width + SLIDE, height, a.bpp)

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

    group = displayio.Group()
    if a.image:
        # Lay the pictures out left to right, wrapping when the row is full
        shown = []
        x = y = row_height = 0
        for image in a.image:
            odb = displayio.OnDiskBitmap(image)
            if x and x + odb.width > width:
                x, y = 0, y + row_height
                row_height = 0
            group.append(displayio.TileGrid(odb, pixel_shader=odb.pixel_shader,
                                            x=x, y=y))
            shown.append("%s %dx%d %d bit"
                         % (os.path.basename(image), odb.width, odb.height,
                            odb._bits_per_pixel))  # pylint: disable=protected-access
            x += odb.width
            row_height = max(row_height, odb.height)
        what = ", ".join(shown)
    else:
        odb = displayio.OnDiskBitmap(path)
        group.append(displayio.TileGrid(odb, pixel_shader=odb.pixel_shader))
        what = "%d bit BMP" % a.bpp


    print("# %s %dx%d, %s, displayio from %s"
          % (a.display, width, height, what, os.path.dirname(displayio.__file__)))
    time.sleep(2)  # black: the sync mark between clips

    display.root_group = group
    display.refresh()
    frames = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < a.seconds:
        group.x = -((frames * a.step) % SLIDE)
        display.refresh()
        frames += 1
    took = time.perf_counter() - t0
    print("%d frames in %.1f s, %.2f frames per second" % (frames, took, frames / took))

    display.root_group = blank
    display.refresh()


if __name__ == "__main__":
    main()
