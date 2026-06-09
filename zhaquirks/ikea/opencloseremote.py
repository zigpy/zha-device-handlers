"""Device handler for IKEA of Sweden TRADFRI remote control."""

from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.const import (
    ARGS,
    CLOSE,
    COMMAND,
    COMMAND_STOP,
    LONG_RELEASE,
    OPEN,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)
from zhaquirks.ikea import IKEA, DoublingPowerConfig1CRCluster

COMMAND_CLOSE = "down_close"
COMMAND_STOP_OPENING = "stop_opening"
COMMAND_STOP_CLOSING = "stop_closing"
COMMAND_OPEN = "up_open"


class IkeaWindowCovering(CustomCluster, WindowCovering):
    """Ikea Window covering cluster."""

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self._is_closing = None

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster specific commands.

        We just want to keep track of direction, to associate it with the stop command.
        """

        cmd_name = self.server_commands[hdr.command_id].name
        if cmd_name == COMMAND_OPEN:
            self._is_closing = False
        elif cmd_name == COMMAND_CLOSE:
            self._is_closing = True
        elif cmd_name == COMMAND_STOP:
            action = COMMAND_STOP_CLOSING if self._is_closing else COMMAND_STOP_OPENING
            self.listener_event(ZHA_SEND_EVENT, action, [])


(
    QuirkBuilder("\x02KE", "TRADFRI open/close remote")
    .applies_to(IKEA, "TRADFRI open/close remote")
    .replaces(DoublingPowerConfig1CRCluster, endpoint_id=1)
    .removes(OnOff.cluster_id, cluster_type=ClusterType.Client, endpoint_id=1)
    .adds(IkeaWindowCovering, cluster_type=ClusterType.Client, endpoint_id=1)
    .device_automation_triggers(
        {
            (SHORT_PRESS, OPEN): {COMMAND: COMMAND_OPEN, ARGS: []},
            (LONG_RELEASE, OPEN): {COMMAND: COMMAND_STOP_OPENING, ARGS: []},
            (SHORT_PRESS, CLOSE): {COMMAND: COMMAND_CLOSE, ARGS: []},
            (LONG_RELEASE, CLOSE): {COMMAND: COMMAND_STOP_CLOSING, ARGS: []},
        }
    )
    .add_to_registry()
)
