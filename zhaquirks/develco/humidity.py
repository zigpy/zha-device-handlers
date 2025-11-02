"""Develco Smart Humidity Sensor."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.develco import DevelcoPowerConfiguration

(
    QuirkBuilder("frient A/S", "HMSZB-120")
    .replaces(DevelcoPowerConfiguration, endpoint_id=38)
    .add_to_registry()
)
