"""Tests for the Tuya pool sensor."""

import asyncio
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from zha.application.platforms.button import Button
from zha.application.platforms.number import NumberConfigurationEntity
from zha.application.platforms.select import ZCLEnumSelectEntity
from zigpy.zcl import ClusterType

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder.metadata import ZCLCommandButtonMetadata, ZCLEnumMetadata
from zhaquirks.tuya import (
    TUYA_QUERY_DATA,
    TUYA_SET_DATA,
    TuyaCommand,
    TuyaDatapointData,
    TuyaDPType,
    TuyaNewManufCluster,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.ts0601_pool_sensor import (
    DP_CALIBRATION_KEEP_AWAKE,
    DP_EC_CALIBRATION,
    DP_ORP_CALIBRATION,
    DP_PH_CALIBRATION,
    PHCalibrationStandard,
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
    pool_sensor = device.endpoints[1].in_clusters[TuyaMCUCluster.cluster_id]
    yield pool_sensor
    pool_sensor.handle_auto_update_timers_cancel()
    await asyncio.sleep(0)


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
    ph_sensor = next(
        metadata
        for metadata in entity_metadata
        if getattr(metadata, "attribute_name", None) == "ph_measured_value"
    )
    assert ph_sensor.divisor == 10


@pytest.mark.parametrize("divisor", [10, 100])
async def test_ph_limit_formats(pool_sensor, divisor):
    """Both wire formats display and write the same pH limit values."""
    pool_sensor.handle_get_data(
        TuyaCommand(
            status=0,
            tsn=1,
            datapoints=[
                TuyaDatapointData(106, 14 * divisor),
                TuyaDatapointData(107, 7 * divisor),
            ],
        )
    )
    number = Mock(
        _cluster=pool_sensor,
        _attribute_name="ph_min_value",
        _multiplier=0.1,
    )
    assert pool_sensor.get("ph_max_value") == 140
    assert NumberConfigurationEntity.native_value.fget(number) == 7
    assert pool_sensor.get_cached_value("ph_max_value") == 14 * divisor

    pool_sensor.command = AsyncMock()
    await NumberConfigurationEntity.async_set_native_value(number, 7.5)
    await wait_for_zigpy_tasks()

    command_id, command_data = pool_sensor.command.await_args.args
    assert command_id == TUYA_SET_DATA
    assert command_data.datapoints[0].dp == 107
    assert command_data.datapoints[0].data.payload == 7.5 * divisor
    assert NumberConfigurationEntity.native_value.fget(number) == 7.5


async def test_ph_limit_format_remembered(pool_sensor):
    """Hundredths remain selected after both raw limits fall below 140."""
    pool_sensor.update_attribute("ph_max_value", 1400)
    assert pool_sensor.get("ph_max_value") == 140
    pool_sensor.update_attribute("ph_max_value", 100)
    pool_sensor.update_attribute("ph_min_value", 50)

    # Restore only persisted attributes into a fresh cluster, like appdb does.
    restored = type(pool_sensor)(pool_sensor.endpoint)
    try:
        for name in (*pool_sensor.PH_LIMIT_ATTRIBUTES, "ph_limit_divisor"):
            attr = restored.attributes_by_name[name]
            restored._attr_cache.set_value(attr, pool_sensor.get_cached_value(name))
        assert restored.get("ph_max_value") == 10
        assert restored.get("ph_min_value") == 5
        restored.command = AsyncMock()
        await restored.write_attributes(
            {restored.attributes_by_name["ph_max_value"].id: 12}
        )
        await wait_for_zigpy_tasks()
        assert restored.command.await_args.args[1].datapoints[0].data.payload == 120
    finally:
        restored.handle_auto_update_timers_cancel()


@pytest.mark.parametrize("raw", [None, -1, 0xFFFFFFFF])
async def test_ph_limit_unset(pool_sensor, raw):
    """Unset limits do not select a format or expose invalid pH values."""
    pool_sensor.update_attribute("ph_max_value", raw)
    assert pool_sensor.get("ph_max_value") is None
    assert pool_sensor._get_ph_limit_divisor() == 10
    assert pool_sensor.get("unknown_attribute", 123) == 123


@pytest.mark.parametrize(
    ("option", "value"),
    [("Asia (4.00, 6.86, 9.18)", 0), ("Europe (4.00, 7.00, 10.00)", 1)],
)
async def test_ph_buffer_options(pool_sensor, option, value):
    """Buffer labels round-trip through the ZHA selector as Tuya enums."""
    pool_sensor.command = AsyncMock()
    selector = Mock(
        _cluster=pool_sensor,
        _attribute_name="ph_calibration_standard",
        _enum=PHCalibrationStandard,
    )
    await ZCLEnumSelectEntity.async_select_option(selector, option)
    await wait_for_zigpy_tasks()

    datapoint = pool_sensor.command.await_args.args[1].datapoints[0]
    assert datapoint.dp == 103
    assert datapoint.data.dp_type == TuyaDPType.ENUM
    assert datapoint.data.raw == bytes([value])
    assert ZCLEnumSelectEntity.current_option.fget(selector) == option


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


@pytest.mark.parametrize(
    "method_name", ["calibrate_ph", "calibrate_ec", "calibrate_orp"]
)
async def test_calibration_button_press(pool_sensor, method_name):
    """Calibration command buttons invoke the local cluster coroutine."""
    method = AsyncMock()
    setattr(pool_sensor, method_name, method)
    button = Mock(
        _cluster=pool_sensor,
        _command_name=method_name,
        args=[],
        kwargs={},
    )

    await Button.async_press(button)

    method.assert_awaited_once_with()


@pytest.mark.parametrize(
    "error", [RuntimeError("write failed"), asyncio.CancelledError()]
)
async def test_calibration_clears_failed_value_write(pool_sensor, error):
    """A failed or cancelled value write still attempts to clear the data point."""
    pool_sensor._update_attribute(
        pool_sensor.attributes_by_name["ph_measured_value"].id, 58
    )
    pool_sensor._write_dp_value = AsyncMock(side_effect=[None, error, None])
    pool_sensor.command = AsyncMock()

    with (
        patch(
            "zhaquirks.tuya.ts0601_pool_sensor.asyncio.sleep", new=AsyncMock()
        ) as sleep,
        pytest.raises(type(error)),
    ):
        await pool_sensor.calibrate_ph()

    assert pool_sensor._write_dp_value.await_args_list == [
        call(DP_CALIBRATION_KEEP_AWAKE, 1),
        call(DP_PH_CALIBRATION, 58),
        call(DP_PH_CALIBRATION, 0),
    ]
    sleep.assert_awaited_once_with(6)
    pool_sensor.command.assert_not_awaited()


async def test_auto_refresh(pool_sensor):
    """Automatic refresh sends a Tuya data query."""
    pool_sensor.command = AsyncMock()

    await pool_sensor.handle_auto_update()

    pool_sensor.command.assert_awaited_once_with(TUYA_QUERY_DATA)
    assert isinstance(pool_sensor, TuyaPoolManufCluster)
    assert pool_sensor.cluster_id == TuyaNewManufCluster.cluster_id


async def test_auto_refresh_interval_change(pool_sensor):
    """A changed refresh interval cancels and replaces the device task."""
    pool_sensor._update_attribute(
        pool_sensor.attributes_by_name["auto_refresh_interval"].id, 5
    )
    previous_timer = Mock()
    pool_sensor._update_timer_handle = previous_timer
    delay = Mock()
    pool_sensor._handle_auto_update_delay = Mock(return_value=delay)
    pool_sensor.endpoint.device.create_task = Mock()
    pool_sensor.debug = Mock()

    pool_sensor.handle_auto_update_setup_next_call()

    previous_timer.cancel.assert_called_once_with()
    assert pool_sensor.next_refresh_interval == 300
    pool_sensor.debug.assert_called_once_with("using refresh interval of %d minutes", 5)
    pool_sensor._handle_auto_update_delay.assert_called_once_with(300)
    pool_sensor.endpoint.device.create_task.assert_called_once_with(delay)
    assert (
        pool_sensor._update_timer_handle
        is pool_sensor.endpoint.device.create_task.return_value
    )


async def test_auto_refresh_timer_wrapper(pool_sensor):
    """The timer wrapper starts a refresh and schedules the next one."""
    refresh_task = Mock()
    pool_sensor.handle_auto_update = Mock(return_value=refresh_task)
    pool_sensor.create_catching_task = Mock()
    pool_sensor.handle_auto_update_setup_next_call = Mock()

    pool_sensor.handle_auto_update_timer_wrapper()

    pool_sensor.create_catching_task.assert_called_once_with(refresh_task)
    pool_sensor.handle_auto_update_setup_next_call.assert_called_once_with(
        force_new_interval=True
    )


async def test_auto_refresh_delay(pool_sensor):
    """The refresh task waits before invoking its timer wrapper."""
    pool_sensor.handle_auto_update_timer_wrapper = Mock()

    with patch(
        "zhaquirks.tuya.ts0601_pool_sensor.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await pool_sensor._handle_auto_update_delay(300)

    sleep.assert_awaited_once_with(300)
    pool_sensor.handle_auto_update_timer_wrapper.assert_called_once_with()


async def test_auto_refresh_check_delay(pool_sensor):
    """The interval-check task waits before checking again."""
    pool_sensor.handle_auto_update_check_change = Mock()

    with patch(
        "zhaquirks.tuya.ts0601_pool_sensor.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await pool_sensor._handle_auto_update_check_delay()

    sleep.assert_awaited_once_with(60)
    pool_sensor.handle_auto_update_check_change.assert_called_once_with()


async def test_auto_refresh_timers_cancel_on_device_removal(pool_sensor):
    """Device removal cancels refresh tasks created through the public API."""
    check_timer = pool_sensor._check_timer_handle
    pool_sensor._update_attribute(
        pool_sensor.attributes_by_name["auto_refresh_interval"].id, 5
    )
    pool_sensor.handle_auto_update_setup_next_call(force_new_interval=True)
    update_timer = pool_sensor._update_timer_handle

    pool_sensor.endpoint.device.on_remove()
    await asyncio.sleep(0)

    assert check_timer.cancelled()
    assert update_timer.cancelled()
