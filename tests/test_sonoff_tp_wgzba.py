"""Tests for the SONOFF TP-WGZBA thermostat quirk."""

from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import DataTypeId

import zhaquirks
from zhaquirks.sonoff import tp_wgzba
from zhaquirks.sonoff.tp_wgzba import (
    SONOFF_PRIVATE_CLUSTER_ID,
    SonoffTPWGZBAPrivateCluster,
    SonoffTPWGZBAThermostatCluster,
    TPWGZBASystemMode,
)

zhaquirks.setup()


@pytest.fixture
def tp_wgzba_device(zigpy_device_from_v2_quirk):
    """Create a TP-WGZBA device with both custom clusters."""
    return zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )


def test_tp_wgzba_replaces_clusters_and_exposes_entities(zigpy_device_from_v2_quirk):
    """Test the thermostat and private clusters plus representative entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )

    endpoint = device.endpoints[1]
    assert isinstance(endpoint.thermostat, SonoffTPWGZBAThermostatCluster)
    assert isinstance(endpoint.sonoff_private, SonoffTPWGZBAPrivateCluster)

    entry = DEVICE_REGISTRY.match_entry(device)
    metadata_suffixes = {
        metadata.resolved_unique_id_suffix
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    assert {
        "tp_wgzba_ui_system_mode",
        "device_work_mode",
        "weekly_schedule_ui_apply",
        "temporary_mode_ui_apply",
    } <= metadata_suffixes


def test_tp_wgzba_system_mode_mapping():
    """Test the device schedule/manual modes map to HA thermostat modes."""
    assert (
        SonoffTPWGZBAThermostatCluster._system_mode_to_ha(TPWGZBASystemMode.Schedule)
        == Thermostat.SystemMode.Heat
    )
    assert (
        SonoffTPWGZBAThermostatCluster._system_mode_to_device(
            Thermostat.SystemMode.Heat
        )
        == TPWGZBASystemMode.Manual
    )


async def test_tp_wgzba_failed_mode_write_does_not_update_cache(
    zigpy_device_from_v2_quirk,
):
    """Test failed device writes do not report or cache a successful mode change."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat
    private_cluster = device.endpoints[1].sonoff_private
    failure = [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.FAILURE,
                Thermostat.AttributeDefs.system_mode.id,
            )
        ]
    ]

    with mock.patch.object(
        thermostat_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=failure),
    ):
        result = await private_cluster.write_attributes(
            {
                private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.name: (
                    TPWGZBASystemMode.Manual
                )
            }
        )

    assert result == failure
    assert (
        private_cluster.get(private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.name)
        is None
    )


async def test_tp_wgzba_reads_real_system_mode_from_device(
    zigpy_device_from_v2_quirk,
):
    """Test mode reads use the raw thermostat value before the local fallback."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat
    private_cluster = device.endpoints[1].sonoff_private
    mode_attribute = Thermostat.AttributeDefs.system_mode
    record = foundation.ReadAttributeRecord(
        attrid=mode_attribute.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(
            type=mode_attribute.zcl_type,
            value=TPWGZBASystemMode.Manual,
        ),
    )

    with mock.patch.object(
        thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=([record],)),
    ):
        mode = await private_cluster._read_real_system_mode()

    assert mode == TPWGZBASystemMode.Manual


def test_tp_wgzba_schedule_response_updates_ui_values(zigpy_device_from_v2_quirk):
    """Test standard weekly schedule responses populate the UI cache."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private
    response = SimpleNamespace(
        day_of_week_for_sequence=0x04,
        num_transitions_for_sequence=2,
        values=(
            SimpleNamespace(transition_time=30, heat_setpoint=2100),
            SimpleNamespace(transition_time=90, heat_setpoint=2300),
        ),
    )

    private_cluster._update_weekly_schedule_ui_from_rsp(response)

    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_day.name)
        == 2
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_time1.name)
        == 0
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_time2.name)
        == 90
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_temp1.name)
        == 2100
    )
    assert (
        private_cluster.get(private_cluster.AttributeDefs.weekly_schedule_ui_temp2.name)
        == 2300
    )


