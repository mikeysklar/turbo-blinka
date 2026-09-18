# The inner loop of displayio TileGrid._fill_area for the common case: an
# in-memory Bitmap of 1 to 8 bits per value, a Palette, a 16-bit display.
# Same arithmetic as Adafruit_Blinka_Displayio 2.3.2 displayio/_tilegrid.py,
# with every object lookup hoisted out: flat buffers and ints only, so it is
# viper-shaped and each turbo backend can take it as is.
from turbo import turbo


@turbo.viper
def fill_kernel(buf, mask, src, tiles, lut, opaque,
                start: int, x_stride: int, y_stride: int, x_shift: int, y_shift: int,
                start_x: int, end_x: int, start_y: int, end_y: int, scale: int,
                tile_w: int, tile_h: int, top_left_x: int, top_left_y: int,
                w_tiles: int, h_tiles: int, bmp_w_tiles: int,
                bmp_w: int, bmp_h: int, bmp_stride: int, itemsize: int,
                bits: int, xs: int, xm: int, bitmask: int) -> int:
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
