"""Tests for inovelli blue series manufacturer cluster."""

import struct
from unittest import mock
from unittest.mock import MagicMock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import ClusterType

from tests.common import ButtonEventRecorder, send_command
import zhaquirks
from zhaquirks.builder.metadata import ButtonEventMetadata
from zhaquirks.inovelli import InovelliCluster, InovelliVZM32SNMMWaveCluster
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


INOVELLI_MANUFACTURER_CODE = 0x122F

# Inovelli button index -> button event entity unique_id suffix
INOVELLI_BUTTON_ENTITIES = {
    1: "button_down",
    2: "button_up",
    3: "button_config",
    4: "button_aux_down",
    5: "button_aux_up",
    6: "button_aux_config",
}

INOVELLI_BUTTON_EVENT_TYPES = [
    "single_press",
    "multi_press",
    "long_press_start",
    "long_press_end",
    "press_end",
]


def _set_switch_endpoint(device, endpoint_id: int) -> None:
    """Give a test endpoint the profile and device type of the real one."""
    device.endpoints[endpoint_id].profile_id = zha.PROFILE_ID
    device.endpoints[endpoint_id].device_type = zha.DeviceType.DIMMER_SWITCH


def _inovelli_button_device(zigpy_device_from_v2_quirk, model: str):
    """Create a quirked Inovelli switch with its button endpoint 2."""
    device = zigpy_device_from_v2_quirk(
        "Inovelli",
        model,
        cluster_ids={2: {InovelliCluster.cluster_id: ClusterType.Client}},
    )
    _set_switch_endpoint(device, 2)
    return device


def _send_button_event(device, button: int, press_type: int, endpoint_id=2) -> None:
    """Receive a button event (scene) frame from an endpoint of the device."""
    send_command(
        device,
        endpoint_id,
        InovelliCluster.cluster_id,
        "button_event",
        button_pressed=button,
        press_type=press_type,
        manufacturer=INOVELLI_MANUFACTURER_CODE,
    )


@pytest.mark.parametrize("model", ["VZM30-SN", "VZM31-SN", "VZM32-SN", "VZM35-SN"])
async def test_button_events(zigpy_device_from_v2_quirk, model):
    """Test the button event entities of the Inovelli switches."""
    device = _inovelli_button_device(zigpy_device_from_v2_quirk, model)
    recorder = await ButtonEventRecorder.create(device)

    assert recorder.event_types() == dict.fromkeys(
        INOVELLI_BUTTON_ENTITIES.values(), INOVELLI_BUTTON_EVENT_TYPES
    )
    for suffix, entity in recorder.entities.items():
        assert entity.endpoint.id == 2
        # aux switch buttons only report their own events with unique aux scenes
        assert entity.entity_registry_enabled_default is (
            not suffix.startswith("button_aux_")
        )

    for button, suffix in INOVELLI_BUTTON_ENTITIES.items():
        # pressed 1x, 2x .. 5x: the device resolves the number of taps
        for press_type in (0, 3, 4, 5, 6):
            _send_button_event(device, button, press_type)
        # held, then released
        _send_button_event(device, button, 2)
        _send_button_event(device, button, 1)
        # released outside a hold
        _send_button_event(device, button, 1)

        assert recorder.pop() == [
            (suffix, "single_press"),
            (suffix, "multi_press", {"press_count": 2}),
            (suffix, "multi_press", {"press_count": 3}),
            (suffix, "multi_press", {"press_count": 4}),
            (suffix, "multi_press", {"press_count": 5}),
            (suffix, "long_press_start"),
            (suffix, "long_press_end"),
            (suffix, "press_end"),
        ]


