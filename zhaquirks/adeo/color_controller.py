"""Device handler for ADEO Lexman LXEK-5 (HR-C99C-Z-C045) & ZBEK-26 (HR-C99C-Z-C045-B) color controllers."""

from typing import Any, Optional, Union

from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Scenes
from zigpy.zcl.foundation import BaseCommandDefs

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
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    PARAMS,
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

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        preset = foundation.ZCLCommandDef(
            id=0x00,
            schema={"param1": t.uint8_t, "param2": t.uint8_t},
            is_manufacturer_specific=True,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
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

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.scenes_bus.add_listener(self)


class AdeoColorController(CustomDeviceV2):
    """Custom device representing ADEO color controller."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.scenes_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder("ADEO", "LXEK-5")
    .applies_to("ADEO", "ZBEK-26")
    .device_class(AdeoColorController)
    .replaces(AdeoScenesCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(AdeoManufacturerCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .device_automation_triggers(
        {
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
    )
    .add_to_registry()
)
