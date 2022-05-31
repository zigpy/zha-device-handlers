"""Module for xbee devices as remote sensors/switches.

Allows for direct control of an xbee3's digital pins.

Reading pins should work with any coordinator (Untested)
writing pins will only work with an xbee as the coordinator as
it requires zigpy_xbee.

The xbee must be configured via XCTU to send samples to the coordinator,
DH and DL to the coordiator's address (0). and each pin must be configured
to act as a digital input.

Either configure reporting on state change by setting the appropriate bit
mask on IC or set IR to a value greater than zero to send perodic reports
every x milliseconds, I recommend the later, since this will ensure
the xbee stays alive in Home Assistant.
"""

import asyncio
import enum
import logging
from typing import Any, List, Optional, Union

from zigpy.quirks import CustomDevice
import zigpy.types as t
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

_LOGGER = logging.getLogger(__name__)

DATA_IN_CMD = 0x0000
DIO_APPLY_CHANGES = 0x02
DIO_PIN_HIGH = 0x05
DIO_PIN_LOW = 0x04
ON_OFF_CMD = 0x0000
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


class int_t(int):
    """Signed int type."""

    _signed = True

    def serialize(self):
        """Serialize int_t."""
        return self.to_bytes(self._size, "big", signed=self._signed)

    @classmethod
    def deserialize(cls, data):
        """Deserialize int_t."""
        # Work around https://bugs.python.org/issue23640
        r = cls(int.from_bytes(data[: cls._size], "big", signed=cls._signed))
        data = data[cls._size :]
        return r, data


class uint_t(int_t):
    """Unsigned int type."""

    _signed = False


class uint8_t(uint_t):
    """Unsigned int 8 bit type."""

    _size = 1


class int16_t(int_t):
    """Signed int 16 bit type."""

    _size = 2


class uint16_t(uint_t):
    """Unsigned int 16 bit type."""

    _size = 2


class uint32_t(uint_t):
    """Unsigned int 32 bit type."""

    _size = 4


class uint64_t(uint_t):
    """Unsigned int 64 bit type."""

    _size = 8


class Bytes(bytes):
    """Bytes serializable class."""

    def serialize(self):
        """Serialize Bytes."""
        return self

    @classmethod
    def deserialize(cls, data):
        """Deserialize Bytes."""
        return cls(data), b""


