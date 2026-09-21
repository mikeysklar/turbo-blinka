# Numba twin of _fill_pixels in displayio/_tilegrid.py (Adafruit_Blinka_Displayio
# draft #179). Same name and arguments as cy/fill_pixels.py, so the same try-import
# hook picks it up. Numba cannot compile attribute reads, so this wrapper unpacks
# the tilegrid and bitmap in plain Python and hands flat buffers and ints to
# ../fill_kernel.py, compiled with numba.njit(cache=True). No build step.
#   PYTHONPATH=pr4:fastpath/nb python3 pitft_demo.py
import os
import sys
import time
import types
from array import array

_t0 = time.perf_counter()
import numba  # pylint: disable=wrong-import-position

print("# import numba %s: %.2f s" % (numba.__version__, time.perf_counter() - _t0))

if "turbo" not in sys.modules:
    class _Turbo:  # pylint: disable=too-few-public-methods
        viper = staticmethod(numba.njit(cache=True))

    _mod = types.ModuleType("turbo")
    _mod.turbo = _Turbo()
    sys.modules["turbo"] = _mod

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fill_kernel import fill_kernel  # pylint: disable=wrong-import-position

_first = True


def fill_pixels(buffer, mask, colors, opaque, geometry, tilegrid, bitmap) -> bool:
    # pylint: disable=too-many-arguments, protected-access, global-statement
    global _first
    start, x_stride, y_stride, x_shift, y_shift, start_x, end_x, start_y, end_y = geometry
    src = bitmap._data
    t0 = time.perf_counter()
    full = fill_kernel(
        buffer, mask, src, tilegrid._tiles, array("H", colors), opaque,
        start, x_stride, y_stride, x_shift, y_shift,
        start_x, end_x, start_y, end_y, tilegrid._absolute_transform.scale,
        tilegrid._tile_width, tilegrid._tile_height,
        tilegrid._top_left_x, tilegrid._top_left_y,
        tilegrid._width_in_tiles, tilegrid._height_in_tiles,
        tilegrid._bitmap_width_in_tiles,
        bitmap._bmp_width, bitmap._bmp_height, bitmap._stride, src.itemsize,
        bitmap._bits_per_value, bitmap._x_shift, bitmap._x_mask, bitmap._bitmask)
    if _first:
        _first = False
        print("# numba first call, compile or cache load included: %.2f s"
              % (time.perf_counter() - t0))
    return bool(full)
