"""Third Reality blind devices."""

from typing import Final
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, OnOff
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFFF1


class ControlMode(t.uint8_t):
    """Reset mode for not clear and clear."""

    NOT = 0
    CLEAR = 1


class ThirdRealityBlindCluster(CustomCluster):
    """ThirdReality Blind Cluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID


    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        infrared_off: Final = ZCLAttributeDef(
            id=0x0000,
            type=ControlMode,
            is_manufacturer_specific=True,
        )


class blind(CustomDevice):
    """ThirdReality blind device."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RSB015BZ")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    WindowCovering.cluster_id,
                    OnOff.cluster_id,  
                    ThirdRealityBlindCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,  
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    WindowCovering.cluster_id,
                    OnOff.cluster_id,  
                    ThirdRealityBlindCluster,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,  
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                ],
            }
        },
    }