# https://github.com/zigpy/zigpy-xbee/blob/dev/zigpy_xbee/api.py
AT_COMMANDS = {
    # Addressing commands
    "DH": uint32_t,
    "DL": uint32_t,
    "MY": uint16_t,
    "MP": uint16_t,
    "NC": uint32_t,  # 0 - MAX_CHILDREN.
    "SH": uint32_t,
    "SL": uint32_t,
    "NI": Bytes,  # 20 byte printable ascii string
    # "SE": uint8_t,
    # "DE": uint8_t,
    # "CI": uint16_t,
    "TO": uint8_t,
    "NP": uint16_t,
    "DD": uint32_t,
    "CR": uint8_t,  # 0 - 0x3F
    # Networking commands
    "CH": uint8_t,  # 0x0B - 0x1A
    "DA": None,  # no param
    # "ID": uint64_t,
    "OP": uint64_t,
    "NH": uint8_t,
    "BH": uint8_t,  # 0 - 0x1E
    "OI": uint16_t,
    "NT": uint8_t,  # 0x20 - 0xFF
    "NO": uint8_t,  # bitfield, 0 - 3
    "SC": uint16_t,  # 1 - 0xFFFF
    "SD": uint8_t,  # 0 - 7
    # "ZS": uint8_t,  # 0 - 2
    "NJ": uint8_t,
    "JV": t.Bool,
    "NW": uint16_t,  # 0 - 0x64FF
    "JN": t.Bool,
    "AR": uint8_t,
    "DJ": t.Bool,  # WTF, docs
    "II": uint16_t,
    # Security commands
    # "EE": t.Bool,
    # "EO": uint8_t,
    # "NK": Bytes,  # 128-bit value
    # "KY": Bytes,  # 128-bit value
    # RF interfacing commands
    "PL": uint8_t,  # 0 - 4 (basically an Enum)
    "PM": t.Bool,
    "DB": uint8_t,
    "PP": uint8_t,  # RO
    "AP": uint8_t,  # 1-2 (an Enum)
    "AO": uint8_t,  # 0 - 3 (an Enum)
    "BD": uint8_t,  # 0 - 7 (an Enum)
    "NB": uint8_t,  # 0 - 3 (an Enum)
    "SB": uint8_t,  # 0 - 1 (an Enum)
    "RO": uint8_t,
    "D6": uint8_t,  # 0 - 5 (an Enum)
    "D7": uint8_t,  # 0 - 7 (an Enum)
    "P3": uint8_t,  # 0 - 5 (an Enum)
    "P4": uint8_t,  # 0 - 5 (an Enum)
    # I/O commands
    "IR": uint16_t,
    "IC": uint16_t,
    "D0": uint8_t,  # 0 - 5 (an Enum)
    "D1": uint8_t,  # 0 - 5 (an Enum)
    "D2": uint8_t,  # 0 - 5 (an Enum)
    "D3": uint8_t,  # 0 - 5 (an Enum)
    "D4": uint8_t,  # 0 - 5 (an Enum)
    "D5": uint8_t,  # 0 - 5 (an Enum)
    "D8": uint8_t,  # 0 - 5 (an Enum)
    "D9": uint8_t,  # 0 - 5 (an Enum)
    "P0": uint8_t,  # 0 - 5 (an Enum)
    "P1": uint8_t,  # 0 - 5 (an Enum)
    "P2": uint8_t,  # 0 - 5 (an Enum)
    "P5": uint8_t,  # 0 - 5 (an Enum)
    "P6": uint8_t,  # 0 - 5 (an Enum)
    "P7": uint8_t,  # 0 - 5 (an Enum)
    "P8": uint8_t,  # 0 - 5 (an Enum)
    "P9": uint8_t,  # 0 - 5 (an Enum)
    "LT": uint8_t,
    "PR": uint16_t,
    "RP": uint8_t,
    "%V": uint16_t,  # read only
    "V+": uint16_t,
    "TP": int16_t,
    "M0": uint16_t,  # 0 - 0x3FF
    "M1": uint16_t,  # 0 - 0x3FF
    # Diagnostics commands
    "VR": uint16_t,
    "HV": uint16_t,
    "AI": uint8_t,
    # AT command options
    "CT": uint16_t,  # 2 - 0x028F
    "CN": None,
    "GT": uint16_t,
    "CC": uint8_t,
    # Sleep commands
    "SM": uint8_t,
    "SN": uint16_t,
    "SP": uint16_t,
    "ST": uint16_t,
    "SO": uint8_t,
    "WH": uint16_t,
    "SI": None,
    "PO": uint16_t,  # 0 - 0x3E8
    # Execution commands
    "AC": None,
    "WR": None,
    "RE": None,
    "FR": None,
    "NR": t.Bool,
    "SI": None,
    "CB": uint8_t,
    "DN": Bytes,  # "up to 20-Byte printable ASCII string"
    "IS": None,
    "1S": None,
    "AS": None,
    # Stuff I've guessed
    # "CE": uint8_t,
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


class XBeeBasic(LocalDataCluster, Basic):
    """XBee Basic Cluster."""

    def __init__(self, endpoint, is_server=True):
        """Set default values and store them in cache."""
        super().__init__(endpoint, is_server)
        self._update_attribute(0x0000, 0x02)  # ZCLVersion
        self._update_attribute(0x0007, self.PowerSource.Unknown)  # PowerSource


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
        return 0, foundation.Status.SUCCESS


class XBeeAnalogInput(LocalDataCluster, AnalogInput):
    """XBee Analog Input Cluster."""


class XBeePWM(LocalDataCluster, AnalogOutput):
    """XBee PWM Cluster."""

    _ep_id_2_pwm = {0xDA: "M0", 0xDB: "M1"}

    def __init__(self, endpoint, is_server=True):
        """Set known attributes and store them in cache."""
        super().__init__(endpoint, is_server)
        self._update_attribute(0x0041, float(0x03FF))  # max_present_value
        self._update_attribute(0x0045, 0.0)  # min_present_value
        self._update_attribute(0x0051, 0)  # out_of_service
        self._update_attribute(0x006A, 1.0)  # resolution
        self._update_attribute(0x006F, 0x00)  # status_flags

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
    server_commands = {}

    _seq: int = 1

    class EUI64(t.EUI64):
        """EUI64 serializable class."""

        @classmethod
        def deserialize(cls, data):
            """Deserialize EUI64."""
            r, data = super().deserialize(data)
            return cls(r[::-1]), data

        def serialize(self):
            """Serialize EUI64."""
            assert self._length == len(self)
            return super().serialize()[::-1]

    class NWK(int):
        """Network address serializable class."""

        _signed = False
        _size = 2

        def serialize(self):
            """Serialize NWK."""
            return self.to_bytes(self._size, "big", signed=self._signed)

        @classmethod
        def deserialize(cls, data):
            """Deserialize NWK."""
            r = cls(int.from_bytes(data[: cls._size], "big", signed=cls._signed))
            data = data[cls._size :]
            return r, data

    def __init__(self, *args, **kwargs):
        """Generate client_commands from AT_COMMANDS."""
        super().__init__(*args, **kwargs)
        self.client_commands = {
            k: (v[0], (v[1],), None)
            for k, v in zip(range(1, len(AT_COMMANDS) + 1), AT_COMMANDS.items())
        }

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
        options = uint8_t(0)
        if apply_changes:
            options |= 0x02
        return self._remote_at_command(options, cmd_name, *args)

    async def _remote_at_command(self, options, name, *args):
        _LOGGER.debug("Remote AT command: %s %s", name, args)
        data = t.serialize(args, (AT_COMMANDS[name],))
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
            uint8_t,
            uint8_t,
            uint8_t,
            uint8_t,
            self.EUI64,
            self.NWK,
            Bytes,
            Bytes,
        )
        data = t.serialize(
            (
                0x32,
                0x00,
                options,
                frame_id,
                self._endpoint.device.application.ieee,
                self._endpoint.device.application.nwk,
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
        self, command_id, *args, manufacturer=None, expect_reply=False, tsn=None
    ):
        """Handle AT request."""
        command = self.client_commands[command_id][0]
        try:
            value = args[0]
            if isinstance(value, dict):
                value = None
        except IndexError:
            value = None

        if value:
            value = await self.remote_at_command(command, value)
        else:
            value = await self.remote_at_command(command)

        tsn = self._endpoint.device.application.get_sequence()
        hdr = foundation.ZCLHeader.cluster(tsn, command_id)
        self._endpoint.device.endpoints[232].out_clusters[
            LevelControl.cluster_id
        ].handle_cluster_request(hdr, value)

        # XXX: Is command_id=0x00 correct?
        return foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=0x00, status=foundation.Status.SUCCESS)


