"""Konke sensors."""
from typing import Any, List, Optional, Union

import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
import zigpy.zcl.foundation

from .. import CustomCluster, LocalDataCluster, MotionWithReset, OccupancyOnEvent
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
    manufacturer_attributes = {0x0000: (PRESS_TYPE, t.uint8_t)}

    def handle_cluster_general_request(
        self,
        header: zigpy.zcl.foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        self.info(
            "Konke general request - handle_cluster_general_request: header: %s - args: [%s]",
            header,
            args,
        )

        if header.command_id != zigpy.zcl.foundation.Command.Report_Attributes:
            return

        attr = args[0][0]
        if attr.attrid != 0x0000:
            return

        value = attr.value.value
        event_args = {
            PRESS_TYPE: self.PRESS_TYPES.get(value, value),
            COMMAND_ID: value,
        }
        self.listener_event(ZHA_SEND_EVENT, event_args[PRESS_TYPE], event_args)

    def deserialize(self, data):
        """Deserialize fix for Konke butchered Bool ZCL type."""
        try:
            return super().deserialize(data)
        except ValueError:
            hdr, data = zigpy.zcl.foundation.ZCLHeader.deserialize(data)
            if (
                hdr.frame_control.is_cluster
                or hdr.command_id != zigpy.zcl.foundation.Command.Report_Attributes
            ):
                raise
            attr_id, data = t.uint16_t.deserialize(data)
            attr = zigpy.zcl.foundation.Attribute(
                attr_id, zigpy.zcl.foundation.TypeValue(t.uint8_t, data[1])
            )
            return hdr, [[attr]]
