"""Quirk for Tuya 24GHz mmWave human presence sensor.
Model: TS0601
Manufacturer: _TZE200_gkfbdvyx
author: @albertjh
"""

import math

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfLength, UnitOfTime
from zigpy.quirks.v2 import EntityType
import zigpy.types as t
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing

from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder

# --- Custom Tuya Clusters ---


class TuyaIlluminanceCluster(IlluminanceMeasurement, TuyaLocalCluster):
    """Custom Tuya illuminance cluster."""

    # This cluster will receive illuminance data from the corresponding DP.


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Custom Tuya occupancy sensing cluster."""

    # This cluster will receive presence data from the corresponding DP.


# --- Quirk Builder ---

(
    TuyaQuirkBuilder("_TZE200_gkfbdvyx", "TS0601")
    # DP 1: Occupancy Sensor (Presence)
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaOccupancySensing.ep_attribute,
        attribute_name=OccupancySensing.AttributeDefs.occupancy.name,
        # The sensor reports 1 (motion) or 2 (static presence). Both mean 'occupied'.
        converter=lambda x: True if x in (1, 2) else False,
    )
    .adds(TuyaOccupancySensing)  # Adds the occupancy cluster to the device
    # DP 2: Motion sensitivity (0-10)
    .tuya_number(
        dp_id=2,
        attribute_name="move_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="move_sensitivity",
        fallback_name="Motion sensitivity",
        entity_type=EntityType.CONFIG,  # This is a configuration entity
    )
    # DP 3: Minimum detection range (0-8.25m)
    .tuya_number(
        dp_id=3,
        attribute_name="detection_distance_min",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0,
        max_value=8.25,
        step=0.75,
        multiplier=0.01,  # The DP value is multiplied by 0.01 to get meters
        translation_key="detection_distance_min",
        fallback_name="Minimum range",
        entity_type=EntityType.CONFIG,
    )
    # DP 4: Maximum detection range (0.75-9.0m)
    .tuya_number(
        dp_id=4,
        attribute_name="detection_distance_max",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        min_value=0.75,
        max_value=9.0,
        step=0.75,
        multiplier=0.01,  # The DP value is multiplied by 0.01 to get meters
        translation_key="detection_distance_max",
        fallback_name="Maximum range",
        entity_type=EntityType.CONFIG,
    )
    # DP 9: Target distance (read-only sensor)
    .tuya_sensor(
        dp_id=9,
        attribute_name="distance",
        type=t.uint16_t,
        divisor=100,  # The DP value is divided by 100 to get meters
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DISTANCE,
        unit=UnitOfLength.METERS,
        entity_type=EntityType.STANDARD,
        translation_key="distance",
        fallback_name="Target distance",
    )
    # DP 101: Distance switch (function not entirely clear, exposed as a switch)
    .tuya_switch(
        dp_id=101,
        attribute_name="find_switch",
        entity_type=EntityType.STANDARD,
        translation_key="find_switch",
        fallback_name="Distance switch",
    )
    # DP 102: Static presence sensitivity (0-10)
    .tuya_number(
        dp_id=102,
        attribute_name="presence_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=10,
        step=1,
        translation_key="presence_sensitivity",
        fallback_name="Presence sensitivity",
        entity_type=EntityType.CONFIG,
    )
    # DP 103: Illuminance Sensor
    .tuya_dp(
        dp_id=103,
        ep_attribute=TuyaIlluminanceCluster.ep_attribute,
        attribute_name=TuyaIlluminanceCluster.AttributeDefs.measured_value.name,
        # Standard Tuya formula to convert to Lux
        converter=lambda x: round(10000 * math.log10(x) + 1) if x > 0 else 0,
    )
    .adds(TuyaIlluminanceCluster)  # Adds the illuminance cluster
    # DP 105: Fading time (timeout) in seconds
    .tuya_number(
        dp_id=105,
        attribute_name="presence_timeout",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=1,
        max_value=15000,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
        entity_type=EntityType.CONFIG,
    )
    # --- Finalization ---
    .skip_configuration()  # Avoids configuration errors with Tuya devices
    .add_to_registry()  # Registers the quirk in ZHA
)
