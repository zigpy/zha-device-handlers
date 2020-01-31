"""Xiaomi aqara opple remote devices."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zdo.types import NodeDescriptor

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import (
    ARGS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_COLOR_TEMP,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

BOTH_BUTTONS = "both_buttons"
BOTH_DOUBLE = "both_double"
BOTH_HOLD = "both_long press"
BOTH_SINGLE = "both_single"
ENDPOINT_MAP = {1: "left", 2: "right", 3: "both"}
LEFT_DOUBLE = "left_double"
LEFT_HOLD = "left_long press"
LEFT_SINGLE = "left_single"
PRESS_TYPES = {0: "long press", 1: "single", 2: "double"}
RIGHT_DOUBLE = "right_double"
RIGHT_HOLD = "right_long press"
RIGHT_SINGLE = "right_single"
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_CLUSTER_ID = 0xFFFF
XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03

_LOGGER = logging.getLogger(__name__)


class RemoteB286OPCN01(XiaomiCustomDevice):
    """Aqara Opple 2 button remote device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=261
        # device_version=1
        # input_clusters=[0, 3, 1]
        # output_clusters=[3, 6, 8, 768]>
        MODELS_INFO: [(LUMI, "lumi.remote.b286opcn01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=259
            # device_version=1
            # input_clusters=[3]
            # output_clusters=[6, 3]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [1, 85, 7],
        },
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [1, 69, 7, 0, 0],
        },
        (DOUBLE_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [0, 85, 7],
        },
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [3, 69, 7, 0, 0],
        },
    }


class RemoteB486OPCN01(XiaomiCustomDevice):
    """Aqara Opple 4 button remote device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=261
        # device_version=1
        # input_clusters=[0, 3, 1]
        # output_clusters=[3, 6, 8, 768]>
        MODELS_INFO: [(LUMI, "lumi.remote.b486opcn01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=259
            # device_version=1
            # input_clusters=[3]
            # output_clusters=[6, 3]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [1, 85, 7],
        },
        (DOUBLE_PRESS, BUTTON_3): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [1, 69, 7, 0, 0],
        },
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [0, 85, 7],
        },
        (DOUBLE_PRESS, BUTTON_4): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [3, 69, 7, 0, 0],
        },
    }


class RemoteB686OPCN01(XiaomiCustomDevice):
    """Aqara Opple 6 button remote device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=261
        # device_version=1
        # input_clusters=[0, 3, 1]
        # output_clusters=[3, 6, 8, 768]>
        MODELS_INFO: [(LUMI, "lumi.remote.b686opcn01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=259
            # device_version=1
            # input_clusters=[3]
            # output_clusters=[6, 3]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {},
            4: {},
            5: {},
            6: {},
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_3): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [1, 85, 7],
        },
        (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 1, ARGS: [1, 15]},
        (SHORT_PRESS, BUTTON_4): {
            COMMAND: COMMAND_STEP,
            ENDPOINT_ID: 1,
            ARGS: [0, 85, 7],
        },
        (LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_MOVE, ENDPOINT_ID: 1, ARGS: [0, 15]},
        (SHORT_PRESS, BUTTON_5): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [1, 69, 7, 0, 0],
        },
        (LONG_PRESS, BUTTON_5): {
            COMMAND: COMMAND_MOVE_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [1, 15, 0, 0],
        },
        (SHORT_PRESS, BUTTON_6): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [3, 69, 7, 0, 0],
        },
        (LONG_PRESS, BUTTON_6): {
            COMMAND: COMMAND_MOVE_COLOR_TEMP,
            ENDPOINT_ID: 1,
            ARGS: [3, 15, 0, 0],
        },
    }
