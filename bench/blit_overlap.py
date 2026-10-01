#!/usr/bin/env python3
"""Does blit copy a bitmap into itself correctly when the two areas overlap?

    PYTHONPATH=main248:. python3 blit_overlap.py

A 16x12 bitmap where every pixel holds its own number is shifted by 3 pixels
within itself, in each of the 8 directions, and also with x1/y1 offsets and
skip indices. The right answer is the same blit taken from an untouched copy of
the bitmap. Wrong pixels mean the copy read pixels it had already overwritten.
Run for an exact Bitmap, which takes the fast path, and for a subclass, which
takes the per-pixel loop.
"""
import sys

import bitmaptools
import displayio

W, H, SHIFT = 16, 12, 3


class Sub(displayio.Bitmap):
    """A Bitmap subclass, so blit takes the general loop."""


def numbered(kind):
    bitmap = kind(W, H, 256)
    for y in range(H):
        for x in range(W):
            bitmap[x, y] = (y * W + x) % 256
    return bitmap


def pixels(bitmap):
    return [bitmap[x, y] for y in range(H) for x in range(W)]


CASES = []
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        if dx or dy:
            CASES.append(("shift %+d,%+d" % (dx, dy),
                          dict(x=4 + dx * SHIFT, y=3 + dy * SHIFT, x1=4, y1=3, x2=12, y2=9)))
CASES += [
    ("whole bitmap right and down", dict(x=SHIFT, y=SHIFT)),
    ("whole bitmap left and up", dict(x=-SHIFT, y=-SHIFT, x1=0, y1=0)),
    ("right, skip source 20", dict(x=7, y=3, x1=4, y1=3, x2=12, y2=9, skip_source_index=20)),
    ("down, skip dest 40", dict(x=4, y=6, x1=4, y1=3, x2=12, y2=9, skip_dest_index=40)),
]


def main():
    print("# blit into itself, %dx%d, displayio from %s" % (W, H, displayio.__file__))
    print("| case | Bitmap wrong px | subclass wrong px |")
    print("|---|---|---|")
    wrong_total = 0
    for name, args in CASES:
        cells = []
        for kind in (displayio.Bitmap, Sub):
            bitmap = numbered(kind)
            expected = numbered(kind)
            bitmaptools.blit(expected, numbered(kind), args["x"], args["y"],
                             **{k: v for k, v in args.items() if k not in ("x", "y")})
            bitmaptools.blit(bitmap, bitmap, args["x"], args["y"],
                             **{k: v for k, v in args.items() if k not in ("x", "y")})
            wrong = sum(a != b for a, b in zip(pixels(bitmap), pixels(expected)))
            wrong_total += wrong
            cells.append(str(wrong))
        print("| %s | %s |" % (name, " | ".join(cells)))
    print("total wrong pixels: %d" % wrong_total)
    return 1 if wrong_total else 0


if __name__ == "__main__":
    sys.exit(main())
