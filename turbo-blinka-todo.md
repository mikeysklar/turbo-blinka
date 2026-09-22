**Next: faster `fill_region` (PR 5b)**

- Every pixel builds two `Area` objects, redoes dirty math
- 1300 ms on Zero 2 W, 124 ms on Pi 5
- `Bitmap.fill` does the same in 4.3 and 0.4 ms
- Fix: mark dirty rectangle once, write pixels directly
- Matches CircuitPython's C version
- Check with `bitmaptools_bench.py`, then time both Pis
- Then `draw_line`, `draw_circle`, `blit`, `rotozoom`, one PR each

**Dropped 2026-09-20: PR 4a to 4d, widen the #179 fast path**

- 4a: `ColorConverter`, images without a palette, ~3x
- 4b: `OnDiskBitmap`, images read from a file, ~2x
- 4c: `vectorio` shapes, ~3x
- 4d: mono and under-16-bit displays, ~3x
- Gains were guesses, never measured
- Each changes #179's shared loop, needs new test scenes
- Gains don't stack, each covers different images
