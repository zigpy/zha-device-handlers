"""Tests for Tuya Pool Sensor."""

# These tests specifically cover the refresh logic.

from unittest.mock import AsyncMock, Mock, patch

import pytest

import zhaquirks
from zhaquirks.tuya import TUYA_QUERY_DATA
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_pool_sensor import TuyaPoolManufCluster

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


@patch("asyncio.get_running_loop")
def test_tuya_pool_manuf_cluster_init(mock_get_loop, mock_loop, mock_device):
    """Test initialization of TuyaPoolManufCluster."""
    # Patch the asyncio loop
    mock_get_loop.return_value = mock_loop

    cluster = TuyaPoolManufCluster(endpoint=mock_device.endpoints[1])

    # Verify attributes are initialized correctly
    assert cluster._update_timer_handle is not None, (
        "Timer handle should have been set via next_call"
    )
    assert cluster.check_interval == 60, "Default check_interval should be 60 seconds"
    assert cluster.next_refresh_interval == 5 * 60, (
        "Default next_refresh_interval should be 5*60"
    )
    assert cluster._loop is mock_loop, "Asyncio loop should be set correctly"

    # Verify that handle_auto_update_check_change is called
    mock_loop.call_later.assert_any_call(60, cluster.handle_auto_update_check_change)


@patch("asyncio.get_running_loop")
def test_handle_auto_update_cancel(mock_get_loop, mock_device, mock_loop):
    """Test canceling an auto-update timer."""

    mock_get_loop.return_value = mock_loop
    cluster = TuyaPoolManufCluster(endpoint=mock_device.endpoints[1])

    # Simulate an active timer
    mock_timer = Mock()
    cluster._update_timer_handle = mock_timer

    cluster.handle_auto_update_cancel()

    # Verify the timer was canceled
    mock_timer.cancel.assert_called_once()
    assert cluster._update_timer_handle is None, "Timer handle should be reset to None"


@patch("asyncio.get_running_loop")
async def test_handle_auto_update(mock_get_loop, mock_device, mock_loop):
    """Test the async auto-update logic."""

    mock_get_loop.return_value = mock_loop
    cluster = TuyaPoolManufCluster(endpoint=mock_device.endpoints[1])

    # Mock TuyaMCUCluster's command method
    tuya_cluster = mock_device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
    tuya_cluster.command = AsyncMock()

    await cluster.handle_auto_update()

    # Verify the TUYA_QUERY_DATA command was sent
    tuya_cluster.command.assert_called_once_with(TUYA_QUERY_DATA)


@patch("asyncio.get_running_loop")
def test_handle_auto_update_setup_next_call(mock_get_loop, mock_device, mock_loop):
    """Test setting up the next auto-update call."""

    mock_get_loop.return_value = mock_loop
    cluster = TuyaPoolManufCluster(endpoint=mock_device.endpoints[1])

    # Invoke the method to test
    cluster.handle_auto_update_setup_next_call(force_new_interval=True)

    # Verify the next call is scheduled correctly
    mock_loop.call_later.assert_called_with(
        5 * 60, cluster.handle_auto_update_timer_wrapper
    )


@patch("asyncio.get_running_loop")
def test_handle_auto_update_timer_wrapper(mock_get_loop, mock_loop, mock_device):
    """Test handle_auto_update_timer_wrapper behavior."""

    mock_get_loop.return_value = mock_loop
    cluster = TuyaPoolManufCluster(endpoint=mock_device.endpoints[1])

    cluster.create_catching_task = Mock()
    cluster.handle_auto_update = Mock(return_value=Mock())
    cluster.handle_auto_update_setup_next_call = Mock()

    # Call the method under test
    cluster.handle_auto_update_timer_wrapper()

    cluster.create_catching_task.assert_called_once_with(cluster.handle_auto_update())
    cluster.handle_auto_update_setup_next_call.assert_called_once_with(
        force_new_interval=True
    )
    cluster.create_catching_task.assert_called_once()
    cluster.handle_auto_update_setup_next_call.assert_called_once()
