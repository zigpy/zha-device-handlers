"""SONOFF SNZB-01M 4-button wireless switch quirk."""

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.const import (
    COMMAND,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)

SONOFF_CLUSTER_ID_FC12 = 0xFC12


class SonoffButtonCluster(CustomCluster):
    """Sonoff button cluster for handling button events."""

    cluster_id = SONOFF_CLUSTER_ID_FC12
    ep_attribute = "sonoff_button_cluster"

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the Sonoff button cluster."""

        key_action_event = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,  # 用标准uint8类型
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.key_action_event.id:
            event = button_event_from_report(self.endpoint.endpoint_id, value)
            if event:
                self.listener_event(ZHA_SEND_EVENT, event["event"], event)


# 直接用整数做key
ACTION_MAP = {
    1: SHORT_PRESS,  # 0x01
    2: DOUBLE_PRESS,  # 0x02
    3: LONG_PRESS,  # 0x03
    4: TRIPLE_PRESS,  # 0x04
}


def button_event_from_report(endpoint_id, value):
    """Convert button report value to event dictionary."""
    action = ACTION_MAP.get(value)
    if action:
        return {
            "endpoint_id": endpoint_id,
            "event": action,
            "button": f"button{endpoint_id}",
        }
    return None
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Basic


(
    QuirkBuilder("SONOFF", "SNZB-01M")
    .applies_to("SONOFF", "SNZB-01M")
    .adds(SonoffButtonCluster, endpoint_id=1)
    .adds(SonoffButtonCluster, endpoint_id=2)
    .adds(SonoffButtonCluster, endpoint_id=3)
    .adds(SonoffButtonCluster, endpoint_id=4)
    .device_automation_triggers(
        {
            (SHORT_PRESS, f"button{ep}"): {COMMAND: SHORT_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, f"button{ep}"): {COMMAND: DOUBLE_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    .device_automation_triggers(
        {
            (LONG_PRESS, f"button{ep}"): {COMMAND: LONG_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    .device_automation_triggers(
        {
            (TRIPLE_PRESS, f"button{ep}"): {COMMAND: TRIPLE_PRESS, "endpoint_id": ep}
            for ep in range(1, 5)
        }
    )
    .add_to_registry()
)
