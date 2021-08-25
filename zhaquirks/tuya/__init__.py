"""Tuya devices."""
import dataclasses
import datetime
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import LevelControl, OnOff, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface

from zhaquirks import Bus, EventableCluster, LocalDataCluster
from zhaquirks.const import DOUBLE_PRESS, LONG_PRESS, SHORT_PRESS, ZHA_SEND_EVENT

# ---------------------------------------------------------
# Tuya Custom Cluster ID
# ---------------------------------------------------------
TUYA_CLUSTER_ID = 0xEF00
# ---------------------------------------------------------
# Tuya Cluster Commands
# ---------------------------------------------------------
TUYA_SET_DATA = 0x00
TUYA_GET_DATA = 0x01
TUYA_SET_DATA_RESPONSE = 0x02
TUYA_SEND_DATA = 0x04
TUYA_ACTIVE_STATUS_RPT = 0x06
TUYA_SET_TIME = 0x24
TUYA_LEVEL_COMMAND = 514

COVER_EVENT = "cover_event"
LEVEL_EVENT = "level_event"

# ---------------------------------------------------------
# Value for dp_type
# ---------------------------------------------------------
# ID    Name            Description
# ---------------------------------------------------------
# 0x00 	DP_TYPE_RAW 	?
# 0x01 	DP_TYPE_BOOL 	?
# 0x02 	DP_TYPE_VALUE 	4 byte unsigned integer
# 0x03 	DP_TYPE_STRING 	variable length string
# 0x04 	DP_TYPE_ENUM 	1 byte enum
# 0x05 	DP_TYPE_FAULT 	1 byte bitmap (didn't test yet)
TUYA_DP_TYPE_RAW = 0x0000
TUYA_DP_TYPE_BOOL = 0x0100
TUYA_DP_TYPE_VALUE = 0x0200
TUYA_DP_TYPE_STRING = 0x0300
TUYA_DP_TYPE_ENUM = 0x0400
TUYA_DP_TYPE_FAULT = 0x0500
# ---------------------------------------------------------
# Value for dp_identifier (These are device specific)
# ---------------------------------------------------------
# ID    Name               Type    Description
# ---------------------------------------------------------
# 0x01  control            enum    open, stop, close, continue
# 0x02  percent_control    value   0-100% control
# 0x03  percent_state      value   Report from motor about current percentage
# 0x04  control_back       enum    Configures motor direction (untested)
# 0x05  work_state         enum    Motor Direction Setting
# 0x06  situation_set      enum    Configures if 100% equals to fully closed or fully open (untested)
# 0x07  fault              bitmap  Anything but 0 means something went wrong (untested)
TUYA_DP_ID_CONTROL = 0x01
TUYA_DP_ID_PERCENT_CONTROL = 0x02
TUYA_DP_ID_PERCENT_STATE = 0x03
TUYA_DP_ID_DIRECTION_CHANGE = 0x05
TUYA_DP_ID_COVER_INVERTED = 0x06
# ---------------------------------------------------------
# Window Cover Server Commands
# ---------------------------------------------------------
WINDOW_COVER_COMMAND_UPOPEN = 0x0000
WINDOW_COVER_COMMAND_DOWNCLOSE = 0x0001
WINDOW_COVER_COMMAND_STOP = 0x0002
WINDOW_COVER_COMMAND_LIFTPERCENT = 0x0005
WINDOW_COVER_COMMAND_CUSTOM = 0x0006
# ---------------------------------------------------------
# TUYA Cover Custom Values
# ---------------------------------------------------------
COVER_EVENT = "cover_event"
ATTR_COVER_POSITION = 0x0008
ATTR_COVER_DIRECTION = 0x8001
ATTR_COVER_INVERTED = 0x8002
# For most tuya devices 0 = Up/Open, 1 = Stop, 2 = Down/Close
TUYA_COVER_COMMAND = {
    "_TZE200_zah67ekd": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
    "_TZE200_fzo2pocs": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
    "_TZE200_xuzcvlku": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
    "_TZE200_rddyvrci": {0x0000: 0x0002, 0x0001: 0x0001, 0x0002: 0x0000},
    "_TZE200_3i3exuay": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
    "_TZE200_nueqqe6k": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
    "_TZE200_gubdgai2": {0x0000: 0x0000, 0x0001: 0x0002, 0x0002: 0x0001},
}
# ---------------------------------------------------------
# TUYA Switch Custom Values
# ---------------------------------------------------------
SWITCH_EVENT = "switch_event"
ATTR_ON_OFF = 0x0000
ATTR_COVER_POSITION = 0x0008
TUYA_CMD_BASE = 0x0100
# ---------------------------------------------------------
# DP Value meanings in Status Report
# ---------------------------------------------------------
# Type ID    IntDP   Description
# ---------------------------------------------------------
# 0x04 0x01  1025    Confirm opening/closing/stopping (triggered from Zigbee)
# 0x02 0x02   514    Started moving to position (triggered from Zigbee)
# 0x04 0x07  1031    Started moving (triggered by transmitter order pulling on curtain)
# 0x02 0x03   515    Arrived at position
# 0x01 0x05   261    Returned by configuration set; ignore
# 0x02 0x69   617    Not sure what this is
# 0x04 0x05  1029    Changed the Motor Direction
# 0x04 0x65  1125    Change of tilt/lift mode 1 = lift 0=tilt
# ---------------------------------------------------------

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


