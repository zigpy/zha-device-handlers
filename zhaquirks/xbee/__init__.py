"""Module for xbee devices as remote sensors/switches.

See xbee.md for additional information.
"""

import asyncio
import enum
import logging
from typing import Any, List, Optional, Union

from zigpy.quirks import CustomDevice
import zigpy.types as zt
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    AnalogOutput,
    Basic,
    BinaryInput,
    LevelControl,
    OnOff,
)

from zhaquirks import EventableCluster, LocalDataCluster
from zhaquirks.const import ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS

from . import types as t

_LOGGER = logging.getLogger(__name__)

DATA_IN_CMD = 0x0000
DIO_APPLY_CHANGES = 0x02
DIO_PIN_HIGH = 0x05
DIO_PIN_LOW = 0x04
ON_OFF_CMD = 0x0000
SAMPLE_DATA_CMD = 0x0000
SERIAL_DATA_CMD = 0x0000
AT_RESPONSE_CMD = 0x0000
XBEE_DATA_CLUSTER = 0x11
XBEE_AT_REQUEST_CLUSTER = 0x21
XBEE_AT_RESPONSE_CLUSTER = 0xA1
XBEE_AT_ENDPOINT = 0xE6
XBEE_DATA_ENDPOINT = 0xE8
XBEE_IO_CLUSTER = 0x92
XBEE_PROFILE_ID = 0xC105
ATTR_ON_OFF = 0x0000
ATTR_PRESENT_VALUE = 0x0055
PIN_ANALOG_OUTPUT = 2

REMOTE_AT_COMMAND_TIMEOUT = 30


# https://github.com/zigpy/zigpy-xbee/blob/dev/zigpy_xbee/api.py
AT_COMMANDS = {
    # Addressing commands
    "DH": t.uint32_t,
    "DL": t.uint32_t,
    "MY": t.uint16_t,
    "MP": t.uint16_t,
    "NC": t.uint32_t,  # 0 - MAX_CHILDREN.
    "SH": t.uint32_t,
    "SL": t.uint32_t,
    "NI": t.Bytes,  # 20 byte printable ascii string
    # "SE": t.uint8_t,
    # "DE": t.uint8_t,
    # "CI": t.uint16_t,
    "TO": t.uint8_t,
    "NP": t.uint16_t,
    "DD": t.uint32_t,
    "CR": t.uint8_t,  # 0 - 0x3F
    # Networking commands
    "CH": t.uint8_t,  # 0x0B - 0x1A
    "DA": None,  # no param
    # "ID": t.uint64_t,
    "OP": t.uint64_t,
    "NH": t.uint8_t,
    "BH": t.uint8_t,  # 0 - 0x1E
    "OI": t.uint16_t,
    "NT": t.uint8_t,  # 0x20 - 0xFF
    "NO": t.uint8_t,  # bitfield, 0 - 3
    "SC": t.uint16_t,  # 1 - 0xFFFF
    "SD": t.uint8_t,  # 0 - 7
    # "ZS": t.uint8_t,  # 0 - 2
    "NJ": t.uint8_t,
    "JV": t.Bool,
    "NW": t.uint16_t,  # 0 - 0x64FF
    "JN": t.Bool,
    "AR": t.uint8_t,
    "DJ": t.Bool,  # WTF, docs
    "II": t.uint16_t,
    # Security commands
    # "EE": t.Bool,
    # "EO": t.uint8_t,
    # "NK": t.Bytes,  # 128-bit value
    # "KY": t.Bytes,  # 128-bit value
    # RF interfacing commands
    "PL": t.uint8_t,  # 0 - 4 (basically an Enum)
    "PM": t.Bool,
    "DB": t.uint8_t,
    "PP": t.uint8_t,  # RO
    "AP": t.uint8_t,  # 1-2 (an Enum)
    "AO": t.uint8_t,  # 0 - 3 (an Enum)
    "BD": t.uint8_t,  # 0 - 7 (an Enum)
    "NB": t.uint8_t,  # 0 - 3 (an Enum)
    "SB": t.uint8_t,  # 0 - 1 (an Enum)
    "RO": t.uint8_t,
    "D6": t.uint8_t,  # 0 - 5 (an Enum)
    "D7": t.uint8_t,  # 0 - 7 (an Enum)
    "P3": t.uint8_t,  # 0 - 5 (an Enum)
    "P4": t.uint8_t,  # 0 - 5 (an Enum)
    # I/O commands
    "IR": t.uint16_t,
    "IC": t.uint16_t,
    "D0": t.uint8_t,  # 0 - 5 (an Enum)
    "D1": t.uint8_t,  # 0 - 5 (an Enum)
    "D2": t.uint8_t,  # 0 - 5 (an Enum)
    "D3": t.uint8_t,  # 0 - 5 (an Enum)
    "D4": t.uint8_t,  # 0 - 5 (an Enum)
    "D5": t.uint8_t,  # 0 - 5 (an Enum)
    "D8": t.uint8_t,  # 0 - 5 (an Enum)
    "D9": t.uint8_t,  # 0 - 5 (an Enum)
    "P0": t.uint8_t,  # 0 - 5 (an Enum)
    "P1": t.uint8_t,  # 0 - 5 (an Enum)
    "P2": t.uint8_t,  # 0 - 5 (an Enum)
    "P5": t.uint8_t,  # 0 - 5 (an Enum)
    "P6": t.uint8_t,  # 0 - 5 (an Enum)
    "P7": t.uint8_t,  # 0 - 5 (an Enum)
    "P8": t.uint8_t,  # 0 - 5 (an Enum)
    "P9": t.uint8_t,  # 0 - 5 (an Enum)
    "LT": t.uint8_t,
    "PR": t.uint16_t,
    "RP": t.uint8_t,
    "%V": t.uint16_t,  # read only
    "V+": t.uint16_t,
    "TP": t.int16_t,
    "M0": t.uint16_t,  # 0 - 0x3FF
    "M1": t.uint16_t,  # 0 - 0x3FF
    # Diagnostics commands
    "VR": t.uint16_t,
    "HV": t.uint16_t,
    "AI": t.uint8_t,
    # AT command options
    "CT": t.uint16_t,  # 2 - 0x028F
    "CN": None,
    "GT": t.uint16_t,
    "CC": t.uint8_t,
    # Sleep commands
    "SM": t.uint8_t,
    "SN": t.uint16_t,
    "SP": t.uint16_t,
    "ST": t.uint16_t,
    "SO": t.uint8_t,
    "WH": t.uint16_t,
    "SI": None,
    "PO": t.uint16_t,  # 0 - 0x3E8
    # Execution commands
    "AC": None,
    "WR": None,
    "RE": None,
    "FR": None,
    "NR": t.Bool,
    "CB": t.uint8_t,
    "DN": t.Bytes,  # "up to 20-Byte printable ASCII string"
    "IS": t.IOSample,
    "AS": None,
    # Stuff I've guessed
    # "CE": t.uint8_t,
}

