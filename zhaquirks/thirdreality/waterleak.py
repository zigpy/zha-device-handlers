"""Third Reality WaterLeak devices."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration
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

THIRD_REALITY_WATERLEAK_CLUSTER_ID = 0xFF01
THIRD_REALITY_WATERLEAK_BRIGHTNESS_CLUSTER_ID = 0xFF00
DELAY_OPEN_ATTR_ID = 0x0000


class ControlMode(t.uint8_t):
    """ThirdReality Acceleration Cluster."""
    pass


class ThirdRealityWaterLeakCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_WATERLEAK_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        siren_on_off: Final = ZCLAttributeDef(
            id=0x0010,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

        siren_mintues: Final = ZCLAttributeDef(
            id=0x0011,
            type=ControlMode,
            is_manufacturer_specific=True,
        )


class ThirdRealityWaterLeakBrightnessCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_WATERLEAK_BRIGHTNESS_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        redlight: Final = ZCLAttributeDef(
            id=0x0000,
            type=ControlMode,
            is_manufacturer_specific=True,
        )

        bluelight: Final = ZCLAttributeDef(
            id=0x0002,
            type=ControlMode,
            is_manufacturer_specific=True,
        )


class WaterLeak(CustomDevice):
    """ThirdReality WaterLeak device."""

    signature = {
        MODELS_INFO: [
            (THIRD_REALITY, "3RWS18BZ"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityWaterLeakCluster.cluster_id,
                    ThirdRealityWaterLeakBrightnessCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    OnOff.cluster_id,
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
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityWaterLeakCluster,
                    ThirdRealityWaterLeakBrightnessCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        },
    }
