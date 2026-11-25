"""Tests for the HOBEIAN ZG-IR01 infrared blaster quirk."""

import asyncio
import base64
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff, PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder import EntityPlatform
from zhaquirks.tuya import TUYA_CLUSTER_ID, TuyaCommand, TuyaData, TuyaDatapointData
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts1201 import ZosungIRControl
from zhaquirks.tuya.zg_ir01 import (
    IRStudyState,
    ZGIR01Control,
    ZGIR01Device,
    ZGIR01Transmit,
    _broadlink_code_for_hardware,
    _broadlink_packet_from_hardware,
    _decode_broadlink_packet,
    _encode_broadlink_packet,
    _hardware_tick,
    _LearnTransfer,
    _OutgoingTransfer,
    _standard_tick,
)

zhaquirks.setup()

_BASE_CLUSTERS = {
    1: {
        OnOff.cluster_id: ClusterType.Server,
        PowerConfiguration.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
        RelativeHumidity.cluster_id: ClusterType.Server,
        TUYA_CLUSTER_ID: ClusterType.Server,
    }
}
_BROADLINK_CODE = "JgAGAAABKJQSEg0F"
_SECOND_BROADLINK_CODE = "JgAGAAABKJQSEw0F"


def _cluster_ids(*, raw_transport: bool) -> dict[int, dict[int, ClusterType]]:
    """Return an interviewed ZG-IR01 cluster set."""
    clusters = {1: _BASE_CLUSTERS[1].copy()}
    if raw_transport:
        clusters[1].update(
            {
                ZosungIRControl.cluster_id: ClusterType.Server,
                ZGIR01Transmit.cluster_id: ClusterType.Server,
            }
        )
    return clusters


async def _serve_outgoing_message(transmit, message: str) -> None:
    """Request every wrapper byte and the exact-end terminal part."""
    for position in range(0, len(message), 50):
        request = bytes.fromhex("1167020000") + position.to_bytes(4, "little") + b"\x40"
        hdr, args = transmit.deserialize(request)
        transmit.handle_message(hdr, args)
        transfer = transmit.endpoint.device._ir_send_transfer
        assert transfer is not None
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))
    terminal = (
        bytes.fromhex("1167020000") + len(message).to_bytes(4, "little") + b"\x40"
    )
    hdr, args = transmit.deserialize(terminal)
    transmit.handle_message(hdr, args)
    transfer = transmit.endpoint.device._ir_send_transfer
    assert transfer is not None
    while transfer.response_tasks:
        await asyncio.gather(*tuple(transfer.response_tasks))


def _broadlink_packet(ticks: list[int]) -> str:
    """Build a canonical Broadlink packet from integer timing ticks."""
    payload = bytearray()
    for value in ticks:
        if value < 0x100:
            payload.append(value)
        else:
            payload.extend((0, value >> 8, value & 0xFF))
    packet = bytearray((0x26, 0, len(payload) & 0xFF, len(payload) >> 8))
    packet.extend(payload)
    packet.extend((0x0D, 0x05))
    while (len(packet) + 4) % 16:
        packet.append(0)
    return base64.b64encode(packet).decode()


def test_zg_ir01_normalizes_broadlink_timer_domains():
    """Standard library and learned timings cross a calibrated boundary."""
    standard_ticks = [18, 20, 40, 80, 160, 255, 256, 448, 512, 1313, 1800]
    code = _broadlink_packet(standard_ticks)

    hardware_code = _broadlink_code_for_hardware(code)
    repeat, hardware_ticks = _decode_broadlink_packet(base64.b64decode(hardware_code))

    assert repeat == 0
    assert hardware_ticks == [
        17,
        18,
        38,
        75,
        152,
        240,
        242,
        423,
        484,
        1241,
        1700,
    ]

    normalized_packet = _broadlink_packet_from_hardware(base64.b64decode(hardware_code))
    _, recovered_ticks = _decode_broadlink_packet(normalized_packet)
    assert all(
        abs(expected - recovered) <= 1
        for expected, recovered in zip(standard_ticks, recovered_ticks, strict=True)
    )


