"""ZunZunBee button device."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    CLUSTER_ID,
    COMMAND,
    LONG_PRESS,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.zunzunbee import ZUNZUNBEE

PRESS_TYPES = {
    1: SHORT_PRESS,
    2: LONG_PRESS,
}


class ZunZunBeeIASCluster(CustomCluster, IasZone):
    """IAS cluster used for ZunZunBee button."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id:
            press = (value & 1) + 1
            value = value & 0x01FE

            if value == 2:
                button = BUTTON_1
                press_type = PRESS_TYPES[press]
            elif value == 4:
                button = BUTTON_2
                press_type = PRESS_TYPES[press]
            elif value == 8:
                button = BUTTON_3
                press_type = PRESS_TYPES[press]
            elif value == 16:
                button = BUTTON_4
                press_type = PRESS_TYPES[press]
            elif value == 32:
                button = BUTTON_5
                press_type = PRESS_TYPES[press]
            elif value == 64:
                button = BUTTON_6
                press_type = PRESS_TYPES[press]
            elif value == 128:
                button = BUTTON_7
                press_type = PRESS_TYPES[press]
            elif value == 256:
                button = BUTTON_8
                press_type = PRESS_TYPES[press]
            else:
                # discard invalid values:
                return

            action = f"{button}_{press_type}"
            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


(
    QuirkBuilder(ZUNZUNBEE, "SSWZ8T")
    .replaces(ZunZunBeeIASCluster)
    .device_automation_triggers(
        {
            (press_type, button): {
                COMMAND: f"{button}_{press_type}",
                CLUSTER_ID: IasZone.cluster_id,
            }
            for press_type in (SHORT_PRESS, LONG_PRESS)
            for button in (
                BUTTON_1,
                BUTTON_2,
                BUTTON_3,
                BUTTON_4,
                BUTTON_5,
                BUTTON_6,
                BUTTON_7,
                BUTTON_8,
            )
        }
    )
    .add_to_registry()
)
