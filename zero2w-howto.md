# Pi Zero 2 W: 3 fills to 97 fills in 10 seconds

The source is the same Python. There were three changes, and the last one
compiles the slow loop.

## Result

| Zero 2 W, PiTFT 2.8" | One full-screen fill | Fills in 10 s |
|---|---|---|
| Stock | 4 871 ms | 3 |
| Draw once (#178) | 2 460 ms | not counted |
| Faster loop (#179) | 889 ms | not counted |
| Compiled loop (turbo + Cython) | 75.6 ms | 97 |

The pixels sent are byte-identical in all 20 test scenes.

## Hardware

| | |
|---|---|
| Board | Raspberry Pi Zero 2 W, Pi OS 64-bit |
| Display | PiTFT Plus 2.8" (2423), 320x240, SPI |
| Software | Blinka 9.2.0, blinka-displayio 2.3.2, Python 3.13.5 |

## Setup on the Pi

```
sudo raspi-config nonint do_spi 0
source ~/env/bin/activate
pip install adafruit-circuitpython-ili9341 cython
```

## Change 1: draw each change once (#178)

`displayio/_tilegrid.py`, 7 lines added and 4 removed. Every bitmap change was
being drawn twice. [PR](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178).

```python
bitmap_areas = []
self._bitmap._get_refresh_areas(bitmap_areas)
if bitmap_areas:
    refresh_area = bitmap_areas[-1]
```

## Change 2: a faster pixel loop (#179)

Same file, +108 lines. Colours are looked up once into a table, and the loop
uses plain numbers. [PR](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/179).

```python
colors, opaque = _palette_table(palette, colorspace, count)
covered = _fill_pixels(buffer, mask, colors, opaque, geometry, self, bitmap)
```

## Change 3: compile that loop

`fastpath/cy/fill_pixels.py` is a copy of `_fill_pixels` with types added. The
loop itself is unchanged.

```python
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.locals(x=cython.int, y=cython.int, offset=cython.int, ...)
def fill_pixels(buffer: cython.ushort[:], mask: cython.uint[:], colors,
                opaque: cython.uchar[:], geometry, tilegrid, bitmap) -> bool:
```

Build it. This takes 75 s on the Zero:

```
cd fastpath/cy
cythonize -i -3 fill_pixels.py
```

Add 4 lines to `_tilegrid.py`, above `class TileGrid`, so it uses the compiled
loop when the `.so` is present:

```python
try:
    from fill_pixels import fill_pixels as _fill_pixels
except ImportError:
    pass
```

## Run it

`pr4` is a copy of the installed `displayio` with the three changes. `cy4` holds
the `.so`.

```
python3 bench/pitft_demo.py --display ili9341 --seconds 10                       # stock
PYTHONPATH=pr4:cy4 python3 bench/pitft_demo.py --display ili9341 --seconds 10    # compiled
```

```
3 full-screen fills in 10 s
97 full-screen fills in 10 s
```

## Where turbo fits

| Turbo step | Here |
|---|---|
| Find the slow function | the pixel loop in `TileGrid._fill_area` |
| Compile it | Cython, done by hand for now |
| Check the output is identical | 20 scenes, matching sha256 |
| Measure | `bench/pitft_demo.py`, `bench/displayio_refresh.py` |

Numbers and logs: `RESULTS.md`, `logs/pizero2w-pitft28-20260920.log`.
