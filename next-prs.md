# Next PRs, after 5b

Widen the #179 fast path to the other image sources. Measured on stock 2.4.0
with `bench/displayio_sources.py`, 2026-09-22: a full 240x240 redraw, no display
attached, one layer per scene. Logs: `logs/*-displayio-sources-main240-20260922.log`.

| Image source | Zero 2 W ms | Pi 5 ms | Behind fast path | PR |
|---|---|---|---|---|
| Bitmap + Palette, the #179 fast path | 514 | 52 | 1.0x | done |
| OnDiskBitmap, 16-bit BMP | 3 548 | 315 | 6.9x / 6.0x | 4b |
| OnDiskBitmap, 24-bit BMP | 3 403 | 302 | 6.6x / 5.8x | 4b |
| Bitmap + ColorConverter | 3 209 | 283 | 6.2x / 5.4x | 4a |
| OnDiskBitmap, 8-bit BMP | 2 088 | 187 | 4.1x / 3.6x | 4b |
| Mono display, 128x64 | 303 | 28 | 4.1x / 3.7x | 4d |
| vectorio Polygon | 1 641 | 163 | 3.2x / 3.1x | 4c |
| vectorio Rectangle | 1 390 | 133 | 2.7x / 2.5x | 4c |
| vectorio Circle | 1 302 | 122 | 2.5x / 2.3x | 4c |

The last column is the ceiling, not a promise: it is what a PR would gain only
if the new code matched the #179 path. Pixels sent and output hash
(`55ada9a3802a`) are identical on both Pis.

Order, by the numbers rather than the old guesses:

- 4a: `ColorConverter`. The slowest three rows may share one fix, because a
  16-bit or 24-bit `OnDiskBitmap` uses a `ColorConverter` as its pixel shader.
  Read in the source, not yet measured.
- 4b: `OnDiskBitmap`. What is left after 4a, above all the 8-bit path.
- 4d: mono and under-16-bit displays. 303 ms for a 128x64 OLED on a Zero 2 W is
  about 3 frames a second.
- 4c: `vectorio` shapes. Closest to the fast path already.

Each one changes the shared pixel loop and needs its own test scenes.