# 4 AO lines
# 10 digital
# Discovered endpoint information: <SimpleDescriptor endpoint=232 profile=49413
# device_type=1 device_version=0 input_clusters=[] output_clusters=[]>


ENDPOINT_TO_AT = {
    0xD0: "D0",
    0xD1: "D1",
    0xD2: "D2",
    0xD3: "D3",
    0xD4: "D4",
    0xD5: "D5",
    0xD6: "D6",
    0xD7: "D7",
    0xD8: "D8",
    0xD9: "D9",
    0xDA: "P0",
    0xDB: "P1",
    0xDC: "P2",
    0xDD: "P3",
    0xDE: "P4",
}


class ATCommandResult(enum.IntEnum):
    """AT command results."""

    OK = 0
    ERROR = 1
    INVALID_COMMAND = 2
    INVALID_PARAMETER = 3
    TX_FAILURE = 4


class XBeeBasic(LocalDataCluster, Basic):
    """XBee Basic Cluster."""

    _CONSTANT_ATTRIBUTES = {
        0x0000: 0x02,  # ZCLVersion
        0x0007: Basic.PowerSource.Unknown,  # PowerSource
    }


class XBeeOnOff(LocalDataCluster, OnOff):
    """XBee on/off cluster."""

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Xbee change pin state command, requires zigpy_xbee."""
        pin_name = ENDPOINT_TO_AT.get(self._endpoint.endpoint_id)
        if command_id not in [0, 1] or pin_name is None:
            return super().command(command_id, *args)
        if command_id == 0:
            pin_cmd = DIO_PIN_LOW
        else:
            pin_cmd = DIO_PIN_HIGH
        await self._endpoint.device.remote_at(pin_name, pin_cmd)
        self._update_attribute(ATTR_ON_OFF, command_id)
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


class XBeeAnalogInput(LocalDataCluster, AnalogInput):
    """XBee Analog Input Cluster."""


class XBeePWM(LocalDataCluster, AnalogOutput):
    """XBee PWM Cluster."""

    _CONSTANT_ATTRIBUTES = {
        0x0041: float(0x03FF),  # max_present_value
        0x0045: 0.0,  # min_present_value
        0x0051: 0,  # out_of_service
        0x006A: 1.0,  # resolution
        0x006F: 0x00,  # status_flags
    }

    _ep_id_2_pwm = {0xDA: "M0", 0xDB: "M1"}

    async def write_attributes(self, attributes, manufacturer=None):
        """Intercept present_value attribute write."""
        attr_id = None
        if ATTR_PRESENT_VALUE in attributes:
            attr_id = ATTR_PRESENT_VALUE
        elif "present_value" in attributes:
            attr_id = "present_value"
        if attr_id:
            duty_cycle = int(round(float(attributes[attr_id])))
            at_command = self._ep_id_2_pwm.get(self._endpoint.endpoint_id)
            await self._endpoint.device.remote_at(at_command, duty_cycle)

            at_command = ENDPOINT_TO_AT.get(self._endpoint.endpoint_id)
            await self._endpoint.device.remote_at(at_command, PIN_ANALOG_OUTPUT)

        return await super().write_attributes(attributes, manufacturer)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Intercept present_value attribute read."""
        if ATTR_PRESENT_VALUE in attributes or "present_value" in attributes:
            at_command = self._ep_id_2_pwm.get(self._endpoint.endpoint_id)
            result = await self._endpoint.device.remote_at(at_command)
            self._update_attribute(ATTR_PRESENT_VALUE, float(result))
        return await super().read_attributes_raw(attributes, manufacturer)


