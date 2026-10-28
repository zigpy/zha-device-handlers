"""Tests for the Tuya TS1201 / Zosung IR blaster."""

import asyncio
import base64
import contextlib
import struct
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
import zigpy.zdo.types as zdo_t

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
import zhaquirks.tuya.ts1201

zhaquirks.setup()

# Learned by a physical ZS06 from a washlet remote ("wash and dry"). At 251 bytes it is
# learned in five parts, sent as a 414-byte message in eight, and its base64 form is
# longer than 255 characters.
REAL_LEARNED_IR_CODE = "DVQNzQaCAb4BggHyAYIBwAdAC0ADByMFvgG+AYIBQAtABwC+YAFAB+ALAwG+AcAvBSMFggG+AcADQAHAC4AHwB9ABwUjBb4BvgFAB4AD4AULQAFAEwe+ASMFvgG+AUALCIIBIwWCAYIBviABQAWAA0ATAL4gAUAHQAMAvmABgAcBhdDgAecAvuAAAUALgAPgBy8DvgGCAYADQAFAC4ABgAkBggHAL0AHwRvABwG+AeABA0AfQA9AB0AD4AULA74BIwWAAwG+AYAbAL4gAUATAb4BQAsBggHgAQtAAQGCAUADBCMFggG+IAEBIwWAAwu+AYIBvgGCAb4BvgE="  # codespell:ignore
# The device sends at most one byte less than the part length it is asked for.
DEVICE_PART_LENGTH = zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_LENGTH - 1


def device_frame(cluster, command_name, **kwargs):
    """Build a frame as the blaster sends it on the given cluster."""
    command = getattr(cluster.ServerCommandDefs, command_name)
    data = bytes([0x11, 0x42, command.id]) + command.schema(**kwargs).serialize()
    return cluster.deserialize(data)


def sent_commands(request_mock, cluster):
    """Decode the commands sent on the given cluster, in order."""
    commands = []
    for call in request_mock.mock_calls:
        if call.kwargs["cluster"] != cluster.cluster_id:
            continue
        command = cluster.server_commands[call.kwargs["command_id"]]
        args, _ = command.schema.deserialize(call.kwargs["data"][3:])
        commands.append((command.id, args))
    return commands


def announce_learned_code(transmit, length, seq=1):
    """Frame 0x00: the blaster announces a learned code of the given length."""
    transmit.handle_message(
        *device_frame(
            transmit,
            "receive_ir_frame_00",
            seq=seq,
            length=length,
            unk1=0,
            clusterid=zhaquirks.tuya.ts1201.ZosungIRControl.cluster_id,
            unk2=1,
            cmd=4,
            unk3=0,
        )
    )


def learned_code_part(transmit, position, msg_part, seq=1, crc=None):
    """Frame 0x03: the blaster hands over one part of a learned code."""
    transmit.handle_message(
        *device_frame(
            transmit,
            "receive_ir_frame_03",
            zero=0,
            seq=seq,
            position=position,
            msgpart=msg_part,
            msgpartcrc=(
                zhaquirks.tuya.ts1201.ir_msg_part_crc(msg_part) if crc is None else crc
            ),
        )
    )


def learned_code_done(transmit, seq=1):
    """Frame 0x05: the blaster confirms the learned code was handed over."""
    transmit.handle_message(
        *device_frame(transmit, "receive_ir_frame_05", seq=seq, zero=0)
    )


def request_msg_part(transmit, seq, position):
    """Frame 0x02: the blaster asks for a part of the IR message being sent."""
    transmit.handle_message(
        *device_frame(
            transmit,
            "receive_ir_frame_02",
            seq=seq,
            position=position,
            maxlen=zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_LENGTH,
        )
    )


def confirm_sent(transmit, seq):
    """Frame 0x04: the blaster confirms it received the whole IR message."""
    transmit.handle_message(
        *device_frame(transmit, "receive_ir_frame_04", zero0=0, seq=seq, zero1=0)
    )


async def pull_ir_msg(transmit, seq, length):
    """Request every part of an IR message being sent and return what was sent."""
    received = b""
    for position in range(0, length, zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_LENGTH):
        request_msg_part(transmit, seq, position)
        await wait_for_zigpy_tasks()
        command_id, args = sent_commands(transmit.endpoint.request, transmit)[-1]
        assert command_id == 0x03
        assert args.seq == seq
        assert args.position == position
        assert args.msgpartcrc == zhaquirks.tuya.ts1201.ir_msg_part_crc(args.msgpart)
        received += args.msgpart
    return received


async def start_ir_send(control, **kwargs):
    """Start an IRSend and return its task once it waits for the blaster."""
    requests = control.endpoint.request.await_count
    task = asyncio.create_task(
        control.command(control.ServerCommandDefs.IRSend.id, **kwargs)
    )
    # A send queued behind another one never gets as far as a request.
    for _ in range(10):
        await asyncio.sleep(0)
        if control.endpoint.request.await_count > requests:
            break
    return task


