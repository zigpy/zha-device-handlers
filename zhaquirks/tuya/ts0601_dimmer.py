"""Tuya based touch switch."""
from typing import Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    LevelControl,
    Ota,
    Scenes,
    Time,
)

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
from zhaquirks.tuya.mcu import (
    TuyaInWallLevelControl,
    TuyaLevelControlManufCluster,
    TuyaOnOff as TuyaOnOffMCU,
)


class NoManufacturerCluster(CustomCluster):
    """Forces the NO manufacturer id in command."""

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""
        self.debug("Setting the NO manufacturer id in command: %s", command_id)
        return await super().command(
            command_id,
            *args,
            manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID,
            expect_reply=expect_reply,
            tsn=tsn,
        )


class TuyaInWallLevelControlNM(NoManufacturerCluster, TuyaInWallLevelControl):
    """Tuya Level cluster for inwall dimmable device with NoManufacturerID."""

    pass


class TuyaOnOffNM(NoManufacturerCluster, TuyaOnOffMCU):
    """Tuya OnOff cluster with NoManufacturerID."""

    pass


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


class TuyaDoubleSwitchDimmer(TuyaDimmerSwitch):
    """Tuya double channel dimmer device."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
        #                     user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        #                     mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
        #                     manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264,
        #                     maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True,
        #                     *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False, *is_full_function_device=True,
        #                     *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)
        #   "endpoints": {
        #       "1": { "profile_id": 260, "device_type": "0x0051", "in_clusters": [ "0x0000", "0x0004", "0x0005", "0xef00" ], "out_clusters": [ "0x000a", "0x0019" ] }
        #   },
        #  "manufacturer": "_TZE200_e3oitdyu",
        #  "model": "TS0601",
        #  "class": "zigpy.device.Device"
        #  }
        MODELS_INFO: [
            ("_TZE200_e3oitdyu", "TS0601"),
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
                    TuyaLevelControlManufCluster,
                    TuyaOnOffMCU,
                    TuyaInWallLevelControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffMCU,
                    TuyaInWallLevelControl,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaTripleSwitchDimmerGPP(TuyaDimmerSwitch):
    """Tuya double channel dimmer device."""

    signature = {
        # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0, user_descriptor_available=0,
        #                     reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
        #                     mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
        #                     manufacturer_code=4417, maximum_buffer_size=66, maximum_incoming_transfer_size=66, server_mask=10752,
        #                     maximum_outgoing_transfer_size=66, descriptor_capability_field=<DescriptorCapability.NONE: 0>,
        #                     *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
        #                     *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True,
        #                     *is_security_capable=False)",
        # "endpoints": {
        #     "1": {"profile_id": 260, "device_type": "0x0051", "in_clusters": ["0x0000","0x0004","0x0005","0xef00"],"out_clusters": ["0x000a","0x0019"]},
        #     "242": {"profile_id": 41440,"device_type": "0x0061","in_clusters": [],"out_clusters": ["0x0021"]}
        # },
        # "manufacturer": "_TZE200_vm1gyrso",
        # "model": "TS0601",
        # "class": "zigpy.device.Device"
        MODELS_INFO: [
            ("_TZE200_vm1gyrso", "TS0601"),
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
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
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
                    TuyaLevelControlManufCluster,
                    TuyaOnOffNM,
                    TuyaInWallLevelControlNM,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                    TuyaInWallLevelControlNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOffNM,
                    TuyaInWallLevelControlNM,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