def test_zg_ir01_normalizes_learned_packet_dialect():
    """The device's total-length, unterminated capture becomes canonical."""
    hardware_ticks = [17, 18, 38, 75, 152, 240, 242, 423, 484, 1241, 1700]
    canonical_hardware = base64.b64decode(_broadlink_packet(hardware_ticks))
    timing_length = int.from_bytes(canonical_hardware[2:4], "little")
    timing_payload = canonical_hardware[4 : 4 + timing_length]
    learned_packet = (
        bytes((0x26, 0))
        + (len(timing_payload) + 4).to_bytes(2, "little")
        + timing_payload
    )

    repeat, decoded_hardware_ticks = _decode_broadlink_packet(learned_packet)
    assert repeat == 0
    assert decoded_hardware_ticks == hardware_ticks

    normalized_packet = _broadlink_packet_from_hardware(learned_packet)
    _, standard_ticks = _decode_broadlink_packet(normalized_packet)
    expected_ticks = [18, 20, 40, 80, 160, 255, 256, 448, 512, 1313, 1800]
    assert all(
        abs(expected - actual) <= 1
        for expected, actual in zip(expected_ticks, standard_ticks, strict=True)
    )


def test_zg_ir01_timer_mapping_is_reversible_across_broadlink_domain():
    """Every standard 16-bit timing survives the calibrated round trip."""
    for index in (0, 1):
        for standard_tick in range(1, 0x10000):
            hardware_tick = _hardware_tick(standard_tick, index)
            recovered_tick = _standard_tick(hardware_tick, index)

            assert 1 <= hardware_tick <= 0xFFFF
            assert abs(recovered_tick - standard_tick) <= 1


@pytest.mark.parametrize(
    "packet, message",
    (
        (b"not broadlink", "not a Broadlink"),
        (b"\x26\x00\x04\x00\x01\x02", "truncated"),
        (b"\x26\x00\x01\x00\x01\x00\x00", "terminator"),
        (b"\x26\x00\x01\x00\x01\x0d\x05\x01", "trailing"),
    ),
)
def test_zg_ir01_rejects_invalid_broadlink_packets(packet, message):
    """Malformed packets cannot reach the device or learned-code consumers."""
    with pytest.raises(ValueError, match=message):
        _broadlink_packet_from_hardware(packet)


def test_zg_ir01_rejects_oversized_broadlink_packets():
    """A timing-domain conversion cannot wrap the payload length field."""
    with pytest.raises(ValueError, match="timing payload exceeds"):
        _encode_broadlink_packet(0, [0x100] * 0x5556)

    with pytest.raises(ValueError, match="packet exceeds"):
        _decode_broadlink_packet(b"\x26\x00\x00\x00\x0d\x05" + b"\x00" * 0x10007)