async def wait_for_announcement(transmit, seq):
    """Let the loop run until the IR message with `seq` is announced."""
    for _ in range(20):
        await asyncio.sleep(0)
        if (0x00, seq) in [
            (command_id, args.seq)
            for command_id, args in sent_commands(transmit.endpoint.request, transmit)
        ]:
            return
    raise AssertionError(f"IR message {seq} was never announced")


def last_announced_seq(transmit):
    """Return the seq of the last IR message announced to the blaster."""
    command_id, args = sent_commands(transmit.endpoint.request, transmit)[-1]
    assert command_id == 0x00
    return args.seq


def ir_msg(code, freq=38000, num=1):
    """Return the message the blaster expects for an IR code."""
    return (
        f'{{"key_num":1,"delay":300,"key1":'
        f'{{"num":{num},"freq":{freq},"type":1,"key_code":"{code}"}}}}'
    ).encode()


@pytest.fixture
def zs06(zigpy_device_from_quirk):
    """Return a ZS06 blaster whose endpoint requests always succeed."""
    dev = zigpy_device_from_quirk(zhaquirks.tuya.ts1201.ZosungIRBlaster_ZS06)
    # The ZS06 is a mains-powered router, as its diagnostics report.
    dev.node_desc = zdo_t.NodeDescriptor(
        logical_type=zdo_t.LogicalType.Router,
        mac_capability_flags=zdo_t.NodeDescriptor.MACCapabilityFlags(142),
    )
    with mock.patch.object(
        dev.endpoints[1], "request", return_value=foundation.Status.SUCCESS
    ):
        yield dev


