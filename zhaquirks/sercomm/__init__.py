"""Module for sercomm quirks."""

from zhaquirks import PowerConfigurationCluster

SERCOMM = "Sercomm Corp."


class SercommPowerConfiguration(PowerConfigurationCluster):
    """Sercomm power configuration cluster for flood sensor."""

    MAX_VOLTS = 3.2
    MIN_VOLTS = 2.1
