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

import logging
import struct

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import AnalogInput, BinaryInput, LevelControl, OnOff

from .. import EventableCluster, LocalDataCluster
from ..const import ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS

_LOGGER = logging.getLogger(__name__)

DATA_IN_CMD = 0x0000
DIO_APPLY_CHANGES = 0x02
DIO_PIN_HIGH = 0x05
DIO_PIN_LOW = 0x04
ON_OFF_CMD = 0x0000
XBEE_DATA_CLUSTER = 0x11
XBEE_DST_ENDPOINT = 0xE8
XBEE_IO_CLUSTER = 0x92
XBEE_PROFILE_ID = 0xC105
XBEE_REMOTE_AT = 0x17
XBEE_SRC_ENDPOINT = 0xE8


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
        Digital mask byte 0,1
        Analog mask byte 3
        Digital samples byte 4, 5
        Analog Sample, 2 bytes per
        """
        digital_mask = data[0:2]
        analog_mask = data[2:3]
        digital_sample = data[3:5]
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
        digital_samples = [
            (int.from_bytes(digital_sample, byteorder="big") >> bit) & 1
            for bit in range(num_bits - 1, -1, -1)
        ]
        digital_samples = list(reversed(digital_samples))
        sample_index = 0
        analog_samples = []
        for apin in analog_pins:
            if apin == 1:
                analog_samples.append(
                    int.from_bytes(
                        data[5 + sample_index : 7 + sample_index], byteorder="big"
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
            b"",
        )


# 4 AO lines
# 10 digital
# Discovered endpoint information: <SimpleDescriptor endpoint=232 profile=49413
# device_type=1 device_version=0 input_clusters=[] output_clusters=[]>


ENDPOINT_MAP = {
    0: 0xD0,
    1: 0xD1,
    2: 0xD2,
    3: 0xD3,
    4: 0xD4,
    5: 0xD5,
    7: 0xD7,
    8: 0xD8,
    9: 0xD9,
    10: 0xDA,
    11: 0xDB,
    12: 0xDC,
}


class XBeeOnOff(CustomCluster, OnOff):
    """XBee on/off cluster."""

    ep_id_2_pin = {
        0xD0: "D0",
        0xD1: "D1",
        0xD2: "D2",
        0xD3: "D3",
        0xD4: "D4",
        0xD5: "D5",
        0xD8: "D8",
        0xD9: "D9",
        0xDA: "P0",
        0xDB: "P1",
        0xDC: "P2",
    }

    async def command(self, command, *args, manufacturer=None, expect_reply=True):
        """Xbee change pin state command, requires zigpy_xbee."""
        pin_name = self.ep_id_2_pin.get(self._endpoint.endpoint_id)
        if command not in [0, 1] or pin_name is None:
            return super().command(command, *args)
        if command == 0:
            pin_cmd = DIO_PIN_LOW
        else:
            pin_cmd = DIO_PIN_HIGH
        await self._endpoint.device.remote_at(pin_name, pin_cmd)
        return 0, foundation.Status.SUCCESS


class XBeeCommon(CustomDevice):
    """XBee common class."""

    def remote_at(self, command, *args, **kwargs):
        """Remote at command."""
        if hasattr(self._application, "remote_at_command"):
            return self._application.remote_at_command(
                self.nwk, command, *args, apply_changes=True, encryption=True, **kwargs
            )
        _LOGGER.warning("Remote At Command not supported by this coordinator")

    class DigitalIOCluster(CustomCluster, BinaryInput):
        """Digital IO Cluster for the XBee."""

        cluster_id = XBEE_IO_CLUSTER

        def handle_cluster_request(self, tsn, command_id, args):
            """Handle the cluster request.

            Update the digital pin states
            """
            if command_id == ON_OFF_CMD:
                values = args[0]
                if "digital_pins" in values and "digital_samples" in values:
                    # Update digital inputs
                    active_pins = [
                        i for i, x in enumerate(values["digital_pins"]) if x == 1
                    ]
                    for pin in active_pins:
                        # pylint: disable=W0212
                        self._endpoint.device.__getitem__(
                            ENDPOINT_MAP[pin]
                        ).__getattr__(OnOff.ep_attribute)._update_attribute(
                            ON_OFF_CMD, values["digital_samples"][pin]
                        )
                if "analog_pins" in values and "analog_samples" in values:
                    # Update analog inputs
                    active_pins = [
                        i for i, x in enumerate(values["analog_pins"]) if x == 1
                    ]
                    for pin in active_pins:
                        # pylint: disable=W0212
                        self._endpoint.device.__getitem__(
                            ENDPOINT_MAP[pin]
                        ).__getattr__(AnalogInput.ep_attribute)._update_attribute(
                            0x0055,  # "present_value"
                            values["analog_samples"][pin]
                            / (10.23 if pin != 7 else 1000),  # supply voltage is in mV
                        )
            else:
                super().handle_cluster_request(tsn, command_id, args)

        def deserialize(self, data):
            """Deserialize."""
            hdr, data = foundation.ZCLHeader.deserialize(data)
            self.debug("ZCL deserialize: %s", hdr)
            if hdr.frame_control.frame_type == foundation.FrameType.CLUSTER_COMMAND:
                # Cluster command
                if hdr.is_reply:
                    commands = self.client_commands
                else:
                    commands = self.server_commands

                try:
                    schema = commands[hdr.command_id][1]
                    hdr.frame_control.is_reply = commands[hdr.command_id][2]
                except KeyError:
                    data = (
                        struct.pack(">i", hdr.tsn)[-1:]
                        + struct.pack(">i", hdr.command_id)[-1:]
                        + data
                    )
                    hdr.command_id = ON_OFF_CMD
                    try:
                        schema = commands[hdr.command_id][1]
                        hdr.frame_control.is_reply = commands[hdr.command_id][2]
                    except KeyError:
                        self.warn("Unknown cluster-specific command %s", hdr.command_id)
                        return hdr, data
                    value, data = t.deserialize(data, schema)
                    return hdr, value
            else:
                # General command
                try:
                    schema = foundation.COMMANDS[hdr.command_id][0]
                    hdr.frame_control.is_reply = foundation.COMMANDS[hdr.command_id][1]
                except KeyError:
                    self.warn("Unknown foundation command %s", hdr.command_id)
                    return hdr, data

            value, data = t.deserialize(data, schema)
            if data != b"":
                _LOGGER.warning("Data remains after deserializing ZCL frame")
            return hdr, value

        attributes = {0x0055: ("present_value", t.Bool)}
        client_commands = {0x0000: ("io_sample", (IOSample,), False)}
        server_commands = {0x0000: ("io_sample", (IOSample,), False)}

    class EventRelayCluster(EventableCluster, LevelControl):
        """A cluster with cluster_id which is allowed to send events."""

        attributes = {}
        client_commands = {}
        server_commands = {0x0000: ("receive_data", (str,), None)}

    class SerialDataCluster(LocalDataCluster):
        """Serial Data Cluster for the XBee."""

        cluster_id = XBEE_DATA_CLUSTER

        def command(self, command, *args, manufacturer=None, expect_reply=False):
            """Handle outgoing data."""
            data = bytes("".join(args), encoding="latin1")
            return self._endpoint.device.application.request(
                self._endpoint.device,
                XBEE_PROFILE_ID,
                XBEE_DATA_CLUSTER,
                XBEE_SRC_ENDPOINT,
                XBEE_DST_ENDPOINT,
                self._endpoint.device.application.get_sequence(),
                data,
                expect_reply=False,
            )

        def handle_cluster_request(self, tsn, command_id, args):
            """Handle incoming data."""
            if command_id == DATA_IN_CMD:
                self._endpoint.out_clusters[
                    LevelControl.cluster_id
                ].handle_cluster_request(tsn, command_id, str(args, encoding="latin1"))
            else:
                super().handle_cluster_request(tsn, command_id, args)

        attributes = {}
        client_commands = {0x0000: ("send_data", (bytes,), None)}
        server_commands = {0x0000: ("receive_data", (bytes,), None)}

    def deserialize(self, endpoint_id, cluster_id, data):
        """Pretends to be parsing incoming data."""
        if cluster_id != XBEE_DATA_CLUSTER:
            return super().deserialize(endpoint_id, cluster_id, data)

        tsn = self._application.get_sequence()
        command_id = DATA_IN_CMD
        is_reply = False

        class Hdr(foundation.ZCLHeader):
            """Trivial serialization class."""

            def __init__(self, tsn, command_id, is_reply):
                frc = foundation.FrameControl()
                frc.is_reply = is_reply
                frc.frame_type = foundation.FrameType.CLUSTER_COMMAND
                super().__init__(frame_control=frc, tsn=tsn, command_id=command_id)

        return Hdr(tsn, command_id, is_reply), data

    replacement = {
        ENDPOINTS: {
            232: {
                "manufacturer": "XBEE",
                "model": "xbee.io",
                INPUT_CLUSTERS: [DigitalIOCluster, SerialDataCluster],
                OUTPUT_CLUSTERS: [SerialDataCluster, EventRelayCluster],
            }
        }
    }
