#!/usr/bin/env python3
"""Awkward dirty rectangles on a display that packs several pixels into a byte.

    PYTHONPATH=main243 python3 packed_subrect.py > stock.txt
    PYTHONPATH=subfix python3 packed_subrect.py > new.txt
    diff stock.txt new.txt

A display of fewer than 8 bits per pixel takes a window and a blob of packed
bytes. Hashing the wire is no use here, because the fix sends the same pixels in
fewer writes. So this replays every (window, blob) pair into a framebuffer and
hashes that instead: same pixels means the panel shows the same thing, however
many writes it took.

Hooking set_region_to_update and _send_pixels gives those pairs without decoding
any controller protocol.

Every geometry either prints a framebuffer hash and a write count, or the error
it raised. On stock 2.4.1 a column packed display raises on a dirty rectangle
that is not a whole number of 8 row bands tall.
"""
import hashlib
import sys

import busdisplay
import displayio

from displayio_refresh import NullBus, host

W, H = 128, 64

# bitmap size, placement, and how far it then moves, which sets the dirty area
CASES = (
    ("full screen", (W, H), (0, 0), 1),
    ("odd 37x23 at 0,0", (37, 23), (0, 0), 1),
    ("7x3 off the bottom right", (7, 3), (W - 7, H - 3), 1),
    ("37x8, one band tall", (37, 8), (0, 0), 1),
    ("37x16 at 0,8", (37, 16), (0, 8), 1),
    ("100x5, part of a band", (100, 5), (3, 7), 1),
    ("64x64 off the right edge", (64, 64), (60, 0), 1),
    ("1x8, one pixel wide", (1, 8), (0, 0), 1),
    ("full width, 3 rows", (W, 3), (0, 30), 1),
    ("moved a whole band", (37, 23), (0, 0), 8),
)


def paint(depth, share_row, size, at, move):
    """Draw, move, draw again, and return the framebuffer the panel would hold."""
    # pylint: disable=protected-access, too-many-locals
    displayio.release_displays()
    framebuffer = bytearray(W * H)
    writes = []
    display = busdisplay.BusDisplay(
        NullBus(), b"", width=W, height=H, auto_refresh=False, color_depth=depth,
        grayscale=True, pixels_in_byte_share_row=share_row)
    pixels_per_byte = 8 // depth
    window = {}
    real_region = display._core.set_region_to_update
    real_send = display._send_pixels

    def region(area):
        window["at"] = (area.x1, area.y1, area.x2, area.y2)
        return real_region(area)

    def send(data):
        writes.append((window["at"], bytes(data)))
        return real_send(data)

    display._core.set_region_to_update = region
    display._send_pixels = send

    bitmap = displayio.Bitmap(size[0], size[1], 1 << depth)
    for y in range(size[1]):
        for x in range(size[0]):
            bitmap[x, y] = (x + y) % (1 << depth)
    palette = displayio.Palette(1 << depth)
    for i in range(1 << depth):
        step = 255 // max(1, (1 << depth) - 1)
        palette[i] = 0x010101 * (i * step)
    group = displayio.Group()
    group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=at[0], y=at[1]))
    display.root_group = group
    display.refresh()
    group[0].x += move
    display.refresh()

    for (x1, y1, x2, y2), blob in writes:
        width, height = x2 - x1, y2 - y1
        for n in range(width * height):
            if share_row:
                row, col, index = n // width, n % width, n
            else:
                # Several rows share a byte, so they share a column instead
                col, row = n // height, n % height
                index = (
                    col * pixels_per_byte
                    + (row // pixels_per_byte) * pixels_per_byte * width
                    + row % pixels_per_byte
                )
            if index // pixels_per_byte >= len(blob):
                continue
            shift = (index % pixels_per_byte) * depth
            value = (blob[index // pixels_per_byte] >> shift) & ((1 << depth) - 1)
            x, y = x1 + col, y1 + row
            if 0 <= x < W and 0 <= y < H:
                framebuffer[y * W + x] = value
    return hashlib.sha256(bytes(framebuffer)).hexdigest()[:12], len(writes)


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# packed subrectangles, %dx%d, %s, displayio from %s"
          % (W, H, host(), displayio.__file__))
    print("| depth | share_row | case | framebuffer | writes |")
    print("|---|---|---|---|---|")
    for depth in (1, 2, 4):
        for share_row in (True, False):
            for name, size, at, move in CASES:
                try:
                    digest, writes = paint(depth, share_row, size, at, move)
                except Exception as e:  # pylint: disable=broad-except
                    print("| %d | %s | %s | %s: %s | |"
                          % (depth, share_row, name, type(e).__name__, e))
                    continue
                print("| %d | %s | %s | %s | %d |"
                      % (depth, share_row, name, digest, writes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
