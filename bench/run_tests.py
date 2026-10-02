#!/usr/bin/env python3
"""Run every test_* function in a test file without pytest.

    PYTHONPATH=bitmapvalues3:. python3 run_tests.py test_bitmap_values.py
"""
import importlib.util
import sys
import traceback

spec = importlib.util.spec_from_file_location("t", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
failed = 0
for name in sorted(n for n in dir(mod) if n.startswith("test_")):
    try:
        getattr(mod, name)()
        print("PASS", name)
    except Exception as e:  # pylint: disable=broad-except
        failed += 1
        last = traceback.extract_tb(e.__traceback__)[-1]
        print("FAIL %s: %s: %s (line %d)" % (name, type(e).__name__, e, last.lineno))
print("%d failed" % failed)
sys.exit(1 if failed else 0)
