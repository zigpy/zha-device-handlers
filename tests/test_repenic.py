"""Tests for the Repenic RD-250ZG dimmer quirk."""

import asyncio
from datetime import timedelta
from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff, Time

import zhaquirks
from zhaquirks.const import (
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_TRIPLE,
    VALUE,
)
from zhaquirks.repenic.rd250zg import (
    Hour,
    Minute,
    OnOffState,
    PressType,
    RepenicLevelControl,
    RepenicOnOff,
    RepenicPressureCluster,
    RepenicSceneModeCluster,
    RepenicTimeCluster,
    SleepCountdown,
    WakeupCountdown,
)

zhaquirks.setup()

MANUFACTURER = "Repenic Ltd."
MODEL = "RD-250ZG"


def make_read_attributes_rsp(attrid: int, value: bytes) -> bytes:
    """Build a Read Attributes Response frame holding a CharacterString value.

    Layout: frame_control(1) + tsn(1) + cmd_id(1) + attrid(2) + status(1)
    + type(1) + len(1) + value, which the quirk parses from raw bytes.
    """
    return (
        bytes([0x18, 0x01, 0x01])
        + attrid.to_bytes(2, "little")
        + bytes([0x00, 0x42, len(value)])
        + value
    )


@pytest.fixture
async def repenic_device(MockAppController, zigpy_device_from_v2_quirk):
    """Create a Repenic RD-250ZG device with all quirk clusters applied."""
    # Pretend the application is running so background startup tasks finish
    MockAppController.state = "running"
    device = zigpy_device_from_v2_quirk(
        manufacturer=MANUFACTURER,
        model=MODEL,
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                LevelControl.cluster_id: ClusterType.Server,
                Time.cluster_id: ClusterType.Server,
                RepenicSceneModeCluster.cluster_id: ClusterType.Server,
                RepenicPressureCluster.cluster_id: ClusterType.Server,
            }
        },
    )
    # Let the background OnOff poll task started by RepenicOnOff.__init__ finish
    on_off_cluster = device.endpoints[1].on_off
    with mock.patch.object(on_off_cluster, "read_attributes", mock.AsyncMock()):
        await asyncio.sleep(0.1)
    return device


async def test_quirk_replaces_clusters(repenic_device):
    """Test that all custom clusters replace the stock ones."""
    endpoint = repenic_device.endpoints[1]

    assert isinstance(endpoint.on_off, RepenicOnOff)
    assert isinstance(endpoint.level, RepenicLevelControl)
    assert isinstance(endpoint.time, RepenicTimeCluster)
    assert isinstance(endpoint.repenic_scene_mode, RepenicSceneModeCluster)
    assert isinstance(endpoint.repenic_pressure, RepenicPressureCluster)


async def test_scene_mode_deserialize_sleep_pattern(repenic_device):
    """Test parsing a sleep_pattern Read Attributes response."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    frame = make_read_attributes_rsp(0x0000, bytes([1, 10, 0, 0, 30, 0]))

    result = cluster.deserialize(frame)

    assert isinstance(result, tuple)
    assert result[0].command_id == foundation.GeneralCommand.Read_Attributes_rsp
    assert cluster._attr_cache["sleep_on_off"] == OnOffState.On
    assert cluster._attr_cache["sleep_hour"] == Hour.hour_10
    assert cluster._attr_cache["sleep_minute"] == Minute.minute_00
    assert cluster._attr_cache["sleep_countdown"] == SleepCountdown.minutes_30


async def test_scene_mode_deserialize_wakeup_pattern(repenic_device):
    """Test parsing a wake_up_pattern Read Attributes response."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    frame = make_read_attributes_rsp(0x0001, bytes([1, 6, 30, 127, 20, 0]))

    cluster.deserialize(frame)

    assert cluster._attr_cache["wakeup_on_off"] == OnOffState.On
    assert cluster._attr_cache["wakeup_hour"] == Hour.hour_06
    assert cluster._attr_cache["wakeup_minute"] == Minute.minute_30
    assert cluster._attr_cache["wakeup_brightness"] == 50
    assert cluster._attr_cache["wakeup_countdown"] == WakeupCountdown.minutes_20


