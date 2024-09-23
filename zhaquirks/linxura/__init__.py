"""Konke sensors."""

from typing import Any, Optional, Union

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
import zigpy.zcl.foundation

from zhaquirks import CustomCluster, LocalDataCluster, MotionWithReset, OccupancyOnEvent
from zhaquirks.const import (
    BUTTON,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_SINGLE,
    PRESS_TYPE,
    ZHA_SEND_EVENT,
)

LINXURA = "Linxura"


class LinxuraButtonEvent(t.enum8):
    """Linxura button event."""

    Single = 0x80
    Double = 0x81
    Hold = 0x82


PRESS_TYPES = {
    LinxuraButtonEvent.Single: COMMAND_SINGLE,
    LinxuraButtonEvent.Double: COMMAND_DOUBLE,
    LinxuraButtonEvent.Hold: COMMAND_HOLD,
}


class OccupancyCluster(LocalDataCluster, OccupancyOnEvent):
    """Occupancy cluster."""

    reset_s: int = 600


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60
    send_occupancy_event: bool = True


class LinxuraOnOffCluster(CustomCluster):
    """Linxura OnOff cluster implementation."""

    cluster_id = OnOff.cluster_id
    ep_attribute = "Linxura_on_off"

    attributes = OnOff.attributes.copy()
    attributes[0x0000] = ("Linxura_button_event", LinxuraButtonEvent)

    server_commands = OnOff.server_commands.copy()
    client_commands = OnOff.client_commands.copy()

    def handle_cluster_general_request(
        self,
        header: zigpy.zcl.foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        self.info(
            "Linxura general request - handle_cluster_general_request: header: %s - args: [%s]",
            header,
            args,
        )

        if header.command_id != zigpy.zcl.foundation.GeneralCommand.Report_Attributes:
            return

        attr = args[0][0]

        if attr.attrid != self.attributes_by_name["Linxura_button_event"].id:
            return

        value = attr.value.value
        event_args = {
            PRESS_TYPE: PRESS_TYPES[value],
            COMMAND_ID: value.value,  # to maintain backwards compatibility
        }
        self.listener_event(ZHA_SEND_EVENT, event_args[PRESS_TYPE], event_args)