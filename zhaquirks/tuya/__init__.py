"""Tuya devices."""
import logging

from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl import foundation
import zigpy.types as t

from .. import Bus
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

TUYA_CLUSTER_ID = 0xEF00
TUYA_SET_DATA = 0x0000
TUYA_GET_DATA = 0x0001
TUYA_SET_DATA_RESPONSE = 0x0002

SWITCH_EVENT = "switch_event"
ATTR_ON_OFF = 0x0000
TUYA_CMD_BASE = 0x0100

_LOGGER = logging.getLogger(__name__)


class Data(t.List, item_type=t.uint8_t):
    """list of uint8_t."""


class TuyaManufCluster(CustomCluster):
    """Tuya manufacturer specific cluster."""

    name = "Tuya Manufacturer Specicific"
    cluster_id = TUYA_CLUSTER_ID
    ep_attribute = "tuya_manufacturer"

    class Command(t.Struct):
        """Tuya manufacturer cluster command."""

        status: t.uint8_t
        tsn: t.uint8_t
        command_id: t.uint16_t
        function: t.uint8_t
        data: Data

    manufacturer_server_commands = {0x0000: ("set_data", (Command,), False)}

    manufacturer_client_commands = {
        0x0001: ("get_data", (Command,), True),
        0x0002: ("set_data_response", (Command,), True),
    }


class TuyaOnOff(CustomCluster, OnOff):
    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.switch_bus.add_listener(self)

    def switch_event(self, channel, state):
        """Switch event."""
        _LOGGER.debug(
            "%s - Received switch event message, channel: %d, state: %d",
            self.endpoint.device.ieee,
            channel,
            state,
        )
        self._update_attribute(ATTR_ON_OFF, state)

    async def command(self, command, *args, manufacturer=None, expect_reply=None):
        """Override the default Cluster command."""

        if command == 0x0000 or command == 0x0001:
            cmd_payload = TuyaManufCluster.Command()
            cmd_payload.status = 0
            cmd_payload.tsn = 0
            cmd_payload.command_id = TUYA_CMD_BASE + self.endpoint.endpoint_id
            cmd_payload.function = 0
            cmd_payload.data = [1, command]
            return await self.endpoint.tuya_manufacturer.command(
                TUYA_SET_DATA, cmd_payload, expect_reply=True
            )
        else:
            return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaManufacturerClusterOnOff(TuyaManufCluster):
    """Manufacturer Specific Cluster of the Motion device."""

    def handle_cluster_request(
        self, tsn: int, command_id: int, args: Tuple[TuyaManufCluster.Command]
    ) -> None:
        """Handle cluster request."""

        tuya_payload = args[0]
        if command_id == 0x0002 or command_id == 0x0001:
            self.endpoint.device.switch_bus.listener_event(
                SWITCH_EVENT,
                tuya_payload.command_id - TUYA_CMD_BASE,
                tuya_payload.data[1],
            )


class TuyaSwitch(CustomDevice):
    """Tuya switch device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.switch_bus = Bus()
        super().__init__(*args, **kwargs)
