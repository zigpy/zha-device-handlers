"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from zigpy.quirks.v2 import QuirkBuilder

(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .add_to_registry()
)  # fmt: skip
