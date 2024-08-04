"""Xiaomi Aqara wall switch devices. Also see switch_h1 files for similar H1 rocker switches."""

import copy
from enum import Enum

from zigpy import types as t
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogInput,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

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
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    DeviceTemperatureCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    OnOffCluster,
    XiaomiCustomDevice,
)
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster, OppleCluster

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
            action = f"{self.endpoint.endpoint_id}_{self._current_state}"
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
                    DeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    Alarms.cluster_id,
                    MultistateInputCluster,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            61: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
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


class XiaomiOpple2ButtonSwitch1(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Signature 1."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2naus01")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[12], output_clusters=[]
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }


class XiaomiOpple2ButtonSwitch2(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Signature 2."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2naus01")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }


class XiaomiOpple2ButtonSwitch3(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Signature 3."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2naus01")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 1794, 2820], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }


class XiaomiOpple2ButtonSwitch4(XiaomiOpple2ButtonSwitchBase):
    """Xiaomi Opple 2 Button Switch. Signature 4."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2naus01")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 9, 1794, 2820], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
