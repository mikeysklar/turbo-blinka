#!/usr/bin/env python3
"""Correctness scenes for the TileGrid._fill_area fast path.

    python3 displayio_scenes.py [--kernel python|numba|cython] [--only NAME]

Every scene is built twice on a headless 96x64 16-bit display: once on stock
displayio, once with fastpath/tilegrid_fast.py installed. Each does a first
refresh, a change, and a second refresh. The sha256 of every byte sent to the
bus must match. Exit status is the number of scenes that differ.

The display is small and not square on purpose: it keeps the pure-Python runs
short and a swapped width/height cannot hide.
"""
import argparse
import hashlib
import os
import sys
import time

import busdisplay
import displayio

from displayio_refresh import NullBus

W, H = 96, 64


def pattern(bitmap, values, salt=0):
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 7 + y * 13 + (x * y) // 5 + salt) % values


def palette_of(n):
    pal = displayio.Palette(n)
    for i in range(n):
        pal[i] = ((i * 37) & 0xFF) << 16 | ((255 - i * 53) & 0xFF) << 8 | ((i * 101) & 0xFF)
    return pal


def backdrop(group, salt=0):
    bmp = displayio.Bitmap(W, H, 4)
    pattern(bmp, 4, salt)
    group.append(displayio.TileGrid(bmp, pixel_shader=palette_of(4)))
    return bmp


# Each scene: build(group) -> change(), a callable that dirties something.

def s_depth(values):
    def build(group):
        bmp = displayio.Bitmap(W, H, values)
        pattern(bmp, values)
        group.append(displayio.TileGrid(bmp, pixel_shader=palette_of(min(values, 256))))
        return lambda: pattern(bmp, values, salt=3)
    return build


def s_sprite(flip_x=False, flip_y=False, transpose=False, x=20, y=10):
    def build(group):
        backdrop(group)
        bmp = displayio.Bitmap(40, 24, 16)
        pattern(bmp, 16)
        tg = displayio.TileGrid(bmp, pixel_shader=palette_of(16), x=x, y=y)
        tg.flip_x, tg.flip_y, tg.transpose_xy = flip_x, flip_y, transpose
        group.append(tg)

        def change():
            bmp[3, 5] = 9
            bmp[39, 23] = 2
            tg.x += 7
        return change
    return build


def s_scale(scale, gx, gy):
    def build(group):
        backdrop(group)
        inner = displayio.Group(scale=scale, x=gx, y=gy)
        bmp = displayio.Bitmap(20, 12, 16)
        pattern(bmp, 16)
        tg = displayio.TileGrid(bmp, pixel_shader=palette_of(16), x=2, y=1)
        inner.append(tg)
        group.append(inner)

        def change():
            bmp[0, 0] = 5
            bmp[19, 11] = 7
        return change
    return build


def s_sheet(group):
    sheet = displayio.Bitmap(32, 24, 16)  # 4x3 tiles of 8x8
    pattern(sheet, 16)
    tg = displayio.TileGrid(sheet, pixel_shader=palette_of(16), width=10, height=6,
                            tile_width=8, tile_height=8, x=8, y=8)
    for i in range(60):
        tg[i] = (i * 5 + 3) % 12
    backdrop(group)
    group.append(tg)

    def change():
        tg[7] = 11
        tg[59] = 0
        sheet[9, 9] = 1
    return change


def s_transparent(group):
    bottom = backdrop(group)
    bmp = displayio.Bitmap(60, 40, 8)
    pattern(bmp, 8)
    pal = palette_of(8)
    pal.make_transparent(0)
    pal.make_transparent(5)
    tg = displayio.TileGrid(bmp, pixel_shader=pal, x=18, y=12)
    group.append(tg)

    def change():
        bmp[10, 10] = 0
        bottom[30, 30] = 2
        tg.y += 3
    return change


def s_overlap(group):
    backdrop(group)
    grids = []
    for k in range(3):
        bmp = displayio.Bitmap(36, 28, 16)
        pattern(bmp, 16, salt=k * 4)
        grids.append(displayio.TileGrid(bmp, pixel_shader=palette_of(16),
                                        x=10 + k * 18, y=6 + k * 12))
        group.append(grids[-1])

    def change():
        grids[0].x += 5
        grids[2].y -= 4
    return change


def s_offscreen(group):
    backdrop(group)
    bmp = displayio.Bitmap(40, 30, 16)
    pattern(bmp, 16)
    tg = displayio.TileGrid(bmp, pixel_shader=palette_of(16), x=-15, y=-8)
    group.append(tg)

    def change():
        tg.x, tg.y = W - 20, H - 12
    return change


