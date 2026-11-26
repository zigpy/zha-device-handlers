"""Tests for the Tuya TS0601 metering breaker."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

import zhaquirks
import zhaquirks.tuya.ts0601_metering_breaker  # noqa: F401

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr_name,value",
    [
        (b"\x09\x6d\x02\x00\xf2\x14\x02\x00\x04\x00\x00\x09\x5f", "voltage", 2399),
        (b"\x09\x02\x02\x00\x02\x12\x02\x00\x04\x00\x00\x00\x1b", "current", 27),
        (b"\x09\x01\x02\x00\x01\x13\x02\x00\x04\x00\x00\x01\x8b", "power", 395),
        (b"\x09\x03\x02\x00\x03\x2f\x02\x00\x04\x00\x00\x00\x27", "temperature", 39),
    ],
)
async def test_metering_breaker_datapoints(
    zigpy_device_from_v2_quirk, msg, attr_name, value
):
    """Test measurement datapoints update the matching attribute."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_5m4nchbm", "TS0601")
    tuya_cluster = quirked.endpoints[1].tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(msg)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get(attr_name) == value


@pytest.mark.parametrize(
    "msg,expected",
    [
        (b"\x09\x04\x02\x00\x04\x01\x01\x00\x01\x01", True),
        (b"\x09\x05\x02\x00\x05\x01\x01\x00\x01\x00", False),
    ],
)
async def test_metering_breaker_on_off(zigpy_device_from_v2_quirk, msg, expected):
    """Test the relay state datapoint updates the on/off cluster."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_5m4nchbm", "TS0601")
    ep = quirked.endpoints[1]

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    assert ep.tuya_manufacturer.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert bool(ep.on_off.get("on_off")) is expected


async def test_metering_breaker_scaling(zigpy_device_from_v2_quirk):
    """Test the scaling confirmed against the breaker's display."""

    quirked = zigpy_device_from_v2_quirk("_TZE284_5m4nchbm", "TS0601")
    entry = DEVICE_REGISTRY.match_entry(quirked)
    divisors = {
        metadata.resolved_unique_id_suffix: metadata.divisor
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
        if hasattr(metadata, "divisor")
    }

    assert divisors["voltage"] == 10
    assert divisors["current"] == 100
    assert divisors["power"] == 10
