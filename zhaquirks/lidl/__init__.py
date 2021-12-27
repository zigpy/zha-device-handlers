"""Module for LIDL devices."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff


# Tuya Zigbee OnOff Cluster Attribute Implementation
class SwitchBackLight(t.enum8):
    """Tuya switch back light mode enum."""

    Mode_0 = 0x00
    Mode_1 = 0x01
    Mode_2 = 0x02


class SwitchMode(t.enum8):
    """Tuya switch mode enum."""

    Command = 0x00
    Event = 0x01


class PowerOnState(t.enum8):
    """Tuya power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0x02


class TuyaZBOnOffAttributeCluster(CustomCluster, OnOff):
    """Tuya Zigbee On Off cluster with extra attributes."""

    attributes = OnOff.attributes.copy()
    attributes.update({0x8001: ("backlight_mode", SwitchBackLight)})
    attributes.update({0x8002: ("power_on_state", PowerOnState)})
    attributes.update({0x8004: ("switch_mode", SwitchMode)})
