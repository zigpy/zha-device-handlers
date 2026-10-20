"""Focused regression tests for the Aqara W600 quirk.

These tests intentionally exercise the pure mapping and state-synchronisation
contracts without requiring a live Zigbee network.
"""

import asyncio
import struct
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from zha.application.helpers import write_attributes_safe
from zha.application.platforms.binary_sensor import BinarySensor
from zha.application.platforms.number import NumberConfigurationEntity
from zha.application.platforms.select import ZCLEnumSelectEntity
from zha.application.platforms.sensor import Sensor
from zha.exceptions import ZHAException
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
import zigpy.exceptions
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import CustomCluster
from zhaquirks.xiaomi.aqara import thermostat_aeu005 as w600
from zhaquirks.xiaomi.aqara.thermostat_aeu005 import (
    AQARA,
    AQARA_MANUFACTURER_CODE,
    ATTR_DEVICE_STATE,
    ATTR_SCHEDULE_ENABLED,
    ATTR_SYSTEM_MODE,
    ATTR_THERMOSTAT_ENABLED,
    ATTR_VALVE_POSITION_RAW,
    MODEL,
    RUNSTATE_HEAT_ON,
    RUNSTATE_IDLE,
    SYS_AUTO,
    SYS_HEAT,
    SYS_OFF,
    W600_MODE_WRITES,
    AqaraW600FCC0,
    AqaraW600Status,
    AqaraW600Thermostat,
    W600TemperatureSource,
    _all_success,
    _decode_w600_preset_table,
    _iter_status_records,
    _optional_flag,
    _temperature_source_name,
)


def test_quirk_registration_matches_exact_manufacturer_and_model() -> None:
    """The V2 registration must target only the W600 identity."""

    matches = [
        model_info
        for entry in DEVICE_REGISTRY
        for model_info in entry.device_match.applies_to
        if (model_info.manufacturer, model_info.model) == (AQARA, MODEL)
    ]
    assert matches


def test_w600_attributes_resolve_with_manufacturer_code() -> None:
    """Vendor attributes must carry Aqara manufacturer code 4447."""
    expected = {
        "thermostat_enabled": (0x0271, "uint8_t"),
        "schedule_enabled": (0x027D, "uint8_t"),
        "device_state": (0x0311, "uint8_t"),
        "valve_position_raw": (0x0360, "Single"),
    }
    for name, (attr_id, type_name) in expected.items():
        definition = getattr(AqaraW600FCC0.AttributeDefs, name)
        assert definition.id == attr_id
        assert definition.manufacturer_code == AQARA_MANUFACTURER_CODE
        assert definition.type.__name__ == type_name


def test_mode_matrix_contains_only_off_heat_and_auto_paths() -> None:
    """Mode writes use FCC0 state and never standard system_mode."""
    assert W600_MODE_WRITES == {
        SYS_OFF: {ATTR_THERMOSTAT_ENABLED: 0, ATTR_SCHEDULE_ENABLED: 0},
        SYS_HEAT: {ATTR_THERMOSTAT_ENABLED: 1, ATTR_SCHEDULE_ENABLED: 0},
        SYS_AUTO: {ATTR_THERMOSTAT_ENABLED: 1, ATTR_SCHEDULE_ENABLED: 1},
    }
    assert set(W600_MODE_WRITES) == {SYS_OFF, SYS_HEAT, SYS_AUTO}
    assert all(ATTR_SYSTEM_MODE not in writes for writes in W600_MODE_WRITES.values())


@pytest.mark.parametrize(
    "records",
    [
        [SimpleNamespace(status=foundation.Status.SUCCESS)],
        [[SimpleNamespace(status=foundation.Status.SUCCESS)]],
        [
            [SimpleNamespace(status=foundation.Status.SUCCESS)],
            [SimpleNamespace(status=foundation.Status.SUCCESS)],
        ],
    ],
)
def test_status_processing_accepts_flat_and_nested_success(records) -> None:
    """Verify status processing accepts flat and nested success."""
    assert _all_success(records)
    assert list(_iter_status_records(records))


def test_status_processing_rejects_nested_failure() -> None:
    """Verify status processing rejects nested failure."""
    records = [
        [SimpleNamespace(status=foundation.Status.SUCCESS)],
        [SimpleNamespace(status=foundation.Status.FAILURE)],
    ]
    assert not _all_success(records)


class _FakeFCC0:
    def __init__(self, enabled: int) -> None:
        self._attr_cache = {ATTR_THERMOSTAT_ENABLED: enabled}


class _FakeThermostat(AqaraW600Thermostat):
    def __init__(self, enabled: int) -> None:
        self.fcc0 = _FakeFCC0(enabled)
        self.updates = []

    def _fcc0(self):
        return self.fcc0

    def _update_attribute(self, attrid, value) -> None:
        self.updates.append((attrid, value))


@pytest.mark.parametrize(
    ("enabled", "valve", "expected_action"),
    [
        (1, 0, RUNSTATE_IDLE),
        (1, 25, RUNSTATE_HEAT_ON),
        (1, 0.01, RUNSTATE_HEAT_ON),
        (1, 0.5, RUNSTATE_HEAT_ON),
        (None, 0.5, RUNSTATE_HEAT_ON),
        (0, 25, RUNSTATE_IDLE),
    ],
)
def test_valve_position_updates_only_running_state(
    enabled: int, valve: int, expected_action: int
) -> None:
    """Verify valve position updates only running state."""
    thermostat = _FakeThermostat(enabled)

    thermostat._sync_running_state_from_valve(valve)

    assert thermostat.updates == [(0x0029, expected_action)]
    assert all(attrid != ATTR_SYSTEM_MODE for attrid, _ in thermostat.updates)
    assert ATTR_VALVE_POSITION_RAW == 0x0360
    assert ATTR_DEVICE_STATE == 0x0311


@pytest.fixture
def clusters():
    """Use real Zigpy clusters and caches without radio traffic."""
    device = zigpy.device.Device(MagicMock(), t.EUI64([0] * 8), t.NWK(0))
    device.node_desc = NodeDescriptor(manufacturer_code=AQARA_MANUFACTURER_CODE)
    endpoint = device.add_endpoint(1)
    fcc0 = AqaraW600FCC0(endpoint)
    endpoint.add_input_cluster(fcc0.cluster_id, fcc0)
    thermostat = AqaraW600Thermostat(endpoint)
    endpoint.add_input_cluster(thermostat.cluster_id, thermostat)
    return fcc0, thermostat


@pytest.mark.parametrize("enabled_first", [True, False])
def test_fractional_opening_independent_of_report_order(clusters, enabled_first):
    """Verify fractional opening independent of report order."""
    fcc0, thermostat = clusters
    reports = [(ATTR_THERMOSTAT_ENABLED, 1), (ATTR_VALVE_POSITION_RAW, 0.5)]
    if not enabled_first:
        reports.reverse()
    for attrid, value in reports:
        fcc0._update_attribute(attrid, value)
    assert thermostat.get(0x0029) == RUNSTATE_HEAT_ON
    assert thermostat.get(ATTR_SYSTEM_MODE) == SYS_HEAT