@pytest.mark.parametrize(
    "manufacturer",
    ("_TZ3290_ot6ewjvmejq5ekhl", "_TZ3290_yyax9ajf"),
)
def test_ts1201_signature(assert_signature_matches_quirk, manufacturer):
    """Test TS1201 remote signature is matched to its quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4098, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0xf000",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0004",
                    "0x0005",
                    "0x0006",
                    "0xe004",
                    "0xed00",
                ],
                "out_clusters": ["0x000a", "0x0019"],
            }
        },
        "manufacturer": manufacturer,
        "model": "TS1201",
        "class": "zhaquirks.tuya.ts1201.ZosungIRBlaster",
    }
    assert_signature_matches_quirk(zhaquirks.tuya.ts1201.ZosungIRBlaster, signature)


async def test_ts1201_ir_blaster(zigpy_device_from_quirk):
    """Test Tuya TS1201 IR blaster."""
    quirk = zhaquirks.tuya.ts1201.ZosungIRBlaster

    part_max_length = 0x38

    ir_code_to_learn = "A/AESQFAAwUIAvAErwHgAQNADwXwBK8BrwFABcADAXYfwAkBrwHACeABBwXwBK8BrwFABcAD4GgvAgRJAQ=="
    ir_code_to_learn_bytes = base64.b64decode(ir_code_to_learn)
    ir_code_to_learn_part1 = ir_code_to_learn_bytes[: part_max_length - 1]
    crc1 = 0
    for x in ir_code_to_learn_part1:
        crc1 = (crc1 + x) % 0x100
    ir_code_to_learn_part2 = ir_code_to_learn_bytes[part_max_length - 1 :]
    crc2 = 0
    for x in ir_code_to_learn_part2:
        crc2 = (crc2 + x) % 0x100

    # TV power off/on code
    ir_code_to_send = "B3wPfA/5AcoH4AUDAeUDgAPAC+AHB+AHA+ADN+ALBw=="  # codespell:ignore
    ir_msg = (
        f'{{"key_num":1,"delay":300,"key1":{{'
        f'"num":1,"freq":38000,"type":1,"key_code":"{ir_code_to_send}"}}}}'
    )
    ir_msg_length = len(ir_msg)
    position = 0
    control_cluster_id = 57348
    transmit_cluster_id = 60672

    ts1201_dev = zigpy_device_from_quirk(quirk)
    ts1201_control_cluster = ts1201_dev.endpoints[1].zosung_ircontrol
    ts1201_transmit_cluster = ts1201_dev.endpoints[1].zosung_irtransmit
    ts1201_transmit_listener = ClusterListener(ts1201_transmit_cluster)

    with mock.patch.object(
        ts1201_control_cluster.endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
    ) as m1:
        # study mode on
        rsp = await ts1201_control_cluster.command(0x0001, on_off=True)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=1,
            data=b"\x01\x01\x00" + b'{"study":0}',
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert rsp == foundation.Status.SUCCESS

        # simulate receive_ir_frame_00 (first frame when device sends a learned code)
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01k\x00\x01\x00=\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x04\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=3,
            data=(
                b"\x01\x03\x02\x01\x00"
                + struct.pack("<L", position)
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[0][2].command.name
            == "receive_ir_frame_00"
        )
        assert ts1201_transmit_listener.cluster_commands[0][2].length == 61
        assert (
            ts1201_transmit_listener.cluster_commands[0][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[0][2].cmd == 0x04

        # simulate receive_ir_frame_01
        position += part_max_length - 1
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\tl\x03\x00\x01\x00\x00\x00\x00\x007\x03\xf0\x04I\x01@\x03\x05\x08\x02"
            b"\xf0\x04\xaf\x01\xe0\x01\x03@\x0f\x05\xf0\x04\xaf\x01\xaf\x01@\x05\xc0"
            b"\x03\x01v\x1f\xc0\t\x01\xaf\x01\xc0\t\xe0\x01\x07\x05\xf0\x04\xaf\x01"
            b"\xaf\x01@\x05\xc0\x03\xe0\xcd"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=4,
            data=(
                b"\x01\x04\x02\x01\x00"
                + struct.pack("<L", position)
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[1][2].command.name
            == "resp_ir_frame_03"
        )
        assert ts1201_transmit_listener.cluster_commands[1][2].position == 0
        assert (
            ts1201_transmit_listener.cluster_commands[1][2].msgpart
            == ir_code_to_learn_part1
        )
        assert ts1201_transmit_listener.cluster_commands[1][2].msgpartcrc == crc1

        # simulate second receive_ir_frame_01
        position += part_max_length - 1
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\tm\x03\x00\x01\x007\x00\x00\x00\x06h/\x02\x04I\x01\xe7"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=5,
            data=b"\x01\x05\x04\x00\x01\x00\x00\x00",
            command_id=4,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].command.name
            == "resp_ir_frame_03"
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].position
            == position - part_max_length + 1
        )
        assert (
            ts1201_transmit_listener.cluster_commands[2][2].msgpart
            == ir_code_to_learn_part2
        )
        assert ts1201_transmit_listener.cluster_commands[2][2].msgpartcrc == crc2

        # simulate last receive_ir_frame_01
        hdr, args = ts1201_transmit_cluster.deserialize(b"\tn\x05\x01\x00\x00\x00")
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=6,
            data=b'\x01\x06\x00{"study":1}',
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[3][2].command.name
            == "resp_ir_frame_05"
        )

        # should return learned IR code
        succ, fail = await ts1201_control_cluster.read_attributes(
            ("last_learned_ir_code",)
        )
        assert succ[0] == ir_code_to_learn

        # test unknown attribute
        succ, fail = await ts1201_control_cluster.read_attributes(
            ("another_attribute",)
        )
        assert fail["another_attribute"] == foundation.Status.UNSUPPORTED_ATTRIBUTE

        # IR send tests
        send_task = await start_ir_send(ts1201_control_cluster, code=ir_code_to_send)
        # IR send must call ir transmit command id 0x00
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=7,
            data=(
                b"\x01\x07\x00\x01\x00"
                + struct.pack("<I", ir_msg_length)
                + b"\x00\x00\x00\x00"
                + struct.pack("<H", control_cluster_id)
                + b"\x01\x02\x00\x00"
            ),
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )

        # simulate receive_ir_frame_00
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x05\x02\x10\x01\x00\x01\x00z\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x02\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=9,
            data=(
                b"\x01\x09\x02\x01\x00\x00\x00\x00\x00"
                + struct.pack("<B", part_max_length)
            ),
            command_id=2,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[4][2].command.name
            == "receive_ir_frame_00"
        )
        assert ts1201_transmit_listener.cluster_commands[4][2].length == ir_msg_length
        assert (
            ts1201_transmit_listener.cluster_commands[4][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[4][2].cmd == 2

        # simulate receive_ir_frame_01
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01f\x01\x00\x01\x00z\x00\x00\x00\x00\x00\x00\x00\x04\xe0\x01\x02\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[5][2].command.name
            == "receive_ir_frame_01"
        )
        assert ts1201_transmit_listener.cluster_commands[5][2].length == ir_msg_length
        assert (
            ts1201_transmit_listener.cluster_commands[5][2].clusterid
            == control_cluster_id
        )
        assert ts1201_transmit_listener.cluster_commands[5][2].cmd == 2

        # simulate receive_ir_frame_02
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x11g\x02\x01\x00\x00\x00\x00\x00@"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[6][2].command.name
            == "receive_ir_frame_02"
        )
        assert ts1201_transmit_listener.cluster_commands[6][2].position == 0
        assert ts1201_transmit_listener.cluster_commands[6][2].maxlen == 64

        # simulate receive_ir_frame_04
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x01i\x04\x00\x01\x00\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=transmit_cluster_id,
            sequence=11,
            data=b"\x01\x0b\x05\x01\x00\x00\x00",
            command_id=5,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert (
            ts1201_transmit_listener.cluster_commands[7][2].command.name
            == "receive_ir_frame_04"
        )
        # IRSend returns once the device has confirmed the message.
        rsp = await send_task
        assert rsp.status == foundation.Status.SUCCESS

        # test raw data command
        rsp = await ts1201_control_cluster.command(
            0x0000, t.Bytes(b"\x00\x01\x02\x03\x04")
        )
        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=control_cluster_id,
            sequence=12,
            data=b"\x01\x0c\x00\x00\x01\x02\x03\x04",
            command_id=0,
            timeout=5,
            expect_reply=True,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
            retries=None,
            retry_delay=None,
            aps_encryption=False,
        )
        assert rsp == foundation.Status.SUCCESS

        # test unknown request from device
        hdr, args = ts1201_transmit_cluster.deserialize(
            b"\x110\x06\x01\x00\x00\x00\x00\x00"
        )
        ts1201_transmit_cluster.handle_message(hdr, args)
        assert (
            ts1201_transmit_listener.cluster_commands[8][2]
            == b"\x01\x00\x00\x00\x00\x00"
        )


async def test_ts1201_learn_state_is_per_instance(zigpy_device_from_quirk):
    """Test TS1201 learn state is per cluster instance, not shared class state."""
    dev1 = zigpy_device_from_quirk(
        zhaquirks.tuya.ts1201.ZosungIRBlaster,
        ieee=t.EUI64.convert("11:11:11:11:11:11:11:11"),
    )
    dev2 = zigpy_device_from_quirk(
        zhaquirks.tuya.ts1201.ZosungIRBlaster_ZS06,
        ieee=t.EUI64.convert("22:22:22:22:22:22:22:22"),
    )
    transmit1 = dev1.endpoints[1].zosung_irtransmit
    transmit2 = dev2.endpoints[1].zosung_irtransmit

    assert transmit1.ir_msg is not transmit2.ir_msg
    assert transmit1.send_lock is not transmit2.send_lock

    # A learn on the first device must not leak into the second one.
    with mock.patch.object(
        transmit1.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        # receive_ir_frame_00 for seq 1, announcing a four byte message
        hdr, args = transmit1.deserialize(
            bytes.fromhex("016b00") + struct.pack("<HIIHBBH", 1, 4, 0, 0xE004, 1, 4, 0)
        )
        transmit1.handle_message(hdr, args)
        # receive_ir_frame_03 carrying the whole message at position 0
        hdr, args = transmit1.deserialize(
            bytes.fromhex("016c03")
            + struct.pack("<BHI", 0, 1, 0)
            + b"\x04\xde\xad\xbe\xef"
            + struct.pack("<B", 0x38)
        )
        transmit1.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

    assert bytes(transmit1.ir_msg) == b"\xde\xad\xbe\xef"
    assert transmit1.msg_length == 4
    assert transmit2.ir_msg == []
    assert transmit2.msg_length == 0


async def test_ts1201_learn_real_capture(zs06):
    """Test a full learn of a code captured from a physical ZS06."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    control = zs06.endpoints[1].zosung_ircontrol
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    for position in range(0, len(code), DEVICE_PART_LENGTH):
        learned_code_part(
            transmit, position, code[position : position + DEVICE_PART_LENGTH]
        )
    await wait_for_zigpy_tasks()

    commands = sent_commands(zs06.endpoints[1].request, transmit)
    assert commands[0][0] == 0x01
    requested = [args.position for command_id, args in commands if command_id == 0x02]
    assert requested == list(range(0, len(code), DEVICE_PART_LENGTH))
    assert commands[-1][0] == 0x04

    learned_code_done(transmit)
    await wait_for_zigpy_tasks()

    assert zs06.last_learned_ir_code == REAL_LEARNED_IR_CODE
    succ, _ = await control.read_attributes(("last_learned_ir_code",))
    assert succ[0] == REAL_LEARNED_IR_CODE
    # Learning mode is left once the code is in.
    assert sent_commands(zs06.endpoints[1].request, control)[-1][1].data == (
        b'{"study":1}'
    )


