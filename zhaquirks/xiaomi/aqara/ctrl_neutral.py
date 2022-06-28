"""Xiaomi aqara single key wall switch devices."""
import logging

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

from zhaquirks import EventableCluster
from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    VALUE,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    OnOffCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

ATTRIBUTE_ON_OFF = "on_off"
DOUBLE = "double"
HOLD = "long press"
PRESS_TYPES = {0: "long press", 1: "single", 2: "double"}
SINGLE = "single"
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_CLUSTER_ID = 0xFFFF
XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03

_LOGGER = logging.getLogger(__name__)

# click attr 0xF000
# single click 0x3FF1F00
# double click 0xCFF1F00


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


class WallSwitchOnOffCluster(EventableCluster, OnOff):
    """WallSwitchOnOffCluster: fire events corresponding to press type."""


class CtrlNeutral(XiaomiCustomDevice):
    """Aqara single key switch device."""

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.ctrl_neutral1"),
            (LUMI, "lumi.switch.b1lacn02"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=2
            # input_clusters=[0, 3, 1, 2, 25, 10]
            # output_clusters=[0, 10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=6 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=8 profile=260 device_type=83
            # device_version=2
            # input_clusters=[12]
            # output_clusters=[]>
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    BasicClusterDecoupled,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOffCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOffCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                    WallSwitchOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (COMMAND_HOLD, BUTTON): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 0},
        },
        (COMMAND_RELEASE, BUTTON): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 1},
        },
        (COMMAND_DOUBLE, BUTTON): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 2},
        },
    }


class CtrlNeutral_2G(XiaomiCustomDevice):
    """Aqara double key switch device."""

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.ctrl_neutral2"),
            (LUMI, "lumi.switch.b2lacn02"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=2
            # input_clusters=[0, 3, 1, 2, 25, 10]
            # output_clusters=[0, 10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=256
            # device_version=2
            # input_clusters=[16, 6, 4, 5]
            # output_clusters=[]
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=5 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=6 profile=260 device_type=0
            # device_version=2
            # input_clusters=[18, 6]
            # output_clusters=[]>
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id, OnOff.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=8 profile=260 device_type=83
            # device_version=2
            # input_clusters=[12]
            # output_clusters=[]>
            8: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    BasicClusterDecoupled,
                    Identify.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, Ota.cluster_id],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOffCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BinaryOutput.cluster_id,
                    OnOffCluster,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                    WallSwitchOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            5: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                    WallSwitchOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (COMMAND_HOLD, BUTTON_1): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 0},
        },
        (COMMAND_RELEASE, BUTTON_1): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 1},
        },
        (COMMAND_DOUBLE, BUTTON_1): {
            ENDPOINT_ID: 4,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 2},
        },
        (COMMAND_HOLD, BUTTON_2): {
            ENDPOINT_ID: 5,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 0},
        },
        (COMMAND_RELEASE, BUTTON_2): {
            ENDPOINT_ID: 5,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 1},
        },
        (COMMAND_DOUBLE, BUTTON_2): {
            ENDPOINT_ID: 5,
            CLUSTER_ID: 6,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ATTRIBUTE_ON_OFF, VALUE: 2},
        },
    }
