"""Quirks for Sonoff devices."""
from zigpy.quirks import CustomCluster

SONOFF_CLUSTER_ID = 0xFC57


class SonoffManufactureCluster(CustomCluster):
    name = "Sonoff Manufacturer Specicific"
    cluster_id = SONOFF_CLUSTER_ID
