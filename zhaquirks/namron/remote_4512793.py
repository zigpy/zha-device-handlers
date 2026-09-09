"""Namron Simplify wireless remote (4512793)."""

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    CLUSTER_ID,
    COMMAND,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

BUTTON_ACTION_PRESS = 0x01
BUTTON_ACTION_HOLD = 0x02
BUTTON_ACTION_RELEASE = 0x04

PRESS_TYPES = {
    BUTTON_ACTION_PRESS: SHORT_PRESS,
    BUTTON_ACTION_HOLD: LONG_PRESS,
    BUTTON_ACTION_RELEASE: LONG_RELEASE,
}

BUTTON_MAPPING = {
    1: BUTTON_1,
    2: BUTTON_2,
    3: BUTTON_3,
    4: BUTTON_4,
    5: BUTTON_5,
    6: BUTTON_6,
}


class NamronPrivateRemoteCluster(CustomCluster):
    """Namron private cluster (0xE004) reporting Simplify remote button events.

    Command 0x00 payload is (button: 1-6, action: 0x01=press, 0x02=hold,
    0x04=release). A short tap sends only `press`; holding sends `hold`
    then `release`, without a preceding `press`.
    """

    name: str = "Namron Private Remote Cluster"
    cluster_id: t.uint16_t = 0xE004
    ep_attribute: str = "namron_private_remote"

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        button_action: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={"button": t.uint8_t, "action": t.uint8_t},
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Translate the raw button/action payload into a named zha_event."""
        if hdr.command_id != self.ClientCommandDefs.button_action.id:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        button = BUTTON_MAPPING.get(args.button)
        press_type = PRESS_TYPES.get(args.action)
        if button is None or press_type is None:
            return

        action = f"{button}_{press_type}"
        self.listener_event(
            ZHA_SEND_EVENT, action, {BUTTON: button, PRESS_TYPE: press_type}
        )


(
    # OnOff/LevelControl output clusters on all endpoints are unused in
    # normal (hub-connected) operation; they only apply when binding the
    # remote directly to a light via Namron's own app.
    QuirkBuilder("Namron AS", "4512793")
    .replaces(NamronPrivateRemoteCluster, endpoint_id=1)
    .device_automation_triggers(
        {
            (press_type, button): {
                COMMAND: f"{button}_{press_type}",
                CLUSTER_ID: NamronPrivateRemoteCluster.cluster_id,
            }
            for press_type in (SHORT_PRESS, LONG_PRESS, LONG_RELEASE)
            for button in (BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, BUTTON_5, BUTTON_6)
        }
    )
    .add_to_registry()
)
