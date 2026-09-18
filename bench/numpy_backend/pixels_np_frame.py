# numpy backend the way numpy wants it: the whole frame at once. Same math and
# same checksum as src/pixels.py, but the API changed from row to frame, so the
# caller has to change too.
import numpy as np


def mandel_frame(out, width, height, max_iter):
    dx = (3 << 12) // width
    cx = (np.arange(width, dtype=np.int32) * dx - (2 << 12))[None, :]
    cy = ((np.arange(height, dtype=np.int32) * 2 << 12) // height - (1 << 12))[:, None]
    x = np.zeros((height, width), np.int32)
    y = np.zeros((height, width), np.int32)
    i = np.zeros((height, width), np.uint8)
    active = np.ones((height, width), bool)
    for _ in range(max_iter):
        x2 = (x * x) >> 12
        y2 = (y * y) >> 12
        active &= (x2 + y2) <= (4 << 12)
        if not active.any():
            break
        y = np.where(active, ((x * y) >> 11) + cy, y)
        x = np.where(active, x2 - y2 + cx, x)
        i += active
    np.frombuffer(out, np.uint8).reshape(height, width)[:] = i


def _turbo_bench():
    W, H, IT = 160, 120, 64
    frame = bytearray(W * H)
    mandel_frame(frame, W, H, IT)
    return sum(frame)
