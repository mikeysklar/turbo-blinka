Title: Fix copying part of a bitmap onto itself

[Video, main on top](https://drive.google.com/file/d/1UEkoknWUkpWX-MUcrtbxg__T9y7hONHb/view?usp=sharing)

## What
`bitmaptools.blit` copies from the far edge when moving right or down, as CircuitPython does.

## Why
Copying a bitmap into itself, shifted right or down, read pixels it had already overwritten, so the copy came out smeared.

## Tested
Raspberry Pi 5 and Pi Zero 2 W, Python 3.13.5. A 16x12 bitmap where each pixel holds its own number, shifted 3 pixels within itself. Wrong pixels compared with copying from an untouched copy:

| shift | main | this PR |
|---|---|---|
| right | 30 | 0 |
| down | 24 | 0 |
| down and left, down and right | 15, 15 | 0, 0 |
| whole bitmap right and down | 60 | 0 |
| right with `skip_source_index`, down with `skip_dest_index` | 30, 24 | 0, 0 |
| left, up, up and left, up and right | 0 | 0 |

Same on both boards, and the same for a `Bitmap` subclass.

Copies between two different bitmaps are unchanged: 114 of 120 earlier `blit` test scenes give identical pixels. The other 6 are this bug, plus one case that already raises on main. Speed is the same:

| `blit` 240x240, median of 10 | main | this PR |
|---|---|---|
| Pi 5 | 65.8 ms | 66.9 ms |
| Zero 2 W | 597.1 ms | 598.9 ms |

## AI assistance
Written with Claude Code. I ran every test on both Pis myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
