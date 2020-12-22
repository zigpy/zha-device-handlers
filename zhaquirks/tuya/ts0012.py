"""Tuya 2 Button switch."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, Ota, Scenes, PowerConfiguration, Time

from . import TuyaSmartRemote, TuyaSmartRemoteOnOffCluster, TuyaManufacturerClusterOnOff, TuyaManufCluster, TuyaOnOff, TuyaSwitch
from ..const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)


class TuyaDoubleSwitch(TuyaSwitch):
    """Tuya 2-button remote device."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=100, device_version=0, input_clusters=[0, 4, 5, 6], output_clusters=[19]))
        # SizePrefixedSimpleDescriptor(endpoint=2, profile=260, device_type=100, device_version=0, input_clusters=[4, 5, 6], output_clusters=[])
        MODELS_INFO: [("_TYZB01_vzrytttn", "TS0012")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufCluster.cluster_id,

                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufCluster.cluster_id,
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
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerClusterOnOff,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    TuyaSmartRemoteOnOffCluster,
                    Time.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerClusterOnOff,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: SHORT_PRESS},
        (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: SHORT_PRESS},
    }