async def test_scene_mode_deserialize_night_pattern(repenic_device):
    """Test parsing a night_pattern Read Attributes response."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    frame = make_read_attributes_rsp(0x0002, bytes([1, 22, 30, 51, 6, 15]))

    cluster.deserialize(frame)

    assert cluster._attr_cache["night_on_off"] == OnOffState.On
    assert cluster._attr_cache["night_hour"] == Hour.hour_22
    assert cluster._attr_cache["night_minute"] == Minute.minute_30
    assert cluster._attr_cache["night_brightness"] == 20
    assert cluster._attr_cache["night_end_hour"] == Hour.hour_06
    assert cluster._attr_cache["night_end_minute"] == Minute.minute_15


async def test_scene_mode_deserialize_short_sleep_pattern(repenic_device):
    """Test parsing a truncated sleep_pattern falls back to defaults."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    frame = make_read_attributes_rsp(0x0000, bytes([1, 10]))

    cluster.deserialize(frame)

    assert cluster._attr_cache["sleep_on_off"] == OnOffState.On
    assert cluster._attr_cache["sleep_hour"] == Hour.hour_10
    assert cluster._attr_cache["sleep_minute"] == Minute.minute_00
    assert cluster._attr_cache["sleep_countdown"] == SleepCountdown.minutes_30


@pytest.mark.parametrize(
    "frame",
    [
        b"\x18\x01\x0a\x00\x00\x18\x01",  # not a Read Attributes response
        make_read_attributes_rsp(0x0003, b"\x01"),  # not a pattern attribute
        # sleep_pattern attribute with a non-string data type
        b"\x18\x01\x01\x00\x00\x00\x20\x05",
    ],
)
async def test_scene_mode_deserialize_ignores_other_frames(repenic_device, frame):
    """Test that frames not carrying pattern data do not update the cache."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    cluster.deserialize(frame)

    assert cluster._attr_cache.get("sleep_on_off") is None
    assert cluster._attr_cache.get("sleep_hour") is None


async def test_scene_mode_deserialize_failure_keeps_result(repenic_device):
    """Test that a parsing failure is logged and does not break deserialization."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    frame = make_read_attributes_rsp(0x0000, bytes([1, 10, 0, 0, 30, 0]))

    with mock.patch(
        "zhaquirks.repenic.rd250zg.Hour", side_effect=ValueError("bad hour")
    ):
        result = cluster.deserialize(frame)

    # sleep_on_off is updated before the failure, sleep_hour keeps its default
    assert cluster._attr_cache["sleep_on_off"] == OnOffState.On
    assert cluster._attr_cache.get("sleep_hour") is None
    assert isinstance(result, tuple)


async def test_scene_mode_deserialize_failed_status(repenic_device):
    """Test a response with a failure status does not update the cache."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    # Record 1: sleep_pattern with failure status, record 2: wakeup_pattern
    frame = b"\x18\x01\x01" + b"\x00\x00\x01" + b"\x01\x00\x00\x42\x01\x41"

    cluster.deserialize(frame)

    assert cluster._attr_cache.get("sleep_on_off") is None
    assert cluster._attr_cache.get("sleep_hour") is None


@pytest.mark.parametrize(
    "attrid",
    [0x0001, 0x0002],  # wake_up_pattern, night_pattern
)
async def test_scene_mode_deserialize_pattern_failure_status(repenic_device, attrid):
    """Test that a failure status for wake/night patterns does not update the cache."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    # Read Attributes response: first record carries the target attrid with a
    # FAILURE status (no value); a second failure record pads the frame past the
    # quirk's 8-byte length gate.
    frame = (
        bytes([0x18, 0x01, 0x01])
        + attrid.to_bytes(2, "little")
        + bytes([0x01])
        + bytes([0x00, 0x00, 0x01])
    )

    cluster.deserialize(frame)

    assert cluster._attr_cache.get("wakeup_on_off") is None
    assert cluster._attr_cache.get("night_on_off") is None