async def test_button_events_release_while_held(zigpy_device_from_v2_quirk):
    """Test that a release only ends a hold of the same button."""
    device = _inovelli_button_device(zigpy_device_from_v2_quirk, "VZM31-SN")
    recorder = await ButtonEventRecorder.create(device)

    # a release without a hold ends a short press
    _send_button_event(device, 2, 1)
    assert recorder.pop() == [("button_up", "press_end")]

    # a release of another button does not end the hold
    _send_button_event(device, 2, 2)
    _send_button_event(device, 1, 1)
    _send_button_event(device, 2, 1)
    assert recorder.pop() == [
        ("button_up", "long_press_start"),
        ("button_down", "press_end"),
        ("button_up", "long_press_end"),
    ]

    # a second release after the hold ended is not the end of a hold
    _send_button_event(device, 2, 1)
    assert recorder.pop() == [("button_up", "press_end")]


@pytest.mark.parametrize("model", ["VZM30-SN", "VZM35-SN"])
async def test_button_events_other_endpoint(zigpy_device_from_v2_quirk, model):
    """Test that button events from endpoint 3 fire no button events."""
    device = zigpy_device_from_v2_quirk(
        "Inovelli",
        model,
        cluster_ids={
            2: {InovelliCluster.cluster_id: ClusterType.Client},
            3: {InovelliCluster.cluster_id: ClusterType.Client},
        },
    )
    _set_switch_endpoint(device, 2)
    _set_switch_endpoint(device, 3)
    recorder = await ButtonEventRecorder.create(device)
    assert set(recorder.entities) == set(INOVELLI_BUTTON_ENTITIES.values())

    for button in INOVELLI_BUTTON_ENTITIES:
        for press_type in (0, 3, 4, 5, 6, 2, 1):
            _send_button_event(device, button, press_type, endpoint_id=3)
    assert recorder.pop() == []

    # the same frame from endpoint 2 does fire
    _send_button_event(device, 2, 0)
    assert recorder.pop() == [("button_up", "single_press")]


async def test_vzm35_button_cluster_added_by_quirk(zigpy_device_from_v2_quirk):
    """Test the VZM35-SN button entities when the quirk adds the button cluster.

    Devices paired with an old firmware lack the 0xFC31 client cluster on
    endpoint 2 in the zigpy database, so the quirk adds it.
    """
    device = zigpy_device_from_v2_quirk("Inovelli", "VZM35-SN", endpoint_ids=[1, 2])
    _set_switch_endpoint(device, 2)
    assert InovelliCluster.cluster_id in device.endpoints[2].out_clusters

    recorder = await ButtonEventRecorder.create(device)
    assert set(recorder.entities) == set(INOVELLI_BUTTON_ENTITIES.values())

    _send_button_event(device, 2, 0)
    assert recorder.pop() == [("button_up", "single_press")]


async def test_button_events_unrelated(zigpy_device_from_v2_quirk):
    """Test that LED effect notifications fire no button events."""
    device = _inovelli_button_device(zigpy_device_from_v2_quirk, "VZM31-SN")
    recorder = await ButtonEventRecorder.create(device)

    send_command(
        device,
        2,
        InovelliCluster.cluster_id,
        "led_effect_complete",
        notification_type=16,
        manufacturer=INOVELLI_MANUFACTURER_CODE,
    )
    send_command(
        device,
        2,
        InovelliCluster.cluster_id,
        "led_effect_complete",
        notification_type=255,
        manufacturer=INOVELLI_MANUFACTURER_CODE,
    )
    assert recorder.pop() == []


async def test_vzm36_no_button_events(zigpy_device_from_v2_quirk):
    """Test that the VZM36 canopy module, without buttons, has no button events."""
    entries = [
        entry
        for entry in DEVICE_REGISTRY
        if entry.source.module == "zhaquirks.inovelli.VZM36"
    ]
    assert entries
    for entry in entries:
        definition = entry.zha_device_factory.quirk_definition
        assert definition.entity_metadata
        assert not any(
            isinstance(entity_metadata, ButtonEventMetadata)
            for entity_metadata in definition.entity_metadata
        )

    device = zigpy_device_from_v2_quirk("Inovelli", "VZM36", endpoint_ids=[1, 2])
    recorder = await ButtonEventRecorder.create(device)
    assert recorder.event_types() == {}
