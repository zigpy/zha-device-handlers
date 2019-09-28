"""Third Reality switch devices."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
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

from . import THIRD_REALITY
from .. import PowerConfigurationCluster


class Switch(CustomDevice):
    """3RSS008Z device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260
        # device_type=2 device_version=1
        # input_clusters=[0, 4, 3, 6, 5, 25, 1]
        # output_clusters=[1]>
        MODELS_INFO: [(THIRD_REALITY, "3RSS007Z"), (THIRD_REALITY, "3RSS008Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    PowerConfiguration.cluster_id,
                ],
                OUTPUT_CLUSTERS: [PowerConfiguration.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    PowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [PowerConfiguration.cluster_id],
            }
        }
    }
