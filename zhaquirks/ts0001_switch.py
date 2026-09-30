"""ZHA quirk for Click Smart+ 13A Fused Connection Unit."""

from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl import Cluster
from zigpy.zcl.clusters.general import Basic, Groups, OnOff, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class ClickSmartFusedSpur(CustomDevice):
    """Quirk for Click Smart+ Fused Connection Unit (CMA30651 / TS0001).

    Forces the device to present as a Switch instead of a Light.
    """

    signature: Dict[str, Dict] = {
        MODELS_INFO: [("_TZ3210_fhx7lk3d", "TS0001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    0xEF00,  # Tuya Manufacturer Cluster
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement: Dict[str, Dict] = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    0xEF00,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }