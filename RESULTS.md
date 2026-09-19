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

Not measured yet: `numba.njit(cache=True)` on a second process.

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

## Other runs

| Date | Host | What | Result |
|---|---|---|---|
| 2026-09-18 | Pi Zero 2 W | `bench/life.py`, Conway 64x32, plain CPython | 10.49 ms/gen |
| 2026-09-18 | Pi 5 | same | 1.15 ms/gen |