def test_tp_wgzba_schedule_rejects_non_contiguous_slots(zigpy_device_from_v2_quirk):
    """Test a non-NULL schedule slot cannot follow a NULL slot."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private

    with pytest.raises(ValueError, match="after NULL"):
        private_cluster._validate_weekly_schedule_ui_updates(
            {
                private_cluster._WEEKLY_TIME_ATTRS[1].id: 0xFFFF,
                private_cluster._WEEKLY_TIME_ATTRS[2].id: 90,
            }
        )


async def test_tp_wgzba_weekly_schedule_command_encoding(
    zigpy_device_from_v2_quirk,
):
    """Test weekly schedule writes encode day, mode, and temperature values."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    thermostat_cluster = device.endpoints[1].thermostat

    with mock.patch.object(
        thermostat_cluster, "command", mock.AsyncMock(return_value="sent")
    ) as command:
        result = await thermostat_cluster.set_weekly_schedule_heat(
            0x02, [(0, 20.0), (30, 21.0)]
        )

    assert result == "sent"
    command.assert_awaited_once_with(
        thermostat_cluster.ServerCommandDefs.set_weekly_schedule.id,
        2,
        thermostat_cluster.SeqDayOfWeek(0x02),
        thermostat_cluster.SeqMode.Heat,
        [0, 2000, 30, 2100],
        manufacturer=None,
        expect_reply=True,
        tsn=None,
    )


