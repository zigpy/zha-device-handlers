"""Tests for the Tuya TS1201 / Zosung IR blaster."""

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


@pytest.mark.parametrize("test_bytes", (b"\x00\x01\x02\x03\x04",))
def test_ts1201_ir_blaster_bytes(test_bytes):
    """Test quirk Byte helper class."""
    a, b = zhaquirks.tuya.ts1201.Bytes.deserialize(data=test_bytes)
    assert a == test_bytes
    assert b == b""


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
        assert fail[0] == foundation.Status.UNSUPPORTED_ATTRIBUTE

        # IR send tests
        await ts1201_control_cluster.command(0x0002, code=ir_code_to_send)
        await wait_for_zigpy_tasks()
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

        # test raw data command
        rsp = await ts1201_control_cluster.command(
            0x0000, zhaquirks.tuya.ts1201.Bytes(b"\x00\x01\x02\x03\x04")
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


async def test_ts1201_ir_send_bounded_and_guarded(zigpy_device_from_quirk):
    """Test TS1201 bounds the pending IR-message dict and guards unknown seqs.

    Regression test for https://github.com/zigpy/zha-device-handlers/issues/4641.
    """
    quirk = zhaquirks.tuya.ts1201.ZosungIRBlaster
    ir_code_to_send = "B3wPfA/5AcoH4AUDAeUDgAPAC+AHB+AHA+ADN+ALBw=="  # codespell:ignore

    dev = zigpy_device_from_quirk(quirk)
    control_cluster = dev.endpoints[1].zosung_ircontrol
    transmit_cluster = dev.endpoints[1].zosung_irtransmit

    # ir_msg_to_send is initialised per instance, not shared at class level.
    assert dev.ir_msg_to_send == {}

    with mock.patch.object(
        control_cluster.endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
    ):
        # Many consecutive sends must not grow the pending dict without bound.
        for _ in range(12):
            await control_cluster.command(
                zhaquirks.tuya.ts1201.ZosungIRControl.ServerCommandDefs.IRSend.id,
                code=ir_code_to_send,
            )
        await wait_for_zigpy_tasks()
        assert len(dev.ir_msg_to_send) <= 8

        # An ACK frame for a sequence with no pending message must be ignored,
        # not raise KeyError (previously crashed on sleepy devices).
        dev.ir_msg_to_send.clear()
        # receive_ir_frame_02 frame for seq 1 (b"g" + position + maxlen).
        hdr, args = transmit_cluster.deserialize(bytes.fromhex("11670201000000000040"))
        transmit_cluster.handle_message(hdr, args)
        await wait_for_zigpy_tasks()


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
    assert dev1.ir_msg_to_send is not dev2.ir_msg_to_send

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
