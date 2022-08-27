"""Quirk for shutters."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import (
    Diagnostic,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.schneiderelectric import (
    SE_MANUF_NAME,
    SESpecificCluster,
    SEWindowCovering,
)


class NHPBShutter1(CustomDevice):
    """NHPB/SHUTTER/1 from Schneider Electric."""

    # NodeDescriptor(logical_type=<LogicalType.Router: 1>, complex_descriptor_available=0,
    # user_descriptor_available=0, reserved=0, aps_flags=0,
    # frequency_band=<FrequencyBand.Freq2400MHz: 8>,
    # mac_capability_flags=<MACCapabilityFlags.AllocateAddress|RxOnWhenIdle|MainsPowered|FullFunctionDevice: 142>,
    # manufacturer_code=4190, maximum_buffer_size=82, maximum_incoming_transfer_size=82,
    # server_mask=11264, maximum_outgoing_transfer_size=82,
    # descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True,
    # *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=False,
    # *is_full_function_device=True, *is_mains_powered=True, *is_receiver_on_when_idle=True,
    # *is_router=True, *is_security_capable=False)
    signature = {
        MODELS_INFO: [
            (SE_MANUF_NAME, "NHPB/SHUTTER/1"),
        ],
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,  # 0x0202
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    WindowCovering.cluster_id,  # 0x0102
                    Diagnostic.cluster_id,  # 0x0B05
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 0x0019
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,  # 0x0104
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Diagnostic.cluster_id,  # 0x0B05
                    SESpecificCluster.cluster_id,  # 0xff17
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    WindowCovering.cluster_id,  # 0x0102
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],  # 0x0021
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,  # 0x0202
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    WindowCovering.cluster_id,  # 0x0102
                    Diagnostic.cluster_id,  # 0x0B05
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],  # 0x0019
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,  # 0x0104
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Diagnostic.cluster_id,  # 0x0B05
                    SESpecificCluster,  # 0xff17
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    SEWindowCovering,  # 0x0102
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],  # 0x0021
            },
        }
    }
