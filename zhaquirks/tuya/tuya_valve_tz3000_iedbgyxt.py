from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time

MANUFACTURER = "_TZ3000_iedbgyxt"
MODEL = "TS0001"

TUYA_MFG_CLUSTER_E000 = 0xE000
TUYA_MFG_CLUSTER_E001 = 0xE001
GREEN_POWER_CLUSTER_ID = 0x0021
GREEN_POWER_DEVICE_ID_COMBO_BASIC = 0x0061


class TuyaValve_TZ3000_iedbgyxt(CustomDevice):
    """Custom quirk for Tuya water shutoff valve (TS0001 / _TZ3000_iedbgyxt)
    to be recognized as a switch instead of a light.
    Includes definition for Green Power endpoint 242.
    Uses raw IDs for GreenPower cluster and device type to avoid import/attribute issues.
    """

    signature = {
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        "node_descriptor": {
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
                    TUYA_MFG_CLUSTER_E000,
                    TUYA_MFG_CLUSTER_E001,
                ],
                "output_clusters": [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                "profile_id": zgp.PROFILE_ID,  # 0xa1e0 (Green Power Profile ID)
                "device_type": GREEN_POWER_DEVICE_ID_COMBO_BASIC,  # Use raw ID: 0x0061
                "input_clusters": [],
                "output_clusters": [GREEN_POWER_CLUSTER_ID],  # Use raw ID: 0x0021
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
                    TUYA_MFG_CLUSTER_E000,
                    TUYA_MFG_CLUSTER_E001,
                ],
                "output_clusters": [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                "profile_id": zgp.PROFILE_ID,
                "device_type": GREEN_POWER_DEVICE_ID_COMBO_BASIC,  # Use raw ID: 0x0061
                "input_clusters": [],
                "output_clusters": [GREEN_POWER_CLUSTER_ID],  # Use raw ID: 0x0021
            },
        },
    }