class XBeeRemoteATRequest(LocalDataCluster):
    """Remote AT Command Request Cluster."""

    cluster_id = XBEE_AT_REQUEST_CLUSTER
    client_commands = {}
    server_commands = {
        k: foundation.ZCLCommandDef(
            name=v[0].replace("%V", "PercentV").replace("V+", "VPlus"),
            schema={"param?": v[1]} if v[1] else {},
            is_manufacturer_specific=True,
        )
        for k, v in zip(range(1, len(AT_COMMANDS) + 1), AT_COMMANDS.items())
    }

    _seq: int = 1

    def _save_at_request(self, frame_id, future):
        self._endpoint.in_clusters[XBEE_AT_RESPONSE_CLUSTER].save_at_request(
            frame_id, future
        )

    def remote_at_command(self, cmd_name, *args, apply_changes=True, **kwargs):
        """Execute a Remote AT Command and Return Response."""
        if hasattr(self._endpoint.device.application, "remote_at_command"):
            return self._endpoint.device.application.remote_at_command(
                self._endpoint.device.nwk,
                cmd_name,
                *args,
                apply_changes=apply_changes,
                encryption=False,
                **kwargs,
            )
        _LOGGER.debug("Remote AT%s command: %s", cmd_name, args)
        options = t.uint8_t(0)
        if apply_changes:
            options |= 0x02
        return self._remote_at_command(options, cmd_name, *args)

    async def _remote_at_command(self, options, name, *args):
        _LOGGER.debug("Remote AT command: %s %s", name, args)
        data = zt.serialize(args, (AT_COMMANDS[name],))
        try:
            return await asyncio.wait_for(
                await self._command(options, name.encode("ascii"), data, *args),
                timeout=REMOTE_AT_COMMAND_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning("No response to %s command", name)
            raise

    async def _command(self, options, command, data, *args):
        _LOGGER.debug("Command %s %s", command, data)
        frame_id = self._seq
        self._seq = (self._seq % 255) + 1
        schema = (
            t.uint8_t,
            t.uint8_t,
            t.uint8_t,
            t.uint8_t,
            t.EUI64,
            t.NWK,
            t.Bytes,
            t.Bytes,
        )
        data = zt.serialize(
            (
                0x32,
                0x00,
                options,
                frame_id,
                self._endpoint.device.application.state.node_info.ieee,
                self._endpoint.device.application.state.node_info.nwk,
                command,
                data,
            ),
            schema,
        )

        future = asyncio.Future()
        self._save_at_request(frame_id, future)

        try:
            await self._endpoint.device.application.request(
                self._endpoint.device,
                XBEE_PROFILE_ID,
                XBEE_AT_REQUEST_CLUSTER,
                XBEE_AT_ENDPOINT,
                XBEE_AT_ENDPOINT,
                self._endpoint.device.application.get_sequence(),
                data,
                expect_reply=False,
            )
        except Exception as e:
            future.set_exception(e)

        return future

    async def command(
        self,
        command_id,
        param=None,
        *args,
        manufacturer=None,
        expect_reply=False,
        tsn=None,
    ):
        """Handle AT request."""
        command = (
            self.server_commands[command_id]
            .name.replace("PercentV", "%V")
            .replace("VPlus", "V+")
        )

        if param is not None:
            value = await self.remote_at_command(command, param)
        else:
            value = await self.remote_at_command(command)

        tsn = self._endpoint.device.application.get_sequence()
        hdr = foundation.ZCLHeader.cluster(tsn, command_id)
        self._endpoint.device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
            LevelControl.cluster_id
        ].handle_cluster_request(hdr, {"response": value})

        if command == "IS" and value:
            tsn = self._endpoint.device.application.get_sequence()
            hdr = foundation.ZCLHeader.cluster(tsn, SAMPLE_DATA_CMD)
            self._endpoint.device.endpoints[XBEE_DATA_ENDPOINT].in_clusters[
                XBEE_IO_CLUSTER
            ].handle_cluster_request(
                hdr,
                self._endpoint.device.endpoints[XBEE_DATA_ENDPOINT]
                .in_clusters[XBEE_IO_CLUSTER]
                .server_commands[SAMPLE_DATA_CMD]
                .schema(io_sample=value),
            )

        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