@pytest.mark.parametrize("raw_transport", (False, True))
def test_zg_ir01_matches_capabilities(zigpy_device_from_v2_quirk, raw_transport):
    """Test the HOBEIAN device with both advertised cluster shapes."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=raw_transport),
    )
    endpoint = device.endpoints[1]

    assert isinstance(device, ZGIR01Device)
    assert device.next_seq() == 0
    assert device.seq == 0
    assert isinstance(endpoint.tuya_manufacturer, TuyaMCUCluster)
    assert type(endpoint.power) is PowerConfiguration
    assert type(endpoint.temperature) is TemperatureMeasurement
    assert type(endpoint.humidity) is RelativeHumidity
    assert type(endpoint.on_off) is OnOff

    if raw_transport:
        assert isinstance(endpoint.zosung_ircontrol, ZGIR01Control)
        assert isinstance(endpoint.zosung_irtransmit, ZGIR01Transmit)
    else:
        assert ZosungIRControl.cluster_id not in endpoint.in_clusters
        assert ZGIR01Transmit.cluster_id not in endpoint.in_clusters

    entry = DEVICE_REGISTRY.match_entry(device)
    definition = entry.zha_device_factory.quirk_definition
    assert definition.skip_configuration is True
    metadata = definition.entity_metadata
    assert len(metadata) == 18
    assert sum(item.entity_platform is EntityPlatform.SWITCH for item in metadata) == 6
    assert sum(item.entity_platform is EntityPlatform.SELECT for item in metadata) == 12
    assert {item.fallback_name for item in metadata} >= {
        "Switch 1",
        "Switch 6",
        "Switch 1 on code",
        "Switch 6 off code",
    }
    assert any(
        item.endpoint_id == 1 and item.cluster_id == OnOff.cluster_id
        for item in definition.disabled_default_entities
    )


def test_zg_ir01_learn_transfer_validation():
    """Learn assembly rejects corruption, gaps, and unrelated terminals."""
    transfer = _LearnTransfer()
    packet = b"abcdefgh"

    assert transfer.start(0x0117, len(packet)) is None
    assert transfer.append(0x0117, 4, packet[4:], sum(packet[4:]) % 0x100) is None
    assert transfer.expected_position == 0
    assert transfer.append(0x0117, 0, packet[:4], 0) == (
        "the transfer part checksum does not match"
    )
    assert transfer.append(0x0117, 0, packet[:4], sum(packet[:4]) % 0x100) is None
    assert transfer.append(0x0117, 0, packet[:4], sum(packet[:4]) % 0x100) is None
    assert transfer.append(0x0117, 1, b"BAD", sum(b"BAD") % 0x100) == (
        "the transfer part conflicts with bytes already received"
    )
    assert transfer.finish(0x0017) == (packet, None)
    assert transfer.finish(0x0018) == (packet, None)
    assert transfer.finish(0x0020) == (
        None,
        "the transfer sequence does not match",
    )


def test_zg_ir01_incomplete_and_invalid_learn_transfers():
    """Unsafe lengths, bounds, and premature terminals never publish data."""
    transfer = _LearnTransfer()

    assert transfer.append(1, 0, b"data", sum(b"data") % 0x100) == (
        "no learn transfer is active"
    )
    assert transfer.finish(1) == (None, "no learn transfer is active")
    assert transfer.start(1, 0) == "the announced length is empty"
    assert transfer.start(1, 0x1000C) is None
    assert transfer.start(1, 0x1000D) == (
        "the announced length exceeds the Broadlink packet limit"
    )
    assert transfer.start(0x0117, 4) is None
    assert transfer.append(0x0117, 0, b"", 0) == "the transfer part is empty"
    assert transfer.append(2, 0, b"data", sum(b"data") % 0x100) == (
        "the transfer sequence does not match"
    )
    assert (
        transfer.append(0x0117, 0, b"overflow", sum(b"overflow") % 0x100)
        == "the transfer part exceeds the announced length"
    )
    assert transfer.append(0x0117, 0, b"da", sum(b"da") % 0x100) is None
    assert transfer.finish(0x0017) == (
        None,
        "the transfer ended before every byte arrived",
    )


async def test_zg_ir01_datapoint_reports_and_writes(zigpy_device_from_v2_quirk):
    """Test representative channel and study-state datapoint round trips."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=False),
    )
    cluster = device.endpoints[1].tuya_manufacturer

    status = cluster.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[
                TuyaDatapointData(1, TuyaData(t.Bool.true)),
                TuyaDatapointData(121, TuyaData(IRStudyState.Registered)),
            ],
        )
    )
    assert status == foundation.Status.SUCCESS
    assert cluster.get("switch_1") is t.Bool.true
    assert cluster.get("switch_1_off_code") == IRStudyState.Registered

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        await cluster.write_attributes({"switch_1": t.Bool.true})
        await wait_for_zigpy_tasks()
        assert request_mock.call_args.kwargs["data"].endswith(
            b"\x01\x01\x01\x00\x01\x01"
        )

        await cluster.write_attributes({"switch_1_off_code": IRStudyState.Study})
        await wait_for_zigpy_tasks()
        assert request_mock.call_args.kwargs["data"].endswith(b"\x79\x04\x00\x01\x00")


