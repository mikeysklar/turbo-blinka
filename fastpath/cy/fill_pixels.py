# Compiled twin of _fill_pixels in displayio/_tilegrid.py (Adafruit_Blinka_Displayio
# draft #179). Same arguments, same loop. Differences: typed locals, and the colour
# list is copied into an array("H") so the loop can index it as uint16.
#   buffer, table -> cython.ushort[:]   mask -> cython.uint[:]
#   words -> cython.ulong[:]            (Bitmap._data is array("L"))
#   tiles, opaque, data_bytes -> cython.uchar[:]
# Build: cythonize -i -3 fill_pixels.py
from array import array

import cython


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
@cython.locals(
    table=cython.ushort[:], tiles=cython.uchar[:], words=cython.ulong[:],
    data_bytes=cython.uchar[:],
    start=cython.int, x_stride=cython.int, y_stride=cython.int, x_shift=cython.int,
    y_shift=cython.int, start_x=cython.int, end_x=cython.int, start_y=cython.int,
    end_y=cython.int, scale=cython.int, tile_width=cython.int, tile_height=cython.int,
    top_left_x=cython.int, top_left_y=cython.int, width_in_tiles=cython.int,
    height_in_tiles=cython.int, bitmap_width_in_tiles=cython.int,
    words_per_row=cython.int, bytes_per_row=cython.int, width=cython.int,
    height=cython.int, bits=cython.int, values_shift=cython.int, values_mask=cython.int,
    bitmask=cython.int, full_coverage=cython.bint, y=cython.int, x=cython.int,
    row_start=cython.int, local_y=cython.int, local_x=cython.int, offset=cython.int,
    tile=cython.int, tile_x=cython.int, tile_y=cython.int, pixel=cython.int)
def fill_pixels(buffer: cython.ushort[:], mask: cython.uint[:], colors,
                opaque: cython.uchar[:], geometry, tilegrid, bitmap) -> bool:
    # pylint: disable=too-many-arguments, too-many-locals, protected-access
    table = array("H", colors)
    start, x_stride, y_stride, x_shift, y_shift = geometry[:5]
    start_x, end_x, start_y, end_y = geometry[5:]
    scale = tilegrid._absolute_transform.scale
    tiles = tilegrid._tiles
    tile_width = tilegrid._tile_width
    tile_height = tilegrid._tile_height
    top_left_x = tilegrid._top_left_x
    top_left_y = tilegrid._top_left_y
    width_in_tiles = tilegrid._width_in_tiles
    height_in_tiles = tilegrid._height_in_tiles
    bitmap_width_in_tiles = tilegrid._bitmap_width_in_tiles
    words = bitmap._data
    data_bytes = memoryview(bitmap._data).cast("B")
    words_per_row = bitmap._stride
    bytes_per_row = words_per_row * bitmap._data.itemsize
    width = bitmap._bmp_width
    height = bitmap._bmp_height
    bits = bitmap._bits_per_value
    values_shift = bitmap._x_shift
    values_mask = bitmap._x_mask
    bitmask = bitmap._bitmask

    full_coverage = True
    for y in range(start_y, end_y):
        row_start = start + (y - start_y + y_shift) * y_stride
        local_y = y // scale
        for x in range(start_x, end_x):
            offset = row_start + (x - start_x + x_shift) * x_stride
            if mask[offset >> 5] & (1 << (offset & 31)):
                continue
            local_x = x // scale
            tile = tiles[
                ((local_y // tile_height + top_left_y) % height_in_tiles)
                * width_in_tiles
                + (local_x // tile_width + top_left_x) % width_in_tiles
            ]
            tile_x = (tile % bitmap_width_in_tiles) * tile_width + local_x % tile_width
            tile_y = (
                tile // bitmap_width_in_tiles
            ) * tile_height + local_y % tile_height
            pixel = 0
            if tile_x < width and tile_y < height:
                if bits == 8:
                    pixel = data_bytes[tile_y * bytes_per_row + tile_x]
                else:
                    pixel = (
                        words[tile_y * words_per_row + (tile_x >> values_shift)]
                        >> (32 - ((tile_x & values_mask) + 1) * bits)
                    ) & bitmask
            if opaque[pixel]:
                mask[offset >> 5] |= 1 << (offset & 31)
                buffer[offset] = table[pixel]
            else:
                full_coverage = False
    return full_coverage
