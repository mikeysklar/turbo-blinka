# One recording to a titled side-by-side mp4

How `pi5-2x-3.5inch.mov` (one 35.6 s take, stock run then patched run) became
`pi5-2x-3.5inch-side-by-side.mp4` (12 s, 1400x560, 2.5 MB). Now packaged as the
`/split-video` skill: `~/.claude/skills/split-video/`.

## 1. Make the test filmable

`bench/pitft_demo.py --seconds 10` on each run: 2 s of black, 10 s of
full-screen fills, black again. Fixed time, not fixed work, so both clips are
the same length and the faster run just shows more frames.

```
python3 pitft_demo.py --seconds 10                       # stock
sleep 3
PYTHONPATH=patched python3 pitft_demo.py --seconds 10    # patched
```

## 2. Look at the whole take

One frame per second on a contact sheet. Shows where the screen is in the frame
and roughly when each run starts.

```
ffmpeg -v error -y -i IN.mov -vf "fps=1,scale=256:-1,tile=9x4" -frames:v 1 overview.png
```

Read off two rectangles, `W:H:X:Y` in source pixels:

| Rectangle | Value here | Why |
|---|---|---|
| watch | `260:30:450:250` | Thin strip at the top of the panel. The panel paints top-down, so this changes first. |
| crop | `700:560:230:100` | The display and the Pi, not the desk. |

## 3. Find each run's first coloured frame

Per-frame average Y, U, V of the watch strip:

```
ffmpeg -v error -i IN.mov -vf "crop=260:30:450:250,signalstats,metadata=print:file=stats.txt" -f null -
```

Colour strength per frame is `abs(U-128) + abs(V-128)`. Black, grey and white
are near 0, saturated red is about 45. A run start is a frame that:

- follows at least 1.5 s without colour, and
- is followed by 3 s where at least 90% of frames are coloured.

| Found | Time s | Kept? |
|---|---|---|
| HX8357 white init flash | 0.6, 19.9 | No. White has no chroma. |
| First refresh shows red for 0.6 s | 2.0, 21.3 | No. Does not hold 3 s. |
| Stock run starts | 5.80 | Yes |
| Patched run starts | 24.47 | Yes |

The script start times on the Pi were 19 s apart. The pixel starts are 18.67 s
apart. That third of a second is why the cut uses pixels, not the clock.

## 4. Cut, crop, title, stack

Each half starts 1 s before its first coloured frame and runs 12 s.

This Mac's ffmpeg has no `drawtext` filter (`ffmpeg -filters | grep drawtext`
is empty), so the titles are PNGs: white Helvetica 34 px on a 65% black box,
made with Pillow in a throwaway venv, then overlaid.

```
ffmpeg -y -i IN.mov -i label_l.png -i label_r.png -filter_complex "\
[0:v]trim=start=4.80:duration=12,setpts=PTS-STARTPTS,crop=700:560:230:100[lv];[lv][1:v]overlay=16:16[l];\
[0:v]trim=start=23.47:duration=12,setpts=PTS-STARTPTS,crop=700:560:230:100[rv];[rv][2:v]overlay=16:16[r];\
[l][r]hstack=inputs=2" \
-an -c:v libx264 -crf 20 -pix_fmt yuv420p -movflags +faststart OUT.mp4
```

| Piece | Does |
|---|---|
| `trim` + `setpts=PTS-STARTPTS` | Cuts the window and restarts its clock at 0, so both halves play in step. |
| `crop` | Same rectangle on both, so the halves match. |
| `overlay=16:16` | Title in the top-left corner. |
| `hstack` | Left and right. `vstack` for portrait footage. |
| `-pix_fmt yuv420p -movflags +faststart` | Plays in browsers, Slack and GitHub. |

With a `drawtext` build, skip the PNGs:

```
drawtext=text='stock':x=16:y=16:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=8
```

## 5. Check it

Tile the result and look. Both halves must leave black on the same frame.

```
ffmpeg -v error -y -i OUT.mp4 -vf "fps=1.5,scale=560:-1,tile=3x6" -frames:v 1 check.png
```

## As one command

```
python3 ~/.claude/skills/split-video/scripts/split_video.py pi5-2x-3.5inch.mov \
    --labels "stock  ·  9 fills in 10 s" "patched  ·  18 fills in 10 s" \
    --watch 260:30:450:250 --crop 700:560:230:100
```

Reproduces the same two start times (5.80, 24.47) and the same output.
