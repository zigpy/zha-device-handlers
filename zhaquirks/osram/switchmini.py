"""Osram Smart+ Switch Mini device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from . import OSRAM
from ..const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP_ON_OFF,
    COMMAND_STOP,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

OSRAM_CLUSTER = 0xFD00


class OsramSwitchMini(CustomDevice):
    """Osram Smart+ Switch Mini device."""

    signature = {
        MODELS_INFO: [(OSRAM, "Lightify Switch Mini")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 1, 20, 4096, 64758]
            # output_clusters=[3, 4, 5, 6, 8, 25, 768, 4096]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    OSRAM_CLUSTER,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OSRAM_CLUSTER],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=2064
            # device_version=1
            # input_clusters=[0, 4096, 64768]
            # output_clusters=[3, 4, 5, 6, 8, 768, 4096]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id, LightLink.cluster_id, OSRAM_CLUSTER],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {**signature}
    replacement.pop(MODELS_INFO)

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_STEP_ON_OFF, ENDPOINT_ID: 1},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
            ENDPOINT_ID: 3,
        },
        (LONG_PRESS, BUTTON_2): {COMMAND: "move_to_saturation", ENDPOINT_ID: 3},
        (LONG_RELEASE, BUTTON_2): {COMMAND: "move_hue", ENDPOINT_ID: 3},
        (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 2},
        (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 2},
        (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_STOP, ENDPOINT_ID: 2},
    }