def test_enable_report_recomputes_cached_valve_state(clusters):
    """Verify enable report recomputes cached valve state."""
    fcc0, thermostat = clusters
    fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 0)
    fcc0._update_attribute(ATTR_VALVE_POSITION_RAW, 0.5)
    assert thermostat.get(0x0029) == RUNSTATE_IDLE
    fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 1)
    assert thermostat.get(0x0029) == RUNSTATE_HEAT_ON
    fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 0)
    assert thermostat.get(0x0029) == RUNSTATE_IDLE


def test_enable_without_valve_sample_does_not_invent_idle(clusters):
    """Verify enable without valve sample does not invent idle."""
    fcc0, thermostat = clusters
    fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 1)
    assert thermostat.get(0x0029) is None


@pytest.mark.parametrize("sample", [None, -1, float("nan"), float("inf"), "bad"])
def test_invalid_valve_sample_preserves_last_action(clusters, sample):
    """Verify invalid valve sample preserves last action."""
    fcc0, thermostat = clusters
    fcc0._update_attribute(ATTR_THERMOSTAT_ENABLED, 1)
    fcc0._update_attribute(ATTR_VALVE_POSITION_RAW, 0.5)
    fcc0._update_attribute(ATTR_VALVE_POSITION_RAW, sample)
    assert thermostat.get(0x0029) == RUNSTATE_HEAT_ON


def test_zero_valve_report_closes_after_fractional_opening(clusters):
    """Verify zero valve report closes after fractional opening."""
    fcc0, thermostat = clusters
    fcc0._update_attribute(ATTR_VALVE_POSITION_RAW, 0.5)
    assert thermostat.get(0x0029) == RUNSTATE_HEAT_ON
    fcc0._update_attribute(ATTR_VALVE_POSITION_RAW, 0)
    assert thermostat.get(0x0029) == RUNSTATE_IDLE
    assert thermostat.get(ATTR_SYSTEM_MODE) is None


@pytest.mark.parametrize(
    "wire_type", [foundation.DataTypeId.single, foundation.DataTypeId.uint16]
)
def test_valve_report_decoding_preserves_wire_value(clusters, wire_type):
    """Decode current float reports and retain compatibility with integers."""
    fcc0, thermostat = clusters
    value = (
        t.Single(0.5) if wire_type == foundation.DataTypeId.single else t.uint16_t(25)
    )
    command = foundation.GeneralCommand.Report_Attributes
    header = foundation.ZCLHeader.general(
        tsn=1, command_id=command, manufacturer=AQARA_MANUFACTURER_CODE
    )
    header = header.replace(
        frame_control=header.frame_control.replace(disable_default_response=True)
    )
    payload = foundation.GENERAL_COMMANDS[command].schema(
        attribute_reports=[
            foundation.Attribute(
                attrid=ATTR_VALVE_POSITION_RAW,
                value=foundation.TypeValue(type=wire_type, value=value),
            )
        ]
    )
    decoded_header, decoded_payload = fcc0.deserialize(
        header.serialize() + payload.serialize()
    )
    fcc0.handle_cluster_general_request(decoded_header, decoded_payload)
    assert fcc0.get(ATTR_VALVE_POSITION_RAW) == value
    assert thermostat.get(0x0029) == RUNSTATE_HEAT_ON


@pytest.fixture
def status_clusters(clusters):
    """Attach the local status cluster to the test device."""

    fcc0, thermostat = clusters
    status = AqaraW600Status(fcc0.endpoint)
    fcc0.endpoint.add_input_cluster(status.cluster_id, status)
    return fcc0, status


def _report_bytes(cluster, attrid, value):
    """Exercise the actual ZCL octet-string report path, including decoding."""
    command = foundation.GeneralCommand.Report_Attributes
    header = foundation.ZCLHeader.general(
        tsn=1, command_id=command, manufacturer=AQARA_MANUFACTURER_CODE
    )
    header = header.replace(
        frame_control=header.frame_control.replace(disable_default_response=True)
    )
    payload = foundation.GENERAL_COMMANDS[command].schema(
        attribute_reports=[
            foundation.Attribute(
                attrid=attrid,
                value=foundation.TypeValue(
                    type=foundation.DataTypeId.octstr, value=t.LVBytes(value)
                ),
            )
        ]
    )
    decoded_header, decoded_payload = cluster.deserialize(
        header.serialize() + payload.serialize()
    )
    cluster.handle_cluster_general_request(decoded_header, decoded_payload)


def test_heartbeat_battery_on_wire_and_zero_voltage(status_clusters):
    """An anonymized FW7216 field subset reports 100%, not 50%."""
    fcc0, status = status_clusters
    _report_bytes(fcc0, 0x00F7, bytes.fromhex("0d23301c000017210000182064"))
    assert status.get("battery_percentage") == 100
    assert status.get("battery_millivolts") is None
    _report_bytes(fcc0, 0x00F7, bytes.fromhex("1721b80b18205a"))
    assert status.get("battery_millivolts") == 3000
    assert status.get("battery_percentage") == 90
    _report_bytes(fcc0, 0x00F7, bytes.fromhex("172100001820ff"))
    assert status.get("battery_millivolts") == 3000
    assert status.get("battery_percentage") == 90


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x18",
        b"\x18\x20",
        b"\x18\x20\x64\x17\x21\x01",
        b"\x18\xff",
        None,
        "invalid",
    ],
)
def test_invalid_heartbeat_preserves_battery(status_clusters, payload):
    """Verify invalid heartbeat preserves battery."""
    fcc0, status = status_clusters
    fcc0.update_attribute(0x00F7, bytes.fromhex("182064"))
    fcc0.update_attribute(0x00F7, payload)
    assert status.get("battery_percentage") == 100


async def test_local_status_never_sends_radio_requests(status_clusters):
    """Verify local status never sends radio requests."""

    _, status = status_clusters
    with patch.object(status.endpoint, "request", new_callable=AsyncMock) as request:
        await status.bind()
        await status.configure_reporting("battery_percentage", 0, 900, 1)
        await status.read_attributes(["battery_percentage"])
        result = await status.write_attributes({"battery_percentage": 50})
    request.assert_not_called()
    assert result[0][0].status == foundation.Status.READ_ONLY
    assert status.get("battery_percentage") is None


@pytest.mark.parametrize(
    ("code", "window", "alarm"),
    [
        (0x00, False, False),
        (0x0D, True, False),
        (0x0E, True, False),
        (0x10, None, True),
        (0xFF, None, None),
    ],
)
def test_heartbeat_window_and_alarm(status_clusters, code, window, alarm):
    """Verify heartbeat window and alarm."""
    fcc0, status = status_clusters
    # Seed an active state to check that unknown values do not invent "OK".
    status.update_attribute(0x0002, True)
    status.update_attribute(0x0003, True)
    _report_bytes(fcc0, 0x00F7, b"\x9c\x41\x08" + bytes([0, 0, 0, 0, code, 0, 0, 0]))

    assert _optional_flag(status.get("window_open")) is window
    assert _optional_flag(status.get("valve_alarm")) is alarm


def test_short_or_missing_status_block_preserves_state(status_clusters):
    """Verify short or missing status block preserves state."""
    fcc0, status = status_clusters
    status.update_attribute(0x0003, True)
    _report_bytes(fcc0, 0x00F7, b"\x9c\x41\x04\x00\x00\x00\x00")
    assert status.get("valve_alarm") == 1
    _report_bytes(fcc0, 0x00F7, bytes.fromhex("182064"))
    assert status.get("valve_alarm") == 1


