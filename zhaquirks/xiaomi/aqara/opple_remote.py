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

from .. import LUMI, BasicCluster, XiaomiCustomDevice
from ... import PowerConfigurationCluster
from ...const import (
    ALT_DOUBLE_PRESS,
    ALT_LONG_PRESS,
    ALT_SHORT_PRESS,
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
    LONG_RELEASE,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

PRESS_TYPES = {0: "long press", 1: "single", 2: "double", 3: "triple", 255: "release"}
STATUS_TYPE_ATTR = 0x0055  # decimal = 85

COMMAND_1_SINGLE = "1_single"
COMMAND_1_DOUBLE = "1_double"
COMMAND_1_TRIPLE = "1_triple"
COMMAND_1_HOLD = "1_hold"
COMMAND_1_RELEASE = "1_release"

COMMAND_2_SINGLE = "2_single"
COMMAND_2_DOUBLE = "2_double"
COMMAND_2_TRIPLE = "2_triple"
COMMAND_2_HOLD = "2_hold"
COMMAND_2_RELEASE = "2_release"

COMMAND_3_SINGLE = "3_single"
COMMAND_3_DOUBLE = "3_double"
COMMAND_3_TRIPLE = "3_triple"
COMMAND_3_HOLD = "3_hold"
COMMAND_3_RELEASE = "3_release"

COMMAND_4_SINGLE = "4_single"
COMMAND_4_DOUBLE = "4_double"
COMMAND_4_TRIPLE = "4_triple"
COMMAND_4_HOLD = "4_hold"
COMMAND_4_RELEASE = "4_release"

COMMAND_5_SINGLE = "5_single"
COMMAND_5_DOUBLE = "5_double"
COMMAND_5_TRIPLE = "5_triple"
COMMAND_5_HOLD = "5_hold"
COMMAND_5_RELEASE = "5_release"

COMMAND_6_SINGLE = "6_single"
COMMAND_6_DOUBLE = "6_double"
COMMAND_6_TRIPLE = "6_triple"
COMMAND_6_HOLD = "6_hold"
COMMAND_6_RELEASE = "6_release"

OPPLE_CLUSTER_ID = 0xFCC0
OPPLE_MFG_CODE = 0x115F

_LOGGER = logging.getLogger(__name__)


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    cluster_id = MultistateInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    async def configure_reporting(
        self,
        attribute,
        min_interval,
        max_interval,
        reportable_change,
        manufacturer=None,
    ):
        """Configure reporting."""
        pass

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


class OppleCluster(CustomCluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    cluster_id = OPPLE_CLUSTER_ID
    manufacturer_attributes = {0x0009: ("mode", types.uint8_t)}
    attr_config = {0x0009: 0x01}

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=OPPLE_MFG_CODE)
        return result


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
        (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
        (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
        (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
        (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
    }


class RemoteB286OPCN01Alt(XiaomiCustomDevice):
    """Aqara Opple 2 button remote device (after alternate mode is enabled)."""

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
            2: {},
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

    device_automation_triggers = RemoteB286OPCN01.device_automation_triggers


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
        (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
        (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
        (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
        (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_DOUBLE},
        (TRIPLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_3_HOLD},
        (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_3_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
        (TRIPLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
        (LONG_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
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
        (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
        (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
        (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
        (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
        (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_DOUBLE},
        (TRIPLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_3_HOLD},
        (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_3_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
        (TRIPLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
        (LONG_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_5): {COMMAND: COMMAND_5_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_5): {COMMAND: COMMAND_5_DOUBLE},
        (TRIPLE_PRESS, BUTTON_5): {COMMAND: COMMAND_5_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_5): {COMMAND: COMMAND_5_HOLD},
        (LONG_RELEASE, BUTTON_5): {COMMAND: COMMAND_5_RELEASE},
        (ALT_SHORT_PRESS, BUTTON_6): {COMMAND: COMMAND_6_SINGLE},
        (ALT_DOUBLE_PRESS, BUTTON_6): {COMMAND: COMMAND_6_DOUBLE},
        (TRIPLE_PRESS, BUTTON_6): {COMMAND: COMMAND_6_TRIPLE},
        (ALT_LONG_PRESS, BUTTON_6): {COMMAND: COMMAND_6_HOLD},
        (LONG_RELEASE, BUTTON_6): {COMMAND: COMMAND_6_RELEASE},
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

    device_automation_triggers = RemoteB286OPCN01.device_automation_triggers


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

    device_automation_triggers = RemoteB486OPCN01.device_automation_triggers


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

    device_automation_triggers = RemoteB686OPCN01.device_automation_triggers


class RemoteB686OPCN01V3(XiaomiCustomDevice):
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
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id, Identify.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
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
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id, Identify.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster, Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster, Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster, Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInputCluster, Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
        },
    }

    device_automation_triggers = RemoteB686OPCN01.device_automation_triggers
