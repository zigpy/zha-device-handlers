"""Tests for Tuya Pool Sensor."""

# These tests specifically cover the refresh logic.

from unittest.mock import Mock

import pytest

import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()


@pytest.fixture
def mock_device():
    """Mock a TuyaMCUCluster device and endpoint."""
    tuya_cluster = Mock()
    tuya_cluster.cluster_id = TuyaMCUCluster.cluster_id
    tuya_cluster.attributes_by_name = {"auto_refresh_interval": None}
    tuya_cluster.get = Mock(return_value=5)

    endpoint = Mock()
    endpoint.in_clusters = {TuyaMCUCluster.cluster_id: tuya_cluster}

    device = Mock()
    device.endpoints = {1: endpoint}

    endpoint.device = device

    return device


@pytest.fixture
def mock_loop():
    """Mock asyncio loop."""
    loop = Mock()
    loop.call_later = Mock()
    return loop


@pytest.mark.parametrize(
    "model,manuf",
    [
        ("_TZE200_v1jqz5cy", "TS0601"),
    ],
)
@pytest.mark.parametrize(
    "cluster", (zhaquirks.tuya.ts0601_pool_sensor.TuyaPoolManufCluster,)
)
async def test_pool_sensor_initialization(
    zigpy_device_from_v2_quirk, model, manuf, cluster
):
    """Tests pool sensor quirk exists."""

    device = zigpy_device_from_v2_quirk(model, manuf)
    tuya_cluster = device.endpoints[1].in_clusters.get(cluster.cluster_id)
    assert tuya_cluster is not None
