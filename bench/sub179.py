"""#179 subclass check: every scene plus a Bitmap and a Palette subclass, digest per scene."""
import displayio
import displayio_scenes as sc

class ShiftBitmap(displayio.Bitmap):
    def _get_pixel(self, x, y):
        return super()._get_pixel((x + 1) % self.width, y)

class StripePalette(displayio.Palette):
    def _get_color(self, colorspace, input_pixel, output_pixel):
        super()._get_color(colorspace, input_pixel, output_pixel)
        if input_pixel.tile_x % 2:
            output_pixel.pixel ^= 0xFFFF

def s_sub_bitmap(group):
    bm = ShiftBitmap(40, 30, 4)
    sc.pattern(bm, 4)
    group.append(displayio.TileGrid(bm, pixel_shader=sc.palette_of(4), x=10, y=8))
    def change():
        bm[3, 3] = 2
    return change

def s_sub_palette(group):
    bm = displayio.Bitmap(40, 30, 4)
    sc.pattern(bm, 4)
    pal = StripePalette(4)
    for i, c in enumerate((0xE0103A, 0x1565D8, 0x12A150, 0xF2B400)):
        pal[i] = c
    group.append(displayio.TileGrid(bm, pixel_shader=pal, x=10, y=8))
    def change():
        bm[3, 3] = 2
    return change

displayio._stop_background()
scenes = list(sc.SCENES) + [("subclass Bitmap", s_sub_bitmap, {}), ("subclass Palette", s_sub_palette, {})]
for name, build, kw in scenes:
    print(name, sc.run_scene(build, kw)[0])
