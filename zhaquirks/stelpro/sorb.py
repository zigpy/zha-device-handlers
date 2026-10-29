"""Stelpro SORB fan heater."""

import functools

from zha.application.platforms.climate import Thermostat
from zha.application.platforms.climate.const import HVACMode
from zigpy.zcl.clusters.hvac import Thermostat as ThermostatCluster

from zhaquirks.builder import QuirkBuilder


class StelproFanHeaterThermostat(Thermostat):
    """Stelpro fan heater thermostat."""

    @functools.cached_property
    def hvac_modes(self) -> list[HVACMode]:
        """Return only the heat mode, because the device can't be turned off."""
        return [HVACMode.HEAT]


(
    QuirkBuilder("Stelpro", "SORB")
    .replaces_entity(
        Thermostat,
        StelproFanHeaterThermostat,
        cluster_id=ThermostatCluster.cluster_id,
    )
    .add_to_registry()
)