@pytest.mark.parametrize(
    "attrid",
    [0x0001, 0x0002],  # wake_up_pattern, night_pattern
)
async def test_scene_mode_deserialize_pattern_non_string_type(repenic_device, attrid):
    """Test that a non-string data type for wake/night patterns is ignored."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    # Read Attributes response with SUCCESS status but a uint8 data type (0x20)
    frame = (
        bytes([0x18, 0x01, 0x01])
        + attrid.to_bytes(2, "little")
        + bytes([0x00, 0x20, 0x05])
    )

    cluster.deserialize(frame)

    assert cluster._attr_cache.get("wakeup_on_off") is None
    assert cluster._attr_cache.get("night_on_off") is None


async def test_scene_mode_apply_custom_configuration(repenic_device):
    """Test that custom configuration reads all three pattern attributes."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as mock_read:
        await cluster.apply_custom_configuration()

    assert mock_read.await_count == 3
    mock_read.assert_any_await([0x0000])
    mock_read.assert_any_await([0x0001])
    mock_read.assert_any_await([0x0002])


async def test_write_sleep_attributes_by_name(repenic_device):
    """Test writing sleep attributes by name sends a set_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(cluster, "set_pattern", mock.AsyncMock()) as set_pattern,
    ):
        result = await cluster.write_attributes({"sleep_hour": 11, "sleep_minute": 30})

    set_pattern.assert_awaited_once_with(pattern=bytes([0, 11, 30, 0, 30, 0]))
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._attr_cache["sleep_hour"] == 11
    assert cluster._attr_cache["sleep_minute"] == 30


async def test_write_sleep_attributes_by_id(repenic_device):
    """Test writing sleep attributes by attribute id sends a set_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(cluster, "set_pattern", mock.AsyncMock()) as set_pattern,
    ):
        await cluster.write_attributes({0xA002: 11})

    set_pattern.assert_awaited_once_with(pattern=bytes([0, 11, 0, 0, 30, 0]))
    assert cluster._attr_cache["sleep_hour"] == 11


async def test_write_wakeup_attributes_by_name(repenic_device):
    """Test writing wakeup attributes by name sends a set_wakeup_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(
            cluster, "set_wakeup_pattern", mock.AsyncMock()
        ) as set_wakeup_pattern,
    ):
        result = await cluster.write_attributes(
            {"wakeup_on_off": 1, "wakeup_brightness": 50}
        )

    set_wakeup_pattern.assert_awaited_once_with(pattern=bytes([1, 10, 0, 127, 30, 0]))
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._attr_cache["wakeup_on_off"] == 1
    assert cluster._attr_cache["wakeup_brightness"] == 50


async def test_write_wakeup_attributes_by_id(repenic_device):
    """Test writing wakeup attributes by attribute id sends a set_wakeup_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(
            cluster, "set_wakeup_pattern", mock.AsyncMock()
        ) as set_wakeup_pattern,
    ):
        await cluster.write_attributes({0xA008: 100})

    set_wakeup_pattern.assert_awaited_once_with(pattern=bytes([0, 10, 0, 254, 30, 0]))
    assert cluster._attr_cache["wakeup_brightness"] == 100


async def test_write_night_attributes_by_name(repenic_device):
    """Test writing night attributes by name sends a set_night_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(
            cluster, "set_night_pattern", mock.AsyncMock()
        ) as set_night_pattern,
    ):
        result = await cluster.write_attributes({"night_hour": 23, "night_end_hour": 5})

    set_night_pattern.assert_awaited_once_with(pattern=bytes([0, 23, 0, 25, 5, 0]))
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._attr_cache["night_hour"] == 23
    assert cluster._attr_cache["night_end_hour"] == 5


async def test_write_night_attributes_by_id(repenic_device):
    """Test writing night attributes by attribute id sends a set_night_pattern command."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(
            cluster, "set_night_pattern", mock.AsyncMock()
        ) as set_night_pattern,
    ):
        await cluster.write_attributes({0xA00F: 20})

    set_night_pattern.assert_awaited_once_with(pattern=bytes([0, 0, 0, 50, 6, 0]))
    assert cluster._attr_cache["night_brightness"] == 20


