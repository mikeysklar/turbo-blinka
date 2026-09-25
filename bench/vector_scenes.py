#!/usr/bin/env python3
"""Correctness scenes for a vectorio fast path in _VectorShape._fill_area.

    PYTHONPATH=main242 python3 vector_scenes.py > stock.txt
    PYTHONPATH=vec4c python3 vector_scenes.py > new.txt
    diff stock.txt new.txt

Every scene draws one or more vectorio shapes on a headless display and prints
the sha256 of the bytes sent. Covers the three shapes, the geometry the loop
works out itself (every display rotation, scale, placement off each edge), shapes
that overlap, a transparent palette entry, a color index outside the palette,
a 1 bit display, and the cases that must fall through to the old loop: a
dithered palette, a Palette subclass, a shape subclass and a ColorConverter.
Run it against stock and against the change; every line must be identical.
"""
import sys

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus

W, H = 96, 64


class MyPalette(displayio.Palette):
    """A subclass, which may override _get_color, so it takes the old loop."""


class MyCircle(vectorio.Circle):
    """A subclass, which may override _get_pixel, so it takes the old loop."""


POINTS = [(0, 0), (60, 12), (40, 50), (8, 30)]


def palette_of(n, cls=None, dither=False, transparent=None):
    palette = (cls or displayio.Palette)(n, dither=dither)
    for i in range(n):
        palette[i] = ((i * 87) & 0xFF) << 16 | ((255 - i * 41) & 0xFF) << 8 | (i * 29) & 0xFF
    if transparent is not None:
        palette.make_transparent(transparent)
    return palette


def build(kind, shader, color_index=1, x=10, y=8, cls=None):
    if kind == "rectangle":
        return vectorio.Rectangle(pixel_shader=shader, width=40, height=28, x=x, y=y,
                                  color_index=color_index)
    if kind == "circle":
        return (cls or vectorio.Circle)(pixel_shader=shader, radius=22, x=x + 20,
                                        y=y + 20, color_index=color_index)
    return vectorio.Polygon(pixel_shader=shader, points=POINTS, x=x, y=y,
                            color_index=color_index)


def scene(name, kinds=("circle",), colors=3, color_index=1, dither=False,
          transparent=None, palette_cls=None, shape_cls=None, converter=False,
          depth=16, reverse=False, scale=1, rotation=0, at=(10, 8), second=None):
    # pylint: disable=too-many-arguments, too-many-locals
    displayio.release_displays()
    bus = NullBus()
    try:
        kwargs = {}
        if depth != 16:
            kwargs = dict(color_depth=depth, grayscale=True,
                          pixels_in_byte_share_row=False)
        display = busdisplay.BusDisplay(bus, b"", width=W, height=H, auto_refresh=False,
                                        rotation=rotation,
                                        reverse_bytes_in_word=reverse, **kwargs)
        if converter:
            shader = displayio.ColorConverter(
                input_colorspace=displayio.Colorspace.RGB888)
        else:
            shader = palette_of(colors, cls=palette_cls, dither=dither,
                                transparent=transparent)
        group = displayio.Group(scale=scale)
        for kind in kinds:
            shape = build(kind, shader, color_index=color_index, x=at[0], y=at[1],
                          cls=shape_cls)
            group.append(shape)
        if second is not None:
            group.append(build(second, shader, color_index=color_index,
                               x=at[0] + 18, y=at[1] + 10))
        for shape in group:
            shape.hidden = False
        display.root_group = group
        display.refresh()
        group[0].x += 1
        display.refresh()
        group[0].y -= 1
        display.refresh()
    except Exception as e:  # pylint: disable=broad-except
        print("| %s | %s: %s |" % (name, type(e).__name__, e))
        return
    print("| %s | %s | %d bytes |" % (name, bus.digest.hexdigest()[:12], bus.sent))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# vectorio scenes, %dx%d, vectorio from %s" % (W, H, vectorio.__file__))
    for kind in ("rectangle", "circle", "polygon"):
        for reverse in (False, True):
            scene("%s, reverse=%s" % (kind, reverse), kinds=(kind,), reverse=reverse)

    # must keep the old loop
    scene("circle, dithered palette", dither=True)
    scene("circle, Palette subclass", palette_cls=MyPalette)
    scene("circle, Circle subclass", shape_cls=MyCircle)
    scene("circle, ColorConverter shader", converter=True)
    scene("circle, 1 bit display", depth=1)
    scene("rectangle, 1 bit display", kinds=("rectangle",), depth=1)

    # the palette entry the shape asks for
    scene("circle, transparent color", transparent=1)
    scene("circle, color index 0", color_index=0)
    scene("circle, color index 2 of 3", color_index=2)
    scene("circle, color index past the palette", color_index=9)

    for kind in ("rectangle", "circle", "polygon"):
        for name, kwargs in (
            ("scale 2", dict(scale=2)),
            ("scale 3", dict(scale=3)),
            ("rotated 90", dict(rotation=90)),
            ("rotated 180", dict(rotation=180)),
            ("rotated 270", dict(rotation=270)),
            ("off the left edge", dict(at=(-15, -9))),
            ("off the right edge", dict(at=(W - 12, H - 7))),
            ("off the top", dict(at=(20, -25))),
            ("overlapping a rectangle", dict(second="rectangle")),
            ("overlapping a circle", dict(second="circle")),
        ):
            scene("%s, %s" % (kind, name), kinds=(kind,), **kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
