"""Eurotronic Spirit Zigbee quirk."""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.eurotronic import EUROTRONIC, EurotronicThermostat, ThermostatCluster

(
    QuirkBuilder(EUROTRONIC, "SPZB0001")
    .replaces(ThermostatCluster, endpoint_id=1)
    .replaces_entity(EurotronicThermostat)
    .add_to_registry()
)
