#!/usr/bin/env python3
"""What does a newline in a label's text cost once the whole text is batch loaded?

    PYTHONPATH=main247:bf-243:dt-main:. python3 label_newline.py

No font has a glyph for "\\n", and the per-character loops never ask for one. A
batch load of the whole text does. Times 20 updates of a two line label after the
first, all glyphs already loaded, and the same text on one line for comparison.
"""
import os
import statistics
import sys
import time

import displayio
import adafruit_bitmap_font
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label, label

HERE = os.path.dirname(os.path.abspath(__file__))


def updates(cls, font_file, sep):
    font = bitmap_font.load_font(os.path.join(HERE, "fonts", font_file))
    lbl = cls(font, text="count" + sep + "0123456789")
    times = []
    for i in range(20):
        t0 = time.perf_counter()
        lbl.text = "count" + sep + str(9876543210 - i)
        times.append((time.perf_counter() - t0) * 1e3)
    return statistics.median(times)


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# label newline, display_text from %s, bitmap_font from %s"
          % (os.path.dirname(label.__file__), os.path.dirname(adafruit_bitmap_font.__file__)))
    print("| font | class | update, one line ms | update, two lines ms |")
    print("|---|---|---|---|")
    for font_file in ("LeagueSpartan-Bold-16.bdf", "Junction-regular-24.pcf"):
        for name, cls in (("label", label.Label), ("bitmap_label", bitmap_label.Label)):
            print("| %s | %s | %.1f | %.1f |" % (font_file, name, updates(cls, font_file, " "),
                                                updates(cls, font_file, "\n")))


if __name__ == "__main__":
    sys.exit(main())
