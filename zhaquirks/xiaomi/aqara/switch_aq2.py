"""Xiaomi aqara button sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff

from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    QUADRUPLE_PRESS,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    TRIPLE_PRESS,
    UNKNOWN,
    VALUE,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)

BUTTON_DEVICE_TYPE = 0x5F01
ON_OFF = "on_off"
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)


class SwitchAQ2(XiaomiQuickInitDevice):
    """Aqara button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 6, 65535]
        # output_clusters=[0, 4, 65535]>
        MODELS_INFO: [(LUMI, "lumi.sensor_switch.aq2")],
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: BUTTON_DEVICE_TYPE,
                INPUT_CLUSTERS: [Basic.cluster_id, OnOff.cluster_id, XIAOMI_CLUSTER_ID],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    OnOff.cluster_id,
                ],
            }
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, SHORT_PRESS): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: 0, ATTRIBUTE_NAME: ON_OFF, VALUE: 1},
        },
        (DOUBLE_PRESS, DOUBLE_PRESS): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: 32768, ATTRIBUTE_NAME: UNKNOWN, VALUE: 2},
        },
        (TRIPLE_PRESS, TRIPLE_PRESS): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: 32768, ATTRIBUTE_NAME: UNKNOWN, VALUE: 3},
        },
        (QUADRUPLE_PRESS, QUADRUPLE_PRESS): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: 32768, ATTRIBUTE_NAME: UNKNOWN, VALUE: 4},
        },
    }