class TuyaDPType(t.enum8):
    """DataPoint Type."""

    RAW = 0x00
    BOOL = 0x01
    VALUE = 0x02
    STRING = 0x03
    ENUM = 0x04
    BITMAP = 0x05


class TuyaData(t.Struct):
    """Tuya Data type."""

    dp_type: TuyaDPType
    function: t.uint8_t
    raw: t.LVBytes

    @classmethod
    def deserialize(cls, data: bytes) -> Tuple["TuyaData", bytes]:
        """Deserialize data."""
        res = cls()
        res.dp_type, data = TuyaDPType.deserialize(data)
        res.function, data = t.uint8_t.deserialize(data)
        res.raw, data = t.LVBytes.deserialize(data)
        if res.dp_type not in (TuyaDPType.BITMAP, TuyaDPType.STRING, TuyaDPType.ENUM):
            res.raw = res.raw[::-1]
        return res, data

    @property
    def payload(self) -> Union[t.Bool, t.CharacterString, t.uint32_t, t.data32]:
        """Payload accordingly to data point type."""
        if self.dp_type == TuyaDPType.VALUE:
            return t.uint32_t.deserialize(self.raw)[0]
        elif self.dp_type == TuyaDPType.BOOL:
            return t.Bool.deserialize(self.raw)[0]
        elif self.dp_type == TuyaDPType.STRING:
            return self.raw.decode("utf8")
        elif self.dp_type == TuyaDPType.ENUM:
            return t.enum8.deserialize(self.raw)[0]
        elif self.dp_type == TuyaDPType.BITMAP:
            bitmaps = {1: t.bitmap8, 2: t.bitmap16, 4: t.bitmap32}
            try:
                return bitmaps[len(self.raw)].deserialize(self.raw)[0]
            except KeyError as exc:
                raise ValueError(f"Wrong bitmap length: {len(self.raw)}") from exc

        raise ValueError(f"Unknown {self.dp_type} datapoint type")


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


class TuyaCommand(t.Struct):
    """Tuya manufacturer cluster command."""

    status: t.uint8_t
    tsn: t.uint8_t
    dp: t.uint8_t
    data: TuyaData


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
        0x0024: ("set_time_request", (t.data16,), True),
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


