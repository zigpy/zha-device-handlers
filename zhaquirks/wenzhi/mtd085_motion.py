"""Wenzhi/LeapMMW MTD085-ZB mmWave radar presence sensor.

This device operates in basic IAS Zone mode when paired directly with ZHA.
The advanced features (illuminance, distance measurement, configuration parameters)
require the Tuya MCU cluster (0xEF00) which is not exposed in this mode.

Current functionality:
- Motion detection via IAS Zone (binary_sensor.motion)
- Occupancy clear when leaving the room
- Basic device info
- Uses Tuya enchantment spell to initialize proper occupancy reporting
- Periodic reporting configured to detect device disconnection faster
"""

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
from zhaquirks.tuya import EnchantedDevice


class WenzhiMTD085_ZB(EnchantedDevice):
    """Wenzhi MTD085-ZB 24GHz mmWave radar presence sensor.

    Basic IAS Zone motion sensor mode.
    Uses Tuya enchantment spell to report occupancy state changes.

    Manufacturer: _TZ321C_fkzihax8 / _TZ321C_4slreunp
    Model: TS0225
    """

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration including IAS Zone reporting."""
        # First apply the Tuya enchantment spell from parent class
        await super().apply_custom_configuration(*args, **kwargs)

        try:
            # Configure periodic reporting on IAS Zone cluster
            # This ensures the device reports regularly to maintain availability
            # Home Assistant marks devices unavailable after missing several reports
            # Using shorter intervals for faster disconnection detection
            ias_zone_cluster = self.endpoints[1].in_clusters[IasZone.cluster_id]
            await ias_zone_cluster.bind()
            await ias_zone_cluster.configure_reporting(
                IasZone.AttributeDefs.zone_status.id,
                min_interval=10,  # Report at least every 10 seconds on state changes
                max_interval=300,  # Report at most every 5 minutes even if no change
                reportable_change=1,  # Report on any zone status change
            )
        except Exception as ex:
            # Log the error but continue - device may not support reporting config
            self.debug("Failed to configure IAS Zone reporting: %s", ex)

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
