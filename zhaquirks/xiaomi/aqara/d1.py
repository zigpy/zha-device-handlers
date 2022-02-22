"""Xiaomi aqara single key wall switch devices."""
import copy
import logging

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    ARGS,
    ATTR_ID,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    OnOffCluster,
    XiaomiCustomDevice, DeviceTemperatureCluster, BasicCluster,
)
from .opple_remote import MultistateInputCluster, OppleCluster

ATTRIBUTE_ON_OFF = "on_off"
DOUBLE = "double"
HOLD = "long press"
PRESS_TYPES = {0: "hold", 1: "single", 2: "double", 3: "triple", 255: "release"}
SINGLE = "single"
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_CLUSTER_ID = 0xFFFF
XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03
XIAOMI_WALL_SWITCH_PROFILE_ID = 0xA1E0
XIAOMI_WALL_SWITCH_TYPE = 0x61

_LOGGER = logging.getLogger(__name__)


class OppleOperationMode(t.enum8):
    Decoupled = 0x00
    Coupled = 0x01


class OppleD1Cluster(OppleCluster):
    """Xiaomi mfg cluster implementation."""

    if hasattr(OppleCluster, 'attributes'):
        attributes = copy.deepcopy(OppleCluster.attributes)
    elif hasattr(OppleCluster, 'manufacturer_attributes'):
        attributes = copy.deepcopy(OppleCluster.manufacturer_attributes)
    else:
        attributes = {}
    
    attributes.update(
        {
            0x0200: ("operation_mode", OppleOperationMode),
        }
    )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x00FC:
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


class D1WallSwitch3Btn(XiaomiCustomDevice):
    """Aqara single and double key switch device."""

    manufacturer_id_override = 0x115F

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.switch.n3acn3"),
        ],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    DeviceTemperature.cluster_id,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    MultistateInputCluster.cluster_id,  # 18
                    OppleD1Cluster.cluster_id,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    MultistateInputCluster.cluster_id,  # 18
                    OppleD1Cluster.cluster_id,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    18,  # 18
                    OppleD1Cluster.cluster_id,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 12
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 12
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            43: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            52: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            53: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            61: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster.cluster_id,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperatureCluster,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOffCluster,  # 6
                    MultistateInputCluster,  # 18
                    OppleD1Cluster,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOffCluster,  # 6
                    MultistateInputCluster,  # 18
                    OppleD1Cluster,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOffCluster,  # 6
                    MultistateInputCluster,  # 18
                    OppleD1Cluster,  # 0xFCC0 / 64704
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 12
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 12
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            43: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            52: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            53: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            61: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (COMMAND_BUTTON_SINGLE, BUTTON_1): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BUTTON_1): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: DOUBLE, VALUE: 2},
        },
        (COMMAND_BUTTON_HOLD, BUTTON_1): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0xFCC0,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x00FC, VALUE: False},
        },

        (COMMAND_BUTTON_SINGLE, BUTTON_2): {
            ENDPOINT_ID: 42,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BUTTON_2): {
            ENDPOINT_ID: 42,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: DOUBLE, VALUE: 2},
        },
        (COMMAND_BUTTON_HOLD, BUTTON_2): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0xFCC0,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x00FC, VALUE: False},
        },

        (COMMAND_BUTTON_SINGLE, BUTTON_3): {
            ENDPOINT_ID: 43,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BUTTON_3): {
            ENDPOINT_ID: 43,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: DOUBLE, VALUE: 2},
        },
        (COMMAND_BUTTON_HOLD, BUTTON_3): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0xFCC0,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x00FC, VALUE: False},
        }, 
    }
