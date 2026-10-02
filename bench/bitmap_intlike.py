#!/usr/bin/env python3
"""Melissa's #197 review: integer-like pixel values, not just int.

    PYTHONPATH=main249:. python3 bitmap_intlike.py

Sets b[0, 0] and fill_region with 12 given as int, NumPy uint8/uint16/int64,
a bool and an object with __index__, plus a float that must still be refused,
on 4, 8 and 16 bit bitmaps. Prints what was stored, or the exception.
"""
import bitmaptools
import displayio
import numpy as np


class Index:
    """An integer-like object that only implements __index__."""

    def __init__(self, value):
        self.value = value

    def __index__(self):
        return self.value


VALUES = [
    ("int", 12),
    ("np.uint8", np.uint8(12)),
    ("np.uint16", np.uint16(12)),
    ("np.int64", np.int64(12)),
    ("bool", True),
    ("__index__", Index(12)),
    ("float", 12.0),
]


def outcome(fn, bitmap):
    try:
        fn()
    except Exception as e:  # pylint: disable=broad-except
        return "%s: %s" % (type(e).__name__, e)
    stored = bitmap[0, 0]
    return "stored %d (%s)" % (stored, type(stored).__name__)


def main():
    print("# integer-like values, numpy %s, displayio from %s" % (np.__version__, displayio.__file__))
    print("| bits | value | `b[0, 0] = value` | `fill_region` |")
    print("|---|---|---|---|")
    for bits, count in ((4, 16), (8, 256), (16, 65536)):
        for name, value in VALUES:
            b = displayio.Bitmap(2, 2, count)
            a = outcome(lambda: b.__setitem__((0, 0), value), b)
            b = displayio.Bitmap(2, 2, count)
            f = outcome(lambda: bitmaptools.fill_region(b, 0, 0, 2, 2, value), b)
            print("| %d | %s | %s | %s |" % (bits, name, a, f))


if __name__ == "__main__":
    main()
