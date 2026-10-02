Title: Stop crashes when a pixel value is too big for an 8 or 16 bit bitmap

## What
Too-big values now raise a clear `ValueError` or get trimmed, matching CircuitPython, instead of crashing.

## Why
On 8 and 16 bit bitmaps, setting a pixel, `blit`, `fill_region` and `rotozoom` crashed with a confusing `struct.error`.

## Tested
Raspberry Pi 5 and Pi Zero 2 W, Python 3.13.5. Same results on both.

| 8 bit bitmap, value 256 | main | this PR | CircuitPython, per its C source |
|---|---|---|---|
| `b[0, 0] = 256` or `= -1` | `struct.error` | `ValueError: value must be 0-255` | same |
| `fill_region(b, ..., 256)` | `struct.error` | `ValueError: out of range of target` | same |
| `blit` from a 16 bit bitmap | `struct.error` | stores 0 | stores 0 |
| `rotozoom` from a 16 bit bitmap | `struct.error` | stores 0 | stores 0 |

On a 16 bit bitmap, setting 65536 and `fill_region` behave the same way.

Unchanged on purpose: bitmaps under 8 bits and `fill` still trim quietly, so code that works today keeps working. CircuitPython raises there.

Everything else draws the same pixels:

| check | result |
|---|---|
| `bitmaptools` operations | identical, except `rotozoom`'s changed area, below |
| 120 earlier `blit` scenes | 119 identical, the other is the 16 into 8 bit case above |
| 120 `rotozoom` cases: angles, scales, clips, skip index | identical pixels |

`rotozoom` now marks its whole area as changed once, as CircuitPython does. In all 120 cases that area covers everything main marked and stays inside the bitmap. It is about twice as fast:

| median of 3 runs | main | this PR |
|---|---|---|
| Pi 5, `rotozoom` 64x64 at 2x | 54.3 ms | 28.8 ms |
| Zero 2 W, same | 547.2 ms | 263.9 ms |
| Pi 5, `b[x, y] = v` 240x240, 8 bit | 137.6 ms | 141.2 ms |
| Zero 2 W, same | 1426.6 ms | 1429.7 ms |

## AI assistance
Written with Claude Code. I ran every test on both Pis myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
