#!/usr/bin/env python3
"""Conway life kernel bench for Blinka turbo backends.

    python3 life.py [--w 64] [--h 32] [--gens 50] [--trials 5]

The kernel is apply_life_rule from the Learn guide CircuitPython_RGBMatrix/life,
on a flat bytearray instead of a displayio Bitmap so it times the loop and
nothing else. Backends register in BACKENDS. Same rule as `turbo_cli bench`:
a backend whose result differs from plain Python is rejected, not timed.
"""
import argparse
import hashlib
import platform
import random
import time


def life_py(old, new, width, height):
    for y in range(height):
        yyy = y * width
        ym1 = ((y + height - 1) % height) * width
        yp1 = ((y + 1) % height) * width
        xm1 = width - 1
        for x in range(width):
            xp1 = (x + 1) % width
            neighbors = (
                old[xm1 + ym1] + old[xm1 + yyy] + old[xm1 + yp1] +
                old[x + ym1] + old[x + yp1] +
                old[xp1 + ym1] + old[xp1 + yyy] + old[xp1 + yp1])
            new[x + yyy] = neighbors == 3 or (neighbors == 2 and old[x + yyy])
            xm1 = x


# name -> loader. A loader returns (kernel, setup_seconds) or raises ImportError.
# setup_seconds is import plus any compile or JIT warm-up: the cost a user pays
# once per process before the first fast frame.
BACKENDS = {"python": lambda: (life_py, 0.0)}


def seed(width, height):
    rng = random.Random(2293)
    return bytearray(rng.random() < 0.33 for _ in range(width * height))


def run(kernel, width, height, gens):
    a, b = seed(width, height), bytearray(width * height)
    t0 = time.perf_counter()
    for _ in range(gens):
        kernel(a, b, width, height)
        a, b = b, a
    return time.perf_counter() - t0, hashlib.sha256(a).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--w", type=int, default=64)
    ap.add_argument("--h", type=int, default=32)
    ap.add_argument("--gens", type=int, default=50)
    ap.add_argument("--trials", type=int, default=5)
    a = ap.parse_args()

    try:
        with open("/proc/device-tree/model") as f:
            model = f.read().strip("\x00\n")
    except OSError:
        model = platform.machine()
    print("%s, Python %s, %dx%d, %d gens, best of %d"
          % (model, platform.python_version(), a.w, a.h, a.gens, a.trials))
    print("| backend | setup s | ms/gen | vs python | result |")
    print("|---|---|---|---|---|")

    base = want = None
    for name, load in BACKENDS.items():
        try:
            kernel, setup = load()
        except ImportError as e:
            print("| %s | - | - | - | not installed: %s |" % (name, e))
            continue
        best, digest = min(run(kernel, a.w, a.h, a.gens) for _ in range(a.trials))
        if want is None:
            base, want = best, digest
        if digest != want:
            print("| %s | %.2f | - | - | REJECTED %s != %s |" % (name, setup, digest, want))
            continue
        print("| %s | %.2f | %.2f | %.1fx | %s |"
              % (name, setup, best / a.gens * 1e3, base / best, digest))


if __name__ == "__main__":
    main()
