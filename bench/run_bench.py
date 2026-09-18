#!/usr/bin/env python3
"""Run turbo example modules under CPython/Blinka, same rules as the farm.

    python3 run_bench.py [--trials 8] [--tag before] MODULE.py [MODULE.py ...]

Each module is an unmodified turbo source file: it does `from turbo import turbo`,
decorates with @turbo / @turbo.native / @turbo.viper, and defines
`_turbo_bench()` returning a comparable value. Reports the median of N trials in
milliseconds, like the table in turbo-on-the-farm.md, plus the returned value so
runs can be checked against each other and against the boards.
"""
import argparse
import builtins
import importlib.util
import os
import platform
import statistics
import sys
import time
import types


def install_shim(backend="identity"):
    """CPython stand-in for lib/turbo.py: the decorators are identity markers.

    Viper type names must exist as builtins. MicroPython never evaluates the
    `out: ptr8` annotation, CPython before 3.14 does at def time and raises
    NameError without this.
    """
    class _Turbo:
        def __call__(self, f):
            return f
        native = viper = __call__

    if backend == "numba":
        # no build step: @turbo.viper is the JIT. Unmodified source, numba
        # ignores the ptr8 annotations and infers int64 (no 32-bit wrap).
        t0 = time.perf_counter()
        import numba
        print("# import numba %s: %.2f s" % (numba.__version__, time.perf_counter() - t0))
        _Turbo.viper = staticmethod(numba.njit(cache=False))

    mod = types.ModuleType("turbo")
    mod.turbo = _Turbo()
    mod.arch = None
    sys.modules["turbo"] = mod
    for name in ("ptr8", "ptr16", "ptr32", "ptr", "uint"):
        if not hasattr(builtins, name):
            setattr(builtins, name, object)


def load(path):
    # first dot, so pixels.cpython-313-aarch64-linux-gnu.so loads as `pixels`
    name = os.path.basename(path).split(".")[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    t0 = time.perf_counter()
    spec.loader.exec_module(mod)
    return name, mod, time.perf_counter() - t0


def host():
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip("\x00\n")
    except OSError:
        return platform.machine()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modules", nargs="+")
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--tag", default="before")
    ap.add_argument("--shim", choices=["identity", "numba"], default="identity")
    a = ap.parse_args()

    install_shim(a.shim)
    print("# %s, %s, Python %s, %s" % (a.tag, host(), platform.python_version(),
                                       time.strftime("%Y-%m-%d %H:%M")))
    print("| module | import s | first call ms | median ms | min ms | max ms | value |")
    print("|---|---|---|---|---|---|---|")
    for path in a.modules:
        name, mod, imp = load(path)
        times, value = [], None
        t0 = time.perf_counter()
        mod._turbo_bench()  # first call apart: a JIT backend compiles here
        first = (time.perf_counter() - t0) * 1e3
        for _ in range(a.trials):
            t0 = time.perf_counter()
            value = mod._turbo_bench()
            times.append((time.perf_counter() - t0) * 1e3)
        print("| %s | %.2f | %.1f | %.1f | %.1f | %.1f | %s |"
              % (os.path.dirname(path) + "/" + name, imp, first,
                 statistics.median(times), min(times), max(times), value))


if __name__ == "__main__":
    main()
