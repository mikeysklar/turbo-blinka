#!/usr/bin/env python3
"""Correctness scenes for an OnDiskBitmap fast path in TileGrid._fill_area.

    PYTHONPATH=main240 python3 ondisk_scenes.py > stock.txt
    PYTHONPATH=odb4b python3 ondisk_scenes.py > new.txt
    diff stock.txt new.txt

Every scene draws a TileGrid of an OnDiskBitmap on a headless display and prints
the sha256 of the bytes sent. Covers 1, 4 and 8 bit indexed BMPs, both output
byte orders, the geometry the loop computes itself (flips, transpose, scale,
sprite sheet tiles, placement off each edge, an odd width), a transparent
palette index, a truncated file, and the cases that must fall through to the old
loop: a dithered palette and an OnDiskBitmap subclass. Run it against stock and
against the change; every line must be identical.
"""
import os
import struct
import sys
import tempfile

import busdisplay
import displayio

from displayio_refresh import NullBus

W, H = 48, 32


class MyOnDiskBitmap(displayio.OnDiskBitmap):
    """A subclass, which may override _get_pixel, so it takes the old loop."""


def write_bmp(path, w, h, bpp, truncate=0, masks=None):
    """An uncompressed BMP, bottom-up rows padded to 4 bytes. Indexed for 8 bits
    and under, where the values pack into a byte most significant bits first.
    With masks, a BITMAPV4HEADER carrying them, which is how a 16 bit file says
    5:6:5 instead of the 5:5:5 a short header means."""
    indexed = bpp <= 8
    colors = 1 << bpp if indexed else 0
    header_size = 108 if masks else 40
    offset = 14 + header_size + colors * 4
    if indexed:
        bit_stride = w * bpp
        if bit_stride % 32:
            bit_stride += 32 - bit_stride % 32
        stride = bit_stride // 8
    else:
        stride = (w * bpp // 8 + 3) & ~3
    values = colors if indexed else 256
    rows = []
    for y in range(h - 1, -1, -1):
        row = bytearray(stride)
        for x in range(w):
            v = (x * 7 + y * 13 + (x * y) // 5) % values
            if indexed:
                per_byte = 8 // bpp
                shift = (8 - bpp) - (x % per_byte) * bpp
                row[x // per_byte] |= v << shift
            elif bpp == 16 and masks == (0xF800, 0x07E0, 0x001F):
                struct.pack_into("<H", row, x * 2,
                                 ((v >> 3) << 11) | (((255 - v) >> 2) << 5) | (x & 31))
            elif bpp == 16:  # 5:5:5
                struct.pack_into("<H", row, x * 2,
                                 ((v >> 3) << 10) | (((255 - v) >> 3) << 5) | (x & 31))
            elif bpp == 32:
                row[x * 4:x * 4 + 4] = bytes((x & 0xFF, 255 - v, v, 0xFF))
            else:
                row[x * 3:x * 3 + 3] = bytes((x & 0xFF, 255 - v, v))
        rows.append(bytes(row))
    data = b"".join(rows)
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", offset + len(data), 0, 0, offset))
        f.write(struct.pack("<IiiHHIIiiII", header_size, w, h, 1, bpp,
                            3 if masks else 0, len(data), 2835, 2835, colors, 0))
        if masks:
            f.write(struct.pack("<IIII", masks[0], masks[1], masks[2], 0))
            f.write(struct.pack("<I", 0) + bytes(36) + struct.pack("<III", 0, 0, 0))
        for i in range(colors):
            f.write(bytes(((i * 5) & 0xFF, (255 - i * 11) & 0xFF, (i * 37) & 0xFF, 0)))
        f.write(data[:len(data) - truncate] if truncate else data)


def scene(name, path, reverse=True, cls=None, dither=False, transparent=None,
          grid_kwargs=None, scale=1, flip_x=False, flip_y=False, transpose=False):
    # pylint: disable=too-many-arguments
    displayio.release_displays()
    bus = NullBus()
    try:
        display = busdisplay.BusDisplay(bus, b"", width=W, height=H, auto_refresh=False,
                                        reverse_bytes_in_word=reverse)
        odb = (cls or displayio.OnDiskBitmap)(path)
        shader = odb.pixel_shader
        shader.dither = dither
        if transparent is not None:
            shader.make_transparent(transparent)
        grid = displayio.TileGrid(odb, pixel_shader=shader, **(grid_kwargs or {}))
        grid.flip_x, grid.flip_y, grid.transpose_xy = flip_x, flip_y, transpose
        group = displayio.Group(scale=scale)
        group.append(grid)
        display.root_group = group
        display.refresh()
        grid.x += 1
        display.refresh()
    except Exception as e:  # pylint: disable=broad-except
        print("| %s | %s: %s |" % (name, type(e).__name__, e))
        return
    print("| %s | %s | %d bytes |" % (name, bus.digest.hexdigest()[:12], bus.sent))


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# OnDiskBitmap scenes, %dx%d, displayio from %s" % (W, H, displayio.__file__))
    tmp = tempfile.mkdtemp()
    bmp = {}
    for bpp in (1, 4, 8, 16, 24, 32):
        bmp[bpp] = os.path.join(tmp, "img%d.bmp" % bpp)
        write_bmp(bmp[bpp], W, H, bpp)
    rgb565 = os.path.join(tmp, "img565.bmp")
    write_bmp(rgb565, W, H, 16, masks=(0xF800, 0x07E0, 0x001F))
    odd24 = os.path.join(tmp, "odd24.bmp")
    write_bmp(odd24, 37, 23, 24)
    cut24 = os.path.join(tmp, "cut24.bmp")
    write_bmp(cut24, W, H, 24, truncate=W * 9)
    odd = os.path.join(tmp, "odd.bmp")
    write_bmp(odd, 37, 23, 8)
    odd4 = os.path.join(tmp, "odd4.bmp")
    write_bmp(odd4, 37, 23, 4)
    cut = os.path.join(tmp, "cut.bmp")
    write_bmp(cut, W, H, 8, truncate=W * 3)
    sheet = os.path.join(tmp, "sheet.bmp")
    write_bmp(sheet, 32, 32, 8)

    for bpp in (1, 4, 8, 16, 24, 32):
        for reverse in (True, False):
            scene("%d bpp, reverse=%s" % (bpp, reverse), bmp[bpp], reverse=reverse)
    for reverse in (True, False):
        scene("16 bpp 5:6:5 masks, reverse=%s" % reverse, rgb565, reverse=reverse)
    scene("24 bpp, odd 37x23", odd24)
    scene("24 bpp, truncated file", cut24)
    scene("16 bpp, dithered converter", bmp[16], dither=True)
    scene("24 bpp, dithered converter", bmp[24], dither=True)
    scene("16 bpp, subclass", bmp[16], cls=MyOnDiskBitmap)
    scene("24 bpp, subclass", bmp[24], cls=MyOnDiskBitmap)
    scene("16 bpp, transparent black", bmp[16], transparent=0x000000)
    scene("24 bpp, transparent black", bmp[24], transparent=0x000000)
    scene("24 bpp, transparent 0x00FF7F", bmp[24], transparent=0x00FF7F)
    scene("8 bpp, odd 37x23", odd)
    scene("4 bpp, odd 37x23", odd4)
    scene("8 bpp, truncated file", cut)
    scene("8 bpp, dithered palette", bmp[8], dither=True)
    scene("8 bpp, subclass", bmp[8], cls=MyOnDiskBitmap)
    scene("1 bpp, subclass", bmp[1], cls=MyOnDiskBitmap)
    for index in (0, 7, 255):
        scene("8 bpp, transparent %d" % index, bmp[8], transparent=index)
    scene("1 bpp, transparent 0", bmp[1], transparent=0)
    scene("4 bpp, transparent 3", bmp[4], transparent=3)

    for name, kwargs in (
        ("scale 2", dict(scale=2)),
        ("scale 3", dict(scale=3)),
        ("flip_x", dict(flip_x=True)),
        ("flip_y", dict(flip_y=True)),
        ("flip both", dict(flip_x=True, flip_y=True)),
        ("transposed", dict(transpose=True)),
        ("transposed and flipped", dict(transpose=True, flip_x=True)),
        ("placed off the left edge", dict(grid_kwargs=dict(x=-9, y=-5))),
        ("placed off the right edge", dict(grid_kwargs=dict(x=W - 7, y=H - 3))),
    ):
        for bpp in (1, 4, 8, 16, 24):
            scene("%d bpp, %s" % (bpp, name), bmp[bpp], **kwargs)
    for bpp in (1, 4, 8, 16, 24):
        sheet_bmp = sheet if bpp == 8 else bmp[bpp]
        scene("%d bpp, sprite sheet 4x2 tiles" % bpp, sheet_bmp,
              grid_kwargs=dict(tile_width=16, tile_height=16, width=4, height=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
