from zigpy.profiles import zha, zgp
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Groups,
    Scenes,
    OnOff,
    Ota,
    Time,
    GreenPowerProxy,
)

from zhaquirks.const import (
    MODELS_INFO,
    ENDPOINTS,
    PROFILE_ID,
    DEVICE_TYPE,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
)


class TS0003USB3Switch(CustomDevice):
    """Custom quirk for TS0003 (_TZ3000_mw1pqqqt) 3-USB switch — without power metering."""

    signature = {
        MODELS_INFO: [("_TZ3000_mw1pqqqt", "TS0003")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0100,
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0003,  # Identify
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0006,  # OnOff
                    0x0702,  # Metering — ignored
                    0x0B04,  # Electrical Measurement — ignored
                    0xE000,  # Tuya proprietary
                    0xE001,  # Tuya proprietary
                ],
                OUTPUT_CLUSTERS: [
                    0x000A,  # Time
                    0x0019,  # OTA
                ],
            },
            2: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0100,
                INPUT_CLUSTERS: [0x0004, 0x0005, 0x0006],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: 0x0100,
                INPUT_CLUSTERS: [0x0004, 0x0005, 0x0006],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [0x0021],  # Green Power Proxy
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic,
                    Identify,
                    Groups,
                    Scenes,
                    OnOff,
                ],
                OUTPUT_CLUSTERS: [
                    Time,
                    Ota,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Groups,
                    Scenes,
                    OnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Groups,
                    Scenes,
                    OnOff,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy],
            },
        }
    }