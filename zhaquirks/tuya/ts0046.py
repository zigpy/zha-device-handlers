"""Tuya 6 Button Remote."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration, Time

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.tuya import (
    EnchantedDevice,
    TuyaNoBindPowerConfigurationCluster,
    TuyaSmartRemoteOnOffCluster,
    TuyaZBE000Cluster,
)


class Tuya6ButtonTriggers:
    """Tuya 6-button remote device triggers."""

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_3): {ENDPOINT_ID: 3, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_4): {ENDPOINT_ID: 4, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_5): {ENDPOINT_ID: 5, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_5): {ENDPOINT_ID: 5, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_5): {ENDPOINT_ID: 5, COMMAND: DOUBLE_PRESS},
        (SHORT_PRESS, BUTTON_6): {ENDPOINT_ID: 6, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_6): {ENDPOINT_ID: 6, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_6): {ENDPOINT_ID: 6, COMMAND: DOUBLE_PRESS},
    }


class TuyaSmartRemote0046(EnchantedDevice, Tuya6ButtonTriggers):
    """Tuya 6-button remote device with time on out cluster."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0, device_version=1, input_clusters=[0, 1, 6, 57344], output_clusters=[10, 25]))
        # SizePrefixedSimpleDescriptor(endpoint=2, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        # SizePrefixedSimpleDescriptor(endpoint=3, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        # SizePrefixedSimpleDescriptor(endpoint=4, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        MODEL: "TS0046",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    TuyaZBE000Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
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
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            4: {
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
                    TuyaNoBindPowerConfigurationCluster,
                    TuyaZBE000Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
        },
    }
