#!/usr/bin/env python3
"""Melissa's #194 review: a nested group removed while its queue is being drained.

    PYTHONPATH=grouperase:. python3 group_nested_race.py

A child group holds two squares, both drawn. The first square is removed, so its
old area waits in the child's queue. A thread then starts the child's part of a
refresh and is held right after it takes that area off the queue. While it is
held, the main thread removes the child from the root. The thread is let go,
the display refreshes, and the screen is compared with a full redraw. Pixels of
the first square left behind are the lost area.

The pause is a queue subclass, so a fix that never pops one area at a time just
runs straight through. The waits time out, so a fix that makes the removal wait
for the drain shows up as "blocked", not as a hang.
"""
import sys
import threading

import displayio

from group_remove import build, square, stale_pixels
from vector_travel import Recorder

WAIT = 1.0


def paused_queue(queue, popped, resume):
    """A copy of queue whose first popleft or pop waits for resume."""

    class Paused(type(queue)):
        held = False

        def _hold(self):
            if not Paused.held:
                Paused.held = True
                popped.set()
                resume.wait(WAIT)

        def popleft(self):
            item = super().popleft()
            self._hold()
            return item

        def pop(self, *args):
            item = super().pop(*args)
            self._hold()
            return item

    return Paused(queue)


def trial():
    # pylint: disable=protected-access
    def scene(root):
        child = displayio.Group()
        first, second = square(4, 4, 3, 3, 1), square(40, 30, 3, 3, 2)
        child.append(first)
        child.append(second)
        root.append(child)
        return child, first

    display, root, (child, first) = build(scene, 0)
    recorder = Recorder(display)
    display.refresh()

    child.remove(first)
    popped, resume = threading.Event(), threading.Event()
    child._removed_areas = paused_queue(child._removed_areas, popped, resume)
    drain = threading.Thread(target=child._get_refresh_areas, args=([],))
    drain.start()
    held = popped.wait(WAIT)

    remover = threading.Thread(target=root.remove, args=(child,))
    remover.start()
    remover.join(0.2)
    blocked = remover.is_alive()
    resume.set()
    drain.join(WAIT)
    remover.join(WAIT)

    display.refresh()
    settled = bytes(recorder.framebuffer)
    display._core.full_refresh = True
    display.refresh()
    stale = stale_pixels(settled, bytes(recorder.framebuffer))
    return held, blocked, stale


def main():
    held, blocked, stale = trial()
    print("# nested group removed mid-drain, displayio from %s" % displayio.__file__)
    print("drain paused after a pop: %s" % ("yes" if held else "no, never popped one"))
    print("removal waited for the drain: %s" % ("yes, blocked" if blocked else "no"))
    print("stale pixels after refresh: %d %s" % (stale, "STALE" if stale else "ok"))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
