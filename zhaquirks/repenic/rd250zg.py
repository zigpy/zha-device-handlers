"""Repenic RD-250ZG Dimmer."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff

from zhaquirks import EventableCluster, NoReplyMixin
from zhaquirks.const import (
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)


class PressType(t.enum8):
    """Press type enum."""

    triple_click = 0x010
    long_press = 0x02
    release = 0x04
    double_click = 0x08


class RepenicPressureCluster(EventableCluster):
    """Private cluster 0xE004 for pressure events."""

    cluster_id = 0xE004
    name = "Repenic Pressure"
    ep_attribute = "repenic_pressure"

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        """Handle cluster request."""
        self.debug(
            "RepenicPressureCluster cluster request: command_id=0x%02x args=%r",
            hdr.command_id,
            args,
        )
        if hdr.command_id == 0x00 and len(args) > 1:
            press_value = args[1]
            press_command = None
            if press_value == int(PressType.double_click):
                press_command = COMMAND_DOUBLE
            elif press_value == int(PressType.triple_click):
                press_command = COMMAND_TRIPLE
            elif press_value == int(PressType.long_press):
                press_command = COMMAND_HOLD
            elif press_value == int(PressType.release):
                press_command = COMMAND_RELEASE

            if press_command is not None:
                self.listener_event(ZHA_SEND_EVENT, press_command, {VALUE: press_value})
        return super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


class SceneMode(t.enum8):
    """Scene mode enum."""

    Off = 0
    On = 1


class RepenicSceneModeCluster(CustomCluster):
    """Private cluster 0xE003 for scene mode."""

    cluster_id = 0xE003
    name = "Repenic Scene Mode"
    ep_attribute = "repenic_scene_mode"
    attributes = {
        0x0003: ("scene_mode", SceneMode, False),
    }


class DimmingMode(t.enum8):
    """Dimming mode enum."""

    Leading_edge = 0
    Trailing_edge = 1


class RepenicOnOff(NoReplyMixin, CustomCluster, OnOff):
    """Repenic On Off Cluster with optimistic state updates."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


class RepenicLevelControl(NoReplyMixin, CustomCluster, LevelControl):
    """Repenic LevelControl Cluster."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}

    attributes = LevelControl.attributes.copy()
    attributes.update(
        {
            0xA000: ("min_brightness", t.uint8_t, False),
            0xA003: ("max_brightness", t.uint8_t, False),
            0xA004: ("boost", t.uint8_t, False),
            0xB000: ("dimming_mode", DimmingMode, False),
        }
    )


(
    QuirkBuilder("Repenic Ltd.", "RD-250ZG")
    .replaces(RepenicLevelControl)
    .replaces(RepenicSceneModeCluster)
    .replaces(RepenicPressureCluster)
    .replaces(RepenicOnOff)
    .number(
        attribute_name="min_brightness",
        cluster_id=RepenicLevelControl.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="min_brightness",
        fallback_name="Minimum brightness",
    )
    .number(
        attribute_name="max_brightness",
        cluster_id=RepenicLevelControl.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        attribute_initialized_from_cache=True,
        translation_key="max_brightness",
        fallback_name="Maximum brightness",
    )
    .switch(
        attribute_name="boost",
        cluster_id=RepenicLevelControl.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="boost",
        fallback_name="Boost",
    )
    .enum(
        attribute_name="dimming_mode",
        enum_class=DimmingMode,
        cluster_id=RepenicLevelControl.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="dimming_mode",
        fallback_name="Dimming mode",
    )
    .enum(
        attribute_name="scene_mode",
        enum_class=SceneMode,
        cluster_id=RepenicSceneModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="scene_mode",
        fallback_name="Scene mode",
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, BUTTON): {
                COMMAND: COMMAND_DOUBLE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (TRIPLE_PRESS, BUTTON): {
                COMMAND: COMMAND_TRIPLE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_PRESS, BUTTON): {
                COMMAND: COMMAND_HOLD,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
            (LONG_RELEASE, BUTTON): {
                COMMAND: COMMAND_RELEASE,
                CLUSTER_ID: RepenicPressureCluster.cluster_id,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
