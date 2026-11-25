"""Device handler for IKEA of Sweden TRADFRI remote control."""

import time
from typing import Any, Final, cast

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff, Scenes

from zhaquirks import CustomCluster, LevelControlWithMoveDirection
from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_MOVE,
    COMMAND_MOVE_DOWN_RELEASE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_MOVE_UP_RELEASE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    RIGHT,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ikea import IKEA, DoublingPowerConfig2AAACluster, ScenesCluster

# The remote opens every arrow long press with a Scenes `release` of 0, and about half
# a second later, while the arrow is still held, it sends an `on` that no button press
# caused: https://github.com/Koenkk/zigbee2mqtt/issues/13335. An arrow press let go
# before the hold sends the `release` of 0 alone. Short arrow presses send a Scenes
# `press` instead, and the release ending an arrow hold carries the hold's duration,
# so only a `release` of 0 marks the start of a possible arrow hold. Every `on` within
# this many seconds of it is dropped, also a second copy of the frame, which zigpy
# doesn't drop when it arrives over another route. The measured gap is 0.4 to 0.5
# seconds; Zigbee2MQTT uses 0.7 seconds.
STRAY_ON_WINDOW: Final = 0.7


class StyrbarScenesCluster(ScenesCluster):
    """IKEA Scenes cluster noting when an arrow long press may start."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self.arrow_hold_started: float | None = None

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        # This parameter is unused and kept only for backwards compatibility
        dst_addressing: t.AddrMode | None = None,
    ):
        """Note the `release` of 0 that opens an arrow long press.

        Any other Scenes command means the arrow hold's `on` has passed or won't come.
        """
        if hdr.command_id == self.ServerCommandDefs.release.id and args[0] == 0:
            self.arrow_hold_started = time.monotonic()
        else:
            self.arrow_hold_started = None

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class StyrbarOnOffCluster(CustomCluster, OnOff):
    """On/Off cluster dropping the `on` the remote sends at the start of an arrow hold.

    Dropping it here keeps it from the device's `zha_event`s, so neither the on
    button's device trigger nor anything else sees a press that didn't happen.
    """

    def handle_message(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
    ) -> None:
        """Handle a message, unless it is the `on` of an arrow hold."""
        if (
            hdr.frame_control.is_cluster
            and hdr.command_id == OnOff.ServerCommandDefs.on.id
            and self._arrow_hold_started_recently()
        ):
            self.debug(
                "Dropping the `on` the remote sends at the start of an arrow hold"
            )
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(hdr, foundation.Status.SUCCESS)
            return

        super().handle_message(hdr, args)

    def _arrow_hold_started_recently(self) -> bool:
        """Return whether an arrow long press may have started within the window."""
        # The quirk always puts StyrbarScenesCluster on this endpoint
        scenes = cast(
            StyrbarScenesCluster, self.endpoint.out_clusters[Scenes.cluster_id]
        )
        started = scenes.arrow_hold_started
        return started is not None and time.monotonic() - started <= STRAY_ON_WINDOW


(
    QuirkBuilder(IKEA, "Remote Control N2")
    .replaces(DoublingPowerConfig2AAACluster)  # will only double for old firmware
    .replaces(StyrbarScenesCluster, cluster_type=ClusterType.Client)
    .replaces(StyrbarOnOffCluster, cluster_type=ClusterType.Client)
    .replaces(LevelControlWithMoveDirection, cluster_type=ClusterType.Client)
    .device_automation_triggers(
        {
            (SHORT_PRESS, TURN_ON): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_UP): {
                COMMAND: COMMAND_MOVE_ON_OFF,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 0},
            },
            (LONG_RELEASE, DIM_UP): {
                COMMAND: COMMAND_MOVE_UP_RELEASE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, TURN_OFF): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, DIM_DOWN): {
                COMMAND: COMMAND_MOVE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"move_mode": 1},
            },
            (LONG_RELEASE, DIM_DOWN): {
                COMMAND: COMMAND_MOVE_DOWN_RELEASE,
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
            },
            (SHORT_PRESS, LEFT): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 257,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (LONG_PRESS, LEFT): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 3329,
                    "param2": 0,
                },
            },
            (SHORT_PRESS, RIGHT): {
                COMMAND: COMMAND_PRESS,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 256,
                    "param2": 13,
                    "param3": 0,
                },
            },
            (LONG_PRESS, RIGHT): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: 5,
                ENDPOINT_ID: 1,
                PARAMS: {
                    "param1": 3328,
                    "param2": 0,
                },
            },
        }
    )
    # The `on` the remote sends at the start of every arrow long press is dropped by
    # `StyrbarOnOffCluster`, so it doesn't fire a press of the on button.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_ON)
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, DIM_UP),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, DIM_UP),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_on",
        translation_key="on_button",
        fallback_name="On button",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, TURN_OFF)
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, DIM_DOWN),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, DIM_DOWN),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_off",
        translation_key="off_button",
        fallback_name="Off button",
    )
    # The arrows send the same release, so it ends the hold of the arrow held
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, LEFT)
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START, trigger=(LONG_PRESS, LEFT)
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                event_data={
                    COMMAND: COMMAND_RELEASE,
                    CLUSTER_ID: Scenes.cluster_id,
                    ENDPOINT_ID: 1,
                },
                while_held=True,
            ),
        ],
        cluster_id=Scenes.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_left",
        translation_key="left_button",
        fallback_name="Left button",
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_END, trigger=(SHORT_PRESS, RIGHT)
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, RIGHT),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                event_data={
                    COMMAND: COMMAND_RELEASE,
                    CLUSTER_ID: Scenes.cluster_id,
                    ENDPOINT_ID: 1,
                },
                while_held=True,
            ),
        ],
        cluster_id=Scenes.cluster_id,
        cluster_type=ClusterType.Client,
        unique_id_suffix="button_right",
        translation_key="right_button",
        fallback_name="Right button",
    )
    .add_to_registry()
)
