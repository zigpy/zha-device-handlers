"""Philips first generation RWL devices."""

from zigpy.profiles import zha, zll
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.philips import (
    HUE_REMOTE_DEVICE_TRIGGERS,
    PHILIPS,
    SIGNIFY,
    PhilipsBasicCluster,
    PhilipsRemoteCluster,
)

DEVICE_SPECIFIC_UNKNOWN = 64512


class PhilipsRWLFirstGen(CustomDevice):
    """Philips updated RWL020 and RWL021 devices."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2096
        #  device_version=2
        #  input_clusters=[0]
        #  output_clusters=[0, 3, 4, 6, 8, 5]>
        MODELS_INFO: [
            (PHILIPS, "RWL020"),
            (SIGNIFY, "RWL020"),
            (PHILIPS, "RWL021"),
            (SIGNIFY, "RWL021"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.SCENE_CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 15, 64512]
            #  output_clusters=[25]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                ],
            },
            2: {
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PhilipsRemoteCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
    }

    device_automation_triggers = HUE_REMOTE_DEVICE_TRIGGERS


class PhilipsRWLFirstGen2(CustomDevice):
    """Philips older RWL020 and RWL021 devices."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2080
        #  device_version=2
        #  input_clusters=[0]
        #  output_clusters=[0, 3, 4, 6, 8]>
        MODELS_INFO: [
            (PHILIPS, "RWL020"),
            (SIGNIFY, "RWL020"),
            (PHILIPS, "RWL021"),
            (SIGNIFY, "RWL021"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.CONTROLLER,
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 15, 64512]
            #  output_clusters=[25]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    DEVICE_SPECIFIC_UNKNOWN,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [Basic.cluster_id],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                ],
            },
            2: {
                INPUT_CLUSTERS: [
                    PhilipsBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PhilipsRemoteCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
    }

    device_automation_triggers = HUE_REMOTE_DEVICE_TRIGGERS
