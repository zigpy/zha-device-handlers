"""Tests for the Tuya TS1201 / Zosung IR blaster."""

import asyncio
import base64
import struct
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
import zhaquirks.tuya.ts1201

zhaquirks.setup()

# Learned by a physical ZS06 from a washlet remote ("wash and dry"). At 251 bytes it
# spans five message parts, and its base64 form is longer than 255 characters.
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
