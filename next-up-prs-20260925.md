# Next up, after 4a to 4d

Found 2026-09-25 by reviewing the library from five angles at once: per-refresh
allocation, remaining pixel loops, the refresh and dirty-area machinery, the bus
layer below it, and the companion libraries above it.

Everything in the **measured** column I ran myself, on a Raspberry Pi 5 and a Pi
Zero 2 W against `main243` (upstream/main at 9207357's base). Anything I have not
run says so. Two findings the review handed me turned out to be overstated, and
they are kept below with their real numbers, because a rejected lead is worth as
much as an accepted one.

## Worth a PR

| # | what | repo | measured | risk |
|---|---|---|---|---|
| 1 | `blit` ignores `y1` | Blinka_Displayio | copies source rows 0-3 when asked for 3-6 | low |
| 2 | debug `print()` shipped in `bitmaptools` | Blinka_Displayio | 40,000 lines for a 200x200 `alphablend` | none |
| 3 | vectorio redraws the whole travel box | Blinka_Displayio | 37,400 px to 4,800 px on one jump, 7.8x | medium |
| 4 | `blit` marks the bitmap dirty per pixel | Blinka_Displayio | 725 ns/px, 428 of it in `Area` allocation | low |
| 5 | `blit` has no self-overlap reverse handling | Blinka_Displayio | not yet tested | medium |
| 6 | display_text never batch loads glyphs | Display_Text | not yet tested | low |
| 7 | SPI mode re-applied on every write | Adafruit_Blinka | not yet tested, 18 ioctls per refresh | medium |
| 8 | background thread polls instead of sleeping | Blinka_Displayio | 27% of a core idle on a Zero 2 W | low |

### 1. `blit` ignores `y1`

`bitmaptools/__init__.py:223-225` builds a flat index as

```python
y1 + (y_count * source_bitmap.width) + x1 + x_count
```

A flat index is `y * width + x`, so `y1` has to be inside the multiply. It is off
by `y1 * (width - 1)`, which is why `y1=0` works and nothing else does. Correct:

```python
(y1 + y_count) * source_bitmap.width + x1 + x_count
```

Demonstrated on a Pi 5: an 8x8 source whose every row holds its own row number,
`blit(dst, src, 0, 0, x1=0, y1=3, x2=8, y2=7)` puts rows `[0, 1, 2, 3]` in the
destination where `[3, 4, 5, 6]` was asked for. With `y1=0` it is correct, which
is how this survived.

A test wants: `y1` non-zero, `x1` non-zero, both, and the `skip_source_index` and
`skip_dest_index` paths, since they read through the same index.

### 2. Debug prints left in `bitmaptools`

| line | function | how often |
|---|---|---|
| 136 | `draw_polygon` | once per edge |
| 147 | `draw_polygon` | once per call |
| 688 | `alphablend` | **once per pixel** |
| 757 | `dither` | once per call |

Line 688 is the one that matters: it prints `pixel hex: 0x...` inside the RGB565
inner loop, so `alphablend` on a 200x200 image writes 40,000 lines to stdout.
That makes the function unusable as shipped rather than merely slow. Four
single-line deletions, no behaviour to test beyond "output unchanged, stdout
empty".

Ship 1 and 2 together or separately, but not mixed with 4: 4 is a performance
change to the same function and wants its own before and after.

### 3. vectorio redraws the whole travel box

This is the biggest win on the list, and it is **pre-existing, not from #186**.
Verified: the redrawn area is identical on `main241` (before #186) and `main243`
(after), so merging #186 did not cause it.

`_consume_dirty_areas` unions the **new** position into the stale area
(`vectorio/_vectorshape.py:351`). CircuitPython unions only the **old** one:

```c
// shared-module/vectorio/VectorShape.c:204-205, before the copy at 210
displayio_area_union(&self->current_area, &self->ephemeral_dirty_area, &self->ephemeral_dirty_area);
displayio_area_copy(&current_area, &self->current_area);
```

So in Python `ephemeral ⊇ current` always holds, which makes
`union - dirty - current + overlap` always 0, so the test at
`_vectorshape.py:399` always takes the combine branch and the `else` at 407 is
unreachable. Every frame a shape moves further than its own size, the display
redraws the entire bounding box of the journey.

Prototyped the C's rule on a Pi 5. A 20x20 rectangle jumping from (10,10) to
(210,160):

| | areas | pixels composited |
|---|---|---|
| today | 1 | 37,400 |
| C's rule | 2 | 4,800 |

7.8x fewer, and it grows with the distance travelled. The 4,800 is not 800
because setting `.x` and `.y` separately queues two moves, so the intermediate
footprint is cleaned too, exactly as the C would.

**Two traps.** First, once `ephemeral` no longer contains `current`, the disjoint
branch goes live for the first time, and `Area.compute_overlap`
(`displayio/_area.py:68-69`) returns `False` without writing `y1`/`y2`, leaving
whatever the swap area held before. That yields a negative `overlap_size` and a
wrong branch choice. Second, a wrong fix here leaves stale pixels on the screen,
which a byte hash will not catch if the areas differ legitimately. This needs the
framebuffer oracle from `bench/packed_subrect.py`: replay the writes, compare the
painted result, not the wire.

### 4. `blit` marks the bitmap dirty per pixel

`blit` writes through `Bitmap.__setitem__`, which calls
`_set_dirty_area(Area(x, y, x + 1, y + 1))` unconditionally at
`displayio/_bitmap.py:169`, so every pixel allocates two `Area` objects and runs
`canon`, `union` and `compute_overlap`. That is 428 ns of the 725 ns per pixel.
The C marks the area once before the loop
(`shared-module/bitmaptools/__init__.c:1074-1075`) and then writes through
`displayio_bitmap_write_pixel`, which does not touch the dirty area.

This is the same fix already merged for `fill_region` (6e571ae), so it is a
proven pattern: about 3.8x. While in there, `blit` passes flat ints to
`__getitem__`/`__setitem__`, which immediately decode them back to x and y with
`%` and `//`, despite `blit` already holding both.

### 5. `blit` cannot blit a bitmap into itself

C sets `x_reverse = (x > x1)` and `y_reverse = (y > y1)` and iterates from the far
edge backwards, so an overlapping self-blit never reads a pixel it has already
written (`shared-module/bitmaptools/__init__.c:1077-1098`). The Python always
iterates forward from `(x1, y1)`, so `blit(b, b, 10, 0, x2=100, y2=100)` smears
the leading edge. Separate PR from 4, with its own test: self-blit in each of the
four overlap directions. Not yet reproduced on hardware.

### 6. display_text never batch loads glyphs

`label.py:256`, `bitmap_label.py:411` and `:496` call `get_glyph` per character.
`glyph_cache.py:55` handles a miss by calling `load_glyphs(one_code_point)` and
then `gc.collect()`, and for BDF `bdf.py:156` does `file.seek(0)` and walks the
file looking for that one encoding. So a 60 character label is around 60 near-full
scans of the font file and 60 collections, where one batched call makes a single
pass. The fix is one guarded line in each of the two labels:

```python
if hasattr(self._font, "load_glyphs"):
    self._font.load_glyphs(new_text)
```

Memory-neutral, since the same glyphs end up cached either way. Not yet measured;
measure a BDF label's first render on a Zero 2 W before writing anything, because
the claim is "seconds to milliseconds" and that needs to be real.

`wrap_text_to_pixels` is separately quadratic: it re-splits the string inside its
own loops (`__init__.py:102-107`), re-measures `"-"` every iteration (`:129`), and
re-measures the whole partial word per character (`:130`).

### 7. SPI mode re-applied on every write

`Adafruit_Blinka`'s `generic_linux/spi.py:83-85` sets `max_speed_hz`, `mode` and
`bits_per_word` on every `write()`, and each is 3 ioctls in PureIO, roughly 18
redundant ioctls per refresh area. Caching the last applied triple is about
0.25 ms a refresh by the review's estimate, which I have not checked. The risk is
real: another library sharing `/dev/spidev0.0` can change the mode behind us, so
the cache has to be invalidated in `init()`. Different repo, so a separate PR.

Related but not a code change: PureIO chunks SPI writes at 4096 bytes
(`spi.py:54`), so a 320x240 frame is 38 ioctls. `SPI_BUFSIZE` plus the kernel's
`spidev.bufsiz` takes that to 3. Worth documenting, not patching.

### 8. The background thread polls

`displayio/__init__.py:41-49` loops over every display and calls
`time.sleep(0.0)`, which returns immediately, so the thread runs flat out. The
comment above it already admits the problem.

Measured, idle, nothing animating:

| board | CPU burned | application throughput kept |
|---|---|---|
| Pi 5 | 5% of a core | |
| Zero 2 W | 27% of a core | 99.0% |

So the review's "pins a core and fights your animation for the GIL" is wrong on
both counts: it is 27% at worst, and the application keeps 99% of its throughput
because the Pi has four cores. This is a power, heat and battery fix, not a frame
rate one, and the PR should say so. CircuitPython does not poll at all: it calls
`displayio_background()` from the 1 ms tick (`supervisor/shared/tick.c:57`). The
fix is to sleep until the earliest next frame deadline, floored around 1 ms.

## Ruled out, with numbers

Keeping these so nobody spends a day on them twice.

| lead | claim | what it actually is |
|---|---|---|
| `bytearray([0] * n)` per refresh | 190x slower than `bytearray(n)` in isolation, which is true: 10.8 ms versus 0.05 ms for a 480x320 frame on a Zero 2 W | 0.6% of a refresh. A full 480x320 refresh is 1746.2 ms before and 1746.2 ms after, output hashes identical. Compositing costs 11 µs a pixel and this costs 0.07 µs. Fold it into another PR as a tidy-up, do not claim a speedup |
| `buffer.tobytes()[:n]` | two full copies per refresh | 0.13 ms, and the full-length slice is free because CPython returns the same object. The remaining copies are all inside PureIO and cannot be avoided from this side |
| no-op writes queue an `Area` | #186 dropped the `moved` guard, so every write allocates | The `x` and `y` setters already guard on equality: 50,000 writes of the same value queue 0 areas, 8 ms, identical before and after #186. `hidden` has no guard, which is a real but tiny gap |

The queue growth from #186 is still real and still unfixed: 200,000 genuine moves
between refreshes queue 200,000 `Area` objects and 23 MB, where the C keeps two
areas. The consumer collapses the queue to exactly two areas anyway, so no
information is lost by coalescing at append time. That is worth raising with
Melissa rather than patching unilaterally, since it is her design and the thread
safety comment at `_vectorshape.py:51-52` is the reason the queue exists.

## Order

1 and 2 first: small, obviously right, and they touch a file none of the four open
PRs touch. Then 3, which is the real prize and needs the framebuffer oracle. Then
4, 5, 8. Then 6 and 7, which are other repos and want their own measurements
first.

Not started: polygon scanline filling, which #188 leaves on the slow path
(`_COVER_ASK_SHAPE`, 344 to 1494 ns/px against 28 to 37 for rectangles and
circles). Highest risk on the whole list, and it wants a brute-force differential
test against the current code before a line of it is written.
