"""Lellki WP33 Power Strips."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Scenes

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class e220_kr4n0z0_ha(CustomDevice):
    """Lellki WP33 E220_KR4N0Z0_HA 4 controlled AC + 2 uncontrolled USB Power Strip."""

    # "NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
    # user_descriptor_available=0, reserved=0, aps_flags=0,
    # frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    # mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
    # manufacturer_code=0, maximum_buffer_size=80, maximum_incoming_transfer_size=160,
    # server_mask=0, maximum_outgoing_transfer_size=160,
    # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True,
    # *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
    # *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True,
    # *is_router=True, *is_security_capable=False)",
    signature = {
        MODELS_INFO: [(" ", "E220-KR4N0Z0-HA")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0100
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0x0100
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
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
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=0x0100
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
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
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0x0100
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0x0051
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=0x0051
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
            # <SimpleDescriptor endpoint=4 profile=260 device_type=0x0051
            # device_version=0 input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[0]>
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            },
        },
    }
