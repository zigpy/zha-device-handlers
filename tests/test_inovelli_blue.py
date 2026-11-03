"""Tests for inovelli blue series manufacturer cluster."""

import struct
from unittest import mock
from unittest.mock import MagicMock

import zigpy.types as t
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.inovelli import InovelliVZM32SNMMWaveCluster
from zhaquirks.inovelli.types import MMWaveArea, MMWaveTarget

zhaquirks.setup()


def test_mfg_cluster_events(zigpy_device_from_v2_quirk):
    """Test Inovelli manufacturer cluster generates correct events."""
    data = b"\x15/\x12\x05\x00\x03\x00"  # button_3_press event
    cluster_id = 0xFC31
    endpoint_id = 2

    class Listener:
        zha_send_event = mock.MagicMock()

    device = zigpy_device_from_v2_quirk(
        "Inovelli", "VZM31-SN", cluster_ids={2: {0xFC31: ClusterType.Client}}
    )
    device._packet_debouncer.filter = MagicMock(return_value=False)
    cluster_listener = Listener()
    device.endpoints[endpoint_id].out_clusters[cluster_id].add_listener(
        cluster_listener
    )

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(data),
        )
    )

    assert cluster_listener.zha_send_event.call_count == 1
    assert cluster_listener.zha_send_event.call_args == mock.call(
        "button_3_press", {"button": "button_3", "press_type": "press", "command_id": 0}
    )

    cluster_listener.zha_send_event.reset_mock()

    led_effect_complete_data = b"\x15/\x12\x0c$\x10"
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster_id,
            src_ep=endpoint_id,
            dst_ep=endpoint_id,
            data=t.SerializableBytes(led_effect_complete_data),
        )
    )

    assert cluster_listener.zha_send_event.call_count == 1
    assert cluster_listener.zha_send_event.call_args == mock.call(
        "led_effect_complete_ALL_LEDS",
        {"notification_type": "ALL_LEDS", "command_id": 36},
    )


def test_vzm32_mmwave_set_stay_area_roundtrip():
    """set_stay_area (server command 0x03) serializes bounds as little-endian int16s."""
    set_stay = InovelliVZM32SNMMWaveCluster.ServerCommandDefs.set_stay_area.with_compiled_schema().schema
    payload = set_stay(
        area_id=1,
        x_min=-18,
        x_max=600,
        y_min=0,
        y_max=425,
        z_min=-116,
        z_max=135,
    )
    raw = payload.serialize()
    # area_id(1) | x_min(-18=EEFF) | x_max(600=5802) | y_min(0=0000)
    # | y_max(425=A901) | z_min(-116=8CFF) | z_max(135=8700)
    assert raw == bytes.fromhex("01eeff58020000a9018cff8700")

    parsed, rest = set_stay.deserialize(raw)
    assert rest == b""
    assert parsed.area_id == 1
    assert parsed.x_min == -18
    assert parsed.x_max == 600
    assert parsed.z_max == 135


def test_vzm32_mmwave_report_stay_area_roundtrip():
    """report_stay_area (client command 0x04) decodes count + 4 MMWaveArea structs."""
    report_stay = InovelliVZM32SNMMWaveCluster.ClientCommandDefs.report_stay_area.with_compiled_schema().schema
    empty = MMWaveArea(x_min=0, x_max=0, y_min=0, y_max=0, z_min=0, z_max=0)
    a1 = MMWaveArea(x_min=-18, x_max=600, y_min=0, y_max=425, z_min=-116, z_max=135)
    a2 = MMWaveArea(x_min=-300, x_max=300, y_min=-100, y_max=500, z_min=-50, z_max=250)
    instance = report_stay(count=2, area_1=a1, area_2=a2, area_3=empty, area_4=empty)
    raw = instance.serialize()
    # 1 byte count + 4 areas * 12 bytes each
    assert len(raw) == 1 + 4 * 12

    parsed, rest = report_stay.deserialize(raw)
    assert rest == b""
    assert parsed.count == 2
    assert parsed.area_1.x_min == -18 and parsed.area_1.x_max == 600
    assert parsed.area_2.y_max == 500
    assert parsed.area_3 == empty
    assert parsed.area_4 == empty


def test_vzm32_mmwave_report_target_info_variable_length():
    """report_target_info (client 0x01) reads a list of 9-byte target structs."""
    report_target = InovelliVZM32SNMMWaveCluster.ClientCommandDefs.report_target_info.with_compiled_schema().schema
    instance = report_target(
        target_num=2,
        targets=[
            MMWaveTarget(x=100, y=200, z=-50, dop=5, target_id=1),
            MMWaveTarget(x=-100, y=300, z=0, dop=-3, target_id=2),
        ],
    )
    raw = instance.serialize()
    # 1 byte target_num + 2 targets * 9 bytes (x/y/z/dop int16 + id int8,
    # matching Z2M's stride for this report)
    assert len(raw) == 1 + 2 * 9
    assert raw == bytes([2]) + struct.pack("<hhhhb", 100, 200, -50, 5, 1) + struct.pack(
        "<hhhhb", -100, 300, 0, -3, 2
    )

    parsed, rest = report_target.deserialize(raw)
    assert rest == b""
    assert parsed.target_num == 2
    assert len(parsed.targets) == 2
    assert parsed.targets[0].x == 100
    assert parsed.targets[1].target_id == 2


def test_vzm32_mmwave_anyone_in_reporting_area():
    """anyone_in_reporting_area (client 0x00) carries 4 per-area occupancy bytes."""
    anyone = InovelliVZM32SNMMWaveCluster.ClientCommandDefs.anyone_in_reporting_area.with_compiled_schema().schema
    instance = anyone(area_1=1, area_2=0, area_3=1, area_4=0)
    raw = instance.serialize()
    assert raw == bytes([1, 0, 1, 0])

    parsed, rest = anyone.deserialize(raw)
    assert rest == b""
    assert parsed.area_1 == 1 and parsed.area_2 == 0
    assert parsed.area_3 == 1 and parsed.area_4 == 0
