#!/usr/bin/env python3
"""Correctness scenes for a packed display fast path in TileGrid._fill_area.

    PYTHONPATH=main240 python3 mono_scenes.py > stock.txt
    PYTHONPATH=mono4d python3 mono_scenes.py > new.txt
    diff stock.txt new.txt

Every scene draws a TileGrid on a headless display of fewer than 8 bits per
pixel and prints the sha256 of the bytes sent. Covers 1, 2 and 4 bit displays,
both ways of packing pixels into a byte, both bit orders within the byte,
grayscale and not, bitmaps of 1 to 8 bits per value, the geometry the loop
computes itself, and the cases that must fall through to the old loop: a
dithered palette, a Bitmap subclass, a Palette subclass and a ColorConverter.
Run it against stock and against the change; every line must be identical.
"""
import sys

import busdisplay
import displayio

from displayio_refresh import NullBus

W, H = 128, 64


class MyBitmap(displayio.Bitmap):
    """A subclass, which may override _get_pixel, so it takes the old loop."""


class MyPalette(displayio.Palette):
    """A subclass, which may override _get_color, so it takes the old loop."""


def pattern(bitmap, values):
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 7 + y * 13 + (x * y) // 5) % values


def palette_of(n, cls=None, dither=False, transparent=None):
    palette = (cls or displayio.Palette)(n, dither=dither)
    for i in range(n):
        palette[i] = ((i * 37) & 0xFF) << 16 | ((255 - i * 11) & 0xFF) << 8 | (i * 5) & 0xFF
    if transparent is not None:
        palette.make_transparent(transparent)
    return palette


def scene(name, depth=1, share_row=False, reverse_in_byte=False, grayscale=True,
          values=2, size=None, bitmap_cls=None, palette_cls=None, dither=False,
          transparent=None, converter=False, grid_kwargs=None, scale=1,
          flip_x=False, flip_y=False, transpose=False):
    # pylint: disable=too-many-arguments, too-many-locals
    displayio.release_displays()
    bus = NullBus()
    try:
        display = busdisplay.BusDisplay(
            bus, b"", width=W, height=H, auto_refresh=False, color_depth=depth,
            grayscale=grayscale, pixels_in_byte_share_row=share_row,
            reverse_pixels_in_byte=reverse_in_byte)
        bw, bh = size or (W, H)
        bitmap = (bitmap_cls or displayio.Bitmap)(bw, bh, values)
        pattern(bitmap, values)
        if converter:
            shader = displayio.ColorConverter(
                input_colorspace=displayio.Colorspace.RGB565)
        else:
            shader = palette_of(values, cls=palette_cls, dither=dither,
                                transparent=transparent)
        grid = displayio.TileGrid(bitmap, pixel_shader=shader, **(grid_kwargs or {}))
        grid.flip_x, grid.flip_y, grid.transpose_xy = flip_x, flip_y, transpose
        group = displayio.Group(scale=scale)
        group.append(grid)
        display.root_group = group
        display.refresh()
        grid.x += 1
        display.refresh()
    except Exception as e:  # pylint: disable=broad-except
        print("| %s | %s: %s |" % (name, type(e).__name__, e))
        return
    print("| %s | %s | %d bytes |" % (name, bus.digest.hexdigest()[:12], bus.sent))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# packed display scenes, %dx%d, displayio from %s" % (W, H, displayio.__file__))
    for depth in (1, 2, 4):
        for share_row in (False, True):
            for reverse in (False, True):
                scene("%d bit, share_row=%s, reverse=%s"
                      % (depth, share_row, reverse), depth=depth, share_row=share_row,
                      reverse_in_byte=reverse, values=1 << depth)
    for depth in (1, 2, 4):
        scene("%d bit, color, not grayscale" % depth, depth=depth, grayscale=False,
              values=1 << depth)
    for values in (2, 4, 16, 256):
        scene("1 bit display, %d value bitmap" % values, values=values)
        scene("4 bit display, %d value bitmap" % values, depth=4, values=values)

    # must keep the old loop
    scene("1 bit, dithered palette", dither=True)
    scene("1 bit, Bitmap subclass", bitmap_cls=MyBitmap)
    scene("1 bit, Palette subclass", palette_cls=MyPalette)
    scene("1 bit, ColorConverter", values=65536, converter=True)
    scene("4 bit, dithered palette", depth=4, values=16, dither=True)

    for name, kwargs in (
        ("transparent 0", dict(transparent=0)),
        ("transparent 1", dict(transparent=1)),
        ("scale 2", dict(scale=2)),
        ("scale 3", dict(scale=3)),
        ("flip_x", dict(flip_x=True)),
        ("flip_y", dict(flip_y=True)),
        ("flip both", dict(flip_x=True, flip_y=True)),
        ("transposed", dict(transpose=True)),
        ("transposed and flipped", dict(transpose=True, flip_y=True)),
        ("odd 37x23 bitmap", dict(size=(37, 23))),
        ("placed off the left edge", dict(grid_kwargs=dict(x=-9, y=-5))),
        ("placed off the right edge", dict(grid_kwargs=dict(x=W - 7, y=H - 3))),
        ("sprite sheet 4x2 tiles", dict(size=(64, 32),
                                        grid_kwargs=dict(tile_width=16, tile_height=16,
                                                         width=4, height=2))),
    ):
        for depth, share_row in ((1, False), (1, True), (4, False)):
            scene("%d bit, share_row=%s, %s" % (depth, share_row, name), depth=depth,
                  share_row=share_row, values=1 << depth, **kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
