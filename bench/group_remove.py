#!/usr/bin/env python3
"""Does removing a layer from a Group take it off the screen?

    PYTHONPATH=main247:. python3 group_remove.py > stock.txt
    PYTHONPATH=grouperase:. python3 group_remove.py > new.txt

Each scene draws, removes or replaces something, refreshes, and replays every
window and blob sent into a framebuffer. The same final scene is then drawn with a
full refresh, and the two framebuffers are compared. A removed layer whose pixels
stay on screen shows up as STALE, with how many pixels differ.

A last section checks that a layer taken out with remove() or del can be added to
a group again.
"""
import sys

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus
from vector_travel import Recorder

W, H = 96, 64
COLORS = (0x000000, 0xE0103A, 0xF2B400, 0x1565D8, 0x12A150)


def palette():
    pal = displayio.Palette(len(COLORS))
    for i, c in enumerate(COLORS):
        pal[i] = c
    return pal


def square(x, y, w, h, color):
    """A TileGrid of one solid colour."""
    bitmap = displayio.Bitmap(w, h, len(COLORS))
    bitmap.fill(color)
    return displayio.TileGrid(bitmap, pixel_shader=palette(), x=x, y=y)


def label_like(x, y):
    """A Group holding two TileGrids, the shape of a display_text label."""
    group = displayio.Group(x=x, y=y)
    group.append(square(0, 0, 10, 12, 2))
    group.append(square(12, 0, 10, 12, 3))
    return group


def build(scene, rotation):
    """A display and the layers a scene asks for, in a root group."""
    displayio.release_displays()
    display = busdisplay.BusDisplay(
        NullBus(), b"", width=W, height=H, auto_refresh=False, rotation=rotation
    )
    root = displayio.Group()
    made = scene(root)
    display.root_group = root
    return display, root, made


def stale_pixels(a, b):
    return sum(1 for i in range(0, len(a), 2) if a[i : i + 2] != b[i : i + 2])


def run(name, scene, steps, rotation=0):
    try:
        check(name, scene, steps, rotation)
    except ValueError as e:
        print("| %-44s | %6s | ValueError: %s |" % (name, "", e))


def check(name, scene, steps, rotation):
    # pylint: disable=protected-access
    display, root, made = build(scene, rotation)
    recorder = Recorder(display)
    display.refresh()
    first = recorder.pixels
    for step in steps:
        step(root, made)
        display.refresh()
    incremental = bytes(recorder.framebuffer)

    display2, root2, made2 = build(scene, rotation)
    display2.refresh()
    for step in steps:
        step(root2, made2)
    display2._core.full_refresh = True
    reference = Recorder(display2)
    display2.refresh()

    stale = stale_pixels(incremental, bytes(reference.framebuffer))
    print("| %-44s | %6d | %s |" % (name, recorder.pixels - first,
                                     "ok" if not stale else "STALE, %d px" % stale))


def one_square(root):
    sq = square(20, 10, 30, 20, 1)
    root.append(sq)
    return [sq]


def two_squares(root):
    a, b = square(5, 5, 20, 20, 1), square(60, 30, 24, 24, 3)
    root.append(a)
    root.append(b)
    return [a, b]


def with_background(root):
    root.append(square(0, 0, W, H, 4))
    sq = square(30, 20, 20, 16, 1)
    root.append(sq)
    return [sq]


def nested_label(root):
    lbl = label_like(10, 30)
    root.append(lbl)
    return [lbl]


def scaled_inner(root):
    inner = displayio.Group(scale=2, x=8, y=8)
    sq = square(0, 0, 10, 8, 2)
    inner.append(sq)
    root.append(inner)
    return [inner, sq]


def inner_group(root):
    inner = displayio.Group(x=4, y=4)
    a, b = square(0, 0, 16, 16, 1), square(40, 20, 16, 16, 2)
    inner.append(a)
    inner.append(b)
    root.append(inner)
    return [inner, a, b]


def shape(root):
    rect = vectorio.Rectangle(pixel_shader=palette(), width=24, height=18, x=30, y=20,
                              color_index=3)
    root.append(rect)
    return [rect]


def move(layer, x, y):
    layer.x = x
    layer.y = y


