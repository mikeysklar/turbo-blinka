# What a Cython backend for `turbo build` would generate from src/pixels.py.
# Only the decorator and signature lines change, the body is byte-for-byte the
# viper source:
#   @turbo.viper      -> @cython.boundscheck(False) / wraparound(False) / cdivision(True)
#   out: ptr8         -> out: cython.uchar[:]   (any buffer: bytearray, array, memoryview)
#   name: int         -> name: cython.int       (32-bit, wraps like viper)
#   int locals        -> @cython.locals(...)    (viper infers these, Cython must be told)
# Build: cp pixels_typed.py build/pixels.py && cythonize -i -3 build/pixels.py
import cython


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.locals(px=cython.int, cx=cython.int, x=cython.int, y=cython.int,
               i=cython.int, x2=cython.int, y2=cython.int)
def mandel_row(out: cython.uchar[:], width: cython.int, dx: cython.int,
               cy: cython.int, max_iter: cython.int):
    # fixed point, 12 fractional bits, integers only so viper can take it
    for px in range(width):
        cx = px * dx - (2 << 12)
        x = 0
        y = 0
        i = 0
        while i < max_iter:
            x2 = (x * x) >> 12
            y2 = (y * y) >> 12
            if x2 + y2 > (4 << 12):
                break
            y = ((x * y) >> 11) + cy
            x = x2 - y2 + cx
            i += 1
        out[px] = i


def _turbo_bench():
    W, H, IT = 160, 120, 64
    row = bytearray(W)
    dx = (3 << 12) // W
    total = 0
    for r in range(H):
        mandel_row(row, W, dx, ((r * 2) << 12) // H - (1 << 12), IT)
        total += sum(row)
    return total
