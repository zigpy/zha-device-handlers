"""Tuya 1 Button Remote."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration, Time

from zhaquirks.const import (
    BUTTON_1,
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
    TuyaNoBindPowerConfigurationCluster,
    TuyaSmartRemoteOnOffCluster,
    TuyaZBE000Cluster,
)


class TuyaSmartRemote0041TO(CustomDevice):
    """Tuya 1-button remote device with time on out."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0, device_version=1, input_clusters=[0, 1, 6], output_clusters=[25, 10])
        MODEL: "TS0041",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
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
                    TuyaSmartRemoteOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
    }


class TuyaSmartRemote0041TI(CustomDevice):
    """Tuya 1-button remote device with time on in."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0, device_version=1, input_clusters=[0, 10, 1, 6], output_clusters=[25]))
        MODEL: "TS0041",
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
                    TuyaSmartRemoteOnOffCluster,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
    }


class TuyaSmartRemote0041TOPlusA(CustomDevice):
    """Tuya 1-button remote device with time on out cluster."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0, device_version=1, input_clusters=[0, 1, 6, 57344], output_clusters=[10, 25]))
        # SizePrefixedSimpleDescriptor(endpoint=2, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        # SizePrefixedSimpleDescriptor(endpoint=3, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        # SizePrefixedSimpleDescriptor(endpoint=4, profile=260, device_type=0, device_version=1, input_clusters=[1, 6], output_clusters=[])
        MODEL: "TS0041",
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
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaNoBindPowerConfigurationCluster,
                    TuyaZBE000Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                    TuyaSmartRemoteOnOffCluster,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
    }


class TuyaSmartRemote0041_var04(CustomDevice):
    """Tuya 1-button remote device with time on out cluster."""

    signature = {
        MODEL: "TS0041A",
        ENDPOINTS: {
            # "profile_id": 260,
            # "device_type": "0x0000",
            # "in_clusters": ["0x0000","0x0001","0x0006"],
            # "out_clusters": ["0x0006","0x000a","0x0019"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Time.cluster_id,
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
                    TuyaSmartRemoteOnOffCluster,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: LONG_PRESS},
        (DOUBLE_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: DOUBLE_PRESS},
    }
