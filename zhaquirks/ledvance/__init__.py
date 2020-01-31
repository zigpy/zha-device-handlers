"""Ledvance quirks elements."""
from zigpy.quirks import CustomCluster

LEDVANCE = "LEDVANCE"


class LedvanceLightCluster(CustomCluster):
    """LedvanceLightCluster."""

    attributes = {}
    client_commands = {}
    cluster_id = 0xFC01
    ep_attribute = "ledvance_light"
    name = "LedvanceLight"
    server_commands = {0x0001: ("save_defaults", (), False)}