class XBeeRemoteATResponse(LocalDataCluster):
    """Remote AT Command Response Cluster."""

    cluster_id = XBEE_AT_RESPONSE_CLUSTER

    _awaiting = {}

    def save_at_request(self, frame_id, future):
        """Save pending request."""
        self._awaiting[frame_id] = (future,)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[zt.Addressing.Group, zt.Addressing.IEEE, zt.Addressing.NWK]
        ] = None,
    ):
        """Handle AT response."""
        if hdr.command_id == DATA_IN_CMD:
            _LOGGER.debug(
                "Remote AT command response: %s",
                (args.frame_id, args.cmd, args.status, args.value),
            )
            (fut,) = self._awaiting.pop(args.frame_id)
            try:
                status = ATCommandResult(args.status)
            except ValueError:
                status = ATCommandResult.ERROR

            if status:
                fut.set_exception(
                    RuntimeError("AT Command response: {}".format(status.name))
                )
                return

            response_type = AT_COMMANDS[args.cmd.decode("ascii")]
            if response_type is None or len(args.value) == 0:
                fut.set_result(None)
                return

            response, remains = response_type.deserialize(args.value)
            fut.set_result(response)

        else:
            super().handle_cluster_request(hdr, args)

    client_commands = {}
    server_commands = {
        AT_RESPONSE_CMD: foundation.ZCLCommandDef(
            name="remote_at_response",
            schema={
                "frame_id": t.uint8_t,
                "cmd": t.ATCommand,
                "status": t.uint8_t,
                "value": t.Bytes,
            },
            is_manufacturer_specific=True,
        )
    }