async def test_tp_wgzba_temporary_mode_ui_command(zigpy_device_from_v2_quirk):
    """Test the temporary mode UI command dispatches a boost request."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="TP-WGZBA",
        cluster_ids={
            1: {
                Thermostat.cluster_id: ClusterType.Server,
                SONOFF_PRIVATE_CLUSTER_ID: ClusterType.Server,
            }
        },
    )
    private_cluster = device.endpoints[1].sonoff_private
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_action.id,
        1,
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_duration_minutes.id,
        10,
    )

    with mock.patch.object(
        private_cluster, "set_boost", mock.AsyncMock(return_value="boosted")
    ) as set_boost:
        result = await private_cluster.command(
            private_cluster.ServerCommandDefs.temporary_mode_ui_apply.id
        )

    assert result == "boosted"
    set_boost.assert_awaited_once_with(600, 30.0)


def test_tp_wgzba_payload_codecs():
    """Test the raw and uint8-array payload codecs and validation errors."""
    raw, remainder = tp_wgzba.RawBytes.deserialize(b"\x01\x02")
    assert raw == b"\x01\x02"
    assert remainder == b""
    assert tp_wgzba.RawBytes(None).serialize() == b""

    encoded = tp_wgzba.Uint8ArrayPayload(b"\x01\x02").serialize()
    payload, remainder = tp_wgzba.Uint8ArrayPayload.deserialize(encoded + b"tail")
    assert payload == b"\x01\x02"
    assert remainder == b"tail"

    with pytest.raises(ValueError, match="too short"):
        tp_wgzba.Uint8ArrayPayload.deserialize(b"\x20")
    with pytest.raises(ValueError, match="element type"):
        tp_wgzba.Uint8ArrayPayload.deserialize(b"\x21\x00\x00")
    with pytest.raises(ValueError, match="declared"):
        tp_wgzba.Uint8ArrayPayload.deserialize(b"\x20\x02\x00\x01")

    type_value = foundation.TypeValue(type=DataTypeId.uint8, value=t.uint8_t(1))
    assert tp_wgzba.RawBytes(type_value) == b"\x20\x01"
    assert (
        tp_wgzba.RawBytes(foundation.ZCLStructure([type_value])) == b"\x01\x00\x20\x01"
    )
    assert tp_wgzba.RawBytes([type_value]) == b"\x01\x00\x20\x01"

    array = foundation.Array(
        type=DataTypeId.uint8,
        value=t.LVList[t.uint8_t, t.uint16_t]([t.uint8_t(1), t.uint8_t(2)]),
    )
    assert tp_wgzba.Uint8ArrayPayload(array) == b"\x01\x02"
    with pytest.raises(ValueError, match="Expected uint8"):
        tp_wgzba.Uint8ArrayPayload(foundation.Array(type=DataTypeId.uint16, value=[]))


def test_tp_wgzba_private_payload_codecs(tp_wgzba_device):
    """Test packed diagnostic and remote-temperature payload conversions."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private

    threshold = private_cluster._encode_threshold_pair(-25, 125)
    assert private_cluster._decode_threshold_pair(threshold) == (-25, 125)
    assert private_cluster._decode_threshold_pair(None) == (-200, 200)

    period = private_cluster._encode_time_period(90, 1230)
    assert private_cluster._decode_time_period(period) == (90, 1230)
    assert private_cluster._decode_time_period(b"bad") == (0, 0)

    assert private_cluster._decode_relay_output_type(0xFF) == (1, 1)
    assert private_cluster._encode_relay_output_type(1, 0) == 1

    linkage = private_cluster._encode_remote_attribute_linkage(
        tp_wgzba.TemperatureSensorSelect.external, 2150
    )
    assert private_cluster._decode_remote_attribute_linkage(linkage) == (
        tp_wgzba.TemperatureSensorSelect.external,
        2150,
    )
    assert private_cluster._decode_remote_attribute_linkage(b"\x00\x00\x00") == (
        tp_wgzba.TemperatureSensorSelect.internal,
        0,
    )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"\x00\x01\x01", tp_wgzba.HvacMessageOpenWindowState.open),
        (b"\x00\x01\x00", tp_wgzba.HvacMessageOpenWindowState.closed),
        (b"\x20\x03\x00\x00\x01\x01", tp_wgzba.HvacMessageOpenWindowState.open),
        (b"invalid", tp_wgzba.HvacMessageOpenWindowState.closed),
    ],
)
def test_tp_wgzba_diagnostic_decoders(tp_wgzba_device, payload, expected):
    """Test HVAC, NTC, and temporary-mode diagnostic state decoders."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private
    assert private_cluster._decode_hvac_message_open_window_state(payload) == expected
    assert (
        private_cluster._format_ntc_current_temperature_display(
            2150, tp_wgzba.NtcCurrentTemperatureState.normal
        )
        == "21.50 C"
    )
    assert (
        private_cluster._format_ntc_current_temperature_display(
            None, tp_wgzba.NtcCurrentTemperatureState.idle
        )
        == "Not Connected"
    )

    assert private_cluster._decode_ntc_current_temperature(-32768) == (
        None,
        tp_wgzba.NtcCurrentTemperatureState.idle,
    )
    assert private_cluster._decode_ntc_current_temperature(2150) == (
        2150,
        tp_wgzba.NtcCurrentTemperatureState.normal,
    )
    assert (
        private_cluster._decode_temporary_temperature_mode_state(
            tp_wgzba.TemporaryTemperatureModeSettings.Boost
        )
        == tp_wgzba.TemporaryTemperatureModeState.Boost
    )


def test_tp_wgzba_private_attribute_mirrors(tp_wgzba_device):
    """Test raw private attributes update their virtual diagnostic mirrors."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temperature_control_threshold.id,
        private_cluster._encode_threshold_pair(-10, 80),
    )
    assert private_cluster.get("temperature_control_threshold_low") == -10
    assert private_cluster.get("temperature_control_threshold_high") == 80

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.radar_do_not_disturb_period.id,
        private_cluster._encode_time_period(61, 119),
    )
    assert private_cluster.get("radar_do_not_disturb_start_minute") == 60
    assert private_cluster.get("radar_do_not_disturb_end_minute") == 120

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.relay_output_type_bitmap.id, 2
    )
    assert private_cluster.get("relay_output_type_relay1") == 0
    assert private_cluster.get("relay_output_type_relay2") == 1

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.remote_attribute_linkage.id,
        private_cluster._encode_remote_attribute_linkage(
            tp_wgzba.TemperatureSensorSelect.external_2, 9990
        ),
    )
    assert private_cluster.get("temperature_sensor_select") == (
        tp_wgzba.TemperatureSensorSelect.external_2
    )
    assert private_cluster.get("external_temperature_sensor") is True
    assert private_cluster.get("external_temperature_input") == 9990

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.current_ntc_temperature_raw.id, 2150
    )
    assert private_cluster.get("current_ntc_temperature") == 2150
    assert private_cluster.get("current_ntc_temperature_display") == "21.50 C"