@pytest.mark.parametrize(
    ("position", "crc"),
    [
        (0, 0x00),  # corrupted part
        (DEVICE_PART_LENGTH, None),  # part ahead of the one requested
    ],
)
async def test_ts1201_learn_rerequests_bad_part(zs06, position, crc):
    """Test a corrupted or misplaced part is asked for again, not assembled."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    learned_code_part(
        transmit, position, code[position : position + DEVICE_PART_LENGTH], crc=crc
    )
    await wait_for_zigpy_tasks()

    assert transmit.ir_msg == []
    command_id, args = sent_commands(zs06.endpoints[1].request, transmit)[-1]
    assert command_id == 0x02
    assert args.position == 0

    # The retried part is accepted.
    learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH])
    await wait_for_zigpy_tasks()
    assert bytes(transmit.ir_msg) == code[:DEVICE_PART_LENGTH]
    assert transmit.msg_part_retries == 0


async def test_ts1201_learn_rejects_part_past_announced_length(zs06):
    """Test a part running past the announced length is asked for again."""
    transmit = zs06.endpoints[1].zosung_irtransmit

    announce_learned_code(transmit, 4)
    learned_code_part(transmit, 0, b"\x01\x02\x03\x04\x05")
    await wait_for_zigpy_tasks()

    assert transmit.ir_msg == []
    command_id, args = sent_commands(zs06.endpoints[1].request, transmit)[-1]
    assert command_id == 0x02
    assert args.position == 0


async def test_ts1201_learn_gives_up_after_bad_parts(zs06, caplog):
    """Test a learn is abandoned after too many bad parts in a row."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    control = zs06.endpoints[1].zosung_ircontrol
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    for _ in range(zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_RETRIES + 1):
        learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH], crc=0x00)
    await wait_for_zigpy_tasks()

    requests = [
        command_id
        for command_id, _ in sent_commands(zs06.endpoints[1].request, transmit)
        if command_id == 0x02
    ]
    # The initial request plus one per allowed retry, and no more.
    assert len(requests) == 1 + zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_RETRIES
    assert transmit.msg_length == 0
    assert "after 4 bad message parts" in caplog.text
    # The device is taken out of learning mode instead of being left in it.
    assert sent_commands(zs06.endpoints[1].request, control)[-1][1].data == (
        b'{"study":1}'
    )

    # Nothing is learned from the abandoned transfer.
    learned_code_done(transmit)
    await wait_for_zigpy_tasks()
    assert zs06.last_learned_ir_code == ""


