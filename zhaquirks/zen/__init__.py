"""Module for Zen Within quirks implementations."""

from zhaquirks import PowerConfigurationCluster

ZEN = "Zen Within"


class ZenPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 3.6
    MAX_VOLTS = 6.0
