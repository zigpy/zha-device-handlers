"""ZHA Quirk (v2) for Stello HT402.

Adds manufacturer attributes:
- 0x4008: Instant power (W)
- 0x4009: Cumulative energy (Wh)
- 0x4001: Outdoor temperature (°C or °F, read/write)
"""

from typing import Final

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import UnitOfEnergy, UnitOfPower, UnitOfTemperature

MANUFACTURER: Final = "Stello"
MODEL: Final = "HT402"
EP_THERMOSTAT: Final = 25  # 0x19


class AlliaThermostatCluster(Thermostat, CustomCluster):
    """Thermostat cluster extended with Stello/Allia manufacturer attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Vendor-specific attributes added to the Thermostat cluster.

        - 0x4001: outdoor temperature (°C or °F), int16, read/write
        - 0x4008: instant power (W), uint16, read-only
        - 0x4009: cumulative energy (Wh), uint32, read-only
        """

        # 0x4001: Outdoor temperature (int16, read/write)
        allia_outdoor_temperature = ZCLAttributeDef(
            id=0x4001,
            type=t.int16s,
            access="rpw",  # readable, reportable, writable
        )
        # 0x4008: Instant power in Watts (uint16)
        allia_power_w = ZCLAttributeDef(id=0x4008, type=t.uint16_t, access="rp")
        # 0x4009: Cumulative energy in Watt-hours (uint32)
        allia_energy_wh = ZCLAttributeDef(id=0x4009, type=t.uint32_t, access="rp")


(
    QuirkBuilder(MANUFACTURER, MODEL)
    .replaces(AlliaThermostatCluster, endpoint_id=EP_THERMOSTAT)
    # Instant Power
    .sensor(
        attribute_name=AlliaThermostatCluster.AttributeDefs.allia_power_w.name,
        cluster_id=AlliaThermostatCluster.cluster_id,
        endpoint_id=EP_THERMOSTAT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        reporting_config=ReportingConfig(
            min_interval=5, max_interval=300, reportable_change=1
        ),
        translation_key="allia_power_w",
        fallback_name="Allia Power",
    )
    # Energy (cumulative)
    .sensor(
        attribute_name=AlliaThermostatCluster.AttributeDefs.allia_energy_wh.name,
        cluster_id=AlliaThermostatCluster.cluster_id,
        endpoint_id=EP_THERMOSTAT,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.WATT_HOUR,
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=3600, reportable_change=10
        ),
        translation_key="allia_energy_wh",
        fallback_name="Allia Energy",
    )
    # Outdoor Temperature (0x4001) — read/write
    .sensor(
        attribute_name=AlliaThermostatCluster.AttributeDefs.allia_outdoor_temperature.name,
        cluster_id=AlliaThermostatCluster.cluster_id,
        endpoint_id=EP_THERMOSTAT,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS, # Would need to convert to F
        translation_key="allia_outdoor_temperature",
        fallback_name="Outdoor Temperature",
    )
    .add_to_registry()
)
