"""Module for Sinope quirks implementations."""

from zigpy.quirks import CustomCluster
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
    LONG_RELEASE,
    SHORT_PRESS,
    SHORT_RELEASE,
    TURN_OFF,
    TURN_ON,
    VALUE,
)

SINOPE = "Sinope Technologies"
SINOPE_MANUFACTURER_CLUSTER_ID = 0xFF01
ATTRIBUTE_ACTION = "action_report"

LIGHT_DEVICE_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_INITIAL_PRESS,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: 1,
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
            VALUE: 17,
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
            VALUE: 2,
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
            VALUE: 18,
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
            VALUE: 4,
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
            VALUE: 20,
        },
    },
    (LONG_RELEASE, TURN_ON): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_LONG_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_ON,
            VALUE: 3,
        },
    },
    (LONG_RELEASE, TURN_OFF): {
        ENDPOINT_ID: 1,
        CLUSTER_ID: 65281,
        COMMAND: COMMAND_M_LONG_RELEASE,
        ARGS: {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: TURN_OFF,
            VALUE: 19,
        },
    },
}


class CustomDeviceTemperatureCluster(CustomCluster, DeviceTemperature):
    """Custom device temperature cluster that multiplies temperature by 100."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.current_temperature.id:
            value = value * 100
        super()._update_attribute(attrid, value)
