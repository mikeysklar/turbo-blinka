#!/usr/bin/env python3
"""rotozoom: pixels and dirty area, separately, over a spread of angles, scales,
clips and skip indexes, so a change that only moves the dirty area shows as such.

    PYTHONPATH=main249:. python3 rotozoom_check.py
"""
import hashlib

import bitmaptools
import displayio

pixels = hashlib.sha256()
rows = []
src = displayio.Bitmap(40, 30, 16)
for y in range(30):
    for x in range(40):
        src[x, y] = (x * 3 + y * 5) % 16
for angle in (0.0, 0.3, 1.2, 3.14159, -0.7):
    for scale in (0.5, 1.0, 2.5):
        for clip in (None, ((10, 10), (60, 50)), ((-20, -20), (5, 5)), ((90, 70), (120, 100))):
            for skip in (None, 3):
                d = displayio.Bitmap(80, 60, 16)
                d._finish_refresh()  # pylint: disable=protected-access
                kw = {} if clip is None else {"dest_clip0": clip[0], "dest_clip1": clip[1]}
                bitmaptools.rotozoom(d, src, angle=angle, scale=scale, skip_index=skip, **kw)
                pixels.update(bytes(memoryview(d._data).cast("B")))  # pylint: disable=protected-access
                a = d._dirty_area  # pylint: disable=protected-access
                rows.append("%s %s %s %s: %d,%d,%d,%d" % (angle, scale, clip, skip, a.x1, a.y1, a.x2, a.y2))
print("# rotozoom check, %d cases, displayio from %s" % (len(rows), displayio.__file__))
print("pixels sha256 %s" % pixels.hexdigest()[:12])
print("\n".join(rows))
