"""IKEA Bilresa 2 button remote control."""
from typing import Any, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.ikea import IKEA, ScenesCluster

from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    DOUBLE_PRESS,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)

class IkeaBilresaLevelControl(CustomCluster, LevelControl):
    """Custom LevelControl cluster for Bilresa remote to track direction."""

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self._last_move_direction = None

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
        
        Track move commands to remember direction for stop commands"""
        if hdr.command_id in (0x01, 0x05):
            move_mode = args[0]
            self._last_move_direction = move_mode
        elif hdr.command_id in (0x03, 0x07):
            if self._last_move_direction == 0:
                self.listener_event(ZHA_SEND_EVENT, "move_up_release", [])
            elif self._last_move_direction == 1:
                self.listener_event(ZHA_SEND_EVENT, "move_down_release", [])

class IkeaBilresa2ButtonRemote(CustomDeviceV2):
    """Custom device for IKEA Bilresa 2 button remote."""

(
    QuirkBuilder(IKEA, "09B9")
    .replaces(ScenesCluster, cluster_type=ClusterType.Client)
    .replace_cluster_occurrences(IkeaBilresaLevelControl)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON, 
                CLUSTER_ID: 6, 
                ENDPOINT_ID: 1
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: "move_up_release",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF, 
                CLUSTER_ID: 6, 
                ENDPOINT_ID: 1
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: "move_down_release",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (DOUBLE_PRESS, DIM_UP): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (DOUBLE_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
        } 
    )
    .add_to_registry()
)