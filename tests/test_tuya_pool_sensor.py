"""Tests for the Tuya pool sensor."""

from unittest.mock import AsyncMock, call, patch

import pytest
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.builder.metadata import ZCLCommandButtonMetadata, ZCLEnumMetadata
from zhaquirks.tuya import TUYA_QUERY_DATA, TUYA_SET_DATA, TuyaNewManufCluster
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_pool_sensor import (
    DP_CALIBRATION_KEEP_AWAKE,
    DP_EC_CALIBRATION,
    DP_ORP_CALIBRATION,
    DP_PH_CALIBRATION,
    TuyaPoolManufCluster,
)

zhaquirks.setup()


@pytest.fixture
async def pool_sensor(zigpy_device_from_v2_quirk):
    """Create a quirked pool sensor."""
    device = zigpy_device_from_v2_quirk(
        "_TZE200_v1jqz5cy",
        "TS0601",
        cluster_ids={1: {TuyaMCUCluster.cluster_id: ClusterType.Server}},
    )
    return device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]


def test_pool_sensor_entities(device_mock):
    """Verify that calibration controls are exposed by the quirk."""
    device_mock.manufacturer = "_TZE200_v1jqz5cy"
    device_mock.model = "TS0601"

    entry = zhaquirks.ZHA_DEVICE_REGISTRY.match_entry(device_mock)
    assert entry is not None

    entity_metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    commands = {
        metadata.command_name
        for metadata in entity_metadata
        if isinstance(metadata, ZCLCommandButtonMetadata)
    }
    enums = {
        metadata.attribute_name
        for metadata in entity_metadata
        if isinstance(metadata, ZCLEnumMetadata)
    }

    assert commands == {"query_data", "calibrate_ph", "calibrate_ec", "calibrate_orp"}
    assert enums == {"ph_calibration_standard"}


async def test_calibration_payload(pool_sensor):
    """Calibration writes use the raw four-byte Tuya value payload."""
    pool_sensor.command = AsyncMock()

    await pool_sensor._write_dp_value(DP_PH_CALIBRATION, 58)

    command_id, command_data = pool_sensor.command.await_args.args
    assert command_id == TUYA_SET_DATA
    assert command_data.datapoints[0].dp == DP_PH_CALIBRATION
    assert command_data.datapoints[0].data.raw == b"\x00\x00\x00\x3a"
    assert pool_sensor.command.await_args.kwargs == {"expect_reply": True}


@pytest.mark.parametrize(
    ("method_name", "attribute_name", "calibration_dp", "raw_value"),
    [
        ("calibrate_ph", "ph_measured_value", DP_PH_CALIBRATION, 58),
        ("calibrate_ec", "ec_measured_value", DP_EC_CALIBRATION, 1413),
        ("calibrate_orp", "redox_potential", DP_ORP_CALIBRATION, 222),
    ],
)
async def test_calibration_sequence(
    pool_sensor, method_name, attribute_name, calibration_dp, raw_value
):
    """Calibration refreshes, writes the reading, clears, and queries."""
    pool_sensor._update_attribute(
        pool_sensor.attributes_by_name[attribute_name].id, raw_value
    )
    pool_sensor._write_dp_value = AsyncMock()
    pool_sensor.command = AsyncMock()

    with patch(
        "zhaquirks.tuya.ts0601_pool_sensor.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await getattr(pool_sensor, method_name)()

    assert pool_sensor._write_dp_value.await_args_list == [
        call(DP_CALIBRATION_KEEP_AWAKE, 1),
        call(calibration_dp, raw_value),
        call(calibration_dp, 0),
    ]
    assert sleep.await_args_list == [call(6), call(3)]
    pool_sensor.command.assert_awaited_once_with(TUYA_QUERY_DATA)


async def test_calibration_without_measurement(pool_sensor):
    """A missing measurement must not start calibration."""
    pool_sensor._write_dp_value = AsyncMock()
    pool_sensor.command = AsyncMock()

    with (
        patch("zhaquirks.tuya.ts0601_pool_sensor.asyncio.sleep", new=AsyncMock()),
        pytest.raises(ValueError, match="No pH measurement"),
    ):
        await pool_sensor.calibrate_ph()

    pool_sensor._write_dp_value.assert_awaited_once_with(DP_CALIBRATION_KEEP_AWAKE, 1)
    pool_sensor.command.assert_not_awaited()


async def test_auto_refresh(pool_sensor):
    """Automatic refresh sends a Tuya data query."""
    pool_sensor.command = AsyncMock()

    await pool_sensor.handle_auto_update()

    pool_sensor.command.assert_awaited_once_with(TUYA_QUERY_DATA)
    assert isinstance(pool_sensor, TuyaPoolManufCluster)
    assert pool_sensor.cluster_id == TuyaNewManufCluster.cluster_id
