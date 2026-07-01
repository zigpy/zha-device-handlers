"""Module for Legrand dimmers."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
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

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import (
    LEGRAND,
    MANUFACTURER_SPECIFIC_CLUSTER_ID,
    DeviceMode,
    LegrandCluster,
    LegrandIdentify,
    LegrandPowerConfigurationCluster,
)


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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
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
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.COMBO_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


(
    QuirkBuilder(f" {LEGRAND}", " Dimmer switch with neutral")
    .replaces(LegrandCluster)
    .replaces(LegrandIdentify)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=BinaryInput.cluster_id)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.device_mode.name,
        cluster_id=LegrandCluster.cluster_id,
        on_value=DeviceMode.Dimmer_On,
        off_value=DeviceMode.Dimmer_Off,
        translation_key="dimmer_mode",
        fallback_name="Dimmer mode",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_dark.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_off",
        fallback_name="Turn on LED when off",
    )
    .switch(
        attribute_name=LegrandCluster.AttributeDefs.led_on.name,
        cluster_id=LegrandCluster.cluster_id,
        translation_key="turn_on_led_when_on",
        fallback_name="Turn on LED when on",
    )
    .add_to_registry()
)


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