def test_tp_wgzba_private_schedule_defaults_and_helpers(tp_wgzba_device):
    """Test schedule defaults, time snapping, group validation, and UI conversion."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private

    assert private_cluster._normalize_weekly_schedule_ui_minute(14) == 0
    assert private_cluster._normalize_weekly_schedule_ui_minute(16) == 30
    assert private_cluster._normalize_weekly_schedule_ui_minute(1439) == 1410
    assert private_cluster._normalize_weekly_schedule_ui_minute(0xFFFF) == 0xFFFF
    assert private_cluster._weekly_schedule_ui_day_to_standard_mask(2) == 4
    assert private_cluster._weekly_schedule_standard_mask_to_ui_day(0x20) == 5
    assert private_cluster._weekly_schedule_standard_mask_to_ui_day(0) == 0

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.weekly_schedule_ui_time2.id, 90
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.weekly_schedule_ui_temp2.id, 2150
    )
    day, transitions = private_cluster._weekly_schedule_ui_values()
    assert day == 0
    assert transitions == [(0, 500), (90, 2150)]

    assert private_cluster._group(0) == 0
    with pytest.raises(ValueError, match="group_id"):
        private_cluster._group(3)


def test_tp_wgzba_private_mode_ui_values(tp_wgzba_device):
    """Test temporary-mode defaults and the device work-mode mirror."""
    endpoint = tp_wgzba_device.endpoints[1]
    private_cluster = endpoint.sonoff_private
    endpoint.thermostat._update_attribute(
        Thermostat.AttributeDefs.occupied_heating_setpoint.id, 2150
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_action.id,
        tp_wgzba.TemporaryModeUiAction.Timer,
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_duration_minutes.id, 0
    )
    private_cluster._update_attribute(
        private_cluster.AttributeDefs.temporary_mode_ui_target_temperature.id, 3100
    )

    assert private_cluster._temporary_mode_ui_values() == (
        tp_wgzba.TemporaryModeUiAction.Timer,
        1,
        3000,
    )
    private_cluster._update_device_work_mode_from_system(TPWGZBASystemMode.Manual)
    assert (
        private_cluster.get("device_work_mode") == tp_wgzba.TPWGZBADeviceWorkMode.Manual
    )


async def test_tp_wgzba_temporary_mode_payloads(tp_wgzba_device):
    """Test exit, boost, and timer commands encode the vendor payload correctly."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private

    with mock.patch.object(
        private_cluster, "command", mock.AsyncMock(return_value="sent")
    ) as command:
        assert await private_cluster.exit_temporary_mode() == "sent"
        assert await private_cluster.set_boost(60, 21.5) == "sent"
        assert await private_cluster.set_timer(120, 22) == "sent"

    assert command.await_args_list == [
        mock.call(0x11, b"\x00"),
        mock.call(0x11, b"\x01\x3c\x00\x00\x00\x66\x08"),
        mock.call(0x11, b"\x02\x78\x00\x00\x00\x98\x08"),
    ]
    with pytest.raises(ValueError, match="duration_seconds"):
        await private_cluster.set_timer(86400, 20)


async def test_tp_wgzba_thermostat_schedule_commands(tp_wgzba_device):
    """Test schedule group switching, reading, clearing, and validation."""
    endpoint = tp_wgzba_device.endpoints[1]
    thermostat_cluster = endpoint.thermostat
    private_cluster = endpoint.sonoff_private

    with (
        mock.patch.object(
            private_cluster,
            "set_active_schedule_group",
            mock.AsyncMock(return_value="grouped"),
        ) as set_group,
        mock.patch.object(
            thermostat_cluster, "command", mock.AsyncMock(return_value="sent")
        ) as command,
    ):
        assert (
            await thermostat_cluster.set_weekly_schedule_heat_for_group(
                1, 0x04, [(0, 2000), (60, 21.0)]
            )
            == "sent"
        )
        assert await thermostat_cluster.get_weekly_schedule_heat(0x04) == "sent"
        assert await thermostat_cluster.clear_weekly_schedule_current_group() == "sent"

    set_group.assert_awaited_once_with(1)
    assert command.await_count == 3

    with pytest.raises(ValueError, match="day_of_week_mask"):
        await thermostat_cluster.get_weekly_schedule_heat(0)
    with pytest.raises(ValueError, match="one day"):
        await thermostat_cluster.get_weekly_schedule_heat(0x03)
    with pytest.raises(ValueError, match="first transition"):
        await thermostat_cluster.set_weekly_schedule_heat(1, [(30, 20)])
    with pytest.raises(ValueError, match="strictly increasing"):
        await thermostat_cluster.set_weekly_schedule_heat(1, [(0, 20), (0, 21)])
    with pytest.raises(ValueError, match="target temperature"):
        await thermostat_cluster.set_weekly_schedule_heat(1, [(0, 4)])


