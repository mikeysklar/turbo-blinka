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

| After | Zero 2 W | Pi 5 |
|---|---|---|
| Stock 2.3.2 | 3 595 | 325.7 |
| PR 1 | 1 796 | 162.7 |
| PR 1 + PR 2, not measured together | about 620 | about 60 |
| PR 1 + PR 2 + PR 4 | 13.7 | 1.8 |

The "about" numbers are 1 796 / 2.9 and 162.7 / 2.7.

## Before any PR

- [ ] Run PR 1 on a real display. Everything so far is headless with a null bus.
      One ST7789 240x240 on the Zero 2 W is enough.
- [ ] Fork `adafruit/Adafruit_Blinka_Displayio` to `mikeysklar`.
- [ ] `pip install pre-commit && pre-commit install` in the fork. Hooks: black,
      reuse, pylint.
- [ ] The repo has no `tests/` directory. `bench/displayio_refresh.py` is the
      regression check: the last pixel payload hash must not change.

## PR 1: draw each bitmap change once

Smallest possible PR. No new files, no new dependencies, no behavior change on
screen.

- File: `displayio/_tilegrid.py`, `TileGrid._get_refresh_areas`, 9 lines.
- Patch: `patches/blinka-displayio-double-composite.patch`, applies to main
  (69909dc).
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

| Full-screen refresh | Zero 2 W ms | Pi 5 ms | Pixels composited |
|---|---|---|---|
| main | 3 595 | 325.7 | 115 622 |
| this PR | 1 796 | 162.7 | 57 811 |

| Two pixels set in a 32x32 sprite at (50,60) | Rectangles redrawn |
|---|---|
| main | `(0,0)-(32,32)` and `(50,60)-(82,92)` |
| this PR | `(50,60)-(82,92)` |

Last pixel payload identical, sha256 `78b6f072aa84`.

Risk: low. One thing to check first: the unchanged background was also fully
redrawn on the second refresh after display creation. Probably a separate
startup redraw. Confirm it is not caused by this change before opening.

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
- [ ] Add scenes to the bench first: flipped, transposed, scale 2, tiled sprite
      sheet, transparent palette index. The current bench covers none of these.
- [ ] Measure PR 1 + PR 2 together, no Cython. Put that number in the PR.

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
