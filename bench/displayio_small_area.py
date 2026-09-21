"""Refresh time for small dirty areas, a 256 colour palette, VALUES bitmap values (default 256)."""
import os, statistics, sys, time
import busdisplay, displayio
from displayio_refresh import NullBus

displayio.release_displays()
display = busdisplay.BusDisplay(NullBus(), b"", width=240, height=240, auto_refresh=False)
displayio._stop_background()
pal = displayio.Palette(256)
for i in range(256):
    pal[i] = i * 65793
values = int(os.environ.get("VALUES", "256"))
bmp = displayio.Bitmap(240, 240, values)
g = displayio.Group()
g.append(displayio.TileGrid(bmp, pixel_shader=pal))
display.root_group = g
display.refresh()
print("# displayio from", os.path.dirname(displayio.__file__))
for n in (1, 4, 8, 16, 32, 240):
    times = []
    for rep in range(30 if n < 240 else 5):
        v = rep % (values - 1) + 1
        bmp[0, 0] = v
        bmp[n - 1, n - 1] = v
        t = time.perf_counter()
        display.refresh()
        times.append((time.perf_counter() - t) * 1e6)
    print("%3dx%-3d %9.0f us" % (n, n, statistics.median(times)))