async def test_tp_wgzba_thermostat_mode_and_reporting_paths(tp_wgzba_device):
    """Test thermostat mode normalization, successful writes, and reporting skips."""
    endpoint = tp_wgzba_device.endpoints[1]
    thermostat_cluster = endpoint.thermostat
    private_cluster = endpoint.sonoff_private
    success = [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS,
                Thermostat.AttributeDefs.system_mode.id,
            )
        ]
    ]

    with mock.patch.object(
        thermostat_cluster, "write_attributes_raw", mock.AsyncMock(return_value=success)
    ):
        result = await thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Heat}
        )
    assert result == success
    assert thermostat_cluster.get(Thermostat.AttributeDefs.system_mode.name) == (
        Thermostat.SystemMode.Heat
    )
    thermostat_cluster._update_attribute(
        Thermostat.AttributeDefs.system_mode.id, TPWGZBASystemMode.Manual
    )
    assert private_cluster.get("tp_wgzba_ui_system_mode") == TPWGZBASystemMode.Manual

    local_config = {
        Thermostat.AttributeDefs.local_temperature: mock.sentinel.reporting_config
    }
    assert await thermostat_cluster.configure_reporting_multiple(local_config) == {
        Thermostat.AttributeDefs.local_temperature: foundation.Status.SUCCESS
    }

    with mock.patch.object(
        tp_wgzba.CustomCluster,
        "configure_reporting_multiple",
        mock.AsyncMock(
            return_value={
                Thermostat.AttributeDefs.system_mode: foundation.Status.SUCCESS
            }
        ),
    ) as configure_reporting:
        result = await thermostat_cluster.configure_reporting_multiple(
            {
                Thermostat.AttributeDefs.local_temperature: mock.sentinel.config,
                Thermostat.AttributeDefs.system_mode: mock.sentinel.config,
            }
        )
    assert (
        result[Thermostat.AttributeDefs.local_temperature] == foundation.Status.SUCCESS
    )
    configure_reporting.assert_awaited_once()