async def test_zg_ir01_outgoing_transport_caps_parts(
    zigpy_device_from_v2_quirk,
):
    """Test raw transport uses sequence zero and sends at most 50 bytes."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    message = "A" * 80
    transfer = device.begin_ir_send(message)

    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    request = request_mock.call_args.kwargs
    assert request["cluster"] == ZGIR01Transmit.cluster_id
    assert request["command_id"] == (
        ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_03.id
    )
    sent_hdr, sent_args = transmit.deserialize(request["data"])
    assert sent_hdr.command_id == ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_03.id
    assert sent_args.seq == 0
    assert sent_args.position == 0
    assert bytes(sent_args.msgpart) == b"A" * 50
    assert sent_args.msgpartcrc == sum(b"A" * 50) % 0x100

    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as final_part_request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670200003200000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    final_part_hdr, final_part_args = transmit.deserialize(
        final_part_request_mock.call_args.kwargs["data"]
    )
    assert final_part_hdr.command_id == (
        ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_03.id
    )
    assert final_part_args.position == 50
    assert bytes(final_part_args.msgpart) == b"A" * 30

    with mock.patch.object(transmit.endpoint, "request") as unknown_request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670201000000000040"))
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        unknown_request_mock.assert_not_called()

    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as completion_request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670200005000000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    terminal_request = completion_request_mock.call_args_list[0].kwargs
    terminal_hdr, terminal_args = transmit.deserialize(terminal_request["data"])
    assert terminal_hdr.command_id == (
        ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_03.id
    )
    assert terminal_args.position == len(message)
    assert bytes(terminal_args.msgpart) == b""
    assert terminal_args.msgpartcrc == 0
    assert transfer.completed.done()
    device.abandon_ir_send(transfer)
    assert device.ir_msg_to_send == {}

    transfer = device.begin_ir_send(message)
    with mock.patch.object(transmit.endpoint, "request") as invalid_request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670200005100000040"))
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        invalid_request_mock.assert_not_called()
    assert transfer.request_activity == 1
    assert device.ir_msg_to_send == {0: message}
    device.abandon_ir_send(transfer)


async def test_zg_ir01_coalesces_in_flight_duplicate_part_requests(
    zigpy_device_from_v2_quirk,
):
    """Test concurrent retries do not backlog while later retries still work."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    transfer = device.begin_ir_send("A" * 80)
    frame = bytes.fromhex("11670200000000000040")
    hdr, args = transmit.deserialize(frame)
    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        transmit.handle_message(hdr, args)
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))
        assert request_mock.call_count == 1

        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    assert request_mock.call_count == 2
    first_hdr, first_args = transmit.deserialize(
        request_mock.call_args_list[0].kwargs["data"]
    )
    second_hdr, second_args = transmit.deserialize(
        request_mock.call_args_list[1].kwargs["data"]
    )
    assert first_hdr.command_id == second_hdr.command_id
    assert first_args == second_args
    device.abandon_ir_send(transfer)


async def test_zg_ir01_rejects_stale_sequence_zero_completion(
    zigpy_device_from_v2_quirk,
):
    """A previous send's terminal frames cannot complete a new transfer."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    previous = device.begin_ir_send("A" * 80)
    device.abandon_ir_send(previous)
    current = device.begin_ir_send("B" * 80)

    with mock.patch.object(transmit.endpoint, "request") as request_mock:
        terminal = bytes.fromhex("1167020000") + (80).to_bytes(4, "little") + b"\x40"
        hdr, args = transmit.deserialize(terminal)
        transmit.handle_message(hdr, args)
        hdr, args = transmit.deserialize(bytes.fromhex("0169040000000000"))
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    request_mock.assert_called_once()  # inherited frame-0x04 acknowledgement only
    assert not current.completed.done()
    assert device.ir_msg_to_send == {0: "B" * 80}
    device.abandon_ir_send(current)


async def test_zg_ir01_late_abandon_cannot_remove_new_identical_send(
    zigpy_device_from_v2_quirk,
):
    """Cleanup owns its map entry even when fixed-sequence payloads match."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    previous = device.begin_ir_send("same")
    device.abandon_ir_send(previous)
    current = device.begin_ir_send("same")

    device.abandon_ir_send(previous)

    assert device._ir_send_transfer is current
    assert device.ir_msg_to_send == {0: "same"}
    device.abandon_ir_send(current)


async def test_zg_ir01_cancels_owned_part_tasks_before_next_send(
    zigpy_device_from_v2_quirk,
):
    """Abandoned responses cannot leak old bytes into a later sequence-zero send."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    previous = device.begin_ir_send("A" * 80)
    part_started = asyncio.Event()

    async def blocked_request(**kwargs):
        part_started.set()
        await asyncio.Event().wait()

    with mock.patch.object(transmit.endpoint, "request", side_effect=blocked_request):
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        await part_started.wait()
        await ZGIR01Control._drain_transfer(previous, cancel_pending=True)

    assert not previous.response_tasks
    device.abandon_ir_send(previous)

    current = device.begin_ir_send("B" * 80)
    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        while current.response_tasks:
            await asyncio.gather(*tuple(current.response_tasks))

    _, sent = transmit.deserialize(request_mock.call_args.kwargs["data"])
    assert bytes(sent.msgpart) == b"B" * 50
    device.abandon_ir_send(current)


async def test_zg_ir01_cancelled_unstarted_part_does_not_leak_request_key(
    zigpy_device_from_v2_quirk,
):
    """Cancellation before coroutine entry cannot poison later part requests."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    transfer = device.begin_ir_send("A" * 80)

    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        assert len(transfer.response_tasks) == 1
        assert len(transmit._outgoing_parts_in_flight) == 1
        task = next(iter(transfer.response_tasks))
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await asyncio.sleep(0)

    assert not transfer.response_tasks
    assert not transmit._outgoing_parts_in_flight
    device.abandon_ir_send(transfer)


