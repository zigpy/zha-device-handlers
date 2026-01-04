"""Tint remote."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Scenes
from zigpy.zcl.foundation import GeneralCommand

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STOP,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    VALUE,
)

TINT_SCENE_ATTR = 0x4005


class TintRemoteScenesCluster(LocalDataCluster, Scenes):
    """Tint remote cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

        self.endpoint.device.add_listener(self)

    def change_scene(self, value):
        """Change scene attribute to new value."""
        self._update_attribute(self.attributes_by_name["current_scene"].id, value)


class TintRemoteBasicCluster(CustomCluster, Basic):
    """Tint remote cluster."""

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Send write_attributes value to TintRemoteSceneCluster."""
        if hdr.command_id != GeneralCommand.Write_Attributes:
            return

        attr = args[0][0]
        if attr.attrid != TINT_SCENE_ATTR:
            return

        value = attr.value.value
        self.endpoint.device.listener_event("change_scene", value)


DAT = {
    # ON / OFF BUTTON
    (SHORT_PRESS, "BUTTON_ON"): {
        COMMAND: COMMAND_ON,
        CLUSTER_ID: 6,
        ENDPOINT_ID: 1,
        ARGS: [],
    },
    (SHORT_PRESS, "BUTTON_OFF"): {
        COMMAND: COMMAND_OFF,
        CLUSTER_ID: 6,
        ENDPOINT_ID: 1,
        ARGS: [],
    },
    # COLOR WHEEL
    # todo:  validate correct handling for dynamic color values sent by color wheel
    # WARMER
    (SHORT_PRESS, "COLOR_WHEEL"): {
        COMMAND: "move_to_color",
        CLUSTER_ID: 768,
        ENDPOINT_ID: 1,
        ARGS: [24420, 38570, 0],  # sample values
    },
    # COLOR TEMPERATURE BUTTONS
    # todo:  validate correct handling for cycling through available values
    # WARMER
    (SHORT_PRESS, "BUTTON_COLOR_TEMP_WARM"): {
        COMMAND: "move_to_color_temp",
        CLUSTER_ID: 768,
        ENDPOINT_ID: 1,
        ARGS: [370, 10],
    },
    # COLDER
    (SHORT_PRESS, "BUTTON_COLOR_TEMP_COLD"): {
        COMMAND: "move_to_color_temp",
        CLUSTER_ID: 768,
        ENDPOINT_ID: 1,
        ARGS: [153, 10],
    },
    # BRIGHTNESS UP/DOWN BUTTONS
    (SHORT_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        ARGS: [1, 43, 10],
    },
    (LONG_PRESS, DIM_DOWN): {
        COMMAND: COMMAND_MOVE,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        ARGS: [1, 100],
    },
    (SHORT_PRESS, DIM_UP): {
        COMMAND: COMMAND_STEP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        ARGS: [0, 43, 10],
    },
    (LONG_PRESS, DIM_UP): {
        COMMAND: COMMAND_MOVE,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        ARGS: [0, 100],
    },
    # todo: check for correct definition, because stop command is being sent for up and down equally
    (LONG_RELEASE): {
        COMMAND: COMMAND_STOP,
        CLUSTER_ID: 8,
        ENDPOINT_ID: 1,
        ARGS: [],
    },
    # SCENE BUTTONS
    (SHORT_PRESS, "worklight"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 3,
        },
    },
    (SHORT_PRESS, "sunset"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 1,
        },
    },
    (SHORT_PRESS, "party"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 2,
        },
    },
    (SHORT_PRESS, "nightlight"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 6,
        },
    },
    (SHORT_PRESS, "campfire"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 4,
        },
    },
    (SHORT_PRESS, "romance"): {
        COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        CLUSTER_ID: 5,
        ENDPOINT_ID: 1,
        ARGS: {
            ATTRIBUTE_ID: 1,
            ATTRIBUTE_NAME: "current_scene",
            VALUE: 5,
        },
    },
}

(
    QuirkBuilder("MLI", "ZBT-Remote-ALL-RGBW")
    .replace_cluster_occurrences(TintRemoteBasicCluster)
    .adds(TintRemoteScenesCluster, cluster_type=ClusterType.Client)
    .device_automation_triggers(DAT.copy())
    .add_to_registry()
)

(
    QuirkBuilder("MLI", "tint-Remote-white")
    .replaces(TintRemoteBasicCluster)
    .adds(TintRemoteScenesCluster, cluster_type=ClusterType.Client)
    .device_automation_triggers(DAT.copy())
    .add_to_registry()
)
