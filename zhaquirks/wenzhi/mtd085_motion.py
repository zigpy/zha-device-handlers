"""Wenzhi/LeapMMW MTD085-ZB mmWave radar presence sensor.

This device operates in basic IAS Zone mode when paired directly with ZHA.
The advanced features (illuminance, distance measurement, configuration parameters)
require the Tuya MCU cluster (0xEF00) which is not exposed in this mode.

Current functionality:
- Motion detection via IAS Zone (binary_sensor.motion)
- Occupancy clear when leaving the room
- Basic device info
"""

from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Scenes
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class WenzhiMTD085_ZB(CustomDevice):
    """Wenzhi MTD085-ZB 24GHz mmWave radar presence sensor.

    Basic IAS Zone motion sensor mode. Requires "magic packet" initialization
    to properly report occupancy state changes.

    Manufacturer: _TZ321C_fkzihax8 / _TZ321C_4slreunp
    Model: TS0225
    """

    async def apply_custom_configuration(self, *args, **kwargs):
        """Send magic packet to initialize proper IAS Zone reporting."""
        try:
            # Read Basic cluster attributes to initialize device
            # This enables proper occupancy state reporting
            basic_cluster = self.endpoints[1].in_clusters[Basic.cluster_id]
            await basic_cluster.read_attributes(
                [0, 1, 4, 5, 7, 0xFFFE],
                allow_cache=False,
            )
        except Exception:
            # Ignore errors - device may not support all attributes
            pass

        await super().apply_custom_configuration(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            ("_TZ321C_fkzihax8", "TS0225"),
            ("_TZ321C_4slreunp", "TS0225"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
            # device_version=0
            # input_clusters=[0, 4, 5, 1280]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: 260,  # ZHA profile
                DEVICE_TYPE: 0x0402,  # IAS_ZONE = 1026 decimal = 0x0402 hex
                INPUT_CLUSTERS: [
                    0x0000,  # Basic
                    0x0004,  # Groups
                    0x0005,  # Scenes
                    0x0500,  # IasZone
                ],
                OUTPUT_CLUSTERS: [
                    0x000A,  # Time
                    0x0019,  # OTA
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,  # Green Power profile
                DEVICE_TYPE: 0x0061,  # Proxy Basic
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    0x0021,  # Green Power
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: 260,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    0x000A,  # Time
                    0x0019,  # OTA
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    0x0021,
                ],
            },
        },
    }