async def test_write_other_attributes_falls_back(repenic_device):
    """Test writing a non-pattern attribute falls back to the stock cluster."""
    cluster = repenic_device.endpoints[1].repenic_scene_mode
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with (
        mock.patch.object(cluster, "sync_time", mock.AsyncMock()),
        mock.patch.object(
            cluster, "write_attributes_raw", mock.AsyncMock(return_value=success)
        ) as mock_raw,
    ):
        result = await cluster.write_attributes({"scene_mode": 1})

    assert mock_raw.await_count == 1
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster._attr_cache["scene_mode"] == 1


async def test_sync_time_writes_to_time_cluster(repenic_device):
    """Test that sync_time writes local time and timezone to the Time cluster."""
    scene_cluster = repenic_device.endpoints[1].repenic_scene_mode
    time_cluster = repenic_device.endpoints[1].time

    with (
        mock.patch("zhaquirks.repenic.rd250zg.time.time", return_value=1000.0),
        mock.patch("zhaquirks.repenic.rd250zg.datetime") as mock_datetime,
        mock.patch.object(
            time_cluster, "write_attributes", mock.AsyncMock()
        ) as mock_write,
    ):
        mock_datetime.now.return_value.astimezone.return_value.utcoffset.return_value = timedelta(
            seconds=3600
        )
        await scene_cluster.sync_time()

    mock_write.assert_awaited_once_with(
        {"time": 4600, "time_zone": 3600}, manufacturer=None
    )


async def test_sync_time_without_time_cluster(repenic_device, caplog):
    """Test that sync_time logs a warning when no Time cluster exists."""
    endpoint = repenic_device.endpoints[1]

    with mock.patch.object(endpoint, "time", None):
        await endpoint.repenic_scene_mode.sync_time()

    assert "Time cluster not found on endpoint" in caplog.text


async def test_time_cluster_sync_time(repenic_device):
    """Test the time cluster writes local time and timezone."""
    time_cluster = repenic_device.endpoints[1].time

    with (
        mock.patch("zhaquirks.repenic.rd250zg.time.time", return_value=2000.0),
        mock.patch("zhaquirks.repenic.rd250zg.datetime") as mock_datetime,
        mock.patch.object(
            time_cluster, "write_attributes", mock.AsyncMock()
        ) as mock_write,
    ):
        mock_datetime.now.return_value.astimezone.return_value.utcoffset.return_value = timedelta(
            seconds=0
        )
        await time_cluster._sync_time()

    mock_write.assert_awaited_once_with(
        {"time": 2000, "time_zone": 0}, manufacturer=None
    )


async def test_time_cluster_sync_time_when_ready(repenic_device):
    """Test that the time cluster syncs once the application is running."""
    time_cluster = repenic_device.endpoints[1].time

    with mock.patch.object(time_cluster, "_sync_time", mock.AsyncMock()) as mock_sync:
        await time_cluster._sync_time_when_ready()

    mock_sync.assert_awaited_once()


async def test_time_cluster_sync_time_when_ready_without_application(repenic_device):
    """Test the readiness wait loop tolerates a missing application."""
    time_cluster = repenic_device.endpoints[1].time

    with (
        mock.patch("asyncio.sleep", new=mock.AsyncMock()),
        mock.patch.object(repenic_device, "_application", None),
        mock.patch.object(time_cluster, "_sync_time", mock.AsyncMock()) as mock_sync,
    ):
        await time_cluster._sync_time_when_ready()

    mock_sync.assert_awaited_once()


async def test_time_cluster_sync_time_when_ready_waits_for_running(repenic_device):
    """Test the readiness loop waits while the application is not yet running."""
    time_cluster = repenic_device.endpoints[1].time

    with (
        mock.patch("asyncio.sleep", new=mock.AsyncMock()),
        mock.patch.object(time_cluster, "_sync_time", mock.AsyncMock()) as mock_sync,
    ):
        repenic_device.application.state = "created"
        await time_cluster._sync_time_when_ready()

    mock_sync.assert_awaited_once()


