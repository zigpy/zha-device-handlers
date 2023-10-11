"""Tuya dimmable dual white led controller."""
from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaManufCluster


class DualWhiteLedController(CustomDevice):
    """Tuya dimmable dual white led controller."""

    # {
    #   "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.FullFunctionDevice|MainsPowered|RxOnWhenIdle|AllocateAddress: 142>, manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752, maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
    #   "endpoints": {
    #     "1": {
    #       "profile_id": "0x0104",
    #       "device_type": "0x010c",
    #       "input_clusters": [
    #         "0x0000",
    #         "0x0003",
    #         "0x0004",
    #         "0x0005",
    #         "0x0006",
    #         "0x0008",
    #         "0x0300",
    #         "0x1000",
    #         "0xef00"
    #       ],
    #       "output_clusters": [
    #         "0x000a",
    #         "0x0019"
    #       ]
    #     },
    #     "242": {
    #       "profile_id": "0xa1e0",
    #       "device_type": "0x0061",
    #       "input_clusters": [],
    #       "output_clusters": [
    #         "0x0021"
    #       ]
    #     }
    #   },
    #   "manufacturer": "_TZ3210_xwqng7ol",
    #   "model": "TS0502B",
    #   "class": "zigpy.device.Device"
    # }
    signature = {
        MODELS_INFO: [
            ("_TZ3210_xwqng7ol", "TS0502B"),
            ("_TZ3210_frm6149r", "TS0502B"),
            ("_TZ3210_jtifm80b", "TS0502B"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=268
            # input_clusters=[0, 3, 4, 5, 6, 8, 768, 4096, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