async def test_tp_wgzba_private_reporting_and_group_paths(tp_wgzba_device):
    """Test virtual reporting mappings and active schedule group writes."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private
    config = {
        private_cluster.AttributeDefs.current_ntc_temperature: mock.sentinel.config,
        private_cluster.AttributeDefs.current_ntc_temperature_state: mock.sentinel.config,
        private_cluster.AttributeDefs.device_work_mode: mock.sentinel.config,
        private_cluster.AttributeDefs.hvac_message_open_window_state: mock.sentinel.config,
        private_cluster.AttributeDefs.current_ntc_temperature_raw: mock.sentinel.config,
    }
    result_from_parent = {
        private_cluster.AttributeDefs.current_ntc_temperature_raw: foundation.Status.SUCCESS,
        private_cluster.AttributeDefs.device_work_mode_source: foundation.Status.SUCCESS,
        private_cluster.AttributeDefs.hvac_message_notification: foundation.Status.SUCCESS,
    }
    with mock.patch.object(
        tp_wgzba.CustomCluster,
        "configure_reporting_multiple",
        mock.AsyncMock(return_value=result_from_parent),
    ):
        result = await private_cluster.configure_reporting_multiple(config)

    assert (
        result[private_cluster.AttributeDefs.current_ntc_temperature]
        == foundation.Status.SUCCESS
    )
    assert (
        result[private_cluster.AttributeDefs.current_ntc_temperature_state]
        == foundation.Status.SUCCESS
    )
    assert (
        result[private_cluster.AttributeDefs.device_work_mode]
        == foundation.Status.SUCCESS
    )
    assert (
        result[private_cluster.AttributeDefs.hvac_message_open_window_state]
        == foundation.Status.SUCCESS
    )
    assert (
        result[private_cluster.AttributeDefs.current_ntc_temperature_raw]
        == foundation.Status.SUCCESS
    )

    with mock.patch.object(
        private_cluster, "write_attributes", mock.AsyncMock(return_value="written")
    ) as write_attributes:
        assert await private_cluster.set_active_schedule_group(2) == "written"
    write_attributes.assert_awaited_once_with(
        {private_cluster.AttributeDefs.weekly_schedule_active_num.id: 2},
        manufacturer=None,
    )


async def test_tp_wgzba_private_virtual_reads(tp_wgzba_device):
    """Test virtual reads proxy raw vendor attributes and synthesize UI records."""
    endpoint = tp_wgzba_device.endpoints[1]
    thermostat_cluster = endpoint.thermostat
    private_cluster = endpoint.sonoff_private
    defs = private_cluster.AttributeDefs
    raw_values = {
        defs.temporary_temperature_mode_settings.id: 0,
        defs.device_work_mode_source.id: 5,
        defs.temperature_control_threshold.id: private_cluster._encode_threshold_pair(
            -10, 80
        ),
        defs.radar_do_not_disturb_period.id: private_cluster._encode_time_period(
            90, 1230
        ),
        defs.screen_night_mode_period.id: private_cluster._encode_time_period(
            120, 1320
        ),
        defs.relay_output_type_bitmap.id: 1,
        defs.remote_attribute_linkage.id: private_cluster._encode_remote_attribute_linkage(
            tp_wgzba.TemperatureSensorSelect.external, 2150
        ),
        defs.hvac_message_notification.id: b"\x00\x01\x01",
        defs.current_ntc_temperature_raw.id: 2150,
    }

    async def read_private_attributes(attributes, **kwargs):
        """Return deterministic raw private-cluster records for this test."""
        records = []
        for attr_id in attributes:
            record = foundation.ReadAttributeRecord(
                attrid=attr_id,
                status=foundation.Status.SUCCESS,
                value=foundation.TypeValue(),
            )
            record.value.value = raw_values.get(attr_id, 0)
            records.append(record)
        return (records,)

    system_mode_record = foundation.ReadAttributeRecord(
        attrid=Thermostat.AttributeDefs.system_mode.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(),
    )
    system_mode_record.value.value = TPWGZBASystemMode.Manual
    with (
        mock.patch.object(
            private_cluster,
            "_read_attributes",
            mock.AsyncMock(side_effect=read_private_attributes),
        ),
        mock.patch.object(
            thermostat_cluster,
            "_read_attributes",
            mock.AsyncMock(return_value=([system_mode_record],)),
        ),
    ):
        result = await private_cluster.read_attributes_raw(
            [
                defs.temporary_temperature_mode_settings.id,
                defs.temporary_temperature_mode_state.id,
                defs.tp_wgzba_ui_system_mode.id,
                defs.device_work_mode.id,
                defs.temporary_mode_ui_action.id,
                defs.temporary_mode_ui_duration_minutes.id,
                defs.temporary_mode_ui_target_temperature.id,
                defs.weekly_schedule_ui_day.id,
                defs.weekly_schedule_ui_transition_count.id,
                defs.weekly_schedule_ui_time2.id,
                defs.weekly_schedule_ui_temp2.id,
                defs.temperature_control_threshold_low.id,
                defs.temperature_control_threshold_high.id,
                defs.radar_do_not_disturb_start_minute.id,
                defs.radar_do_not_disturb_end_minute.id,
                defs.screen_night_mode_start_minute.id,
                defs.screen_night_mode_end_minute.id,
                defs.relay_output_type_relay1.id,
                defs.relay_output_type_relay2.id,
                defs.temperature_sensor_select.id,
                defs.external_temperature_input.id,
                defs.external_temperature_sensor.id,
                defs.hvac_message_open_window_state.id,
                defs.current_ntc_temperature.id,
                defs.current_ntc_temperature_state.id,
                defs.current_ntc_temperature_display.id,
            ]
        )

    records = result[0]
    assert not result[1:] or not result[1]
    values = {record.attrid: record.value.value for record in records}
    assert values[defs.temporary_temperature_mode_state.id] == (
        tp_wgzba.TemporaryTemperatureModeState.Boost
    )
    assert values[defs.tp_wgzba_ui_system_mode.id] == TPWGZBASystemMode.Manual
    assert (
        values[defs.device_work_mode.id]
        == tp_wgzba.TPWGZBADeviceWorkMode.Temporary_Manual
    )
    assert values[defs.temperature_control_threshold_low.id] == -10
    assert values[defs.temperature_control_threshold_high.id] == 80
    assert values[defs.current_ntc_temperature_display.id] == "21.50 C"


async def test_tp_wgzba_private_virtual_writes(tp_wgzba_device):
    """Test virtual writes pack UI values into the vendor attributes."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private
    defs = private_cluster.AttributeDefs
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with mock.patch.object(
        private_cluster, "write_attributes_raw", mock.AsyncMock(return_value=success)
    ) as write_raw:
        result = await private_cluster.write_attributes(
            {
                defs.temporary_mode_ui_action.name: tp_wgzba.TemporaryModeUiAction.Timer,
                defs.temporary_mode_ui_duration_minutes.name: 10,
                defs.temporary_mode_ui_target_temperature.name: 2200,
                defs.weekly_schedule_ui_day.name: 2,
                defs.weekly_schedule_ui_transition_count.name: 2,
                defs.weekly_schedule_ui_time2.name: 90,
                defs.weekly_schedule_ui_temp2.name: 2200,
                defs.external_temperature_sensor.name: True,
                defs.external_temperature_input.name: 2150,
                defs.temperature_control_threshold_low.name: -10,
                defs.temperature_control_threshold_high.name: 80,
                defs.radar_do_not_disturb_start_minute.name: 90,
                defs.radar_do_not_disturb_end_minute.name: 1230,
                defs.screen_night_mode_start_minute.name: 120,
                defs.screen_night_mode_end_minute.name: 1320,
                defs.relay_output_type_relay1.name: 1,
                defs.relay_output_type_relay2.name: 0,
                defs.radar_do_not_disturb_period.name: b"bad",
                defs.screen_night_mode_period.name: b"bad",
                defs.child_lock.name: True,
            }
        )

    assert result
    assert write_raw.await_count >= 8
    assert private_cluster.get(defs.temperature_control_threshold.name) == (
        private_cluster._encode_threshold_pair(-10, 80)
    )
    assert private_cluster.get(defs.relay_output_type_bitmap.name) == 1
    assert private_cluster.get(defs.external_temperature_sensor.name) is True


