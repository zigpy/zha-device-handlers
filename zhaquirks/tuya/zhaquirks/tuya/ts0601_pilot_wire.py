"""Compatibility shim for misplaced Tuya TS0601 pilot wire quirk module.

This file resides under a duplicated ``zhaquirks/tuya/zhaquirks/tuya`` path.
The canonical implementation lives in ``zhaquirks/tuya/ts0601_pilot_wire.py``.

It is kept only to preserve compatibility for any imports that might
accidentally reference the nested module path. All symbols are re-exported
from the canonical module.
"""

from zhaquirks.tuya.ts0601_pilot_wire import *  # noqa: F401,F403
