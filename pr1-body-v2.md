[Side-by-side video](https://drive.google.com/file/d/14NT4r2asXWckTx3YOvZuRicXdUTdyauY/view): stock on the left, this PR on the right, 10 seconds each.

## What
Every `Bitmap` change was drawn and sent to the display twice. Now it is drawn once. Seven lines in `TileGrid._get_refresh_areas`.

## Why
- Full-screen refresh takes half as long
- Extra copy landed in wrong place
- Matches the C `TileGrid.c` behavior

The bitmap added its area to the display's list, then the TileGrid added its own copy too.

| Full-screen refresh, ms | main | this PR |
|---|---|---|
| Pi 5, PiTFT 3.5" over SPI | 1147 | 573 |
| Pi 5, no display | 325.7 | 164.3 |
| Pi Zero 2 W, no display | 3595 | 1796 |

## Tested
- Pi 5 with PiTFT Plus 3.5"
- Pi 5 headless
- Pi Zero 2 W headless
- Pixel data sent is identical

Not tested: e-paper, I2C or parallel displays.

<details><summary>code.py for the PiTFT row</summary>

```python
import statistics
import time
import board
import displayio
import fourwire
from adafruit_hx8357 import HX8357

displayio.release_displays()
bus = fourwire.FourWire(board.SPI(), command=board.D25, baudrate=24_000_000)
display = HX8357(bus, width=480, height=320, auto_refresh=False)

palette = displayio.Palette(4)
palette[0], palette[1], palette[2], palette[3] = 0xE0103A, 0x1565D8, 0x12A150, 0xF2B400
bitmap = displayio.Bitmap(480, 320, 4)
group = displayio.Group()
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group
display.refresh()

times = []
for n in range(6):
    bitmap.fill((n + 1) % 4)
    start = time.monotonic()
    display.refresh()
    times.append((time.monotonic() - start) * 1000)
print("full-screen refresh, median of 6: %.0f ms" % statistics.median(times))
```

```
main:    full-screen refresh, median of 6: 1147 ms
this PR: full-screen refresh, median of 6: 573 ms
```

</details>

## AI assistance
Claude was used.
