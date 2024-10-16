"""Signify wall switch devices (RDM001 and RDM004)."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
    SHORT_RELEASE,
    TURN_ON,
)
from zhaquirks.philips import PHILIPS, SIGNIFY, Button, PhilipsRemoteCluster, PressType

DEVICE_SPECIFIC_UNKNOWN = 64512


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes.update(
        {
            0x0031: ("philips", t.bitmap16, True),
            0x0034: ("mode", t.enum8, True),
        }
    )

    attr_config = {0x0031: 0x000B, 0x0034: 0x02}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=0x100B)
        return result


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


class PhilipsWallSwitch(CustomDevice):
    """Philips RDM001 or RDM004 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2080
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512]
        #  output_clusters=[3, 4, 6, 8, 25]>
        MODELS_INFO: [
            (PHILIPS, "RDM001"),
            (SIGNIFY, "RDM001"),
            (PHILIPS, "RDM004"),  # likely not needed
            (SIGNIFY, "RDM004"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PhilipsWallSwitchRemoteCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = (
        PhilipsWallSwitchRemoteCluster.generate_device_automation_triggers()
    )
