"""HOBEIAN ZG-IR01 Tuya infrared blaster quirk.

The public Tuya datapoint map is documented by Rob Jones's MIT-licensed
community quirk and the HOBEIAN definition in zigbee-herdsman-converters:
https://github.com/therealdigitalkiwi/zha-zg-ir01
https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/hobeian.ts

Observed raw-transport behavior on HOBEIAN / ZG-IR01:

* Payloads are standard Broadlink IR packets carried over the Zosung clusters.
* Outgoing transfers use sequence zero, 50-byte parts, and request an empty
  part at the exact end offset instead of reliably sending frame 0x04.
* Learn transfers require normal ZCL default responses and can truncate the
  16-bit sequence to its low byte in terminal frame 0x05.
* Learning can emit terminal-only stop frames while idle and replay the final
  data part after completion; both are acknowledged without republishing.
* Learned packets use a model-specific Broadlink dialect: the length field is
  the complete packet length and the timing payload has no terminator or pad.
* The firmware's Broadlink timer is calibrated at about 32.2 microseconds per
  tick, not the standard 8192 / 269 microseconds. The quirk translates timing
  ticks at the device boundary so learned packets and external Broadlink
  libraries share the standard timebase.
"""

import asyncio
import base64
from dataclasses import dataclass, field
import json
import logging
from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.ts1201 import ZosungIRControl, ZosungIRTransmit

_LOGGER = logging.getLogger(__name__)

_MAX_OUTGOING_CHUNK_LENGTH = 0x32
_MAX_QUEUED_SENDS = 8
_OUTGOING_TRANSFER_TIMEOUT = 10.0
_OUTGOING_TRANSFER_QUIET_PERIOD = 0.25
_OUTGOING_TRANSFER_DRAIN_TIMEOUT = 10.0
# Header + maximum timing payload + terminator + transport padding.
_MAX_LEARN_PACKET_LENGTH = 0x1000C

_STANDARD_BROADLINK_TICK_US = 8192 / 269
# This firmware uses Broadlink's packet syntax, but not its 30.454 us timer.
# Physical reference-device measurements fitted 11 repeated widths from 548 us
# through 15.6 ms. Six held-out widths plus two long gaps through 54.8 ms reduced
# median absolute error from 211 us to 15 us and maximum error from 792 us to
# 74 us; independent capture fits agreed with both slopes within 0.15%.
# Ten non-protocol random waveforms (960 edges) then measured corrected-send
# median absolute errors of 19 us for marks and 14.5 us for spaces, with maxima
# of 28 us and 41 us. Normalized learning had one-tick median and two-tick p95
# error; rare larger edge shifts did not repeat under identical timing context.
# Sending applies the affine inverse; learning applies the forward map. Separate
# mark and space fits preserve the measured edge asymmetry without assuming its
# hardware cause.
_MARK_SLOPE_US = 32.25819277359383
_MARK_INTERCEPT_US = -14.598041656083296
_SPACE_SLOPE_US = 32.20106126330876
_SPACE_INTERCEPT_US = 21.875473711191262


def _decode_broadlink_packet(packet: bytes) -> tuple[int, list[int]]:
    """Decode timing ticks from one validated Broadlink IR packet."""
    if len(packet) > _MAX_LEARN_PACKET_LENGTH:
        raise ValueError("ZG-IR01 Broadlink packet exceeds its length limit")
    if len(packet) < 6 or packet[0] != 0x26:
        raise ValueError("ZG-IR01 code is not a Broadlink IR packet")
    payload_length = int.from_bytes(packet[2:4], "little")
    if payload_length == len(packet):
        # Learned ZG-IR01 packets use total packet length and omit the ordinary
        # Broadlink terminator/padding. Normalize this validated device dialect
        # while continuing to require canonical framing from external callers.
        payload = packet[4:]
    else:
        payload_end = 4 + payload_length
        if payload_end + 2 > len(packet):
            raise ValueError("ZG-IR01 Broadlink timing payload is truncated")
        if packet[payload_end : payload_end + 2] != b"\x0d\x05":
            raise ValueError("ZG-IR01 Broadlink packet terminator is missing")
        if any(packet[payload_end + 2 :]):
            raise ValueError("ZG-IR01 Broadlink packet has nonzero trailing data")
        payload = packet[4:payload_end]
    timings: list[int] = []
    position = 0
    while position < len(payload):
        value = payload[position]
        position += 1
        if value == 0:
            if position + 2 > len(payload):
                raise ValueError("ZG-IR01 Broadlink extended timing is truncated")
            value = int.from_bytes(payload[position : position + 2], "big")
            position += 2
        if value <= 0:
            raise ValueError("ZG-IR01 Broadlink timing must be positive")
        timings.append(value)
    if not timings:
        raise ValueError("ZG-IR01 Broadlink packet has no timings")
    return packet[1], timings