async def test_ts1201_learn_discards_incomplete_code(zs06, caplog):
    """Test a learn that ends early does not publish a truncated code."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    control = zs06.endpoints[1].zosung_ircontrol
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH])
    learned_code_done(transmit)
    await wait_for_zigpy_tasks()

    assert zs06.last_learned_ir_code == ""
    assert "55 of 251 bytes received" in caplog.text
    assert transmit.ir_msg == []
    # Learning mode is still left.
    assert sent_commands(zs06.endpoints[1].request, control)[-1][1].data == (
        b'{"study":1}'
    )


async def test_ts1201_learn_gives_up_on_empty_parts(zs06):
    """Test empty parts count as bad, so they can't keep the device learning."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    control = zs06.endpoints[1].zosung_ircontrol
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    for _ in range(zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_RETRIES + 1):
        learned_code_part(transmit, 0, b"")
    await wait_for_zigpy_tasks()

    assert transmit.msg_length == 0
    assert sent_commands(zs06.endpoints[1].request, control)[-1][1].data == (
        b'{"study":1}'
    )


async def test_ts1201_learn_reacknowledges_resent_final_part(zs06):
    """Test a final part resent after a lost 0x04 is acknowledged, not rejected."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    code = base64.b64decode(REAL_LEARNED_IR_CODE)
    positions = list(range(0, len(code), DEVICE_PART_LENGTH))

    announce_learned_code(transmit, len(code))
    for position in positions:
        learned_code_part(
            transmit, position, code[position : position + DEVICE_PART_LENGTH]
        )
    await wait_for_zigpy_tasks()
    requests_before = len(sent_commands(zs06.endpoints[1].request, transmit))

    # The device didn't get our 0x04, so it sends the last part again.
    for _ in range(zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_RETRIES + 1):
        learned_code_part(transmit, positions[-1], code[positions[-1] :])
    await wait_for_zigpy_tasks()

    resent = [
        command_id
        for command_id, _ in sent_commands(zs06.endpoints[1].request, transmit)[
            requests_before:
        ]
    ]
    assert resent == [0x04] * (zhaquirks.tuya.ts1201.IR_MSG_PART_MAX_RETRIES + 1)
    assert transmit.msg_part_retries == 0

    learned_code_done(transmit)
    await wait_for_zigpy_tasks()
    assert zs06.last_learned_ir_code == REAL_LEARNED_IR_CODE


async def test_ts1201_learn_ignores_repeated_part(zs06):
    """Test a part repeating bytes already received is neither re-requested nor bad."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code))
    learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH])
    await wait_for_zigpy_tasks()
    requests = len(sent_commands(zs06.endpoints[1].request, transmit))

    learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH])
    await wait_for_zigpy_tasks()

    assert len(sent_commands(zs06.endpoints[1].request, transmit)) == requests
    assert bytes(transmit.ir_msg) == code[:DEVICE_PART_LENGTH]
    assert transmit.msg_part_retries == 0


