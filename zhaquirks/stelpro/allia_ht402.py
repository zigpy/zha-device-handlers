"""ZHA Quirk (v2) for Stello HT402.

Exposes vendor attributes 0x4008 (instant power, W), 0x4009 (cumulative energy, Wh)
from the Thermostat cluster on endpoint 25 (0x19).

"""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)

# Units come from the homeassistant submodule (guide uses UnitOfLength similarly)
from zigpy.quirks.v2.homeassistant import UnitOfEnergy, UnitOfPower
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeDef

MANUFACTURER: Final = (
    "Stello"  # Device manufacturer isn't listed as Stelpro for some reason
)
MODEL: Final = "HT402"
EP_THERMOSTAT: Final = 25  # Thermostat cluster


class AlliaThermostatCluster(Thermostat, CustomCluster):
    """Thermostat cluster extended with Stelpro(Stello)/Allia manufacturer attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Vendor-specific attributes added to the Thermostat cluster.

        - 0x4008: instant power (W), uint16
        - 0x4009: cumulative energy (Wh), uint32
        """

        # 0x4008: Instant power in Watts (uint16)
        allia_power_w = ZCLAttributeDef(id=0x4008, type=t.uint16_t, access="rp")
        # 0x4009: Cumulative energy in Watt-hours (uint32)
        allia_energy_wh = ZCLAttributeDef(id=0x4009, type=t.uint32_t, access="rp")


(
    QuirkBuilder(MANUFACTURER, MODEL)
    # Replace the Thermostat cluster on the actual endpoint
    .replaces(AlliaThermostatCluster, endpoint_id=EP_THERMOSTAT)
    # Expose Instant Power (W)
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
    # Expose Energy (Wh)
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
    .add_to_registry()
)
