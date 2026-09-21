# Playground guide notes: Cython on a Raspberry Pi

Running notes for a short Adafruit Playground guide: how to speed up your own
Python code with Cython on a Raspberry Pi, and what speed to expect. Add to this
as the work goes. Numbers come from `RESULTS.md`.

## What the guide should show

| | |
|---|---|
| Reader | Someone running Python on a Pi who has a slow loop of their own |
| Promise | Same Python file, add types, build once, 100x on number loops |
| Proof | Two videos and two small tables |
| Length | One page |

## What the guide must not suggest

| | |
|---|---|
| Blinka stays pure Python | Nothing here changes Blinka or asks Adafruit to ship compiled code |
| This is for your own code | On a full Pi OS, where a compiler is a `pip install` away |
| It is optional | The same file runs as plain Python without the build, only slower |
| It is not for minimal Linux builds | No compiler there, and a built file from a Pi will not load |
| Word to use | "compiled", not "C". Nobody writes C: the source is Python with decorators |

## Hardware used

| Board | Display | Notes |
|---|---|---|
| Pi Zero 2 W | PiTFT Plus 2.8" (2423), ILI9341, 320x240 | Slow and common: good for showing the gain |
| Pi 5 | PiTFT Plus 3.5" (2441), HX8357D, 480x320 | Needs a real 5 V 5 A supply or it browns out |

Pi OS 64-bit desktop (trixie), Python 3.13.5.

## Setup, in order

Blinka, per the [Learn guide](https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi):

```
python3 -m venv env --system-site-packages
source env/bin/activate
pip3 install adafruit-blinka adafruit-blinka-displayio
```

Cython. gcc and the Python headers were already on Pi OS desktop:

```
pip3 install cython
```

Only for the display demos:

```
sudo raspi-config nonint do_spi 0
pip3 install adafruit-circuitpython-ili9341     # 2.8"
pip3 install adafruit-circuitpython-hx8357      # 3.5"
```

## Smallest example

Plain Python, 142.5 ms on a Pi 5:

```python
def mandel_row(out, width, dx, cy, max_iter):
    for px in range(width):
        ...
```

Same body with types, 1.2 ms:

```python
import cython

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.locals(px=cython.int, cx=cython.int, x=cython.int, y=cython.int,
               i=cython.int, x2=cython.int, y2=cython.int)
def mandel_row(out: cython.uchar[:], width: cython.int, dx: cython.int,
               cy: cython.int, max_iter: cython.int):
```

Build once, then import it like any module:

```
cythonize -i -3 pixels.py
```

## What speed to expect

Mandelbrot 160x120, milliseconds:

| | Zero 2 W | Pi 5 |
|---|---|---|
| Plain Python | 1308 | 142.5 |
| Cython, no types | 962 | 104.2 |
| Cython, typed | 6.0 | 1.2 |
| C, gcc -O2 | 4.8 | 1.05 |

Full-screen fills in 10 s on a real display. This is a demo of the ceiling, done
in a test copy of displayio: it is not part of Blinka and not planned for it.

| | Stock | Plain Python fixes + compiled loop | Video |
|---|---|---|---|
| Zero 2 W, 2.8" | 3 | 97 | [watch](https://drive.google.com/file/d/1P1-LijQl6t-twvAlZE3E52PNMB0Iya2U/view) |
| Pi 5, 3.5" | 9 | 75 | [watch](https://drive.google.com/file/d/1eByUEks2I_9uzHSume6ZK1jqVe_WtbQ0/view) |

## Things that tripped us up

| Problem | Fix |
|---|---|
| Cython with no types is only 1.4x | Every loop variable needs a type. A missed one stays slow, silently |
| Build takes 75 s on a Zero 2 W | 10 s on a Pi 5. Build once, keep the `.so` |
| `.so` stops loading after a Python upgrade | Rebuild. The file name carries the Python version |
| SPI is off on a fresh Pi OS | `sudo raspi-config nonint do_spi 0`, no reboot needed |
| "GPIO busy" on a Pi 5 | Leave `chip_select` out of `FourWire`. spidev already owns CE0 |
| PiTFT "easy install" script | Skip it. It gives the display to the kernel, displayio cannot open it |
| A folder named `cython` or `numpy` next to the script | Rename it. It hides the real package |
| Pi 5 resets under load | Use the official 27 W supply |
| `ssh` refuses after re-imaging the SD card | `ssh-keygen -R pizero2w.local` |
| Output must not change | Print a checksum before and after. Ours matched in every run |

## What did not need Cython

Two plain-Python fixes to Blinka_Displayio gave 3.8x on the Pi 5 and 5.5x on the
Zero 2 W before any compiler:
[#178](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/178),
[#179](https://github.com/adafruit/Adafruit_Blinka_Displayio/pull/179). Those
are what goes to Blinka, and they work everywhere Blinka runs. Worth a line in
the guide: look for wasted work first, reach for the compiler second.

## Numba, the no-build option

`TURBO=numba python3 code.py` with the turbo shim, or `@njit(cache=True)` by
hand. Same source, no build, no gcc. Startup before the first fast frame,
seconds:

| | First ever run | Later runs, cached | Cython `.so` |
|---|---|---|---|
| Pi 5 | 1.2 | 0.43 | 0.003 |
| Zero 2 W | 10.1 | 3.4 to 4.5 | not measured |

Frame time after that: 1.9 ms Pi 5, 8.8 ms Zero 2 W (Cython: 1.2 and 6.0). 204 MB
on disk. Good for long-running programs, poor for quick scripts on a Zero. Ints
are 64-bit, not 32-bit wrapping.

## What a built file is tied to

| | |
|---|---|
| CPU type | A `.so` from a Pi 5 or Zero 2 W is aarch64 only |
| Python version | The file name carries it: `pixels.cpython-313-aarch64-linux-gnu.so` |
| C library | Built against glibc on Pi OS. Will not load on a musl system |
| So | Build on the machine that runs it, and rebuild after a Python upgrade |

## Still to add

- `turbo build --target cpython` exists as of 2026-09-20 (turbo-cli). It writes
  the typed copy from a `@turbo.viper` function and builds it: mandelbrot on the
  Pi 5 went 141.6 to 1.2 ms, same checksum, 8.9 s to build. Decide whether the
  guide shows the hand-typed decorators, the one command, or both.
- Running the decorated file without building it needs the `cython` package
  installed, because of `import cython`. No compiler needed for that.
- A photo of each setup.
- Numba and numpy comparison, one row each, from `RESULTS.md`.
