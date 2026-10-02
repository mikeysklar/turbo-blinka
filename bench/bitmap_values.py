#!/usr/bin/env python3
"""What a Bitmap does with a pixel value too big (or negative) for its depth.

    PYTHONPATH=main248:. python3 bitmap_values.py

For each depth, try bitmap[0, 0] = too big, = -1, fill(too big), and a blit from
a 16 bit source holding a value too big for the destination. Prints what was
stored, or the exception. CircuitPython raises ValueError in __setitem__ and fill
and truncates inside blit and the other bitmaptools functions.
"""
import bitmaptools
import displayio

COUNTS = {1: 2, 2: 4, 4: 16, 8: 256, 16: 65536}


def outcome(fn, bitmap):
    try:
        fn()
    except Exception as e:  # pylint: disable=broad-except
        return "%s: %s" % (type(e).__name__, e)
    return "stored %d" % bitmap[0, 0]


def main():
    print("# bitmap values, displayio from %s" % displayio.__file__)
    print("| bits | value | `b[0,0] = value` | `b[0,0] = -1` | `fill(value)` | `fill_region` | `blit` from 16 bit | `rotozoom` from 16 bit |")
    print("|---|---|---|---|---|---|---|---|")
    for bits, count in COUNTS.items():
        # pylint: disable=protected-access
        assert displayio.Bitmap(2, 2, count)._bits_per_value == bits
        big = 1 << bits
        cells = []
        for fn in (
            lambda b: b.__setitem__((0, 0), big),
            lambda b: b.__setitem__((0, 0), -1),
            lambda b: b.fill(big),
            lambda b: bitmaptools.fill_region(b, 0, 0, 2, 2, big),
        ):
            b = displayio.Bitmap(2, 2, count)
            cells.append(outcome(lambda: fn(b), b))
        b = displayio.Bitmap(2, 2, count)
        src = displayio.Bitmap(2, 2, 65536)
        src_big = big if big < 65536 else 65535
        src.fill(src_big)
        if src_big < big:
            cells += ["n/a", "n/a"]
        else:
            cells.append(outcome(lambda: bitmaptools.blit(b, src, 0, 0), b))
            b = displayio.Bitmap(2, 2, count)
            cells.append(outcome(lambda: bitmaptools.rotozoom(b, src), b))
        print("| %d | %d | %s |" % (bits, big, " | ".join(cells)))


if __name__ == "__main__":
    main()