def _encode_broadlink_packet(repeat: int, timings: list[int]) -> bytes:
    """Encode timing ticks as one canonical Broadlink IR packet."""
    payload = bytearray()
    for value in timings:
        if not 0 < value <= 0xFFFF:
            raise ValueError("ZG-IR01 Broadlink timing exceeds its 16-bit range")
        if value < 0x100:
            payload.append(value)
        else:
            payload.extend((0, value >> 8, value & 0xFF))
    if len(payload) > 0xFFFF:
        raise ValueError("ZG-IR01 Broadlink timing payload exceeds its length limit")
    packet = bytearray((0x26, repeat, len(payload) & 0xFF, len(payload) >> 8))
    packet.extend(payload)
    packet.extend((0x0D, 0x05))
    while (len(packet) + 4) % 16:
        packet.append(0)
    return bytes(packet)


def _hardware_tick(standard_tick: int, index: int) -> int:
    """Map one standard Broadlink tick to the ZG-IR01 hardware timer."""
    desired_us = standard_tick * _STANDARD_BROADLINK_TICK_US
    if index % 2 == 0:
        slope = _MARK_SLOPE_US
        intercept = _MARK_INTERCEPT_US
    else:
        slope = _SPACE_SLOPE_US
        intercept = _SPACE_INTERCEPT_US
    return max(1, min(0xFFFF, round((desired_us - intercept) / slope)))


def _standard_tick(hardware_tick: int, index: int) -> int:
    """Map one learned ZG-IR01 timer tick to the Broadlink timebase."""
    if index % 2 == 0:
        slope = _MARK_SLOPE_US
        intercept = _MARK_INTERCEPT_US
    else:
        slope = _SPACE_SLOPE_US
        intercept = _SPACE_INTERCEPT_US
    measured_us = intercept + slope * hardware_tick
    return max(
        1,
        min(0xFFFF, round(measured_us / _STANDARD_BROADLINK_TICK_US)),
    )


def _broadlink_code_for_hardware(code: str) -> str:
    """Convert a standard Broadlink code to the ZG-IR01 timer domain."""
    try:
        packet = base64.b64decode(code, validate=True)
    except ValueError as error:
        raise ValueError("ZG-IR01 code is not valid Base64") from error
    repeat, timings = _decode_broadlink_packet(packet)
    transformed = [_hardware_tick(value, index) for index, value in enumerate(timings)]
    return base64.b64encode(_encode_broadlink_packet(repeat, transformed)).decode()


def _broadlink_packet_from_hardware(packet: bytes) -> bytes:
    """Convert a learned ZG-IR01 packet to the standard Broadlink timebase."""
    repeat, timings = _decode_broadlink_packet(packet)
    transformed = [_standard_tick(value, index) for index, value in enumerate(timings)]
    return _encode_broadlink_packet(repeat, transformed)


class IRStudyState(t.enum8):
    """Per-slot IR code study state."""

    Study = 0x00
    Registered = 0x01
    Unregistered = 0x02


