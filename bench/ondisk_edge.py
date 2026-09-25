#!/usr/bin/env python3
"""The three edge cases raised in review on PR #187, as a standing check.

    PYTHONPATH=main244 python3 ondisk_edge.py > stock.txt
    PYTHONPATH=odb4b   python3 ondisk_edge.py > new.txt
    diff stock.txt new.txt

Reading a whole row instead of a pixel at a time is faster, but it has three ways
to go wrong, and each one is checked here against what the per-pixel loop does:

1. A stream may return fewer bytes than asked for without being at the end. Only
   reads after the header are capped, since a stream that caps the header cannot
   be opened by either version.
2. A clipped draw of a very wide picture must not read the whole row. The file
   bytes read are counted, so the fast path can be held to what the old loop used.
3. A malformed file whose index is past the end of its palette raised IndexError
   before, so it still has to.
"""
import io
import struct
import sys

import busdisplay
import displayio

from displayio_refresh import NullBus, host


class ShortBytesIO(io.BytesIO):
    """Full reads until `capped` is set, then never more than 8 bytes at a time."""

    CAP = 8
    capped = False

    def read(self, size=-1):
        if size is None or size < 0:
            return super().read()
        if not self.capped:
            return super().read(size)
        return super().read(min(size, self.CAP))

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


class CountingFile(io.BufferedReader):
    """Counts the bytes read, so the two paths can be compared for file traffic."""

    def __init__(self, path):
        super().__init__(open(path, "rb"))  # pylint: disable=consider-using-with
        self.bytes_read = 0

    def read(self, size=-1):
        data = super().read(size)
        self.bytes_read += len(data)
        return data


def write_bmp(path, width, height, bpp, colors, pixel):
    """Uncompressed BMP, bottom-up rows padded to 4 bytes."""
    offset = 14 + 40 + colors * 4
    stride = (width * bpp // 8 + 3) & ~3
    rows = []
    for y in range(height - 1, -1, -1):
        row = bytearray(stride)
        for x in range(width):
            value = pixel(x, y)
            if bpp == 8:
                row[x] = value
            else:
                row[x * 3 : x * 3 + 3] = bytes(
                    (value & 0xFF, (255 - value) & 0xFF, (value // 2) & 0xFF)
                )
        rows.append(bytes(row))
    data = b"".join(rows)
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", offset + len(data), 0, 0, offset))
        f.write(
            struct.pack(
                "<IiiHHIIiiII", 40, width, height, 1, bpp, 0, len(data),
                2835, 2835, colors, 0,
            )
        )
        for i in range(colors):
            f.write(bytes(((i * 5) & 0xFF, (255 - i * 11) & 0xFF, (i * 37) & 0xFF, 0)))
        f.write(data)


def draw(source, width, height, shift=0):
    """Show a bitmap on a headless display and return the hash of the bytes sent."""
    displayio.release_displays()
    bus = NullBus()
    display = busdisplay.BusDisplay(
        bus, b"", width=width, height=height, auto_refresh=False
    )
    bitmap = source if isinstance(source, displayio.OnDiskBitmap) else (
        displayio.OnDiskBitmap(source)
    )
    group = displayio.Group()
    group.append(
        displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader, x=-shift)
    )
    display.root_group = group
    display.refresh()
    return bus.digest.hexdigest()[:12]


def check_short_reads():
    """A stream that returns fewer bytes than asked for still has to draw the same."""
    for bpp, colors in ((8, 256), (24, 0)):
        path = "/tmp/edge-short-%d.bmp" % bpp
        write_bmp(path, 40, 12, bpp, colors, lambda x, y: (x * 7 + y * 3) & 0xFF)
        want = draw(path, 40, 12)
        with open(path, "rb") as f:
            blob = f.read()
        try:
            stream = ShortBytesIO(blob)
            bitmap = displayio.OnDiskBitmap(stream)
            stream.capped = True  # header parsed, now short read the pixel rows
            got = draw(bitmap, 40, 12)
        except Exception as e:  # pylint: disable=broad-except
            got = "%s: %s" % (type(e).__name__, e)
        print("| short reads, %d bit | %s | %s |"
              % (bpp, got, "same as a regular file" if got == want else "DIFFERENT"))


def check_wide_row():
    """One pixel of a very wide picture must not pull in the whole row."""
    for bpp, colors in ((8, 256), (24, 0)):
        path = "/tmp/edge-wide-%d.bmp" % bpp
        write_bmp(path, 4000, 4, bpp, colors, lambda x, y: x & 0xFF)
        counter = CountingFile(path)
        draw(counter, 1, 4, shift=2000)
        print("| 1 px of a 4000 px row, %d bit | %d file bytes read |"
              % (bpp, counter.bytes_read))


def check_index_past_palette():
    """A malformed file whose index is past its palette raised before, so it still has to."""
    path = "/tmp/edge-oob.bmp"
    write_bmp(path, 16, 8, 8, 4, lambda x, y: 4)  # 4 colours, every index is 4
    try:
        got = draw(path, 16, 8)
    except Exception as e:  # pylint: disable=broad-except
        got = "%s" % type(e).__name__
    print("| index past the palette | %s |" % got)


def main():
    displayio._stop_background()  # pylint: disable=protected-access
    print("# ondisk edge cases, %s, displayio from %s" % (host(), displayio.__file__))
    print("| case | result | |")
    print("|---|---|---|")
    check_short_reads()
    check_wide_row()
    check_index_past_palette()
    return 0


if __name__ == "__main__":
    sys.exit(main())
