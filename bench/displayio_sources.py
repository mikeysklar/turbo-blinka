#!/usr/bin/env python3
"""Refresh cost of each image source displayio can draw, no display needed.

    python3 displayio_sources.py [--size 240] [--trials 5]
    PYTHONPATH=main240 python3 displayio_sources.py

One TileGrid or vectorio shape per scene on a headless 16-bit BusDisplay (the
bus throws the bytes away, see displayio_refresh.py), plus one scene on a 1-bit
display. Each trial moves the layer 1 px so the whole area is composited again.
The Bitmap + Palette scene is the #179 fast path; everything else takes the
per-pixel loop. Prints ms per 1000 pixels sent, so scenes of different sizes
compare, and a sha256 of the bytes sent per scene.
"""
import argparse
import hashlib
import os
import platform
import statistics
import struct
import tempfile
import time

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus, host


def write_bmp(path, w, h, bpp):
    # uncompressed BITMAPINFOHEADER BMP, bottom-up rows padded to 4 bytes
    stride = (w * bpp // 8 + 3) & ~3
    colors = 256 if bpp == 8 else 0
    offset = 14 + 40 + colors * 4
    rows = []
    for y in range(h - 1, -1, -1):
        row = bytearray()
        for x in range(w):
            v = (x * 7 + y * 13 + (x * y) // 5) & 0xFF
            if bpp == 8:
                row.append(v)
            elif bpp == 16:  # 5:5:5
                row += struct.pack("<H", ((v >> 3) << 10) | (((255 - v) >> 3) << 5) | (x & 31))
            else:
                row += bytes((x & 0xFF, 255 - v, v))
        rows.append(bytes(row).ljust(stride, b"\0"))
    data = b"".join(rows)
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", offset + len(data), 0, 0, offset))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, bpp, 0, len(data), 2835, 2835,
                            colors, 0))
        for i in range(colors):
            f.write(bytes((i, 255 - i, (i * 7) & 0xFF, 0)))
        f.write(data)


def pattern(bitmap, values):
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 7 + y * 13 + (x * y) // 5) % values


def palette_of(n):
    p = displayio.Palette(n)
    for i in range(n):
        p[i] = ((i * 37) & 0xFF) << 16 | ((255 - i * 11) & 0xFF) << 8 | (i * 5 & 0xFF)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=240)
    ap.add_argument("--trials", type=int, default=5)
    a = ap.parse_args()
    n = a.size
    tmp = tempfile.mkdtemp()
    bmps = {}
    for bpp in (8, 16, 24):
        bmps[bpp] = os.path.join(tmp, "img%d.bmp" % bpp)
        write_bmp(bmps[bpp], n, n, bpp)

    def bitmap_palette():
        b = displayio.Bitmap(n, n, 256)
        pattern(b, 256)
        return displayio.TileGrid(b, pixel_shader=palette_of(256))

    def ondisk(bpp):
        def make():
            odb = displayio.OnDiskBitmap(bmps[bpp])
            return displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
        return make

    def bitmap_colorconverter():
        b = displayio.Bitmap(n, n, 65536)
        pattern(b, 65536)
        conv = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)
        return displayio.TileGrid(b, pixel_shader=conv)

    def vec(kind):
        def make():
            pal = palette_of(2)
            if kind == "rectangle":
                return vectorio.Rectangle(pixel_shader=pal, width=n, height=n, x=0, y=0,
                                          color_index=1)
            if kind == "circle":
                return vectorio.Circle(pixel_shader=pal, radius=n // 2, x=n // 2, y=n // 2,
                                       color_index=1)
            return vectorio.Polygon(pixel_shader=pal, x=0, y=0, color_index=1,
                                    points=[(0, 0), (n - 1, n // 4), (n // 2, n - 1),
                                            (n // 5, n // 2)])
        return make

    # name, layer factory, display kwargs, display size
    mono = dict(color_depth=1, grayscale=True, pixels_in_byte_share_row=False)
    scenes = [
        ("Bitmap + Palette (#179 fast path)", bitmap_palette, {}, (n, n)),
        ("OnDiskBitmap, 8-bit BMP", ondisk(8), {}, (n, n)),
        ("OnDiskBitmap, 16-bit BMP", ondisk(16), {}, (n, n)),
        ("OnDiskBitmap, 24-bit BMP", ondisk(24), {}, (n, n)),
        ("Bitmap + ColorConverter", bitmap_colorconverter, {}, (n, n)),
        ("vectorio Rectangle", vec("rectangle"), {}, (n, n)),
        ("vectorio Circle", vec("circle"), {}, (n, n)),
        ("vectorio Polygon", vec("polygon"), {}, (n, n)),
        ("Bitmap + Palette, 1-bit mono display 128x64", bitmap_palette, mono, (128, 64)),
    ]

    displayio._stop_background()  # pylint: disable=protected-access
    print("# displayio sources, %s, Python %s, %dx%d, displayio from %s, %s"
          % (host(), platform.python_version(), n, n, os.path.dirname(displayio.__file__),
             time.strftime("%Y-%m-%d %H:%M")))
    print("| scene | pixels sent | median ms | ms per 1k px | vs fast path | sha256 |")
    print("|---|---|---|---|---|---|")
    total = hashlib.sha256()
    base = None
    for name, make, kwargs, (w, h) in scenes:
        displayio.release_displays()
        bus = NullBus()
        try:
            display = busdisplay.BusDisplay(bus, b"", width=w, height=h, auto_refresh=False,
                                            **kwargs)
            layer = make()
            group = displayio.Group()
            group.append(layer)
            display.root_group = group
            display.refresh()
            sent0 = bus.sent
            times = []
            for t in range(a.trials):
                layer.x += 1 if t % 2 == 0 else -1
                t0 = time.perf_counter()
                display.refresh()
                times.append((time.perf_counter() - t0) * 1e3)
        except Exception as e:  # pylint: disable=broad-except
            print("| %s | | | | | %s: %s |" % (name, type(e).__name__, e))
            continue
        bits = kwargs.get("color_depth", 16)
        px = (bus.sent - sent0) * 8 // bits // a.trials
        med = statistics.median(times)
        per = med / max(px, 1) * 1e3
        base = base or per
        sha = bus.digest.hexdigest()[:12]
        total.update(sha.encode())
        print("| %s | %d | %.1f | %.2f | %.1fx | %s |" % (name, px, med, per, per / base, sha))
    print("# output sha256 %s" % total.hexdigest()[:12])


if __name__ == "__main__":
    main()