class TuyaDimmerSwitch(TuyaSwitch):
    """Tuya dimmer switch device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.dimmer_bus = Bus()
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


# Tuya Window Cover Implementation
class TuyaManufacturerWindowCover(TuyaManufCluster):
    """Manufacturer Specific Cluster for cover device."""

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
        """Tuya Specific Cluster Commands"""
        if hdr.command_id == TUYA_SET_DATA_RESPONSE:
            tuya_payload = args[0]
            _LOGGER.debug(
                "%s Received Attribute Report. Command is 0x%04x, Tuya Paylod values"
                "[Status : %s, TSN: %s, Command: 0x%04x, Function: 0x%02x, Data: %s]",
                self.endpoint.device.ieee,
                hdr.command_id,
                tuya_payload.status,
                tuya_payload.tsn,
                tuya_payload.command_id,
                tuya_payload.function,
                tuya_payload.data,
            )

            if tuya_payload.command_id == TUYA_DP_TYPE_VALUE + TUYA_DP_ID_PERCENT_STATE:
                self.endpoint.device.cover_bus.listener_event(
                    COVER_EVENT,
                    ATTR_COVER_POSITION,
                    tuya_payload.data[4],
                )
            elif (
                tuya_payload.command_id
                == TUYA_DP_TYPE_ENUM + TUYA_DP_ID_DIRECTION_CHANGE
            ):
                self.endpoint.device.cover_bus.listener_event(
                    COVER_EVENT,
                    ATTR_COVER_DIRECTION,
                    tuya_payload.data[1],
                )
            elif (
                tuya_payload.command_id == TUYA_DP_TYPE_ENUM + TUYA_DP_ID_COVER_INVERTED
            ):
                self.endpoint.device.cover_bus.listener_event(
                    COVER_EVENT,
                    ATTR_COVER_INVERTED,
                    tuya_payload.data[1],  # Check this
                )
        elif hdr.command_id == 0x0011:
            """Assuming this is the pairing event"""
            _LOGGER.debug(
                "%s Pairing New Tuya Roller Blind. Self [%s], Header [%s], Tuya Paylod [%s]",
                self.endpoint.device.ieee,
                self,
                hdr,
                args,
            )
            """set initial attributes"""
            self.endpoint.device.cover_bus.listener_event(
                COVER_EVENT,
                ATTR_COVER_POSITION,
                0,
            )
            self.endpoint.device.cover_bus.listener_event(
                COVER_EVENT,
                ATTR_COVER_DIRECTION,
                0,
            )
            self.endpoint.device.cover_bus.listener_event(
                COVER_EVENT,
                ATTR_COVER_INVERTED,
                0,
            )
        elif hdr.command_id == TUYA_SET_TIME:
            """Time event call super"""
            super().handle_cluster_request(self, hdr, args, dst_addressing)
        else:
            _LOGGER.debug(
                "%s Received Attribute Report - Unknown Command. Self [%s], Header [%s], Tuya Paylod [%s]",
                self.endpoint.device.ieee,
                self,
                hdr,
                args,
            )


class TuyaWindowCoverControl(LocalDataCluster, WindowCovering):
    """Manufacturer Specific Cluster of Device cover."""

    """Add additional attributes for direction"""
    attributes = WindowCovering.attributes.copy()
    attributes.update({ATTR_COVER_DIRECTION: ("motor_direction", t.Bool)})
    attributes.update({ATTR_COVER_INVERTED: ("cover_inverted", t.Bool)})

    def __init__(self, *args, **kwargs):
        """Initialize instance."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.cover_bus.add_listener(self)

    def cover_event(self, attribute, value):
        """Event listener for cover events."""
        if attribute == ATTR_COVER_POSITION:
            value = (
                value if self._attr_cache.get(ATTR_COVER_INVERTED) == 1 else 100 - value
            )
        self._update_attribute(attribute, value)
        _LOGGER.debug(
            "%s Tuya Attribute Cache : [%s]",
            self.endpoint.device.ieee,
            self._attr_cache,
        )

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""
        if manufacturer is None:
            manufacturer = self.endpoint.device.manufacturer
        _LOGGER.debug(
            "%s Sending Tuya Cluster Command.. Manufacturer is %s Cluster Command is 0x%04x, Arguments are %s",
            self.endpoint.device.ieee,
            manufacturer,
            command_id,
            args,
        )
        # Open Close or Stop commands
        tuya_payload = TuyaManufCluster.Command()
        if command_id in (
            WINDOW_COVER_COMMAND_UPOPEN,
            WINDOW_COVER_COMMAND_DOWNCLOSE,
            WINDOW_COVER_COMMAND_STOP,
        ):
            tuya_payload.status = 0
            tuya_payload.tsn = tsn if tsn else 0
            tuya_payload.command_id = TUYA_DP_TYPE_ENUM + TUYA_DP_ID_CONTROL
            tuya_payload.function = 0
            tuya_payload.data = [
                1,
                # need to implement direction change
                TUYA_COVER_COMMAND[manufacturer][command_id],
            ]  # remap the command to the Tuya command
        # Set Position Command
        elif command_id == WINDOW_COVER_COMMAND_LIFTPERCENT:
            tuya_payload.status = 0
            tuya_payload.tsn = tsn if tsn else 0
            tuya_payload.command_id = TUYA_DP_TYPE_VALUE + TUYA_DP_ID_PERCENT_CONTROL
            tuya_payload.function = 0
            """Check direction and correct value"""
            position = (
                args[0]
                if self._attr_cache.get(ATTR_COVER_INVERTED) == 1
                else 100 - args[0]
            )
            tuya_payload.data = [
                4,
                0,
                0,
                0,
                position,
            ]
        # Custom Command
        elif command_id == WINDOW_COVER_COMMAND_CUSTOM:
            tuya_payload.status = args[0]
            tuya_payload.tsn = args[1]
            tuya_payload.command_id = args[2]
            tuya_payload.function = args[3]
            tuya_payload.data = args[4]
        else:
            tuya_payload = None
        # Send the command
        if tuya_payload.command_id:
            _LOGGER.debug(
                "%s Sending Tuya Command. Paylod values [endpoint_id : %s, "
                "Status : %s, TSN: %s, Command: 0x%04x, Function: %s, Data: %s]",
                self.endpoint.device.ieee,
                self.endpoint.endpoint_id,
                tuya_payload.status,
                tuya_payload.tsn,
                tuya_payload.command_id,
                tuya_payload.function,
                tuya_payload.data,
            )

            return self.endpoint.tuya_manufacturer.command(
                TUYA_SET_DATA, tuya_payload, expect_reply=True
            )
        else:
            _LOGGER.debug("Unrecognised command: %x", command_id)
            return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaWindowCover(CustomDevice):
    """Tuya switch device."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.cover_bus = Bus()
        super().__init__(*args, **kwargs)


class TuyaManufacturerLevelControl(TuyaManufCluster):
    """Manufacturer Specific Cluster for cover device."""

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

        _LOGGER.debug(
            "%s Received Attribute Report. Command is %x, Tuya Paylod values"
            "[Status : %s, TSN: %s, Command: %s, Function: %s, Data: %s]",
            self.endpoint.device.ieee,
            hdr.command_id,
            tuya_payload.status,
            tuya_payload.tsn,
            tuya_payload.command_id,
            tuya_payload.function,
            tuya_payload.data,
        )

        if hdr.command_id in (0x0002, 0x0001):
            if tuya_payload.command_id == TUYA_LEVEL_COMMAND:
                self.endpoint.device.dimmer_bus.listener_event(
                    LEVEL_EVENT,
                    tuya_payload.command_id,
                    tuya_payload.data,
                )
            else:
                self.endpoint.device.switch_bus.listener_event(
                    SWITCH_EVENT,
                    tuya_payload.command_id - TUYA_CMD_BASE,
                    tuya_payload.data[1],
                )


class TuyaLevelControl(CustomCluster, LevelControl):
    """Tuya Level cluster for dimmable device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.dimmer_bus.add_listener(self)

    def level_event(self, channel, state):
        """Level event."""
        level = (((state[3] << 8) + state[4]) * 255) // 1000
        _LOGGER.debug(
            "%s - Received level event message, channel: %d, level: %d, data: %d",
            self.endpoint.device.ieee,
            channel,
            level,
            state,
        )
        self._update_attribute(self.attridx["current_level"], level)

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
    ):
        """Override the default Cluster command."""
        _LOGGER.debug(
            "%s Sending Tuya Cluster Command.. Cluster Command is %x, Arguments are %s",
            self.endpoint.device.ieee,
            command_id,
            args,
        )
        # Move to level
        # move_to_level_with_on_off
        if command_id in (0x0000, 0x0001, 0x0004):
            cmd_payload = TuyaManufCluster.Command()
            cmd_payload.status = 0
            cmd_payload.tsn = 0
            cmd_payload.command_id = TUYA_LEVEL_COMMAND
            cmd_payload.function = 0
            brightness = (args[0] * 1000) // 255
            val1 = brightness >> 8
            val2 = brightness & 0xFF
            cmd_payload.data = [4, 0, 0, val1, val2]  # Custom Command

            return self.endpoint.tuya_manufacturer.command(
                TUYA_SET_DATA, cmd_payload, expect_reply=True
            )

        return foundation.Status.UNSUP_CLUSTER_COMMAND