@pytest.mark.parametrize(("schedule", "hold_calls"), [(0, 0), (1, 1)])
async def test_preset_write_arms_hold_only_with_schedule(
    clusters, schedule, hold_calls
):
    """Verify preset write arms hold only with schedule."""

    fcc0, thermostat = clusters
    fcc0.update_attribute(0x027D, schedule)
    fcc0.update_attribute(0x0311, 255)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        result = await fcc0.write_attributes({"device_state": 3})
    assert result[0][0].status == foundation.Status.SUCCESS
    assert fcc0.get(0x0311) == 3
    assert write.await_count == 1 + hold_calls
    assert write.call_args_list[0].args == ({0x0311: 3},)
    assert write.call_args_list[0].kwargs["manufacturer"] == 4447
    assert write.call_args_list[0].kwargs["update_cache"] is False
    if schedule:
        assert write.call_args_list[1].args == ({0x0023: 1},)


async def test_failed_hold_does_not_confirm_selected_preset(clusters):
    """Verify failed hold does not confirm selected preset."""

    fcc0, thermostat = clusters
    fcc0.update_attribute(0x027D, 1)
    fcc0.update_attribute(0x0311, 255)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    with patch.object(
        CustomCluster,
        "write_attributes",
        new_callable=AsyncMock,
        side_effect=[success, failure],
    ):
        result = await fcc0.write_attributes({0x0311: 1})
    assert result[0][0].status == foundation.Status.FAILURE
    assert fcc0.get(0x0311) == 255


async def test_manual_preset_uses_current_target_not_vendor_255(clusters):
    """Verify manual preset uses current target not vendor 255."""

    fcc0, thermostat = clusters
    thermostat.update_attribute(0x0012, 1850)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        thermostat, "write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        await fcc0.write_attributes({"device_state": 255})
    write.assert_awaited_once_with({0x0012: 1850})
    assert fcc0.get(0x0311) == 255


async def test_unknown_schedule_is_read_before_profile_write(clusters):
    """Verify unknown schedule is read before profile write."""

    fcc0, _ = clusters
    with (
        patch.object(
            fcc0,
            "read_attributes",
            new_callable=AsyncMock,
            return_value=({}, {0x027D: foundation.Status.FAILURE}),
        ) as read,
        patch.object(
            CustomCluster, "write_attributes", new_callable=AsyncMock
        ) as write,
    ):
        result = await fcc0.write_attributes({"device_state": 1})
    read.assert_awaited_once()
    write.assert_not_awaited()
    assert result[0][0].status == foundation.Status.FAILURE


# Anonymized table fields observed on FW7216; contains no device identifiers.
PRESET_TABLE = bytes.fromhex("05010000280a0200000807030000d007050000e8030600006009")


def test_preset_table_wire_decoding(status_clusters):
    """Verify preset table wire decoding."""
    fcc0, status = status_clusters
    _report_bytes(fcc0, 0x0317, PRESET_TABLE)
    assert [status.get(0x0010 + i) for i in range(5)] == [2600, 1800, 2000, 1000, 2400]
    _report_bytes(fcc0, 0x0317, PRESET_TABLE[:-1])
    assert status.get("preset_home_temperature") == 2600


async def test_preset_temperature_write_preserves_other_records(status_clusters):
    """Verify preset temperature write preserves other records."""

    fcc0, status = status_clusters
    # Unknown records and reserved bytes must survive a read/modify/write.
    raw = bytes([6]) + PRESET_TABLE[1:] + bytes.fromhex("6301020304")
    raw = raw[:2] + b"\x12\x34" + raw[4:]
    fcc0.update_attribute(0x0317, raw)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        await status.write_attributes({"preset_home_temperature": 2150})
    written = write.call_args.args[0][0x0317]
    assert written[:4] == raw[:4]
    assert written[4:6] == (2150).to_bytes(2, "little")
    assert written[6:] == raw[6:]
    assert write.call_args.kwargs == {"manufacturer": 4447, "update_cache": False}
    assert status.get("preset_home_temperature") == 2150
    assert status.get("preset_away_temperature") == 1800


@pytest.mark.parametrize(
    "temperature", [499, 3001, 2125, float("nan"), float("inf"), "21"]
)
async def test_invalid_profile_temperature_never_writes(status_clusters, temperature):
    """Verify invalid profile temperature never writes."""

    fcc0, status = status_clusters
    with patch.object(fcc0, "write_attributes", new_callable=AsyncMock) as write:
        result = await status.write_attributes({"preset_home_temperature": temperature})
    write.assert_not_awaited()
    assert result[0][0].status == foundation.Status.INVALID_VALUE


async def test_unknown_table_is_read_and_failed_write_keeps_values(status_clusters):
    """Verify unknown table is read and failed write keeps values."""

    fcc0, status = status_clusters
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    with (
        patch.object(
            fcc0,
            "read_attributes",
            new_callable=AsyncMock,
            return_value=({0x0317: PRESET_TABLE}, {}),
        ) as read,
        patch.object(
            CustomCluster,
            "write_attributes",
            new_callable=AsyncMock,
            return_value=failure,
        ),
    ):
        result = await status.write_attributes({"preset_home_temperature": 2150})
    read.assert_awaited_once()
    assert result[0][0].status == foundation.Status.FAILURE
    assert status.get("preset_home_temperature") is None


async def test_unavailable_table_prevents_write(status_clusters):
    """Verify unavailable table prevents write."""

    fcc0, status = status_clusters
    with (
        patch.object(
            fcc0, "read_attributes", new_callable=AsyncMock, return_value=({}, {})
        ),
        patch.object(fcc0, "write_attributes", new_callable=AsyncMock) as write,
    ):
        result = await status.write_attributes({"preset_home_temperature": 2150})
    write.assert_not_awaited()
    assert result[0][0].status == foundation.Status.FAILURE


async def test_serial_profile_updates_preserve_both_changes(status_clusters):
    """Verify serial profile updates preserve both changes."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0317, PRESET_TABLE)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=success
    ):
        await asyncio.gather(
            status.write_attributes({"preset_home_temperature": 2150}),
            status.write_attributes({"preset_away_temperature": 1650}),
        )
    assert status.get("preset_home_temperature") == 2150
    assert status.get("preset_away_temperature") == 1650


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "internal"), (1, "external"), (2, None), (255, None), (None, None)],
)
def test_temperature_source_mapping(value, expected):
    """Verify temperature source mapping."""

    assert _temperature_source_name(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"), [(0, False), (1, False), (2, True), (3, None), (255, None)]
)
def test_external_status_is_separate_from_source(status_clusters, value, expected):
    """Verify external status is separate from source."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0280, 1)
    fcc0.update_attribute(0x027E, value)
    assert fcc0.get(0x0280) == 1
    assert _optional_flag(status.get("external_temperature_problem")) is expected


@pytest.mark.parametrize(
    "attribute", ["window_open", "valve_alarm", "external_temperature_problem"]
)
def test_zha_binary_sensor_reports_unknown_before_first_sample(
    status_clusters, attribute
):
    """Verify zha binary sensor reports unknown before first sample."""

    _, status = status_clusters
    entity = SimpleNamespace(
        _cluster=status, _attribute_name=attribute, _attribute_converter=_optional_flag
    )
    assert BinarySensor.is_on.fget(entity) is None


