"""Tests for Adeo quirks."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.exceptions import DeliveryError
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.security import IasZone

import zhaquirks.adeo.sensor_ldsenk08
from zhaquirks.builder.device import QuirkV2Factory

SENSITIVITY_ID = IasZone.AttributeDefs.current_zone_sensitivity_level.id


def _status_result(status: foundation.Status):
    """Build a write attributes response with a single status record."""
    return [[foundation.WriteAttributesStatusRecord(status, SENSITIVITY_ID)]]


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


@pytest.mark.parametrize(
    ("unique_id_suffix", "zone_status_bit"),
    [
        ("contact", IasZone.ZoneStatus.Alarm_1),
        ("vibration", IasZone.ZoneStatus.Alarm_2),
        ("tamper", IasZone.ZoneStatus.Tamper),
    ],
)
def test_adeo_ldsenk08_zone_status_binary_sensors(unique_id_suffix, zone_status_bit):
    """Test each binary sensor only reflects its own zone_status bit."""
    (definition,) = {
        entry.zha_device_factory.quirk_definition
        for entry in DEVICE_REGISTRY
        if isinstance(entry.zha_device_factory, QuirkV2Factory)
        and str(entry.source.file).endswith("sensor_ldsenk08.py")
    }
    (entity,) = (
        em
        for em in definition.entity_metadata
        if em.unique_id_suffix == unique_id_suffix
    )
    all_bits = (
        IasZone.ZoneStatus.Alarm_1
        | IasZone.ZoneStatus.Alarm_2
        | IasZone.ZoneStatus.Tamper
        | IasZone.ZoneStatus.Battery
    )

    assert entity.attribute_converter(zone_status_bit) is True
    assert entity.attribute_converter(all_bits & ~zone_status_bit) is False


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
        (0, 0),
        (4, 4),
        ("3", 3),
    ],
)
def test_adeo_ldsenk08_sensitivity_normalization(value, expected):
    """Test sensitivity normalization accepts the numeric 0..4 range."""
    assert (
        zhaquirks.adeo.sensor_ldsenk08.IasMultiZoneCluster._normalize_sensitivity(value)
        == expected
    )


@pytest.mark.parametrize("value", ["high", -1, 5])
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
        "zhaquirks.clusters.CustomCluster.write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as patched_super:
        result = await cluster.write_attributes(
            {IasZone.AttributeDefs.current_zone_sensitivity_level.name: "2"}
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
        "zhaquirks.clusters.CustomCluster.write_attributes",
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
        "zhaquirks.clusters.CustomCluster.write_attributes",
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
        "zhaquirks.clusters.CustomCluster.write_attributes",
        new=mock.AsyncMock(side_effect=TimeoutError),
    ) as patched_super:
        result = await cluster.write_attributes(
            {IasZone.AttributeDefs.current_zone_sensitivity_level.name: "2"}
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
        "zhaquirks.clusters.CustomCluster.write_attributes",
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


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [TimeoutError, DeliveryError("not delivered")])
async def test_adeo_ldsenk08_write_attributes_queues_on_retryable_exception(
    zigpy_device_from_v2_quirk, exception
):
    """Test transient delivery errors queue the sensitivity write."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    with mock.patch(
        "zhaquirks.clusters.CustomCluster.write_attributes",
        new=mock.AsyncMock(side_effect=exception),
    ):
        result = await cluster.write_attributes({SENSITIVITY_ID: 1})

    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._pending_sensitivity_level == 1
    assert cluster.get(SENSITIVITY_ID) == 1


@pytest.mark.asyncio
async def test_adeo_ldsenk08_write_attributes_raises_unexpected_exception(
    zigpy_device_from_v2_quirk,
):
    """Test non-transient errors are not masked as queued writes."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    with (
        mock.patch(
            "zhaquirks.clusters.CustomCluster.write_attributes",
            new=mock.AsyncMock(side_effect=RuntimeError),
        ),
        pytest.raises(RuntimeError),
    ):
        await cluster.write_attributes({SENSITIVITY_ID: 1})

    assert cluster._pending_sensitivity_level is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [foundation.Status.FAILURE, foundation.Status.UNSUPPORTED_ATTRIBUTE]
)
async def test_adeo_ldsenk08_write_attributes_returns_device_status(
    zigpy_device_from_v2_quirk, status
):
    """Test status records returned by the awake device are not queued."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    failure = _status_result(status)

    with mock.patch(
        "zhaquirks.clusters.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=failure),
    ):
        result = await cluster.write_attributes({SENSITIVITY_ID: 3})

    assert result == failure
    assert cluster._pending_sensitivity_level is None
    assert cluster.get(SENSITIVITY_ID) is None


def test_adeo_ldsenk08_notification_burst_schedules_single_retry(
    zigpy_device_from_v2_quirk,
):
    """Test only one pending sensitivity retry runs at a time."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster._pending_sensitivity_level = 3
    cluster.send_default_rsp = mock.MagicMock()
    cluster.create_catching_task = mock.MagicMock(side_effect=lambda coro: coro.close())

    header = foundation.ZCLHeader()
    header.command_id = IasZone.ClientCommandDefs.status_change_notification.id
    header.frame_control = foundation.FrameControl.cluster()
    for _ in range(3):
        cluster.handle_cluster_request(header, [0x01])

    cluster.create_catching_task.assert_called_once()


@pytest.mark.asyncio
async def test_adeo_ldsenk08_apply_pending_sensitivity_device_status(
    zigpy_device_from_v2_quirk,
):
    """Test any status returned by the awake device clears the pending write."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster._pending_sensitivity_level = 3
    cluster._sensitivity_retry_in_flight = True

    with mock.patch(
        "zhaquirks.clusters.CustomCluster.write_attributes",
        new=mock.AsyncMock(
            return_value=_status_result(foundation.Status.UNSUPPORTED_ATTRIBUTE)
        ),
    ):
        await cluster._apply_pending_sensitivity()

    assert cluster._pending_sensitivity_level is None
    assert cluster._sensitivity_retry_in_flight is False


@pytest.mark.asyncio
async def test_adeo_ldsenk08_apply_pending_sensitivity_still_asleep(
    zigpy_device_from_v2_quirk,
):
    """Test a retry that is not delivered keeps the write queued."""
    device = zigpy_device_from_v2_quirk(
        "ADEO",
        "LDSENK08",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone
    cluster._pending_sensitivity_level = 3
    cluster._sensitivity_retry_in_flight = True

    with (
        mock.patch(
            "zhaquirks.clusters.CustomCluster.write_attributes",
            new=mock.AsyncMock(side_effect=TimeoutError),
        ),
        pytest.raises(TimeoutError),
    ):
        await cluster._apply_pending_sensitivity()

    assert cluster._pending_sensitivity_level == 3
    assert cluster._sensitivity_retry_in_flight is False
