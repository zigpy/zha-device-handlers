"""Tuya devices."""
import logging
from typing import Optional, Tuple, Union

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

from .. import Bus

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


class TuyaManufClusterAttributes(TuyaManufCluster):
    """Manufacturer specific cluster for Tuya converting attributes <-> commands."""

    def handle_cluster_request(self, tsn: int, command_id: int, args: Tuple) -> None:
        """Handle cluster request."""
        if command_id not in (0x0001, 0x0002):
            return super().handle_cluster_request(tsn, command_id, args)

        tuya_cmd = args[0].command_id
        tuya_value = args[0].data[1:]  # first uint8_t is length

        _LOGGER.debug(
            "[0x%04x:%s:0x%04x] Received value %s "
            "for attribute 0x%04x (command 0x%04x)",
            self.endpoint.device.nwk,
            self.endpoint.endpoint_id,
            self.cluster_id,
            repr(tuya_value),
            tuya_cmd,
            command_id,
        )

        if tuya_cmd not in self.attributes:
            return

        # tuya data is in big endian whereas ztypes use little endian
        ztype = self.attributes[tuya_cmd][1]
        zvalue, _ = ztype.deserialize(bytes(reversed(tuya_value)))
        self._update_attribute(tuya_cmd, zvalue)

    def read_attributes(
        self, attributes, allow_cache=False, only_cache=False, manufacturer=None
    ):
        """Ignore remote reads as the "get_data" command doesn't seem to do anything."""

        return super().read_attributes(
            attributes, allow_cache=True, only_cache=True, manufacturer=manufacturer
        )

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_data tuya command."""

        records = self._write_attr_records(attributes)

        for record in records:
            # serialized in little-endian
            data = list(record.value.value.serialize())
            # we want big-endian, with length prepended
            data.append(len(data))
            data.reverse()

            cmd_payload = TuyaManufCluster.Command()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            cmd_payload.command_id = record.attrid
            cmd_payload.function = 0
            cmd_payload.data = data

            await super().command(
                TUYA_SET_DATA,
                cmd_payload,
                manufacturer=manufacturer,
                expect_reply=False,
                tsn=cmd_payload.tsn,
            )

        return (foundation.Status.SUCCESS,)


class TuyaOnOff(CustomCluster, OnOff):
    """Tuya On/Off cluster for On/Off device."""

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

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""

        if command_id in (0x0000, 0x0001):
            cmd_payload = TuyaManufCluster.Command()
            cmd_payload.status = 0
            cmd_payload.tsn = 0
            cmd_payload.command_id = TUYA_CMD_BASE + self.endpoint.endpoint_id
            cmd_payload.function = 0
            cmd_payload.data = [1, command_id]

            return self.endpoint.tuya_manufacturer.command(
                TUYA_SET_DATA, cmd_payload, expect_reply=True
            )

        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaManufacturerClusterOnOff(TuyaManufCluster):
    """Manufacturer Specific Cluster of On/Off device."""

    def handle_cluster_request(
        self, tsn: int, command_id: int, args: Tuple[TuyaManufCluster.Command]
    ) -> None:
        """Handle cluster request."""

        tuya_payload = args[0]
        if command_id in (0x0002, 0x0001):
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
