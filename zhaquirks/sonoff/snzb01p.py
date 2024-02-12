"""Sonoff Smart Button SNZB-01P"""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)

from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

SONOFF_CLUSTER_ID = 0xFC57


class SonoffSmartButtonSNZB01P(CustomDevice):
    """Sonoff smart button remote - model SNZB-01P"""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=0
        #  device_version=1
        #  input_clusters=[0, 1, 3, 32, 64599]
        #  output_clusters=[3, 6, 25]>
        MODELS_INFO: [
            ("eWeLink", "SNZB-01P"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    SONOFF_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    SONOFF_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON, CLUSTER_ID: 6, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF, CLUSTER_ID: 6, ENDPOINT_ID: 1},
    }
