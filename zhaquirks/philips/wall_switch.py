"""Signify wall switch devices (RDM001 and RDM004)."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
from zigpy.zcl.foundation import ZCLAttributeDef

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
from zhaquirks.philips import (
    PHILIPS,
    SIGNIFY,
    Button,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
    PressType,
)

DEVICE_SPECIFIC_UNKNOWN = 64512


class PhilipsWallSwitchBasicCluster(PhilipsBasicCluster):
    """Philips wall switch Basic cluster."""

    class AttributeDefs(PhilipsBasicCluster.AttributeDefs):
        """Attribute definitions."""

        mode: Final = ZCLAttributeDef(
            id=0x0034,
            type=t.enum8,
            is_manufacturer_specific=True,
        )

    attr_config = {**PhilipsBasicCluster.attr_config, AttributeDefs.mode.id: 0x02}


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
                    PhilipsWallSwitchBasicCluster,
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
