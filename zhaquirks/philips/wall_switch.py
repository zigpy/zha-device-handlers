"""Signify wall switch devices (RDM001 and RDM004)."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    RIGHT,
    SHORT_PRESS,
    SHORT_RELEASE,
    TURN_ON,
)
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    Button,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
    PressType,
)


class SwitchMode(t.enum8):
    """Wall switch modes. See https://zigbee.blakadder.com/Philips_RDM001.html."""

    SingleRocker = 0x00
    SinglePush = 0x01
    DoubleRocker = 0x02
    DoublePush = 0x03


class PhilipsWallSwitchBasicCluster(PhilipsBasicCluster):
    """Philips wall switch Basic cluster."""

    class AttributeDefs(PhilipsBasicCluster.AttributeDefs):
        """Attribute definitions."""

        mode: Final = ZCLAttributeDef(
            id=0x0034,
            type=SwitchMode,
            is_manufacturer_specific=True,
        )

    attr_config = {
        **PhilipsBasicCluster.attr_config,
        AttributeDefs.mode.id: SwitchMode.DoublePush,
    }


class PhilipsWallSwitchRemoteCluster(PhilipsRemoteCluster):
    """Philips wall switch remote cluster."""

    BUTTONS = {
        1: Button(LEFT, TURN_ON),
        2: Button(RIGHT),
    }

    PRESS_TYPES: dict[int, PressType] = {
        1: PressType(LONG_PRESS, "hold"),
        3: PressType(LONG_RELEASE, "long_release", "hold_release"),
    }

    SIMULATE_SHORT_EVENTS = [
        PressType(SHORT_PRESS, "press"),
        PressType(SHORT_RELEASE, "short_release"),
    ]


# Philips RDM001 or RDM004 device using old firmware.
#  <SimpleDescriptor endpoint=1 profile=260 device_type=2080
#  device_version=1
#  input_clusters=[0, 1, 3, 64512]
#  output_clusters=[3, 4, 6, 8, 25]>
(
    QuirkBuilder(PHILIPS, "RDM001")
    .applies_to(SIGNIFY, "RDM001")
    .applies_to(PHILIPS, "RDM004")  # likely not needed
    .applies_to(SIGNIFY, "RDM004")
    # TODO: use real firmware version filters
    .filter(
        lambda device: device.endpoints[1].device_type
        == zha.DeviceType.NON_COLOR_CONTROLLER
    )
    .replaces(PhilipsWallSwitchBasicCluster, endpoint_id=1)
    .replaces(PhilipsWallSwitchRemoteCluster, endpoint_id=1)
    .device_automation_triggers(
        PhilipsWallSwitchRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)


# Philips RDM001 or RDM004 device using new firmware.
(
    QuirkBuilder(PHILIPS, "RDM001")
    .applies_to(SIGNIFY, "RDM001")
    .applies_to(PHILIPS, "RDM004")  # likely not needed
    .applies_to(SIGNIFY, "RDM004")
    # TODO: use real firmware version filters
    .filter(
        lambda device: device.endpoints[1].device_type
        == zha.DeviceType.NON_COLOR_SCENE_CONTROLLER
    )
    .replaces(PhilipsWallSwitchBasicCluster, endpoint_id=1)
    .replaces(PhilipsWallSwitchRemoteCluster, endpoint_id=1)
    .device_automation_triggers(
        PhilipsWallSwitchRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
