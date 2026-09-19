#!/usr/bin/env python3
"""Real-display check on an Adafruit PiTFT Plus 3.5" (product 2441, HX8357D,
480x320, SPI0 CE0, DC on GPIO25).

    python3 pitft_demo.py [--fills 6] [--moves 40] [--fast cython]

Full-screen colour fills, then a sprite walking across the screen. Prints the
time of every display.refresh(), SPI transfer included. Run it against stock
displayio and against a patched copy (PYTHONPATH) to compare.
"""
import argparse
import os
import statistics
import sys
import time

import board
import displayio
import fourwire
from adafruit_hx8357 import HX8357

COLORS = (0xE0103A, 0x1565D8, 0x12A150, 0xF2B400, 0x8A2BE2, 0x101010)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fills", type=int, default=6)
    ap.add_argument("--moves", type=int, default=40)
    ap.add_argument("--baud", type=int, default=24_000_000)
    ap.add_argument("--fast", choices=["python", "cython"])
    ap.add_argument("--seconds", type=float,
                    help="for filming: 2 s black, then fills for this long, no sprite pass")
    a = ap.parse_args()

    if a.fast:
        here = os.path.dirname(os.path.abspath(__file__))
        fp = next(d for d in (os.path.join(here, "fastpath"), os.path.join(here, "..", "fastpath"))
                  if os.path.isdir(d))
        sys.path[:0] = [os.path.join(fp, "cy"), fp] if a.fast == "cython" else [fp]
        from run_bench import install_shim
        install_shim()
        import fill_kernel
        import tilegrid_fast
        tilegrid_fast.install(fill_kernel.fill_kernel)

    displayio.release_displays()
    # no chip_select: spidev owns CE0 and toggles it per transfer. Claiming it as
    # a GPIO as well fails with "GPIO busy" on a Pi 5.
    bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=a.baud)
    display = HX8357(bus, width=480, height=320, auto_refresh=False)

    palette = displayio.Palette(len(COLORS) + 1)
    for i, c in enumerate(COLORS):
        palette[i] = c
    palette[len(COLORS)] = 0xFFFFFF
    background = displayio.Bitmap(480, 320, len(COLORS) + 1)
    sprite_bmp = displayio.Bitmap(48, 48, len(COLORS) + 1)
    sprite_bmp.fill(len(COLORS))
    sprite = displayio.TileGrid(sprite_bmp, pixel_shader=palette, x=0, y=136)
    group = displayio.Group()
    group.append(displayio.TileGrid(background, pixel_shader=palette))
    group.append(sprite)
    display.root_group = group
    display.refresh()

    print("# displayio from %s, fast path %s, SPI %d Hz"
          % (os.path.dirname(displayio.__file__), a.fast or "off", a.baud))
    if a.seconds:
        background.fill(len(COLORS) - 1)  # near-black: the sync mark between clips
        display.refresh()
        time.sleep(2)
        n, end = 0, time.monotonic() + a.seconds
        while time.monotonic() < end:
            background.fill(n % (len(COLORS) - 1))
            display.refresh()
            n += 1
        background.fill(len(COLORS) - 1)
        display.refresh()
        print("%d full-screen fills in %.0f s" % (n, a.seconds))
        return

    fills = []
    for n in range(a.fills):
        background.fill(n % len(COLORS))
        t0 = time.perf_counter()
        display.refresh()
        fills.append((time.perf_counter() - t0) * 1e3)
        print("fill %d: %.0f ms" % (n, fills[-1]))
    moves = []
    for n in range(a.moves):
        sprite.x = (n + 1) * 10
        t0 = time.perf_counter()
        display.refresh()
        moves.append((time.perf_counter() - t0) * 1e3)
    print("| scene | median ms | fps |")
    print("|---|---|---|")
    for name, t in (("full-screen fill, 480x320", fills), ("move 48x48 sprite 10 px", moves)):
        med = statistics.median(t)
        print("| %s | %.1f | %.1f |" % (name, med, 1e3 / med))


if __name__ == "__main__":
    main()
