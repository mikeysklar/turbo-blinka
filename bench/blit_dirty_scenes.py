#!/usr/bin/env python3
"""Does bitmaptools.blit still write the same pixels once it marks dirty once?

    PYTHONPATH=main247:. python3 blit_dirty_scenes.py > stock.txt
    PYTHONPATH=blitdirty:. python3 blit_dirty_scenes.py > new.txt
    diff stock.txt new.txt

Every scene runs at 1, 2, 4, 8 and 16 bits per value. Each prints a hash of the
destination's words, the dirty area left behind, and any exception. Pixels and
exceptions should not change. The dirty area is expected to grow in the skip
scenes only, from the box of pixels written to the whole clipped rect, as in C.
"""
import hashlib
import sys

import displayio
import bitmaptools

SW, SH = 16, 12  # source
DW, DH = 20, 14  # destination
COUNTS = {1: 2, 2: 4, 4: 16, 8: 256, 16: 65536}


class SubBitmap(displayio.Bitmap):
    """A subclass, which has to keep taking the per-pixel path."""


def pattern(bitmap, count, salt):
    """Fill with values that differ per pixel and use the full width of a value."""
    for y in range(bitmap.height):
        for x in range(bitmap.width):
            bitmap[x, y] = (x * 257 + y * 4099 + salt) % count


def fresh(cls, w, h, count, salt):
    bitmap = cls(w, h, count)
    pattern(bitmap, count, salt)
    bitmap._finish_refresh()  # pylint: disable=protected-access
    return bitmap


def dirty(bitmap):
    a = bitmap._dirty_area  # pylint: disable=protected-access
    if a.x1 == a.x2:
        return "none"
    return "(%d,%d)-(%d,%d)" % (a.x1, a.y1, a.x2, a.y2)


def scenes(count):
    """name, x, y, blit kwargs, options"""
    v = (3 * 257 + 2 * 4099 + 1) % count  # a value the source holds
    d = (5 * 257 + 4 * 4099 + 7) % count  # a value the destination holds
    return [
        ("whole source at 0,0", 0, 0, {}, {}),
        ("region 2,3-10,9 at 3,2", 3, 2, {"x1": 2, "y1": 3, "x2": 10, "y2": 9}, {}),
        ("placed at -4,-3", -4, -3, {}, {}),
        ("placed at 15,10, clipped", 15, 10, {}, {}),
        ("fully off the right", 25, 0, {}, {}),
        ("fully off the bottom", 0, 20, {}, {}),
        ("fully off above left", -30, -30, {}, {}),
        ("x1=-2", 0, 0, {"x1": -2}, {}),
        ("y1=-2", 0, 0, {"y1": -2}, {}),
        ("x1=-2, placed at -5 so unread", -5, 0, {"x1": -2}, {}),
        ("x1 past the source", 0, 0, {"x1": 20}, {}),
        ("reversed region 10,9-2,3", 1, 1, {"x1": 10, "y1": 9, "x2": 2, "y2": 3}, {}),
        ("y2 past the source", 0, 0, {"y1": 4, "y2": 40}, {}),
        ("one pixel", 7, 5, {"x1": 5, "y1": 6, "x2": 6, "y2": 7}, {}),
        ("skip_source_index", 2, 1, {"skip_source_index": v}, {}),
        ("skip_dest_index", 2, 1, {"skip_dest_index": d}, {}),
        ("both skips", 2, 1, {"skip_source_index": v, "skip_dest_index": d}, {}),
        ("skip_source_index, clipped", -3, 8, {"skip_source_index": v}, {}),
        ("two blits, dirty unions", 0, 0, {"x2": 4, "y2": 4}, {"again": (14, 9)}),
        ("read-only destination", 0, 0, {}, {"read_only": True}),
        ("subclass destination", 3, 2, {}, {"dest_cls": SubBitmap}),
        ("subclass source", 3, 2, {}, {"src_cls": SubBitmap}),
        ("self blit, overlapping", 2, 1, {"x2": 12, "y2": 10}, {"self": True}),
        ("16 bit source into this depth", 1, 1, {}, {"src_count": 65536}),
    ]


def run(bits, name, x, y, kwargs, opts):
    count = COUNTS[bits]
    dst = fresh(opts.get("dest_cls", displayio.Bitmap), DW, DH, count, 7)
    if opts.get("self"):
        src = dst
    else:
        src_count = opts.get("src_count", count)
        src = fresh(opts.get("src_cls", displayio.Bitmap), SW, SH, src_count, 1)
    if opts.get("read_only"):
        dst._read_only = True  # pylint: disable=protected-access
    try:
        bitmaptools.blit(dst, src, x, y, **kwargs)
        if "again" in opts:
            bitmaptools.blit(dst, src, *opts["again"], **kwargs)
        err = ""
    except Exception as e:  # pylint: disable=broad-except
        err = "%s: %s" % (type(e).__name__, e)
    words = hashlib.sha1(bytes(dst._data)).hexdigest()[:12]  # pylint: disable=protected-access
    print("| %2d | %-34s | %s | %-15s | %s |" % (bits, name, words, dirty(dst), err))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# blit dirty scenes, %dx%d source into %dx%d, bitmaptools from %s"
          % (SW, SH, DW, DH, bitmaptools.__file__))
    print("| bits | scene | dest words | dirty | exception |")
    print("|---|---|---|---|---|")
    for bits in COUNTS:
        for scene in scenes(COUNTS[bits]):
            run(bits, *scene)
    return 0


if __name__ == "__main__":
    sys.exit(main())