class TuyaLocalCluster(LocalDataCluster):
    """Tuya virtual clusters.

    Prevents attribute reads and writes. Attribute writes could be converted
    to DataPoint updates.
    """

    def update_attribute(self, attr_name: str, value: Any) -> None:
        """Update attribute by attribute name."""

        try:
            attrid = self.attridx[attr_name]
        except KeyError:
            self.debug("no such attribute: %s", attr_name)
            return
        return self._update_attribute(attrid, value)


@dataclasses.dataclass
class DPToAttributeMapping:
    """Container for datapoint to cluster attribute update mapping."""

    ep_attribute: str
    attribute_name: str
    converter: Optional[
        Callable[
            [
                Any,
            ],
            Any,
        ]
    ] = None
    endpoint_id: Optional[int] = None


class TuyaNewManufCluster(CustomCluster):
    """Tuya manufacturer specific cluster.

    This is an attempt to consolidate the multiple above clusters into a
    single framework. Instead of overriding the handle_cluster_request()
    method, implement handlers for commands, like get_data, set_data_response,
    set_time_request, etc.
    """

    name: str = "Tuya Manufacturer Specific"
    cluster_id: t.uint16_t = TUYA_CLUSTER_ID
    ep_attribute: str = "tuya_manufacturer"

    manufacturer_server_commands = {
        TUYA_SET_DATA: ("set_data", (TuyaCommand,), False),
        TUYA_SEND_DATA: ("send_data", (TuyaCommand,), False),
        TUYA_SET_TIME: ("set_time", (TuyaTimePayload,), False),
    }

    manufacturer_client_commands = {
        TUYA_GET_DATA: ("get_data", (TuyaCommand,), True),
        TUYA_SET_DATA_RESPONSE: ("set_data_response", (TuyaCommand,), True),
        TUYA_ACTIVE_STATUS_RPT: ("active_status_report", (TuyaCommand,), True),
        TUYA_SET_TIME: ("set_time_request", (t.data16,), True),
    }

    data_point_handlers: Dict[int, str] = {}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple,
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster specific request."""

        try:
            if (
                hdr.is_reply
            ):  # server_cluster -> client_cluster cluster specific command
                handler_name = f"handle_{self.client_commands[hdr.command_id][0]}"
            else:
                handler_name = f"handle_{self.server_commands[hdr.command_id][0]}"
        except KeyError:
            self.debug(
                "Received unknown manufacturer command %s: %s", hdr.command_id, args
            )
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(
                    hdr, status=foundation.Status.UNSUP_CLUSTER_COMMAND
                )
                return

        try:
            status = getattr(self, handler_name)(*args)
        except AttributeError:
            self.warning(
                "No '%s' tuya handler found for %s",
                handler_name,
                args,
            )
            status = foundation.Status.UNSUP_CLUSTER_COMMAND

        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=status)

    def handle_get_data(self, command: TuyaCommand) -> foundation.Status:
        """Handle get_data response (report)."""
        try:
            dp_handler = self.data_point_handlers[command.dp]
            getattr(self, dp_handler)(command)
        except (AttributeError, KeyError):
            self.debug("No datapoint handler for %s", command)
            return foundation.status.UNSUPPORTED_ATTRIBUTE

        return foundation.Status.SUCCESS

    handle_set_data_response = handle_get_data
    handle_active_status_report = handle_get_data

    def handle_set_time_request(self, payload: t.uint16_t) -> foundation.Status:
        """Handle Time set request."""
        return foundation.Status.SUCCESS

    def _dp_2_attr_update(self, command: TuyaCommand) -> None:
        """Handle data point to attribute report conversion."""
        try:
            dp_map = self.dp_to_attribute[command.dp]
        except KeyError:
            self.debug("No attribute mapping for %s data point", command.dp)
            return

        endpoint = self.endpoint
        if dp_map.endpoint_id:
            endpoint = self.endpoint.device.endpoints[dp_map.endpoint_id]
        cluster = getattr(endpoint, dp_map.ep_attribute)
        value = command.data.payload
        if dp_map.converter:
            value = dp_map.converter(value)

        cluster.update_attribute(dp_map.attribute_name, value)