SCENES = [
    ("pop a TileGrid", one_square, [lambda r, m: r.pop()]),
    ("remove a TileGrid", one_square, [lambda r, m: r.remove(m[0])]),
    ("del group[0]", one_square, [lambda r, m: r.__delitem__(0)]),
    ("group[0] = a smaller TileGrid elsewhere", one_square,
     [lambda r, m: r.__setitem__(0, square(70, 40, 8, 8, 2))]),
    ("pop the top of two", two_squares, [lambda r, m: r.pop()]),
    ("pop both before one refresh", two_squares, [lambda r, m: (r.pop(), r.pop())]),
    ("pop over a background", with_background, [lambda r, m: r.pop()]),
    ("pop a label-like Group", nested_label, [lambda r, m: r.pop()]),
    ("pop a scaled Group", scaled_inner, [lambda r, m: r.pop()]),
    ("pop inside a nested Group", inner_group, [lambda r, m: m[0].pop()]),
    ("remove inside a nested Group", inner_group, [lambda r, m: m[0].remove(m[1])]),
    ("pop a vectorio Rectangle", shape, [lambda r, m: r.pop()]),
    ("move a Rectangle, pop before refresh", shape,
     [lambda r, m: (move(m[0], 60, 40), r.pop())]),
    ("move a TileGrid, pop before refresh", one_square,
     [lambda r, m: (move(m[0], 50, 30), r.pop())]),
    ("hide, refresh, then pop", one_square,
     [lambda r, m: setattr(m[0], "hidden", True), lambda r, m: r.pop()]),
    ("append and pop before any refresh", one_square,
     [lambda r, m: (r.append(square(60, 5, 10, 10, 2)), r.pop())]),
    ("remove, refresh, add back elsewhere", one_square,
     [lambda r, m: r.remove(m[0]), lambda r, m: (move(m[0], 55, 30), r.append(m[0]))]),
    ("del group[:]", two_squares, [lambda r, m: r.__delitem__(slice(None))]),
    ("del group[1:]", two_squares, [lambda r, m: r.__delitem__(slice(1, None))]),
    ("pop a Group, add it back elsewhere", inner_group,
     [lambda r, m: r.pop(), lambda r, m: (move(m[0], 30, 20), r.append(m[0]))]),
    ("pop, then two more refreshes", one_square,
     [lambda r, m: r.pop(), lambda r, m: None, lambda r, m: None]),
    # Nothing removed: ordinary changes after the first, full refresh
    ("no change", with_background, [lambda r, m: None]),
    ("move a TileGrid", with_background, [lambda r, m: move(m[0], 50, 30)]),
    ("write a pixel", with_background,
     [lambda r, m: m[0].bitmap.__setitem__((3, 3), 2)]),
    ("hide, then show", with_background,
     [lambda r, m: setattr(m[0], "hidden", True),
      lambda r, m: setattr(m[0], "hidden", False)]),
    ("change a palette colour", with_background,
     [lambda r, m: m[0].pixel_shader.__setitem__(1, 0x00FFFF)]),
    ("flip_x and transpose_xy", with_background,
     [lambda r, m: (setattr(m[0], "flip_x", True), setattr(m[0], "transpose_xy", True))]),
    ("move a nested Group", inner_group, [lambda r, m: move(m[0], 20, 12)]),
    ("scale a nested Group", scaled_inner, [lambda r, m: setattr(m[0], "scale", 3)]),
    ("move a Rectangle", shape, [lambda r, m: move(m[0], 5, 5)]),
]


def readd_checks():
    print()
    print("| add back after | result |")
    print("|---|---|")
    for name, take_out in (("pop()", lambda g, l: g.pop()),
                           ("remove()", lambda g, l: g.remove(l)),
                           ("del group[0]", lambda g, l: g.__delitem__(0))):
        group, other = displayio.Group(), displayio.Group()
        layer = square(0, 0, 4, 4, 1)
        group.append(layer)
        take_out(group, layer)
        try:
            other.append(layer)
            result = "ok"
        except ValueError as e:
            result = "ValueError: %s" % e
        print("| %s | %s |" % (name, result))


def second_refresh():
    """How long the refresh after a group is first shown takes, on a 480x320 screen."""
    # pylint: disable=protected-access
    import time  # pylint: disable=import-outside-toplevel

    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=480, height=320,
                                    auto_refresh=False)
    root = displayio.Group()
    root.append(square(0, 0, 480, 320, 4))
    marker = square(10, 10, 8, 8, 1)
    root.append(marker)
    display.root_group = root
    t0 = time.perf_counter()
    display.refresh()
    full = time.perf_counter() - t0
    marker.bitmap[0, 0] = 2
    t0 = time.perf_counter()
    display.refresh()
    second = time.perf_counter() - t0
    print()
    print("480x320: first, full refresh %.1f ms; next refresh after one pixel changed %.1f ms"
          % (full * 1e3, second * 1e3))


def api_checks():
    # pylint: disable=protected-access
    print()
    print("| check | result |")
    print("|---|---|")
    group, other = displayio.Group(), displayio.Group()
    layer = square(0, 0, 4, 4, 1)
    other.append(layer)
    group.append(square(0, 0, 4, 4, 2))
    try:
        group[0] = layer
        result = "accepted"
    except ValueError as e:
        result = "ValueError: %s" % e
    print("| group[0] = a layer already in another group | %s |" % result)
    try:
        group[0] = "not a layer"
        result = "accepted"
    except Exception as e:  # pylint: disable=broad-except
        result = "%s: %s" % (type(e).__name__, e)
    print("| group[0] = a string | %s |" % result)

    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=W, height=H, auto_refresh=False)
    shown, hidden = displayio.Group(), displayio.Group()
    display.root_group = shown
    display.refresh()
    for _ in range(1000):
        hidden.append(square(0, 0, 4, 4, 1))
        hidden.pop()
    queued = len(getattr(hidden, "_removed_areas", ()))
    print("| areas queued after 1000 append and pop on a group not shown | %d |" % queued)


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# group remove, %dx%d, displayio from %s" % (W, H, displayio.__file__))
    for rotation in (0, 90):
        print()
        print("rotation %d" % rotation)
        print("| scene | px sent after first draw | screen |")
        print("|---|---|---|")
        for name, scene, steps in SCENES:
            run(name, scene, steps, rotation)
    readd_checks()
    api_checks()
    second_refresh()
    return 0


if __name__ == "__main__":
    sys.exit(main())
