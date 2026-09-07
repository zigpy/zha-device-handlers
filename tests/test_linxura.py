"""Tests for Linxura quirks."""

from unittest import mock

import pytest
from zha.application import discovery  # noqa: F401 -- load platforms before Device
from zha.application.helpers import CoordinatorConfiguration, ZHAConfiguration, ZHAData
from zha.application.platforms.sensor import Battery
from zha.quirks import DEVICE_REGISTRY, QUIRK_REGISTRY_ENTRY_ATTR
from zha.zigbee.device import Device as ZHADevice
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import AttributeUpdatedEvent, ClusterType
from zigpy.zcl.clusters.general import Basic, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

import zhaquirks
import zhaquirks.linxura
from zhaquirks.linxura.aura import LinxuraAuraIASCluster
from zhaquirks.linxura.button import LinxuraButton, LinxuraIASCluster

zhaquirks.setup()


async def test_button_ias(zigpy_device_from_quirk):
    """Test Linxura button remotes."""

    device = zigpy_device_from_quirk(zhaquirks.linxura.button.LinxuraButton)
    ias_zone_status_attr_id = IasZone.AttributeDefs.zone_status.id
    cluster = device.endpoints[1].ias_zone

    attribute_event_listener = mock.Mock()
    cluster.on_event(AttributeUpdatedEvent.event_type, attribute_event_listener)
    zha_listener = mock.MagicMock()
    cluster.add_listener(zha_listener)

    for i in range(0, 24):
        # button press
        cluster.update_attribute(ias_zone_status_attr_id, i)

        # update_attribute on the IasZone cluster is always called
        event = attribute_event_listener.mock_calls[-1].args[0]
        assert event.attribute_id == ias_zone_status_attr_id
        assert event.value == i

    # we get 24 attribute updates
    assert len(attribute_event_listener.mock_calls) == 24
    # we get 20 events, 4 are discarded as invalid (0, 6, 12, 18)
    assert zha_listener.zha_send_event.call_count == 20


@pytest.mark.parametrize(
    "message, button, press_type",
    [
        (
            b"\x18\n\n\x02\x00\x19\x01\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x03\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x05\x00\xfe\xff0\x01",
            "button_1",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x07\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x09\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0b\x00\xfe\xff0\x01",
            "button_2",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0d\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x0f\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x11\x00\xfe\xff0\x01",
            "button_3",
            "remote_button_long_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x13\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_short_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x15\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_double_press",
        ),
        (
            b"\x18\n\n\x02\x00\x19\x17\x00\xfe\xff0\x01",
            "button_4",
            "remote_button_long_press",
        ),
    ],
)
async def test_button_triggers(zigpy_device_from_quirk, message, button, press_type):
    """Test ZHA_SEND_EVENT case."""
    device = zigpy_device_from_quirk(zhaquirks.linxura.button.LinxuraButton)
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(message),
        )
    )
    assert listener.zha_send_event.call_count == 1
    assert listener.zha_send_event.call_args == mock.call(
        f"{button}_{press_type}",
        {
            "button": button,
            "press_type": press_type,
        },
    )


@pytest.fixture(params=["Smart Controller", "Aura Smart Button"])
def linxura_device(request, zigpy_device_from_quirk, zigpy_device_from_v2_quirk):
    """Resolve both Linxura models through the device registry."""
    if request.param == "Smart Controller":
        raw = zigpy_device_from_quirk(LinxuraButton, apply_quirk=False)
        return DEVICE_REGISTRY.resolve(raw), 4

    device = zigpy_device_from_v2_quirk(
        "Linxura",
        "Aura Smart Button",
        cluster_ids={
            1: {
                Basic.cluster_id: ClusterType.Server,
                PowerConfiguration.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )
    return device, 12


async def test_linxura_model_registration(linxura_device):
    """Keep the models' clusters and automation triggers separate."""
    device, button_count = linxura_device
    expected_cluster = (
        LinxuraAuraIASCluster if button_count == 12 else LinxuraIASCluster
    )
    assert type(device.endpoints[1].ias_zone) is expected_cluster
    assert len(device.device_automation_triggers) == button_count * 3
    assert set(device.device_automation_triggers) == {
        (press_type, f"button_{button}")
        for button in range(1, button_count + 1)
        for press_type in (
            "remote_button_short_press",
            "remote_button_double_press",
            "remote_button_long_press",
        )
    }
    expected_clusters = {Basic.cluster_id, IasZone.cluster_id}
    if button_count == 12:
        expected_clusters.add(PowerConfiguration.cluster_id)
        assert type(device.endpoints[1].power) is PowerConfiguration
    assert set(device.endpoints[1].in_clusters) == expected_clusters
    assert not device.endpoints[1].out_clusters


@pytest.mark.parametrize(
    "press_code, press_type",
    [
        (1, "remote_button_short_press"),
        (2, "remote_button_double_press"),
        (3, "remote_button_double_press"),
        (4, "remote_button_long_press"),
        (5, "remote_button_long_press"),
    ],
)
async def test_linxura_reports_and_triggers(linxura_device, press_code, press_type):
    """Decode every valid code and repeated reports into exactly one event each."""
    device, button_count = linxura_device
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    for button in range(1, button_count + 1):
        # Attribute report format from the original Linxura packet fixtures.
        value = (button - 1) * 6 + press_code
        for sequence in range(2):
            message = bytes([0x18, sequence, 0x0A, 0x02, 0x00, 0x19]) + value.to_bytes(
                2, "little"
            )
            listener.reset_mock()
            device.packet_received(
                t.ZigbeePacket(
                    profile_id=zha.PROFILE_ID,
                    cluster_id=IasZone.cluster_id,
                    src_ep=1,
                    dst_ep=1,
                    data=t.SerializableBytes(message),
                )
            )
            command = f"button_{button}_{press_type}"
            listener.zha_send_event.assert_called_once_with(
                command, {"button": f"button_{button}", "press_type": press_type}
            )
            assert device.device_automation_triggers[
                (press_type, f"button_{button}")
            ] == {
                "command": command,
                "cluster_id": IasZone.cluster_id,
            }


async def test_linxura_invalid_codes(linxura_device):
    """Discard separator codes and codes outside each model's button range."""
    device, button_count = linxura_device
    cluster = device.endpoints[1].ias_zone
    listener = mock.MagicMock()
    cluster.add_listener(listener)
    for value in [
        -1,
        *range(0, button_count * 6, 6),
        *range(button_count * 6, 73),
        65535,
    ]:
        cluster.update_attribute(IasZone.AttributeDefs.zone_status.id, value)
    cluster.update_attribute(IasZone.AttributeDefs.zone_type.id, 1)
    listener.zha_send_event.assert_not_called()


async def test_aura_battery_report(zigpy_device_from_v2_quirk):
    """Preserve the standard battery percentage report without button events."""
    device = zigpy_device_from_v2_quirk(
        "Linxura",
        "Aura Smart Button",
        cluster_ids={1: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )
    listener = mock.MagicMock()
    device.endpoints[1].ias_zone.add_listener(listener)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zha.PROFILE_ID,
            cluster_id=PowerConfiguration.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(b"\x18\x01\x0a\x21\x00\x20\x96"),
        )
    )
    assert device.endpoints[1].power.get("battery_percentage_remaining") == 150
    listener.zha_send_event.assert_not_called()


async def test_linxura_zha_entities(linxura_device):
    """Discover the standard battery sensor only for Aura and retain ZHA triggers."""
    device, button_count = linxura_device
    device.node_desc = device.node_desc.replace(logical_type=2, mac_capability_flags=0)
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.IAS_ZONE
    gateway = mock.MagicMock()
    gateway.config = ZHAData(
        config=ZHAConfiguration(
            coordinator_configuration=CoordinatorConfiguration(path="/dev/ttyUSB0")
        )
    )
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    factory = entry.zha_device_factory or ZHADevice
    zha_device = factory(device, gateway)
    batteries = [
        entity
        for entity in zha_device.discover_entities()
        if isinstance(entity, Battery)
    ]
    assert len(batteries) == (1 if button_count == 12 else 0)
    for trigger, definition in device.device_automation_triggers.items():
        assert zha_device.device_automation_triggers[trigger] == definition
    if batteries:
        battery = batteries[0]
        assert battery.is_supported()
        device.endpoints[1].power.update_attribute(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 150
        )
        assert battery.state["state"] == 75
        device.endpoints[1].power.update_attribute(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 100
        )
        assert battery.state["state"] == 50
