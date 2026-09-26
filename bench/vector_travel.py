#!/usr/bin/env python3
"""Does a moving vectorio shape leave the screen right, and how much does it redraw?

    PYTHONPATH=main245 python3 vector_travel.py > stock.txt
    PYTHONPATH=travel  python3 vector_travel.py > new.txt
    diff stock.txt new.txt

Two things are measured per scene, and they answer different questions.

The framebuffer hash is correctness. Every window and blob the refresh sends is
replayed into a framebuffer, then the same scene is drawn again with a full
refresh forced, and the two are compared. They must be equal: if a move leaves a
stale pixel behind, the incremental result differs from the full redraw and the
scene reports STALE. A hash of the bytes sent cannot see this, because sending
different bytes is exactly what a change to the dirty areas does.

The pixel count is the point of the change. It is how many pixels the refresh
asked the compositor for, so a smaller number for the same framebuffer is the
whole win.

Scenes cover a shape moving less than its own size, exactly its own size, further
than its own size, off each edge, diagonally, several moves between refreshes,
a resize, a hide, two shapes at once, and a shape under a scaled group.
"""
import hashlib
import sys

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus, host

W, H = 96, 64
ROTATION = 0


class Recorder:
    """Replays the windows and blobs a refresh sends into a framebuffer."""

    def __init__(self, display):
        # pylint: disable=protected-access
        self.width = display.width
        self.height = display.height
        self.framebuffer = bytearray(self.width * self.height * 2)
        self.pixels = 0
        self._window = None
        self._real_region = display._core.set_region_to_update
        self._real_send = display._send_pixels
        display._core.set_region_to_update = self._region
        display._send_pixels = self._send

    def _region(self, area):
        self._window = (area.x1, area.y1, area.x2, area.y2)
        return self._real_region(area)

    def _send(self, data):
        x1, y1, x2, y2 = self._window
        width = x2 - x1
        blob = bytes(data)
        for index in range(len(blob) // 2):
            x, y = x1 + index % width, y1 + index // width
            if 0 <= x < self.width and 0 <= y < self.height:
                at = (y * self.width + x) * 2
                self.framebuffer[at : at + 2] = blob[index * 2 : index * 2 + 2]
        self.pixels += len(blob) // 2
        return self._real_send(data)

    def digest(self):
        return hashlib.sha256(bytes(self.framebuffer)).hexdigest()[:12]


def build(shapes, scale=1):
    """A display and a group holding the shapes the scene asks for."""
    displayio.release_displays()
    display = busdisplay.BusDisplay(
        NullBus(), b"", width=W, height=H, auto_refresh=False, rotation=ROTATION
    )
    palette = displayio.Palette(3)
    palette[0] = 0xE0103A
    palette[1] = 0xF2B400
    palette[2] = 0x1565D8
    group = displayio.Group(scale=scale)
    made = []
    for kind, kwargs in shapes:
        if kind == "rectangle":
            shape = vectorio.Rectangle(pixel_shader=palette, **kwargs)
        elif kind == "circle":
            shape = vectorio.Circle(pixel_shader=palette, **kwargs)
        else:
            shape = vectorio.Polygon(pixel_shader=palette, **kwargs)
        group.append(shape)
        made.append(shape)
    display.root_group = group
    return display, made


def run(name, shapes, steps, scale=1):
    """Draw, apply each step, refresh, and compare against a full redraw."""
    # pylint: disable=protected-access
    display, made = build(shapes, scale=scale)
    # Record the first draw as well, so the framebuffer holds the whole screen and
    # not just the parts a later refresh happened to touch
    recorder = Recorder(display)
    display.refresh()
    first_draw = recorder.pixels
    for step in steps:
        step(made)
        display.refresh()
    incremental = recorder.digest()
    moved_pixels = recorder.pixels - first_draw

    # The same scene again, drawn in one go, which is the answer to compare against
    display2, made2 = build(shapes, scale=scale)
    display2.refresh()
    for step in steps:
        step(made2)
    display2._core.full_refresh = True
    reference = Recorder(display2)
    display2.refresh()

    verdict = "ok" if incremental == reference.digest() else "STALE"
    print("| %-34s | %s | %6d px | %s |" % (name, incremental, moved_pixels, verdict))


def move(index, x=None, y=None):
    def step(shapes):
        if x is not None:
            shapes[index].x = x
        if y is not None:
            shapes[index].y = y

    return step


def main():
    # pylint: disable=too-many-statements, global-statement
    global W, H, ROTATION
    if len(sys.argv) > 2:
        W, H = int(sys.argv[1]), int(sys.argv[2])
    if len(sys.argv) > 3:
        ROTATION = int(sys.argv[3])
    displayio._stop_background()  # pylint: disable=protected-access
    print(
        "# vectorio travel, %dx%d rotation %d, %s, vectorio from %s"
        % (W, H, ROTATION, host(), vectorio.__file__)
    )
    print("| scene | framebuffer | redrawn | |")
    print("|---|---|---|---|")

    rect = ("rectangle", dict(width=20, height=20, x=10, y=10, color_index=1))
    circle = ("circle", dict(radius=10, x=20, y=20, color_index=2))
    poly = (
        "polygon",
        dict(points=[(0, 0), (18, 4), (12, 16)], x=10, y=10, color_index=1),
    )

    run("rectangle, 2 px", [rect], [move(0, x=12)])
    run("rectangle, its own width", [rect], [move(0, x=30)])
    run("rectangle, well past itself", [rect], [move(0, x=70)])
    run("rectangle, back again", [rect], [move(0, x=70), move(0, x=10)])
    run("rectangle, diagonal jump", [rect], [move(0, x=70, y=40)])
    run("rectangle, off the right", [rect], [move(0, x=90)])
    run("rectangle, off the left", [rect], [move(0, x=-15)])
    run("rectangle, off the bottom", [rect], [move(0, y=60)])
    run(
        "rectangle, three moves, one refresh",
        [rect],
        [
            lambda s: (
                setattr(s[0], "x", 40),
                setattr(s[0], "x", 60),
                setattr(s[0], "x", 80),
            )
        ],
    )
    run("rectangle, two refreshes apart", [rect], [move(0, x=40), move(0, x=80)])
    run("circle, well past itself", [circle], [move(0, x=80)])
    run("circle, diagonal jump", [circle], [move(0, x=75, y=45)])
    run("polygon, well past itself", [poly], [move(0, x=70)])
    run("polygon, off the top", [poly], [move(0, y=-10)])
    run("rectangle, resized", [rect], [lambda s: setattr(s[0], "width", 40)])
    run("circle, resized", [circle], [lambda s: setattr(s[0], "radius", 25)])
    run("rectangle, hidden", [rect], [lambda s: setattr(s[0], "hidden", True)])
    run(
        "rectangle, hidden then shown",
        [rect],
        [
            lambda s: setattr(s[0], "hidden", True),
            lambda s: setattr(s[0], "hidden", False),
        ],
    )
    run("two shapes, both jump", [rect, circle], [move(0, x=70), move(1, x=10)])
    run("two shapes, crossing", [rect, circle], [move(0, x=60), move(1, x=15)])
    run("rectangle under scale 2", [rect], [move(0, x=30)], scale=2)
    run("circle under scale 2", [circle], [move(0, x=35)], scale=2)
    run("rectangle, no change at all", [rect], [lambda s: None])

    # A transparent entry means a move leaves part of its old box unwritten, which
    # is the case most likely to show a stale pixel
    clear = ("rectangle", dict(width=20, height=20, x=10, y=10, color_index=0))
    run("transparent shape, well past itself", [clear], [move(0, x=70)])
    run(
        "transparent over a solid, crossing",
        [rect, clear],
        [move(0, x=60), move(1, x=15)],
    )
    # The case the change is for: a shape crossing the screen, so the box it travels
    # through is far larger than the shape itself
    run("rectangle, crosses the screen", [rect], [move(0, x=W - 25)])
    run("circle, crosses the screen", [circle], [move(0, x=W - 15)])
    run("rectangle, crosses diagonally", [rect], [move(0, x=W - 25, y=H - 25)])
    run(
        "rectangle, many small steps",
        [rect],
        [move(0, x=10 + step * 3) for step in range(1, 12)],
    )
    run(
        "circle, many small steps",
        [circle],
        [move(0, x=20 + step * 4) for step in range(1, 10)],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