async def test_tp_wgzba_private_ui_commands(tp_wgzba_device):
    """Test temporary and weekly schedule UI command dispatch."""
    endpoint = tp_wgzba_device.endpoints[1]
    private_cluster = endpoint.sonoff_private
    thermostat_cluster = endpoint.thermostat
    defs = private_cluster.AttributeDefs
    private_cluster._update_attribute(
        defs.temporary_mode_ui_action.id, tp_wgzba.TemporaryModeUiAction.Timer
    )
    private_cluster._update_attribute(defs.temporary_mode_ui_duration_minutes.id, 5)
    private_cluster._update_attribute(
        defs.temporary_mode_ui_target_temperature.id, 2200
    )

    with mock.patch.object(
        private_cluster, "set_timer", mock.AsyncMock(return_value="timer")
    ) as set_timer:
        assert await private_cluster.command(0x80) == "timer"
    set_timer.assert_awaited_once_with(300, 22.0)

    private_cluster._update_attribute(defs.weekly_schedule_ui_time2.id, 60)
    private_cluster._update_attribute(defs.weekly_schedule_ui_temp2.id, 2100)
    private_cluster._update_attribute(defs.weekly_schedule_active_num.id, 1)
    with (
        mock.patch.object(
            thermostat_cluster,
            "set_weekly_schedule_heat_for_group",
            mock.AsyncMock(return_value="applied"),
        ) as apply_schedule,
        mock.patch.object(
            thermostat_cluster,
            "get_weekly_schedule_heat_for_group",
            mock.AsyncMock(return_value=mock.sentinel.response),
        ) as read_schedule,
    ):
        assert await private_cluster.command(0x81) == "applied"
        assert await private_cluster.command(0x82) is mock.sentinel.response

    apply_schedule.assert_awaited_once()
    read_schedule.assert_awaited_once()


def test_tp_wgzba_schedule_validation_and_response_fallback(tp_wgzba_device):
    """Test close schedule slots and flat/alternate response field formats."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private
    with pytest.raises(ValueError, match="at least"):
        private_cluster._validate_weekly_schedule_ui_updates(
            {
                private_cluster._WEEKLY_TIME_ATTRS[1].id: 30,
                private_cluster._WEEKLY_TIME_ATTRS[2].id: 30,
            }
        )

    private_cluster._update_weekly_schedule_ui_from_rsp(
        SimpleNamespace(
            day_of_week_for_sequence=0x01,
            num_transitions_for_sequence=2,
            values=[0, 2000, 90, 2200],
        )
    )
    assert private_cluster.get("weekly_schedule_ui_time2") == 90
    assert private_cluster.get("weekly_schedule_ui_temp2") == 2200

    private_cluster._update_weekly_schedule_ui_from_rsp(
        SimpleNamespace(
            day_of_week_for_sequence=0x02,
            num_transitions_for_sequence=2,
            values=[
                SimpleNamespace(transTime=0, heatSetpoint=2000),
                SimpleNamespace(transTime=120, heatSetpoint=2300),
            ],
        )
    )
    assert private_cluster.get("weekly_schedule_ui_time2") == 120
    private_cluster._update_weekly_schedule_ui_from_rsp(SimpleNamespace())
    private_cluster._update_weekly_schedule_ui_from_rsp(None)


def test_tp_wgzba_remote_linkage_and_mode_edge_cases(tp_wgzba_device):
    """Test malformed remote linkage records and all temporary-mode states."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private
    assert (
        private_cluster._decode_remote_attribute_linkage(
            b"\x01\x02\x00\x02\x01\x03\x01"
        )[0]
        == tp_wgzba.TemperatureSensorSelect.internal
    )
    assert (
        int(
            private_cluster._decode_remote_attribute_linkage(
                b"\x01\x01\x00\x01\x03\x09\x00\x00"
            )[0]
        )
        == 9
    )
    assert private_cluster._decode_remote_attribute_linkage(None) == (
        tp_wgzba.TemperatureSensorSelect.internal,
        0,
    )
    assert (
        private_cluster._decode_temporary_temperature_mode_state(
            tp_wgzba.TemporaryTemperatureModeSettings.Timer
        )
        == tp_wgzba.TemporaryTemperatureModeState.Timer
    )
    assert private_cluster._decode_temporary_temperature_mode_state(99) == (
        tp_wgzba.TemporaryTemperatureModeState.Idle
    )


