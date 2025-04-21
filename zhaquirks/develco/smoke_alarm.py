"""Frient Smoke Alarm."""

from zigpy.quirks.v2 import QuirkBuilder

from . import DevelcoIasZone, DevelcoPowerConfiguration

(
    QuirkBuilder("frient A/S", "SMSZB-120")
    .applies_to("Develco Products A/S", "SMSZB-120")
    .replaces(DevelcoIasZone, endpoint_id=35)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    .add_to_registry()
)
