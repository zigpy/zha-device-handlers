"""Tuya RGB+CCT LED controller misidentified as TS0502B (CCT-only).

Some Tuya RGB+CCT LED strip controllers (e.g. _TZB210_nfzrlz29) advertise the
TS0502B model identifier but actually support full RGB+CCT lighting. The default
ZHA discovery treats them as Color Temperature lights only, hiding the RGB
color picker in the UI.

This quirk overrides the device type to EXTENDED_COLOR_LIGHT and forces
color_capabilities to expose Hue/Saturation, XY, EnhancedHue, ColorLoop and
ColorTemperature.
"""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
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


class TuyaRGBCCTColorCluster(CustomCluster, Color):
    """Color cluster advertising HS + EnhancedHue + ColorLoop + XY + CCT capabilities."""

    _CONSTANT_ATTRIBUTES = {
        # color_capabilities (0x400A): bit 0=HS, 1=EnhancedHue, 2=ColorLoop, 3=XY, 4=CCT
        # 0x1F = all five capabilities supported
        0x400A: 0x1F,
    }


class TS0502BRGBCCTController(CustomDevice):
    """Tuya RGB+CCT LED controller advertised as TS0502B."""

    signature = {
        MODELS_INFO: [
            ("_TZB210_nfzrlz29", "TS0502B"),
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
                    0xEF00,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[] output_clusters=[33]>
            242: {
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
                DEVICE_TYPE: zha.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TuyaRGBCCTColorCluster,
                    LightLink.cluster_id,
                    0xEF00,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