async def test_tp_wgzba_mode_read_fallbacks(tp_wgzba_device):
    """Test thermostat mode reads fall back to cache and the default schedule mode."""
    endpoint = tp_wgzba_device.endpoints[1]
    thermostat_cluster = endpoint.thermostat
    private_cluster = endpoint.sonoff_private
    failure = foundation.ReadAttributeRecord(
        attrid=Thermostat.AttributeDefs.system_mode.id,
        status=foundation.Status.FAILURE,
        value=foundation.TypeValue(),
    )
    with mock.patch.object(
        thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=([failure],)),
    ):
        assert (
            await private_cluster._read_real_system_mode() == TPWGZBASystemMode.Schedule
        )
        private_cluster._update_attribute(
            private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.id,
            TPWGZBASystemMode.Manual,
        )
        assert (
            await private_cluster._read_real_system_mode() == TPWGZBASystemMode.Manual
        )


def test_tp_wgzba_helper_edge_cases(tp_wgzba_device):
    """Test helper fallbacks and the schedule path without NULL slots."""
    private_cluster = tp_wgzba_device.endpoints[1].sonoff_private

    class Serializable:
        """Provide a serializable value for the raw-byte helper test."""

        def serialize(self):
            """Return the test payload."""
            return b"serialized"

    assert private_cluster._as_bytes(Serializable()) == b"serialized"
    assert private_cluster._as_bytes(object()) is None
    assert private_cluster._first_status([]) == foundation.Status.UNSUPPORTED_ATTRIBUTE

    updates = {
        attr_def.id: index * 30
        for index, attr_def in enumerate(private_cluster._WEEKLY_TIME_ATTRS)
    }
    assert private_cluster._validate_weekly_schedule_ui_updates(updates) == 12

    private_cluster._update_attribute(
        private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.id, None
    )
    private_cluster.endpoint.thermostat._update_attribute(
        Thermostat.AttributeDefs.system_mode.id, TPWGZBASystemMode.Manual
    )
    private_cluster._refresh_device_work_mode()
    assert (
        private_cluster.get("device_work_mode") == tp_wgzba.TPWGZBADeviceWorkMode.Manual
    )


async def test_tp_wgzba_private_ui_mode_write_and_read_failure(tp_wgzba_device):
    """Test virtual mode writes and failed packed-attribute reads."""
    endpoint = tp_wgzba_device.endpoints[1]
    private_cluster = endpoint.sonoff_private
    thermostat_cluster = endpoint.thermostat
    success = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]
    with mock.patch.object(
        thermostat_cluster,
        "write_real_system_mode",
        mock.AsyncMock(return_value=success),
    ) as write_mode:
        assert (
            await private_cluster.write_attributes(
                {
                    private_cluster.AttributeDefs.tp_wgzba_ui_system_mode.name: TPWGZBASystemMode.Manual
                }
            )
            == success
        )
    write_mode.assert_awaited_once_with(TPWGZBASystemMode.Manual)

    failure = foundation.ReadAttributeRecord(
        attrid=private_cluster.AttributeDefs.temperature_control_threshold.id,
        status=foundation.Status.FAILURE,
        value=foundation.TypeValue(),
    )
    with mock.patch.object(
        private_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=([], [failure])),
    ):
        result = await private_cluster.read_attributes_raw(
            [private_cluster.AttributeDefs.temperature_control_threshold_low.id]
        )
    assert result[1][0].status == foundation.Status.FAILURE
