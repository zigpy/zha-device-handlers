"""Smoke Sensor."""

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasWd, IasZone
import zigpy.zdo.types
import logging

logger = logging.getLogger('zha.debug')

# from heiman import HeimanE1Cluster


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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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


class HeimanSmokCO_CTPG(CustomDevice):
    """CO_CTPG quirk."""

    signature = {
        MODELS_INFO: [(HEIMAN, "CO_CTPG")],
        ENDPOINTS: {
            1: {
                # "profile_id": 260,
                # "device_type": "0x0402",
                # "in_clusters": ["0x0000","0x0001","0x0003","0x0009","0x0500"]
                # "out_clusters": ["0x0019"]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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
            logical_type=2,
            complex_descriptor_available=0,
            user_descriptor_available=0,
            reserved=0,
            aps_flags=0,
            frequency_band=8,
            mac_capability_flags=132 & 0b1111_1011,
            manufacturer_code=4627,
            maximum_buffer_size=64,
            maximum_incoming_transfer_size=0,
            server_mask=0,
            maximum_outgoing_transfer_size=0,
            descriptor_capability_field=3,
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
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


class HeimanSmokeN30(CustomDevice):
    """SmokeN30 quirk."""

    # NodeDescriptor(
    #     logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0,
    #     frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>,
    #     manufacturer_code=4619, maximum_buffer_size=127, maximum_incoming_transfer_size=100, server_mask=11264, maximum_outgoing_transfer_size=100,
    #     descriptor_capability_field=<DescriptorCapability.NONE: 0>,
    #     *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False,
    #     *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)
    signature = {
        MODELS_INFO: [("HEIMAN", "SmokeSensor-N-3.0")],
        ENDPOINTS: {
            # "profile_id": 260,"device_type": "0x0402",
            # "in_clusters": ["0x0000","0x0001","0x0003","0x0500","0x0502","0x0b05"],
            # "out_clusters": ["0x0019"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    IasWd.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }


class HeimanSmokeEF30(CustomDevice):
    """SmokeEF30 quirk."""

    # NodeDescriptor(
    #     logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0,
    #     frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>,
    #     manufacturer_code=4619, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82,
    #     descriptor_capability_field=<DescriptorCapability.NONE: 0>,
    #     *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False,
    #     *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)
    signature = {
        MODELS_INFO: [("HEIMAN", "SmokeSensor-EF-3.0")],
        ENDPOINTS: {
            # "profile_id": "0x0104", "device_type": "0x0402",
            # "input_clusters": ["0x0000", "0x0001", "0x0003", "0x0020", "0x0500", "0x0502", "0x0b05"],
            # "output_clusters": ["0x0003", "0x0019"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    IasWd.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }


class HeimanSmokeEM(CustomDevice):
    """SmokeEM quirk."""

    signature = {
        MODELS_INFO: [("HEIMAN", "SmokeSensor-EM")],
        ENDPOINTS: {
            # "profile_id": "0x0104", "device_type": "0x0402",
            # "input_clusters": ["0x0000", "0x0001", "0x0003", "0x0500", "0x0502"],
            # "output_clusters": ["0x0019"]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
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
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

# BUZZER_MANUAL_MUTE = 0x0126
# SELF_TEST = 0x0127
# SMOKE = 0x013A
# SMOKE_DENSITY = 0x013B
# HEARTBEAT_INDICATOR = 0x013C
# BUZZER_MANUAL_ALARM = 0x013D
# BUZZER = 0x013E
# LINKAGE_ALARM = 0x014B
# LINKAGE_ALARM_STATE = 0x014C
# SMOKE_DENSITY_DBM = 0x1403  # fake attribute for smoke density in dB/m


# SMOKE_DENSITY_DBM_MAP = {
#     0: 0,
#     1: 0.085,
#     2: 0.088,
#     3: 0.093,
#     4: 0.095,
#     5: 0.100,
#     6: 0.105,
#     7: 0.110,
#     8: 0.115,
#     9: 0.120,
#     10: 0.125,
# }


# class OppleCluster(XiaomiAqaraE1Cluster):
# class OppleCluster(HeimanE1Cluster):
#     """Opple cluster."""

#     attributes = {
#         BUZZER_MANUAL_MUTE: ("buzzer_manual_mute", types.uint8_t, True),
#         SELF_TEST: ("self_test", types.Bool, True),
#         SMOKE: ("smoke", types.uint8_t, True),
#         SMOKE_DENSITY: ("smoke_density", types.uint8_t, True),
#         HEARTBEAT_INDICATOR: ("heartbeat_indicator", types.uint8_t, True),
#         BUZZER_MANUAL_ALARM: ("buzzer_manual_alarm", types.uint8_t, True),
#         BUZZER: ("buzzer", types.uint32_t, True),
#         LINKAGE_ALARM: ("linkage_alarm", types.uint8_t, True),
#         LINKAGE_ALARM_STATE: ("linkage_alarm_state", types.uint8_t, True),
#         SMOKE_DENSITY_DBM: ("smoke_density_dbm", types.Single, True),
#     }

#     def _update_attribute(self, attrid: int, value: any) -> None:
#         """Pass attribute update to another cluster if necessary."""
#         # super()._update_attribute(attrid, value)
#         if attrid == SMOKE:
#             # self.endpoint.ias_zone.update_attribute(ZONE_STATUS, value)
#             logger.debug("=== SMOKE ===")
#         elif attrid == SMOKE_DENSITY:
#             self.update_attribute(SMOKE_DENSITY_DBM, SMOKE_DENSITY_DBM_MAP[value])




# class HeimanSmokeEFA2(CustomDevice):
#     """SmokeEFA2 quirk."""

#     signature = {
#         MODELS_INFO: [("HEIMAN", "HS1SA-EF-3.0")],
#         ENDPOINTS: {
#             1: {
#                 PROFILE_ID: zha.PROFILE_ID,
#                 DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
#                 INPUT_CLUSTERS: [
#                     Basic.cluster_id,
#                     PowerConfiguration.cluster_id,
#                     Identify.cluster_id,
#                     PollControl.cluster_id,
#                     IasZone.cluster_id,
#                     IasWd.cluster_id,
#                     Diagnostic.cluster_id,
#                 ],
#                 OUTPUT_CLUSTERS: [
#                     Identify.cluster_id,
#                     Ota.cluster_id,
#                 ],
#             },
#         },
#     }

#     replacement = {
#         ENDPOINTS: {
#             1: {
#                 PROFILE_ID: zha.PROFILE_ID,
#                 DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
#                 INPUT_CLUSTERS: [
#                     Basic.cluster_id,
#                     PowerConfiguration.cluster_id,
#                     Identify.cluster_id,
#                     PollControl.cluster_id,
#                     IasZone.cluster_id,
#                     Diagnostic.cluster_id,
#                 ],
#                 OUTPUT_CLUSTERS: [
#                     Identify.cluster_id,
#                     Ota.cluster_id,
#                 ],
#             },
#         },
#     }
