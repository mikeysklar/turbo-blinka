#!/usr/bin/env python3
"""Time bitmap[x, y] = v on an 8 bit bitmap, every pixel of 240x240, median of 10.

    PYTHONPATH=main248:. python3 setitem_8bit.py
"""
import statistics
import time

import displayio

N = 240
bitmap = displayio.Bitmap(N, N, 256)
times = []
for _ in range(10):
    t0 = time.perf_counter()
    for y in range(N):
        for x in range(N):
            bitmap[x, y] = (x + y) & 255
    times.append((time.perf_counter() - t0) * 1000)
print("8 bit bitmap[x, y] = v, %dx%d: median %.1f ms, range %.1f-%.1f, displayio from %s"
      % (N, N, statistics.median(times), min(times), max(times), displayio.__file__))
