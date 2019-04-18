"""Osram quirks elements."""
from zigpy.quirks import CustomCluster


class OsramLightCluster(CustomCluster):
    """OsramLightCluster."""

    cluster_id = 0xFC0F
    name = 'OsramLight'
    ep_attribute = 'osram_light'
    attributes = {}
    server_commands = {
        0x0001: ('save_defaults', (), False)
    }
    client_commands = {}
