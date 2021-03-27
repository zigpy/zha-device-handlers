"""Quirks for Develco Products A/S."""
from zhaquirks import PowerConfigurationCluster

DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2
