import copy
import logging

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Alarms,
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
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_OFF,
    COMMAND_SINGLE,
    COMMAND_TOGGLE,
    COMMAND_TRIPLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    DeviceTemperatureCluster,
    OnOffCluster,
    XiaomiCustomDevice,
    XiaomiMeteringCluster,
)
from zhaquirks.xiaomi.aqara.opple_remote import PRESS_TYPES, MultistateInputCluster
from zhaquirks.xiaomi.aqara.opple_switch import (
    OppleIndicatorLight,
    OppleOperationMode,
    OppleSwitchCluster,
)

_LOGGER = logging.getLogger(__name__)


class AqaraH1SingleRockerSwitch(XiaomiCustomDevice):
    """Aqara H1 Single Rocker Switch (with neutral)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n1aeu1")],
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
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000a
                    Ota.cluster_id,  # 0x0019
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,  # 0
                    DeviceTemperatureCluster.cluster_id, # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOffCluster,  # 6
                    Alarms.cluster_id,  # 9
                    MultistateInputCluster,  # 18
                    XiaomiMeteringCluster.cluster_id,  # 0x0702
                    OppleSwitchCluster,  # 0xFCC0 / 64704
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
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
        (SHORT_PRESS, BUTTON): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            COMMAND: '41_{}'.format(COMMAND_SINGLE),
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
        },
        (DOUBLE_PRESS, BUTTON): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            COMMAND: '41_{}'.format(COMMAND_DOUBLE),
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
        },
        # when triple-pressed, you're technically getting an attribute update call, so not sure if it can be used
        (TRIPLE_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0,
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            ARGS: {ATTRIBUTE_ID: 5, ATTRIBUTE_NAME: 'model', VALUE: 'lumi.switch.n1aeu1'},
        },
        (LONG_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 64704,
            COMMAND: '1_{}'.format(COMMAND_HOLD),
            ARGS: {ATTR_ID: 0x00FC, PRESS_TYPE: COMMAND_HOLD, VALUE: 0},
        },
    }