async def test_time_cluster_deserialize_schedules_sync(repenic_device):
    """Test that deserializing a frame schedules a time sync."""
    time_cluster = repenic_device.endpoints[1].time

    with mock.patch.object(
        time_cluster, "_sync_time_when_ready", mock.AsyncMock()
    ) as mock_sync:
        result = time_cluster.deserialize(b"\x00\x01\x00\x00\x00")
        await asyncio.sleep(0.1)

    assert mock_sync.await_count == 1
    hdr, args = result
    assert hdr.command_id == foundation.GeneralCommand.Read_Attributes
    assert args.attribute_ids == [0]


async def test_onoff_reads_state_when_ready(repenic_device):
    """Test that the OnOff cluster polls its state when the application is ready."""
    on_off_cluster = repenic_device.endpoints[1].on_off

    with mock.patch.object(
        on_off_cluster, "read_attributes", mock.AsyncMock()
    ) as mock_read:
        await on_off_cluster._read_onoff_when_ready()

    mock_read.assert_awaited_once_with([0])


async def test_onoff_reads_state_when_ready_without_application(repenic_device):
    """Test the OnOff readiness wait loop tolerates a missing application."""
    on_off_cluster = repenic_device.endpoints[1].on_off

    with (
        mock.patch("asyncio.sleep", new=mock.AsyncMock()),
        mock.patch.object(repenic_device, "_application", None),
        mock.patch.object(
            on_off_cluster, "read_attributes", mock.AsyncMock()
        ) as mock_read,
    ):
        await on_off_cluster._read_onoff_when_ready()

    mock_read.assert_awaited_once_with([0])


async def test_onoff_reads_state_waits_for_running(repenic_device):
    """Test the OnOff readiness loop waits while the application is not running."""
    on_off_cluster = repenic_device.endpoints[1].on_off

    with (
        mock.patch("asyncio.sleep", new=mock.AsyncMock()),
        mock.patch.object(
            on_off_cluster, "read_attributes", mock.AsyncMock()
        ) as mock_read,
    ):
        repenic_device.application.state = "created"
        await on_off_cluster._read_onoff_when_ready()

    mock_read.assert_awaited_once_with([0])


@pytest.mark.parametrize(
    ("press_value", "expected_command"),
    [
        (int(PressType.double_click), COMMAND_DOUBLE),
        (int(PressType.triple_click), COMMAND_TRIPLE),
        (int(PressType.long_press), COMMAND_HOLD),
        (int(PressType.release), COMMAND_RELEASE),
    ],
)
async def test_pressure_cluster_sends_press_events(
    repenic_device, press_value, expected_command
):
    """Test that known press values are emitted as ZHA events."""
    pressure_cluster = repenic_device.endpoints[1].repenic_pressure
    listener = mock.Mock()
    pressure_cluster.add_listener(listener)
    hdr = foundation.ZCLHeader.cluster(tsn=1, command_id=0x00)

    pressure_cluster.handle_cluster_request(hdr, [0, press_value])

    listener.zha_send_event.assert_called_once_with(
        expected_command, {VALUE: press_value}
    )


@pytest.mark.parametrize(
    ("command_id", "args"),
    [
        (0x00, [0]),  # not enough arguments
        (0x00, [0, 0x99]),  # unknown press value
        (0x01, [0, int(PressType.double_click)]),  # not a press command
    ],
)
async def test_pressure_cluster_ignores_other_requests(
    repenic_device, command_id, args
):
    """Test that unexpected requests do not emit ZHA events."""
    pressure_cluster = repenic_device.endpoints[1].repenic_pressure
    listener = mock.Mock()
    pressure_cluster.add_listener(listener)
    hdr = foundation.ZCLHeader.cluster(tsn=1, command_id=command_id)

    pressure_cluster.handle_cluster_request(hdr, args)

    listener.zha_send_event.assert_not_called()


async def test_level_control_update_attribute(repenic_device):
    """Test that level control attribute updates are cached."""
    level_cluster = repenic_device.endpoints[1].level
    attrid = LevelControl.AttributeDefs.current_level.id

    level_cluster._update_attribute(attrid, 42)

    assert level_cluster._attr_cache[attrid] == 42
