"""Osram quirks elements."""
from zigpy.quirks import CustomCluster

OSRAM = "OSRAM"


class OsramLightCluster(CustomCluster):
    """OsramLightCluster."""

    cluster_id = 0xFC0F
    ep_attribute = "osram_light"
    name = "OsramLight"
    manufacturer_server_commands = {0x0001: ("save_defaults", (), False)}
