# turbo on Blinka: measured results

Running log of every number. Raw logs are in `logs/`, one file per host per
backend. Update this file whenever a run is added.

## Setup

| | Pi Zero 2 W | Pi 5 |
|---|---|---|
| Host | `pizero2w.local` | `pi5.local` |
| SoC | BCM2710A1, 4x Cortex-A53 1 GHz, 512 MB | BCM2712, 4x Cortex-A76 2.4 GHz, 4 GB |
| OS | Raspberry Pi OS desktop 64-bit, Debian 13 trixie | same |
| Python | 3.13.5, venv `~/env --system-site-packages` per the Learn guide | same |
| Blinka | adafruit-blinka 9.2.0, adafruit-blinka-displayio 2.3.2 | same |
| Backends | Cython 3.3.0, Numba 0.67.0 / llvmlite 0.49.0, numpy 2.2.4 (system) | same |
| Compiler | gcc (Debian 13), `-O2` | same |

Benchmark: turbo's own mandelbrot example, `src/pixels.py` (fixed point, the
`@turbo.viper` source) and `src/mandel_float.py`, copied unmodified from
[turbo-cli](https://github.com/mikeysklar/turbo-cli) into `bench/src/`. 160x120, 64 iterations,
407,644 inner iterations. Median of 8 trials, milliseconds. Same workload and
same checksum as the board table in [turbo](https://github.com/mikeysklar/turbo). Harness:
`bench/run_bench.py`.

## 2026-09-18: mandelbrot, all backends

Every row returned checksum 407644 except the float source (407790, expected:
float and fixed point round differently, same as on the boards).

| Variant | Source changed? | Pi Zero 2 W ms | vs int | Pi 5 ms | vs int |
|---|---|---|---|---|---|
| CPython, float source | | 564 | | 72.7 | |
| CPython, int source (baseline) | | 1 308 | 1.0x | 142.5 | 1.0x |
| Cython, source unmodified | no | 962 | 1.4x | 104.2 | 1.4x |
| numpy, one row per call | rewrite, same API | 1 581 | 0.8x | 158.9 | 0.9x |
| numpy, whole frame | rewrite, new API | 115.0 | 11x | 10.5 | 14x |
| Numba, source unmodified | no | 8.6 | 152x | 1.9 | 75x |
| Cython, typed signature | decorator + signature lines | 6.0 | 218x | 1.2 | 119x |
| C reference, `gcc -O2` (ceiling) | | 4.8 | 272x | 1.05 | 135x |

## One-time costs

| | Pi Zero 2 W | Pi 5 |
|---|---|---|
| `pip install cython` | 19 s | not timed |
| Cython build, unmodified source | 28 s | 3.4 s |
| Cython build, typed source | 70 s | 8.8 s |
| Cython cost at run time | none | none |
| `pip install numba` (wheels, no source build) | 55 s | 9 s |
| Numba + llvmlite on disk | 204 MB | 204 MB |
| `import numba`, every process | 2.3 s warm, 4.7 s first time | 0.25 s |
| Numba first-call JIT, every process (`cache=False`) | 2.4 s warm, 4.1 s first time | 0.28 s |
| `import numpy`, every process | 0.66 s | 0.06 s |

`numba.njit(cache=True)` on a second process: measured 2026-09-21, see "The CPython
shim" below.

## Against the boards, like for like

Same workload, board numbers from [turbo](https://github.com/mikeysklar/turbo). Interpreted against interpreted,
compiled against compiled.

| | Interpreted ms | Compiled ms | Gain |
|---|---|---|---|
| Metro RP2040 | 8 296 int bytecode | 384 `@viper` | 22x |
| Metro RP2350 | 4 547 int bytecode | 261 `@viper` | 17x |
| EK-RA8D1 (Cortex-M85) | 1 567 int bytecode | 47 `@viper` | 33x |
| Pi Zero 2 W | 1 308 int CPython | 6.0 typed Cython | 218x |
| Pi 5 | 142.5 int CPython | 1.2 typed Cython | 119x |

## Findings so far

- Types do the work, not the compiler. Cython on unmodified source is 1.4x. The
  same body with typed locals is within 25% of hand-written C.
- The viper source ports with no body changes. Cython needs the decorator and
  signature lines rewritten (`ptr8` to `cython.uchar[:]`, `int` to
  `cython.int`, int locals declared). Numba needs nothing: the shim sets
  `turbo.viper = numba.njit`.
- On CPython the fixed-point source is 2x slower than float until it is
  compiled. Then it is the fastest version.
- Numba's price is startup: about 5 to 9 s per process on a Zero 2 W and
  204 MB of disk. On a Pi 5 it is about half a second.
- numpy only pays when the code is restructured to whole-frame operations, and
  even then it is 10x to 20x behind Cython and Numba here. Keeping the per-row
  API is slower than plain Python.
- Numba infers 64-bit ints. viper and `cython.int` are 32-bit and wrap. No
  difference on this kernel. Not yet tested on hash or CRC code that relies on
  the wrap.
- CPython before 3.14 evaluates `out: ptr8` at def time, so the Blinka shim must
  define `ptr8`, `ptr16`, `ptr32`, `uint` or the viper source raises NameError.

## 2026-09-18: Blinka_Displayio refresh, before

`bench/displayio_refresh.py`. `display.refresh()` on a 240x240 16-bit
`BusDisplay` through the public API, adafruit-blinka-displayio 2.3.2 as
installed by pip. The bus discards the bytes, so this is compositing cost only,
no SPI time. Median of 5, milliseconds. Output sha256 `d39c3852b738` on both
hosts.

| Scene | Pixels composited | Pi Zero 2 W ms | fps | Pi 5 ms | fps |
|---|---|---|---|---|---|
| Full screen, after `bitmap.fill()` | 115 200 | 3 560 | 0.3 | 325.7 | 3.1 |
| Move a 32x32 sprite 8 px | 1 280 | 42.6 | 23.5 | 4.0 | 253 |
| 20 `bitmaptools.draw_line`, then refresh | 115 200 | 3 594 | 0.3 | 327.9 | 3.0 |

Cost is flat at about 31 ms per 1000 pixels on the Zero 2 W and 2.8 ms on the
Pi 5, whatever the scene. It is all the per-pixel loop in `TileGrid._fill_area`.

Two things found on the way:

- A full-screen change is composited and sent twice. One `bitmap.fill()` yields
  two identical dirty areas `(0,0)-(240,240)`, so 115 200 pixels are drawn for a
  57 600 pixel screen. `TileGrid._get_refresh_areas` passes the display's area
  list to `Bitmap._get_refresh_areas`, which appends the bitmap's dirty area,
  and then appends its own transformed copy of the same area
  (`displayio/_tilegrid.py:449-470`). The C version
  (`shared-module/displayio/TileGrid.c`, `displayio_tilegrid_get_refresh_areas`)
  only reads the bitmap's area into a local and links its own `dirty_area` to
  `tail`, so the bitmap's area never joins the display list.
  Fixing it would halve these numbers before any turbo work.
- displayio starts a background thread that loops on `time.sleep(0.0)`. Checked
  whether it steals time from `refresh()`: with `--no-background` the Zero 2 W
  goes 3 560 to 3 505 ms (1.5%), the Pi 5 does not move. Not a factor.

## 2026-09-18: Blinka_Displayio refresh, after

Same bench with `--fast`. `fastpath/tilegrid_fast.py` monkeypatches
`TileGrid._fill_area` on the pip-installed package: per-call setup stays in
Python, the palette is resolved once per index into a lookup table, and the
pixel loop moves to `fastpath/fill_kernel.py`, a flat-buffer function with int
arguments only. Covers Bitmap (1 to 8 bits) + Palette on a 16-bit display,
anything else falls through to the original. 55 of 55 `_fill_area` calls took
the fast path. Output sha256 `d39c3852b738` in every cell: byte-identical to
stock.

Full-screen refresh, 240x240, milliseconds (fps). Still includes the
double-composite found above.

| Kernel run as | Pi Zero 2 W | vs stock | Pi 5 | vs stock |
|---|---|---|---|---|
| Stock 2.3.2 | 3 560 (0.3) | 1.0x | 325.7 (3.1) | 1.0x |
| Fast path, plain Python | 1 241 (0.8) | 2.9x | 121.8 (8.2) | 2.7x |
| Fast path, Numba | 34.1 (29) | 104x | 4.6 (219) | 71x |
| Fast path, typed Cython | 26.8 (37) | 133x | 3.5 (289) | 93x |

Move a 32x32 sprite 8 px (1 280 pixels):

| Kernel run as | Pi Zero 2 W ms | Pi 5 ms |
|---|---|---|
| Stock 2.3.2 | 42.6 | 4.0 |
| Fast path, plain Python | 16.1 | 1.6 |
| Fast path, Numba | 1.2 | 0.1 |
| Fast path, typed Cython | 1.0 | 0.1 |

Small areas are now bounded by the Python per-call setup and the palette table
build, not the pixels. Cython build of the kernel: 74 s on the Zero 2 W.
Numba startup as in the mandelbrot table (4.6 s import on the Zero 2 W here).

## 2026-09-18: double composite fixed

`patches/blinka-displayio-double-composite.patch`, 9 lines in
`TileGrid._get_refresh_areas`: read the bitmap's dirty area into a local list,
like the C version, instead of appending it to the display's list. Measured by
running the same bench against a patched copy of the installed package
(`PYTHONPATH`), installed package untouched. Logs:
`logs/*-displayio-doublefix-20260918.log`.

Full-screen refresh, 240x240, milliseconds (fps):

| | Pi Zero 2 W | vs stock | Pi 5 | vs stock |
|---|---|---|---|---|
| Stock 2.3.2 | 3 595 (0.3) | 1.0x | 325.7 (3.1) | 1.0x |
| Patch only | 1 796 (0.6) | 2.0x | 162.7 (6.1) | 2.0x |
| Cython fast path only | 27.2 (37) | 132x | 3.5 (287) | 93x |
| Patch + Cython fast path | 13.7 (73) | 262x | 1.8 (568) | 181x |

Pixels composited per full refresh go from 115 622 to 57 811. The last pixel
payload on the bus is identical with and without the patch (sha256
`78b6f072aa84`, 115 200 bytes). Moving a sprite is unchanged (42.4 ms stock,
1.0 ms fast path on the Zero 2 W): that path never consulted the bitmap.

Partial change check, two pixels set in a 32x32 sprite placed at (50,60):

| | Areas redrawn for the sprite |
|---|---|
| Stock | `(0,0)-(32,32)` and `(50,60)-(82,92)` |
| Patched | `(50,60)-(82,92)` |

Stock also redraws the bitmap's own untransformed rectangle, which is the wrong
place on screen whenever the TileGrid is not at the origin.

At 13.7 ms the compositing is no longer the limit on a Zero 2 W. Sending
115 200 bytes over SPI at 24 MHz takes about 38 ms.

## 2026-09-19: real display, PiTFT Plus 3.5" on the Pi 5

Adafruit product 2441, HX8357D, 480x320, SPI0 at 24 MHz, DC on GPIO25.
`bench/pitft_demo.py`. Times are `display.refresh()` including the SPI transfer.
Log: `logs/pi5-pitft35-20260919.log`.

| | Full-screen fill ms | fps | Move 48x48 sprite ms |
|---|---|---|---|
| Stock 2.3.2 | 1 157 | 0.9 | 11.2 |
| Double composite patch | 577 | 1.7 | 11.2 |
| Cython fast path | 261 | 3.8 | 2.7 |
| Patch + Cython fast path | 131 | 7.7 | 2.7 |

Same 2.0x from the patch as the headless bench. With both, the 131 ms is mostly
the wire: 307 200 bytes at 24 MHz is 102 ms.

[Side-by-side video](https://drive.google.com/file/d/14NT4r2asXWckTx3YOvZuRicXdUTdyauY/view),
stock on the left, patched on the right, 10 seconds each: 9 full-screen fills
against 18. How it was cut: `split-video-title-mp4.md`.

Upstream PR for the patch:
[adafruit/Adafruit_Blinka_Displayio#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178).

Setup notes for a Pi 5:

- SPI is off on a fresh Pi OS image: `sudo raspi-config nonint do_spi 0`.
- Do not pass `chip_select=board.CE0` to `FourWire`. spidev owns CE0 and lgpio
  fails with "GPIO busy". Leave it out and the kernel toggles CE0 per transfer.

## 2026-09-20: PR 1 + PR 2 together, no compiler

The combination that needs no dependencies: the upstream PR 1 file (`299c87a`)
plus the fast path with its plain-Python kernel. Full-screen refresh,
milliseconds. Log: `logs/pr1-pr2-combined-20260920.log`. Last pixel payload
`78b6f072aa84` in every headless run.

| | Pi Zero 2 W, headless 240x240 | Pi 5, headless 240x240 | Pi 5, PiTFT 3.5" 480x320 |
|---|---|---|---|
| Stock 2.3.2 | 3 565 | 326.9 | 1 149 |
| PR 1 | 1 786 (2.0x) | 163.1 (2.0x) | 572 (2.0x) |
| PR 2 | 1 252 (2.8x) | 122.2 (2.7x) | 600 (1.9x) |
| PR 1 + PR 2 | 622 (5.7x) | 61.2 (5.3x) | 300 (3.8x) |

Move a sprite (32x32 headless, 48x48 on the PiTFT):

| | Pi Zero 2 W | Pi 5 | Pi 5, PiTFT |
|---|---|---|---|
| Stock and PR 1 | 42.4 | 3.9 | 11.2 |
| PR 2, with or without PR 1 | 16.1 | 1.6 | 6.1 |

The two gains multiply cleanly headless (2.0 x 2.8 = 5.6). On the PiTFT PR 2
alone is 1.9x, not 2.7x: stock sends the frame twice, about 200 ms of SPI that
PR 2 does not remove. PR 1 removes it.

## 2026-09-20: fast path correctness scenes

`bench/displayio_scenes.py`: 20 scenes on a headless 96x64 display, stock
against the fast path, sha256 of every byte sent. Bitmap depths 1, 2, 4, 8 bit,
flip_x, flip_y, transpose_xy, group scale 2 and 3, sprite sheet, transparent
palette entries, overlapping sprites, clipping, hidden, display rotation 90,
180, 270, and a ColorConverter scene that must fall back. 0 differ with the
Python, Cython and Numba kernels. Log: `logs/pi5-displayio-scenes-20260920.log`.

Four deliberate kernel bugs were caught by 15, 19, 2 and 4 of the 20 scenes.

## 2026-09-20: PR 2 in the file, draft #179

Branch `fill-area-fast-path` (0fa7f56 + 4973eb0), on top of PR 1. Pi 5 only.
Draft: [#179](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/179).

| Pi 5 | PR 1 | PR 1 + PR 2 in the file |
|---|---|---|
| Full-screen refresh, no display, 240x240, ms | 163.1 | 52.2 |
| PiTFT 3.5", full-screen fills in 10 s (stock: 9) | 18 | 34 |
| 20 scenes, bytes sent | | identical to PR 1 |

Last pixel payload sha256 `78b6f072aa84`, unchanged.

An independent review fuzzed about 8 000 random cases against the old loop: 0
differences. It found small updates got slower with a big palette, because the
colour table is rebuilt on every call. Fixed in 4973eb0: areas with fewer
pixels than the palette has entries use the old loop. 8-bit bitmap, 256 colour
palette, microseconds:

| Changed area | PR 1 | PR 2 before the fix | PR 2 |
|---|---|---|---|
| 1x1 | 24 | 217 | 22 |
| 4x4 | 66 | 230 | 67 |
| 8x8 | 211 | 273 | 213 |
| 16x16 | 791 | 438 | 440 |
| 32x32 | 3 107 | 1 115 | 1 118 |
| 240x240 | 175 810 | 52 243 | 52 263 |

Zero 2 W numbers are in the next sections. Video: stock on top, PR 1 + PR 2 on the bottom,
[Drive](https://drive.google.com/file/d/16KWFTQvOk2QP8yC4XHw4lfDtFrJ-eeeQ/view).

### 2026-09-21: two review fixes on #179

Two review comments, both fixed as new commits on `fill-area-fast-path`:

- fdef1d4, from Melissa's AI review: the fast path took `Bitmap` and `Palette`
  subclasses, which can override `_get_pixel` or `_get_color`. It now takes the
  exact types only; subclasses use the old loop.
- 161bde2, from Copilot: small areas were compared against the palette length,
  but the table only resolves `min(len(palette), 1 << bits_per_value)` entries.

`bench/sub179.py`, Pi 5, the 20 scenes plus a Bitmap subclass and a Palette
subclass, compared with PR 1:

| | 20 scenes | Bitmap subclass | Palette subclass |
|---|---|---|---|
| #179 before the fixes | match | different | different |
| #179 with both fixes | match | match | match |

`VALUES=2 bench/displayio_small_area.py`, Pi 5, 1-bit bitmap with a 256 colour
palette, microseconds:

| Changed area | PR 1 | fdef1d4 | 161bde2 |
|---|---|---|---|
| 1x1 | 21 | 22 | 22 |
| 4x4 | 62 | 63 | 37 |
| 8x8 | 194 | 194 | 82 |
| 16x16 | 717 | 260 | 260 |
| 240x240 | 160 454 | 56 831 | 56 629 |

With the default 8-bit bitmap nothing moved (4x4: 67 and 68).

`pitft_demo.py` on the PiTFTs, median ms, before and after both fixes:

| | Pi 5, 3.5" | Zero 2 W, 2.8" |
|---|---|---|
| Full-screen fill | 296.6 / 295.9 | 892.4 / 887.0 |
| Sprite move | 6.0 / 6.0 | 36.7 / 36.5 |

Logs: `logs/pi5-pr179-subclass-20260921.log`, `logs/pi5-pr179-gate-20260921.log`,
`logs/pitft-pr179-fixes-20260921.log`.

## 2026-09-20: compiled loop on real displays, both Pis

`fastpath/cy/fill_pixels.py`: the #179 `_fill_pixels`, same arguments, typed
locals, built with `cythonize -i -3`. Picked up by a 4-line try-import hook in a
copy of `_tilegrid.py` (what PR 4b would be). Zero 2 W: PiTFT Plus 2.8" (2423),
ILI9341, 320x240. Pi 5: PiTFT Plus 3.5" (2441), HX8357D, 480x320. SPI 24 MHz.
`bench/pitft_demo.py`, median of 6 fills and 20 moves.

| Full-screen fill, ms | Zero 2 W, 2.8" | Pi 5, 3.5" |
|---|---|---|
| Stock 2.3.2 | 4 871 | 1 149 |
| PR 1 | 2 460 (2.0x) | 572 (2.0x) |
| PR 1 + PR 2 | 889 (5.5x) | 297 (3.9x) |
| PR 1 + PR 2 + compiled loop | 75.6 (64x) | 130.6 (8.8x) |

| Move 48x48 sprite 10 px, ms | Zero 2 W, 2.8" | Pi 5, 3.5" |
|---|---|---|
| Stock 2.3.2 | 94.2 | 11.2 |
| PR 1 | 94.6 | 11.2 |
| PR 1 + PR 2 | 36.5 | 6.1 |
| PR 1 + PR 2 + compiled loop | 4.7 | 2.8 |

| With the compiled loop | Zero 2 W | Pi 5 |
|---|---|---|
| Full-screen fills in 10 s | 90 | 75 (stock: 9) |
| No display, 240x240, ms | 13.7 | 1.8 |
| 20 scenes, bytes sent | identical to PR 1 | identical to PR 1 |
| Build time, s | 75 | 10 |

Last pixel payload sha256 `78b6f072aa84` on both. The Zero beats the Pi 5 with
the compiled loop because its screen has half the pixels: what is left is SPI.
PR 1 does not change the sprite move: moving a TileGrid dirties no bitmap.
Log: `logs/pizero2w-pitft28-20260920.log`.

## 2026-09-21: Numba on real displays, both Pis

`fastpath/nb/fill_pixels.py`: same name and arguments as the Cython twin, so the
same try-import hook in the `pr4` copy of `_tilegrid.py` picks it up
(`PYTHONPATH=pr4:fastpath/nb`). Numba cannot compile attribute reads, so a plain
Python wrapper unpacks the tilegrid and bitmap and calls `fastpath/fill_kernel.py`
under `numba.njit(cache=True)`. No build step. Same displays, SPI 24 MHz,
`bench/pitft_demo.py`, median of 6 fills and 20 moves. Cython columns are the
2026-09-20 run above.

| | Zero 2 W, Cython | Zero 2 W, Numba | Pi 5, Cython | Pi 5, Numba |
|---|---|---|---|---|
| Full-screen fill, ms | 75.6 (64x) | 80.3 (61x) | 130.6 (8.8x) | 132.2 (8.7x) |
| Move 48x48 sprite 10 px, ms | 4.7 | 5.0 | 2.8 | 2.8 |
| Full-screen fills in 10 s | 90 | 93 | 75 | 73 |
| 20 scenes, bytes sent | identical to PR 1 | identical to PR 1 | identical to PR 1 | identical to PR 1 |

Numba figures are the second, cached run. Three runs each: 80.5, 80.3, 80.2 ms
on the Zero 2 W and 132.2, 133.6, 132.1 ms on the Pi 5.

| Numba start, every process | Zero 2 W | Pi 5 |
|---|---|---|
| `import numba` | 1.6 s (2.1 s first time) | 0.21 s |
| First call, cache empty | 6.6 s | 0.60 s |
| First call, cached | 1.5 s | 0.17 s |

The compile lands on the setup refresh, before the timed fills: the first timed
fill was 86 ms on the Zero 2 W and 135 ms on the Pi 5. On a real display both
backends are SPI-bound, so they are within 6% of each other.
Logs: `logs/pizero2w-pitft28-numba-20260921.log`, `logs/pi5-pitft35-numba-20260921.log`.

## 2026-09-20: bitmaptools on stock, and the boundary_fill fix (#180)

`bench/bitmaptools_bench.py`, 240x240 4-bit bitmap, no display. Median of 5 on
the Pi 5, of 3 on the Zero 2 W. Each case hashes the result bitmap and its dirty
area; every hash is the same on both Pis.

| Stock 2.3.2, ms | Zero 2 W | Pi 5 |
|---|---|---|
| `bitmap[x, y] = v`, every pixel | 1 339 | 127.2 |
| `v = bitmap[x, y]`, every pixel | 340 | 40.0 |
| `Bitmap.fill` | 4.3 | 0.4 |
| `fill_region`, whole bitmap | 1 300 | 124.0 |
| `blit`, whole bitmap | 2 011 | 196.8 |
| `blit` 64x64, skip_source_index | 135.5 | 13.4 |
| `rotozoom` 64x64, 30 degrees, scale 2 | 550.7 | 53.9 |
| `draw_line` x 20 | 112.7 | 10.9 |
| `draw_circle` x 20 | 150.2 | 14.5 |
| `boundary_fill` inside a radius 80 ring | 190 980 | 17 406 |

Two findings:

- `boundary_fill` keeps its visited points in a list and tests `not in` for
  every neighbour, so the cost grows with the square of the area.
- Every `bitmap[x, y] = v` builds two `Area` objects and runs a union and an
  overlap for one pixel. `fill_region` and `Bitmap.fill` write the same bitmap
  (same hash): 1 300 ms against 4.3 ms on the Zero 2 W.

PR 5a, [#180](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/180),
opened 2026-09-20: visited list becomes a set, two lines, branch
`boundary-fill-set` (a967fab) on upstream main.

| `boundary_fill` inside a ring, ms | Zero 2 W | Pi 5 |
|---|---|---|
| Stock | 190 980 | 17 406 |
| #180, visited points in a set | 2 680 (71x) | 273.5 (64x) |
| #180 + c619924, queued points in a deque, each queued once | 791.5 (241x) | 79.0 (220x) |

Result hash `6d73c4f8bb54` in every row, whole bench `8bed9684ccfb`. Logs:
`logs/*-bitmaptools-stock-20260920.log`, `logs/*-bitmaptools-pr5a-20260920.log`.

2026-09-21: Melissa's review suggested the deque, added to #180 as c619924. 150
random bitmaps (sizes, depths, start points, replaced colour None/-1/0/1) give the
same data and dirty area as a967fab. Logs: `logs/*-bitmaptools-pr5c-20260921.log`.

| `boundary_fill_demo.py` on the PiTFT, total fill time | #180 set only | + deque |
|---|---|---|
| Pi 5, 3 rings | 0.48 s | 0.14 s |
| Zero 2 W, 2 rings | 0.77 s | 0.35 s |

## 2026-09-21: the CPython shim, four ways to run one project

turbo-cli `cli/turbo.py`, the `turbo` module for CPython (not committed there
yet). One project folder, `src/pixels.py` (turbo's mandelbrot) and a `code.py`
that imports `turbo`, then `pixels`, and times `_turbo_bench()` twice.
Milliseconds. Checksum 407644 in every row.

| Pi 5 | `pixels` from | import turbo + pixels | first frame | later frames |
|---|---|---|---|---|
| `python3 code.py`, nothing built | `src/pixels.py` | 7 | 158 | 141.4 |
| `TURBO=numba`, first ever run | `src/pixels.py` | 879 | 318.5 | 2.0 |
| `TURBO=numba`, second run, cached | `src/pixels.py` | 256 | 171.6 | 1.9 |
| after `turbo build --target cpython` | `lib/turbo/cpython/pixels.*.so` | 3 | 1.2 | 1.2 |
| `TURBO=source`, `.so` present | `src/pixels.py` | 3 | 141.9 | 139.8 |

| Zero 2 W | import turbo + pixels | first frame | later frames |
|---|---|---|---|
| `python3 code.py`, nothing built | 44 | 1 408 | 1 376 |
| `TURBO=numba`, first ever run | 5 130 | 4 978 | 8.8 |
| `TURBO=numba`, second run, cached | 3 062 | 1 427 | 8.8 |
| `TURBO=numba`, third run, cached | 1 918 | 1 468 | 8.8 |

`cache=True` answers the open question: it cuts the first-call compile by about
two thirds (Pi 5 318 to 172 ms, Zero 2 W 4 978 to about 1 450 ms). What is left
is mostly `import numba`. A cached start on the Zero 2 W still costs about 3.4 s
against 44 ms from source and 3 ms for a Cython `.so`, and the cached first
frame takes as long as one frame of plain Python. Numba pays for long-running
programs, not quick scripts.

Under `TURBO=numba` a function numba cannot compile (an attribute read, a
`ptr8()` cast) printed one line and ran from source with the right result.

## Other runs

| Date | Host | What | Result |
|---|---|---|---|
| 2026-09-18 | Pi Zero 2 W | `bench/life.py`, Conway 64x32, plain CPython | 10.49 ms/gen |
| 2026-09-18 | Pi 5 | same | 1.15 ms/gen |
