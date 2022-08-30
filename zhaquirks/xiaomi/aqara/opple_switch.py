"""Xiaomi aqara single key wall switch devices."""
import copy
from enum import Enum

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogInput,
    Basic,
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
    CLUSTER_ID,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    COMMAND_DOUBLE,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    BasicCluster,
    DeviceTemperatureCluster,
    OnOffCluster,
    XiaomiCustomDevice,
    XiaomiMeteringCluster,
)

from .opple_remote import MultistateInputCluster, OppleCluster

BOTH_BUTTONS = "both_buttons"
PRESS_TYPES = {0: "hold", 1: "single", 2: "double", 3: "triple", 255: "release"}


class OppleOperationMode(t.uint8_t, Enum):
    """Opple operation_mode enum."""

    Decoupled = 0x00
    Coupled = 0x01


class OppleSwitchMode(t.uint8_t, Enum):
    """Opple switch_mode enum."""

    Fast = 0x01
    Multi = 0x02


class OppleSwitchType(t.uint8_t, Enum):
    """Opple switch_type enum."""

    Toggle = 0x01
    Momentary = 0x02


class OppleIndicatorLight(t.uint8_t, Enum):
    """Opple indicator light enum."""

    Normal = 0x00
    Reverse = 0x01


class OppleSwitchCluster(OppleCluster):
    """Xiaomi mfg cluster implementation."""

    attributes = copy.deepcopy(OppleCluster.attributes)

    attributes.update(
        {
            0x0002: ("power_outage_count", t.uint8_t, True),
            0x000A: ("switch_type", OppleSwitchType, True),
            0x00F0: ("reverse_indicator_light", OppleIndicatorLight, True),
            0x0125: ("switch_mode", OppleSwitchMode, True),
            0x0200: ("operation_mode", OppleOperationMode, True),
            0x0201: ("power_outage_memory", t.Bool, True),
            0x0202: ("auto_off", t.Bool, True),
            0x0203: ("do_not_disturb", t.Bool, True),
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


class XiaomiOpple2ButtonSwitchBase(XiaomiCustomDevice):
    """Xiaomi Opple 2 Button Switch."""

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
                    Alarms.cluster_id,  # 9
                    MultistateInputCluster,  # 18
                    XiaomiMeteringCluster,  # 0x0702
                    OppleSwitchCluster,  # 0xFCC0 / 64704
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
                    OppleSwitchCluster,  # 0xFCC0 / 64704
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
            51: {
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
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BUTTON_1): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
        },
        (COMMAND_BUTTON_HOLD, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0xFCC0,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x00FC, VALUE: False},
        },
        (COMMAND_BUTTON_SINGLE, BUTTON_2): {
            ENDPOINT_ID: 42,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BUTTON_2): {
            ENDPOINT_ID: 42,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
        },
        #        (COMMAND_BUTTON_HOLD, BUTTON_2): {
        #            ENDPOINT_ID: 1,
        #            CLUSTER_ID: 0xFCC0,
        #            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
        #            ARGS: {ATTR_ID: 0x00FC, VALUE: False},
        #        },
        (COMMAND_BUTTON_SINGLE, BOTH_BUTTONS): {
            ENDPOINT_ID: 51,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
        },
        (COMMAND_BUTTON_DOUBLE, BOTH_BUTTONS): {
            ENDPOINT_ID: 51,
            CLUSTER_ID: 18,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
        },
        (COMMAND_BUTTON_HOLD, BOTH_BUTTONS): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0xFCC0,
            # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTR_ID: 0x00FC, VALUE: 0},
        },
    }


class XiaomiOpple2ButtonSwitchFace1(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Face 1."""

    device_automation_triggers = XiaomiOpple2ButtonSwitchBase.device_automation_triggers

    signature = {
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    DeviceTemperatureCluster.cluster_id,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    MultistateInputCluster.cluster_id,  # 18
                    OppleSwitchCluster.cluster_id,  # 0xFCC0 / 64704
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
                    OppleSwitchCluster.cluster_id,  # 0xFCC0 / 64704
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
            51: {
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


class XiaomiOpple2ButtonSwitchFace2(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Face 2."""

    device_automation_triggers = XiaomiOpple2ButtonSwitchBase.device_automation_triggers

    signature = {
        ENDPOINTS: {
            #  input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    DeviceTemperatureCluster.cluster_id,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    Alarms.cluster_id,  # 9
                    XiaomiMeteringCluster.cluster_id,  # 0x0702
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            #  input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
