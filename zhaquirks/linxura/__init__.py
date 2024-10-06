"""Linxura button device."""

LINXURA = "Linxura"

from typing import Any, Optional, Union
from zigpy.quirks import CustomCluster
from zigpy.types import Addressing
from zigpy.zcl import foundation
import zigpy.zcl.clusters.security

from zhaquirks.const import (
    ARGS,
    COMMAND_ID,
    PRESS_TYPE,
    ZHA_SEND_EVENT,
)


DOUBLE = 2
HOLD = 3
# LINXURA = "Linxura"
SINGLE = 1
CLICK_TYPES = {SINGLE: "single", DOUBLE: "double", HOLD: "hold"}

class LinxuraIASCluster(CustomCluster, zigpy.zcl.clusters.security.IasZone):
    """Occupancy cluster."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        # self.info(
        #    "Linxura general request - handle_cluster_general_request: header: %s - args: [%s]",
        #    hdr,
        #    args,
        # )
        if hdr.command_id == 0:
            # self.info(
            #    "Linxura general request - state: %s",
            #    args[0],
            # )
            state = args[0]
            if state >= 4:
                return
            else:
                event_args = {
                    PRESS_TYPE: CLICK_TYPES[state],
                    COMMAND_ID: hdr.command_id,
                    ARGS: args,
                }
                action = f"button_{CLICK_TYPES[state]}"
                self.listener_event(ZHA_SEND_EVENT, action, event_args)
