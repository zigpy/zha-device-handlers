"""Frient Electricity Meter Interface Norwegian HAN."""

from __future__ import annotations

from zigpy.quirks.v2 import QuirkBuilder

# This quirk had a workaround for blocking attribute reports with the ZCL divisor
# attribute ID and manufacturer-specific bit set. The underlying issue of incorrectly
# parsing manufacturer-specific attribute reports for ZCL attributes was resolved
# with zigpy 0.91.0.
# There's still a test for this device which tests that the divisor is not incorrectly
# updated. The quirk will also be expanded to use support manufacturer-specific
# attributes for this device, so it's kept, even though there's no functionality now.

(
    QuirkBuilder("frient A/S", "EMIZB-132")
    .add_to_registry()
)  # fmt: skip
