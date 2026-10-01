#!/usr/bin/env python3
"""CPU the process burns with displayio imported, for the cases in
Adafruit_CircuitPython_DisplayIO_SSD1306 issue #48.

    PYTHONPATH=main248:. python3 thread_idle_cases.py import|off
"""
import sys
import time

import displayio

if sys.argv[1] == "off":
    import busdisplay
    from displayio_refresh import NullBus

    displayio.release_displays()
    display = busdisplay.BusDisplay(NullBus(), b"", width=320, height=240, auto_refresh=False)
    display.root_group = displayio.Group()
    display.refresh()

cpu0, wall0 = time.process_time(), time.monotonic()
time.sleep(10)
print("%s: %.1f%% of a core" % (sys.argv[1], 100 * (time.process_time() - cpu0) / (time.monotonic() - wall0)))
