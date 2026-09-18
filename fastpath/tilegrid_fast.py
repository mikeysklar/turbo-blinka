# Fast path for displayio.TileGrid._fill_area, as a monkeypatch so it can be
# measured against the pip-installed Adafruit_Blinka_Displayio without forking
# it. install(kernel) swaps the method; anything outside the common case falls
# through to the original. The per-call setup below is copied from
# displayio/_tilegrid.py 2.3.2 (the part before the pixel loop).
from array import array

from displayio import Bitmap, Palette, TileGrid
from displayio._area import Area
from displayio._structs import InputPixelStruct, OutputPixelStruct

_original = TileGrid._fill_area
_kernel = None
stats = {"fast": 0, "fallback": 0}


def _palette_lut(palette, colorspace, count):
    # ask the Palette itself, once per index instead of once per pixel, so the
    # colours are exactly what the slow path would have produced
    lut = array("H", [0] * count)
    opaque = bytearray(count)
    inp, out = InputPixelStruct(), OutputPixelStruct()
    for i in range(min(count, len(palette))):
        inp.pixel, out.pixel, out.opaque = i, 0, True
        palette._get_color(colorspace, inp, out)
        if out.opaque:
            lut[i], opaque[i] = out.pixel & 0xFFFF, 1
    return lut, opaque


def _fill_area(self, colorspace, area, mask, buffer):
    # pylint: disable=protected-access,too-many-locals
    bitmap, shader = self._bitmap, self._pixel_shader
    if not (colorspace.depth == 16 and type(bitmap) is Bitmap and type(shader) is Palette
            and not shader._dither and bitmap._bits_per_value <= 8 and self._tiles):
        stats["fallback"] += 1
        return _original(self, colorspace, area, mask, buffer)
    stats["fast"] += 1

    if self._hidden_tilegrid or self._hidden_by_parent:
        return False
    overlap = Area()
    if not area.compute_overlap(self._current_area, overlap):
        return False
    if bitmap.width <= 0 or bitmap.height <= 0:
        return False

    tr = self._absolute_transform
    x_stride, y_stride = 1, area.width()
    flip_x, flip_y = self._flip_x, self._flip_y
    if self._transpose_xy != tr.transpose_xy:
        flip_x, flip_y = flip_y, flip_x
    start = 0
    if (tr.dx < 0) != flip_x:
        start += (area.x2 - area.x1 - 1) * x_stride
        x_stride *= -1
    if (tr.dy < 0) != flip_y:
        start += (area.y2 - area.y1 - 1) * y_stride
        y_stride *= -1
    full_coverage = area == overlap

    transformed = Area()
    area.transform_within(flip_x != (tr.dx < 0), flip_y != (tr.dy < 0),
                          self.transpose_xy != tr.transpose_xy,
                          overlap, self._current_area, transformed)
    start_x = transformed.x1 - self._current_area.x1
    end_x = transformed.x2 - self._current_area.x1
    start_y = transformed.y1 - self._current_area.y1
    end_y = transformed.y2 - self._current_area.y1
    if (tr.dx < 0) != flip_x:
        x_shift = area.x2 - overlap.x2
    else:
        x_shift = overlap.x1 - area.x1
    if (tr.dy < 0) != flip_y:
        y_shift = area.y2 - overlap.y2
    else:
        y_shift = overlap.y1 - area.y1
    if self._transpose_xy != tr.transpose_xy:
        x_stride, y_stride = y_stride, x_stride
        x_shift, y_shift = y_shift, x_shift

    lut, opaque = _palette_lut(shader, colorspace, 1 << bitmap._bits_per_value)
    src = bitmap._data
    full = _kernel(buffer.cast("B").cast("H"), mask, src, self._tiles, lut, opaque,
                   start, x_stride, y_stride, x_shift, y_shift,
                   start_x, end_x, start_y, end_y, tr.scale,
                   self._tile_width, self._tile_height, self._top_left_x, self._top_left_y,
                   self._width_in_tiles, self._height_in_tiles, self._bitmap_width_in_tiles,
                   bitmap._bmp_width, bitmap._bmp_height, bitmap._stride, src.itemsize,
                   bitmap._bits_per_value, bitmap._x_shift, bitmap._x_mask, bitmap._bitmask)
    return full_coverage and bool(full)


def install(kernel):
    global _kernel  # pylint: disable=global-statement
    _kernel = kernel
    TileGrid._fill_area = _fill_area


def uninstall():
    TileGrid._fill_area = _original