async def test_zg_ir01_part_delivery_failure_fails_transfer(
    zigpy_device_from_v2_quirk,
):
    """A non-success Zigbee result is not mistaken for delivered bytes."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    transfer = device.begin_ir_send("A" * 80)
    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.FAILURE
    ):
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    with pytest.raises(RuntimeError, match="send part failed"):
        await transfer.completed
    assert not transfer.fully_served
    device.abandon_ir_send(transfer)


async def test_zg_ir01_part_delivery_exception_fails_transfer(
    zigpy_device_from_v2_quirk,
):
    """A Zigbee delivery exception reaches the waiting send caller."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    transfer = device.begin_ir_send("A" * 80)
    with mock.patch.object(
        transmit.endpoint,
        "request",
        side_effect=RuntimeError("synthetic delivery failure"),
    ):
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

    with pytest.raises(RuntimeError, match="synthetic delivery failure"):
        await transfer.completed
    assert not transfer.fully_served
    device.abandon_ir_send(transfer)


async def test_zg_ir01_owns_and_serializes_complete_sends(
    zigpy_device_from_v2_quirk,
):
    """Each caller waits for its complete firmware sequence-zero transfer."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    control = device.endpoints[1].zosung_ircontrol
    transmit = device.endpoints[1].zosung_irtransmit
    first_hardware_code = _broadlink_code_for_hardware(_BROADLINK_CODE)
    second_hardware_code = _broadlink_code_for_hardware(_SECOND_BROADLINK_CODE)
    with mock.patch.object(
        control.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        first_send = asyncio.create_task(
            control.command(control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE)
        )
        await asyncio.sleep(0)
        first_message = device.ir_msg_to_send[0]
        assert device.seq == 0
        assert f'"key_code":"{first_hardware_code}"' in first_message
        assert not first_send.done()

        second_send = asyncio.create_task(
            control.command(
                control.ServerCommandDefs.IRSend.id, code=_SECOND_BROADLINK_CODE
            )
        )
        await asyncio.sleep(0)
        assert device.ir_msg_to_send == {0: first_message}
        assert not second_send.done()

        await _serve_outgoing_message(transmit, first_message)

        assert await first_send == foundation.Status.SUCCESS
        second_message = device.ir_msg_to_send[0]
        assert f'"key_code":"{second_hardware_code}"' in second_message
        assert not second_send.done()

        await _serve_outgoing_message(transmit, second_message)

        assert await second_send == foundation.Status.SUCCESS

    assert device.ir_msg_to_send == {}


async def test_zg_ir01_send_timeout_cleans_up(
    zigpy_device_from_v2_quirk,
    monkeypatch,
):
    """A device that stops requesting data cannot wedge later sends."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_TIMEOUT", 0.01)
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_QUIET_PERIOD", 0)
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    control = device.endpoints[1].zosung_ircontrol

    with (
        mock.patch.object(
            control.endpoint, "request", return_value=foundation.Status.SUCCESS
        ),
        pytest.raises(TimeoutError, match="did not consume"),
    ):
        await control.command(control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE)

    assert device.ir_msg_to_send == {}
    assert device._ir_send_transfer is None


async def test_zg_ir01_double_cancellation_cannot_leak_active_send(
    zigpy_device_from_v2_quirk,
    monkeypatch,
):
    """Cancellation during cancellation cleanup still releases sequence zero."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_QUIET_PERIOD", 1)
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    control = device.endpoints[1].zosung_ircontrol

    with mock.patch.object(
        control.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        send = asyncio.create_task(
            control.command(control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE)
        )
        await asyncio.sleep(0)
        transfer = device._ir_send_transfer
        assert transfer is not None

        send.cancel()
        for _ in range(10):
            if not transfer.accepting_requests:
                break
            await asyncio.sleep(0)
        assert not transfer.accepting_requests
        send.cancel()
        with pytest.raises(asyncio.CancelledError):
            await send

    assert device._ir_send_transfer is None
    assert device.ir_msg_to_send == {}


async def test_zg_ir01_progress_resets_inactivity_timeout(monkeypatch):
    """A long transfer remains alive while the device keeps consuming parts."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_TIMEOUT", 0.01)
    completed = asyncio.get_running_loop().create_future()
    transfer = _OutgoingTransfer(0, "payload", completed)
    waiter = asyncio.create_task(ZGIR01Control._wait_for_completion(transfer))
    await asyncio.sleep(0.007)
    transfer.note_activity()
    await asyncio.sleep(0.007)
    completed.set_result(None)
    await waiter


