#!/usr/bin/env python3
"""Does the screen still end up right when the refresh thread races the app?

    PYTHONPATH=grouperase:. python3 group_race.py [--trials 60]

Issue #150: with auto_refresh on, a change made while the background thread is
part way through a refresh could be lost, and #152 fixed it with _needs_refresh.
This runs the app side on the main thread against the real background refresh:
show a new group, move, add and remove layers at random moments, let the screen
settle, then compare what was sent against a forced full redraw of the same
state. Any difference is a lost or stale update.
"""
import argparse
import random
import sys
import time

import busdisplay
import displayio

from displayio_refresh import NullBus
from group_remove import W, H, square
from vector_travel import Recorder


def main():
    # pylint: disable=protected-access
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--actions", default="move,pop,add,write",
                    help="which of move, pop, add, write to use")
    ap.add_argument("--same-root", action="store_true",
                    help="keep one root group and clear it by popping, instead of "
                    "showing a new root group every trial")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    allowed = a.actions.split(",")

    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=W, height=H, auto_refresh=True)
    recorder = Recorder(display)
    bad = 0
    root = displayio.Group()
    display.root_group = root
    for trial in range(a.trials):
        if a.same_root:
            while len(root):
                root.pop()
            group = root
        else:
            group = displayio.Group()
        layers = [square(rng.randrange(0, W - 12), rng.randrange(0, H - 12),
                         rng.randrange(4, 24), rng.randrange(4, 24), rng.randrange(1, 5))
                  for _ in range(3)]
        for layer in layers:
            group.append(layer)
        if not a.same_root:
            display.root_group = group
        did = []
        for _ in range(6):
            time.sleep(rng.random() * 0.02)
            action = "move pop add write".split().index(rng.choice(allowed))
            did.append("move pop add write".split()[action])
            if action == 0:
                layers[rng.randrange(len(layers))].x = rng.randrange(0, W - 12)
            elif action == 1 and len(group) > 1:
                group.pop(rng.randrange(len(group)))
            elif action == 2:
                group.append(square(rng.randrange(0, W - 8), rng.randrange(0, H - 8),
                                    8, 8, rng.randrange(1, 5)))
            else:
                layers[rng.randrange(len(layers))].bitmap[0, 0] = rng.randrange(0, 5)
        time.sleep(0.3)  # let the background thread catch up
        display.auto_refresh = False
        time.sleep(0.2)  # a refresh already under way finishes
        settled = bytes(recorder.framebuffer)
        display._core.full_refresh = True
        display.refresh()
        if bytes(recorder.framebuffer) != settled:
            bad += 1
            print("trial %d: screen differs from a full redraw after %s"
                  % (trial, " ".join(did)))
        display.auto_refresh = True
    print("# group race, %d trials, %d wrong, %s, actions %s, displayio from %s"
          % (a.trials, bad, "same root" if a.same_root else "new root each trial",
             a.actions, displayio.__file__))
    displayio._stop_background()
    return bad


if __name__ == "__main__":
    sys.exit(main())
