"""Third Reality Door devices."""

from typing import Final

from zigpy.profiles import zha  # type: ignore
from zigpy.quirks import CustomDevice  # type: ignore
import zigpy.types as t  # type: ignore
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration  # type: ignore
from zigpy.zcl.clusters.security import IasZone  # type: ignore
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef  # type: ignore

from zhaquirks import CustomCluster  # type: ignore
from zhaquirks.const import (  # type: ignore
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY  # type: ignore

THIRD_REALITY_DOOR_CLUSTER_ID = 0xFF01
DELAY_OPEN_ATTR_ID = 0x0000

THIRD_REALITY_DOOR_BRIGHTNESS_CLUSTER_ID = 0xFF00
BRIGHTNESS_RED_LIGHT_ATTR_ID = 0x0000
BRIGHTNESS_BLUE_LIGHT_ATTR_ID = 0x0002


class ControlMode(t.uint16_t):
    """Reset mode for not clear and clear."""

    DELAY: int = 10

class BrightnessControlMode(t.uint16_t):  # noqa: D101

    pass


class ThirdRealityDoorCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_DOOR_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        delay_open: Final = ZCLAttributeDef(
            id=DELAY_OPEN_ATTR_ID,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

class ThirdRealityDoorBrightnessCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_DOOR_BRIGHTNESS_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):  # noqa: D106
        red_light: Final = ZCLAttributeDef(
            id=BRIGHTNESS_RED_LIGHT_ATTR_ID,
            type=BrightnessControlMode,
            is_manufacturer_specific=True,
        )

        blue_light: Final = ZCLAttributeDef(
            id=BRIGHTNESS_BLUE_LIGHT_ATTR_ID,
            type=BrightnessControlMode,
            is_manufacturer_specific=True,
        )

class Door(CustomDevice):
    """ThirdReality Door device."""

    signature = {
        MODELS_INFO: [
            (THIRD_REALITY, "3RDS17BZ"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityDoorCluster.cluster_id,  # 0xFF01
                    ThirdRealityDoorBrightnessCluster.cluster_id
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
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityDoorCluster,  # 0xFF01
                    ThirdRealityDoorBrightnessCluster
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                ],
            },
        },
    }
