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

BUTTON_MAPPING = {
    2: BUTTON_1,
    4: BUTTON_2,
    8: BUTTON_3,
    16: BUTTON_4,
    32: BUTTON_5,
    64: BUTTON_6,
    128: BUTTON_7,
    256: BUTTON_8,
}


class ZunZunBeeIASCluster(CustomCluster, IasZone):
    """IAS cluster used for ZunZunBee button."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.zone_status.id:
            # Ignore first bit for determining button id
            button_id = value & 0x01FE

            # Map to button presses, ignore invalid buttons
            button = BUTTON_MAPPING.get(button_id)
            if button is None:
                return

            # Only check first bit for press type
            press_id = (value & 1) + 1
            press_type = PRESS_TYPES[press_id]

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
