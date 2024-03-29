"""Third Reality Plug devices."""

from typing import Final

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
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

THIRD_REALITY_PLUG_CLUSTER_ID = 0xFF03
RESET_SUMMATION_DELIVERED_ATTR_ID = 0x0000


class ControlMode(t.uint8_t):
    """Reset mode for not clear and clear."""

    NOT = 0
    CLEAR = 1


class ThirdRealityPlugCluster(CustomCluster):
    """ThirdReality Acceleration Cluster."""

    cluster_id = THIRD_REALITY_PLUG_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        reset_summation_delivered: Final = ZCLAttributeDef(
            id=RESET_SUMMATION_DELIVERED_ATTR_ID,
            type=ControlMode,
            is_manufacturer_specific=True,
        )


class Plug(CustomDevice):
    """ThirdReality Plug device."""

    signature = {
        MODELS_INFO: [
            (THIRD_REALITY, "3RSP019BZ"),
            (THIRD_REALITY, "3RSP02028BZ"),
            (THIRD_REALITY, "3RSPE01044BZ"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    Metering.cluster_id,  # 0x0702
                    ElectricalMeasurement.cluster_id,  # 0x0b04
                    ThirdRealityPlugCluster.cluster_id,  # 0xFF03
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    Metering.cluster_id,  # 0x0702
                    ElectricalMeasurement.cluster_id,  # 0x0b04
                    ThirdRealityPlugCluster,  # 0xFF03
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,  # 0x0019
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        },
    }
