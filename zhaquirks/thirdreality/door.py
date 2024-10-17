"""Third Reality Door devices."""

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

THIRD_REALITY_DOOR_CLUSTER_ID = 0xFF01
DELAY_OPEN_ATTR_ID = 0x0000

THIRD_REALITY_DOOR_BRIGHTNESS_CLUSTER_ID = 0xFF00
BRIGHTNESS_RED_LIGHT_ATTR_ID = 0x0000
BRIGHTNESS_BLUE_LIGHT_ATTR_ID = 0x0002


class ControlMode(t.uint16_t):
    """Reset mode for not clear and clear."""

    DELAY: int = 10


class BrightnessControlMode(t.uint16_t):
    """ThirdReality Acceleration Cluster."""

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

    class AttributeDefs(BaseAttributeDefs):
        """ThirdReality Acceleration Cluster."""

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
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityDoorCluster.cluster_id,
                    ThirdRealityDoorBrightnessCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
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
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityDoorCluster,
                    ThirdRealityDoorBrightnessCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }
