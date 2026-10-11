"""Tests for Niko socket quirks."""

from unittest import mock

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import ZCLAttributeAccess

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder import EntityType
from zhaquirks.builder.metadata import SwitchMetadata, ZCLEnumMetadata
from zhaquirks.niko import NIKO_MFG_CODE
from zhaquirks.niko.outlet import LedOffColor, NikoOutletConfigCluster

zhaquirks.setup()

OUTLET = ("NIKO NV", "Connected socket outlet")
OFF_COLOR = NikoOutletConfigCluster.AttributeDefs.led_off_color.name


def quirk_definition(device):
    """Return the v2 quirk definition that was applied to a device."""
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    return entry.zha_device_factory.quirk_definition


def test_outlet_friendly_name(zigpy_device_from_v2_quirk):
    """Test that the outlet is shown with the Niko branding."""
    friendly_name = quirk_definition(zigpy_device_from_v2_quirk(*OUTLET)).friendly_name

    assert friendly_name.manufacturer == "Niko"
    assert friendly_name.model == "Connected socket outlet (170-33505/170-34605)"


@pytest.mark.parametrize(
    ("manufacturer", "model", "friendly_model"),
    [
        (
            "Niko NV",
            "Smart plug Zigbee SE",
            "Smart plug with side earthing pin (552-80698)",
        ),
        (
            "Niko NV",
            "Smart plug Zigbee PE",
            "Smart plug with earthing pin (552-80699)",
        ),
        (
            "NIKO NV",
            "Smart plug Zigbee PE",
            "Smart plug with earthing pin (552-80699)",
        ),
    ],
)
def test_plug_friendly_names(
    zigpy_device_from_v2_quirk, manufacturer, model, friendly_model
):
    """Test that both plug variants are shown with the Niko branding."""
    device = zigpy_device_from_v2_quirk(manufacturer, model)
    friendly_name = quirk_definition(device).friendly_name

    assert friendly_name.manufacturer == "Niko"
    assert friendly_name.model == friendly_model


def test_config_cluster(zigpy_device_from_v2_quirk):
    """Test the attributes of the outlet configuration cluster."""
    device = zigpy_device_from_v2_quirk(*OUTLET)
    cluster = device.endpoints[1].niko_config

    assert cluster.cluster_id == 0xFC00
    assert {
        attr.id: (attr.name, attr.access, attr.manufacturer_code)
        for attr in cluster.AttributeDefs
    } == {
        0x0100: (
            "led_off_color",
            ZCLAttributeAccess.from_str("rw"),
            NIKO_MFG_CODE,
        ),
        0x0101: ("child_lock", ZCLAttributeAccess.from_str("rw"), NIKO_MFG_CODE),
        0x0104: ("led_enable", ZCLAttributeAccess.from_str("rw"), NIKO_MFG_CODE),
    }


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
async def test_bind_fresh_pairing(zigpy_device_from_v2_quirk):
    """Test that the off color default is written, not read, when nothing is cached."""
    device = zigpy_device_from_v2_quirk(*OUTLET)
    cluster = device.endpoints[1].niko_config

    with (
        mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read,
        mock.patch.object(cluster, "write_attributes", mock.AsyncMock()) as write,
    ):
        await cluster.bind()
        await wait_for_zigpy_tasks()

    write.assert_awaited_once_with({OFF_COLOR: LedOffColor.Off})
    read.assert_awaited_once_with(["child_lock", "led_enable"])


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
async def test_bind_keeps_cached_off_color(zigpy_device_from_v2_quirk):
    """Test that a cached off color is neither overwritten nor read again."""
    device = zigpy_device_from_v2_quirk(*OUTLET)
    cluster = device.endpoints[1].niko_config
    cluster.update_attribute(
        NikoOutletConfigCluster.AttributeDefs.led_off_color.id, LedOffColor.Blue
    )

    with (
        mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read,
        mock.patch.object(cluster, "write_attributes", mock.AsyncMock()) as write,
    ):
        await cluster.bind()
        await wait_for_zigpy_tasks()

    write.assert_not_awaited()
    read.assert_awaited_once_with(["child_lock", "led_enable"])


def test_outlet_entities(zigpy_device_from_v2_quirk):
    """Test the configuration entities and the disabled voltage and current."""
    definition = quirk_definition(zigpy_device_from_v2_quirk(*OUTLET))
    cluster_id = NikoOutletConfigCluster.cluster_id

    entities = {em.attribute_name: em for em in definition.entity_metadata}
    assert set(entities) == {"child_lock", "led_enable", "led_off_color"}

    child_lock = entities["child_lock"]
    assert isinstance(child_lock, SwitchMetadata)
    assert child_lock.cluster_id == cluster_id
    assert child_lock.entity_type == EntityType.CONFIG
    # the attribute is 0 when the child lock is on
    assert child_lock.on_value == 0
    assert child_lock.off_value == 1

    led_enable = entities["led_enable"]
    assert isinstance(led_enable, SwitchMetadata)
    assert led_enable.entity_type == EntityType.CONFIG
    assert led_enable.on_value == 1
    assert led_enable.off_value == 0

    off_color = entities["led_off_color"]
    assert isinstance(off_color, ZCLEnumMetadata)
    assert off_color.enum is LedOffColor
    assert off_color.entity_type == EntityType.CONFIG
    assert not off_color.initially_disabled

    disabled = {
        meta.unique_id_suffix
        for meta in definition.changed_entity_metadata
        if meta.cluster_id == ElectricalMeasurement.cluster_id
        and meta.new_entity_registry_enabled_default is False
    }
    assert disabled == {"rms_voltage", "rms_current"}
