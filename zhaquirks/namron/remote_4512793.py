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


class NamronRemoteButton(t.enum8):
    """Physical button position on the Namron Simplify remote."""

    TopLeft = 0x01
    BottomLeft = 0x02
    TopMiddle = 0x03
    BottomMiddle = 0x04
    TopRight = 0x05
    BottomRight = 0x06


class NamronRemoteAction(t.enum8):
    """Button action reported by the private cluster."""

    Press = 0x01
    Hold = 0x02
    Release = 0x04


PRESS_TYPES = {
    NamronRemoteAction.Press: SHORT_PRESS,
    NamronRemoteAction.Hold: LONG_PRESS,
    NamronRemoteAction.Release: LONG_RELEASE,
}

BUTTON_MAPPING = {
    NamronRemoteButton.TopLeft: BUTTON_1,
    NamronRemoteButton.BottomLeft: BUTTON_2,
    NamronRemoteButton.TopMiddle: BUTTON_3,
    NamronRemoteButton.BottomMiddle: BUTTON_4,
    NamronRemoteButton.TopRight: BUTTON_5,
    NamronRemoteButton.BottomRight: BUTTON_6,
}


class NamronPrivateRemoteCluster(CustomCluster):
    """Namron private cluster (0xE004) reporting Simplify remote button events.

    A short tap sends only `Press`; holding sends `Hold` then `Release`,
    without a preceding `Press`.
    """

    name: str = "Namron Private Remote Cluster"
    cluster_id: t.uint16_t = 0xE004
    ep_attribute: str = "namron_private_remote"

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        button_action: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={"button": NamronRemoteButton, "action": NamronRemoteAction},
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
