"""Tuya based touch switch."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, LevelControl, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaDimmerSwitch,
    TuyaLevelControl,
    TuyaManufacturerClusterOnOff,
    TuyaManufacturerLevelControl,
    TuyaManufCluster,
    TuyaOnOff,
)


class TuyaSingleSwitchDimmer(TuyaDimmerSwitch):
    """Tuya touch switch device."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1, byte2=64, mac_capability_flags=142, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0>",
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_dfxkcots", "TS0601"),
            ("_TZE200_whpb9yts", "TS0601"),
            ("_TZE200_ebwgzdqq", "TS0601"),
            ("_TZE200_9i9dt8is", "TS0601"),
            ("_TZE200_swaamsoy", "TS0601"),
            ("_TZE200_0nauxa0p", "TS0601"),
            ("_TZE200_la2c2uo9", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    LevelControl.cluster_id,
                    TuyaManufacturerClusterOnOff,
                    TuyaOnOff,
                    TuyaManufacturerLevelControl,
                    TuyaLevelControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
