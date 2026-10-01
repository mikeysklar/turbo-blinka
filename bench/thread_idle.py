#!/usr/bin/env python3
"""What the background refresh thread costs when nothing changes, and what it delivers when something does.

    PYTHONPATH=main248:. python3 thread_idle.py [--seconds 10]

A 320x240 display on a bus that sends nowhere, auto_refresh on, a static
background TileGrid. Three phases:

idle      the app sleeps; CPU the process burns, as % of one core
compute   the app counts in a tight loop; how far it gets, so GIL contention shows
animate   the app moves a vectorio circle once per 60 Hz frame; refreshes done
"""
import argparse
import time

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus, host

W, H = 320, 240


def main():
    # pylint: disable=protected-access
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=10.0)
    a = ap.parse_args()

    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=W, height=H, auto_refresh=False)
    refreshes = [0]
    real_refresh = display.refresh

    def counted(*args, **kwargs):
        refreshes[0] += 1
        return real_refresh(*args, **kwargs)

    display.refresh = counted

    root = displayio.Group()
    background = displayio.Bitmap(W, H, 2)
    palette = displayio.Palette(2)
    palette[0], palette[1] = 0x000000, 0x1565D8
    root.append(displayio.TileGrid(background, pixel_shader=palette))
    circle = vectorio.Circle(pixel_shader=palette, radius=20, x=40, y=H // 2, color_index=1)
    root.append(circle)
    display.root_group = root
    display.auto_refresh = True
    time.sleep(1)  # first full refresh out of the way

    print("# thread idle, %s, %.0f s per phase, displayio from %s"
          % (host(), a.seconds, displayio.__file__))

    cpu0, wall0 = time.process_time(), time.monotonic()
    time.sleep(a.seconds)
    cpu = (time.process_time() - cpu0) / (time.monotonic() - wall0)
    print("idle: %.1f%% of a core" % (cpu * 100))

    count, end = 0, time.monotonic() + a.seconds
    while time.monotonic() < end:
        for _ in range(1000):
            count += 1
    print("compute: %.2f M iterations per second" % (count / a.seconds / 1e6))

    refreshes[0] = 0
    frames, step, x = 0, 1 / 60, 40
    start = time.monotonic()
    end = start + a.seconds
    while time.monotonic() < end:
        x = 40 if x > W - 40 else x + 4
        circle.x = x
        frames += 1
        time.sleep(max(0.0, start + frames * step - time.monotonic()))
    print("animate: %d moves, %d refreshes, %.1f refreshes per second"
          % (frames, refreshes[0], refreshes[0] / a.seconds))

    display.auto_refresh = False
    displayio._stop_background()


if __name__ == "__main__":
    main()
