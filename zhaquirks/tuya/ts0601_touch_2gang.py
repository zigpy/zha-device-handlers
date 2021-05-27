"""Tuya based touch button sensor."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time

from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from ..tuya import (
    TuyaManufacturerClusterOnOff,
    TuyaManufCluster,
    TuyaOnOff,
    TuyaSwitch,
)

class TuyaTouch2Gang(TuyaSwitch):
    """Tuya 2 button switch device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        # "node_descriptor": "<NodeDescriptor(byte1=1, byte2=64, mac_capability_flags=142, manufacturer_code=4098,
        #                       maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                       maximum_outgoing_transfer_size=82, descriptor_capability_field=0,
        #                       *complex_descriptor_available=False, *is_alternate_pan_coordinator=False,
        #                       *is_coordinator=False, *is_end_device=False, *is_full_function_device=True,
        #                       *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False,
        #                       *is_valid=True, *logical_type=<LogicalType.Router: 1>, *user_descriptor_available=False)>",
        # device_version=1
        # input_clusters=[0x0000,0x0004, 0x0005, 0xef00]
        # output_clusters=[0x000a, 0x0019]
        # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051 device_version=1 input_clusters=[0, 4, 5, 61184] output_clusters=[10, 25]>
        MODELS_INFO: [("_TZE200_nkjintbl", "TS0601")],
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
