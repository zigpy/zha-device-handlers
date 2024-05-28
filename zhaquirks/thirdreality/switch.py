"""Third Reality switch devices."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, PowerConfiguration
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
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
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zhaquirks import CustomCluster
import zigpy.types as t

class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""
    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0

	
	
THIRD_REALITY_SWITCH_CLUSTER_ID = 0xFF02
THIRD_REALITY_SWITCH_BRIGHTNESS_CLUSTER_ID = 0xFF00
	
class ThirdRealitySwitchCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_SWITCH_CLUSTER_ID

    attributes = {
      0x0002: ("back_off", t.uint64_t, True),
      0x0001: ("back_on", t.uint64_t, True),
    }

class ThirdRealitySwitchBrightnessCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_SWITCH_BRIGHTNESS_CLUSTER_ID
    attributes = {
      0x0000: ("red_light", t.uint8_t, True),
      0x0002: ("blue_light", t.uint8_t, True),
    }

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
                    ThirdRealitySwitchCluster.cluster_id,  
                    ThirdRealitySwitchBrightnessCluster.cluster_id,
                    PowerConfiguration.cluster_id,      
                    OnOff.cluster_id,
                ],
                 OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    OnOff.cluster_id,
                ],
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
                    ThirdRealitySwitchCluster,  
                    ThirdRealitySwitchBrightnessCluster,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id, 
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    OnOff.cluster_id,
                ],
            }
        }
    }


class Switch_Plus(CustomDevice):
    """RealitySwitch Plus (3RSS009Z) device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260
        # device_type=2 device_version=1
        # input_clusters=[0, 4, 3, 6, 5, 1, 2821]
        # output_clusters=[25]>
        MODELS_INFO: [
            (THIRD_REALITY, "3RSS009Z")
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ThirdRealitySwitchCluster.cluster_id,  
                    ThirdRealitySwitchBrightnessCluster.cluster_id,
                    PowerConfiguration.cluster_id,      
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    ThirdRealitySwitchCluster,  
                    ThirdRealitySwitchBrightnessCluster,
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id, 
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    Ota.cluster_id,
                ],
            },
        }
    }
