"""Philips ROM001 device."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic

from zhaquirks.const import COMMAND_HOLD, COMMAND_ON, LONG_PRESS, LONG_RELEASE, TURN_ON
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    Button,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
    PressType,
)

DEVICE_SPECIFIC_UNKNOWN = 64512


class PhilipsRom001RemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for ROM001."""

    BUTTONS = {
        1: Button(COMMAND_ON, TURN_ON, COMMAND_ON),
    }

    PRESS_TYPES: dict[int, PressType] = {
        # We omit "short_press" and "short_release" on purpose, so it
        # won't interfere with simulated multi-press events. We emit
        # them in the multi-press code later on.
        # 0: SHORT_PRESS,
        1: PressType(LONG_PRESS, COMMAND_HOLD),
        # 2: SHORT_RELEASE,
        3: PressType(LONG_RELEASE, "long_release", "hold_release"),
    }


(
    QuirkBuilder(PHILIPS, "ROM001")
    .applies_to(SIGNIFY, "ROM001")
    .applies_to(SIGNIFY, "RDM003")
    .replaces(PhilipsBasicCluster, Basic.cluster_id, endpoint_id=1)
    .replaces(PhilipsRom001RemoteCluster, DEVICE_SPECIFIC_UNKNOWN, endpoint_id=1)
    .device_automation_triggers(
        PhilipsRom001RemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
