#!/usr/bin/env python3
"""Correctness scenes for a ColorConverter fast path in TileGrid._fill_area.

    PYTHONPATH=main240 python3 converter_scenes.py > stock.txt
    PYTHONPATH=cc4a python3 converter_scenes.py > new.txt
    diff stock.txt new.txt

Every scene draws a 48x32 TileGrid through a ColorConverter on a headless
display and prints the sha256 of the bytes sent. Covers each input colorspace,
both output byte orders, 8 and 16 bit bitmaps, and the cases that must fall
through to the old loop: dithering, a transparent colour, a 32 bit bitmap and a
ColorConverter subclass. Run it against stock and against the change; every
line must be identical.
"""
import hashlib
import sys

import busdisplay
import displayio

from displayio_refresh import NullBus

W, H = 48, 32
SPACES = [n for n in dir(displayio.Colorspace) if not n.startswith("_")]


class MyConverter(displayio.ColorConverter):
    """A subclass, which may override _convert, so it takes the old loop."""


def pattern(bitmap, values):
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 7 + y * 13 + (x * y) // 5) % values


def scene(name, values, space, reverse, dither=False, transparent=None, cls=None,
          size=None, grid_kwargs=None, scale=1, flip_x=False, flip_y=False,
          transpose=False, late_transparent=None):
    # pylint: disable=too-many-arguments, too-many-locals, too-many-branches
    displayio.release_displays()
    bus = NullBus()
    try:
        display = busdisplay.BusDisplay(bus, b"", width=W, height=H, auto_refresh=False,
                                        reverse_bytes_in_word=reverse)
        bw, bh = size or (W, H)
        bitmap = displayio.Bitmap(bw, bh, values)
        pattern(bitmap, values)
        conv = (cls or displayio.ColorConverter)(
            input_colorspace=getattr(displayio.Colorspace, space), dither=dither)
        if transparent is not None:
            conv.make_transparent(transparent)
        grid = displayio.TileGrid(bitmap, pixel_shader=conv, **(grid_kwargs or {}))
        grid.flip_x, grid.flip_y, grid.transpose_xy = flip_x, flip_y, transpose
        group = displayio.Group(scale=scale)
        group.append(grid)
        display.root_group = group
        display.refresh()
        if late_transparent is not None:
            conv.make_transparent(late_transparent)
            bitmap[0, 0] = bitmap[0, 0]  # dirty one pixel so the area is redrawn
        grid.x += 1
        display.refresh()
    except Exception as e:  # pylint: disable=broad-except
        print("| %s | %s: %s |" % (name, type(e).__name__, e))
        return
    print("| %s | %s | %d bytes |" % (name, bus.digest.hexdigest()[:12], bus.sent))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# ColorConverter scenes, %dx%d, displayio from %s" % (W, H, displayio.__file__))
    for space in SPACES:
        for reverse in (True, False):
            for values in (256, 65536):
                scene("%s, reverse=%s, %d values" % (space, reverse, values),
                      values, space, reverse)
    for space in ("RGB565", "RGB555"):
        scene("%s, dithered" % space, 65536, space, True, dither=True)
        scene("%s, transparent 0" % space, 65536, space, True, transparent=0)
        scene("%s, transparent 7" % space, 65536, space, True, transparent=7)
        scene("%s, subclass" % space, 65536, space, True, cls=MyConverter)
        scene("%s, 32 bit bitmap" % space, 1 << 24, space, True)

    # geometry and bit depth, where the loop's own arithmetic could drift from stock
    for values in (2, 4, 16, 256, 65536):
        scene("RGB565, %d values, odd 37x23 bitmap" % values, values, "RGB565", True,
              size=(37, 23))
    for name, kwargs in (
        ("scale 2", dict(scale=2)),
        ("scale 3", dict(scale=3)),
        ("flip_x", dict(flip_x=True)),
        ("flip_y", dict(flip_y=True)),
        ("flip both", dict(flip_x=True, flip_y=True)),
        ("transposed", dict(transpose=True)),
        ("transposed and flipped", dict(transpose=True, flip_x=True)),
        ("sprite sheet 4x2 tiles", dict(size=(32, 32),
                                        grid_kwargs=dict(tile_width=16, tile_height=16,
                                                         width=4, height=2))),
        ("placed off the left edge", dict(grid_kwargs=dict(x=-9, y=-5))),
        ("placed off the right edge", dict(grid_kwargs=dict(x=W - 7, y=H - 3))),
        ("transparent set after creation", dict(late_transparent=5)),
    ):
        for values in (16, 65536):
            scene("RGB565, %s, %d values" % (name, values), values, "RGB565", True,
                  **kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