async def test_zg_ir01_duplicate_parts_do_not_reset_inactivity_timeout(monkeypatch):
    """Retries of already delivered bytes cannot keep a stalled send alive."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_TIMEOUT", 0.01)
    completed = asyncio.get_running_loop().create_future()
    transfer = _OutgoingTransfer(0, "payload", completed)
    assert transfer.mark_served(0, 1)
    waiter = asyncio.create_task(ZGIR01Control._wait_for_completion(transfer))

    async def repeat_served_part() -> None:
        for _ in range(4):
            await asyncio.sleep(0.004)
            assert not transfer.mark_served(0, 1)

    retries = asyncio.create_task(repeat_served_part())
    with pytest.raises(TimeoutError, match="did not consume"):
        await asyncio.wait_for(waiter, timeout=0.05)
    await retries


async def test_zg_ir01_drain_has_a_total_deadline(monkeypatch):
    """Continuous stale traffic cannot delay fixed-sequence cleanup forever."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_QUIET_PERIOD", 0.01)
    monkeypatch.setattr(
        "zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_DRAIN_TIMEOUT", 0.025
    )
    completed = asyncio.get_running_loop().create_future()
    transfer = _OutgoingTransfer(0, "payload", completed)

    async def keep_requesting() -> None:
        while True:
            transfer.note_request()
            await asyncio.sleep(0.002)

    traffic = asyncio.create_task(keep_requesting())
    await asyncio.wait_for(
        ZGIR01Control._drain_transfer(transfer, cancel_pending=False),
        timeout=0.1,
    )
    traffic.cancel()
    await asyncio.gather(traffic, return_exceptions=True)
    assert not transfer.accepting_requests


