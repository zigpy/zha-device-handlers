"""Salus quirks elements.

The iT600 heating devices (SQ610RF thermostat, KL08RF wiring centre) talk a
Computime protocol on manufacturer cluster 0xFC00 instead of standard ZCL. It is
documented in https://github.com/mikkelke/salus-zigbee/blob/main/PROTOCOL.md and
implemented for zigbee2mqtt in zigbee-herdsman-converters `salus_controls.ts`.
"""

import datetime
import time

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Ota
from zigpy.zcl.foundation import BaseCommandDefs, ZCLCommandDef

from zhaquirks import LocalDataCluster
from zhaquirks.clusters import CustomCluster

COMPUTIME = "Computime"
SALUS = "SALUS"
COMPUTIME_MANUFACTURER_CODE = 0x1078

# The devices read the coordinator's Basic model and expect a Salus gateway.
IT600_GATEWAY_MANUFACTURER = COMPUTIME
IT600_GATEWAY_MODEL = "SAU2AG1"

# Resend the sync response (which carries the clock) at most this often.
IT600_SYNC_INTERVAL = 24 * 60 * 60

_ZCL_EPOCH = datetime.datetime(2000, 1, 1)


class It600Payload(t.Struct):
    """Raw iT600 command payload."""

    data: t.Bytes


def payload_bytes(args) -> bytes:
    """Return the raw payload of an incoming iT600 command.

    zigpy picks the command table from the ZCL direction bit and hands back raw
    bytes for an id it does not know, so accept both shapes.
    """
    data = getattr(args, "data", None)
    if data is not None:
        return bytes(data)
    if isinstance(args, (bytes, bytearray)):
        return bytes(args)
    return b""


def local_seconds_since_2000() -> int:
    """Return the local wall-clock time in seconds since 2000-01-01."""
    return int((datetime.datetime.now() - _ZCL_EPOCH).total_seconds())


def sync_response_body(device_number: int) -> bytes:
    """Build the 15-byte sync response (0x81) payload.

    The device number tells the device who it is: wiring centres take 1..9, a
    thermostat takes 0x20. The clock is sent as local time with time zone index
    13 (UTC) and no DST, like zigbee2mqtt does.
    """
    return (
        bytes([device_number, 0x00])
        + local_seconds_since_2000().to_bytes(4, "little")
        + bytes([0x02, 13, 0x00])  # 24-hour clock, no DST; UTC; DST offset 0
        + b"\xff\xff\xff\xff"  # no paired RX10RF receivers
        + b"1\x00"  # gateway online
    )


def _command_defs(name: str) -> type[BaseCommandDefs]:
    """Build a command table with every iT600 command a device sends.

    The thermostat sends server to client and the wiring centre client to
    server, so the same commands are declared for both directions.
    """
    commands = {
        "sync_request": 0x10,
        "time_announce": 0x11,
        "zone_report": 0x12,
        "zone_pair_confirm": 0x14,
        "wiring_centre_request": 0x16,
        "zone_pair_request": 0x18,
        "zone_replaced": 0x1A,
        "update_check": 0x25,
        "record": 0x31,
        "b_command_echo": 0x33,
        "sync_ack": 0x37,
        "pair_button": 0xA9,
    }
    return type(
        name,
        (BaseCommandDefs,),
        {
            command_name: ZCLCommandDef(
                id=command_id, schema=It600Payload, is_manufacturer_specific=True
            )
            for command_name, command_id in commands.items()
        },
    )


