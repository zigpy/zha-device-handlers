"""Konke sensors."""

from zigpy.zcl.clusters.general import OnOff

from .. import (
    CustomCluster,
    CustomDevice,
    LocalDataCluster,
    MotionWithReset,
    OccupancyOnEvent,
)
from ..const import (
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_SINGLE,
    PRESS_TYPE,
    ZHA_SEND_EVENT,
)

KONKE = "Konke"


class OccupancyCluster(LocalDataCluster, OccupancyOnEvent):
    """Occupancy cluster."""

    reset_s: int = 600


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60
    send_occupancy_event: bool = True


class KonkeOnOffCluster(CustomCluster, OnOff):
    """Konke OnOff cluster implementation."""

    PRESS_TYPES = {0x0080: COMMAND_SINGLE, 0x0081: COMMAND_DOUBLE, 0x0082: COMMAND_HOLD}
    cluster_id = 6
    ep_attribute = "custom_on_off"
    attributes = {}
    server_commands = {}
    client_commands = {}

    def handle_cluster_general_request(self, header, args):
        """Handle the cluster command."""
        self.info(
            "Konke general request - handle_cluster_general_request: header: %s - args: [%s]",
            header,
            args,
        )

        cmd = header.command_id
        event_args = {
            PRESS_TYPE: self.PRESS_TYPES.get(cmd, cmd),
            COMMAND_ID: cmd,
        }
        self.listener_event(ZHA_SEND_EVENT, event_args[PRESS_TYPE], event_args)


class KonkeButtonRemote(CustomDevice):
    """Konke 1-button remote device."""

    def handle_message(self, profile, cluster, src_ep, dst_ep, message):
        """Handle a device message."""
        if (
            profile == 260
            and cluster == 6
            and len(message) == 7
            and message[0] == 0x08
            and message[2] == 0x0A
        ):
            # use the 7th byte as command_id
            new_message = bytearray(4)
            new_message[0] = message[0]
            new_message[1] = message[1]
            new_message[2] = message[6]
            new_message[3] = 0
            message = type(message)(new_message)
            super().handle_message(profile, cluster, src_ep, dst_ep, message)
