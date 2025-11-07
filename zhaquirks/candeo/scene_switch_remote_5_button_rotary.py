"""Candeo c-zb-sr5br 5-button remote with rotating dial."""

from typing import Final, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

from zhaquirks.candeo import CANDEO
from zhaquirks.const import (
    ARGS,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_CENTRE,
    COMMAND,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_PRESS,
    COMMAND_RELEASE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    CONTINUED_ROTATING,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    RIGHT,
    ROTATED,
    SHORT_PRESS,
    STARTED_ROTATING,
    STOPPED_ROTATING_WITH_DIRECTION,
    ZHA_SEND_EVENT,
)


class CandeoSceneSwitchRemoteMessageType(t.enum8):
    """Candeo Scene Switch Remote Message Type."""

    button_press = 0x01
    ring_rotation = 0x03


class CandeoSceneSwitchRemoteButtonNumberMap(t.enum8):
    """Candeo Scene Switch Remote Button Number Map."""

    button_1 = 0x01
    button_2 = 0x02
    button_3 = 0x04
    button_4 = 0x08
    button_centre = 0x10


class CandeoSceneSwitchRemoteButtonActionMap(t.enum8):
    """Candeo Scene Switch Remote Button Action Map."""

    press = 0x01
    double_press = 0x02
    hold = 0x03
    release = 0x04


class CandeoSceneSwitchRemoteRingDirectionMap(t.enum8):
    """Candeo Scene Switch Remote Ring Direction Map."""

    right = 0x01
    left = 0x02


class CandeoSceneSwitchRemoteRingActionMap(t.enum8):
    """Candeo Scene Switch Remote Ring Action Map."""

    started_rotating = 0x01
    stopped_rotating = 0x02
    continued_rotating = 0x03


class CandeoSceneSwitchRemoteClusterCommand(t.Struct):
    """CandeoSceneSwitchRemoteClusterCommand."""

    message_type: CandeoSceneSwitchRemoteMessageType
    field_1: t.uint8_t
    field_2: t.uint8_t
    field_3: t.uint8_t


class CandeoSceneSwitchRemoteCluster(CustomCluster):
    """CandeoSceneSwitchRemoteCluster: fire events corresponding to button press or ring rotation."""

    cluster_id: Final[t.uint16_t] = 0xFF03
    name = "CandeoSceneSwitchRemoteCluster_Cluster"
    ep_attribute = "CandeoSceneSwitchRemoteCluster_Cluster"

    class ServerCommandDefs(BaseCommandDefs):
        """overwrite ServerCommandDefs."""

        candeo_scene_switch_remote: Final = ZCLCommandDef(
            id=0x01,
            schema=CandeoSceneSwitchRemoteClusterCommand,
            is_manufacturer_specific=True,
        )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration to bind cluster."""
        await self.bind()

    def __init__(self, *args, **kwargs):
        """__init___."""
        self.last_tsn = -1
        self.previous_rotation_direction = "unknown"
        self.previous_rotation_event = COMMAND_STOPPED_ROTATING
        super().__init__(*args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: tuple[CandeoSceneSwitchRemoteClusterCommand],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Overwrite handle_cluster_request to custom process this cluster."""
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)
        if hdr.tsn == self.last_tsn:
            return
        self.last_tsn = hdr.tsn
        if (
            hdr.command_id == self.ServerCommandDefs.candeo_scene_switch_remote.id
            and CandeoSceneSwitchRemoteMessageType(args.message_type)
            and args.field_1 is not None
            and args.field_2 is not None
            and args.field_3 is not None
        ):
            if (
                args.message_type == CandeoSceneSwitchRemoteMessageType.button_press
                and CandeoSceneSwitchRemoteButtonNumberMap(args.field_2)
                and CandeoSceneSwitchRemoteButtonActionMap(args.field_3)
            ):
                button_number = CandeoSceneSwitchRemoteButtonNumberMap(
                    args.field_2
                ).name
                button_action = CandeoSceneSwitchRemoteButtonActionMap(
                    args.field_3
                ).name
                self.listener_event(
                    ZHA_SEND_EVENT, button_action, {BUTTON: button_number}
                )
            elif (
                args.message_type == CandeoSceneSwitchRemoteMessageType.ring_rotation
                and CandeoSceneSwitchRemoteRingActionMap(args.field_2)
            ):
                ring_action = CandeoSceneSwitchRemoteRingActionMap(args.field_2).name
                if ring_action == COMMAND_STOPPED_ROTATING:
                    if self.previous_rotation_direction != "unknown":
                        self.listener_event(
                            ZHA_SEND_EVENT,
                            COMMAND_STOPPED_ROTATING,
                            {ROTATED: self.previous_rotation_direction},
                        )
                    self.previous_rotation_event = COMMAND_STOPPED_ROTATING
                elif CandeoSceneSwitchRemoteRingDirectionMap(args.field_1):
                    ring_direction = CandeoSceneSwitchRemoteRingDirectionMap(
                        args.field_1
                    ).name
                    ring_clicks = args.field_3
                    if self.previous_rotation_event == COMMAND_STOPPED_ROTATING:
                        self.listener_event(
                            ZHA_SEND_EVENT,
                            COMMAND_STARTED_ROTATING,
                            {ROTATED: ring_direction},
                        )
                        self.previous_rotation_event = COMMAND_STARTED_ROTATING
                        if ring_clicks > 1:
                            for _x in range(1, ring_clicks):
                                self.listener_event(
                                    ZHA_SEND_EVENT,
                                    COMMAND_CONTINUED_ROTATING,
                                    {ROTATED: ring_direction},
                                )
                            self.previous_rotation_event = COMMAND_CONTINUED_ROTATING
                    elif self.previous_rotation_event in {
                        COMMAND_STARTED_ROTATING,
                        COMMAND_CONTINUED_ROTATING,
                    }:
                        self.listener_event(
                            ZHA_SEND_EVENT,
                            COMMAND_CONTINUED_ROTATING,
                            {ROTATED: ring_direction},
                        )
                        if ring_clicks > 1:
                            for _x in range(1, ring_clicks):
                                self.listener_event(
                                    ZHA_SEND_EVENT,
                                    COMMAND_CONTINUED_ROTATING,
                                    {ROTATED: ring_direction},
                                )
                        self.previous_rotation_event = COMMAND_CONTINUED_ROTATING
                    self.previous_rotation_direction = ring_direction