class _LearnTransfer:
    """Assemble one learned IR packet without gaps or corruption."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Discard the active transfer."""
        self.sequence: int | None = None
        self.expected_length = 0
        self.data = bytearray()
        self.received = bytearray()
        self.parts: dict[tuple[int, int], tuple[bytes, int]] = {}

    @property
    def expected_position(self) -> int:
        """Return the first byte offset not received from the device."""
        try:
            return self.received.index(0)
        except ValueError:
            return self.expected_length

    def start(self, sequence: int, expected_length: int) -> str | None:
        """Start a transfer, returning a validation failure when unsafe."""
        self.reset()
        if expected_length <= 0:
            return "the announced length is empty"
        if expected_length > _MAX_LEARN_PACKET_LENGTH:
            return "the announced length exceeds the Broadlink packet limit"

        self.sequence = sequence
        self.expected_length = expected_length
        self.data = bytearray(expected_length)
        self.received = bytearray(expected_length)
        return None

    def append(
        self,
        sequence: int,
        position: int,
        part: bytes,
        checksum: int,
    ) -> str | None:
        """Append a valid transfer part at its announced position."""
        if self.sequence is None:
            return "no learn transfer is active"
        if sequence != self.sequence:
            return "the transfer sequence does not match"
        if not part:
            return "the transfer part is empty"
        if checksum != sum(part) % 0x100:
            return "the transfer part checksum does not match"
        if position < 0 or position + len(part) > self.expected_length:
            return "the transfer part exceeds the announced length"

        for offset, value in enumerate(part, start=position):
            if self.received[offset] and self.data[offset] != value:
                return "the transfer part conflicts with bytes already received"

        self.data[position : position + len(part)] = part
        self.received[position : position + len(part)] = b"\x01" * len(part)
        self.parts[(sequence, position)] = (part, checksum)
        return None

    def matches_completion_sequence(self, sequence: int) -> bool:
        """Match full-width and observed low-byte terminal sequences."""
        return sequence in self.completion_sequences()

    def completion_sequences(self) -> set[int]:
        """Return full-width and observed terminal representations."""
        if self.sequence is None:
            return set()
        full_sequences = {self.sequence, (self.sequence + 1) % 0x10000}
        return full_sequences | {value & 0xFF for value in full_sequences}

    def finish(self, sequence: int) -> tuple[bytes | None, str | None]:
        """Return the packet only after every announced byte was assembled."""
        if self.sequence is None:
            return None, "no learn transfer is active"
        if not self.matches_completion_sequence(sequence):
            return None, "the transfer sequence does not match"
        if self.expected_position < self.expected_length:
            return None, "the transfer ended before every byte arrived"
        return bytes(self.data), None


@dataclass(eq=False, slots=True)
class _OutgoingTransfer:
    """One serialized fixed-sequence transfer owned by the quirk."""

    sequence: int
    message: str
    completed: asyncio.Future[None]
    served: bytearray = field(init=False)
    response_tasks: set[asyncio.Task[None]] = field(default_factory=set)
    activity: int = 0
    request_activity: int = 0
    accepting_requests: bool = True

    def __post_init__(self) -> None:
        """Allocate exact byte-coverage tracking for this transfer."""
        self.served = bytearray(len(self.message))

    @property
    def fully_served(self) -> bool:
        """Return whether every wrapper byte reached the device."""
        return bool(self.served) and 0 not in self.served

    def note_activity(self) -> None:
        """Reset the inactivity deadline after valid firmware progress."""
        self.activity += 1

    def note_request(self) -> None:
        """Record device traffic used only to establish a quiet boundary."""
        self.request_activity += 1

    def mark_served(self, position: int, length: int) -> bool:
        """Record newly delivered bytes and report whether coverage advanced."""
        end = position + length
        advanced = self.served.find(0, position, end) != -1
        self.served[position:end] = b"\x01" * length
        if advanced:
            self.note_activity()
        return advanced


