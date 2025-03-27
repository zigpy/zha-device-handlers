"""Common code for Yandex devices."""

from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

### CONSTANTS ###


YANDEX = "Yandex"
YANDEX_CLUSTER_ID = 0xFC03
YANDEX_MANUFACTURER_CODE = 0x140A


### TYPES ###


class YandexType_SwitchMode(t.enum8):
    """Wired switches: gang mode."""

    Control_Relay = 0x00
    Up_Decoupled = 0x01
    Decoupled = 0x02
    Down_Decoupled = 0x03


class YandexType_SwitchType(t.enum8):
    """Relays: connected switch type."""

    Rocker = 0x00
    Button = 0x01
    Decoupled = 0x02


class YandexType_PowerType(t.enum8):
    """Wired devices: power level."""

    High = 0x00
    Medium = 0x01
    Low = 0x02


class YandexType_LedIndicator(t.basic.enum8):
    """Enable/disable LED indicator."""

    Enabled = 0
    Disabled = 1


class YandexType_Interlock(t.basic.enum8):
    """Double relay only: enable/disable interlock mode."""

    Disabled = 0
    Enabled = 1


class YandexType_ButtonMode(t.enum8):
    """Dimmer only: button presses interpretation."""

    General = 0x00
    Alternative = 0x01


### ATTRIBUTE DEFINITIONS ###


YANDEX_ATTRIBUTE_SWITCH_MODE = ZCLAttributeDef(
    id=0x0001,
    name="switch_mode",
    type=YandexType_SwitchMode,
    access="rw",
)
YANDEX_ATTRIBUTE_SWITCH_TYPE = ZCLAttributeDef(
    id=0x0002,
    name="switch_type",
    type=YandexType_SwitchType,
    access="rw",
)
YANDEX_ATTRIBUTE_POWER_TYPE = ZCLAttributeDef(
    id=0x0003,
    name="power_type",
    type=YandexType_PowerType,
    access="rw",
)
YANDEX_ATTRIBUTE_LED_INDICATOR = ZCLAttributeDef(
    id=0x0005,
    name="led_indicator",
    type=YandexType_LedIndicator,
    access="rw",
)
YANDEX_ATTRIBUTE_INTERLOCK = ZCLAttributeDef(
    id=0x0007,
    name="interlock",
    type=YandexType_Interlock,
    access="rw",
)
YANDEX_ATTRIBUTE_BUTTON_MODE = ZCLAttributeDef(
    id=0x0008,
    name="button_mode",
    type=YandexType_ButtonMode,
    access="rw",
)


### COMMAND DEFINITIONS ###


YANDEX_COMMAND_SWITCH_MODE = ZCLCommandDef(
    id=0x01,
    name="switch_mode",
    schema={"value": YandexType_SwitchMode},
    direction=False,
    is_manufacturer_specific=True,
)
YANDEX_COMMAND_SWITCH_TYPE = ZCLCommandDef(
    id=0x02,
    name="switch_type",
    schema={"value": YandexType_SwitchType},
    direction=False,
    is_manufacturer_specific=True,
)
YANDEX_COMMAND_POWER_TYPE = ZCLCommandDef(
    id=0x03,
    name="power_type",
    schema={"value": YandexType_PowerType},
    direction=False,
    is_manufacturer_specific=True,
)
YANDEX_COMMAND_LED_INDICATOR = ZCLCommandDef(
    id=0x05,
    name="led_indicator",
    schema={"value": YandexType_LedIndicator},
    direction=False,
    is_manufacturer_specific=True,
)
YANDEX_COMMAND_INTERLOCK = ZCLCommandDef(
    id=0x07,
    name="interlock",
    schema={"value": YandexType_Interlock},
    direction=False,
    is_manufacturer_specific=True,
)
YANDEX_COMMAND_BUTTON_MODE = ZCLCommandDef(
    id=0x08,
    name="button_mode",
    schema={"value": YandexType_ButtonMode},
    direction=False,
    is_manufacturer_specific=True,
)


### COMMON CLUSTERS ###


class YandexCluster(CustomCluster):
    """Common Yandex manufacturer-specific cluster properties."""

    cluster_id = YANDEX_CLUSTER_ID
    manufacturer_id_override = YANDEX_MANUFACTURER_CODE


class YandexClusterFull(YandexCluster):
    """Complete Yandex manufacturer-specific cluster, with all commands and attributes."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_mode: Final = YANDEX_ATTRIBUTE_SWITCH_MODE
        switch_type: Final = YANDEX_ATTRIBUTE_SWITCH_TYPE
        power_type: Final = YANDEX_ATTRIBUTE_POWER_TYPE
        led_indicator: Final = YANDEX_ATTRIBUTE_LED_INDICATOR
        interlock: Final = YANDEX_ATTRIBUTE_INTERLOCK
        button_mode: Final = YANDEX_ATTRIBUTE_BUTTON_MODE

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions."""

        switch_mode: Final = YANDEX_COMMAND_SWITCH_MODE
        switch_type: Final = YANDEX_COMMAND_SWITCH_TYPE
        power_type: Final = YANDEX_COMMAND_POWER_TYPE
        led_indicator: Final = YANDEX_COMMAND_LED_INDICATOR
        interlock: Final = YANDEX_COMMAND_INTERLOCK
        button_mode: Final = YANDEX_COMMAND_BUTTON_MODE
