# numpy backend, same API as src/pixels.py: one row per call. The px loop is
# gone, the iteration loop stays in Python. This is a rewrite, not a decorator
# swap: escaped points have to be masked and frozen by hand.
import numpy as np


def mandel_row(out, width, dx, cy, max_iter):
    cx = np.arange(width, dtype=np.int32) * dx - (2 << 12)
    x = np.zeros(width, np.int32)
    y = np.zeros(width, np.int32)
    i = np.zeros(width, np.uint8)
    active = np.ones(width, bool)
    for _ in range(max_iter):
        x2 = (x * x) >> 12
        y2 = (y * y) >> 12
        active &= (x2 + y2) <= (4 << 12)
        if not active.any():
            break
        y = np.where(active, ((x * y) >> 11) + cy, y)
        x = np.where(active, x2 - y2 + cx, x)
        i += active
    np.frombuffer(out, np.uint8)[:] = i


def _turbo_bench():
    W, H, IT = 160, 120, 64
    row = bytearray(W)
    dx = (3 << 12) // W
    total = 0
    for r in range(H):
        mandel_row(row, W, dx, ((r * 2) << 12) // H - (1 << 12), IT)
        total += sum(row)
    return total
