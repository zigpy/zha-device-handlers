"""Linkind sensors."""
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic


class LinkindLeakMode(t.enum8):
    """Linkind Leak Sensor mode enum."""

    Siren_Off_LED_Off = 0x00
    Siren_Off_LED_On = 0x01
    Siren_On_LED_Off = 0x02
    Siren_On_LED_On = 0x03


class LinkindBasicCluster(CustomCluster, Basic):
    """Linkind Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes.update({0x0400A: ("siren_LED_mode", LinkindLeakMode)})
