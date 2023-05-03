from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Groups,
    Identify,
    Scenes,
    Ota,
)
from zigpy.zcl.clusters.closures import (
    DoorLock,
)
import zigpy.zdo.types
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    NODE_DESCRIPTOR,
)

MANUFACTURER_SPECIFIC_PROFILE_ID = 0xFEA2


class BatteryBasicCluster(CustomCluster, Basic):
    """Basic cluster implementation.
    This implementation sets power source to battery
    and removes incorrect MainsPowered-flag."""

    cluster_id = Basic.cluster_id
    POWER_SOURCE = 0x0007

    _CONSTANT_ATTRIBUTES = {
        POWER_SOURCE: Basic.PowerSource.Battery,
    }


class EasyCodeTouch(CustomDevice):
    """onesti.easycodetouch"""

    signature = {
        MODELS_INFO: [("Onesti Products AS", "EasyCodeTouch")],
        ENDPOINTS: {
            # SimpleDescriptor(endpoint=11, profile=260, device_type=10,
            # device_version=1,
            # input_clusters=[0, 1, 3, 5, 4, 257, 65186],
            # output_clusters=[25])
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    DoorLock.cluster_id,
                    MANUFACTURER_SPECIFIC_PROFILE_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        NODE_DESCRIPTOR: zigpy.zdo.types.NodeDescriptor(
            logical_type=2,
            complex_descriptor_available=0,
            user_descriptor_available=0,
            reserved=0,
            aps_flags=0,
            frequency_band=8,
            mac_capability_flags=136,
            manufacturer_code=4660,
            maximum_buffer_size=108,
            maximum_incoming_transfer_size=127,
            server_mask=11264,
            maximum_outgoing_transfer_size=127,
            descriptor_capability_field=0,
        ),
        ENDPOINTS: {
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    BatteryBasicCluster,
                    PowerConfiguration.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    DoorLock.cluster_id,
                    MANUFACTURER_SPECIFIC_PROFILE_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
