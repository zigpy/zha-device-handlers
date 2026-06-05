"""Third Reality switch devices."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


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
                    CustomPowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [CustomPowerConfigurationCluster.cluster_id],
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
                    CustomPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [CustomPowerConfigurationCluster.cluster_id],
            }
        }
    }


class SwitchPlus(Switch):
    """RealitySwitch Plus (3RSS008Z) device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260
        # device_type=2 device_version=1
        # input_clusters=[0, 4, 3, 6, 5, 1, 2821]
        # output_clusters=[25]>
        MODELS_INFO: [(THIRD_REALITY, "3RSS008Z")],
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
                    Diagnostic.cluster_id,
                    CustomPowerConfigurationCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
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
                    Diagnostic.cluster_id,
                    CustomPowerConfigurationCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
