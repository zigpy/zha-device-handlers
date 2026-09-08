"""Tests for Adeo quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.security import IasZone

import zhaquirks.adeo.sensor_ldsenk08


def test_adeo_ldsenk08_v2_replaces_ias_cluster(zigpy_device_from_v2_quirk):
    """Test V2 quirk replaces IAS cluster with custom class."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    assert isinstance(
        device.endpoints[1].ias_zone,
        zhaquirks.adeo.sensor_ldsenk08.IasMultiZoneCluster,
    )


def test_adeo_ldsenk08_cluster_request_updates_zone_status(zigpy_device_from_v2_quirk):
    """Test incoming IAS status updates zone_status attribute."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster.send_default_rsp = mock.MagicMock()
    cluster.update_attribute = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = IasZone.ClientCommandDefs.status_change_notification.id
    header.frame_control = foundation.FrameControl.cluster()

    cluster.handle_cluster_request(header, [0x07])
    cluster.update_attribute.assert_called_with(
        zhaquirks.adeo.sensor_ldsenk08.ZONE_STATUS, 0x07
    )


def test_adeo_ldsenk08_cluster_request_ignores_invalid_payload(
    zigpy_device_from_v2_quirk,
):
    """Test empty payload does not update zone_status."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster.send_default_rsp = mock.MagicMock()
    cluster.update_attribute = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = IasZone.ClientCommandDefs.status_change_notification.id
    header.frame_control = foundation.FrameControl.cluster()

    cluster.handle_cluster_request(header, [])
    cluster.update_attribute.assert_not_called()


def test_adeo_ldsenk08_cluster_request_ignores_invalid_zone_status_type(
    zigpy_device_from_v2_quirk,
):
    """Test invalid zone status type does not update zone_status."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster.send_default_rsp = mock.MagicMock()
    cluster.update_attribute = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = IasZone.ClientCommandDefs.status_change_notification.id
    header.frame_control = foundation.FrameControl.cluster()

    cluster.handle_cluster_request(header, [object()])
    cluster.update_attribute.assert_not_called()


def test_adeo_ldsenk08_cluster_request_ignores_unknown_command(
    zigpy_device_from_v2_quirk,
):
    """Test unknown command id does not update zone_status."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster.send_default_rsp = mock.MagicMock()
    cluster.update_attribute = mock.MagicMock()

    header = foundation.ZCLHeader()
    header.command_id = 0x99
    header.frame_control = foundation.FrameControl.cluster()

    cluster.handle_cluster_request(header, [0x03])
    cluster.update_attribute.assert_not_called()


def test_adeo_ldsenk08_exposes_standard_sensitivity_attribute(
    zigpy_device_from_v2_quirk,
):
    """Test IAS sensitivity attribute is available on endpoint 1."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    assert IasZone.AttributeDefs.current_zone_sensitivity_level.id in cluster.attributes


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("low", 0),
        ("medium", 1),
        ("high", 2),
        (0, 0),
        (4, 4),
    ],
)
def test_adeo_ldsenk08_sensitivity_normalization(value, expected):
    """Test sensitivity normalization supports labels and numeric range."""
    assert (
        zhaquirks.adeo.sensor_ldsenk08.IasMultiZoneCluster._normalize_sensitivity(value)
        == expected
    )


@pytest.mark.parametrize("value", ["ultra", -1, 5])
def test_adeo_ldsenk08_sensitivity_normalization_invalid(value):
    """Test invalid sensitivity values are rejected."""
    with pytest.raises(ValueError):
        zhaquirks.adeo.sensor_ldsenk08.IasMultiZoneCluster._normalize_sensitivity(value)


@pytest.mark.asyncio
async def test_adeo_ldsenk08_write_attributes_normalizes_sensitivity_by_name(
    zigpy_device_from_v2_quirk,
):
    """Test writing sensitivity by attribute name normalizes string values."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as patched_super:
        result = await cluster.write_attributes(
            {IasZone.AttributeDefs.current_zone_sensitivity_level.name: "high"}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    patched_super.assert_awaited_once_with(
        {IasZone.AttributeDefs.current_zone_sensitivity_level.name: 2},
        manufacturer=None,
    )


@pytest.mark.asyncio
async def test_adeo_ldsenk08_write_attributes_normalizes_sensitivity_by_id(
    zigpy_device_from_v2_quirk,
):
    """Test writing sensitivity by attribute id keeps normalized numeric values."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    sensitivity_id = IasZone.AttributeDefs.current_zone_sensitivity_level.id

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as patched_super:
        result = await cluster.write_attributes({sensitivity_id: 4})

    assert result[0][0].status == foundation.Status.SUCCESS
    patched_super.assert_awaited_once_with({sensitivity_id: 4}, manufacturer=None)


@pytest.mark.asyncio
async def test_adeo_ldsenk08_write_attributes_passthrough_non_sensitivity(
    zigpy_device_from_v2_quirk,
):
    """Test non-sensitivity attributes are forwarded without normalization."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    zone_status_id = IasZone.AttributeDefs.zone_status.id

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[[mock.sentinel.ok]]),
    ) as patched_super:
        result = await cluster.write_attributes({zone_status_id: 1})

    assert result == [[mock.sentinel.ok]]
    patched_super.assert_awaited_once_with({zone_status_id: 1}, manufacturer=None)


@pytest.mark.asyncio
async def test_adeo_ldsenk08_write_attributes_queues_sensitivity_on_failure(
    zigpy_device_from_v2_quirk,
):
    """Test failed sensitivity writes are queued and acknowledged."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(side_effect=TimeoutError),
    ) as patched_super:
        result = await cluster.write_attributes(
            {IasZone.AttributeDefs.current_zone_sensitivity_level.name: "high"}
        )

    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._pending_sensitivity_level == 2
    patched_super.assert_awaited_once_with(
        {IasZone.AttributeDefs.current_zone_sensitivity_level.name: 2},
        manufacturer=None,
    )


@pytest.mark.asyncio
async def test_adeo_ldsenk08_apply_pending_sensitivity_on_wake(
    zigpy_device_from_v2_quirk,
):
    """Test pending sensitivity is retried when an IAS command is received."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster._pending_sensitivity_level = 3
    cluster.send_default_rsp = mock.MagicMock()
    cluster.create_catching_task = mock.MagicMock(side_effect=lambda coro: coro.close())

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as patched_super:
        header = foundation.ZCLHeader()
        header.command_id = IasZone.ClientCommandDefs.status_change_notification.id
        header.frame_control = foundation.FrameControl.cluster()
        cluster.handle_cluster_request(header, [0x01])
        await cluster._apply_pending_sensitivity()

    cluster.create_catching_task.assert_called_once()
    patched_super.assert_awaited_with(
        {IasZone.AttributeDefs.current_zone_sensitivity_level.id: 3}
    )
    assert cluster._pending_sensitivity_level is None
