"""Konke sensors."""

from typing import Any, Final

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
import zigpy.zcl.foundation
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster, LocalDataCluster, MotionWithReset, OccupancyOnEvent
from zhaquirks.const import (
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_SINGLE,
    PRESS_TYPE,
    ZHA_SEND_EVENT,
)

KONKE = "Konke"


class KonkeButtonEvent(t.enum8):
    """Konke button event."""

    Single = 0x80
    Double = 0x81
    Hold = 0x82


PRESS_TYPES = {
    KonkeButtonEvent.Single: COMMAND_SINGLE,
    KonkeButtonEvent.Double: COMMAND_DOUBLE,
    KonkeButtonEvent.Hold: COMMAND_HOLD,
}


class OccupancyCluster(LocalDataCluster, OccupancyOnEvent):
    """Occupancy cluster."""

    reset_s: int = 600


class MotionCluster(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60
    send_occupancy_event: bool = True


class KonkeOnOffCluster(CustomCluster):
    """Konke OnOff cluster implementation."""

    cluster_id = OnOff.cluster_id
    ep_attribute = "konke_on_off"

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        konke_button_event: Final = ZCLAttributeDef(id=0x0000, type=KonkeButtonEvent)

    def handle_cluster_general_request(
        self,
        header: zigpy.zcl.foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ):
        """Handle the cluster command."""
        self.info(
            "Konke general request - handle_cluster_general_request: header: %s - args: [%s]",
            header,
            args,
        )

        if header.command_id == zigpy.zcl.foundation.GeneralCommand.Report_Attributes:
            remaining_reports = []

            for attr in args.attribute_reports:
                if attr.attrid != self.AttributeDefs.konke_button_event.id:
                    remaining_reports.append(attr)
                    continue

                value = attr.value.value
                press_type = PRESS_TYPES.get(value)
                if press_type is None:
                    self.debug("Unknown Konke button event: %s", value)
                    continue

                event_args = {
                    PRESS_TYPE: press_type,
                    COMMAND_ID: int(value),  # to maintain backwards compatibility
                }
                self.listener_event(ZHA_SEND_EVENT, event_args[PRESS_TYPE], event_args)

            # Button events aren't attribute updates, pass on everything else
            args.attribute_reports = remaining_reports

        # Always process the request, to send any requested default response
        super().handle_cluster_general_request(
            header, args, dst_addressing=dst_addressing
        )
