"""Linxura button device."""

from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.types import Addressing
from zigpy.zcl import foundation
import zigpy.zcl.clusters.security

from zhaquirks.const import ARGS, COMMAND_ID, PRESS_TYPE, ZHA_SEND_EVENT

DOUBLE = 2
HOLD = 3
LINXURA = "Linxura"
SINGLE = 1
ACT_ERROR = 4
STATUS_PARAM = 0
CLICK_TYPES = {SINGLE: "single", DOUBLE: "double", HOLD: "hold"}


class LinxuraIASCluster(CustomCluster, zigpy.zcl.clusters.security.IasZone):
    """Occupancy cluster."""

    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "button_event",
            {"press_type": t.uint8_t},
        ),
    }

    def handle_cluster_general_request(
        self,
        hdr: zigpy.zcl.foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == 0:
            state = args[STATUS_PARAM]
            if state >= ACT_ERROR:
                return
            else:
                event_args = {
                    PRESS_TYPE: CLICK_TYPES[state],
                    COMMAND_ID: hdr.command_id,
                    ARGS: args,
                }
                action = f"button_{CLICK_TYPES[state]}"
                self.listener_event(ZHA_SEND_EVENT, action, event_args)
