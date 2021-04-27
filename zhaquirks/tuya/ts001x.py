"""Tuya 1,2,3 gang no neutral light switch."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.tuya import TuyaSwitch


class TuyaSingleNoNeutralSwitch(TuyaSwitch):
    """Tuya 1 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        MODELS_INFO: [("_TZ3000_9hpxg80k", "TS0011")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaDoubleNoNeutralSwitch(TuyaSwitch):
    """Tuya 2 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODELS_INFO: [("_TZ3000_fvh3pjaz", "TS0012")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }


class TuyaTripleNoNeutralSwitch(TuyaSwitch):
    """Tuya 3 gang no neutral light switch."""

    signature = {
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)
        # "node_descriptor": "NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=128, manufacturer_code=4098,
        # maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        # maximum_outgoing_transfer_size=82, descriptor_capability_field=0)"
        MODEL: "TS0013",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=100
            # device_version=1
            # input_clusters=[0, 4, 5, 6]
            # output_clusters=[a, 19]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=100
            # device_version=1
            # input_clusters=[4, 5, 6]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
