"""Smoke Sensor."""

import zigpy.profiles.zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Alarms, Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone
import zigpy.zdo.types

from . import HEIMAN
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class HeimanSmokYDLV10(CustomDevice):
    """YDLV10 quirk."""

    # NodeDescriptor(byte1=2, byte2=64, mac_capability_flags=132,
    # manufacturer_code=48042, maximum_buffer_size=64, maximum_incoming_transfer_size=0,
    # server_mask=0, maximum_outgoing_transfer_size=0, descriptor_capability_field=3)
    # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=1026,
    # device_version=0, input_clusters=[0, 3, 1280, 1, 9, 1282], output_clusters=[25])
    signature = {
        MODELS_INFO: [(HEIMAN, "SMOK_YDLV10")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    IasZone.cluster_id,
                    IasWd.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        NODE_DESCRIPTOR: zigpy.zdo.types.NodeDescriptor(
            0x02, 0x40, 0x84 & 0b1111_1011, 0xBBAA, 0x40, 0x0000, 0x0000, 0x0000, 0x03
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    IasZone.cluster_id,
                    IasWd.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }
