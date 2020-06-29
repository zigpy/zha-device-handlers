"""Philips RWL020 device."""

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
)

from . import HUE_REMOTE_DEVICE_TRIGGERS, PhilipsBasicCluster, PhilipsRemoteCluster
from ..const import DEVICE_TYPE, ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS, PROFILE_ID

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class PhilipsRWL020(CustomDevice):
    """Philips RWL020 device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=49246 device_type=2080
        #  device_version=2
        #  input_clusters=[0]
        #  output_clusters=[0, 3, 4, 6, 8]>
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
                    64512,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        }
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
