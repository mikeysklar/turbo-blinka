# Next PRs, after 5b

Widen the #179 fast path. Gains are guesses: measure stock first on both Pis,
then PR only the ones the numbers justify. Each one changes the shared pixel
loop and needs its own test scenes.

- 4b: `OnDiskBitmap` fast path, images read from a file, ~2x
- 4a: `ColorConverter` fast path, images without a palette, ~3x
- 4c: `vectorio` fast path, shapes, ~3x
- 4d: mono and under-16-bit displays fast path, ~3x
