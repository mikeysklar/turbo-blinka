Title: Stop displayio using CPU while the screen is idle

## What
The background refresh thread now waits 1 ms between checks instead of looping nonstop.

## Why
Just importing displayio kept a Pi Zero 2 W core a quarter busy. Fixes adafruit/Adafruit_CircuitPython_DisplayIO_SSD1306#48.

## Tested
Raspberry Pi 5 and Pi Zero 2 W, Python 3.13.5, CPU use of the whole process over 10 s.

| idle CPU, % of one core | Pi 5 main | Pi 5 this PR | Zero 2 W main | Zero 2 W this PR |
|---|---|---|---|---|
| `import displayio` only | 4.7 | 0.3 | 25.0 | 2.1 |
| display, `auto_refresh=False` | 4.9 | 0.3 | 26.0 | 2.2 |
| display, `auto_refresh=True`, nothing changing | 5.8 | 0.4 | 33.5 | 8.6 |

Median of 5 runs with `auto_refresh` on, 3 runs for the others.

## Cost
A frame can start up to 1 ms later. Measured, a circle moving every frame, median of 5 runs:

| refreshes per second | main | this PR |
|---|---|---|
| Pi 5 | 54.6 | 52.0 |
| Zero 2 W | 26.3 | 26.0 |

An app's own loop runs at the same speed either way.

## Background
#143 proposed this same 1 ms. #156 used `sleep(0.0)`, which returns immediately. CircuitPython checks displays every 1/1024 s.

## AI assistance
Written with Claude Code. I ran every measurement on both Pis myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
