"""Xiaomi aqara opple remote devices."""
import logging

from zigpy.profiles import zha
import zigpy.types as types
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    MultistateInput,
    OnOff,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import CustomCluster

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import (
    ARGS,
    ATTR_ID,
    BUTTON,
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
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

PRESS_TYPES = {0: "long press", 1: "single", 2: "double", 3: "triple", 255: "release"}
STATUS_TYPE_ATTR = 0x0055  # decimal = 85

OPPLE_CLUSTER_ID = 0xFCC0

_LOGGER = logging.getLogger(__name__)


class OppleCluster(CustomCluster):
    """Opple cluster."""

    ep_attribute = "oppleCluster"
    cluster_id = OPPLE_CLUSTER_ID
    attributes = {0x0009: ("mode", types.uint8_t)}


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    cluster_id = MultistateInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state = PRESS_TYPES.get(value)
            event_args = {
                BUTTON: self.endpoint.endpoint_id,
                PRESS_TYPE: self._current_state,
                ATTR_ID: attrid,
                VALUE: value,
            }
            action = "{}_{}".format(self.endpoint.endpoint_id, self._current_state)
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            # show something in the sensor in HA
            super()._update_attribute(0, action)


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
                    OppleCluster,
                    MultistateInputCluster,
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
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
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
                    OppleCluster,
                    MultistateInputCluster,
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
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
        ("single", BUTTON_3): {COMMAND: "3_single"},
        ("double", BUTTON_3): {COMMAND: "3_double"},
        ("triple", BUTTON_3): {COMMAND: "3_triple"},
        ("hold", BUTTON_3): {COMMAND: "3_hold"},
        ("release", BUTTON_3): {COMMAND: "3_release"},
        ("single", BUTTON_4): {COMMAND: "4_single"},
        ("double", BUTTON_4): {COMMAND: "4_double"},
        ("triple", BUTTON_4): {COMMAND: "4_triple"},
        ("hold", BUTTON_4): {COMMAND: "4_hold"},
        ("release", BUTTON_4): {COMMAND: "4_release"},
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
                    OppleCluster,
                    MultistateInputCluster,
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
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
        ("single", BUTTON_3): {COMMAND: "3_single"},
        ("double", BUTTON_3): {COMMAND: "3_double"},
        ("triple", BUTTON_3): {COMMAND: "3_triple"},
        ("hold", BUTTON_3): {COMMAND: "3_hold"},
        ("release", BUTTON_3): {COMMAND: "3_release"},
        ("single", BUTTON_4): {COMMAND: "4_single"},
        ("double", BUTTON_4): {COMMAND: "4_double"},
        ("triple", BUTTON_4): {COMMAND: "4_triple"},
        ("hold", BUTTON_4): {COMMAND: "4_hold"},
        ("release", BUTTON_4): {COMMAND: "4_release"},
        ("single", BUTTON_5): {COMMAND: "5_single"},
        ("double", BUTTON_5): {COMMAND: "5_double"},
        ("triple", BUTTON_5): {COMMAND: "5_triple"},
        ("hold", BUTTON_5): {COMMAND: "5_hold"},
        ("release", BUTTON_5): {COMMAND: "5_release"},
        ("single", BUTTON_6): {COMMAND: "6_single"},
        ("double", BUTTON_6): {COMMAND: "6_double"},
        ("triple", BUTTON_6): {COMMAND: "6_triple"},
        ("hold", BUTTON_6): {COMMAND: "6_hold"},
        ("release", BUTTON_6): {COMMAND: "6_release"},
    }


class RemoteB286OPCN01V2(XiaomiCustomDevice):
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
                    OppleCluster,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            }
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
    }


class RemoteB486OPCN01V2(XiaomiCustomDevice):
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
            }
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
                    OppleCluster,
                    MultistateInputCluster,
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
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
        ("single", BUTTON_3): {COMMAND: "3_single"},
        ("double", BUTTON_3): {COMMAND: "3_double"},
        ("triple", BUTTON_3): {COMMAND: "3_triple"},
        ("hold", BUTTON_3): {COMMAND: "3_hold"},
        ("release", BUTTON_3): {COMMAND: "3_release"},
        ("single", BUTTON_4): {COMMAND: "4_single"},
        ("double", BUTTON_4): {COMMAND: "4_double"},
        ("triple", BUTTON_4): {COMMAND: "4_triple"},
        ("hold", BUTTON_4): {COMMAND: "4_hold"},
        ("release", BUTTON_4): {COMMAND: "4_release"},
    }


class RemoteB686OPCN01V2(XiaomiCustomDevice):
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
            }
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
                    OppleCluster,
                    MultistateInputCluster,
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
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [Identify.cluster_id, OnOff.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [],
            },
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
        ("single", BUTTON_1): {COMMAND: "1_single"},
        ("double", BUTTON_1): {COMMAND: "1_double"},
        ("triple", BUTTON_1): {COMMAND: "1_triple"},
        ("hold", BUTTON_1): {COMMAND: "1_hold"},
        ("release", BUTTON_1): {COMMAND: "1_release"},
        ("single", BUTTON_2): {COMMAND: "2_single"},
        ("double", BUTTON_2): {COMMAND: "2_double"},
        ("triple", BUTTON_2): {COMMAND: "2_triple"},
        ("hold", BUTTON_2): {COMMAND: "2_hold"},
        ("release", BUTTON_2): {COMMAND: "2_release"},
        ("single", BUTTON_3): {COMMAND: "3_single"},
        ("double", BUTTON_3): {COMMAND: "3_double"},
        ("triple", BUTTON_3): {COMMAND: "3_triple"},
        ("hold", BUTTON_3): {COMMAND: "3_hold"},
        ("release", BUTTON_3): {COMMAND: "3_release"},
        ("single", BUTTON_4): {COMMAND: "4_single"},
        ("double", BUTTON_4): {COMMAND: "4_double"},
        ("triple", BUTTON_4): {COMMAND: "4_triple"},
        ("hold", BUTTON_4): {COMMAND: "4_hold"},
        ("release", BUTTON_4): {COMMAND: "4_release"},
        ("single", BUTTON_5): {COMMAND: "5_single"},
        ("double", BUTTON_5): {COMMAND: "5_double"},
        ("triple", BUTTON_5): {COMMAND: "5_triple"},
        ("hold", BUTTON_5): {COMMAND: "5_hold"},
        ("release", BUTTON_5): {COMMAND: "5_release"},
        ("single", BUTTON_6): {COMMAND: "6_single"},
        ("double", BUTTON_6): {COMMAND: "6_double"},
        ("triple", BUTTON_6): {COMMAND: "6_triple"},
        ("hold", BUTTON_6): {COMMAND: "6_hold"},
        ("release", BUTTON_6): {COMMAND: "6_release"},
    }