async def test_external_status_initial_read_uses_real_attribute_only(status_clusters):
    """Verify external status initial read uses real attribute only."""

    fcc0, status = status_clusters
    with patch.object(
        fcc0, "read_attributes", new_callable=AsyncMock, return_value=({}, {})
    ) as read:
        await status.read_attributes(["external_temperature_problem"])
    read.assert_awaited_once_with([0x027E], manufacturer=4447, allow_cache=False)
    assert status.get("external_temperature_problem") == 255


def test_new_entities_do_not_add_reporting_and_source_has_readout_and_control():
    """Verify new entities do not add reporting and source has readout and control."""

    entry = next(
        entry
        for entry in DEVICE_REGISTRY
        if any(
            info.manufacturer == AQARA and info.model == MODEL
            for info in entry.device_match.applies_to
        )
    )
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    new = [
        item for item in metadata if (item.unique_id_suffix or "").startswith("w600-")
    ]
    assert len(new) == 16
    assert all(item.reporting_config is None for item in new)
    assert {
        item.entity_platform.value
        for item in new
        if item.attribute_name == "temperature_source"
    } == {"sensor", "select"}
    temperatures = [item for item in new if item.attribute_name.startswith("preset_")]
    assert len(temperatures) == 5
    assert all(
        item.cluster_id == AqaraW600Status.cluster_id and item.multiplier == 0.01
        for item in temperatures
    )


@pytest.mark.parametrize(
    "raw",
    [
        PRESET_TABLE[:-5],
        bytes([5]) + PRESET_TABLE[1:6] + PRESET_TABLE[1:6] + PRESET_TABLE[11:],
        PRESET_TABLE[:4] + b"\xff\xff" + PRESET_TABLE[6:],
    ],
)
def test_incomplete_duplicate_or_invalid_preset_table_is_rejected(raw):
    """Verify incomplete duplicate or invalid preset table is rejected."""

    assert _decode_w600_preset_table(raw) == {}


async def test_sleeping_device_does_not_block_cached_telemetry(status_clusters):
    """Verify sleeping device does not block cached telemetry."""

    fcc0, status = status_clusters
    status.update_attribute(0, 100)
    with patch.object(
        fcc0, "read_attributes", new_callable=AsyncMock, side_effect=TimeoutError
    ):
        success, _ = await status.read_attributes(
            [
                "battery_percentage",
                "external_temperature_problem",
                "preset_home_temperature",
            ]
        )
    assert success["battery_percentage"] == 100
    assert status.get("external_temperature_problem") == 255
    assert status.get("preset_home_temperature") is None


@pytest.mark.parametrize("value", [1, 2, 3, 5, 6, 255, None])
def test_raw_profile_sensor_displays_manual_255(status_clusters, value):
    """Verify raw profile sensor displays manual 255."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0311, value)
    entity = SimpleNamespace(
        _cluster=status,
        _attribute_name="device_state_raw",
        _attribute_converter=None,
        _attr_def=status.attributes_by_name["device_state_raw"],
        formatter=lambda raw: raw,
    )
    entity._is_non_value = lambda raw: Sensor._is_non_value(entity, raw)
    assert Sensor.native_value.fget(entity) == value
    assert fcc0.attributes_by_name["device_state"].type is t.uint8_t
    assert fcc0.get(0x0311) == value


async def test_raw_profile_read_uses_vendor_attribute_not_local_id(status_clusters):
    """Verify raw profile read uses vendor attribute not local id."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0311, 255)
    with patch.object(
        fcc0,
        "read_attributes",
        new_callable=AsyncMock,
        return_value=({0x0311: 255}, {}),
    ) as read:
        result, _ = await status.read_attributes(["device_state_raw"])
    read.assert_awaited_once_with([0x0311], manufacturer=4447, allow_cache=False)
    assert result["device_state_raw"] == 255


def test_raw_profile_sensor_retains_entity_identity():
    """Verify raw profile sensor retains entity identity."""

    entry = next(
        entry
        for entry in DEVICE_REGISTRY
        if any(
            info.manufacturer == AQARA and info.model == MODEL
            for info in entry.device_match.applies_to
        )
    )
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    raw = next(item for item in metadata if item.translation_key == "device_state")
    assert raw.unique_id_suffix == "64704-device_state"
    assert raw.fallback_name == "Device state (raw)"
    assert raw.cluster_id == AqaraW600Status.cluster_id
    assert raw.attribute_name == "device_state_raw"
    assert raw.reporting_config is None


@pytest.mark.parametrize("enabled", [0, 1])
async def test_abnormal_notification_uses_uint8_manufacturer_write(clusters, enabled):
    """Verify abnormal notification uses uint8 manufacturer write."""

    fcc0, _ = clusters
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        fcc0, "_write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        result = await fcc0.write_attributes(
            {"temperature_control_abnormal_notification": enabled}
        )
    assert result[0][0].status == foundation.Status.SUCCESS
    records = write.call_args.args[0]
    assert records[0].attrid == 0x0274
    assert records[0].value.type == foundation.DataTypeId.uint8
    assert records[0].value.value == enabled
    assert write.call_args.kwargs["manufacturer"] == 4447


def test_abnormal_notification_switch_has_no_reporting():
    """Verify abnormal notification switch has no reporting."""

    entry = next(
        entry
        for entry in DEVICE_REGISTRY
        if any(
            info.manufacturer == AQARA and info.model == MODEL
            for info in entry.device_match.applies_to
        )
    )
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    item = next(
        item
        for item in metadata
        if item.translation_key == "temperature_control_abnormal_notification"
    )
    assert item.entity_platform.value == "switch"
    assert item.reporting_config is None


@pytest.mark.parametrize("enabled", [0, 1])
async def test_schedule_control_write_order_and_off_state(status_clusters, enabled):
    """Verify schedule control write order and off state."""

    fcc0, status = status_clusters
    thermostat = fcc0.endpoint.thermostat
    fcc0.update_attribute(0x0271, 0)
    fcc0.update_attribute(0x027D, 1 - enabled)
    thermostat.update_attribute(0x0023, 1)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        result = await status.write_attributes({"schedule_control": enabled})
    assert result[0][0].status == foundation.Status.SUCCESS
    assert [call.args[0] for call in write.call_args_list] == (
        [{0x0023: 0}, {0x027D: 0}] if not enabled else [{0x027D: 1}]
    )
    assert write.call_args.kwargs == {"manufacturer": 4447, "update_cache": False}
    assert fcc0.get(0x0271) == 0
    assert thermostat.get(0x001C) == SYS_OFF
    assert status.get("schedule_control") == enabled
    if not enabled:
        assert thermostat.get(0x0023) == 0


async def test_schedule_disable_failed_hold_stops_before_schedule(status_clusters):
    """Verify schedule disable failed hold stops before schedule."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x027D, 1)
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=failure
    ) as write:
        result = await status.write_attributes({"schedule_control": 0})
    assert result[0][0].status == foundation.Status.FAILURE
    assert write.await_count == 1
    assert fcc0.get(0x027D) == 1
    assert status.get("schedule_control") == 1


async def test_schedule_write_failure_is_not_confirmed(status_clusters):
    """Verify schedule write failure is not confirmed."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x027D, 0)
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=failure
    ):
        await status.write_attributes({"schedule_control": 1})
    assert status.get("schedule_control") == 0


