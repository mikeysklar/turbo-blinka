# PR plan: Blinka_Displayio, one at a time

Target repo: `adafruit/Adafruit_Blinka_Displayio`. One PR open at a time, next
one starts after the previous merges. Numbers are full-screen refresh, 240x240,
16-bit, from `RESULTS.md`.

## Short list

- **PR 1:** Draw bitmap changes once ([#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178), open). Displayio. 2.0x
- **PR 2:** Plain-Python fast pixel loop. Displayio. 2.9x
- **PR 3a:** Fast path for ColorConverter. Displayio. ~3x
- **PR 3b:** Fast path for OnDiskBitmap. Displayio. ~2x
- **PR 3c:** Fast path for vectorio shapes. Displayio. ~3x
- **PR 3d:** Fast path for mono displays. Displayio. ~3x
- **PR 4a:** Compiled kernel package with wheels. New repo. 46x together with 4b
- **PR 4b:** Use compiled kernel if installed. Displayio. 46x together with 4a
- **PR 5:** Faster bitmaptools drawing functions. Displayio. ~50 to 100x
- Cython backend for `turbo build`. turbo-cli. 119x to 218x
- Run `turbo bench` over ssh. turbo-cli
- CPython shim with viper types. turbo
- **Maybe:** check `<` versus `<=`, line 441. Displayio

`~` means not measured yet. Displayio is `adafruit/Adafruit_Blinka_Displayio`.

## Detail

| PR | What | Gain | State | Git repo |
|---|---|---|---|---|
| 1 | Double composite fix, all in `TileGrid._get_refresh_areas` | 2.0x | Open 2026-09-19: [#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178) | `adafruit/Adafruit_Blinka_Displayio` |
| 2 | `_fill_area` fast path, plain Python, no dependencies | 2.9x | Written as a monkeypatch, needs moving into the file | `adafruit/Adafruit_Blinka_Displayio` |
| 3 | Widen the fast path, one case per PR | | Not started | `adafruit/Adafruit_Blinka_Displayio` |
| 4a | Compiled kernel package with aarch64 and armv7 wheels | 46x | Kernel written, package and wheels not started | New repo, not created yet (working name `adafruit-blinka-displayio-turbo`) |
| 4b | `try: import` hook that picks up the compiled kernel | | Not started | `adafruit/Adafruit_Blinka_Displayio` |
| 5 | `bitmaptools` kernels | | Not measured yet | `adafruit/Adafruit_Blinka_Displayio` |
| | Cython backend for `turbo build`, bench over ssh | | Not started | `mikeysklar/turbo-cli` |
| | CPython shim: define `ptr8`, `ptr16`, `ptr32`, `uint` | | Working copy in `bench/run_bench.py` | `mikeysklar/turbo` |

Patch, kernels, benches and logs for all of these: `mikeysklar/turbo-blinka`.

Measured full-screen refresh, milliseconds:

| After | Zero 2 W | Pi 5 | Pi 5, PiTFT 3.5" |
|---|---|---|---|
| Stock 2.3.2 | 3 565 | 326.9 | 1 149 |
| PR 1 | 1 786 | 163.1 | 572 |
| PR 1 + PR 2 | 622 | 61.2 | 300 |
| PR 1 + PR 2 + PR 4 | 13.7 | 1.8 | 131 |

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

- [ ] Move the kernel and the case check into `_tilegrid.py`.
- [ ] Hash check: `bench/displayio_refresh.py` before and after, same payload hash.
- [x] Add scenes to the bench first. Done 2026-09-20: `bench/displayio_scenes.py`,
      20 scenes, 0 differ, four deliberate kernel bugs all caught.
- [x] Measure PR 1 + PR 2 together, no Cython. Done 2026-09-20: 622 ms on the
      Zero 2 W (5.7x), 61.2 ms on the Pi 5, 300 ms on the PiTFT 3.5".

Risk: medium. The setup code is a copy of the existing preamble. Reviewers may
ask for it to be shared, not copied. If they want it smaller, split off "build
the palette table once per call" as its own PR first. That split has not been
measured.

## PR 3: widen the fast path

One PR per case, each with its own bench scene and hash check. Order by how
common the case is:

1. `ColorConverter` shader with a 16-bit bitmap (imageload, camera frames).
2. `OnDiskBitmap`.
3. `vectorio` shapes (`_vectorshape.py` has its own copy of the loop).
4. Displays under 16-bit: mono OLED, e-ink.

Nothing here is written or measured.

## PR 4a and 4b: optional compiled kernel

This is where Cython arrives. Blinka_Displayio itself stays pure Python.

- 4a: new small package, working name `adafruit-blinka-displayio-turbo`, holding
  only the compiled `_fill_kernel`. Wheels for aarch64 and armv7 so nobody
  builds on a Zero (74 s there).
- 4b, the PR to Blinka_Displayio, is a few lines:

```python
try:
    from blinka_displayio_turbo import fill_kernel as _fill_kernel
except ImportError:
    pass  # keep the Python kernel defined above
```

- Source: `fastpath/cy/fill_kernel.py`. Same body as the Python kernel, typed
  signature only.

Needs a decision before starting: where the package lives and who publishes the
wheels. Ask before PR 2 merges so PR 2 can shape the kernel signature for it.

## PR 5: `bitmaptools`

Not measured yet. Measure first, then decide. `draw_line`, `draw_circle`,
`blit`, `rotozoom`, `fill_region`, `boundary_fill` are all per-pixel Python
loops. Same recipe as PR 2 then PR 4.

## Not Blinka PRs

- turbo-cli: Cython backend for `turbo build` (rewrite signature, declare int
  locals from the AST), bench over ssh.
- turbo shim: define `ptr8`, `ptr16`, `ptr32`, `uint` on CPython.
