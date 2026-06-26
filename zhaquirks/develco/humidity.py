"""Develco Smart Humidity Sensor."""

from zhaquirks.builder import QuirkBuilder
from zhaquirks.develco import DevelcoPowerConfiguration


class HumidityPowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration with device-specific voltage bounds."""

    MIN_VOLTS = 2.3
    MAX_VOLTS = 3.0


(
    QuirkBuilder("frient A/S", "HMSZB-120")
    .applies_to("Develco Products A/S", "HMSZB-120")
    .applies_to("frient A/S", "HMSZB-110")
    .applies_to("Develco Products A/S", "HMSZB-110")
    .replaces(HumidityPowerConfiguration, endpoint_id=38)
    .add_to_registry()
)