async def test_ts1201_learn_ignores_frames_of_another_seq(zs06):
    """Test parts and the end of another learn's seq don't touch this one."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    control = zs06.endpoints[1].zosung_ircontrol
    code = base64.b64decode(REAL_LEARNED_IR_CODE)

    announce_learned_code(transmit, len(code), seq=1)
    await wait_for_zigpy_tasks()
    requests = zs06.endpoints[1].request.await_count

    learned_code_part(transmit, 0, code[:DEVICE_PART_LENGTH], seq=7)
    learned_code_done(transmit, seq=7)
    await wait_for_zigpy_tasks()

    assert transmit.ir_msg == []
    assert transmit.msg_length == len(code)
    assert zs06.endpoints[1].request.await_count == requests
    assert sent_commands(zs06.endpoints[1].request, control) == []


async def test_ts1201_learn_ignores_end_with_nothing_learned(zs06, caplog):
    """Test a 0x05 after the code was stored neither warns nor leaves study again."""
    transmit = zs06.endpoints[1].zosung_irtransmit

    learned_code_done(transmit)
    await wait_for_zigpy_tasks()

    assert "Discarding" not in caplog.text
    assert zs06.endpoints[1].request.await_count == 0


async def test_ts1201_learn_ignores_part_without_announcement(zs06):
    """Test a part arriving when no code is being learned is ignored."""
    transmit = zs06.endpoints[1].zosung_irtransmit

    learned_code_part(transmit, 0, b"\x01\x02\x03\x04")
    await wait_for_zigpy_tasks()

    assert transmit.ir_msg == []
    assert sent_commands(zs06.endpoints[1].request, transmit) == []


async def test_ts1201_send_real_capture(zs06):
    """Test a full send of a code captured from a physical ZS06."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit
    expected = ir_msg(REAL_LEARNED_IR_CODE)

    task = await start_ir_send(control, code=REAL_LEARNED_IR_CODE)

    command_id, args = sent_commands(zs06.endpoints[1].request, transmit)[-1]
    assert command_id == 0x00
    assert args.length == len(expected)
    assert args.clusterid == control.cluster_id
    assert args.cmd == control.ServerCommandDefs.IRSend.id
    seq = args.seq

    assert await pull_ir_msg(transmit, seq, len(expected)) == expected
    assert not task.done()

    confirm_sent(transmit, seq)
    await wait_for_zigpy_tasks()

    rsp = await task
    assert rsp.command_id == control.ServerCommandDefs.IRSend.id
    assert rsp.status == foundation.Status.SUCCESS
    assert transmit.pending_send is None
    command_id, args = sent_commands(zs06.endpoints[1].request, transmit)[-1]
    assert command_id == 0x05
    assert args.seq == seq


async def test_ts1201_sends_one_at_a_time(zs06):
    """Test a send is not announced until the previous one is confirmed."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    first = await start_ir_send(control, code="AAAA")
    second = await start_ir_send(control, code="BBBB")
    announced = [
        args.seq
        for command_id, args in sent_commands(zs06.endpoints[1].request, transmit)
        if command_id == 0x00
    ]
    assert len(announced) == 1
    assert not second.done()

    assert await pull_ir_msg(transmit, announced[0], len(ir_msg("AAAA"))) == ir_msg(
        "AAAA"
    )
    confirm_sent(transmit, announced[0])
    await first
    await asyncio.sleep(0)

    seq = last_announced_seq(transmit)
    assert seq == announced[0] + 1
    assert not second.done()
    assert await pull_ir_msg(transmit, seq, len(ir_msg("BBBB"))) == ir_msg("BBBB")
    confirm_sent(transmit, seq)
    assert (await second).status == foundation.Status.SUCCESS


async def test_ts1201_send_times_out_without_confirmation(zs06, caplog):
    """Test a send the blaster never confirms fails and frees the next one."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    with (
        mock.patch.object(zhaquirks.tuya.ts1201, "IR_SEND_TIMEOUT", 0.01),
        pytest.raises(TimeoutError),
    ):
        await control.command(control.ServerCommandDefs.IRSend.id, code="AAAA")
    stale_seq = last_announced_seq(transmit)
    assert transmit.pending_send is None
    assert f"was not confirmed by {zs06.ieee} (seq: {stale_seq})" in caplog.text

    # A late request for the abandoned message is not answered.
    request_msg_part(transmit, stale_seq, 0)
    await wait_for_zigpy_tasks()
    assert sent_commands(zs06.endpoints[1].request, transmit)[-1][0] == 0x00

    task = await start_ir_send(control, code="BBBB")
    seq = last_announced_seq(transmit)
    assert await pull_ir_msg(transmit, seq, len(ir_msg("BBBB"))) == ir_msg("BBBB")
    confirm_sent(transmit, seq)
    assert (await task).status == foundation.Status.SUCCESS


