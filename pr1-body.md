Title: Draw each bitmap change once instead of twice

## What
Every change to a `Bitmap` was drawn and sent to the display twice. Now it is drawn once.

## Why
Screen updates on a Raspberry Pi take half as long. The extra copy was also drawn in the wrong place.

| `TileGrid._get_refresh_areas` | main | this PR | C `TileGrid.c` |
|---|---|---|---|
| Bitmap's dirty area | appended to the display's list | read into a local list | read into a local |
| TileGrid's copy, moved to screen position | appended | appended | linked to `tail` |
| Areas queued per change | 2 | 1 | 1 |
| Change skipped if the bitmap's area equals the previous list entry | yes, compared by value | no | no |

| Two pixels set in a 32x32 bitmap shown at (50,60) | Areas redrawn |
|---|---|
| main | `(0,0)-(32,32)` and `(50,60)-(82,92)` |
| this PR | `(50,60)-(82,92)` |

## Hardware tested
| Board | Display | OS | Python |
|---|---|---|---|
| Raspberry Pi 5 | PiTFT Plus 3.5" (2441), HX8357D, 480x320, SPI 24 MHz | Pi OS 64-bit trixie | 3.13.5 |
| Raspberry Pi 5 | none, bus discards bytes, 240x240 | same | same |
| Raspberry Pi Zero 2 W | none, bus discards bytes, 240x240 | same | same |

Not tested: e-paper (same code path), I2C and parallel displays, `OnDiskBitmap`.

## How I tested it
`bitmap.fill(n)` then `display.refresh()`, timed around `refresh()`. Median of 5 or 6 runs, milliseconds.

<details><summary>code.py for the PiTFT rows</summary>

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

| Full-screen refresh | main | this PR |
|---|---|---|
| Pi 5, PiTFT 3.5", SPI included | 1147 | 573 |
| Pi 5, no display | 325.7 | 164.3 |
| Pi Zero 2 W, no display | 3595 | 1796 |

| Check, main against this PR | Result |
|---|---|
| Last pixel data sent for a full refresh | identical, sha256 `78b6f072aa84` |
| Pixels drawn per 240x240 refresh | 115622, then 57811 |
| Sprite sheet: set a pixel, switch tile | same pixel data, one area instead of two |
| Hidden TileGrid, bitmap changed | nothing redrawn, both |
| Nothing changed | nothing redrawn, both |
| Move a 48x48 TileGrid on the PiTFT | 11.2 ms, both |

[Side-by-side video](https://drive.google.com/file/d/14NT4r2asXWckTx3YOvZuRicXdUTdyauY/view), main on the left, 10 seconds each.

## Scope
One function in `displayio/_tilegrid.py`. No API change. The per-pixel loop speed is a separate follow-up.

## AI assistance
Claude was used.