(
    QuirkBuilder(CANDEO, "C-ZB-SR5BR")
    .replaces(CandeoSceneSwitchRemoteCluster)
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_PRESS,
                ARGS: {BUTTON: BUTTON_1},
            },
            (DOUBLE_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_DOUBLE,
                ARGS: {BUTTON: BUTTON_1},
            },
            (LONG_PRESS, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_HOLD,
                ARGS: {BUTTON: BUTTON_1},
            },
            (LONG_RELEASE, BUTTON_1): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_RELEASE,
                ARGS: {BUTTON: BUTTON_1},
            },
            (SHORT_PRESS, BUTTON_2): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_PRESS,
                ARGS: {BUTTON: BUTTON_2},
            },
            (DOUBLE_PRESS, BUTTON_2): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_DOUBLE,
                ARGS: {BUTTON: BUTTON_2},
            },
            (LONG_PRESS, BUTTON_2): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_HOLD,
                ARGS: {BUTTON: BUTTON_2},
            },
            (LONG_RELEASE, BUTTON_2): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_RELEASE,
                ARGS: {BUTTON: BUTTON_2},
            },
            (SHORT_PRESS, BUTTON_3): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_PRESS,
                ARGS: {BUTTON: BUTTON_3},
            },
            (DOUBLE_PRESS, BUTTON_3): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_DOUBLE,
                ARGS: {BUTTON: BUTTON_3},
            },
            (LONG_PRESS, BUTTON_3): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_HOLD,
                ARGS: {BUTTON: BUTTON_3},
            },
            (LONG_RELEASE, BUTTON_3): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_RELEASE,
                ARGS: {BUTTON: BUTTON_3},
            },
            (SHORT_PRESS, BUTTON_4): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_PRESS,
                ARGS: {BUTTON: BUTTON_4},
            },
            (DOUBLE_PRESS, BUTTON_4): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_DOUBLE,
                ARGS: {BUTTON: BUTTON_4},
            },
            (LONG_PRESS, BUTTON_4): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_HOLD,
                ARGS: {BUTTON: BUTTON_4},
            },
            (LONG_RELEASE, BUTTON_4): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_RELEASE,
                ARGS: {BUTTON: BUTTON_4},
            },
            (SHORT_PRESS, BUTTON_CENTRE): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_PRESS,
                ARGS: {BUTTON: BUTTON_CENTRE},
            },
            (DOUBLE_PRESS, BUTTON_CENTRE): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_DOUBLE,
                ARGS: {BUTTON: BUTTON_CENTRE},
            },
            (LONG_PRESS, BUTTON_CENTRE): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_HOLD,
                ARGS: {BUTTON: BUTTON_CENTRE},
            },
            (LONG_RELEASE, BUTTON_CENTRE): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_RELEASE,
                ARGS: {BUTTON: BUTTON_CENTRE},
            },
            (STARTED_ROTATING, LEFT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_STARTED_ROTATING,
                ARGS: {ROTATED: LEFT},
            },
            (CONTINUED_ROTATING, LEFT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_CONTINUED_ROTATING,
                ARGS: {ROTATED: LEFT},
            },
            (STOPPED_ROTATING_WITH_DIRECTION, LEFT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_STOPPED_ROTATING,
                ARGS: {ROTATED: LEFT},
            },
            (STARTED_ROTATING, RIGHT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_STARTED_ROTATING,
                ARGS: {ROTATED: RIGHT},
            },
            (CONTINUED_ROTATING, RIGHT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_CONTINUED_ROTATING,
                ARGS: {ROTATED: RIGHT},
            },
            (STOPPED_ROTATING_WITH_DIRECTION, RIGHT): {
                ENDPOINT_ID: 1,
                COMMAND: COMMAND_STOPPED_ROTATING,
                ARGS: {ROTATED: RIGHT},
            },
        }
    )
    .add_to_registry()
)
