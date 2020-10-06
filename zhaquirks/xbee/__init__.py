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

from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    AnalogOutput,
    BinaryInput,
    LevelControl,
    OnOff,
)

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
ATTR_ON_OFF = 0x0000
ATTR_PRESENT_VALUE = 0x0055
PIN_ANALOG_OUTPUT = 2


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
        result = await self._endpoint.device.remote_at(pin_name, pin_cmd)
        if result == foundation.Status.SUCCESS:
            self._update_attribute(ATTR_ON_OFF, command_id)
        return 0, result


class XBeeAnalogInput(LocalDataCluster, AnalogInput):
    """XBee Analog Input Cluster."""

    pass


class XBeePWM(LocalDataCluster, AnalogOutput):
    """XBee PWM Cluster."""

    ep_id_2_pwm = {0xDA: "M0", 0xDB: "M1"}

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
        if ATTR_PRESENT_VALUE in attributes:
            duty_cycle = int(round(float(attributes.pop(ATTR_PRESENT_VALUE))))
            at_command = self.ep_id_2_pwm.get(self._endpoint.endpoint_id)
            result = await self._endpoint.device.remote_at(at_command, duty_cycle)
            if result != foundation.Status.SUCCESS:
                return result

            at_command = ENDPOINT_TO_AT.get(self._endpoint.endpoint_id)
            result = await self._endpoint.device.remote_at(
                at_command, PIN_ANALOG_OUTPUT
            )
            if result != foundation.Status.SUCCESS or not attributes:
                return result

        return await super().write_attributes(attributes, manufacturer)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Intercept present_value attribute read."""
        if ATTR_PRESENT_VALUE in attributes:
            at_command = self.ep_id_2_pwm.get(self._endpoint.endpoint_id)
            result = await self._endpoint.device.remote_at(at_command)
            self._update_attribute(ATTR_PRESENT_VALUE, float(result))
        return await super().read_attributes_raw(attributes, manufacturer)


class XBeeCommon(CustomDevice):
    """XBee common class."""

    def remote_at(self, command, *args, **kwargs):
        """Remote at command."""
        if hasattr(self._application, "remote_at_command"):
            return self._application.remote_at_command(
                self.nwk, command, *args, apply_changes=True, encryption=True, **kwargs
            )
        _LOGGER.warning("Remote At Command not supported by this coordinator")

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
                super().handle_cluster_request(tsn, command_id, args)

        attributes = {0x0055: ("present_value", t.Bool)}
        client_commands = {0x0000: ("io_sample", (IOSample,), False)}
        server_commands = {0x0000: ("io_sample", (IOSample,), False)}

    # pylint: disable=too-many-ancestors
    class EventRelayCluster(EventableCluster, LocalDataCluster, LevelControl):
        """A cluster with cluster_id which is allowed to send events."""

        attributes = {}
        client_commands = {}
        server_commands = {0x0000: ("receive_data", (str,), None)}

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
                ].handle_cluster_request(tsn, command_id, args[0])
            else:
                super().handle_cluster_request(tsn, command_id, args)

        attributes = {}
        client_commands = {0x0000: ("send_data", (BinaryString,), None)}
        server_commands = {0x0000: ("receive_data", (BinaryString,), None)}

    replacement = {
        ENDPOINTS: {
            232: {
                INPUT_CLUSTERS: [DigitalIOCluster, SerialDataCluster],
                OUTPUT_CLUSTERS: [SerialDataCluster, EventRelayCluster],
            }
        },
        "manufacturer": "Digi",
    }
