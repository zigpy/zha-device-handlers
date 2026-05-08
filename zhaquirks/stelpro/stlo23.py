"""ZHA Quirk (v2) for Stello STLO-23 water heater control.

Adds manufacturer attributes:
- 0x0001: uint8_t = 50, maybe high temp Celsius (rwp)
- 0x0003: uint16_t = 1200 ??? (rwp)
- 0x0005: uint8_t Current temperature, Celsius (rp)
- 0x0006: uint8_t = 1 ??? (rwp)
- 0x0007: uint8_t = 49, maybe low temp Celsius (rwp)
"""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import UnitOfTemperature
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

STELLO_MANUFACTURER_ID = 4759

# ──────────────────────────────────────────────────────────────
# Custom Temperature cluster
# ──────────────────────────────────────────────────────────────


class STLO23TemperatureCluster(CustomCluster):
    """Custom Stello temperature cluster."""

    manufacturer_id_override = STELLO_MANUFACTURER_ID
    cluster_id = 0xFC02
    ep_attribute = "stlo23_temperature_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Vendor-specific attributes.

        - 0x0001: uint8_t = 50, maybe high temp Celsius (rwp)
        - 0x0003: uint16_t = 1200 ??? (rwp)
        - 0x0005: uint8_t Current temperature, Celsius (rp)
        - 0x0006: uint8_t = 1 ??? (rwp)
        - 0x0007: uint8_t = 49, maybe low temp Celsius (rwp)

        If I was to guess, I would say that 0x0001 and 0x0007 are
        the high and low temperature triggers. 0x0003 could be a
        time value, like "stay on for at least 1200 seconds
        (20 minutes) when the low temperature is reached,
        but don't turn off until you reached the high temperature
        mark". 0x0006 could be a boolean "enable/disable" for
        some feature, maybe the high/low temp triggers.
        """

        # 0x0001: uint8_t = 50, maybe high temp Celsius (rwp)
        high_temp = ZCLAttributeDef(
            id=0x0001,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=STELLO_MANUFACTURER_ID,
        )
        # 0x0003: uint16_t = 1200 ??? (rwp)
        unknown_0x0003 = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="rwp",
            manufacturer_code=STELLO_MANUFACTURER_ID,
        )
        # 0x0005: uint8_t Current temperature, Celsius (rp)
        current_temp = ZCLAttributeDef(
            id=0x0005,
            type=t.uint8_t,
            access="rp",
            manufacturer_code=STELLO_MANUFACTURER_ID,
        )
        # 0x0006: uint8_t = 1 ??? (rwp)
        unknown_0x0006 = ZCLAttributeDef(
            id=0x0006,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=STELLO_MANUFACTURER_ID,
        )
        # 0x0007: uint8_t = 49, maybe low temp Celsius (rwp)
        low_temp = ZCLAttributeDef(
            id=0x0007,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=STELLO_MANUFACTURER_ID,
        )


(
    QuirkBuilder("Stello", "STLO-23")
    .replaces(STLO23TemperatureCluster)
    # Current temperature
    .sensor(
        attribute_name=STLO23TemperatureCluster.AttributeDefs.current_temp.name,
        cluster_id=STLO23TemperatureCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        suggested_display_precision=0,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=300, reportable_change=1
        ),
        translation_key="temperature",
        fallback_name="Temperature",
    )
    .add_to_registry()
)
