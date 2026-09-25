#!/usr/bin/env python3
"""Does bitmaptools.blit copy the region it was asked for?

    PYTHONPATH=main244 python3 blit_scenes.py > stock.txt
    PYTHONPATH=blity1 python3 blit_scenes.py > new.txt
    diff stock.txt new.txt

The source bitmap holds its own coordinates: every pixel is y * 16 + x. So the
value of a copied pixel says exactly which source pixel it came from, and a wrong
index shows up as the wrong number rather than as a subtly wrong picture.

Each scene prints what landed in the destination next to what the region asked
for. A scene is correct when the two match.
"""
import sys

import displayio
import bitmaptools

W = H = 16


def source():
    """Every pixel holds y * 16 + x, so a pixel names its own position."""
    bitmap = displayio.Bitmap(W, H, 256)
    for y in range(H):
        for x in range(W):
            bitmap[x, y] = y * W + x
    return bitmap


def run(name, at, region, skip_source=None, skip_dest=None, dest_fill=None):
    """Blit a region, then report the copied block and the one that was asked for."""
    src = source()
    dst = displayio.Bitmap(W, H, 256)
    if dest_fill is not None:
        for y in range(H):
            for x in range(W):
                dst[x, y] = dest_fill
    x1, y1, x2, y2 = region
    kwargs = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    # blit documents that it swaps a reversed region and clips to the source, so the
    # expectation below has to do the same to be an expectation and not a second bug
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    x2, y2 = min(x2, W), min(y2, H)
    if skip_source is not None:
        kwargs["skip_source_index"] = skip_source
    if skip_dest is not None:
        kwargs["skip_dest_index"] = skip_dest
    try:
        bitmaptools.blit(dst, src, at[0], at[1], **kwargs)
    except Exception as e:  # pylint: disable=broad-except
        print("| %-34s | %s: %s | |" % (name, type(e).__name__, e))
        return

    # The first row of the copied block, and the source row it should have come from
    got = [dst[at[0] + i, at[1]] for i in range(min(x2 - x1, W - at[0]))]
    want = [y1 * W + x1 + i for i in range(len(got))]
    print("| %-34s | %s | %s | %s |"
          % (name, got[:6], want[:6], "ok" if got == want else "WRONG ROW"))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# blit scenes, %dx%d source holding y*%d+x, bitmaptools from %s"
          % (W, H, W, bitmaptools.__file__))
    print("| scene | copied | asked for | |")
    print("|---|---|---|---|")
    run("whole bitmap", (0, 0), (0, 0, W, H))
    run("y1=1", (0, 0), (0, 1, W, H))
    run("y1=3, y2=7", (0, 0), (0, 3, 8, 7))
    run("y1=8, bottom half", (0, 0), (0, 8, W, H))
    run("x1=4", (0, 0), (4, 0, W, H))
    run("x1=4 and y1=4", (0, 0), (4, 4, 12, 12))
    run("y1=15, last row", (0, 0), (0, 15, W, H))
    run("placed at 2,3", (2, 3), (0, 5, 8, 9))
    run("placed at 8,8, clipped", (8, 8), (0, 4, W, H))
    run("one pixel, x1=5 y1=6", (0, 0), (5, 6, 6, 7))
    run("y1=2 with skip_source_index", (0, 0), (0, 2, W, H), skip_source=999)
    run("y1=2 with skip_dest_index", (0, 0), (0, 2, W, H), skip_dest=7,
        dest_fill=3)
    run("y2 past the source", (0, 0), (0, 4, W, H + 8))
    run("reversed region, y2 < y1", (0, 0), (0, 9, W, 4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
