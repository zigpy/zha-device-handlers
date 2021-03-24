"""Module for Samjin quirks implementations."""
import logging
from typing import Any, List, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.types import Addressing
from zigpy.zcl import foundation
import zigpy.zcl.clusters.security

from zhaquirks.const import ARGS, COMMAND_ID, PRESS_TYPE, ZHA_SEND_EVENT

_LOGGER = logging.getLogger(__name__)

DOUBLE = 2
HOLD = 3
SAMJIN = "Samjin"
SINGLE = 1

CLICK_TYPES = {SINGLE: "single", DOUBLE: "double", HOLD: "hold"}


class SamjinIASCluster(CustomCluster, zigpy.zcl.clusters.security.IasZone):
    """Occupancy cluster."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[Addressing.Group, Addressing.IEEE, Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == 0:
            state = args[0] & 3
            event_args = {
                PRESS_TYPE: CLICK_TYPES[state],
                COMMAND_ID: hdr.command_id,
                ARGS: args,
            }
            action = "button_{}".format(CLICK_TYPES[state])
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