async def test_ts1201_cancelled_send_still_holds_the_blaster(zs06):
    """Test a caller giving up does not let the next send overlap the transfer."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    first = await start_ir_send(control, code="AAAA")
    first_seq = last_announced_seq(transmit)
    second = await start_ir_send(control, code="BBBB")
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    await asyncio.sleep(0)

    # The blaster is still fetching the first message, so it is served and the
    # second send waits instead of being announced over it.
    assert last_announced_seq(transmit) == first_seq
    assert await pull_ir_msg(transmit, first_seq, len(ir_msg("AAAA"))) == ir_msg("AAAA")
    assert not second.done()

    confirm_sent(transmit, first_seq)
    second_seq = first_seq + 1
    await wait_for_announcement(transmit, second_seq)
    assert await pull_ir_msg(transmit, second_seq, len(ir_msg("BBBB"))) == ir_msg(
        "BBBB"
    )
    confirm_sent(transmit, second_seq)
    assert (await second).status == foundation.Status.SUCCESS


async def test_ts1201_cancelled_queued_send_is_dropped(zs06):
    """Test a send whose caller gives up before its turn is never announced."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    first = await start_ir_send(control, code="AAAA")
    first_seq = last_announced_seq(transmit)
    queued = await start_ir_send(control, code="BBBB")
    queued.cancel()
    with pytest.raises(asyncio.CancelledError):
        await queued

    await pull_ir_msg(transmit, first_seq, len(ir_msg("AAAA")))
    confirm_sent(transmit, first_seq)
    assert (await first).status == foundation.Status.SUCCESS
    await wait_for_zigpy_tasks()

    announced = [
        args.seq
        for command_id, args in sent_commands(zs06.endpoints[1].request, transmit)
        if command_id == 0x00
    ]
    assert announced == [first_seq]
    assert not transmit.send_lock.locked()


async def test_ts1201_slow_final_ack_is_not_a_timeout(zs06):
    """Test a confirmed send succeeds even if the final 0x05 outlasts the window."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit
    ack_sent = asyncio.Event()
    windows = []
    real_timeout = asyncio.timeout

    async def request(*args, **kwargs):
        if kwargs["cluster"] == transmit.cluster_id and kwargs["command_id"] == 0x05:
            await ack_sent.wait()
        return foundation.Status.SUCCESS

    def timeout(delay):
        # The send's window gets no deadline; the test ends it on demand instead.
        window = real_timeout(None)
        windows.append(window)
        return window

    zs06.endpoints[1].request.side_effect = request
    with mock.patch.object(zhaquirks.tuya.ts1201.asyncio, "timeout", timeout):
        task = await start_ir_send(control, code="AAAA")
        seq = last_announced_seq(transmit)
        await pull_ir_msg(transmit, seq, len(ir_msg("AAAA")))
        confirm_sent(transmit, seq)
        await asyncio.sleep(0)

        # The window runs out while the 0x05 is still going out.
        loop = asyncio.get_running_loop()
        for window in windows:
            with contextlib.suppress(RuntimeError):  # already left
                window.reschedule(loop.time())
        await asyncio.sleep(0)
        assert not task.done()
        assert transmit.send_lock.locked()

        ack_sent.set()
        assert (await task).status == foundation.Status.SUCCESS
    assert not transmit.send_lock.locked()


async def test_ts1201_send_closes_the_transfer_before_the_next(zs06):
    """Test the final acknowledgment goes out before the next send is announced."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    async def send_both():
        for code in ("AAAA", "BBBB"):
            await control.command(control.ServerCommandDefs.IRSend.id, code=code)

    both = asyncio.create_task(send_both())
    while not zs06.endpoints[1].request.await_count:
        await asyncio.sleep(0)
    first_seq = last_announced_seq(transmit)
    await pull_ir_msg(transmit, first_seq, len(ir_msg("AAAA")))
    confirm_sent(transmit, first_seq)
    await wait_for_announcement(transmit, first_seq + 1)

    frames = [
        (command_id, args.seq)
        for command_id, args in sent_commands(zs06.endpoints[1].request, transmit)
        if command_id in (0x00, 0x05)
    ]
    assert frames == [(0x00, first_seq), (0x05, first_seq), (0x00, first_seq + 1)]

    second_seq = first_seq + 1
    await pull_ir_msg(transmit, second_seq, len(ir_msg("BBBB")))
    confirm_sent(transmit, second_seq)
    await both


