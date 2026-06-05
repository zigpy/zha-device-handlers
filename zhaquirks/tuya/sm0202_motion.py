"""Device handler for Tuya LH-961ZB motion sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import MotionWithReset
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60


class SM0202Motion(CustomDevice):
    """Quirk for LH-961ZB motion sensor."""

    signature = {
        # "endpoint": 1
        # "profile_id": 260,
        # "device_type": "0x0402",
        # "in_clusters": ["0x0000","0x0001","0x0003", "0x0500", "0xeeff"],
        # "out_clusters": ["0x0019"]
        MODELS_INFO: [("_TYZB01_z2umiwvq", "SM0202")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    0xEEFF,  # Unknown
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
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
                    Identify.cluster_id,
                    MotionCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
