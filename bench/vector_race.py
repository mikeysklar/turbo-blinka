#!/usr/bin/env python3
"""Check PR #186, vector shape changes made while a refresh is running.

    PYTHONPATH=main241 python3 vector_race.py
    PYTHONPATH=vec186 python3 vector_race.py

Three checks, all headless:

1. Interleave. Collect the refresh areas, change the shape, then finish the
   refresh, which is the order issue #160 describes. The change must still be
   waiting on the next frame. On the code before the fix it is lost.
2. Same dirty rectangles. 500 random moves and resizes, printing a hash of
   every area collected, so the two builds can be compared line for line.
3. Timing. The two numbers the PR quotes, a clean scan and a change plus
   refresh cycle.
"""
import hashlib
import random
import sys
import time

import busdisplay
import displayio
import vectorio

from displayio_refresh import NullBus, host

W, H = 240, 240


def make_display():
    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=W, height=H,
                                    auto_refresh=False)
    palette = displayio.Palette(1)
    palette[0] = 0xFF55FF
    circle = vectorio.Circle(pixel_shader=palette, radius=20, x=120, y=120)
    group = displayio.Group()
    group.append(circle)
    display.root_group = group
    display.refresh()
    return display, circle


def areas_of(display):
    return [(a.x1, a.y1, a.x2, a.y2)
            for a in display._get_refresh_areas()]  # pylint: disable=protected-access


def check_interleave():
    """The change lands between collecting the areas and finishing the refresh."""
    display, circle = make_display()
    circle.x = 40
    display.refresh()  # draw it where it is now, nothing outstanding

    during = areas_of(display)  # refresh starts here
    circle.x = 200  # the application thread moves the shape mid refresh
    display._core.finish_refresh()  # pylint: disable=protected-access

    after = areas_of(display)
    covers_200 = any(a[0] <= 200 <= a[2] for a in after)
    print("| interleave | collected %d areas at start, %d after | move kept: %s |"
          % (len(during), len(after), "yes" if covers_200 else "NO, change lost"))
    return covers_200


def check_full_refresh_interleave():
    """The same, but the refresh in progress is a full screen one."""
    display, circle = make_display()
    display._core.full_refresh = True  # pylint: disable=protected-access
    areas_of(display)
    circle.x = 210
    display._core.finish_refresh()  # pylint: disable=protected-access
    after = areas_of(display)
    covers = any(a[0] <= 210 <= a[2] for a in after)
    print("| full refresh interleave | %d areas after | move kept: %s |"
          % (len(after), "yes" if covers else "NO, change lost"))
    return covers


def check_random_frames(frames=500, seed=1234):
    """Every dirty rectangle, hashed, so two builds can be compared."""
    display, circle = make_display()
    rng = random.Random(seed)
    digest = hashlib.sha256()
    collected = 0
    for _ in range(frames):
        for _ in range(rng.randint(1, 3)):
            what = rng.randrange(3)
            if what == 0:
                circle.x = rng.randrange(-30, W + 30)
            elif what == 1:
                circle.y = rng.randrange(-30, H + 30)
            else:
                circle.radius = rng.randrange(1, 60)
        areas = areas_of(display)
        collected += len(areas)
        digest.update(repr(areas).encode())
        display._core.finish_refresh()  # pylint: disable=protected-access
    print("| %d random frames | %d areas | %s |"
          % (frames, collected, digest.hexdigest()[:12]))


def time_clean_scan(calls=200_000):
    display, _ = make_display()
    display.refresh()
    get_areas = display._get_refresh_areas  # pylint: disable=protected-access
    t0 = time.perf_counter()
    for _ in range(calls):
        get_areas()
    took = time.perf_counter() - t0
    print("| clean scan | %d calls | %.1f ns per call |" % (calls, took / calls * 1e9))


def time_move_cycle(cycles=50_000):
    display, circle = make_display()
    finish = display._core.finish_refresh  # pylint: disable=protected-access
    get_areas = display._get_refresh_areas  # pylint: disable=protected-access
    t0 = time.perf_counter()
    for i in range(cycles):
        circle.x = 100 + (i & 31)
        get_areas()
        finish()
    took = time.perf_counter() - t0
    print("| move, collect, finish | %d cycles | %.2f us per cycle |"
          % (cycles, took / cycles * 1e6))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# vector race checks, %s, vectorio from %s, %s"
          % (host(), vectorio.__file__, time.strftime("%Y-%m-%d %H:%M")))
    print("| check | detail | result |")
    print("|---|---|---|")
    kept = check_interleave()
    kept_full = check_full_refresh_interleave()
    check_random_frames()
    time_clean_scan()
    time_move_cycle()
    return 0 if (kept and kept_full) else 1


if __name__ == "__main__":
    sys.exit(main())