class XBeeDigitalIOCluster(LocalDataCluster, BinaryInput):
    """Digital IO Cluster for the XBee."""

    cluster_id = XBEE_IO_CLUSTER

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[zt.Addressing.Group, zt.Addressing.IEEE, zt.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster request.

        Update the digital pin states
        """
        if hdr.command_id == SAMPLE_DATA_CMD:
            values = args.io_sample
            if "digital_samples" in values:
                # Update digital inputs
                active_pins = [
                    i for i, x in enumerate(values["digital_samples"]) if x is not None
                ]
                for pin in active_pins:
                    # pylint: disable=W0212
                    self._endpoint.device[0xD0 + pin].on_off._update_attribute(
                        ATTR_ON_OFF, values["digital_samples"][pin]
                    )
            if "analog_samples" in values:
                # Update analog inputs
                active_pins = [
                    i for i, x in enumerate(values["analog_samples"]) if x is not None
                ]
                for pin in active_pins:
                    # pylint: disable=W0212
                    self._endpoint.device[0xD0 + pin].analog_input._update_attribute(
                        ATTR_PRESENT_VALUE,
                        values["analog_samples"][pin]
                        / (10.23 if pin != 7 else 1000),  # supply voltage is in mV
                    )
        else:
            super().handle_cluster_request(hdr, args)

    client_commands = {}
    server_commands = {
        SAMPLE_DATA_CMD: foundation.ZCLCommandDef(
            name="io_sample",
            schema={"io_sample": t.IOSample},
            is_manufacturer_specific=True,
        )
    }


# pylint: disable=too-many-ancestors
class XBeeEventRelayCluster(EventableCluster, LocalDataCluster, LevelControl):
    """A cluster with cluster_id which is allowed to send events."""

    attributes = {}
    client_commands = {}
    server_commands = {
        k: foundation.ZCLCommandDef(
            name=v[0].replace("%V", "PercentV").replace("V+", "VPlus").lower()
            + "_command_response",
            schema={"response?": v[1]} if v[1] else {},
            is_manufacturer_specific=True,
        )
        for k, v in zip(range(1, len(AT_COMMANDS) + 1), AT_COMMANDS.items())
    }
    server_commands[SERIAL_DATA_CMD] = foundation.ZCLCommandDef(
        name="receive_data", schema={"data": str}, is_manufacturer_specific=True
    )


class XBeeSerialDataCluster(LocalDataCluster):
    """Serial Data Cluster for the XBee."""

    cluster_id = XBEE_DATA_CLUSTER
    ep_attribute = "xbee_serial_data"

    async def command(
        self,
        command_id,
        data,
        *args,
        manufacturer=None,
        expect_reply=False,
        tsn=None,
    ):
        """Handle outgoing data."""
        data = t.BinaryString(data).serialize()
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(
            command_id=0x00,
            status=(
                await self._endpoint.device.application.request(
                    self._endpoint.device,
                    XBEE_PROFILE_ID,
                    XBEE_DATA_CLUSTER,
                    XBEE_DATA_ENDPOINT,
                    XBEE_DATA_ENDPOINT,
                    self._endpoint.device.application.get_sequence(),
                    data,
                    expect_reply=False,
                )
            )[0],
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[zt.Addressing.Group, zt.Addressing.IEEE, zt.Addressing.NWK]
        ] = None,
    ):
        """Handle incoming data."""
        if hdr.command_id == DATA_IN_CMD:
            self._endpoint.out_clusters[LevelControl.cluster_id].handle_cluster_request(
                hdr, {"data": args.data}
            )
        else:
            super().handle_cluster_request(hdr, args)

    attributes = {}
    client_commands = {
        SERIAL_DATA_CMD: foundation.ZCLCommandDef(
            name="send_data",
            schema={"data": t.BinaryString},
            is_manufacturer_specific=True,
        )
    }
    server_commands = {
        SERIAL_DATA_CMD: foundation.ZCLCommandDef(
            name="receive_data",
            schema={"data": t.BinaryString},
            is_manufacturer_specific=True,
        )
    }


class XBeeCommon(CustomDevice):
    """XBee common class."""

    def remote_at(self, command, *args, **kwargs):
        """Remote at command."""
        return (
            self.endpoints[XBEE_AT_ENDPOINT]
            .out_clusters[XBEE_AT_REQUEST_CLUSTER]
            .remote_at_command(command, *args, apply_changes=True, **kwargs)
        )

    def deserialize(self, endpoint_id, cluster_id, data):
        """Deserialize."""
        tsn = self._application.get_sequence()
        command_id = 0x0000
        hdr = foundation.ZCLHeader.cluster(tsn, command_id)
        data = hdr.serialize() + data
        return super().deserialize(endpoint_id, cluster_id, data)

    replacement = {
        ENDPOINTS: {
            XBEE_AT_ENDPOINT: {
                INPUT_CLUSTERS: [XBeeRemoteATResponse],
                OUTPUT_CLUSTERS: [XBeeRemoteATRequest],
            },
            XBEE_DATA_ENDPOINT: {
                INPUT_CLUSTERS: [
                    XBeeDigitalIOCluster,
                    XBeeSerialDataCluster,
                    XBeeBasic,
                ],
                OUTPUT_CLUSTERS: [XBeeSerialDataCluster, XBeeEventRelayCluster],
            },
        },
        "manufacturer": "Digi",
    }
