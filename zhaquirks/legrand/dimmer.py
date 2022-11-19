"""Device handler for Legrand Dimmer switch w/o neutral."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import LEGRAND

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class LegrandCluster(CustomCluster, ManufacturerSpecificCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"
    attributes = {
        0x0000: ("dimmer", t.data16, True),
        0x0001: ("led_dark", t.Bool, True),
        0x0002: ("led_on", t.Bool, True),
    }


class LegrandPowerConfigurationCluster(PowerConfigurationCluster):
    """PowerConfiguration conversor 'V --> %' for Legrand devices."""

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


class DimmerWithoutNeutral(CustomDevice):
    """Dimmer switch w/o neutral."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 64513, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, LegrandCluster, Ota.cluster_id],
            }
        }
    }


class DimmerWithoutNeutral2(DimmerWithoutNeutral):
    """Dimmer switch w/o neutral 2."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 64513, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }


class DimmerWithoutNeutral3(CustomDevice):
    """Dimmer switch w/o neutral (at least for firmware 0x2e and above)."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 8, 15, 64513]
        # output_clusters=[0, 5, 6, 25, 64513]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0066,
                INPUT_CLUSTERS: [0x0021],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    # Some devices with firmware 0x39 have Ballast cluster,
                    # but some of them don't. But in any case Ballast works,
                    # if we add it here.
                    Ballast.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandCluster,
                    Ota.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            # Green Power End Point
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0066,  # GP Combo Minimum
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class DimmerWithoutNeutralAndBallast(CustomDevice):
    """Dimmer switch w/o neutral (at least for firmware 0x39)."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 5, 6, 8, 15, 769, 64513]
        # output_clusters=[0, 5, 6, 25, 64513]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch w/o neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    Ballast.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0066,
                INPUT_CLUSTERS: [0x0021],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    Ballast.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandCluster,
                    Ota.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            # Green Power End Point
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0066,  # GP Combo Minimum
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class DimmerWithNeutral(DimmerWithoutNeutral):
    """Dimmer switch with neutral."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 25, 64513]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch with neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0066,
                INPUT_CLUSTERS: [0x0021],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }


class DimmerWithNeutral2(CustomDevice):
    """Dimmer switch with neutral."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 64513, 5, 25]>
        MODELS_INFO: [(f" {LEGRAND}", " Dimmer switch with neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0066,
                INPUT_CLUSTERS: [0x0021],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandCluster,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }


class RemoteDimmer(CustomDevice):
    """Remote dimmer ."""

    signature = {
        MODELS_INFO: [(f" {LEGRAND}", " Remote dimmer switch")],
        ENDPOINTS: {
            1: {
                # "profile_id": 260,
                # "device_type": "0x0104",
                # "in_clusters": ["0x0000","0x0001","0x0003","0x000f","0x0020","0xfc01"],
                # "out_clusters": ["0x0000","0x0003","0x0006","0x0008","0x0019","0xfc01"]
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    LegrandCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandPowerConfigurationCluster,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster,
                ],
            }
        }
    }
