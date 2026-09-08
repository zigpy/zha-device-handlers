"""Compatibility shim for misplaced Tuya TS0601 pilot wire quirk module.

This file resides under a duplicated ``zhaquirks/tuya/zhaquirks/tuya`` path.
The canonical implementation should live in ``zhaquirks/tuya/ts0601_pilot_wire.py``.

It is kept only to preserve compatibility for any imports that might
accidentally reference the nested module path. This stub intentionally
does not import the canonical module to avoid ImportError when that file
is not present.
"""

# No-op stub: importing this module has no side effects.
pass
