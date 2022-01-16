"""zigfred device handler."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

# Siglis specific clusters
ZIGFRED_CLUSTER_0345_ID = 0x0345

# Siglis Cluster 0x0345 Implementation
class Zigfred0345Cluster(CustomCluster):
    """Siglis manufacturer specific cluster 837."""

    name = "Siglis Manufacturer Specific"
    cluster_id = ZIGFRED_CLUSTER_0345_ID


class ZigfredUnoColorCluster(CustomCluster, Color):
    """zigfred uno Color custom cluster."""

    # Set correct capabilities to ct, xy, hs
    # zigfred uno does not correctly report this attribute (comes back as None in Home Assistant)
    _CONSTANT_ATTRIBUTES = {0x400A: 0b01000}


class ZigfredUno(CustomDevice):
    """zigfred uno device handler."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("Siglis", "zigfred uno")],
        ENDPOINTS: {
            5: {
                # Front Module LED
                # SizePrefixedSimpleDescriptor(endpoint=5,
                # profile=260, device_type=258,
                # device_version=1,
                # input_clusters=[0, 3, 4, 5, 6, 8, 768, 837],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    Zigfred0345Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            6: {
                # Relay
                # SizePrefixedSimpleDescriptor(endpoint=6,
                # profile=260, device_type=256,
                # device_version=1,
                # input_clusters=[0, 3, 4, 5, 6],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            7: {
                # Relay
                # SizePrefixedSimpleDescriptor(endpoint=7,
                # profile=260, device_type=257,
                # device_version=1,
                # input_clusters=[0, 3, 5, 4, 6, 8],
                # output_clusters=[])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                # SizePrefixedSimpleDescriptor(endpoint=242,
                # profile=41440, device_type=97,
                # device_version=0,
                # input_clusters=[],
                # output_clusters=[33])
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        MODELS_INFO: [("Siglis", "zigfred uno")],
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ZigfredUnoColorCluster,
                    Zigfred0345Cluster,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
            6: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            7: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
