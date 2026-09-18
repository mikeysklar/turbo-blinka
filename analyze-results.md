# turbo analyze over Blinka, 2026-09-18

`turbo_cli.py analyze` run unchanged from a Mac. It reads source shape only, no
timing. Run against shallow clones of both repos.

| Tree | Commit | Functions | skip | native | viper |
|---|---|---|---|---|---|
| Adafruit_Blinka `src/` | 37a4ff5 (2026-07-30) | 829 | 764 | 65 | 0 |
| Adafruit_Blinka_Displayio | 69909dc (2026-07-27) | 308 | 276 | 30 | 2 |
| Learn guides, Pi-flavored grep (127 files) | local checkout | - | - | 65 | 7 |

## Adafruit_Blinka: nothing to compile

All 65 hits are loops around I/O: `i2c.scan`, `readfrom_into`, HID transfers to
u2if / MCP2221 / FT232H, sysfs opens, `keypad` scans. The time is in the kernel
or on the wire. No backend changes that. The only CPU loops are the two
`neopixel_write` list builders (u2if and generic board), and they are trivial.

Blinka core is not a turbo target.

## Adafruit_Blinka_Displayio: the target

This is CircuitPython's C displayio re-written in pure Python, and it runs per
pixel on every refresh.

| Function | File:line | Shape |
|---|---|---|
| `TileGrid._fill_area` | `displayio/_tilegrid.py:231` | The inner loop of every refresh. Per pixel: mask test, tile lookup with 6 divisions, `isinstance` x3, `Bitmap._get_pixel` call, `Palette._get_color` call, `struct.pack_into`. All through attribute access on two struct objects. |
| `VectorShape._fill_area` | `vectorio/_vectorshape.py:218` | Same loop shape for vectorio. |
| `Polygon._get_pixel` | `vectorio/_polygon.py:93` | Called per pixel from the loop above. |
| `bitmaptools.draw_line`, `draw_circle` | `bitmaptools/__init__.py:33,62` | Pure integer Bresenham. analyze says viper. |
| `bitmaptools.blit`, `rotozoom`, `arrayblit`, `fill_row`, `write_pixels`, `boundary_fill` | `bitmaptools/__init__.py` | Nested per-pixel loops over a Bitmap. |
| `Bitmap.fill`, `_from_buffer` | `displayio/_bitmap.py:202,72` | Per-element loops. |

analyze marks `_fill_area` "native" and not "viper" only because of the object
attribute access. On CPython that distinction goes away: all three backends want
the same rewrite, locals and flat buffers instead of `input_pixel.x`.

`_bitmap.py` already hints at numpy in its docstring but the package does not
depend on it. Pillow is already a dependency.

## Bundle libraries on a Pi

The turbo library list carries over as-is. The same source
runs under Blinka: framebuf, imageload, bitmap_font, display_shapes, miniqr,
bitmapsaver, led_animation. They all draw into the Blinka_Displayio Bitmap, so
they stack on top of the target above.

## Learn guides

The guides that actually run on a Pi mostly do I/O, Pillow drawing or
OpenCV/numpy already (Thermal_Camera_Overlay, TFT_Sidekick, EInk_Bonnet
calendar, gif players). Pillow and numpy are C. Few hot Python loops there.

The guides with real loops are the displayio ones, and they are written for
MCUs but run on a Pi through Blinka_Displayio unchanged:

| Guide | Function | Verdict |
|---|---|---|
| CircuitPython_RGBMatrix/life | `apply_life_rule`, `conway` | viper / native |
| MatrixPortal_S3_Analog_Clock | `draw_line`, `fill_dot`, `_draw_stars` | viper / native |
| LED_Matrix_Clock | `draw_char`, `draw_eye` | native |
| PyGamer_Improved_Thermal_Camera | `update_image_frame` | native |
| ulab_Crunch_Numbers_Fast/waterfall | `show` | native |
| CircuitPython_Painter, Light_Paintstick | `read_le` | viper |

Conway life is the natural benchmark: it is already the turbo demo on the farm,
so the Pi number lines up against the RP2040/RP2350 numbers.

## Takeaway

One target gives most of the win: the Blinka_Displayio refresh loop plus
bitmaptools. Everything a user draws on a Pi goes through it.
