"""SONOFF SNZB-01M 4-button wireless switch quirk."""

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    SHORT_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)

BUTTONS = {
    1: BUTTON_1,
    2: BUTTON_2,
    3: BUTTON_3,
    4: BUTTON_4,
}

ACTION_MAP = {
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    3: COMMAND_HOLD,
    4: COMMAND_TRIPLE,
}

TRIGGER_MAP = {
    COMMAND_SINGLE: SHORT_PRESS,
    COMMAND_DOUBLE: DOUBLE_PRESS,
    COMMAND_HOLD: LONG_PRESS,
    COMMAND_TRIPLE: TRIPLE_PRESS,
}


class SonoffButtonCluster(CustomCluster):
    """Sonoff button cluster for handling button events."""

    cluster_id = 0xFC12
    ep_attribute = "sonoff_button_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Sonoff button cluster."""

        key_action_event = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            manufacturer_code=None,
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.key_action_event.id:
            action = ACTION_MAP.get(value)
            if action:
                self.listener_event(ZHA_SEND_EVENT, action, {})


(
    QuirkBuilder("SONOFF", "SNZB-01M")
    .replaces(SonoffButtonCluster, endpoint_id=1)
    .replaces(SonoffButtonCluster, endpoint_id=2)
    .replaces(SonoffButtonCluster, endpoint_id=3)
    .replaces(SonoffButtonCluster, endpoint_id=4)
    .device_automation_triggers(
        {
            # (SHORT_PRESS, "button_1"): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 1},
            # ...
            (trigger, button): {COMMAND: command, ENDPOINT_ID: ep}
            for ep, button in BUTTONS.items()
            for command, trigger in TRIGGER_MAP.items()
        }
    )
    .add_to_registry()
)