class SalusIt600Cluster(LocalDataCluster):
    """Salus iT600 manufacturer cluster 0xFC00.

    The device leaves the network unless its sync request (0x10) is answered
    with a sync response (0x81). Everything it reports arrives as commands, so
    the attributes are local only.
    """

    cluster_id = 0xFC00
    ep_attribute = "salus_it600"
    name = "Salus iT600"
    manufacturer_id_override = COMPUTIME_MANUFACTURER_CODE

    # Device number assigned on first contact; a device that already holds one
    # sends it back in its sync request and keeps it.
    DEFAULT_DEVICE_NUMBER: int = 0x20

    ServerCommandDefs = _command_defs("ServerCommandDefs")
    ClientCommandDefs = _command_defs("ClientCommandDefs")

    _last_sync: float | None = None

    def handle_cluster_request(
        self, hdr: foundation.ZCLHeader, args, *, dst_addressing=None
    ):
        """Answer the sync request and hand other commands to the subclass."""
        payload = payload_bytes(args)
        if hdr.command_id == self.ClientCommandDefs.sync_request.id:
            device_number = (
                payload[0]
                if payload and payload[0] != 0xFF
                else self.DEFAULT_DEVICE_NUMBER
            )
            self.create_catching_task(self.send_sync_response(device_number))
            return
        if hdr.command_id in self.client_commands:
            # The device disables the default response; none is sent.
            self.handle_it600_command(hdr.command_id, payload)
            return
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    def handle_it600_command(self, command_id: int, payload: bytes) -> None:
        """Handle an iT600 command other than the sync request."""
        self.debug("iT600 command 0x%02x: %s", command_id, payload.hex())

    async def send_sync_response(self, device_number: int) -> None:
        """Send the sync response, which also sets the device clock."""
        self._last_sync = time.monotonic()
        await self.send_it600_frame(0x81, sync_response_body(device_number))

    async def send_it600_frame(
        self, command_id: int, payload: bytes, tsn: int | None = None
    ) -> None:
        """Send an iT600 frame the way a Salus gateway does.

        Gateway frames are server to client with the default response disabled,
        which zigpy's request helpers cannot produce from this cluster.
        """
        if tsn is None:
            tsn = self.endpoint.device.application.get_sequence()
        hdr = foundation.ZCLHeader.cluster(
            tsn=tsn, command_id=command_id, manufacturer=COMPUTIME_MANUFACTURER_CODE
        )
        hdr = hdr.replace(
            frame_control=hdr.frame_control.replace(
                direction=foundation.Direction.Server_to_Client,
                disable_default_response=True,
            )
        )
        await self.endpoint.reply(
            cluster=self.cluster_id,
            sequence=tsn,
            data=hdr.serialize() + payload,
            command_id=command_id,
        )


class SalusIt600Basic(CustomCluster, Basic):
    """Basic cluster answering the device's coordinator identity check.

    zigpy dispatches a read the device sends to the coordinator on the device's
    own Basic cluster, so the answer is given here.
    """

    def handle_read_attribute_manufacturer(self) -> t.CharacterString:
        """Return the Salus gateway manufacturer."""
        return t.CharacterString(IT600_GATEWAY_MANUFACTURER)

    def handle_read_attribute_model(self) -> t.CharacterString:
        """Return the Salus gateway model."""
        return t.CharacterString(IT600_GATEWAY_MODEL)


class SalusIt600Ota(CustomCluster, Ota):
    """OTA cluster answering the device's query like a Salus gateway.

    A Salus gateway answers Query Next Image with a Default Response, status
    Invalid Field. The thermostat stalls on a real OTA server answer.
    """

    def handle_cluster_request(self, hdr, args, *, dst_addressing=None):
        """Answer Query Next Image with a Default Response."""
        if (
            hdr.direction == foundation.Direction.Client_to_Server
            and hdr.command_id == self.ServerCommandDefs.query_next_image.id
        ):
            self.create_catching_task(self._send_default_response(hdr.tsn))
            return
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    async def _send_default_response(self, tsn: int) -> None:
        hdr = foundation.ZCLHeader.general(
            tsn=tsn,
            command_id=foundation.GeneralCommand.Default_Response,
            direction=foundation.Direction.Server_to_Client,
        )
        # The gateway leaves disable default response clear.
        hdr = hdr.replace(
            frame_control=hdr.frame_control.replace(disable_default_response=False)
        )
        body = foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(
            command_id=self.ServerCommandDefs.query_next_image.id,
            status=foundation.Status.INVALID_FIELD,
        )
        await self.endpoint.reply(
            cluster=self.cluster_id,
            sequence=tsn,
            data=hdr.serialize() + body.serialize(),
            command_id=foundation.GeneralCommand.Default_Response,
        )
