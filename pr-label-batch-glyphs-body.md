Video, main on top: https://drive.google.com/file/d/1XtDlfm_dZXjM-HtLj03PtCab3K6b16BS/view?usp=sharing

## What
A label asks the font for all of its letters at once, not one at a time.

## Why
Each new letter cost a font read and a garbage collection. #85 fixed this; #102 and #110 accidentally dropped it.

## Measured
| | main | this PR | |
|---|---|---|---|
| Pi 5, LeagueSpartan-Bold-16.bdf | 207.1 ms | 97.3 ms | 2.1x |
| Pi 5, Junction-regular-24.pcf | 207.5 ms | 22.1 ms | 9.4x |
| Pi Zero 2 W, LeagueSpartan-Bold-16.bdf | 1398.8 ms | 677.5 ms | 2.1x |
| Pi Zero 2 W, Junction-regular-24.pcf | 1412.4 ms | 206.4 ms | 6.8x |
| Pi 5, HX8357, 20 labels, refresh after each | 4.24 s | 1.45 s | 2.9x |
| Pi Zero 2 W, ILI9341, 16 labels, same | 20.00 s | 7.08 s | 2.8x |

Font rows: one `label.Label`, 44 characters, newly loaded font, median of 10 runs.

## Tested
Raspberry Pi 5 and Pi Zero 2 W with Blinka, Python 3.13.5. Not tested on a CircuitPython board.

| check | result |
|---|---|
| pixels drawn, 4 fonts, `label` and `bitmap_label` | same as main |
| label whose letters are already loaded | same time as main |
| two line label update, adafruit_bitmap_font 2.4.2 and 2.4.3 | same time as main |
| `terminalio.FONT`, which has no `load_glyphs` | works |

## Scope
Repeated letters and newlines are not sent to the font. TextBox is unchanged.

## AI assistance
Written with Claude Code. I ran the measurements on both Pis and filmed the panels myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