async def test_zg_ir01_bounds_concurrent_send_callers(
    zigpy_device_from_v2_quirk, monkeypatch
):
    """One stalled device cannot accumulate an unbounded lock wait queue."""
    monkeypatch.setattr("zhaquirks.tuya.zg_ir01._OUTGOING_TRANSFER_QUIET_PERIOD", 0)
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    control = device.endpoints[1].zosung_ircontrol
    with mock.patch.object(
        control.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        callers = [
            asyncio.create_task(
                control.command(
                    control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE
                )
            )
            for _ in range(9)
        ]
        await asyncio.sleep(0)
        assert device._ir_send_callers == 9
        with pytest.raises(RuntimeError, match="queue is full"):
            await control.command(
                control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE
            )
        for caller in callers:
            caller.cancel()
        await asyncio.gather(*callers, return_exceptions=True)

    assert device._ir_send_callers == 0


async def test_zg_ir01_send_dispatch_failure_cleans_up(
    zigpy_device_from_v2_quirk,
):
    """A failed initial Zigbee request releases all fixed-sequence state."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    control = device.endpoints[1].zosung_ircontrol

    with (
        mock.patch.object(
            control.endpoint,
            "request",
            side_effect=RuntimeError("synthetic delivery failure"),
        ),
        pytest.raises(RuntimeError, match="synthetic delivery failure"),
    ):
        await control.command(control.ServerCommandDefs.IRSend.id, code=_BROADLINK_CODE)

    assert device.ir_msg_to_send == {}
    assert device._ir_send_transfer is None


async def test_zg_ir01_transport_command_defaults_and_completion(
    zigpy_device_from_v2_quirk,
):
    """Test outgoing defaults are suppressed and completed sends are cleared."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit

    with mock.patch(
        "zhaquirks.tuya.ts1201.ZosungIRTransmit.command",
        new=mock.AsyncMock(return_value=foundation.Status.SUCCESS),
    ) as command_mock:
        await transmit.command(
            ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_05.id,
            seq=0,
            zero=0,
        )
        command_mock.assert_awaited_once_with(
            ZGIR01Transmit.ClientCommandDefs.resp_ir_frame_05.id,
            seq=0,
            zero=0,
            disable_default_response=True,
        )

    transfer = device.begin_ir_send("synthetic")
    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        hdr, args = transmit.deserialize(bytes.fromhex("0169040000000000"))
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        assert not transfer.completed.done()
        hdr, args = transmit.deserialize(bytes.fromhex("11670200000000000040"))
        transmit.handle_message(hdr, args)
        while transfer.response_tasks:
            await asyncio.gather(*tuple(transfer.response_tasks))

        hdr, args = transmit.deserialize(bytes.fromhex("0169040000000000"))
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    device.abandon_ir_send(transfer)
    assert device.ir_msg_to_send == {}
    assert transfer.completed.done()


async def test_zg_ir01_rejects_invalid_learn_start(zigpy_device_from_v2_quirk):
    """A zero-length announcement fails before allocation or part requests."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    start = bytes.fromhex("05021001000700000000000000000004e001020000")

    with (
        mock.patch.object(transmit, "send_default_rsp") as default_response_mock,
        mock.patch.object(transmit.endpoint, "request") as request_mock,
    ):
        hdr, args = transmit.deserialize(start)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    default_response_mock.assert_called_once_with(
        hdr,
        status=foundation.Status.FAILURE,
    )
    request_mock.assert_not_called()
    assert transmit._learn_transfer.sequence is None


async def test_zg_ir01_acknowledges_idle_learn_terminal(
    zigpy_device_from_v2_quirk,
):
    """A terminal-only stop response is harmless while no transfer is active."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    terminal = bytes.fromhex("09690542000000")

    with mock.patch.object(transmit, "send_default_rsp") as default_response_mock:
        hdr, args = transmit.deserialize(terminal)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    default_response_mock.assert_called_once_with(
        hdr,
        status=foundation.Status.SUCCESS,
    )
    assert device.last_learned_ir_code == ""


async def test_zg_ir01_rejects_mismatched_active_learn_terminal(
    zigpy_device_from_v2_quirk,
):
    """An unrelated terminal cannot finish or discard an active transfer."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    sequence = 0x0117
    start = (
        bytes.fromhex("0502100100")
        + sequence.to_bytes(2, "little")
        + (4).to_bytes(4, "little")
        + bytes.fromhex("0000000004e001020000")
    )
    terminal = bytes.fromhex("09690518000000")

    with (
        mock.patch.object(
            transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
        ),
        mock.patch.object(transmit, "send_default_rsp") as default_response_mock,
    ):
        hdr, args = transmit.deserialize(start)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        hdr, args = transmit.deserialize(terminal)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    default_response_mock.assert_called_with(
        hdr,
        status=foundation.Status.FAILURE,
    )
    assert transmit._learn_transfer.sequence == sequence
    assert device.last_learned_ir_code == ""


async def test_zg_ir01_low_byte_terminal_retries_incomplete_learn(
    zigpy_device_from_v2_quirk,
):
    """A truncated terminal retries the full-width transfer's first gap."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    packet = b"abcdefgh"
    sequence = 0x0117

    with mock.patch.object(
        transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request_mock:
        start = (
            bytes.fromhex("0502100100")
            + sequence.to_bytes(2, "little")
            + len(packet).to_bytes(4, "little")
            + bytes.fromhex("0000000004e001020000")
        )
        hdr, args = transmit.deserialize(start)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        part = packet[:4]
        part_frame = (
            bytes.fromhex("09680300")
            + sequence.to_bytes(2, "little")
            + (0).to_bytes(4, "little")
            + bytes((len(part),))
            + part
            + bytes((sum(part) % 0x100,))
        )
        hdr, args = transmit.deserialize(part_frame)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        terminal = bytes.fromhex("096905") + bytes((sequence & 0xFF, 0, 0, 0))
        hdr, args = transmit.deserialize(terminal)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    assert device.last_learned_ir_code == ""
    part_requests = []
    for request in request_mock.call_args_list:
        if request.kwargs["cluster"] != transmit.cluster_id:
            continue
        request_hdr, request_args = transmit.deserialize(request.kwargs["data"])
        if (
            request_hdr.frame_control.is_cluster
            and request_hdr.command_id
            == transmit.ServerCommandDefs.receive_ir_frame_02.id
        ):
            part_requests.append(request_args)
    assert int(part_requests[-1].seq) == sequence
    assert int(part_requests[-1].position) == len(part)


async def test_zg_ir01_validates_capture_protocol(
    zigpy_device_from_v2_quirk,
    caplog,
):
    """Capture uses the proven shared flow, including a truncated terminal seq."""
    device = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
    )
    transmit = device.endpoints[1].zosung_irtransmit
    packet = base64.b64decode(_broadlink_packet([20 + index for index in range(65)]))
    sequence = 0x0117

    with (
        mock.patch.object(
            transmit.endpoint, "request", return_value=foundation.Status.SUCCESS
        ) as request_mock,
        mock.patch.object(transmit, "send_default_rsp") as default_response_mock,
    ):
        start = (
            bytes.fromhex("0502100100")
            + sequence.to_bytes(2, "little")
            + len(packet).to_bytes(4, "little")
            + bytes.fromhex("0000000004e001020000")
        )
        hdr, args = transmit.deserialize(start)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        first_part = packet[:55]
        first_part_frame = (
            bytes.fromhex("09680300")
            + sequence.to_bytes(2, "little")
            + (0).to_bytes(4, "little")
            + bytes((len(first_part),))
            + first_part
            + bytes((sum(first_part) % 0x100,))
        )
        hdr, args = transmit.deserialize(first_part_frame)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        assert device.last_learned_ir_code == ""

        remaining = packet[len(first_part) :]
        final_part = (
            bytes.fromhex("09690300")
            + sequence.to_bytes(2, "little")
            + len(first_part).to_bytes(4, "little")
            + bytes((len(remaining),))
            + remaining
            + bytes((sum(remaining) % 0x100,))
        )
        hdr, args = transmit.deserialize(final_part)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        final_part_header = hdr
        final_part_args = args

        # The observed firmware truncates a 16-bit sequence to its low byte.
        complete = bytes.fromhex("096905") + bytes((sequence & 0xFF, 0, 0, 0))
        hdr, args = transmit.deserialize(complete)
        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        request_count = request_mock.call_count
        caplog.clear()
        transmit.handle_message(final_part_header, final_part_args)
        await wait_for_zigpy_tasks()
        assert request_mock.call_count == request_count
        assert default_response_mock.call_args.kwargs["status"] == (
            foundation.Status.SUCCESS
        )
        assert "Rejecting ZG-IR01 learn transfer part" not in caplog.text

        altered_remaining = bytes((remaining[0] ^ 0x01,)) + remaining[1:]
        altered_final_part = (
            bytes.fromhex("09690300")
            + sequence.to_bytes(2, "little")
            + len(first_part).to_bytes(4, "little")
            + bytes((len(altered_remaining),))
            + altered_remaining
            + bytes((sum(altered_remaining) % 0x100,))
        )
        altered_header, altered_args = transmit.deserialize(altered_final_part)
        transmit.handle_message(altered_header, altered_args)
        await wait_for_zigpy_tasks()
        assert default_response_mock.call_args.kwargs["status"] == (
            foundation.Status.FAILURE
        )
        assert "no learn transfer is active" in caplog.text

        transmit.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        assert request_mock.call_count == request_count
        assert default_response_mock.call_args.kwargs["status"] == (
            foundation.Status.SUCCESS
        )

    assert (
        device.last_learned_ir_code
        == base64.b64encode(_broadlink_packet_from_hardware(packet)).decode()
    )
    learn_requests = []
    for request in request_mock.call_args_list:
        if request.kwargs["cluster"] != transmit.cluster_id:
            continue
        request_hdr, request_args = transmit.deserialize(request.kwargs["data"])
        if request_hdr.frame_control.is_cluster and request_hdr.command_id in {
            transmit.ServerCommandDefs.receive_ir_frame_01.id,
            transmit.ServerCommandDefs.receive_ir_frame_02.id,
            transmit.ServerCommandDefs.receive_ir_frame_04.id,
        }:
            learn_requests.append((request_hdr, request_args))
    assert [header.command_id for header, _ in learn_requests] == [1, 2, 2, 4]
    assert all(
        not header.frame_control.disable_default_response
        for header, _ in learn_requests
    )
    assert [
        int(args.position) for header, args in learn_requests if header.command_id == 2
    ] == [0, 55]


async def test_zg_ir01_transport_state_is_per_instance(
    zigpy_device_from_v2_quirk,
):
    """Test learned and outgoing transfer state is not shared by devices."""
    first = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
        ieee=t.EUI64(b"ZgIrDev1"),
    )
    second = zigpy_device_from_v2_quirk(
        "HOBEIAN",
        "ZG-IR01",
        cluster_ids=_cluster_ids(raw_transport=True),
        ieee=t.EUI64(b"ZgIrDev2"),
    )

    first_transmit = first.endpoints[1].zosung_irtransmit
    second_transmit = second.endpoints[1].zosung_irtransmit
    first_transfer = first.begin_ir_send("synthetic")
    first._ir_send_callers = 1
    assert first_transmit._learn_transfer.start(7, 4) is None
    first_transmit._outgoing_parts_in_flight.add((id(first_transfer), 0))

    assert second.ir_msg_to_send == {}
    assert second._ir_send_transfer is None
    assert second._ir_send_callers == 0
    assert first._ir_send_lock is not second._ir_send_lock
    assert second_transmit._learn_transfer.sequence is None
    assert not second_transmit._outgoing_parts_in_flight

    first.abandon_ir_send(first_transfer)