class ZGIR01Device(CustomZigpyDevice):
    """Device state required by the ZG-IR01 Zosung transport."""

    last_learned_ir_code = t.CharacterString("")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize per-device transfer state."""
        self.seq = 0
        self.ir_msg_to_send: dict[int, str] = {}
        self._ir_send_lock = asyncio.Lock()
        self._ir_send_callers = 0
        self._ir_send_transfer: _OutgoingTransfer | None = None
        super().__init__(*args, **kwargs)

    def next_seq(self) -> int:
        """Return the fixed transfer sequence required by this firmware."""
        return 0

    def begin_ir_send(self, message: str) -> _OutgoingTransfer:
        """Register the only transfer that may use the fixed sequence."""
        if self._ir_send_transfer is not None:
            raise RuntimeError("a ZG-IR01 transfer is already active")
        transfer = _OutgoingTransfer(
            sequence=self.next_seq(),
            message=message,
            completed=asyncio.get_running_loop().create_future(),
        )
        self._ir_send_transfer = transfer
        self.ir_msg_to_send[transfer.sequence] = message
        return transfer

    def finish_ir_send(
        self,
        transfer: _OutgoingTransfer,
        error: Exception | None = None,
    ) -> None:
        """Complete one transfer without touching a newer sequence-zero send."""
        if self._ir_send_transfer is not transfer:
            return
        if transfer.completed.done():
            return
        if error is None:
            transfer.completed.set_result(None)
        else:
            transfer.completed.set_exception(error)

    def abandon_ir_send(self, transfer: _OutgoingTransfer) -> None:
        """Discard a failed, cancelled, or timed-out transfer."""
        if self._ir_send_transfer is transfer:
            self._ir_send_transfer = None
            if self.ir_msg_to_send.get(transfer.sequence) == transfer.message:
                self.ir_msg_to_send.pop(transfer.sequence, None)
        if not transfer.completed.done():
            transfer.completed.cancel()


class ZGIR01Control(ZosungIRControl):
    """Own and serialize the complete ZG-IR01 send exchange."""

    async def command(self, command_id: Any, *args: Any, **kwargs: Any) -> Any:
        """Wait until the device consumes every byte of an IR send."""
        if command_id != self.ServerCommandDefs.IRSend.id:
            return await super().command(command_id, *args, **kwargs)

        device = self.endpoint.device
        if device._ir_send_callers > _MAX_QUEUED_SENDS:
            raise RuntimeError("ZG-IR01 send queue is full")
        device._ir_send_callers += 1
        try:
            async with device._ir_send_lock:
                return await self._send_ir_code(kwargs)
        finally:
            device._ir_send_callers -= 1

    async def _send_ir_code(self, kwargs: dict[str, Any]) -> foundation.Status:
        """Run one complete, serialized fixed-sequence transfer."""
        device = self.endpoint.device
        code = _broadlink_code_for_hardware(str(kwargs["code"]))
        message = json.dumps(
            {
                "key_num": 1,
                "delay": 300,
                "key1": {
                    "num": 1,
                    "freq": 38000,
                    "type": 1,
                    "key_code": code,
                },
            },
            separators=(",", ":"),
        )
        transfer = device.begin_ir_send(message)
        succeeded = False
        try:
            status = await self.endpoint.zosung_irtransmit.command(
                self.endpoint.zosung_irtransmit.ServerCommandDefs.receive_ir_frame_00.id,
                seq=transfer.sequence,
                length=len(message),
                unk1=0x00000000,
                clusterid=self.cluster_id,
                unk2=0x01,
                cmd=self.ServerCommandDefs.IRSend.id,
                unk3=0x0000,
                expect_reply=False,
                tsn=kwargs.get("tsn"),
            )
            if isinstance(status, foundation.Status) and (
                status != foundation.Status.SUCCESS
            ):
                raise RuntimeError(f"ZG-IR01 send start failed: {status.name}")
            await self._wait_for_completion(transfer)
            succeeded = True
            return foundation.Status.SUCCESS
        finally:
            try:
                await self._drain_transfer(transfer, cancel_pending=not succeeded)
            finally:
                device.abandon_ir_send(transfer)

    @staticmethod
    async def _wait_for_completion(transfer: _OutgoingTransfer) -> None:
        """Wait for completion while progress resets the inactivity deadline."""
        while not transfer.completed.done():
            activity = transfer.activity
            try:
                await asyncio.wait_for(
                    asyncio.shield(transfer.completed),
                    timeout=_OUTGOING_TRANSFER_TIMEOUT,
                )
            except TimeoutError as error:
                if transfer.activity != activity:
                    continue
                raise TimeoutError(
                    "ZG-IR01 did not consume the complete IR transmission"
                ) from error
        await transfer.completed

    @staticmethod
    async def _drain_transfer(
        transfer: _OutgoingTransfer, *, cancel_pending: bool
    ) -> None:
        """Bound cleanup while waiting for a quiet fixed-sequence boundary."""
        transfer.accepting_requests = False
        if cancel_pending:
            for task in tuple(transfer.response_tasks):
                task.cancel()
        try:
            async with asyncio.timeout(_OUTGOING_TRANSFER_DRAIN_TIMEOUT):
                while True:
                    if transfer.response_tasks:
                        await asyncio.gather(
                            *tuple(transfer.response_tasks), return_exceptions=True
                        )
                    request_activity = transfer.request_activity
                    await asyncio.sleep(_OUTGOING_TRANSFER_QUIET_PERIOD)
                    if (
                        request_activity == transfer.request_activity
                        and not transfer.response_tasks
                    ):
                        return
        except TimeoutError:
            _LOGGER.warning("Timed out draining ZG-IR01 transfer responses")
        finally:
            pending = tuple(transfer.response_tasks)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)


class ZGIR01Transmit(ZosungIRTransmit):
    """Apply the outgoing transfer behavior required by ZG-IR01."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize per-cluster outgoing response state."""
        super().__init__(*args, **kwargs)
        self._outgoing_parts_in_flight: set[tuple[int, int]] = set()
        self._learn_transfer = _LearnTransfer()
        self._last_completed_learn_parts: dict[tuple[int, int], tuple[bytes, int]] = {}

    async def command(self, command_id: Any, *args: Any, **kwargs: Any) -> Any:
        """Suppress default responses for coordinator-to-device frames."""
        kwargs.setdefault("disable_default_response", True)
        return await super().command(command_id, *args, **kwargs)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Any,
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Handle validated learning and the model-specific send lifecycle."""
        command_id = hdr.command_id
        if command_id == self.ServerCommandDefs.receive_ir_frame_00.id:
            self._start_learn_transfer(hdr, args)
            return
        if command_id == self.ServerCommandDefs.receive_ir_frame_02.id:
            self._send_message_part(hdr, args)
            return
        if command_id == self.ServerCommandDefs.receive_ir_frame_03.id:
            self._append_learn_transfer(hdr, args)
            return
        if command_id == self.ServerCommandDefs.receive_ir_frame_05.id:
            self._finish_learn_transfer(hdr, args)
            return

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
        if command_id == self.ServerCommandDefs.receive_ir_frame_04.id:
            self._finish_outgoing_transfer(int(args.seq))

    def _send_default_response(
        self,
        hdr: foundation.ZCLHeader,
        status: foundation.Status = foundation.Status.SUCCESS,
    ) -> None:
        """Send a default response only when the incoming frame requested one."""
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=status)

    def _request_learn_part(
        self,
        sequence: int,
        position: int,
        *,
        expect_reply: bool,
    ) -> None:
        """Request the first missing learned-code part."""
        self.create_catching_task(
            super().command(
                self.ServerCommandDefs.receive_ir_frame_02.id,
                seq=sequence,
                position=position,
                maxlen=0x38,
                expect_reply=expect_reply,
                disable_default_response=False,
            )
        )

    def _start_learn_transfer(self, hdr: foundation.ZCLHeader, args: Any) -> None:
        """Validate a learn announcement and request its first part."""
        sequence = int(args.seq)
        expected_length = int(args.length)
        error = self._learn_transfer.start(sequence, expected_length)
        if error is not None:
            _LOGGER.warning("Rejecting ZG-IR01 learn transfer: %s", error)
            self._send_default_response(hdr, foundation.Status.FAILURE)
            return

        self._last_completed_learn_parts.clear()
        self._send_default_response(hdr)
        self.create_catching_task(
            super().command(
                self.ServerCommandDefs.receive_ir_frame_01.id,
                zero=0,
                seq=sequence,
                length=expected_length,
                unk1=args.unk1,
                clusterid=args.clusterid,
                unk2=args.unk2,
                cmd=args.cmd,
                unk3=args.unk3,
                expect_reply=True,
                disable_default_response=False,
            )
        )
        self._request_learn_part(sequence, 0, expect_reply=True)

    def _append_learn_transfer(self, hdr: foundation.ZCLHeader, args: Any) -> None:
        """Validate one learned-code part and advance through the packet."""
        sequence = int(args.seq)
        position = int(args.position)
        part = bytes(args.msgpart)
        checksum = int(args.msgpartcrc)
        if (
            self._learn_transfer.sequence is None
            and self._last_completed_learn_parts.get((sequence, position))
            == (part, checksum)
        ):
            # This firmware can deliver a duplicate of the final data part after
            # its terminal frame. Acknowledge only an exact part from the most
            # recently completed transfer; unrelated orphan parts still fail.
            self._send_default_response(hdr)
            return
        error = self._learn_transfer.append(
            sequence,
            position,
            part,
            checksum,
        )
        if error is not None:
            _LOGGER.warning(
                "Rejecting ZG-IR01 learn transfer part: %s "
                "(sequence=%s, position=%s, bytes=%s)",
                error,
                sequence,
                position,
                len(part),
            )
            self._send_default_response(hdr, foundation.Status.FAILURE)
            if sequence == self._learn_transfer.sequence:
                self._request_learn_part(
                    sequence,
                    self._learn_transfer.expected_position,
                    expect_reply=False,
                )
            return

        self._send_default_response(hdr)
        if (
            self._learn_transfer.expected_position
            < self._learn_transfer.expected_length
        ):
            self._request_learn_part(
                sequence,
                self._learn_transfer.expected_position,
                expect_reply=False,
            )
            return

        self.create_catching_task(
            super().command(
                self.ServerCommandDefs.receive_ir_frame_04.id,
                zero0=0,
                seq=sequence,
                zero1=0,
                expect_reply=False,
                disable_default_response=False,
            )
        )

    def _finish_learn_transfer(self, hdr: foundation.ZCLHeader, args: Any) -> None:
        """Publish only a complete packet from the active learn transfer."""
        sequence = int(args.seq)
        if self._learn_transfer.sequence is None:
            # Stopping learning while idle can produce a terminal-only frame
            # with a new sequence. It carries no data and cannot publish a
            # signal, so acknowledge it idempotently.
            self._send_default_response(hdr)
            return
        packet, error = self._learn_transfer.finish(sequence)
        if error is not None:
            _LOGGER.warning(
                "Rejecting incomplete ZG-IR01 learn transfer: %s "
                "(sequence=%s, first_missing=%s, announced_length=%s)",
                error,
                sequence,
                self._learn_transfer.expected_position,
                self._learn_transfer.expected_length,
            )
            self._send_default_response(hdr, foundation.Status.FAILURE)
            expected_sequence = self._learn_transfer.sequence
            if (
                expected_sequence is not None
                and self._learn_transfer.matches_completion_sequence(sequence)
            ):
                self._request_learn_part(
                    expected_sequence,
                    self._learn_transfer.expected_position,
                    expect_reply=False,
                )
            return

        assert packet is not None
        try:
            normalized_packet = _broadlink_packet_from_hardware(packet)
        except ValueError as error:
            _LOGGER.warning("Rejecting invalid ZG-IR01 learned packet: %s", error)
            self._send_default_response(hdr, foundation.Status.FAILURE)
            self._learn_transfer.reset()
            return
        self._send_default_response(hdr)
        self.endpoint.device.last_learned_ir_code = base64.b64encode(
            normalized_packet
        ).decode()
        self._last_completed_learn_parts = self._learn_transfer.parts.copy()
        self._learn_transfer.reset()
        self.create_catching_task(
            self.endpoint.zosung_ircontrol.command(
                self.endpoint.zosung_ircontrol.ServerCommandDefs.IRLearn.id,
                on_off=False,
                expect_reply=False,
            )
        )

    def _send_message_part(self, hdr: foundation.ZCLHeader, args: Any) -> None:
        self._send_default_response(hdr)
        sequence = int(args.seq)
        transfer = self.endpoint.device._ir_send_transfer
        if transfer is None or transfer.sequence != sequence:
            _LOGGER.warning(
                "Ignoring ZG-IR01 transfer request for unknown sequence %s "
                "at position %s",
                sequence,
                int(args.position),
            )
            return
        transfer.note_request()
        if not transfer.accepting_requests:
            return
        message = transfer.message

        position = int(args.position)
        max_length = min(int(args.maxlen), _MAX_OUTGOING_CHUNK_LENGTH)
        if position < 0 or position > len(message) or max_length <= 0:
            _LOGGER.warning(
                "Ignoring invalid ZG-IR01 transfer request "
                "(sequence=%s, position=%s, max_length=%s)",
                sequence,
                position,
                max_length,
            )
            return

        if position == len(message) and not transfer.fully_served:
            _LOGGER.warning(
                "Ignoring premature ZG-IR01 transfer completion (sequence=%s)",
                sequence,
            )
            return

        part = message[position : position + max_length].encode()
        request_key = (id(transfer), position)
        if request_key in self._outgoing_parts_in_flight:
            return
        self._outgoing_parts_in_flight.add(request_key)
        task = asyncio.create_task(
            self._send_outgoing_part(request_key, transfer, part)
        )
        transfer.response_tasks.add(task)

        def forget_response_task(done_task: asyncio.Task[None]) -> None:
            transfer.response_tasks.discard(done_task)
            self._outgoing_parts_in_flight.discard(request_key)

        task.add_done_callback(forget_response_task)

    async def _send_outgoing_part(
        self,
        request_key: tuple[int, int],
        transfer: _OutgoingTransfer,
        part: bytes,
    ) -> None:
        """Send one requested part without queueing duplicate device retries."""
        _, position = request_key
        try:
            status = await super().command(
                self.ClientCommandDefs.resp_ir_frame_03.id,
                zero=0,
                seq=transfer.sequence,
                position=position,
                msgpart=part,
                msgpartcrc=sum(part) % 0x100,
                expect_reply=False,
                disable_default_response=True,
            )
            if isinstance(status, foundation.Status) and (
                status != foundation.Status.SUCCESS
            ):
                raise RuntimeError(
                    f"ZG-IR01 send part failed at position {position}: {status.name}"
                )
            transfer.mark_served(position, len(part))
            # This firmware does not send frame 0x04 after a transmission. Its
            # exact-end request is the observable signal that it consumed the
            # complete wrapper, so acknowledge that empty part before success.
            if position == len(transfer.message):
                self._finish_outgoing_transfer(transfer.sequence, transfer)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.endpoint.device.finish_ir_send(transfer, error)
        finally:
            self._outgoing_parts_in_flight.discard(request_key)

    def _finish_outgoing_transfer(
        self,
        sequence: int,
        transfer: _OutgoingTransfer | None = None,
    ) -> None:
        """Complete a send after the device consumes it or confirms it."""
        if transfer is None:
            transfer = self.endpoint.device._ir_send_transfer
        if transfer is None or transfer.sequence != sequence:
            return
        if not transfer.fully_served:
            _LOGGER.warning(
                "Ignoring premature ZG-IR01 transfer confirmation (sequence=%s)",
                sequence,
            )
            return
        self.endpoint.device.finish_ir_send(transfer)


_builder = (
    TuyaQuirkBuilder("HOBEIAN", "ZG-IR01")
    .zigpy_device_class(ZGIR01Device)
    .replace_cluster_occurrences(
        ZGIR01Control,
        replace_client_instances=False,
    )
    .replace_cluster_occurrences(
        ZGIR01Transmit,
        replace_client_instances=False,
    )
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=OnOff.cluster_id)
)

for channel in range(1, 7):
    _builder.tuya_switch(
        dp_id=channel,
        attribute_name=f"switch_{channel}",
        translation_key=f"switch_{channel}",
        fallback_name=f"Switch {channel}",
    )

for channel in range(1, 7):
    for state, offset in (("on", 0), ("off", 1)):
        _builder.tuya_enum(
            dp_id=118 + channel * 2 + offset,
            attribute_name=f"switch_{channel}_{state}_code",
            enum_class=IRStudyState,
            translation_key=f"switch_{channel}_{state}_code",
            fallback_name=f"Switch {channel} {state} code",
        )

_builder.skip_configuration().add_to_registry()
