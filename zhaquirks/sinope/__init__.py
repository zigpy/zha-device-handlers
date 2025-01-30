"""Module for Sinope quirks implementations."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import DeviceTemperature

from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    SHORT_PRESS,
    SHORT_RELEASE,
    TURN_OFF,
    TURN_ON,
    VALUE,
)

SINOPE = "Sinope Technologies"
SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01
ATTRIBUTE_ACTION = "action_report"


class ButtonAction(t.enum8):
    """Action_report values."""

    Pressed_on = 0x01
    Released_on = 0x02
    Long_on = 0x03
    Double_on = 0x04
    Pressed_off = 0x11
    Released_off = 0x12
    Long_off = 0x13
    Double_off = 0x14


LIGHT_DEVICE_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_INITIAL_PRESS,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: int(ButtonAction.Pressed_on),
        },
    },
    (SHORT_PRESS, TURN_OFF): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_INITIAL_PRESS,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_OFF,
            VALUE: int(ButtonAction.Pressed_off),
        },
    },
    (SHORT_RELEASE, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_SHORT_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: int(ButtonAction.Released_on),
        },
    },
    (SHORT_RELEASE, TURN_OFF): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_SHORT_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_OFF,
            VALUE: int(ButtonAction.Released_off),
        },
    },
    (DOUBLE_PRESS, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: int(ButtonAction.Double_on),
        },
    },
    (DOUBLE_PRESS, TURN_OFF): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_OFF,
            VALUE: int(ButtonAction.Double_off),
        },
    },
    (LONG_PRESS, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_LONG_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: int(ButtonAction.Long_on),
        },
    },
    (LONG_PRESS, TURN_OFF): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_LONG_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_OFF,
            VALUE: int(ButtonAction.Long_off),
        },
    },
}


class CustomDeviceTemperatureCluster(CustomCluster, DeviceTemperature):
    """Custom device temperature cluster that multiplies temperature by 100."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.current_temperature.id:
            value = value * 100
        super()._update_attribute(attrid, value)
