"""Tuya 2 Button Remote."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration, Time

from . import TuyaSmartRemote, TuyaSmartRemoteOnOffCluster
from ..const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
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


class TuyaSmartRemote0042(TuyaSmartRemote):
    """Tuya 2-button remote device."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0, device_version=1, input_clusters=[0, 10, 1, 6], output_clusters=[25]))
        # SizePrefixedSimpleDescriptor(endpoint=2, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        MODELS_INFO: [("_TZ3000_owgcnkrh", "TS0042")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    TuyaSmartRemoteOnOffCluster,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    TuyaSmartRemoteOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: DOUBLE_PRESS},
    }
