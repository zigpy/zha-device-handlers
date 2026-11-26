"""Tests for the SmartPad signature filter and raw attribute write guard."""

from unittest.mock import AsyncMock, patch

import pytest
from zigpy.device import Device
from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_smartpad import is_smartpad_ts0601

zhaquirks.setup()


@pytest.mark.parametrize(
    "endpoint_present,mcu_present,expected",
    [(False, False, False), (True, False, False), (True, True, True)],
)
def test_is_smartpad_ts0601(
    MockAppController, ieee_mock, endpoint_present, mcu_present, expected
):
    """Require the MCU input cluster specifically on endpoint 1."""
    device = Device(MockAppController, ieee_mock, 0x1234)
    if endpoint_present:
        endpoint = device.add_endpoint(1)
        if mcu_present:
            endpoint.add_input_cluster(TuyaMCUCluster.cluster_id)
    assert is_smartpad_ts0601(device) is expected


@pytest.fixture
def cluster(zigpy_device_from_v2_quirk):
    """Create a cluster with the SmartPad attribute definitions for guard tests."""
    device = zigpy_device_from_v2_quirk(
        "_TZE28C1000000_zpvusbtv",
        "TS0601",
        cluster_ids={1: {TuyaMCUCluster.cluster_id: ClusterType.Server}},
    )
    return device.endpoints[1].tuya_manufacturer


@pytest.fixture
def parent_write():
    """Isolate our guard from the framework's already tested datapoint codec."""
    with patch.object(
        TuyaMCUCluster, "write_attributes", new_callable=AsyncMock
    ) as write:
        yield write


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("relay_1", 2),
        ("relay_1", 255),
        ("relay_2", 2),
        ("relay_2", 255),
        ("led_brightness", 101),
        ("led_brightness", 255),
        ("led_mode", 0),
        ("led_enable", 2),
        ("led_on_color", 9),
        ("led_off_color", 255),
    ],
)
async def test_unverified_or_invalid_writes_blocked(
    cluster, parent_write, attribute, value
):
    """Reject raw writes outside the confirmed ranges and all LED-mode writes."""
    result = await cluster.write_attributes({attribute: value})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    parent_write.assert_not_awaited()


@pytest.mark.parametrize(
    "invalid", [{"led_mode": 0}, {"relay_2": 2}, {"led_brightness": 101}]
)
async def test_mixed_write_rejected_before_any_dp_is_sent(
    cluster, parent_write, invalid
):
    """Validate the whole request before forwarding even its valid entries."""
    result = await cluster.write_attributes({"relay_1": 1, **invalid})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    parent_write.assert_not_awaited()


async def test_numeric_attribute_ids_do_not_bypass_write_guard(cluster, parent_write):
    """Apply brightness validation to numeric attribute addressing too."""
    result = await cluster.write_attributes({0xEF66: 101})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    parent_write.assert_not_awaited()


async def test_valid_write_passes_through_guard(cluster, parent_write):
    """Forward a valid mixed request unchanged, including keyword arguments."""
    attributes = {
        "relay_1": 0,
        "relay_2": 1,
        "led_brightness": 100,
        "led_on_color": 0,
        "led_off_color": 8,
        "led_enable": 1,
    }
    result = await cluster.write_attributes(attributes, manufacturer=4417)
    assert result is parent_write.return_value
    parent_write.assert_awaited_once_with(attributes, manufacturer=4417)
