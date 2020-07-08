"""Ledvance quirks elements."""
from zigpy.quirks import CustomCluster

LEDVANCE = "LEDVANCE"


class LedvanceLightCluster(CustomCluster):
    """LedvanceLightCluster."""

    cluster_id = 0xFC01
    ep_attribute = "ledvance_light"
    name = "LedvanceLight"
    manufacturer_server_commands = {0x0001: ("save_defaults", (), False)}
