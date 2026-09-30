## What
`bitmaptools.blit` marks the changed area once, then copies pixels directly, like `fill_region` and the C version.

## Why
Every copied pixel updated the changed area on its own. That bookkeeping was most of the time `blit` took.

## Measured
| | main | this PR | |
|---|---|---|---|
| Pi 5, `blit` 240x240 | 183.0 ms | 66.7 ms | 2.7x |
| Pi Zero 2 W, `blit` 240x240 | 1884.7 ms | 598.5 ms | 3.1x |
| Pi 5, HX8357, 48 sprites, refresh after each | 0.62 s | 0.40 s | 1.55x |
| Pi Zero 2 W, ILI9341, same | 2.99 s | 1.64 s | 1.82x |

`blit` rows are the median of 10 runs. Panel rows are one pass, SPI at 24 MHz.

Video, main on top: https://drive.google.com/file/d/17TqYsk3G6I68wKyaOJ4jTdi27EL1zvbW/view?usp=sharing

## Tested
Pi 5 and Pi Zero 2 W, Python 3.13.5. Same pixels as main across 120 edge cases, every bit depth.

| case | main | this PR |
|---|---|---|
| read-only destination | `RuntimeError: Read-only object` | `RuntimeError: Read-only`, even if every pixel is skipped |
| every pixel skipped | nothing marked changed | whole rectangle marked, as in C |

## Scope
`Bitmap` subclasses keep the old loop. Copying onto an overlapping part of the same bitmap is unchanged.

## AI assistance
Written with Claude Code. I ran every test on both Pis and filmed the panels myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
