#!/usr/bin/env python3
"""Headless refresh bench for Adafruit_Blinka_Displayio.

    python3 displayio_refresh.py [--w 240] [--h 240] [--trials 5] [--profile]

Times display.refresh() through the public API on a 16-bit BusDisplay whose bus
throws the bytes away, so the number is the pure-Python compositing cost
(TileGrid._fill_area and friends) with no SPI time in it. No display, no pins,
no root needed. Median of N trials, milliseconds.
"""
import argparse
import hashlib
import os
import platform
import statistics
import sys
import time

import bitmaptools
import busdisplay
import displayio
import fourwire


class NullBus(fourwire.FourWire):
    """A FourWire that owns no pins and sends nowhere. It has to subclass
    FourWire: _DisplayCore rejects any other bus type."""

    def __init__(self):  # pylint: disable=super-init-not-called
        self.sent = 0
        self.last = b""
        self.digest = hashlib.sha256()

    def reset(self):
        pass

    def _free(self):
        return True

    def _begin_transaction(self):
        return True

    def _end_transaction(self):
        pass

    def _send(self, _type, _cs, data):
        self.sent += len(data)
        self.digest.update(data)
        if len(data) > 4:  # pixel payload, not a window command
            self.last = bytes(data)


def host():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip("\x00\n")
    except OSError:
        return platform.machine()


def timed(trials, dirty, display):
    times = []
    for n in range(trials):
        dirty(n)
        t0 = time.perf_counter()
        display.refresh()
        times.append((time.perf_counter() - t0) * 1e3)
    return times


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=240)
    ap.add_argument("--h", type=int, default=240)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--profile", action="store_true",
                    help="cProfile one full-screen refresh instead of timing")
    ap.add_argument("--no-background", action="store_true",
                    help="stop displayio's auto-refresh thread first. It spins on "
                         "sleep(0.0) and competes with refresh() for the GIL")
    ap.add_argument("--fast", choices=["python", "numba", "cython"],
                    help="install fastpath/tilegrid_fast.py with the kernel run this way")
    a = ap.parse_args()

    if a.fast:
        here = os.path.dirname(os.path.abspath(__file__))
        fp = next(d for d in (os.path.join(here, "fastpath"), os.path.join(here, "..", "fastpath"))
                  if os.path.isdir(d))
        sys.path[:0] = [os.path.join(fp, "cy"), fp] if a.fast == "cython" else [fp]
        from run_bench import install_shim
        install_shim("numba" if a.fast == "numba" else "identity")
        import fill_kernel
        import tilegrid_fast
        print("# kernel: %s" % fill_kernel.__file__)
        tilegrid_fast.install(fill_kernel.fill_kernel)

    if a.no_background:
        displayio._stop_background()  # pylint: disable=protected-access
    displayio.release_displays()
    bus = NullBus()
    display = busdisplay.BusDisplay(bus, b"", width=a.w, height=a.h, auto_refresh=False)

    palette = displayio.Palette(16)
    for i in range(16):
        palette[i] = (i * 0x11) << 16 | (255 - i * 0x11) << 8 | (i * 7 & 0xFF)
    background = displayio.Bitmap(a.w, a.h, 16)
    sprite_bmp = displayio.Bitmap(32, 32, 16)
    sprite_bmp.fill(9)
    sprite = displayio.TileGrid(sprite_bmp, pixel_shader=palette, x=10, y=10)
    group = displayio.Group()
    group.append(displayio.TileGrid(background, pixel_shader=palette))
    group.append(sprite)
    display.root_group = group
    display.refresh()

    def full(n):
        background.fill(n % 16)

    def move(n):
        sprite.x = 10 + 8 * (n + 1)

    def lines(n):
        for k in range(20):
            bitmaptools.draw_line(background, 0, k * 10, a.w - 1, a.h - 1 - k * 10,
                                  (n + k) % 16)

    if a.profile:
        import cProfile
        import pstats
        full(1)
        prof = cProfile.Profile()
        prof.runcall(display.refresh)
        pstats.Stats(prof).sort_stats("tottime").print_stats(12)
        return

    print("# displayio refresh, %s, Python %s, %dx%d 16-bit, background thread %s, %s"
          % (host(), platform.python_version(), a.w, a.h,
             "stopped" if a.no_background else "running", time.strftime("%Y-%m-%d %H:%M")))
    print("| scene | pixels composited | median ms | min ms | max ms | ms per 1k px | fps |")
    print("|---|---|---|---|---|---|---|")
    scenes = [("full screen, bitmap fill", full, a.w * a.h),
              ("move 32x32 sprite 8 px", move, 40 * 32),
              ("20 bitmaptools.draw_line, then refresh", lines, None)]
    for name, dirty, npx in scenes:
        before = bus.sent
        times = timed(a.trials, dirty, display)
        sent_px = (bus.sent - before) // 2 // a.trials
        med = statistics.median(times)
        print("| %s | %d | %.1f | %.1f | %.1f | %.2f | %.1f |"
              % (name, sent_px, med, min(times), max(times),
                 med / max(sent_px, 1) * 1e3, 1e3 / med))
    print("# output sha256 %s" % bus.digest.hexdigest()[:12])
    print("# last pixel payload sha256 %s (%d bytes), displayio from %s"
          % (hashlib.sha256(bus.last).hexdigest()[:12], len(bus.last),
             os.path.dirname(displayio.__file__)))
    if a.fast:
        print("# _fill_area calls: %s" % tilegrid_fast.stats)


if __name__ == "__main__":
    main()