async def test_schedule_read_never_uses_local_attribute_on_wire(status_clusters):
    """Verify schedule read never uses local attribute on wire."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x027D, 1)
    with patch.object(fcc0, "read_attributes", new_callable=AsyncMock) as read:
        result, _ = await status.read_attributes(["schedule_control"])
    read.assert_not_awaited()
    assert result["schedule_control"] == 1


@pytest.fixture
def external_writer(status_clusters):
    """Capture external sensor protocol writes for the test device."""

    fcc0, status = status_clusters
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        CustomCluster, "write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        yield fcc0, status, write


async def test_external_source_binding_envelopes_and_samples(external_writer):
    """Verify external source binding envelopes and samples."""

    fcc0, status, write = external_writer
    with patch.object(w600.time, "time", return_value=1_700_000_000):
        result = await fcc0.set_external_temperature(source=1, centidegrees=2150)
    assert result[0][0].status == foundation.Status.SUCCESS
    assert write.await_count == 5
    records = [call.args[0] for call in write.call_args_list]
    assert records[2] == {0x0280: 1}
    packets = [bytes(records[i][0xFFF2]) for i in (0, 1, 3, 4)]
    assert [p[6] for p in packets] == [2, 2, 5, 5]
    assert [p[4] for p in packets] == [0x12, 0x13, 0x14, 0x15]
    assert all(sum(p[:6]) & 255 == 0 for p in packets)
    assert all(
        p[2] == len(p) - 6 and p[7] == 0x41 and p[8] == len(p) - 9 for p in packets
    )
    assert packets[0][9:13] == struct.pack(">I", 1_700_000_000)
    assert packets[0][13] == 0x14 and packets[1][13] == 0x17
    assert packets[0][14:22] == bytes(8)  # Synthetic test device address.
    assert packets[0][22:30] == w600.W600_VIRTUAL_SENSOR
    # Independent expected descriptor bytes from the reference array.
    assert packets[0][34:] == bytes(
        [
            0x15,
            0x0A,
            0x01,
            0,
            0,
            1,
            6,
            0xE6,
            0xB8,
            0xA9,
            0xE5,
            0xBA,
            0xA6,
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            7,
            0x65,
        ]
    )
    assert packets[2][9:] == w600.W600_VIRTUAL_SENSOR + bytes.fromhex(
        "00010055"
    ) + struct.pack(">f", 2150)
    assert packets[3][9:] == w600.W600_VIRTUAL_SENSOR + bytes.fromhex(
        "080007fd00000001"
    )
    assert all(
        call.kwargs == {"manufacturer": 4447, "update_cache": False}
        for call in write.call_args_list
    )
    assert fcc0.get(0x0280) == 1
    assert status.get("external_temperature_input") == 2150


async def test_external_next_sample_does_not_rebind_or_repeat_availability(
    external_writer,
):
    """Verify external next sample does not rebind or repeat availability."""
    fcc0, status, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    await status.write_attributes({"external_temperature_input": 2200})
    assert write.await_count == 1
    assert status.get("external_temperature_input") == 2200


async def test_external_selection_alone_does_not_invent_sample(external_writer):
    """Verify external selection alone does not invent sample."""
    fcc0, status, write = external_writer
    await fcc0.write_attributes({"temperature_source": 1})
    assert write.await_count == 3
    assert status.get("external_temperature_input") is None
    assert fcc0._external_sample is None


async def test_internal_source_unbinds_both_channels_and_clears_sample(external_writer):
    """Verify internal source unbinds both channels and clears sample."""
    fcc0, status, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    result = await fcc0.write_attributes({"temperature_source": 0})
    assert result[0][0].status == foundation.Status.SUCCESS
    assert write.call_args_list[0].args[0] == {0x0280: 0}
    assert write.await_count == 3
    for call in write.call_args_list[1:]:
        packet = call.args[0][0xFFF2]
        assert packet[6] == 4 and packet[22:] == bytes(12)
    assert status.get("external_temperature_input") is None
    assert fcc0._external_sample is None
    assert fcc0.get(0x0280) == 0


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -4001, 12501, 2150.5, True, "2150"]
)
async def test_invalid_external_sample_has_no_side_effects(external_writer, value):
    """Verify invalid external sample has no side effects."""
    fcc0, status, write = external_writer
    result = await fcc0.set_external_temperature(source=1, centidegrees=value)
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    write.assert_not_awaited()
    assert fcc0.get(0x0280) is None
    assert status.get("external_temperature_input") is None


@pytest.mark.parametrize("source", [None, 0])
async def test_external_input_rejected_without_external_source(external_writer, source):
    """Verify external input rejected without external source."""
    fcc0, status, write = external_writer
    if source is not None:
        fcc0.update_attribute(0x0280, source)
    result = await status.write_attributes({"external_temperature_input": 2100})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    write.assert_not_awaited()


@pytest.mark.parametrize("value", [-4000, 0, 12500])
async def test_external_temperature_bounds_and_zero(external_writer, value):
    """Verify external temperature bounds and zero."""

    fcc0, status, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=value)
    packet = write.call_args_list[3].args[0][0xFFF2]
    assert struct.unpack(">f", packet[-4:])[0] == value
    assert status.get("external_temperature_input") == value


def _external_request(channel="temperature", counter=7):

    header = bytes((0xAA, 0x71, 15, 0x84, counter))
    return (
        header
        + bytes(((-sum(header)) & 255, 6, 0x41, 12))
        + w600.W600_VIRTUAL_SENSOR
        + w600.W600_EXTERNAL_CHANNELS[channel][1]
    )


@pytest.mark.parametrize("channel", ["temperature", "availability"])
async def test_external_requests_use_fresh_sample_and_deduplicate_tsn(
    external_writer, channel
):
    """Verify external requests use fresh sample and deduplicate tsn."""
    fcc0, _, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    request = _external_request(channel)
    generation = fcc0._external_generation
    await fcc0._respond_external_request(1, request, generation)
    await fcc0._respond_external_request(1, request, generation)
    assert write.await_count == 1
    # A separate ZCL request may reuse the same body counter.
    await fcc0._respond_external_request(2, request, generation)
    assert write.await_count == 2


async def test_external_request_received_as_zcl_report(external_writer):
    """Verify external request received as zcl report."""

    fcc0, _, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    _report_bytes(fcc0, 0xFFF2, _external_request())
    await asyncio.gather(*tuple(fcc0._tasks))
    assert write.await_count == 1


@pytest.mark.parametrize(
    "mutation", ["checksum", "identity", "marker", "length", "action"]
)
async def test_invalid_external_request_is_ignored(external_writer, mutation):
    """Verify invalid external request is ignored."""
    fcc0, _, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    request = bytearray(_external_request())
    index = {"checksum": 5, "identity": 9, "marker": 17, "length": 8, "action": 6}[
        mutation
    ]
    request[index] ^= 1
    await fcc0._respond_external_request(1, bytes(request), fcc0._external_generation)
    write.assert_not_awaited()


async def test_external_old_sample_is_not_resent(external_writer):
    """Verify external old sample is not resent."""

    fcc0, _, write = external_writer
    with patch.object(w600.time, "monotonic", return_value=100):
        await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    with patch.object(w600.time, "monotonic", return_value=161):
        await fcc0._respond_external_request(
            1, _external_request(), fcc0._external_generation
        )
    write.assert_not_awaited()


async def test_expired_input_is_rejected_before_any_write(external_writer):
    """Verify expired input is rejected before any write."""

    fcc0, _, write = external_writer
    with patch.object(w600.time, "monotonic", side_effect=[100, 161]):
        result = await fcc0.set_external_temperature(source=1, centidegrees=2150)
    assert result[0][0].status == foundation.Status.FAILURE
    write.assert_not_awaited()


@pytest.mark.parametrize("failure_at", range(5))
async def test_external_write_failure_stops_transaction(external_writer, failure_at):
    """Verify external write failure stops transaction."""
    fcc0, status, write = external_writer
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    write.side_effect = [success] * failure_at + [failure]
    result = await fcc0.set_external_temperature(source=1, centidegrees=2150)
    assert result[0][0].status == foundation.Status.FAILURE
    assert write.await_count == failure_at + 1
    assert fcc0._external_sample is None
    assert not fcc0._external_active
    assert status.get("external_temperature_input") is None


async def test_internal_choice_supersedes_queued_external_input(external_writer):
    """Verify internal choice supersedes queued external input."""

    fcc0, status, write = external_writer
    fcc0.update_attribute(0x0280, 1)
    await fcc0._external_lock.acquire()
    sample_task = asyncio.create_task(fcc0.set_external_temperature(centidegrees=2150))
    await asyncio.sleep(0)
    internal_task = asyncio.create_task(fcc0.set_external_temperature(source=0))
    await asyncio.sleep(0)
    fcc0._external_lock.release()
    sample_result, internal_result = await asyncio.gather(sample_task, internal_task)
    assert sample_result[0][0].status == foundation.Status.FAILURE
    assert internal_result[0][0].status == foundation.Status.SUCCESS
    assert write.await_count == 3
    assert write.call_args_list[0].args[0] == {0x0280: 0}
    assert status.get("external_temperature_input") is None


@pytest.mark.parametrize("event", ["announce", "internal_report", "remove"])
async def test_external_lifecycle_drops_cached_sample(external_writer, event):
    """Verify external lifecycle drops cached sample."""
    fcc0, status, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    if event == "announce":
        fcc0.endpoint.device.zdo.listener_event("device_announce", fcc0.endpoint.device)
    elif event == "internal_report":
        fcc0.update_attribute(0x0280, 0)
    else:
        fcc0.endpoint.device.on_remove()
    write.reset_mock()
    await fcc0._respond_external_request(
        1, _external_request(), fcc0._external_generation
    )
    write.assert_not_awaited()
    assert fcc0._external_sample is None
    assert status.get("external_temperature_input") is None


async def test_external_binding_uses_network_order_device_identity(external_writer):
    """Verify external binding uses network order device identity."""
    fcc0, _, write = external_writer
    fcc0.endpoint.device._ieee = t.EUI64.convert("00:11:22:33:44:55:66:77")
    await fcc0.set_external_temperature(source=1)
    packet = write.call_args_list[0].args[0][0xFFF2]
    assert packet[14:22] == bytes.fromhex("0011223344556677")


async def test_external_payload_counter_wraps(external_writer):
    """Verify external payload counter wraps."""
    fcc0, _, write = external_writer
    fcc0._external_counter = 255
    await fcc0.set_external_temperature(source=1)
    assert [call.args[0][0xFFF2][4] for call in write.call_args_list[:2]] == [255, 0]


async def test_internal_source_is_confirmed_even_when_unbind_fails(external_writer):
    """Verify internal source is confirmed even when unbind fails."""
    fcc0, status, write = external_writer
    fcc0.update_attribute(0x0280, 1)
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    write.side_effect = [success, failure]
    result = await fcc0.set_external_temperature(source=0)
    assert result[0][0].status == foundation.Status.FAILURE
    assert fcc0.get(0x0280) == 0
    write.reset_mock()
    result = await status.write_attributes({"external_temperature_input": 2100})
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    write.assert_not_awaited()


async def test_external_request_failure_can_be_retried(external_writer):
    """Verify external request failure can be retried."""
    fcc0, _, write = external_writer
    await fcc0.set_external_temperature(source=1, centidegrees=2150)
    write.reset_mock()
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    write.side_effect = [failure, success]
    request = _external_request()
    await fcc0._respond_external_request(1, request, fcc0._external_generation)
    await fcc0._respond_external_request(1, request, fcc0._external_generation)
    assert write.await_count == 2


async def test_external_sample_rebinds_after_runtime_restart(external_writer):
    """Verify external sample rebinds after runtime restart."""
    fcc0, status, write = external_writer
    # Cached source from HA persistence is not proof of an armed runtime context.
    fcc0.update_attribute(0x0280, 1)
    assert fcc0._external_active is False
    await status.write_attributes({"external_temperature_input": 2100})
    assert write.await_count == 5
    assert status.get("external_temperature_input") == 2100


async def test_external_low_level_wire_types_and_manufacturer(status_clusters):
    """Verify external low level wire types and manufacturer."""

    fcc0, _ = status_clusters
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with patch.object(
        fcc0, "_write_attributes", new_callable=AsyncMock, return_value=success
    ) as write:
        result = await fcc0.set_external_temperature(source=1, centidegrees=2150)
    assert result[0][0].status == foundation.Status.SUCCESS
    records = [call.args[0][0] for call in write.call_args_list]
    assert [r.attrid for r in records] == [0xFFF2, 0xFFF2, 0x0280, 0xFFF2, 0xFFF2]
    assert [r.value.type for r in records] == [
        foundation.DataTypeId.octstr,
        foundation.DataTypeId.octstr,
        foundation.DataTypeId.uint8,
        foundation.DataTypeId.octstr,
        foundation.DataTypeId.octstr,
    ]
    assert all(call.kwargs["manufacturer"] == 4447 for call in write.call_args_list)


async def test_external_cancelled_transaction_drops_context(external_writer):
    """Verify external cancelled transaction drops context."""

    fcc0, status, write = external_writer
    write.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await fcc0.set_external_temperature(source=1, centidegrees=2150)
    assert fcc0._external_sample is None
    assert not fcc0._external_active
    assert status.get("external_temperature_input") is None


async def test_external_cleanup_does_not_cancel_other_cluster_tasks(status_clusters):
    """Verify external cleanup does not cancel other cluster tasks."""

    fcc0, _ = status_clusters
    other = AqaraW600FCC0(fcc0.endpoint)
    ready = asyncio.Event()
    other.create_catching_task(ready.wait())
    tasks = tuple(other._tasks)
    fcc0._close_external()
    await asyncio.sleep(0)
    assert tasks and all(not task.cancelled() and not task.done() for task in tasks)
    ready.set()
    await asyncio.gather(*tasks)
    other._close_external()


def test_external_input_is_created_without_fictitious_initial_temperature(
    status_clusters,
):
    """Verify external input is created without fictitious initial temperature."""

    fcc0, status = status_clusters
    entity = NumberConfigurationEntity(
        endpoint=SimpleNamespace(id=1),
        device=SimpleNamespace(ieee=fcc0.endpoint.device.ieee),
        cluster=status,
        from_quirk=True,
        attribute_name="external_temperature_input",
        multiplier=0.01,
        min_value=-40,
        max_value=125,
        step=0.01,
        unique_id_suffix="w600-external-temperature-input",
    )
    # Quirk-discovered controls are supported even with an empty cache.
    assert entity.is_supported()
    assert entity.native_value is None
    status.update_attribute(0x0007, 2165)
    assert entity.native_value == pytest.approx(21.65)
    status.update_attribute(0x0007, None)
    assert entity.is_supported()
    assert entity.native_value is None


async def test_zha_external_input_rejection_has_attribute_context(status_clusters):
    """Verify zha external input rejection has attribute context."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0280, 0)
    with pytest.raises(ZHAException, match="external_temperature_input"):
        await write_attributes_safe(status, {"external_temperature_input": 2900})