async def test_ts1201_send_fails_when_announcement_fails(zs06):
    """Test a send that cannot be announced fails and frees the next one."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit

    zs06.endpoints[1].request.side_effect = RuntimeError("delivery failed")
    with pytest.raises(RuntimeError):
        await control.command(control.ServerCommandDefs.IRSend.id, code="AAAA")
    assert transmit.pending_send is None
    assert not transmit.send_lock.locked()


async def test_ts1201_send_warns_about_lost_message(zs06, caplog):
    """Test a request for a message that is no longer pending is logged as a loss."""
    transmit = zs06.endpoints[1].zosung_irtransmit

    request_msg_part(transmit, 7, 0)
    await wait_for_zigpy_tasks()

    assert any(
        record.levelname == "WARNING"
        and "no pending message for seq 7" in record.getMessage()
        for record in caplog.records
    )
    assert sent_commands(zs06.endpoints[1].request, transmit) == []


async def test_ts1201_confirms_unknown_sent_seq(zs06):
    """Test a repeated frame 0x04 is confirmed again."""
    transmit = zs06.endpoints[1].zosung_irtransmit

    confirm_sent(transmit, 7)
    await wait_for_zigpy_tasks()

    command_id, args = sent_commands(zs06.endpoints[1].request, transmit)[-1]
    assert command_id == 0x05
    assert args.seq == 7


@pytest.mark.parametrize(
    ("params", "freq", "num"),
    [
        ({}, 38000, 1),
        ({"freq": 37000}, 37000, 1),
        ({"repeats": 2}, 38000, 3),
        ({"freq": 40000, "repeats": 1}, 40000, 2),
    ],
)
async def test_ts1201_send_freq_and_repeats(zs06, params, freq, num):
    """Test the optional carrier frequency and repeat count reach the message."""
    control = zs06.endpoints[1].zosung_ircontrol
    transmit = zs06.endpoints[1].zosung_irtransmit
    expected = ir_msg("AAAA", freq=freq, num=num)

    task = await start_ir_send(control, code="AAAA", **params)

    seq = last_announced_seq(transmit)
    assert await pull_ir_msg(transmit, seq, len(expected)) == expected
    confirm_sent(transmit, seq)
    await task


def test_ts1201_send_freq_and_repeats_are_optional():
    """Test ZHA can issue IRSend with only a code."""
    schema = zhaquirks.tuya.ts1201.ZosungIRControl.ServerCommandDefs.IRSend.schema
    assert [(field.name, field.optional) for field in schema.fields] == [
        ("code", False),
        ("freq", True),
        ("repeats", True),
    ]
    assert schema(code="AAAA").serialize() == schema(code="AAAA").code.serialize()


@pytest.mark.parametrize(
    ("node_desc", "timeout"),
    [
        # The battery TS1201: an end device whose radio is off when idle.
        (
            zdo_t.NodeDescriptor(
                logical_type=zdo_t.LogicalType.EndDevice,
                mac_capability_flags=zdo_t.NodeDescriptor.MACCapabilityFlags(128),
            ),
            zhaquirks.tuya.ts1201.IR_SEND_TIMEOUT_SLEEPY,
        ),
        (None, zhaquirks.tuya.ts1201.IR_SEND_TIMEOUT_SLEEPY),
    ],
)
def test_ts1201_sleepy_blaster_gets_longer_to_confirm(zs06, node_desc, timeout):
    """Test a blaster that only hears us when it polls gets a longer send window."""
    transmit = zs06.endpoints[1].zosung_irtransmit
    assert transmit.send_timeout == zhaquirks.tuya.ts1201.IR_SEND_TIMEOUT

    zs06.node_desc = node_desc
    assert transmit.send_timeout == timeout


@pytest.mark.parametrize("freq", [38, 30000])
async def test_ts1201_send_rejects_carrier_in_khz(zs06, freq):
    """Test a carrier frequency that can't be in Hz is refused, not sent."""
    control = zs06.endpoints[1].zosung_ircontrol

    with pytest.raises(ValueError, match="frequency is in Hz"):
        await control.command(
            control.ServerCommandDefs.IRSend.id, code="AAAA", freq=freq
        )
    assert zs06.endpoints[1].request.await_count == 0


async def test_ts1201_read_last_learned_ir_code(zs06):
    """Test the learned code is served however it is asked for."""
    control = zs06.endpoints[1].zosung_ircontrol
    learned_ir_code = control.AttributeDefs.last_learned_ir_code
    zs06.last_learned_ir_code = REAL_LEARNED_IR_CODE

    for attribute in (learned_ir_code.id, learned_ir_code.name, learned_ir_code):
        assert await control.read_attributes([attribute]) == (
            {learned_ir_code.id: REAL_LEARNED_IR_CODE},
            {},
        )

    assert await control.read_attributes([learned_ir_code.id, 0x1234]) == (
        {learned_ir_code.id: REAL_LEARNED_IR_CODE},
        {0x1234: foundation.Status.UNSUPPORTED_ATTRIBUTE},
    )
    assert zs06.endpoints[1].request.await_count == 0
