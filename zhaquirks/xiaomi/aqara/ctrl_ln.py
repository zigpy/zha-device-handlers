"""Xiaomi aqara single key wall switch devices."""

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    BinaryOutput,
    DeviceTemperature,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks import Bus, EventableCluster
from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    VALUE,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    OnOffCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

ATTRIBUTE_PRESENT_VALUE = "present_value"


class CtrlLn(XiaomiCustomDevice):
    """Aqara double key switch device."""

    class BasicClusterDecoupled(BasicCluster):
        """Adds attributes for decoupled mode."""

        # Known Options for 'decoupled_mode_<button>':
        # * 254 (decoupled)
        # * 18 (relay controlled)
        attributes = BasicCluster.attributes.copy()
        attributes.update(
            {
                0xFF22: ("decoupled_mode_left", t.uint8_t, True),
                0xFF23: ("decoupled_mode_right", t.uint8_t, True),
            }
        )

    class WallSwitchMultistateInputCluster(EventableCluster, MultistateInput):
        """WallSwitchMultistateInputCluster: fire events corresponding to press type."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.ctrl_ln1.aq1"), (LUMI, "lumi.ctrl_ln2.aq1")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    BinaryOutput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [OnOff.cluster_id, BinaryOutput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [Groups.cluster_id, AnalogInput.cluster_id],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, BinaryOutput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, BinaryOutput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, BinaryOutput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    BasicClusterDecoupled,
                    XiaomiPowerConfiguration,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    Time.cluster_id,
                    BinaryOutput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [OnOffCluster, BinaryOutput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [Groups.cluster_id, AnalogInput.cluster_id],
            },
            5: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    WallSwitchMultistateInputCluster,
                    BinaryOutput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    WallSwitchMultistateInputCluster,
                    BinaryOutput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    WallSwitchMultistateInputCluster,
                    BinaryOutput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {
            ENDPOINT_ID: 5,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 1},
        },
        (DOUBLE_PRESS, BUTTON_1): {
            ENDPOINT_ID: 5,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 2},
        },
        (SHORT_PRESS, BUTTON_2): {
            ENDPOINT_ID: 6,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 1},
        },
        (DOUBLE_PRESS, BUTTON_2): {
            ENDPOINT_ID: 6,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 2},
        },
        (SHORT_PRESS, BUTTON_3): {
            ENDPOINT_ID: 7,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 1},
        },
        (DOUBLE_PRESS, BUTTON_3): {
            ENDPOINT_ID: 7,
            CLUSTER_ID: 18,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 85, ATTRIBUTE_NAME: ATTRIBUTE_PRESENT_VALUE, VALUE: 2},
        },
    }