async def test_failed_external_selection_then_29_degree_input_has_no_format_crash(
    status_clusters, caplog
):
    """Verify failed external selection then 29 degree input has no format crash."""

    fcc0, status = status_clusters
    fcc0.update_attribute(0x0280, 0)
    common = {
        "endpoint": SimpleNamespace(id=1),
        "device": SimpleNamespace(ieee=fcc0.endpoint.device.ieee),
        "from_quirk": True,
    }
    select = ZCLEnumSelectEntity(
        cluster=fcc0,
        attribute_name="temperature_source",
        enum=W600TemperatureSource,
        **common,
    )
    number = NumberConfigurationEntity(
        cluster=status,
        attribute_name="external_temperature_input",
        multiplier=0.01,
        **common,
    )
    with patch.object(
        CustomCluster,
        "write_attributes",
        new_callable=AsyncMock,
        side_effect=zigpy.exceptions.DeliveryError("ZIGBEE_DELIVERY_FAILED: 3074"),
    ) as write:
        with pytest.raises(zigpy.exceptions.DeliveryError, match="3074"):
            await select.async_select_option("External")
        with pytest.raises(ZHAException, match="external_temperature_input=2900"):
            await number.async_set_native_value(29)
    assert write.await_count == 1
    assert status.get("external_temperature_input") is None
    assert fcc0.get(0x0280) == 0
    assert not fcc0._external_active
    assert "attribute=0xfff2, action=2, slot=20" in caplog.text


