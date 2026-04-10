"""Yokis quirks elements."""

from zigpy.quirks import CustomCluster

YOKIS = "YOKIS"

"""Specific Yokis clusters"""


class YokisDeviceCluster(CustomCluster):
    """Yokis Device Cluster."""

    cluster_id = 0xFC01


class YokisInputCluster(CustomCluster):
    """Yokis Input Cluster."""

    cluster_id = 0xFC02


class YokisLightControlCluster(CustomCluster):
    """Yokis Light Control Cluster."""

    cluster_id = 0xFC06


class YokisDimmerCluster(CustomCluster):
    """Yokis Dimmer Cluster."""

    cluster_id = 0xFC07


class YokisWindowCoveringCluster(CustomCluster):
    """Yokis Window Covering Cluster."""

    cluster_id = 0xFC08


class YokisChannelCluster(CustomCluster):
    """YokisChannelCluster."""

    cluster_id = 0xFC09


class YokisPilotWireCluster(CustomCluster):
    """Yokis Pilot Wire Cluster."""

    cluster_id = 0xFC0A


class YokisTemperatureMeasurementCluster(CustomCluster):
    """Yokis Temperature Measurement Cluster."""

    cluster_id = 0xFC0B
