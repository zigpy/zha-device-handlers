"""Module for Philips quirks implementations."""
from zigpy.quirks import CustomCluster
from zigpy.zcl.clusters.general import OnOff
import zigpy.types as t

PHILIPS = "Philips"


class PowerOnState(t.enum8):
    """Philips power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0xFF


class PhilipsOnOffCluster(CustomCluster, OnOff):
    """Philips OnOff cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update({0x4003: ("power_on_state", PowerOnState)})
