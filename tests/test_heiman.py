"""Tests for Heiman custom quirks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from zha.application import Platform
from zha.exceptions import ZHAException
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, DeviceTemperature
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.foundation import DataTypeId, Status, WriteAttributesStatusRecord
from zigpy.zdo.types import LogicalType, NodeDescriptor

from tests.zha_helpers import _patch_cluster, zha_gateway
from zhaquirks.heiman.h1_e import CustomHeimanCluster, HeimanTemperatureMeasurement
import zhaquirks.heiman.hs1rm_e

zhaquirks.setup()

CURRENT_TEMP_ID = DeviceTemperature.AttributeDefs.current_temperature.id
MIN_TEMP_ID = DeviceTemperature.AttributeDefs.min_temp_experienced.id


def test_heiman_hs1rm_e_temperature_scaling(zigpy_device_from_v2_quirk):
    """Test that the Heiman HS1RM-E scales raw device temperatures by 100."""
    device = zigpy_device_from_v2_quirk("HEIMAN", "RelayModule-EF-3.0")
    device_temp_cluster = device.endpoints[1].device_temperature

    # current_temperature is scaled *100 to centidegrees for ZHA's /100 divisor
    device_temp_cluster.update_attribute(CURRENT_TEMP_ID, 25)
    assert device_temp_cluster.get(CURRENT_TEMP_ID) == 2500

    # other attributes pass through unchanged
    device_temp_cluster.update_attribute(MIN_TEMP_ID, 25)
    assert device_temp_cluster.get(MIN_TEMP_ID) == 25

    # a None current_temperature must not raise (no multiplication)
    device_temp_cluster.update_attribute(CURRENT_TEMP_ID, None)
    assert device_temp_cluster.get(CURRENT_TEMP_ID) is None


@pytest.fixture
async def h1_e_display_select(request):
    """Create a display select with a device value that includes other flag bits."""
    async with zha_gateway() as gateway:
        raw = zigpy.device.Device(
            gateway.application_controller,
            t.EUI64.convert("00:11:22:33:44:55:66:77"),
            t.NWK(0x1234),
        )
        raw.manufacturer = "Heiman"
        raw.model = "H1-E"
        raw.last_seen = datetime.now(UTC)
        raw.node_desc = NodeDescriptor(
            logical_type=LogicalType.EndDevice, manufacturer_code=0x120B
        )
        endpoint = raw.add_endpoint(1)
        endpoint.profile_id = zha.PROFILE_ID
        endpoint.device_type = zha.DeviceType.TEMPERATURE_SENSOR
        endpoint.add_input_cluster(Basic.cluster_id)
        endpoint.add_input_cluster(TemperatureMeasurement.cluster_id)
        endpoint.add_input_cluster(CustomHeimanCluster.cluster_id)

        device = DEVICE_REGISTRY.resolve(raw)
        cluster = device.endpoints[1].temperature
        attr = HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode
        values = getattr(request, "param", {attr.id: 7}).copy()
        _patch_cluster(cluster, values)
        _patch_cluster(device.endpoints[1].basic, {})
        _patch_cluster(
            device.endpoints[1].in_clusters[CustomHeimanCluster.cluster_id], {}
        )
        gateway.application_controller.devices[device.ieee] = device
        await gateway.async_device_initialized(device)
        await gateway.async_block_till_done()
        select = gateway.get_device(device.ieee).get_platform_entity(
            Platform.SELECT,
            unique_id=f"{device.ieee}-1-temperature_display_mode",
        )
        cluster._write_attributes = AsyncMock(
            return_value=[[WriteAttributesStatusRecord(Status.SUCCESS)]]
        )
        yield cluster, select, values


@pytest.mark.parametrize("h1_e_display_select", [{}], indirect=True)
async def test_heiman_h1_e_display_created_before_attribute_read(h1_e_display_select):
    """Create the config select even when the display attribute has no cached value."""
    cluster, select, _ = h1_e_display_select
    attr = HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode
    assert cluster.get(attr.name) is None
    assert select.current_option is None
    assert select.force_create is True
    assert select.entity_category == "config"


@pytest.mark.parametrize(
    ("reported_value", "expected_option", "celsius_write", "fahrenheit_write"),
    [
        (0, "Fahrenheit", 1, 0),
        (1, "Celsius", 1, 0),
        (2, "Fahrenheit", 3, 2),
        (6, "Fahrenheit", 7, 6),
        (7, "Celsius", 7, 6),
        (-1, "Celsius", -1, -2),
        (-128, "Fahrenheit", -127, -128),
    ],
)
async def test_heiman_h1_e_temperature_display_mode(
    h1_e_display_select,
    reported_value,
    expected_option,
    celsius_write,
    fahrenheit_write,
):
    """Interpret bit 0 and preserve every other bit using the device's int8 type."""
    cluster, select, values = h1_e_display_select
    attr = HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode
    values[attr.id] = reported_value
    cluster.update_attribute(attr.id, reported_value)
    assert select.current_option == expected_option
    assert cluster.get(attr.name) == reported_value
    cluster.read_attributes_raw.reset_mock()

    for option, value in (("Celsius", celsius_write), ("Fahrenheit", fahrenheit_write)):
        await select.async_select_option(option)
        call = cluster._write_attributes.call_args
        record = call.args[0][0]
        assert record.attrid == attr.id
        assert record.value.type == DataTypeId.int8
        assert record.value.value == value
        assert call.kwargs["manufacturer"] == 0x120B
        assert select.current_option == option
    cluster.read_attributes_raw.assert_not_awaited()


async def test_heiman_h1_e_display_uses_cached_flags(h1_e_display_select):
    """Change bit 0 using the cache without issuing an extra read."""
    cluster, select, values = h1_e_display_select
    attr = HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode
    assert cluster.get(attr.name) == 7
    values[attr.id] = 8
    cluster.read_attributes_raw.reset_mock()

    await select.async_select_option("Fahrenheit")

    record = cluster._write_attributes.call_args.args[0][0]
    assert record.value.value == 6
    assert cluster.get(attr.name) == 6
    cluster.read_attributes_raw.assert_not_awaited()


async def test_heiman_h1_e_display_missing_cache(h1_e_display_select):
    """Do not overwrite unknown flags when the cache has no value."""
    cluster, select, _ = h1_e_display_select
    attr = HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode
    cluster.update_attribute(attr.id, None)
    cluster.read_attributes_raw.reset_mock()

    with pytest.raises(ZHAException, match="not available"):
        await select.async_select_option("Fahrenheit")

    cluster._write_attributes.assert_not_awaited()
    cluster.read_attributes_raw.assert_not_awaited()
