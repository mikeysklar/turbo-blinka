# turbo-blinka

[turbo](https://github.com/mikeysklar/turbo) for Blinka on Raspberry Pi. Benchmarks and a displayio fast path.

## Results

Pi Zero 2 W and Pi 5, Pi OS 64-bit, Python 3.13.5. Milliseconds. Full data in [RESULTS.md](RESULTS.md).

### Mandelbrot 160x120, turbo's viper source

| Backend | Source change | Zero 2 W | Pi 5 |
|---|---|---|---|
| CPython | none | 1308 | 142.5 |
| Cython, untyped | none | 962 | 104.2 |
| numpy, whole frame | rewrite | 115 | 10.5 |
| Numba | none | 8.6 | 1.9 |
| Cython, typed | signature only | 6.0 | 1.2 |
| C, gcc -O2 | | 4.8 | 1.05 |

### displayio full refresh, 240x240

| TileGrid._fill_area | Zero 2 W | Pi 5 |
|---|---|---|
| Stock Blinka_Displayio 2.3.2 | 3560 | 325.7 |
| Fast path, Python | 1241 | 121.8 |
| Fast path, Python + double composite patch | 622 | 61.2 |
| Fast path, Numba | 34.1 | 4.6 |
| Fast path, Cython | 26.8 | 3.5 |
| Fast path, Cython + [double composite patch](patches/blinka-displayio-double-composite.patch) | 13.7 | 1.8 |

Output is byte-identical to stock in every row.

### On a real display, stock against turbo + Cython

| Full-screen fills in 10 s | Stock | turbo + Cython | Video |
|---|---|---|---|
| Pi Zero 2 W, PiTFT 2.8" | 3 | 97 | [watch](https://drive.google.com/file/d/1P1-LijQl6t-twvAlZE3E52PNMB0Iya2U/view) |
| Pi 5, PiTFT 3.5" | 9 | 75 | [watch](https://drive.google.com/file/d/1eByUEks2I_9uzHSume6ZK1jqVe_WtbQ0/view) |

How: [zero2w-howto.md](zero2w-howto.md).

### Startup cost

| | Zero 2 W | Pi 5 |
|---|---|---|
| Cython build, once | 70 s | 9 s |
| Cython at run time | 0 | 0 |
| Numba import + JIT, every run | 4.7 to 8.8 s | 0.5 s |
| Numba on disk | 204 MB | 204 MB |

## Setup

Blinka per the [Learn guide](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi).

```
python3 -m venv env --system-site-packages
source env/bin/activate
pip3 install adafruit-blinka adafruit-blinka-displayio cython numba
git clone https://github.com/mikeysklar/turbo-blinka
cd turbo-blinka
```

## Run

Mandelbrot, before:

```
python3 bench/run_bench.py bench/src/mandel_float.py bench/src/pixels.py
```

Cython:

```
mkdir -p build && cp bench/cython_backend/pixels_typed.py build/pixels.py
cythonize -i -3 build/pixels.py && rm build/pixels.py
python3 bench/run_bench.py build/pixels.*.so
```

Numba:

```
python3 bench/run_bench.py --shim numba bench/src/pixels.py
```

numpy:

```
python3 bench/run_bench.py bench/numpy_backend/pixels_np_frame.py
```

C ceiling:

```
gcc -O2 -o mandel_ref bench/mandel_ref.c && ./mandel_ref
```

displayio refresh, stock then fast path:

```
python3 bench/displayio_refresh.py
python3 bench/displayio_refresh.py --fast python
python3 bench/displayio_refresh.py --fast numba
(cd fastpath/cy && cythonize -i -3 fill_kernel.py)
python3 bench/displayio_refresh.py --fast cython
```

[Double composite patch](patches/blinka-displayio-double-composite.patch), tested against a copy so pip's install stays untouched:

```
mkdir patched && cp -r $(python3 -c 'import displayio,os;print(os.path.dirname(displayio.__file__))') patched/
(cd patched && patch -p1 < ../patches/blinka-displayio-double-composite.patch)
PYTHONPATH=patched python3 bench/displayio_refresh.py --fast cython
```

Every run prints a checksum. It must match across backends.

## Files

| Path | What |
|---|---|
| `bench/run_bench.py` | Times a module's `_turbo_bench()`. Holds the CPython turbo shim. |
| `bench/src/` | turbo's mandelbrot sources, unmodified. |
| `bench/cython_backend/` | Viper source with Cython types. Body unchanged. |
| `bench/numpy_backend/` | numpy rewrites, per row and whole frame. |
| `bench/mandel_ref.c` | C version. The ceiling. |
| `bench/displayio_refresh.py` | Headless `display.refresh()` timing. No display needed. |
| `bench/displayio_scenes.py` | 20 scenes, stock against fast path, bytes must match. |
| `bench/pitft_demo.py` | Same timing on a real PiTFT, 3.5" or 2.8". `--seconds` for filming. |
| `bench/displayio_small_area.py` | Refresh time for small changed areas, 1x1 to 240x240. |
| `bench/life.py` | Conway kernel from the RGBMatrix Learn guide. |
| `fastpath/fill_kernel.py` | `_fill_area` pixel loop on flat buffers. |
| `fastpath/tilegrid_fast.py` | Monkeypatch that installs the kernel. Falls back if unsupported. |
| `fastpath/cy/fill_kernel.py` | Same kernel with Cython types. |
| `fastpath/cy/fill_pixels.py` | PR 2's `_fill_pixels` with Cython types. Same arguments. |
| [`patches/`](patches/blinka-displayio-double-composite.patch) | Blinka_Displayio fix: full refresh was drawn twice. |
| [`zero2w-howto.md`](zero2w-howto.md) | Zero 2 W, 3 to 97 fills in 10 s: commands and changes. |
| `pr-plan.md` | Upstream PRs. PR 1 is open (#178), PR 2 is a draft (#179). |
| `pr1-body.md`, `pr1-body-v2.md` | PR 1 description, long and short. |
| `split-video-title-mp4.md` | How the side-by-side video was cut. |
| `turbo-blinka.html` | Summary page: charts, tables, port work. |
| `RESULTS.md` | Every measured number. |
| `analyze-results.md` | `turbo analyze` output over Blinka and Learn guides. |
| `logs/` | Raw output per host per run. |
