"""Tuya based touch switch."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TuyaManufacturerClusterOnOff,
    TuyaManufacturerWindowCover,
    TuyaManufCluster,
    TuyaOnOff,
    TuyaSwitch,
    TuyaWindowCover,
    TuyaWindowCoverControl,
)


class TuyaSingleSwitch(TuyaSwitch):
    """Tuya touch switch device."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # device_version=1
        # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_oisqyl4o", "TS0601"),
            ("_TZE200_wunufsil", "TS0601"),
            ("_TZE200_vhy3iakz", "TS0601"),
            ("_TZ3000_uim07oem", "TS0601"),
            ("_TZE200_tz32mtza", "TS0601"),
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
                    TuyaManufacturerClusterOnOff,
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaZemismartSmartCover0601(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_fzo2pocs", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_3(TuyaWindowCover):
    """Tuya Zemismart blind cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x0004, 0x0005, 0x000a, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=51 input_clusters=[0, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_fzo2pocs", "TS0601"),
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
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartSmartCover0601_2(TuyaWindowCover):
    """Tuya Zemismart curtain cover motor."""

    signature = {
        # "node_descriptor": "<NodeDescriptor byte1=1 byte2=64 mac_capability_flags=142 manufacturer_code=4098
        #                       maximum_buffer_size=82 maximum_incoming_transfer_size=82 server_mask=11264
        #                       maximum_outgoing_transfer_size=82 descriptor_capability_field=0>",
        # input_clusters=[0x0000, 0x000a, 0x0004, 0x0005, 0xef00]
        # output_clusters=[0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=81 input_clusters=[0, 10, 4, 5, 61184] output_clusters=[25]>
        MODELS_INFO: [
            ("_TZE200_3i3exuay", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Time.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaMoesCover0601(TuyaWindowCover):
    """Tuya blind controller device."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        #                    maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                    maximum_outgoing_transfer_size=82, descriptor_capability_field=0)",
        # "endpoints": {
        # "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004","0x0005","0xef00"], "out_clusters": ["0x000a","0x0019"] }
        # },
        # "manufacturer": "_TZE200_zah67ekd",
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        # }
        MODELS_INFO: [
            ("_TZE200_zah67ekd", "TS0601"),
            ("_TZE200_xuzcvlku", "TS0601"),
            ("_TZE200_rddyvrci", "TS0601"),
            ("_TZE200_nueqqe6k", "TS0601"),
            ("_TZE200_gubdgai2", "TS0601"),
        ],  # Not tested
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
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufacturerWindowCover,
                    TuyaWindowCoverControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
