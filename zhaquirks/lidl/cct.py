"""Quirk for LIDL CCT bulb."""
from zigpy.profiles import zha
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


class LidlCCTColorCluster(CustomCluster, Color):
    """Lidl CCT Lighting custom cluster."""

    # Remove RGB color wheel for CCT Lighting: only expose color temperature
    # LIDL bulbs do not correctly report this attribute (comes back as None in Home Assistant)
    _CONSTANT_ATTRIBUTES = {0x400A: 16}


class CCTLight(CustomDevice):
    """Lidl CCT Lighting device."""

    signature = {
        MODELS_INFO: [
            ("_TZ3000_49qchf10", "TS0502A"),
            ("_TZ3000_oborybow", "TS0502A"),
            ("_TZ3000_9evm3otq", "TS0502A"),
            ("_TZ3000_rylaozuc", "TS0502A"),
            ("_TZ3000_el5kt5im", "TS0502A"),
            ("_TZ3000_oh7jddmx", "TS0502A"),
            ("_TZ3000_8uaoilu9", "TS0502A"),
        ],
        ENDPOINTS: {
            1: {
                # <SimpleDescriptor endpoint=1 profile=260 device_type=268
                # device_version=1
                # input_clusters=[0, 3, 4, 5, 6, 8, 768, 4096]
                # output_clusters=[10, 25]
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
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
                # input_clusters=[]
                # output_clusters=[33]
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
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LidlCCTColorCluster,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
