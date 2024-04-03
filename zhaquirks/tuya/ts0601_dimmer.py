"""Tuya based touch switch."""
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import NoManufacturerCluster, TuyaDimmerSwitch
from zhaquirks.tuya.mcu import (
    TuyaInWallLevelControl,
    TuyaLevelControlManufCluster,
    TuyaOnOff,
    TuyaOnOffNM,
)


class TuyaInWallLevelControlNM(NoManufacturerCluster, TuyaInWallLevelControl):
    """Tuya Level cluster for inwall dimmable device with NoManufacturerID."""


# --- DEVICE SUMMARY ---
# TuyaSingleSwitchDimmer: 0x00, 0x04, 0x05, 0xEF00; 0x000A, 0x0019
# TuyaDoubleSwitchDimmer: 0x00, 0x04, 0x05, 0xEF00; 0x000A, 0x0019
# - Dimmer with Green Power Proxy: Endpoint=242 profile=41440 device_type=0x0061, output_clusters: 0x0021 -
# TuyaSingleSwitchDimmerGP: 0x00, 0x04, 0x05, 0xEF00; 0x000A, 0x0019
# TuyaDoubleSwitchDimmerGP: 0x00, 0x04, 0x05, 0xEF00; 0x000A, 0x0019
# TuyaTripleSwitchDimmerGP: 0x00, 0x04, 0x05, 0xEF00; 0x000A, 0x0019


class TuyaSingleSwitchDimmer(TuyaDimmerSwitch):
    """Tuya touch switch device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_dfxkcots", "TS0601"),
            ("_TZE200_whpb9yts", "TS0601"),
            ("_TZE200_ebwgzdqq", "TS0601"),
            ("_TZE200_9i9dt8is", "TS0601"),
            ("_TZE200_swaamsoy", "TS0601"),
            ("_TZE200_0nauxa0p", "TS0601"),
            ("_TZE200_la2c2uo9", "TS0601"),
            ("_TZE200_1agwnems", "TS0601"),  # TODO: validation pending?
            ("_TZE200_9cxuhakf", "TS0601"),  # Added for Mercator IKUU SSWM-DIMZ Device
            ("_TZE200_a0syesf5", "TS0601"),  # Added for Mercator IKUU SSWRM-ZB
            ("_TZE200_p0gzbqct", "TS0601"),
            ("_TZE200_w4cryh2i", "TS0601"),
            ("_TZE204_dcnsggvz", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaLevelControlManufCluster.cluster_id,
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
                    TuyaOnOff,
                    TuyaInWallLevelControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class TuyaDoubleSwitchDimmer(TuyaDimmerSwitch):
    """Tuya double channel dimmer device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_e3oitdyu", "TS0601"),
            ("_TZE204_bxoo2swd", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaLevelControlManufCluster.cluster_id,
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
                    TuyaOnOff,
                    TuyaInWallLevelControl,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    TuyaOnOff,
                    TuyaInWallLevelControl,
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }


class TuyaSingleSwitchDimmerGP(TuyaDimmerSwitch):
    """Tuya touch switch device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_3p5ydos3", "TS0601"),
            ("_TZE200_ip2akl4w", "TS0601"),
            ("_TZE200_vucankjx", "TS0601"),  # Loratap
            ("_TZE200_y8yjulon", "TS0601"),
            ("_TZE204_n9ctkb6j", "TS0601"),  # For BSEED switch
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0100
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaLevelControlManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
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
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaDoubleSwitchDimmerGP(TuyaDimmerSwitch):
    """Tuya double channel dimmer device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_fjjbhx9d", "TS0601"),
            ("_TZE200_gwkapsoq", "TS0601"),  # Loratap
            ("_TZE204_zenj4lxv", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0100
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaLevelControlManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
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
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }


class TuyaTripleSwitchDimmerGP(TuyaDimmerSwitch):
    """Tuya triple channel dimmer device."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_vm1gyrso", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0100
            # device_version=1
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaLevelControlManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
