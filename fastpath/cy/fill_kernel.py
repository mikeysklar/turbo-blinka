# Generated from ../fill_kernel.py: what a Cython backend for `turbo build` would
# emit. Decorator and signature lines only, the body is unchanged.
#   buf, lut   -> cython.ushort[:]     mask -> cython.uint[:]
#   src        -> cython.ulong[:]      (Bitmap._data is array("L"))
#   tiles, opaque -> cython.uchar[:]   int  -> cython.int, locals declared
# Build: cythonize -i -3 fill_kernel.py
import cython


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.locals(full=cython.int, y=cython.int, x=cython.int, row_start=cython.int,
               local_y=cython.int, local_x=cython.int, offset=cython.int, tile=cython.int,
               tx=cython.int, ty=cython.int, pix=cython.int, b=cython.int)
def fill_kernel(buf: cython.ushort[:], mask: cython.uint[:], src: cython.ulong[:],
                tiles: cython.uchar[:], lut: cython.ushort[:], opaque: cython.uchar[:],
                start: cython.int, x_stride: cython.int, y_stride: cython.int,
                x_shift: cython.int, y_shift: cython.int, start_x: cython.int,
                end_x: cython.int, start_y: cython.int, end_y: cython.int,
                scale: cython.int, tile_w: cython.int, tile_h: cython.int,
                top_left_x: cython.int, top_left_y: cython.int, w_tiles: cython.int,
                h_tiles: cython.int, bmp_w_tiles: cython.int, bmp_w: cython.int,
                bmp_h: cython.int, bmp_stride: cython.int, itemsize: cython.int,
                bits: cython.int, xs: cython.int, xm: cython.int,
                bitmask: cython.int) -> cython.int:
    # buf: uint16 per display pixel. mask: uint32 words, 1 bit per pixel.
    # src: Bitmap._data, array("L") words. tiles: uint8. lut: uint16 colour per
    # palette index. opaque: uint8 per palette index.
    # Returns 0 if a transparent pixel was met (the layer did not fully cover).
    full = 1
    for y in range(start_y, end_y):
        row_start = start + (y - start_y + y_shift) * y_stride
        local_y = y // scale
        for x in range(start_x, end_x):
            offset = row_start + (x - start_x + x_shift) * x_stride
            if mask[offset >> 5] & (1 << (offset & 31)):
                continue
            local_x = x // scale
            tile = tiles[((local_y // tile_h + top_left_y) % h_tiles) * w_tiles
                         + (local_x // tile_w + top_left_x) % w_tiles]
            tx = (tile % bmp_w_tiles) * tile_w + local_x % tile_w
            ty = (tile // bmp_w_tiles) * tile_h + local_y % tile_h
            pix = 0
            if tx < bmp_w and ty < bmp_h:
                if bits == 8:
                    b = ty * bmp_stride * itemsize + tx
                    pix = (src[b // itemsize] >> ((b % itemsize) * 8)) & 0xFF
                else:
                    pix = (src[ty * bmp_stride + (tx >> xs)]
                           >> (32 - ((tx & xm) + 1) * bits)) & bitmask
            if opaque[pix]:
                mask[offset >> 5] |= 1 << (offset & 31)
                buf[offset] = lut[pix]
            else:
                full = 0
    return full
