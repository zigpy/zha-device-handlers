"""Philips ROM001 device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from ..const import (
    COMMAND,
    COMMAND_OFF_WITH_EFFECT,
    COMMAND_ON,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

DEVICE_SPECIFIC_UNKNOWN = 64512


class PhilipsROM001(CustomDevice):
    """Philips ROM001 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2096
        #  device_version=1
        #  input_clusters=[0, 1, 3, 64512, 4096]
        #  output_clusters=[25, 0, 3, 4, 6, 8, 5, 4096]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.NON_COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF_WITH_EFFECT},
    }
