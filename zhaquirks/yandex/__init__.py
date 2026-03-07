"""Common code for Yandex devices."""

import zigpy.types as t

### CONSTANTS ###


YANDEX = "Yandex"
YANDEX_MANUFACTURER_CODE_1 = 0x140A


### TYPES ###


class YandexType_SwitchMode(t.enum8):
    """Wired switches: gang mode."""

    Control_Relay = 0x00
    Up_Decoupled = 0x01
    Decoupled = 0x02
    Down_Decoupled = 0x03


class YandexType_PowerType(t.enum8):
    """Wired devices: power level."""

    High = 0x00
    Medium = 0x01
    Low = 0x02


class YandexType_LedIndicator(t.basic.enum8):
    """Enable/disable LED indicator."""

    Enabled = 0
    Disabled = 1
