# PR plan: Blinka_Displayio, one at a time

Target repo: `adafruit/Adafruit_Blinka_Displayio`. One PR open at a time, next
one starts after the previous merges. Numbers are full-screen refresh, 240x240,
16-bit, from `RESULTS.md`.

Rule, 2026-09-20: what goes upstream is plain Python. No compiler, no new
dependency, so it runs on every platform Blinka runs on, minimal Linux builds
included. Compiled code comes last and only if Adafruit asks for it.

## Short list

- **PR 1:** Draw bitmap changes once ([#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178), open). Displayio. 2.0x
- **PR 2:** Plain-Python fast pixel loop ([#179](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/179), draft). Displayio. 2.9x
- **PR 5:** Faster bitmaptools drawing functions, plain Python. Displayio. Not measured
- **Maybe:** check `<` versus `<=`, line 441. Displayio
- Cython backend for `turbo build` (done 2026-09-20, `--target cpython`). turbo-cli. 119x
- Run `turbo bench` over ssh. turbo-cli
- CPython shim with viper types. turbo
- **Last, only if Adafruit asks. PR 4a:** Compiled loop as a package. New repo. 64x on a Zero 2 W display
- **Last, only if Adafruit asks. PR 4b:** Use the compiled loop if installed. Displayio

`~` means not measured yet. Displayio is `adafruit/Adafruit_Blinka_Displayio`.

## Detail

| PR | What | Gain | State | Git repo |
|---|---|---|---|---|
| 1 | Double composite fix, all in `TileGrid._get_refresh_areas` | 2.0x | Open 2026-09-19: [#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178) | `adafruit/Adafruit_Blinka_Displayio` |
| 2 | `_fill_area` fast path, plain Python, no dependencies | 2.9x | Draft 2026-09-20: [#179](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/179), builds on #178 | `adafruit/Adafruit_Blinka_Displayio` |
| 5 | `bitmaptools`, plain Python | | Not measured yet | `adafruit/Adafruit_Blinka_Displayio` |
| | Cython backend for `turbo build` | 119x on mandelbrot | Done 2026-09-20: `turbo build --target cpython` | `mikeysklar/turbo-cli` |
| | `turbo bench` over ssh | | Not started | `mikeysklar/turbo-cli` |
| | CPython shim: define `ptr8`, `ptr16`, `ptr32`, `uint` | | Working copy in `bench/run_bench.py` | `mikeysklar/turbo` |
| 4a, last | Compiled loop as a package | 64x Zero 2 W, 8.8x Pi 5, on a display | Only if Adafruit asks. Loop written and measured: `fastpath/cy/fill_pixels.py` | New repo, not created |
| 4b, last | `try: import` hook that picks up the compiled loop | | Only if Adafruit asks. Tested in copies on both Pis | `adafruit/Adafruit_Blinka_Displayio` |

Patch, kernels, benches and logs for all of these: `mikeysklar/turbo-blinka`.

Measured full-screen refresh, milliseconds:

| After | Zero 2 W | Pi 5 | Pi 5, PiTFT 3.5" |
|---|---|---|---|
| Stock 2.3.2 | 3 565 | 326.9 | 1 149 |
| PR 1 | 1 786 | 163.1 | 572 |
| PR 1 + PR 2 | 622 | 61.2 | 300 |
| PR 1 + PR 2 + compiled loop, not planned upstream | 13.7 | 1.8 | 131 |

All measured. PR 1 + PR 2 is 5.7x on the Zero 2 W with no compiler and no new
dependency.

## Before any PR

- [x] Run PR 1 on a real display. Done 2026-09-19: PiTFT Plus 3.5" (2441) on the
      Pi 5, `bench/pitft_demo.py`.
- [x] Fork `adafruit/Adafruit_Blinka_Displayio` to `mikeysklar`. Branch
      `single-composite`.
- [x] Lint. The repo's pinned hooks (black 23.3.0, pylint 2.17.4, reuse) do not
      install under `pre-commit` on Python 3.12 or later. Run `black==23.3.0`
      directly and compare pylint output before and after. CI runs the real
      hooks: all 8 passed on #178.
- [x] The repo has no `tests/` directory. `bench/displayio_refresh.py` is the
      regression check: the last pixel payload hash must not change.

## PR 1: draw each bitmap change once

Smallest possible PR. No new files, no new dependencies, no behavior change on
screen.

- File: `displayio/_tilegrid.py`, `TileGrid._get_refresh_areas`, 7 lines added,
  4 removed. Upstream commit `299c87a`.
- Patch: `patches/blinka-displayio-double-composite.patch`, applies to main
  (69909dc). Same code as upstream, the comment wording differs.
- What it does: reads the bitmap's dirty area into a local list. Today it is
  appended to the display's list and then the TileGrid appends its own copy, so
  the same pixels are drawn and sent twice.
- Matches C: `shared-module/displayio/TileGrid.c`,
  `displayio_tilegrid_get_refresh_areas` keeps the bitmap's area in a local.

Steps:

```
git checkout -b single-composite
git apply ../turbo-blinka/patches/blinka-displayio-double-composite.patch
pre-commit run --all-files
python3 ../turbo-blinka/bench/displayio_refresh.py
```

Evidence for the PR body:

| Full-screen refresh, ms | main | this PR |
|---|---|---|
| Pi 5, PiTFT 3.5" over SPI, 480x320 | 1 147 | 573 |
| Pi 5, no display, 240x240 | 325.7 | 164.3 |
| Pi Zero 2 W, no display, 240x240 | 3 595 | 1 796 |

Pixels composited per 240x240 refresh: 115 622, then 57 811. The Pi 5 rows use
the exact upstream file. The Zero 2 W row used the first version of the patch:
same code, different comment.

| Two pixels set in a 32x32 sprite at (50,60) | Rectangles redrawn |
|---|---|
| main | `(0,0)-(32,32)` and `(50,60)-(82,92)` |
| this PR | `(50,60)-(82,92)` |

Last pixel payload identical, sha256 `78b6f072aa84`.

Risk: low. Cleared before opening:

- The unchanged background is fully redrawn on the second refresh after display
  creation. Stock does the same, so it is existing behaviour, not this change.
- Sprite sheet (set a pixel, switch tile), hidden TileGrid and no-change cases:
  same pixel data as stock, one area instead of two.
- An independent review matched the new code to `TileGrid.c:662-675` and found
  the pattern nowhere else. E-paper goes through the same function.
- Dropping `refresh_area != tail` also removes a value comparison that could
  skip a change when two areas had the same coordinates.

Left out on purpose: line 441 uses `<` where C uses `<=`. Separate look.

## PR 2: fast path in `_fill_area`, plain Python

Still no dependencies. Bigger diff, so it goes after PR 1 has built some trust.

- File: `displayio/_tilegrid.py` only.
- Source: `fastpath/tilegrid_fast.py` and `fastpath/fill_kernel.py`.
- What it does: for Bitmap (1 to 8 bits) + Palette on a 16-bit display, resolve
  the palette once per index into a table and run the pixel loop on flat
  buffers and ints. Anything else takes the existing loop unchanged.
- Shape in the PR: the kernel becomes a module-level function `_fill_kernel`,
  `_fill_area` calls it when the case matches. Drop the monkeypatch and the
  `@turbo.viper` decorator.

Steps:

- [x] Move the kernel and the case check into `_tilegrid.py`. Done 2026-09-20:
      branch `fill-area-fast-path`, +108 lines, shares the existing setup code.
- [x] Hash check: `bench/displayio_refresh.py` before and after, same payload
      hash, `78b6f072aa84`. 20 scenes identical to PR 1.
- [x] Independent review. Small updates with a big palette were slower, fixed in
      4973eb0. Numbers in `RESULTS.md`.
- [x] Draft opened 2026-09-20: #179. Mark ready once #178 merges.
- [ ] Run the in-file version on the Zero 2 W.
- [x] Add scenes to the bench first. Done 2026-09-20: `bench/displayio_scenes.py`,
      20 scenes, 0 differ, four deliberate kernel bugs all caught.
- [x] Measure PR 1 + PR 2 together, no Cython. Done 2026-09-20: 622 ms on the
      Zero 2 W (5.7x), 61.2 ms on the Pi 5, 300 ms on the PiTFT 3.5".

Risk: medium. The setup code is shared with the existing loop, not copied. If
reviewers want it smaller, split off "build the palette table once per call" as
its own PR first. That split has not been measured.

## PR 3: dropped

Dropped 2026-09-20. Widening the plain-Python fast path to `ColorConverter`,
`OnDiskBitmap`, `vectorio` and displays under 16-bit was never measured. Each
case changes the shared pixel loop and needs its own test scenes, for a gain
that does not add to the 3.8x. Stays dropped unless someone asks.

## PR 5: `bitmaptools`, plain Python

Next upstream candidate. Not measured yet: measure first, then decide.
`draw_line`, `draw_circle`, `blit`, `rotozoom`, `fill_region`, `boundary_fill`
are all per-pixel Python loops. Same recipe as PR 2: plain ints and flat
buffers, output byte-identical, no compiler.

## Not Blinka PRs

- turbo-cli: `turbo build --target cpython`, done 2026-09-20. Rewrites a
  `@turbo.viper` function for Cython (typed signature, int locals from the AST)
  and builds the `.so`. Mandelbrot on the Pi 5: 141.6 to 1.2 ms, same checksum.
  This is for a user's own code on a Pi with a compiler. It does not touch
  Blinka's libraries.
- turbo-cli: bench over ssh. Not started.
- turbo shim: define `ptr8`, `ptr16`, `ptr32`, `uint` on CPython.

## Last, only if Adafruit asks: PR 4a and 4b, optional compiled loop

Not planned upstream. A `.so` is tied to the CPU, the Python version and the C
library, and minimal Linux builds have no compiler and often no glibc, so a
normal Pi wheel would not load there. The compiled loop stays in turbo-blinka
as a demo of the ceiling.

- 4a: a small package holding only the compiled `_fill_pixels`. Source:
  `fastpath/cy/fill_pixels.py`, the #179 loop with typed locals, same arguments.
- 4b, the PR to Blinka_Displayio, would be four lines above `class TileGrid`:

```python
try:
    from fill_pixels import fill_pixels as _fill_pixels
except ImportError:
    pass
```

No matching `.so` means the plain Python loop runs and nothing breaks, so it
could only ever be an extra. Measured with it, on real displays: 64x on the
Zero 2 W, 8.8x on the Pi 5. Build time 75 s on a Zero 2 W, 10 s on a Pi 5.
