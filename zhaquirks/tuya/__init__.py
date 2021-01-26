"""Tuya devices."""
import datetime
import logging
from typing import Any, List, Optional, Tuple, Union

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from .. import Bus, EventableCluster, LocalDataCluster
from ..const import DOUBLE_PRESS, LONG_PRESS, SHORT_PRESS, ZHA_SEND_EVENT

TUYA_CLUSTER_ID = 0xEF00
TUYA_SET_DATA = 0x0000
TUYA_GET_DATA = 0x0001
TUYA_SET_DATA_RESPONSE = 0x0002
TUYA_SET_TIME = 0x0024

SWITCH_EVENT = "switch_event"
ATTR_ON_OFF = 0x0000
TUYA_CMD_BASE = 0x0100

_LOGGER = logging.getLogger(__name__)


class BigEndianInt16(int):
    """Helper class to represent big endian 16 bit value."""

    def serialize(self) -> bytes:
        """Value serialisation."""

        try:
            return self.to_bytes(2, "big", signed=False)
        except OverflowError as e:
            # OverflowError is not a subclass of ValueError, making it annoying to catch
            raise ValueError(str(e)) from e

    @classmethod
    def deserialize(cls, data: bytes) -> Tuple["BigEndianInt16", bytes]:
        """Value deserialisation."""

        if len(data) < 2:
            raise ValueError(f"Data is too short to contain {cls._size} bytes")

        r = cls.from_bytes(data[:2], "big", signed=False)
        data = data[2:]
        return r, data


class TuyaTimePayload(t.LVList, item_type=t.uint8_t, length_type=BigEndianInt16):
    """Tuya set time payload definition."""

    pass


class Data(t.List, item_type=t.uint8_t):
    """list of uint8_t."""

    @classmethod
    def from_value(cls, value):
        """Convert from a zigpy typed value to a tuya data payload."""
        # serialized in little-endian by zigpy
        data = cls(value.serialize())
        # we want big-endian, with length prepended
        data.append(len(data))
        data.reverse()
        return data

    def to_value(self, ztype):
        """Convert from a tuya data payload to a zigpy typed value."""
        # first uint8_t is the length of the remaining data
        # tuya data is in big endian whereas ztypes use little endian
        value, _ = ztype.deserialize(bytes(reversed(self[1:])))
        return value


