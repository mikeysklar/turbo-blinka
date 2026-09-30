Video, main on top: TODO link

## What
Removing something from a group now erases it from the screen on the next refresh.

## Why
`pop()`, `remove()`, `del` and replacing an item left the old pixels on screen. CircuitPython redraws that area.

## Tested
Raspberry Pi 5 and Pi Zero 2 W, Python 3.13.5. Each scene's screen is compared with a full redraw.

| scene | main | this PR |
|---|---|---|
| `pop()`, `remove()`, `del`, `del group[:]`, `group[i] = other` | old pixels stay | erased |
| a label, a scaled group, a layer in a nested group | old pixels stay | erased |
| a vectorio shape, moved or not | old pixels stay | erased |
| add back after `remove()` or `del` | `ValueError: Layer already in a group.` | works |
| `group[i] = ` a layer already in another group | accepted | `ValueError`, as `insert` does |
| move a nested group right after it is shown | old pixels stay | erased |
| move, write a pixel, hide, palette, flip, scale | same as a full redraw | same |

Same results at rotation 0 and 90, on both boards.

With `auto_refresh` on, the app changing layers while the background thread redraws, 40 runs each:

| wrong screens after | Pi 5 main | Pi 5 this PR | Zero 2 W main | Zero 2 W this PR |
|---|---|---|---|---|
| `pop()` | 29 | 0 | 15 | 0 |
| moves | 40 | 4 | 40 | 8 |
| bitmap writes | 0 | 0 | 8 | 5 |
| a mix of all four | 32 | 0 | 35 | 2 |

The moves and writes left over also happen on main without any removal.

## Cost
Erasing takes a redraw. Removing 48 squares one at a time: 0.12 s on a Pi 5, 0.19 s on a Zero 2 W.

## Differences from CircuitPython
| | why |
|---|---|
| removed areas are queued, like vectorio's dirty areas | a removal during a background refresh is still erased |
| the queue merges into one area past 8 | a group that is not shown never drains it |
| `del` still takes a slice | it did before; the C raises instead |
| a TileGrid records where a full refresh draws it | otherwise it has no drawn area until its second refresh |
| a vectorio shape inside a removed group is erased too | the C skips it |

## AI assistance
Written with Claude Code. I ran every test on both Pis and filmed the panels myself.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
