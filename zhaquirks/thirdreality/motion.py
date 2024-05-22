"""Third Reality Motion devices."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone
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

THIRD_REALITY_MOTION_BRIGHTNESS_CLUSTER_ID = 0xFF00
THIRD_REALITY_MOTION_DELAY_CLUSTER_ID = 0xFF01

class ControlMode(t.uint8_t):  # noqa: D101

    pass


class ThirdRealityMotionCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_MOTION_DELAY_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

    detected_to_undetected_delay: Final = ZCLAttributeDef(
        id=0x0001,
        type=ControlMode,
        is_manufacturer_specific=True,
    )



class ThirdRealityMotionBrightnessCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_MOTION_BRIGHTNESS_CLUSTER_ID
    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        red_light: Final = ZCLAttributeDef(
            id=0x0000,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

        blue_light: Final = ZCLAttributeDef(
            id=0x0002,
            type=ControlMode,
            is_manufacturer_specific=True,
        )


class Motion(CustomDevice):
    """ThirdReality Motion device."""

    signature = {
        MODELS_INFO: [
            (THIRD_REALITY, "3RMS16BZ"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityMotionCluster.cluster_id,  # 0xFF01
                    ThirdRealityMotionBrightnessCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityMotionCluster,  # 0xFF01
                    ThirdRealityMotionBrightnessCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                ],
            },
        },
    }
