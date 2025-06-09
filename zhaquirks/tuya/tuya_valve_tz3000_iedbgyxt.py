"""Quirk for Tuya TS0001 (_TZ3000_iedbgyxt) water shutoff valve."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)

MANUFACTURER = "_TZ3000_iedbgyxt"
MODEL = "TS0001"

GREEN_POWER_CLUSTER_ID = 0x0021
GREEN_POWER_DEVICE_ID_COMBO_BASIC = 0x0061


class TuyaManufClusterE000(CustomCluster):
    """Tuya manufacturer specific cluster 0xE000."""

    cluster_id = 0xE000
    name = "Tuya Manufacturer Specific E000"
    ep_attribute = "tuya_manufacturer_specific_e000"


class TuyaManufClusterE001(CustomCluster):
    """Tuya manufacturer specific cluster 0xE001."""

    cluster_id = 0xE001
    name = "Tuya Manufacturer Specific E001"
    ep_attribute = "tuya_manufacturer_specific_e001"


class TuyaValve_TZ3000_iedbgyxt(CustomDevice):
    """Custom quirk for Tuya water shutoff valve (TS0001 / _TZ3000_iedbgyxt).

    Recognizes the device as a switch instead of a light.
    Includes definition for Green Power endpoint 242.
    """

    signature = {
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        "node_desc": {
            "logical_type": 1,
            "mac_capability_flags": 142,
        },
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.ON_OFF_LIGHT,  # 0x0100 (Original)
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaManufClusterE000.cluster_id,  # Use the new class
                    TuyaManufClusterE001.cluster_id,  # Use the new class
                ],
                "output_clusters": [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                "profile_id": zgp.PROFILE_ID,
                "device_type": GREEN_POWER_DEVICE_ID_COMBO_BASIC,
                "input_clusters": [],
                "output_clusters": [
                    GREEN_POWER_CLUSTER_ID,
                ],
            },
        },
    }

    replacement = {
        "endpoints": {
            1: {
                "profile_id": zha.PROFILE_ID,
                "device_type": zha.DeviceType.ON_OFF_OUTPUT,  # 0x0002
                "input_clusters": [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TuyaManufClusterE000,  # Use the new class
                    TuyaManufClusterE001,  # Use the new class
                ],
                "output_clusters": [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                "profile_id": zgp.PROFILE_ID,
                "device_type": GREEN_POWER_DEVICE_ID_COMBO_BASIC,
                "input_clusters": [],
                "output_clusters": [
                    GREEN_POWER_CLUSTER_ID,
                ],
            },
        },
    }