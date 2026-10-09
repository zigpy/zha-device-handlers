"""Quirk for HOBEIAN ZG-101ZD rotary dimmer knob."""

from typing import Any, Final

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import ZCLHeader

from zhaquirks import CustomCluster


class HobeianOnOffCluster(CustomCluster, OnOff):
    """Custom OnOff cluster for HOBEIAN rotation commands.

    This device uses proprietary commands on OnOff cluster for rotation:
    - 0xFC + 0x00/0x01: Rotation direction (right/left)
    - 0x03: Rotation step right
    - 0x04: Rotation step left
    - 0xFD: Button press indicator
    - 0x02: Standard toggle
    """

    cluster_id: Final = OnOff.cluster_id

    ROTATION_DIRECTION_CMD: Final = 0xFC
    ROTATION_STEP_RIGHT_CMD: Final = 0x03
    ROTATION_STEP_LEFT_CMD: Final = 0x04
    BUTTON_PRESS_INDICATOR_CMD: Final = 0xFD
    TOGGLE_CMD: Final = 0x02

    DIRECTION_RIGHT: Final = 0x00
    DIRECTION_LEFT: Final = 0x01

    def handle_cluster_request(
        self,
        hdr: ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.Addressing.Group
        | t.Addressing.IEEE
        | t.Addressing.NWK
        | None = None,
    ) -> None:
        """Handle incoming cluster commands including proprietary rotation."""
        command_id = hdr.command_id

        if command_id == self.ROTATION_DIRECTION_CMD:
            direction = 0
            if args:
                raw_data = args[0]
                if isinstance(raw_data, bytes) and raw_data:
                    direction = raw_data[0]
                elif isinstance(raw_data, int):
                    direction = raw_data
            self.listener_event(
                "zha_send_event",
                "rotation_direction",
                {
                    "direction": "right"
                    if direction == self.DIRECTION_RIGHT
                    else "left",
                    "direction_raw": direction,
                },
            )
            return

        if command_id == self.ROTATION_STEP_RIGHT_CMD:
            self.listener_event(
                "zha_send_event",
                "step_with_on_off",
                {"step_mode": 0, "step_size": 13, "transition_time": 1},
            )
            return

        if command_id == self.ROTATION_STEP_LEFT_CMD:
            self.listener_event(
                "zha_send_event",
                "step_with_on_off",
                {"step_mode": 1, "step_size": 13, "transition_time": 1},
            )
            return

        if command_id == self.BUTTON_PRESS_INDICATOR_CMD:
            return

        if command_id == self.TOGGLE_CMD:
            self.listener_event("zha_send_event", "toggle", {})
            return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder("HOBEIAN", "ZG-101ZD")
    .replaces(HobeianOnOffCluster)
    .replaces(HobeianOnOffCluster, cluster_type="out")
    .device_automation_triggers(
        {
            ("remote_button_short_press", "toggle"): {
                "command": "toggle",
                "cluster_id": 6,
                "endpoint_id": 1,
            },
            ("dim_up", "dim_up"): {
                "command": "step_with_on_off",
                "cluster_id": 6,
                "endpoint_id": 1,
                "args": {"step_mode": 0},
            },
            ("dim_down", "dim_down"): {
                "command": "step_with_on_off",
                "cluster_id": 6,
                "endpoint_id": 1,
                "args": {"step_mode": 1},
            },
        }
    )
    .add_to_registry()
)
