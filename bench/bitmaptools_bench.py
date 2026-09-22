#!/usr/bin/env python3
"""Time the per-pixel Python loops in bitmaptools and Bitmap. No display needed.

    python3 bitmaptools_bench.py [--size 240] [--trials 5] [--verbose]

Each case starts from the same patterned bitmap. Prints the median time and a
sha256 of the destination bitmap's data and dirty area, so a faster version can
be checked against stock. Then runs fill_region edge cases (bit depths,
rectangles off the bitmap, reversed and empty corners) and prints one combined
hash; --verbose lists each case.
"""
import argparse
import hashlib
import os
import platform
import statistics
import time

import bitmaptools
import displayio


def model():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip("\x00\n")
    except OSError:
        return platform.machine()


def pattern(bitmap, values, salt=0):
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 7 + y * 13 + (x * y) // 5 + salt) % values


def digest(bitmap):
    # pylint: disable=protected-access
    h = hashlib.sha256(bytes(memoryview(bitmap._data).cast("B")))
    d = bitmap._dirty_area
    h.update(("%d,%d,%d,%d" % (d.x1, d.y1, d.x2, d.y2)).encode())
    return h.hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=240)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--verbose", action="store_true",
                    help="print every fill_region check, not just the combined hash")
    a = ap.parse_args()
    n = a.size

    source = displayio.Bitmap(n, n, 16)
    pattern(source, 16)
    small = displayio.Bitmap(64, 64, 16)
    pattern(small, 16, salt=5)

    def fresh():
        dest = displayio.Bitmap(n, n, 16)
        dest._finish_refresh()  # pylint: disable=protected-access
        return dest

    def ring(dest):
        bitmaptools.draw_circle(dest, n // 2, n // 2, n // 3, 1)
        dest._finish_refresh()  # pylint: disable=protected-access

    def set_every_pixel(dest):
        for y in range(n):
            for x in range(n):
                dest[x, y] = (x + y) & 15

    def get_every_pixel(dest):
        total = 0
        for y in range(n):
            for x in range(n):
                total += source[x, y]
        dest[0, 0] = total & 15

    cases = [
        ("bitmap[x, y] = v, every pixel", n * n, None, set_every_pixel),
        ("v = bitmap[x, y], every pixel", n * n, None, get_every_pixel),
        ("Bitmap.fill", n * n, None, lambda d: d.fill(3)),
        ("fill_region, whole bitmap", n * n, None,
         lambda d: bitmaptools.fill_region(d, 0, 0, n, n, 3)),
        ("blit, whole bitmap", n * n, None, lambda d: bitmaptools.blit(d, source, 0, 0)),
        ("blit 64x64, skip_source_index", 64 * 64, None,
         lambda d: bitmaptools.blit(d, small, 20, 20, skip_source_index=0)),
        ("rotozoom 64x64, 30 degrees, scale 2", 128 * 128, None,
         lambda d: bitmaptools.rotozoom(d, small, angle=0.5236, scale=2.0)),
        ("draw_line x 20, corner to corner", 20 * n, None,
         lambda d: [bitmaptools.draw_line(d, 0, k * 5, n - 1, n - 1 - k * 5, 2)
                    for k in range(20)]),
        ("draw_circle x 20", 0, None,
         lambda d: [bitmaptools.draw_circle(d, n // 2, n // 2, 10 + k * 5, 2)
                    for k in range(20)]),
        ("boundary_fill inside a ring", 0, ring,
         lambda d: bitmaptools.boundary_fill(d, n // 2, n // 2, 4, 0)),
    ]

    print("# bitmaptools bench, %s, Python %s, %dx%d 4-bit, displayio from %s"
          % (model(), platform.python_version(), n, n, os.path.dirname(displayio.__file__)))
    print("| case | pixels | median ms | us per pixel | sha256 |")
    print("|---|---|---|---|---|")
    total = hashlib.sha256()
    for name, pixels, setup, run in cases:
        times = []
        for _ in range(a.trials):
            dest = fresh()
            if setup:
                setup(dest)
            t0 = time.perf_counter()
            run(dest)
            times.append((time.perf_counter() - t0) * 1e3)
        med = statistics.median(times)
        sha = digest(dest)
        total.update(sha.encode())
        per = "%.2f" % (med * 1e3 / pixels) if pixels else ""
        print("| %s | %s | %.1f | %s | %s |" % (name, pixels or "", med, per, sha))
    print("# output sha256 %s" % total.hexdigest()[:12])
    fill_region_checks(a.verbose)


def fill_region_checks(verbose):
    # Edge cases for fill_region, no timing: bit depths, rectangles that leave the
    # bitmap, reversed and empty corners, and the dirty area left by an earlier
    # write. Each case hashes the bitmap data, its dirty area and any exception.
    # pylint: disable=protected-access
    w, h = 40, 30
    rects = [
        ("inside", (3, 4, 20, 17)),
        ("whole", (0, 0, w, h)),
        ("1x1", (7, 8, 8, 9)),
        ("off left", (-5, 2, 10, 12)),
        ("off top", (4, -6, 12, 9)),
        ("off bottom right", (30, 20, 50, 40)),
        ("larger than bitmap", (-5, -5, w + 5, h + 5)),
        ("all right of bitmap", (w + 5, 5, w + 10, 10)),
        ("all above and left", (-10, -10, -2, -2)),
        ("reversed x", (20, 4, 3, 17)),
        ("reversed y", (3, 17, 20, 4)),
        ("zero width", (5, 5, 5, 10)),
        ("zero height", (5, 5, 10, 5)),
    ]
    before = [
        ("clean", lambda b: b._finish_refresh()),
        ("new bitmap", lambda b: None),
        ("one pixel dirty", lambda b: (b._finish_refresh(), b.__setitem__((33, 25), 1))),
    ]
    total = hashlib.sha256()
    rows = []
    for values in (2, 16, 256, 65536):
        for bname, prep in before:
            for rname, (x1, y1, x2, y2) in rects:
                bmp = displayio.Bitmap(w, h, values)
                pattern(bmp, values)
                prep(bmp)
                try:
                    bitmaptools.fill_region(bmp, x1, y1, x2, y2, 5)
                    err = ""
                except Exception as e:  # pylint: disable=broad-except
                    err = "%s: %s" % (type(e).__name__, e)
                d = bmp._dirty_area
                sha = hashlib.sha256(bytes(memoryview(bmp._data).cast("B")))
                sha.update(("%d,%d,%d,%d|%s" % (d.x1, d.y1, d.x2, d.y2, err)).encode())
                sha = sha.hexdigest()[:12]
                total.update(sha.encode())
                rows.append((values, bname, rname, "%d,%d,%d,%d" % (d.x1, d.y1, d.x2, d.y2),
                             err, sha))
    if verbose:
        print("| values | before | rectangle | dirty area after | error | sha256 |")
        print("|---|---|---|---|---|---|")
        for row in rows:
            print("| %s | %s | %s | %s | %s | %s |" % row)
    print("# fill_region checks: %d cases, sha256 %s" % (len(rows), total.hexdigest()[:12]))


if __name__ == "__main__":
    main()
