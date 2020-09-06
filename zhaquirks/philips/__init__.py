"""Module for Philips quirks implementations."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, OnOff

from ..const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_ID,
    DIM_DOWN,
    DIM_UP,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    SHORT_PRESS,
    SHORT_RELEASE,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
PHILIPS = "Philips"
_LOGGER = logging.getLogger(__name__)

HUE_REMOTE_DEVICE_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {COMMAND: "on_press"},
    (SHORT_PRESS, TURN_OFF): {COMMAND: "off_press"},
    (SHORT_PRESS, DIM_UP): {COMMAND: "up_press"},
    (SHORT_PRESS, DIM_DOWN): {COMMAND: "down_press"},
    (LONG_PRESS, TURN_ON): {COMMAND: "on_hold"},
    (LONG_PRESS, TURN_OFF): {COMMAND: "off_hold"},
    (LONG_PRESS, DIM_UP): {COMMAND: "up_hold"},
    (LONG_PRESS, DIM_DOWN): {COMMAND: "down_hold"},
    (SHORT_RELEASE, TURN_ON): {COMMAND: "on_short_release"},
    (SHORT_RELEASE, TURN_OFF): {COMMAND: "off_short_release"},
    (SHORT_RELEASE, DIM_UP): {COMMAND: "up_short_release"},
    (SHORT_RELEASE, DIM_DOWN): {COMMAND: "down_short_release"},
    (LONG_RELEASE, TURN_ON): {COMMAND: "on_long_release"},
    (LONG_RELEASE, TURN_OFF): {COMMAND: "off_long_release"},
    (LONG_RELEASE, DIM_UP): {COMMAND: "up_long_release"},
    (LONG_RELEASE, DIM_DOWN): {COMMAND: "down_long_release"},
}


class PowerOnState(t.enum8):
    """Philips power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0xFF


class PhilipsOnOffCluster(CustomCluster, OnOff):
    """Philips OnOff cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update({0x4003: ("power_on_state", PowerOnState)})


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    manufacturer_attributes = {0x0031: ("philips", t.bitmap16)}

    attr_config = {0x0031: 0x000B}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=0x100B)
        return result


class PhilipsRemoteCluster(CustomCluster):
    """Philips remote cluster."""

    cluster_id = 64512
    name = "PhilipsRemoteCluster"
    ep_attribute = "philips_remote_cluster"
    manufacturer_client_commands = {
        0x0000: (
            "notification",
            (t.uint8_t, t.uint24_t, t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        )
    }
    BUTTONS = {1: "on", 2: "up", 3: "down", 4: "off"}
    PRESS_TYPES = {0: "press", 1: "hold", 2: "short_release", 3: "long_release"}

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        _LOGGER.debug(
            "PhilipsRemoteCluster - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )
        button = self.BUTTONS.get(args[0], args[0])
        press_type = self.PRESS_TYPES.get(args[2], args[2])

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
            COMMAND_ID: command_id,
            ARGS: args,
        }
        action = "{}_{}".format(button, press_type)
        self.listener_event(ZHA_SEND_EVENT, action, event_args)
