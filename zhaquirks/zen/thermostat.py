"""Module to handle quirks of the  Zen Within thermostat."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.zen import ZEN, ZenPowerConfiguration

(
    QuirkBuilder(ZEN, "Zen-01")
    .replaces(replacement_cluster_class=ZenPowerConfiguration)
    .add_to_registry()
)
