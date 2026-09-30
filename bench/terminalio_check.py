"""A label and a bitmap_label on the built-in font, which has no load_glyphs."""
import displayio
import terminalio
from adafruit_display_text import bitmap_label, label

displayio._stop_background()  # pylint: disable=protected-access
print("terminalio.FONT has load_glyphs:", hasattr(terminalio.FONT, "load_glyphs"))
for cls in (label.Label, bitmap_label.Label):
    lbl = cls(terminalio.FONT, text="Hello, built-in font!")
    lbl.text = "changed"
    print(cls.__module__, "ok, bounding box", lbl.bounding_box)