class XBeeRemoteATResponse(LocalDataCluster):
    """Remote AT Command Response Cluster."""

    cluster_id = XBEE_AT_RESPONSE_CLUSTER

    _awaiting = {}

    class ATCommandResult(enum.IntEnum):
        """AT command results."""

        OK = 0
        ERROR = 1
        INVALID_COMMAND = 2
        INVALID_PARAMETER = 3
        TX_FAILURE = 4

    class ATCommand(Bytes):
        """AT command serializable class."""

        @classmethod
        def deserialize(cls, data):
            """Deserialize ATCommand."""
            return cls(data[:2]), data[2:]

    def save_at_request(self, frame_id, future):
        """Save pending request."""
        self._awaiting[frame_id] = (future,)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle AT response."""
        if hdr.command_id == DATA_IN_CMD:
            frame_id = args[0]
            cmd = args[1]
            status = args[2]
            value = args[3]
            _LOGGER.debug(
                "Remote AT command response: %s", (frame_id, cmd, status, value)
            )
            (fut,) = self._awaiting.pop(frame_id)
            try:
                status = self.ATCommandResult(status)
            except ValueError:
                status = self.ATCommandResult.ERROR

            if status:
                fut.set_exception(
                    RuntimeError("AT Command response: {}".format(status.name))
                )
                return

            response_type = AT_COMMANDS[cmd.decode("ascii")]
            if response_type is None or len(value) == 0:
                fut.set_result(None)
                return

            response, remains = response_type.deserialize(value)
            fut.set_result(response)

        else:
            super().handle_cluster_request(hdr, args)

    client_commands = {}
    server_commands = {
        0x0000: (
            "remote_at_response",
            (
                uint8_t,
                ATCommand,
                uint8_t,
                Bytes,
            ),
            None,
        )
    }


class XBeeCommon(CustomDevice):
    """XBee common class."""

    def remote_at(self, command, *args, **kwargs):
        """Remote at command."""
        return (
            self.endpoints[230]
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

    class DigitalIOCluster(LocalDataCluster, BinaryInput):
        """Digital IO Cluster for the XBee."""

        cluster_id = XBEE_IO_CLUSTER

        class IOSample(bytes):
            """Parse an XBee IO sample report."""

            # pylint: disable=R0201
            def serialize(self):
                """Serialize an IO Sample Report, Not implemented."""
                _LOGGER.debug("Serialize not implemented.")

            @classmethod
            def deserialize(cls, data):
                """Deserialize an xbee IO sample report.

                xbee digital sample format
                Sample set count byte 0
                Digital mask byte 1, 2
                Analog mask byte 3
                Digital samples byte 4, 5 (if any sample exists)
                Analog Sample, 2 bytes per
                """
                sample_sets = int.from_bytes(data[0:1], byteorder="big")
                if sample_sets != 1:
                    _LOGGER.warning("Number of sets is not 1")
                digital_mask = data[1:3]
                analog_mask = data[3:4]
                digital_sample = data[4:6]
                num_bits = 13
                digital_pins = [
                    (int.from_bytes(digital_mask, byteorder="big") >> bit) & 1
                    for bit in range(num_bits - 1, -1, -1)
                ]
                digital_pins = list(reversed(digital_pins))
                analog_pins = [
                    (int.from_bytes(analog_mask, byteorder="big") >> bit) & 1
                    for bit in range(8 - 1, -1, -1)
                ]
                analog_pins = list(reversed(analog_pins))
                if 1 in digital_pins:
                    digital_samples = [
                        (int.from_bytes(digital_sample, byteorder="big") >> bit) & 1
                        for bit in range(num_bits - 1, -1, -1)
                    ]
                    digital_samples = list(reversed(digital_samples))
                    sample_index = 6
                else:
                    # skip digital samples block
                    digital_samples = digital_pins
                    sample_index = 4
                analog_samples = []
                for apin in analog_pins:
                    if apin == 1:
                        analog_samples.append(
                            int.from_bytes(
                                data[sample_index : sample_index + 2], byteorder="big"
                            )
                        )
                        sample_index += 2
                    else:
                        analog_samples.append(0)

                return (
                    {
                        "digital_pins": digital_pins,
                        "analog_pins": analog_pins,
                        "digital_samples": digital_samples,
                        "analog_samples": analog_samples,
                    },
                    data[sample_index:],
                )

        def handle_cluster_request(
            self,
            hdr: foundation.ZCLHeader,
            args: List[Any],
            *,
            dst_addressing: Optional[
                Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
            ] = None,
        ):
            """Handle the cluster request.

            Update the digital pin states
            """
            if hdr.command_id == ON_OFF_CMD:
                values = args[0]
                if "digital_pins" in values and "digital_samples" in values:
                    # Update digital inputs
                    active_pins = [
                        i for i, x in enumerate(values["digital_pins"]) if x == 1
                    ]
                    for pin in active_pins:
                        # pylint: disable=W0212
                        self._endpoint.device[0xD0 + pin].on_off._update_attribute(
                            ATTR_ON_OFF, values["digital_samples"][pin]
                        )
                if "analog_pins" in values and "analog_samples" in values:
                    # Update analog inputs
                    active_pins = [
                        i for i, x in enumerate(values["analog_pins"]) if x == 1
                    ]
                    for pin in active_pins:
                        # pylint: disable=W0212
                        self._endpoint.device[
                            0xD0 + pin
                        ].analog_input._update_attribute(
                            ATTR_PRESENT_VALUE,
                            values["analog_samples"][pin]
                            / (10.23 if pin != 7 else 1000),  # supply voltage is in mV
                        )
            else:
                super().handle_cluster_request(hdr, args)

        attributes = {0x0055: ("present_value", t.Bool)}
        client_commands = {}
        server_commands = {0x0000: ("io_sample", (IOSample,), False)}

    # pylint: disable=too-many-ancestors
    class EventRelayCluster(EventableCluster, LocalDataCluster, LevelControl):
        """A cluster with cluster_id which is allowed to send events."""

        attributes = {}
        client_commands = {}

        def __init__(self, *args, **kwargs):
            """Generate server_commands from AT_COMMANDS."""
            super().__init__(*args, **kwargs)
            self.server_commands = {
                k: (v[0].lower() + "_command_response", (str,), None)
                for k, v in zip(range(1, len(AT_COMMANDS) + 1), AT_COMMANDS.items())
            }
            self.server_commands[0x0000] = ("receive_data", (str,), None)

    class SerialDataCluster(LocalDataCluster):
        """Serial Data Cluster for the XBee."""

        cluster_id = XBEE_DATA_CLUSTER
        ep_attribute = "xbee_serial_data"

        class BinaryString(str):
            """Class to parse and serialize binary data as string."""

            def serialize(self):
                """Serialize string into bytes."""
                return bytes(self, encoding="latin1")

            @classmethod
            def deserialize(cls, data):
                """Interpret data as string."""
                data = str(data, encoding="latin1")
                return (cls(data), b"")

        def command(
            self, command_id, *args, manufacturer=None, expect_reply=False, tsn=None
        ):
            """Handle outgoing data."""
            data = self.BinaryString(args[0]).serialize()
            return self._endpoint.device.application.request(
                self._endpoint.device,
                XBEE_PROFILE_ID,
                XBEE_DATA_CLUSTER,
                XBEE_DATA_ENDPOINT,
                XBEE_DATA_ENDPOINT,
                self._endpoint.device.application.get_sequence(),
                data,
                expect_reply=False,
            )

        def handle_cluster_request(
            self,
            hdr: foundation.ZCLHeader,
            args: List[Any],
            *,
            dst_addressing: Optional[
                Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
            ] = None,
        ):
            """Handle incoming data."""
            if hdr.command_id == DATA_IN_CMD:
                self._endpoint.out_clusters[
                    LevelControl.cluster_id
                ].handle_cluster_request(hdr, args[0])
            else:
                super().handle_cluster_request(hdr, args)

        attributes = {}
        client_commands = {0x0000: ("send_data", (BinaryString,), None)}
        server_commands = {0x0000: ("receive_data", (BinaryString,), None)}

    replacement = {
        ENDPOINTS: {
            230: {
                INPUT_CLUSTERS: [XBeeRemoteATResponse],
                OUTPUT_CLUSTERS: [XBeeRemoteATRequest],
            },
            232: {
                INPUT_CLUSTERS: [DigitalIOCluster, SerialDataCluster, XBeeBasic],
                OUTPUT_CLUSTERS: [SerialDataCluster, EventRelayCluster],
            },
        },
        "manufacturer": "Digi",
    }
