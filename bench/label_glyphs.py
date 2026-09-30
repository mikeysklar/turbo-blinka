#!/usr/bin/env python3
"""How long does a new label take when its font has no glyphs loaded yet?

    PYTHONPATH=main247:dt-main:. python3 label_glyphs.py [--trials 10]

A glyph cache miss loads that one glyph, which for BDF is a read of the font file
from the top, and then runs gc.collect(). A new label misses once per distinct
character. "batched" calls font.load_glyphs(text) first, which is the one line a
fix would add, so both ways run the same library code and draw the same thing.

For each font and label class, prints the median of a fresh font's first label,
stock and batched, then a second label on the warm font both ways. The hash is of
what the label draws, and has to match between stock and batched.
"""
import argparse
import hashlib
import os
import platform
import statistics
import time

import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label, label

TEXT = "Welcome to using displayio on CircuitPython!"
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = [
    "fonts/LeagueSpartan-Bold-16.bdf",
    "fonts/Junction-regular-24.bdf",
    "fonts/Junction-regular-24.pcf",
    "fonts/ter-u12n.bdf",
]
CLASSES = [("label", label.Label), ("bitmap_label", bitmap_label.Label)]


def model():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip("\x00\n")
    except OSError:
        return platform.machine()


def drawn(lbl):
    """Hash what a label draws: every tile grid's place, size and pixels."""
    # pylint: disable=protected-access
    h = hashlib.sha256()
    for tg in lbl._local_group:
        bmp = tg.bitmap
        h.update(repr((tg.x, tg.y, bmp.width, bmp.height)).encode())
        h.update(bytes(memoryview(bmp._data).cast("B")))
    return h.hexdigest()[:12]


def first(path, cls, batched):
    """Time a fresh font's first label. Returns ms, the label."""
    font = bitmap_font.load_font(path)
    t0 = time.perf_counter()
    if batched:
        font.load_glyphs(TEXT)
    lbl = cls(font, text=TEXT)
    return (time.perf_counter() - t0) * 1e3, lbl, font


def warm(font, cls, batched):
    t0 = time.perf_counter()
    if batched:
        font.load_glyphs(TEXT)
    cls(font, text=TEXT)
    return (time.perf_counter() - t0) * 1e3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--no-collect", action="store_true",
                    help="diagnostic: make bitmap_font's gc.collect() calls do nothing")
    a = ap.parse_args()
    displayio._stop_background()  # pylint: disable=protected-access
    if a.no_collect:
        # pylint: disable=import-outside-toplevel
        import types
        from adafruit_bitmap_font import bdf, glyph_cache, pcf

        for mod in (bdf, glyph_cache, pcf):
            mod.gc = types.SimpleNamespace(collect=lambda: 0)

    print("# label glyphs, %s, Python %s, %d trials, %d chars, %d distinct, "
          "gc.collect %s, display_text from %s"
          % (model(), platform.python_version(), a.trials, len(TEXT), len(set(TEXT)),
             "disabled" if a.no_collect else "on", os.path.dirname(label.__file__)))
    print("| font | class | first, stock ms | first, batched ms | | "
          "warm, stock ms | warm, batched ms | hash |")
    print("|---|---|---|---|---|---|---|---|")
    for rel in FONTS:
        path = os.path.join(HERE, rel)
        for name, cls in CLASSES:
            row = {}
            hashes = set()
            for batched in (False, True):
                firsts, warms = [], []
                for _ in range(a.trials):
                    ms, lbl, font = first(path, cls, batched)
                    firsts.append(ms)
                    hashes.add(drawn(lbl))
                    warms.append(warm(font, cls, batched))
                row[batched] = (statistics.median(firsts), statistics.median(warms))
            (fs, ws), (fb, wb) = row[False], row[True]
            print("| %s | %s | %.1f | %.1f | %.1fx | %.1f | %.1f | %s |"
                  % (os.path.basename(rel), name, fs, fb, fs / fb, ws, wb,
                     hashes.pop() if len(hashes) == 1 else "DIFFER"))


if __name__ == "__main__":
    main()