def s_hidden(group):
    backdrop(group)
    bmp = displayio.Bitmap(30, 20, 16)
    pattern(bmp, 16)
    tg = displayio.TileGrid(bmp, pixel_shader=palette_of(16), x=30, y=20)
    group.append(tg)

    def change():
        tg.hidden = True
    return change


def s_converter(group):
    bmp = displayio.Bitmap(W, H, 65536)
    pattern(bmp, 65536, salt=1000)
    conv = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565)
    group.append(displayio.TileGrid(bmp, pixel_shader=conv))
    return lambda: pattern(bmp, 65536, salt=5000)


SCENES = [
    ("1-bit bitmap", s_depth(2), {}),
    ("2-bit bitmap", s_depth(4), {}),
    ("4-bit bitmap", s_depth(16), {}),
    ("8-bit bitmap", s_depth(256), {}),
    ("sprite, plain", s_sprite(), {}),
    ("sprite, flip_x", s_sprite(flip_x=True), {}),
    ("sprite, flip_y", s_sprite(flip_y=True), {}),
    ("sprite, transpose_xy", s_sprite(transpose=True), {}),
    ("sprite, flip_x + flip_y + transpose", s_sprite(True, True, True), {}),
    ("group scale 2", s_scale(2, 4, 3), {}),
    ("group scale 3, odd offset", s_scale(3, 5, 7), {}),
    ("sprite sheet, 10x6 tiles", s_sheet, {}),
    ("transparent palette entries", s_transparent, {}),
    ("three overlapping sprites", s_overlap, {}),
    ("sprite partly off screen", s_offscreen, {}),
    ("sprite hidden", s_hidden, {}),
    ("display rotation 90", s_sprite(flip_x=True), {"rotation": 90}),
    ("display rotation 180", s_sheet, {"rotation": 180}),
    ("display rotation 270", s_transparent, {"rotation": 270}),
    ("16-bit bitmap + ColorConverter (fallback)", s_converter, {}),
]


def run_scene(build, display_kwargs):
    displayio.release_displays()
    bus = NullBus()
    display = busdisplay.BusDisplay(bus, b"", width=W, height=H, auto_refresh=False,
                                    **display_kwargs)
    group = displayio.Group()
    change = build(group)
    display.root_group = group
    t0 = time.perf_counter()
    display.refresh()
    change()
    display.refresh()
    ms = (time.perf_counter() - t0) * 1e3
    return bus.digest.hexdigest()[:12], bus.sent, ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", choices=["python", "numba", "cython"], default="python")
    ap.add_argument("--only", help="run scenes whose name contains this")
    a = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fp = next(d for d in (os.path.join(here, "fastpath"), os.path.join(here, "..", "fastpath"))
              if os.path.isdir(d))
    sys.path[:0] = [os.path.join(fp, "cy"), fp] if a.kernel == "cython" else [fp]
    from run_bench import install_shim
    install_shim("numba" if a.kernel == "numba" else "identity")
    import fill_kernel
    import tilegrid_fast

    displayio._stop_background()  # pylint: disable=protected-access
    print("# %d scenes, %dx%d 16-bit, kernel %s, displayio from %s"
          % (len(SCENES), W, H, a.kernel, os.path.dirname(displayio.__file__)))
    print("| scene | stock sha256 | fast sha256 | bytes | fast calls | fallback calls "
          "| stock ms | fast ms | |")
    print("|---|---|---|---|---|---|---|---|---|")
    bad = 0
    for name, build, kwargs in SCENES:
        if a.only and a.only not in name:
            continue
        tilegrid_fast.uninstall()
        try:
            stock, nbytes, stock_ms = run_scene(build, kwargs)
        except Exception as e:  # pylint: disable=broad-except
            print("| %s | stock raised %s: %s | | | | | | | SKIP |" % (name, type(e).__name__, e))
            continue
        tilegrid_fast.install(fill_kernel.fill_kernel)
        tilegrid_fast.stats.update(fast=0, fallback=0)
        try:
            fast, _, fast_ms = run_scene(build, kwargs)
        except Exception as e:  # pylint: disable=broad-except
            fast, fast_ms = "%s: %s" % (type(e).__name__, e), 0.0
        ok = fast == stock
        bad += not ok
        print("| %s | %s | %s | %d | %d | %d | %.0f | %.0f | %s |"
              % (name, stock, fast, nbytes, tilegrid_fast.stats["fast"],
                 tilegrid_fast.stats["fallback"], stock_ms, fast_ms, "ok" if ok else "DIFF"))
    tilegrid_fast.uninstall()
    print("# %d scene(s) differ" % bad)
    return bad


if __name__ == "__main__":
    sys.exit(main())