@pytest.mark.parametrize(
    "operation", ["source", "schedule", "table_missing", "table_write"]
)
async def test_zha_service_write_failures_identify_requested_attribute(
    status_clusters, operation
):
    """Verify zha service write failures identify requested attribute."""

    fcc0, status = status_clusters
    failure = [[foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE)]]
    if operation == "source":
        cluster, attributes, name = (
            fcc0,
            {"temperature_source": 1},
            "temperature_source",
        )
    elif operation == "schedule":
        cluster, attributes, name = status, {"schedule_control": 1}, "schedule_control"
    else:
        cluster, attributes, name = (
            status,
            {"preset_home_temperature": 2150},
            "preset_home_temperature",
        )
        if operation == "table_write":
            fcc0.update_attribute(0x0317, PRESET_TABLE)
    with (
        patch.object(
            CustomCluster,
            "write_attributes",
            new_callable=AsyncMock,
            return_value=failure,
        ),
        patch.object(
            fcc0, "read_attributes", new_callable=AsyncMock, return_value=({}, {})
        ),
        pytest.raises(ZHAException, match=name),
    ):
        await write_attributes_safe(cluster, attributes)


async def test_cached_heartbeat_restores_derived_status_without_radio(status_clusters):
    """Verify cached heartbeat restores derived status without radio."""

    fcc0, status = status_clusters
    # Simulate restored vendor cache: parent cache write bypasses the quirk hook.
    payload = bytes.fromhex("0d23301c0000172100001820649c41080000000000000000")
    CustomCluster._update_attribute(fcc0, 0x00F7, payload)
    assert status._attr_cache.get(0) is None
    with patch.object(fcc0.endpoint, "request", new_callable=AsyncMock) as request:
        result, _ = await status.read_attributes(
            ["battery_percentage", "window_open", "valve_alarm"]
        )
    request.assert_not_awaited()
    assert result["battery_percentage"] == 100
    assert result["window_open"] == 0
    assert result["valve_alarm"] == 0
    assert status.get("battery_millivolts") is None
    assert status.get("external_temperature_problem") == 255
    assert fcc0._external_sample is None
    assert not fcc0._external_active


def test_lazy_status_get_restores_late_vendor_cache_once(status_clusters):
    """Verify lazy status get restores late vendor cache once."""

    fcc0, status = status_clusters
    assert status.get("battery_percentage") is None
    CustomCluster._update_attribute(fcc0, 0x00F7, bytes.fromhex("182064"))
    CustomCluster._update_attribute(fcc0, 0x0311, 255)
    with patch.object(
        status, "update_attribute", wraps=status.update_attribute
    ) as update:
        assert status.get("battery_percentage") == 100
        count = update.call_count
        assert status.get("device_state_raw") == 255
        assert status.get("battery_millivolts") is None
        assert status.get("battery_percentage") == 100
        assert update.call_count == count


def test_cached_status_restore_does_not_rearm_external_source(status_clusters):
    """Verify cached status restore does not rearm external source."""

    fcc0, status = status_clusters
    CustomCluster._update_attribute(fcc0, 0x0280, 1)
    CustomCluster._update_attribute(fcc0, 0x0317, PRESET_TABLE)
    CustomCluster._update_attribute(fcc0, 0x027E, 2)
    assert status.get("preset_home_temperature") == 2600
    assert status.get("external_temperature_problem") == 1
    assert status.get("external_temperature_input") is None
    assert fcc0._external_sample is None
    assert not fcc0._external_active


@pytest.mark.parametrize("payload", [None, "invalid", b"", b"\x00" * 20, b"\x00" * 22])
async def test_external_request_rejects_invalid_type_and_length(
    external_writer, payload
):
    """Ignore malformed requests without sending or recording a response."""
    fcc0, _, write = external_writer
    fcc0.update_attribute(w600.ATTR_TEMPERATURE_SOURCE, 1)
    fcc0._external_sample = (2150, w600.time.monotonic())
    await fcc0._respond_external_request(1, payload, fcc0._external_generation)
    write.assert_not_awaited()
    assert not fcc0._external_requests


def test_status_restore_blocks_recursive_cache_access(status_clusters):
    """Allow status reads during restoration without recursively replaying caches."""
    fcc0, status = status_clusters
    CustomCluster._update_attribute(fcc0, w600.ATTR_HEARTBEAT, bytes.fromhex("182064"))
    original = fcc0._sync_status_attribute

    def restore_with_nested_read(attrid, value):
        assert status.get("battery_percentage") is None
        original(attrid, value)

    with patch.object(
        fcc0, "_sync_status_attribute", side_effect=restore_with_nested_read
    ) as sync:
        assert status.get("battery_percentage") == 100
    sync.assert_called_once_with(w600.ATTR_HEARTBEAT, bytes.fromhex("182064"))
    assert status._restoring_status is False


