"""Smoke Sensor."""

import zigpy.profiles.zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Alarms, Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone
import zigpy.zdo.types

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.heiman import HEIMAN


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


class HeimanSmokCO_V15(CustomDevice):
    """CO_V15 quirk."""

    # NodeDescriptor(
    #     logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0,
    #     frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress|MainsPowered: 132>,
    #     manufacturer_code=48042, maximum_buffer_size=64, maximum_incoming_transfer_size=0, server_mask=0, maximum_outgoing_transfer_size=0,
    #     descriptor_capability_field=<DescriptorCapability.ExtendedSimpleDescriptorListAvailable|ExtendedActiveEndpointListAvailable: 3>,
    #     *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False,
    #     *is_mains_powered=True, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False
    # )"
    signature = {
        MODELS_INFO: [(HEIMAN, "CO_V15")],
        ENDPOINTS: {
            # "profile_id": 260,"device_type": "0x0402",
            # "in_clusters": ["0x0000","0x0001","0x0003","0x0009","0x0500"],
            # "out_clusters": ["0x0019"]
            1: {
                PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                DEVICE_TYPE: zigpy.profiles.zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    IasZone.cluster_id,
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
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }
