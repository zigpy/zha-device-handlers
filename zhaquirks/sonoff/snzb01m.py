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
    1: SHORT_PRESS,
    2: DOUBLE_PRESS,
    3: LONG_PRESS,
    4: TRIPLE_PRESS,
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
    .adds(SonoffButtonCluster, endpoint_id=1)
    .adds(SonoffButtonCluster, endpoint_id=2)
    .adds(SonoffButtonCluster, endpoint_id=3)
    .adds(SonoffButtonCluster, endpoint_id=4)
    .device_automation_triggers(
        {
            # (SHORT_PRESS, "button_1"): {COMMAND: SHORT_PRESS, ENDPOINT_ID: 1},
            # ...
            (action, button): {COMMAND: action, ENDPOINT_ID: ep}
            for ep, button in BUTTONS.items()
            for action in (SHORT_PRESS, DOUBLE_PRESS, LONG_PRESS, TRIPLE_PRESS)
        }
    )
    .add_to_registry()
)
