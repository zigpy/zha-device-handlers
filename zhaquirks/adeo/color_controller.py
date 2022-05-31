"""Device handler for ADEO Lexman LXEK-5 (HR-C99C-Z-C045) & ZBEK-26 (HR-C99C-Z-C045-B) color controllers."""
from typing import Any, List, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
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
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import Bus, EventableCluster
from zhaquirks.const import (
    ARGS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STEP_HUE,
    COMMAND_STEP_SATURATION,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)

COLOR_UP = "color_up"
COLOR_DOWN = "color_down"
SATURATION_UP = "saturation_up"
SATURATION_DOWN = "saturation_down"
HUE_LEFT = "hue_left"
HUE_RIGHT = "hue_right"

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFE00  # decimal = 65024
SCENE_NO_GROUP = 0x0000


class AdeoManufacturerCluster(EventableCluster):
    """Custom manufacturer cluster (used for preset buttons 1-4)."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "AdeoManufacturerCluster"
    ep_attribute = "adeo_manufacturer_cluster"
    client_commands = {
        0x00: foundation.ZCLCommandDef(
            "preset",
            {"param1": t.uint8_t, "param2": t.uint8_t},
            is_manufacturer_specific=True,
            is_reply=False,
        )
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        if hdr.command_id == 0x0000:
            self.endpoint.device.scenes_bus.listener_event(
                "listener_event", ZHA_SEND_EVENT, "view", [SCENE_NO_GROUP, args[0]]
            )
        else:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class AdeoScenesCluster(Scenes, EventableCluster):
    """Scenes cluster to map preset buttons to the "view" command."""

    cluster_id = Scenes.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.scenes_bus.add_listener(self)


class AdeoColorController(CustomDevice):
    """Custom device representing ADEO color controller."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.scenes_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=2048
        #  device_version=1
        #  input_clusters=[0, 1, 3, 2821, 4096, 64769]
        #  output_clusters=[3, 4, 6, 8, 25, 768, 4096]>
        MODELS_INFO: [("ADEO", "LXEK-5"), ("ADEO", "ZBEK-26")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,  # 260
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,  # 2048
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Diagnostic.cluster_id,  # 2821
                    LightLink.cluster_id,  # 4096
                    0xFD01,  # 64769
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Diagnostic.cluster_id,  # 2821
                    LightLink.cluster_id,  # 4096
                    0xFD01,  # 64769
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    AdeoScenesCluster,  # 5
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                    AdeoManufacturerCluster,  # 65024
                ],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: 6,  # OnOff.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: 6,  # OnOff.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,  # LevelControl.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,  # LevelControl.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, COLOR_UP): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {
                "step_mode": 3,
                "step_size": 22,
                "transition_time": 5,
                "color_temp_min_mireds": 153,
                "color_temp_max_mireds": 370,
            },
        },
        (SHORT_PRESS, COLOR_DOWN): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {
                "step_mode": 1,
                "step_size": 22,
                "transition_time": 5,
                "color_temp_min_mireds": 153,
                "color_temp_max_mireds": 370,
            },
        },
        (SHORT_PRESS, SATURATION_UP): {
            COMMAND: COMMAND_STEP_SATURATION,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, SATURATION_DOWN): {
            COMMAND: COMMAND_STEP_SATURATION,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 3},
        },
        (SHORT_PRESS, HUE_LEFT): {
            COMMAND: COMMAND_STEP_HUE,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 3},
        },
        (SHORT_PRESS, HUE_RIGHT): {
            COMMAND: COMMAND_STEP_HUE,
            CLUSTER_ID: 768,  # Color.cluster_id
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: "view",
            CLUSTER_ID: 5,  # Scenes.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [0, 0xA],
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: "view",
            CLUSTER_ID: 5,  # Scenes.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [0, 0xB],
        },
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: "view",
            CLUSTER_ID: 5,  # Scenes.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [0, 0xC],
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: "view",
            CLUSTER_ID: 5,  # Scenes.cluster_id
            ENDPOINT_ID: 1,
            ARGS: [0, 0xD],
        },
    }
