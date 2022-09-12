"""FeiBit FNB56 ZSW0x series light switches."""
from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.feibit import FEIBIT


class FNB56_ZSW01LX20(CustomDevice):
    """FeiBit FBN56-ZSW01LX2.0 1 Gang Light Switch."""

    # "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.Router: 1>,
    # complex_descriptor_available=0, user_descriptor_available=0, reserved=0,
    # aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    # mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
    # manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90,
    # server_mask=10752, maximum_outgoing_transfer_size=90,
    # descriptor_capability_field=<DescriptorCapability.NONE: 0>,
    # *allocate_address=True, *is_alternate_pan_coordinator=False,
    # *is_coordinator=False, *is_end_device=False, *is_full_function_device=True,
    # *is_mains_powered=True, *is_receiver_on_when_idle=True, *is_router=True,
    # *is_security_capable=False)",
    signature = {
        MODELS_INFO: [(FEIBIT, "FNB56-ZSW01LX2.0")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 4096]
            # output_clusters=[25]>
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 4096]
            # output_clusters=[25]>
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class FNB56_ZSW02LX20(CustomDevice):
    """FeiBit FBN56-ZSW02LX2.0 2 Gang Light Switch."""

    # "NodeDescriptor(logical_type=<LogicalType.Router: 1>,
    # complex_descriptor_available=0, user_descriptor_available=0,
    # reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    # mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
    # manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90,
    # server_mask=10752, maximum_outgoing_transfer_size=90,
    # descriptor_capability_field=<DescriptorCapability.NONE: 0>,
    # *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False,
    # *is_end_device=False, *is_full_function_device=True, *is_mains_powered=True,
    # *is_receiver_on_when_idle=True, *is_router=True, *is_security_capable=False)",
    signature = {
        MODELS_INFO: [(FEIBIT, "FNB56-ZSW02LX2.0")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 4096]
            # output_clusters=[25]>
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=12 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8]
            # output_clusters=[25]>
            12: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 4096]
            # output_clusters=[25]>
            11: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=12 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[25]>
            12: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class FNB56_ZSW03LX20(CustomDevice):
    """FeiBit FBN56-ZSW03LX2.0 3 Gang Light Switch."""

    # "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
    # user_descriptor_available=0, reserved=0, aps_flags=0,
    # frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    # mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
    # manufacturer_code=4478, maximum_buffer_size=127, maximum_incoming_transfer_size=90,
    # server_mask=10752, maximum_outgoing_transfer_size=90,
    # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True,
    # *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
    # *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True,
    # *is_router=True, *is_security_capable=False)",
    signature = {
        MODELS_INFO: [(FEIBIT, "FNB56-ZSW03LX2.0")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 4096]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8]
            # output_clusters=[25]>
            2: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8]
            # output_clusters=[25]>
            3: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6, 4096]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[25]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=49246 device_type=0x0000
            # device_version=2 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[25]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