def test_status_without_vendor_cluster_preserves_unknown(status_clusters):
    """Keep derived telemetry unknown when its vendor cluster is unavailable."""
    fcc0, status = status_clusters
    with patch.object(fcc0.endpoint, "aqara_w600_fcc0", None):
        assert status.get("battery_percentage") is None
        assert status.get("window_open") == 255
    assert not getattr(status, "_restoring_status", False)


async def test_schedule_read_fetches_missing_vendor_state(status_clusters):
    """Read the real vendor attribute before exposing an uncached schedule flag."""
    fcc0, status = status_clusters

    async def report_schedule(*args, **kwargs):
        fcc0.update_attribute(w600.ATTR_SCHEDULE_ENABLED, 1)
        return {w600.ATTR_SCHEDULE_ENABLED: 1}, {}

    with patch.object(fcc0, "read_attributes", side_effect=report_schedule) as read:
        result, failures = await status.read_attributes(["schedule_control"])
    read.assert_awaited_once_with(
        [w600.ATTR_SCHEDULE_ENABLED],
        manufacturer=AQARA_MANUFACTURER_CODE,
        allow_cache=False,
    )
    assert result == {"schedule_control": 1}
    assert not failures


@pytest.mark.parametrize("error", [TimeoutError, zigpy.exceptions.DeliveryError])
async def test_profile_read_failure_preserves_cached_manual_state(
    status_clusters, error
):
    """Retain the last profile when a forced refresh cannot reach the device."""
    fcc0, status = status_clusters
    fcc0.update_attribute(w600.ATTR_DEVICE_STATE, 255)
    with patch.object(fcc0, "read_attributes", side_effect=error("read failed")):
        result, failures = await status.read_attributes(["device_state_raw"])
    assert result == {"device_state_raw": 255}
    assert not failures
    assert fcc0.get(w600.ATTR_DEVICE_STATE) == 255


async def test_profile_temperature_read_populates_all_profile_values(status_clusters):
    """Decode a successfully fetched table into all five local temperature fields."""
    fcc0, status = status_clusters
    with patch.object(
        fcc0,
        "read_attributes",
        new_callable=AsyncMock,
        return_value=({w600.ATTR_PRESET_TEMPERATURE_TABLE: PRESET_TABLE}, {}),
    ) as read:
        result, failures = await status.read_attributes(["preset_home_temperature"])
    read.assert_awaited_once_with(
        [w600.ATTR_PRESET_TEMPERATURE_TABLE],
        manufacturer=AQARA_MANUFACTURER_CODE,
        allow_cache=False,
    )
    assert result == {"preset_home_temperature": 2600}
    assert not failures
    assert fcc0.get(w600.ATTR_PRESET_TEMPERATURE_TABLE) == PRESET_TABLE
    assert [status.get(0x0010 + i) for i in range(5)] == [2600, 1800, 2000, 1000, 2400]


async def test_device_removal_cancels_pending_external_task(external_writer):
    """Cancel owned tasks and discard external state when removing the device."""
    fcc0, status, write = external_writer
    fcc0.update_attribute(w600.ATTR_TEMPERATURE_SOURCE, 1)
    fcc0._external_sample = (2150, w600.time.monotonic())
    status.update_attribute(0x0007, 2150)
    task = asyncio.create_task(asyncio.Event().wait())
    fcc0._tasks.add(task)
    await asyncio.sleep(0)
    fcc0.endpoint.device.on_remove()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
    assert fcc0._external_sample is None
    assert status.get("external_temperature_input") is None
    write.assert_not_awaited()


async def test_stale_external_write_never_reaches_transport(external_writer):
    """Reject an obsolete transaction before issuing any radio write."""
    fcc0, _, write = external_writer
    generation = fcc0._external_generation
    fcc0._reset_external()
    with pytest.raises(w600._ExternalTransactionFailed):
        await fcc0._external_write(w600.ATTR_TEMPERATURE_SOURCE, 1, generation)
    write.assert_not_awaited()


@pytest.mark.parametrize("kwargs", [{"source": 2}, {}])
async def test_invalid_external_operation_has_no_side_effects(external_writer, kwargs):
    """Reject unsupported sources and empty operations with an identified error."""
    fcc0, _, write = external_writer
    generation = fcc0._external_generation
    result = await fcc0.set_external_temperature(**kwargs)
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    assert result[0][0].attrid is not None
    assert fcc0._external_generation == generation
    assert fcc0._external_sample is None
    write.assert_not_awaited()


async def test_external_request_history_evicts_oldest_entry(external_writer):
    """Bound deduplication storage while responding to a distinct fresh request."""
    fcc0, _, write = external_writer
    old_payload = _external_request(counter=7)
    new_payload = _external_request(counter=8)
    with patch.object(w600.time, "monotonic", return_value=100):
        await fcc0.set_external_temperature(source=1, centidegrees=2150)
        write.reset_mock()
        fcc0._external_requests = {(tsn, old_payload): 100 for tsn in range(256)}
        await fcc0._respond_external_request(0, new_payload, fcc0._external_generation)
        await fcc0._respond_external_request(0, new_payload, fcc0._external_generation)
    assert len(fcc0._external_requests) == 256
    assert (0, old_payload) not in fcc0._external_requests
    assert (1, old_payload) in fcc0._external_requests
    assert (0, new_payload) in fcc0._external_requests
    write.assert_awaited_once()


async def test_invalid_schedule_flag_never_writes(external_writer):
    """Reject an invalid schedule value without clearing hold or writing FCC0."""
    fcc0, _, write = external_writer
    with patch.object(
        fcc0.endpoint.thermostat, "write_attributes", new_callable=AsyncMock
    ) as thermostat_write:
        result = await fcc0.set_schedule_enabled(2)
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    assert result[0][0].attrid == w600.ATTR_SCHEDULE_ENABLED
    thermostat_write.assert_not_awaited()
    write.assert_not_awaited()


@pytest.mark.parametrize(
    "attributes, attrid",
    [
        ({"temperature_source": 1, "child_lock": 1}, w600.ATTR_TEMPERATURE_SOURCE),
        ({"device_state": 1, "child_lock": 1}, w600.ATTR_DEVICE_STATE),
        ({"device_state": 4}, w600.ATTR_DEVICE_STATE),
    ],
)
async def test_invalid_composite_writes_are_atomic(external_writer, attributes, attrid):
    """Reject invalid profiles and mixed control writes without partial changes."""
    fcc0, _, write = external_writer
    with patch.object(
        fcc0.endpoint.thermostat, "write_attributes", new_callable=AsyncMock
    ) as thermostat_write:
        result = await fcc0.write_attributes(attributes)
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    assert result[0][0].attrid == attrid
    thermostat_write.assert_not_awaited()
    write.assert_not_awaited()


async def test_manual_selection_without_target_fails_without_writes(external_writer):
    """Avoid writing Manual or inventing a target when no setpoint is known."""
    fcc0, _, write = external_writer
    assert fcc0.endpoint.thermostat.get(w600.ATTR_OCCUPIED_HEATING_SETPOINT) is None
    with patch.object(
        fcc0.endpoint.thermostat, "write_attributes", new_callable=AsyncMock
    ) as thermostat_write:
        result = await fcc0.write_attributes({"device_state": 255})
    assert result[0][0].status == foundation.Status.FAILURE
    assert result[0][0].attrid == w600.ATTR_DEVICE_STATE
    thermostat_write.assert_not_awaited()
    write.assert_not_awaited()
