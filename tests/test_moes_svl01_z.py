"""Tests for the MOES SVL01-Z quirk."""

from unittest import mock

import pytest

from zhaquirks.tuya.moes_svl01_z import (
    TUYA_QUERY_DATA,
    PresenceSwitchCluster,
)


@pytest.mark.asyncio
async def test_moes_svl01_z_delayed_query_data(device_mock):
    """Test that the cluster requests current DP values after initialization."""
    endpoint = device_mock.endpoints[1]

    with mock.patch.object(PresenceSwitchCluster, "create_catching_task"):
        cluster = PresenceSwitchCluster(endpoint)

    endpoint.in_clusters[cluster.cluster_id] = cluster

    with (
        mock.patch(
            "zhaquirks.tuya.moes_svl01_z.asyncio.sleep",
            new_callable=mock.AsyncMock,
        ) as sleep_mock,
        mock.patch.object(
            cluster,
            "command",
            new_callable=mock.AsyncMock,
        ) as command_mock,
    ):
        await cluster._delayed_query_data()

    sleep_mock.assert_awaited_once_with(2)
    command_mock.assert_awaited_once_with(TUYA_QUERY_DATA)


@pytest.mark.asyncio
async def test_moes_svl01_z_delayed_query_data_stale_cluster(device_mock):
    """Test that a stale cluster does not request current DP values."""
    endpoint = device_mock.endpoints[1]

    with mock.patch.object(PresenceSwitchCluster, "create_catching_task"):
        cluster = PresenceSwitchCluster(endpoint)

    endpoint.in_clusters[cluster.cluster_id] = mock.Mock()

    with (
        mock.patch(
            "zhaquirks.tuya.moes_svl01_z.asyncio.sleep",
            new_callable=mock.AsyncMock,
        ),
        mock.patch.object(
            cluster,
            "command",
            new_callable=mock.AsyncMock,
        ) as command_mock,
    ):
        await cluster._delayed_query_data()

    command_mock.assert_not_awaited()