class TuyaManufCluster(CustomCluster):
    """Tuya manufacturer specific cluster."""

    name = "Tuya Manufacturer Specicific"
    cluster_id = TUYA_CLUSTER_ID
    ep_attribute = "tuya_manufacturer"
    set_time_offset = 0

    class Command(t.Struct):
        """Tuya manufacturer cluster command."""

        status: t.uint8_t
        tsn: t.uint8_t
        command_id: t.uint16_t
        function: t.uint8_t
        data: Data

    """ Time sync command (It's transparent between MCU and server)
            Time request device -> server
               payloadSize = 0
            Set time, server -> device
               payloadSize, should be always 8
               payload[0-3] - UTC timestamp (big endian)
               payload[4-7] - Local timestamp (big endian)

            Zigbee payload is very similar to the UART payload which is described here: https://developer.tuya.com/en/docs/iot/device-development/access-mode-mcu/zigbee-general-solution/tuya-zigbee-module-uart-communication-protocol/tuya-zigbee-module-uart-communication-protocol?id=K9ear5khsqoty#title-10-Time%20synchronization

            Some devices need the timestamp in seconds from 1/1/1970 and others in seconds from 1/1/2000.

            NOTE: You need to wait for time request before setting it. You can't set time without request."""

    manufacturer_server_commands = {
        0x0000: ("set_data", (Command,), False),
        0x0024: ("set_time", (TuyaTimePayload,), False),
    }

    manufacturer_client_commands = {
        0x0001: ("get_data", (Command,), True),
        0x0002: ("set_data_response", (Command,), True),
        0x0024: ("set_time_request", (TuyaTimePayload,), True),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple,
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle time request."""

        if hdr.command_id != 0x0024 or self.set_time_offset == 0:
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        # Send default response because the MCU expects it
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        _LOGGER.debug(
            "[0x%04x:%s:0x%04x] Got set time request (command 0x%04x)",
            self.endpoint.device.nwk,
            self.endpoint.endpoint_id,
            self.cluster_id,
            hdr.command_id,
        )
        payload = TuyaTimePayload()
        utc_timestamp = int(
            (
                datetime.datetime.utcnow()
                - datetime.datetime(self.set_time_offset, 1, 1)
            ).total_seconds()
        )
        local_timestamp = int(
            (
                datetime.datetime.now() - datetime.datetime(self.set_time_offset, 1, 1)
            ).total_seconds()
        )
        payload.extend(utc_timestamp.to_bytes(4, "big", signed=False))
        payload.extend(local_timestamp.to_bytes(4, "big", signed=False))

        self.create_catching_task(
            super().command(TUYA_SET_TIME, payload, expect_reply=False)
        )


class TuyaManufClusterAttributes(TuyaManufCluster):
    """Manufacturer specific cluster for Tuya converting attributes <-> commands."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple,
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        if hdr.command_id not in (0x0001, 0x0002):
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        # Send default response because the MCU expects it
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        tuya_cmd = args[0].command_id
        tuya_data = args[0].data

        _LOGGER.debug(
            "[0x%04x:%s:0x%04x] Received value %s "
            "for attribute 0x%04x (command 0x%04x)",
            self.endpoint.device.nwk,
            self.endpoint.endpoint_id,
            self.cluster_id,
            repr(tuya_data[1:]),
            tuya_cmd,
            hdr.command_id,
        )

        if tuya_cmd not in self.attributes:
            return

        ztype = self.attributes[tuya_cmd][1]
        zvalue = tuya_data.to_value(ztype)
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
            cmd_payload = TuyaManufCluster.Command()
            cmd_payload.status = 0
            cmd_payload.tsn = self.endpoint.device.application.get_sequence()
            cmd_payload.command_id = record.attrid
            cmd_payload.function = 0
            cmd_payload.data = Data.from_value(record.value.value)

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
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[TuyaManufCluster.Command],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""

        tuya_payload = args[0]
        if hdr.command_id in (0x0002, 0x0001):
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


class TuyaThermostatCluster(LocalDataCluster, Thermostat):
    """Thermostat cluster for Tuya thermostats."""

    _CONSTANT_ATTRIBUTES = {0x001B: Thermostat.ControlSequenceOfOperation.Heating_Only}

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.thermostat_bus.add_listener(self)

    def temperature_change(self, attr, value):
        """Local or target temperature change from device."""
        self._update_attribute(self.attridx[attr], value)

    def state_change(self, value):
        """State update from device."""
        if value == 0:
            mode = self.RunningMode.Off
            state = self.RunningState.Idle
        else:
            mode = self.RunningMode.Heat
            state = self.RunningState.Heat_State_On
        self._update_attribute(self.attridx["running_mode"], mode)
        self._update_attribute(self.attridx["running_state"], state)

    # pylint: disable=R0201
    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""
        return {}

    async def write_attributes(self, attributes, manufacturer=None):
        """Implement writeable attributes."""

        records = self._write_attr_records(attributes)

        if not records:
            return (foundation.Status.SUCCESS,)

        manufacturer_attrs = {}
        for record in records:
            attr_name = self.attributes[record.attrid][0]
            new_attrs = self.map_attribute(attr_name, record.value.value)

            _LOGGER.debug(
                "[0x%04x:%s:0x%04x] Mapping standard %s (0x%04x) "
                "with value %s to custom %s",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attr_name,
                record.attrid,
                repr(record.value.value),
                repr(new_attrs),
            )

            manufacturer_attrs.update(new_attrs)

        if not manufacturer_attrs:
            return (foundation.Status.FAILURE,)

        await self.endpoint.tuya_manufacturer.write_attributes(
            manufacturer_attrs, manufacturer=manufacturer
        )

        return (foundation.Status.SUCCESS,)

    # pylint: disable=W0236
    async def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Implement thermostat commands."""

        if command_id != 0x0000:
            return foundation.Status.UNSUP_CLUSTER_COMMAND

        mode, offset = args
        if mode not in (self.SetpointMode.Heat, self.SetpointMode.Both):
            return foundation.Status.INVALID_VALUE

        attrid = self.attridx["occupied_heating_setpoint"]

        success, _ = await self.read_attributes((attrid,), manufacturer=manufacturer)
        try:
            current = success[attrid]
        except KeyError:
            return foundation.Status.FAILURE

        # offset is given in decidegrees, see Zigbee cluster specification
        return await self.write_attributes(
            {"occupied_heating_setpoint": current + offset * 10},
            manufacturer=manufacturer,
        )


class TuyaUserInterfaceCluster(LocalDataCluster, UserInterface):
    """HVAC User interface cluster for tuya thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.ui_bus.add_listener(self)

    def child_lock_change(self, mode):
        """Change of child lock setting."""
        if mode == 0:
            lockout = self.KeypadLockout.No_lockout
        else:
            lockout = self.KeypadLockout.Level_1_lockout

        self._update_attribute(self.attridx["keypad_lockout"], lockout)

    def map_attribute(self, attribute, value):
        """Map standardized attribute value to dict of manufacturer values."""
        return {}

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer the keypad_lockout attribute to child_lock."""

        records = self._write_attr_records(attributes)

        manufacturer_attrs = {}
        for record in records:
            if record.attrid == self.attridx["keypad_lockout"]:
                lock = 0 if record.value.value == self.KeypadLockout.No_lockout else 1
                new_attrs = {self._CHILD_LOCK_ATTR: lock}
            else:
                attr_name = self.attributes[record.attrid][0]
                new_attrs = self.map_attribute(attr_name, record.value.value)

                _LOGGER.debug(
                    "[0x%04x:%s:0x%04x] Mapping standard %s (0x%04x) "
                    "with value %s to custom %s",
                    self.endpoint.device.nwk,
                    self.endpoint.endpoint_id,
                    self.cluster_id,
                    attr_name,
                    record.attrid,
                    repr(record.value.value),
                    repr(new_attrs),
                )

            manufacturer_attrs.update(new_attrs)

        if not manufacturer_attrs:
            return (foundation.Status.FAILURE,)

        await self.endpoint.tuya_manufacturer.write_attributes(
            manufacturer_attrs, manufacturer=manufacturer
        )

        return (foundation.Status.SUCCESS,)


class TuyaPowerConfigurationCluster(LocalDataCluster, PowerConfiguration):
    """PowerConfiguration cluster for battery-operated thermostats."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.battery_bus.add_listener(self)

    def battery_change(self, value):
        """Change of reported battery percentage remaining."""
        self._update_attribute(self.attridx["battery_percentage_remaining"], value * 2)


class TuyaThermostat(CustomDevice):
    """Generic Tuya thermostat device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.thermostat_bus = Bus()
        self.ui_bus = Bus()
        self.battery_bus = Bus()
        super().__init__(*args, **kwargs)


class TuyaSmartRemoteOnOffCluster(OnOff, EventableCluster):
    """TuyaSmartRemoteOnOffCluster: fire events corresponding to press type."""

    press_type = {
        0x00: SHORT_PRESS,
        0x01: DOUBLE_PRESS,
        0x02: LONG_PRESS,
    }
    name = "TS004X_cluster"
    ep_attribute = "TS004X_cluster"

    def __init__(self, *args, **kwargs):
        """Init."""
        self.last_tsn = -1
        super().__init__(*args, **kwargs)

    manufacturer_server_commands = {
        0xFD: ("press_type", (t.uint8_t,), False),
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle press_types command."""
        # normally if default response sent, TS004x wouldn't send such repeated zclframe (with same sequence number),
        # but for stability reasons (e. g. the case the response doesn't arrive the device), we can simply ignore it
        if hdr.tsn == self.last_tsn:
            _LOGGER.debug("TS004X: ignoring duplicate frame")
            return
        # save last sequence number
        self.last_tsn = hdr.tsn

        # send default response (as soon as possible), so avoid repeated zclframe from device
        if not hdr.frame_control.disable_default_response:
            self.debug("TS004X: send default response")
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        # handle command
        if hdr.command_id == 0xFD:
            press_type = args[0]
            self.listener_event(
                ZHA_SEND_EVENT, self.press_type.get(press_type, "unknown"), []
            )
