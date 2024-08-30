"""Third Reality WaterLeak devices."""

from typing import Final  # noqa: I001

from zigpy.profiles import zha # type: ignore
from zigpy.quirks import CustomDevice # type: ignore
import zigpy.types as t # type: ignore
from zigpy.zcl.clusters.general import Basic, OnOff, Ota, PowerConfiguration # type: ignore
from zigpy.zcl.clusters.security import IasZone # type: ignore
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef # type: ignore

from zhaquirks import CustomCluster  # type: ignore
from zhaquirks.const import ( # type: ignore
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY # type: ignore

THIRD_REALITY_WATERLEAK_CLUSTER_ID = 0xFF01
THIRD_REALITY_WATERLEAK_BRIGHTNESS_CLUSTER_ID = 0xFF00
DELAY_OPEN_ATTR_ID = 0x0000

class ControlMode(t.uint8_t):  # noqa: D101

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
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityWaterLeakCluster.cluster_id,  # 0xFF01
                    ThirdRealityWaterLeakBrightnessCluster.cluster_id,   #0xFF00
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
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
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    IasZone.cluster_id,  # 0x0500
                    ThirdRealityWaterLeakCluster,  # 0xFF01
                    ThirdRealityWaterLeakBrightnessCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                    OnOff.cluster_id,
                ],
            },
        },
    }
