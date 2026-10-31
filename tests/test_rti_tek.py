"""Tests for the Rti-Tek eTRV-ZB01 thermostat quirk."""

import datetime as dt
from types import SimpleNamespace
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import SeqDayOfWeek, SeqMode, Thermostat

import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.rti_tek.etrv_zb01 import (
    TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR,
    TRVZB_WEEKLY_SCHEDULE_DAY_ATTR,
    TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS,
    TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS,
    TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS,
    RtiTekTrvzbDevice,
    RtiTekTrvzbFirmwareUpdateEntity,
    RtiTekTrvzbPrivateCluster,
    RtiTekTrvzbScreenDirectionSelectEntity,
    RtiTekTrvzbSystemMode,
    RtiTekTrvzbTemperatureControlMode,
    RtiTekTrvzbTemperatureControlModeSelectEntity,
    RtiTekTrvzbTemporaryManualState,
    RtiTekTrvzbThermostat,
    _fault_code_status,
    _is_heat_setpoint_limit_entity,
    _motor_travel_calibration_status,
    _round_valve_switching_difference_raw_value,
    _temporary_manual_status,
    _trvzb_next_schedule_day,
    _trvzb_previous_schedule_day,
    _window_detection_status,
)

zhaquirks.setup()


TRVZB_CLUSTERS = {
    1: {
        Thermostat.cluster_id: ClusterType.Server,
        RtiTekTrvzbPrivateCluster.cluster_id: ClusterType.Server,
    }
}


class _RtiTekTrvzbFirmwareUpdateEntityForTest(RtiTekTrvzbFirmwareUpdateEntity):
    """Provide the two read-only platform references needed by OTA tests."""

    @property
    def endpoint(self):
        """Return the endpoint supplied by the test."""

        return self._test_endpoint

    @property
    def device(self):
        """Return the ZHA device supplied by the test."""

        return self._test_device


def _firmware_update_entity(endpoint, device):
    """Create a minimal OTA entity without needing the full ZHA platform setup."""

    entity = object.__new__(_RtiTekTrvzbFirmwareUpdateEntityForTest)
    entity._test_endpoint = endpoint
    entity._test_device = device
    return entity


class _RtiTekTrvzbDeviceForTest(RtiTekTrvzbDevice):
    """Provide ZHA device state needed by initialization tests."""

    @property
    def available(self):
        """Return the test-controlled availability state."""

        return self._test_available

    def debug(self, *_args, **_kwargs):
        """Capture best-effort initialization failures without logging setup."""


def _quirked_device_for_initialize(zigpy_device, *, available=True):
    """Create the minimal v2 device wrapper used by initialization tests."""

    device = object.__new__(_RtiTekTrvzbDeviceForTest)
    device._zigpy_device = zigpy_device
    device._gateway = SimpleNamespace(config=SimpleNamespace(local_timezone=dt.UTC))
    device._test_available = available
    return device


def _etrv_zb01_entry():
    """Return the sole v2 entry registered for the eTRV-ZB01."""

    entries = [
        entry
        for entry in DEVICE_REGISTRY
        if isinstance(entry.zha_device_factory, QuirkV2Factory)
        and any(
            model_info.manufacturer == "Rti-Tek" and model_info.model == "eTRV-ZB01"
            for model_info in entry.device_match.applies_to
        )
    ]
    assert len(entries) == 1
    return entries[0]


def test_etrv_zb01_quirk_matches_device_signature(zigpy_device_from_v2_quirk):
    """The eTRV-ZB01 must replace its standard and private clusters."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek",
        model="eTRV-ZB01",
        cluster_ids=TRVZB_CLUSTERS,
    )

    assert isinstance(device.endpoints[1].thermostat, RtiTekTrvzbThermostat)
    assert isinstance(
        device.endpoints[1].rti_tek_trvzb_private, RtiTekTrvzbPrivateCluster
    )


def test_etrv_zb01_temperature_control_mode_contract():
    """FD22/0x1004 uses the documented enum8 PID and ON-OFF values."""

    attribute = RtiTekTrvzbPrivateCluster.AttributeDefs.temperature_control_mode

    assert attribute.type is RtiTekTrvzbTemperatureControlMode
    assert int(RtiTekTrvzbTemperatureControlMode.PID) == 0
    assert int(RtiTekTrvzbTemperatureControlMode.ON_OFF) == 1
    assert RtiTekTrvzbTemperatureControlMode.PID.serialize() == b"\x00"
    assert RtiTekTrvzbTemperatureControlMode.ON_OFF.serialize() == b"\x01"


def test_etrv_zb01_entities_have_declared_attributes():
    """Every attribute-backed entity resolves on the final installed cluster."""

    definition = _etrv_zb01_entry().zha_device_factory.quirk_definition
    clusters = {
        Thermostat.cluster_id: RtiTekTrvzbThermostat,
        RtiTekTrvzbPrivateCluster.cluster_id: RtiTekTrvzbPrivateCluster,
    }

    assert len(definition.entity_metadata) == 42
    for entity_metadata in definition.entity_metadata:
        attribute_name = getattr(entity_metadata, "attribute_name", None)
        if attribute_name is None:
            continue
        cluster = clusters[entity_metadata.cluster_id]
        assert attribute_name in cluster.attributes_by_name, (
            f"{entity_metadata.translation_key}: {attribute_name} is not defined on "
            f"{cluster.__name__}"
        )


@pytest.mark.parametrize(
    ("raw_value", "status"),
    (
        (0, "No error"),
        (1, "Internal sensor fault"),
        (0b1010, "Motor operation fault, Low battery blocks firmware upgrade"),
        (1 << 10, "Unknown error (0x00000400)"),
        (-1, "Unknown error"),
        ("invalid", "Unknown error"),
    ),
)
def test_etrv_zb01_fault_status_contract(raw_value, status):
    """The documented FD22 fault bitmap produces stable sensor text."""

    assert _fault_code_status(raw_value) == status


@pytest.mark.parametrize(
    ("raw_value", "status"),
    ((0, "Success"), (1, "Failed"), ("invalid", "Failed")),
)
def test_etrv_zb01_motor_calibration_status_contract(raw_value, status):
    """Only a zero calibration status represents a completed calibration."""

    assert _motor_travel_calibration_status(raw_value) == status


@pytest.mark.parametrize(
    ("raw_value", "status"),
    ((0, "Not detected"), (1, "Detected"), (2, "Unknown"), (None, "Unknown")),
)
def test_etrv_zb01_window_status_contract(raw_value, status):
    """The open-window sensor uses the documented detected wording."""

    assert _window_detection_status(raw_value) == status


def test_etrv_zb01_schedule_day_helpers_wrap_at_week_boundary():
    """Weekly schedule navigation follows the standard Thermostat day bits."""

    assert _trvzb_next_schedule_day(SeqDayOfWeek.Saturday) == SeqDayOfWeek.Sunday
    assert _trvzb_previous_schedule_day(SeqDayOfWeek.Sunday) == SeqDayOfWeek.Saturday
    assert _temporary_manual_status(RtiTekTrvzbTemporaryManualState.Active) == "Active"
    assert _temporary_manual_status("invalid") == "Unknown"


def test_etrv_zb01_weekly_schedule_builds_six_standard_transitions(
    zigpy_device_from_v2_quirk,
):
    """Disabled editor rows are padded in the outgoing standard command only."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR, SeqDayOfWeek.Monday)
    thermostat._update_weekly_schedule_period_time(1, 6 * 60 + 29)
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1], 2000)
    thermostat._update_weekly_schedule_period_time(2, 18 * 60)
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[2], 1500)

    day, transitions, values = thermostat._build_weekly_schedule()

    assert day == SeqDayOfWeek.Monday
    assert transitions == [(389, 2000), (1080, 1500)] * 1 + [(1080, 1500)] * 4
    assert values == [389, 2000, 1080, 1500] + [1080, 1500] * 4
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 6
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[1]) == 29


@pytest.mark.parametrize(
    "periods",
    (
        [(60, 2000), (60, 2100)],
        [(60, 400)],
        [(24 * 60, 2000)],
    ),
)
def test_etrv_zb01_weekly_schedule_rejects_invalid_editor_values(
    zigpy_device_from_v2_quirk, periods
):
    """The local editor rejects disabled-only and invalid standard schedules."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    with pytest.raises(ValueError):
        device.endpoints[1].thermostat._validate_weekly_schedule_periods(periods)


def test_etrv_zb01_weekly_schedule_response_removes_device_padding(
    zigpy_device_from_v2_quirk,
):
    """Repeated final transitions are device padding, not visible editor rows."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    response = (
        6,
        SeqDayOfWeek.Monday,
        SeqMode.Heat,
        [360, 2000, 1080, 1500] + [1080, 1500] * 4,
    )

    assert thermostat._store_weekly_schedule_response(response)
    assert thermostat._weekly_schedule_device_cache[SeqDayOfWeek.Monday] == [
        (360, 2000),
        (1080, 1500),
    ]
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[3]) == 0xFF


async def test_etrv_zb01_valve_difference_write_rounding_and_mode_requirement(
    zigpy_device_from_v2_quirk,
):
    """FD22/0x1005 accepts ON-OFF writes and preserves the documented 0.1 C step."""

    assert _round_valve_switching_difference_raw_value(23) == 20
    assert _round_valve_switching_difference_raw_value(26) == 30

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    private = device.endpoints[1].rti_tek_trvzb_private
    private.read_attributes = mock.AsyncMock(
        return_value=(
            {"temperature_control_mode": RtiTekTrvzbTemperatureControlMode.ON_OFF},
            {},
        )
    )
    written = []

    async def write(_cluster, attributes, *args, **kwargs):
        written.append(attributes)
        return [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.SUCCESS,
                    RtiTekTrvzbPrivateCluster.AttributeDefs.valve_switching_difference.id,
                )
            ],
            [],
        ]

    with mock.patch.object(
        RtiTekTrvzbPrivateCluster.__mro__[1], "write_attributes", write
    ):
        await private.write_attributes({"valve_switching_difference": 26})

    assert written == [{"valve_switching_difference": 30}]


async def test_etrv_zb01_boost_write_requires_auto_or_holiday(
    zigpy_device_from_v2_quirk,
):
    """Boost duration is accepted only while Auto or Holiday is active."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Auto}, {})
    )
    write_result = [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
        [],
    ]

    with mock.patch.object(
        RtiTekTrvzbPrivateCluster.__mro__[1],
        "write_attributes",
        mock.AsyncMock(return_value=write_result),
    ) as write:
        await private.write_attributes({"boost_duration": 1800})

    write.assert_awaited_once_with({"boost_duration": 1800})

    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Manual}, {})
    )
    private.read_attributes = mock.AsyncMock(return_value=({"holiday_duration": 0}, {}))
    with pytest.raises(ValueError, match="Auto or Holiday"):
        await private.write_attributes({"boost_duration": 1800})


async def test_etrv_zb01_holiday_change_exits_active_boost(
    zigpy_device_from_v2_quirk,
):
    """Changing Holiday clears an acknowledged active Boost first."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    private = device.endpoints[1].rti_tek_trvzb_private
    private.read_attributes = mock.AsyncMock(
        return_value=({"boost_duration": 1800}, {})
    )
    boost_id = RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration.id
    write_result = [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS, boost_id)],
        [],
    ]
    with mock.patch.object(
        RtiTekTrvzbPrivateCluster.__mro__[1],
        "write_attributes",
        mock.AsyncMock(return_value=write_result),
    ) as write:
        await private.write_attributes({"holiday_duration": 24 * 60 * 60})

    assert write.await_args_list == [
        mock.call({"boost_duration": 0}),
        mock.call({"holiday_duration": 24 * 60 * 60}),
    ]


async def test_etrv_zb01_weekly_editor_writes_local_state_only(
    zigpy_device_from_v2_quirk,
):
    """Hour, minute, and temperature edits stay local until Apply is pressed."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat

    assert await thermostat.write_attributes({"weekly_schedule_period_1_hour": 6}) == (
        {},
        {},
    )
    await thermostat.write_attributes({"weekly_schedule_period_1_minute": 29})
    await thermostat.write_attributes({"weekly_schedule_period_1_temperature": 2050})

    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 6
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[1]) == 29
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]) == 2050
    with pytest.raises(ValueError, match="strictly increasing"):
        await thermostat.write_attributes({"weekly_schedule_period_2_hour": 6})
    await thermostat.write_attributes({"weekly_schedule_period_1_hour": 0xFF})
    with pytest.raises(ValueError, match="disabled"):
        await thermostat.write_attributes({"weekly_schedule_period_1_minute": 30})


async def test_etrv_zb01_temporary_manual_write_uses_standard_setpoint(
    zigpy_device_from_v2_quirk,
):
    """The local temporary control writes the standard occupied setpoint."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    setpoint_id = Thermostat.AttributeDefs.occupied_heating_setpoint.id
    result = [
        [
            foundation.WriteAttributesStatusRecord(
                foundation.Status.SUCCESS, setpoint_id
            )
        ],
        [],
    ]
    thermostat._start_temporary_manual_inference = mock.AsyncMock()

    with mock.patch.object(
        RtiTekTrvzbThermostat.__mro__[1],
        "write_attributes",
        mock.AsyncMock(return_value=result),
    ) as write:
        await thermostat.write_attributes({"temporary_manual_temperature": 2050})

    write.assert_awaited_once_with({"occupied_heating_setpoint": 2050})
    thermostat._start_temporary_manual_inference.assert_awaited_once()
    assert thermostat.get("temporary_manual_temperature") == 2050
    with pytest.raises(ValueError, match="0.5 C"):
        await thermostat.write_attributes({"temporary_manual_temperature": 2025})


async def test_etrv_zb01_schedule_apply_and_fetch_use_standard_commands(
    zigpy_device_from_v2_quirk,
):
    """Apply pads six slots, then fetches the selected day after settling."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._update_weekly_schedule_period_time(1, 360)
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1], 2000)
    result = SimpleNamespace(status=foundation.Status.SUCCESS, command_id=0x01)
    thermostat.set_weekly_schedule = mock.AsyncMock(return_value=result)
    thermostat.schedule_fetch = mock.AsyncMock()

    with mock.patch("zhaquirks.rti_tek.etrv_zb01.asyncio.sleep", mock.AsyncMock()):
        assert await thermostat.schedule_apply() is result

    thermostat.set_weekly_schedule.assert_awaited_once()
    assert (
        thermostat.set_weekly_schedule.await_args.kwargs["mode_for_sequence"]
        == SeqMode.Heat
    )
    thermostat.schedule_fetch.assert_awaited_once_with(
        expect_reply=True, days_to_return=SeqDayOfWeek.Monday
    )


async def test_etrv_zb01_schedule_fetches_selected_day_before_full_week(
    zigpy_device_from_v2_quirk,
):
    """Fetch reads seven one-day requests because the valve rejects 0x7F."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR, SeqDayOfWeek.Friday)
    response = (1, SeqDayOfWeek.Friday, SeqMode.Heat, [360, 2000])
    thermostat.get_weekly_schedule = mock.AsyncMock(return_value=response)

    responses = await thermostat.schedule_fetch()

    assert len(responses) == 7
    assert thermostat.get_weekly_schedule.await_args_list[0].kwargs[
        "days_to_return"
    ] == (SeqDayOfWeek.Friday)


async def test_etrv_zb01_temporary_manual_uses_next_device_transition(
    zigpy_device_from_v2_quirk,
):
    """Temporary manual state expires at the next transition reported by the valve."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=dt.UTC)
    thermostat.set_local_timezone(dt.UTC)
    thermostat._temporary_manual_now = mock.Mock(return_value=now)
    thermostat._weekly_schedule_device_cache = {
        int(SeqDayOfWeek.Monday): [(360, 2000), (540, 1500)],
        int(SeqDayOfWeek.Tuesday): [(420, 1900)],
    }

    assert thermostat._next_temporary_manual_transition() == now.replace(hour=9)
    assert thermostat._current_weekly_schedule_temperature() == 2000

    thermostat._temporary_manual_inference_active = True
    thermostat._refresh_temporary_manual_expiry()
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Active
    )
    assert thermostat._temporary_manual_expiry_task is not None
    thermostat._cancel_temporary_manual_expiry()

    thermostat._weekly_schedule_device_cache[int(SeqDayOfWeek.Monday)] = [(360, 2000)]
    assert thermostat._next_temporary_manual_transition() == (
        now + dt.timedelta(days=1)
    ).replace(hour=7, minute=0)


async def test_etrv_zb01_temporary_manual_detection_requires_auto_capability(
    zigpy_device_from_v2_quirk,
):
    """A reported setpoint activates temporary manual only for capable Auto mode."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    private.read_attributes = mock.AsyncMock(
        return_value=({"manual_temperature_in_auto_supported": True}, {})
    )
    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Auto}, {})
    )

    assert await thermostat._temporary_manual_is_supported_in_auto() is True

    thermostat._current_weekly_schedule_temperature = mock.Mock(return_value=2000)
    thermostat._refresh_temporary_manual_expiry = mock.Mock()
    thermostat._request_temporary_manual_schedules = mock.AsyncMock()
    await thermostat._detect_device_temporary_manual_mode(2050)
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Active
    )
    thermostat._request_temporary_manual_schedules.assert_awaited_once()

    await thermostat._detect_device_temporary_manual_mode(2000)
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )

    private.read_attributes = mock.AsyncMock(
        return_value=({"manual_temperature_in_auto_supported": False}, {})
    )
    await thermostat._start_temporary_manual_inference()
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )


def test_etrv_zb01_clearing_temporary_manual_cancels_expiry_task(
    zigpy_device_from_v2_quirk,
):
    """Leaving Auto clears the inferred state and cancels its pending deadline."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    expiry_task = mock.Mock()
    thermostat._temporary_manual_expiry_task = expiry_task
    thermostat._temporary_manual_inference_active = True

    thermostat._clear_temporary_manual_mode()

    expiry_task.cancel.assert_called_once()
    assert thermostat._temporary_manual_expiry_task is None
    assert thermostat._temporary_manual_inference_active is False
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )


async def test_etrv_zb01_mode_change_reads_and_clears_private_state(
    zigpy_device_from_v2_quirk,
):
    """Changing system mode exits Boost first and clears active Holiday later."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    private.read_attributes = mock.AsyncMock(
        return_value=({"holiday_duration": 86400, "boost_duration": 1800}, {})
    )
    boost_id = RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration.id
    holiday_id = RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration.id
    successful_writes = {
        boost_id: [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.SUCCESS, boost_id
                )
            ],
            [],
        ],
        holiday_id: [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.SUCCESS, holiday_id
                )
            ],
            [],
        ],
    }
    private.write_attributes = mock.AsyncMock(
        side_effect=lambda attributes: successful_writes[
            RtiTekTrvzbPrivateCluster._attribute_input_value(
                attributes, RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration
            )
            is not None
            and boost_id
            or holiday_id
        ]
    )

    cluster, holiday_active = await thermostat._prepare_system_mode_change()
    assert cluster is private
    assert holiday_active is True
    private.write_attributes.assert_awaited_once_with({"boost_duration": 0})
    await thermostat._finish_system_mode_change(private, holiday_active)
    assert private.write_attributes.await_args_list[-1] == mock.call(
        {"holiday_duration": 0}
    )


async def test_etrv_zb01_system_mode_write_exits_temporary_manual(
    zigpy_device_from_v2_quirk,
):
    """A successful mode write ends the local temporary-manual inference."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    mode_id = Thermostat.AttributeDefs.system_mode.id
    result = [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS, mode_id)],
        [],
    ]
    private_cluster = device.endpoints[1].rti_tek_trvzb_private
    thermostat._prepare_system_mode_change = mock.AsyncMock(
        return_value=(private_cluster, True)
    )
    thermostat._finish_system_mode_change = mock.AsyncMock()
    thermostat._temporary_manual_inference_active = True

    with mock.patch.object(
        RtiTekTrvzbThermostat.__mro__[1],
        "write_attributes",
        mock.AsyncMock(return_value=result),
    ) as write:
        await thermostat.write_attributes({"system_mode": RtiTekTrvzbSystemMode.Manual})

    write.assert_awaited_once_with({"system_mode": RtiTekTrvzbSystemMode.Manual})
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )
    thermostat._finish_system_mode_change.assert_awaited_once_with(
        private_cluster, True
    )


@pytest.mark.parametrize(
    "entity, expected",
    (
        (SimpleNamespace(unique_id="min_heat_setpoint_limit"), True),
        (SimpleNamespace(fallback_name="Maximum max_heat_setpoint_limit"), True),
        (SimpleNamespace(attribute_name="occupied_heating_setpoint"), False),
        (SimpleNamespace(), False),
    ),
)
def test_etrv_zb01_hides_only_default_heat_limit_entities(entity, expected):
    """The climate limits stay available to ZHA without creating editable entities."""

    assert _is_heat_setpoint_limit_entity(entity) is expected


async def test_etrv_zb01_screen_direction_respects_product_capability():
    """Only eTRV-602 exposes all four protocol-defined directions."""

    entity = object.__new__(RtiTekTrvzbScreenDirectionSelectEntity)
    entity._attr_options = ["0°", "90°", "180°", "270°"]
    entity._attribute_name = "screen_direction"
    entity._enum = {
        "0°": SimpleNamespace(value=0),
        "90°": SimpleNamespace(value=3),
        "180°": SimpleNamespace(value=1),
        "270°": SimpleNamespace(value=2),
    }
    entity._cluster = {"product_name": "eTRV-602"}
    entity.maybe_emit_state_changed_event = mock.Mock()

    assert entity.options == ["0°", "90°", "180°", "270°"]
    with mock.patch(
        "zhaquirks.rti_tek.etrv_zb01.write_attributes_safe", mock.AsyncMock()
    ) as write:
        await entity.async_select_option("90°")
    write.assert_awaited_once_with(entity._cluster, {"screen_direction": 3})

    entity._cluster["product_name"] = "eTRV-705"
    assert entity.options == ["0°", "180°"]
    entity.maybe_emit_state_changed_event.reset_mock()
    entity.handle_product_attribute_updated(
        SimpleNamespace(attribute_name="product_name")
    )
    entity.maybe_emit_state_changed_event.assert_called_once()
    with pytest.raises(ValueError, match="not supported"):
        await entity.async_select_option("90°")


@pytest.mark.parametrize(
    ("battery_response", "message"),
    (
        (None, "unavailable"),
        ({"battery_percentage_remaining": 100}, "above 50%"),
        ({"battery_percentage_remaining": 201}, "invalid"),
    ),
)
async def test_etrv_zb01_ota_install_blocks_invalid_or_low_battery(
    battery_response, message
):
    """OTA must never start at 50 percent or when battery state is unavailable."""

    endpoint = SimpleNamespace(id=1)
    if battery_response is None:
        zha_device = SimpleNamespace(
            device=SimpleNamespace(endpoints={1: SimpleNamespace(in_clusters={})})
        )
    else:
        power_cluster = SimpleNamespace(
            read_attributes=mock.AsyncMock(return_value=(battery_response, {}))
        )
        zha_device = SimpleNamespace(
            device=SimpleNamespace(
                endpoints={
                    1: SimpleNamespace(
                        in_clusters={PowerConfiguration.cluster_id: power_cluster}
                    )
                }
            )
        )
    entity = _firmware_update_entity(endpoint, zha_device)

    with pytest.raises(Exception, match=message):
        await entity.async_install(1)


async def test_etrv_zb01_ota_install_proceeds_above_minimum_battery():
    """A valid 51 percent battery reading delegates to the normal OTA update flow."""

    endpoint = SimpleNamespace(id=1)
    power_cluster = SimpleNamespace(
        read_attributes=mock.AsyncMock(
            return_value=({"battery_percentage_remaining": 102}, {})
        )
    )
    zha_device = SimpleNamespace(
        device=SimpleNamespace(
            endpoints={
                1: SimpleNamespace(
                    in_clusters={PowerConfiguration.cluster_id: power_cluster}
                )
            }
        )
    )
    entity = _firmware_update_entity(endpoint, zha_device)
    with mock.patch(
        "zhaquirks.rti_tek.etrv_zb01.FirmwareUpdateEntity.async_install",
        mock.AsyncMock(),
    ) as install:
        await entity.async_install(7)

    install.assert_awaited_once_with(7)


async def test_etrv_zb01_boost_rejects_unknown_mode_prerequisites(
    zigpy_device_from_v2_quirk,
):
    """Boost writes fail closed when the current mode or Holiday value is unknown."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    thermostat.read_attributes = mock.AsyncMock(return_value=({}, {}))

    with pytest.raises(ValueError, match="prerequisites"):
        await private._validate_boost_duration_write({"boost_duration": 1800})

    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Manual}, {})
    )
    private.read_attributes = mock.AsyncMock(side_effect=RuntimeError("read failed"))
    with pytest.raises(ValueError, match="prerequisites"):
        await private._validate_boost_duration_write({"boost_duration": 1800})


async def test_etrv_zb01_temperature_control_select_writes_enum8_value():
    """The PID and ON-OFF select preserves the documented enum8 transport type."""

    entity = object.__new__(RtiTekTrvzbTemperatureControlModeSelectEntity)
    entity._cluster = {
        "temperature_control_mode": RtiTekTrvzbTemperatureControlMode.ON_OFF
    }
    entity._attribute_name = "temperature_control_mode"
    entity.maybe_emit_state_changed_event = mock.Mock()

    assert entity.current_option == "ON-OFF"
    with mock.patch(
        "zhaquirks.rti_tek.etrv_zb01.write_attributes_safe", mock.AsyncMock()
    ) as write:
        await entity.async_select_option("PID")

    write.assert_awaited_once_with(
        entity._cluster,
        {"temperature_control_mode": RtiTekTrvzbTemperatureControlMode.PID},
    )
    entity.maybe_emit_state_changed_event.assert_called_once()
    entity._cluster["temperature_control_mode"] = None
    assert entity.current_option is None
    entity._cluster["temperature_control_mode"] = 2
    assert entity.current_option is None
    with pytest.raises(ValueError, match="not supported"):
        await entity.async_select_option("invalid")


async def test_etrv_zb01_temporary_manual_handles_missing_data_and_fetch_errors(
    zigpy_device_from_v2_quirk,
):
    """Temporary mode stays local and degrades to Unknown when inputs are absent."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private

    device.endpoints[1].in_clusters.pop(RtiTekTrvzbPrivateCluster.cluster_id)
    assert await thermostat._temporary_manual_is_supported_in_auto() is None
    device.endpoints[1].in_clusters[RtiTekTrvzbPrivateCluster.cluster_id] = private

    private.read_attributes = mock.AsyncMock(side_effect=RuntimeError("read failed"))
    assert await thermostat._temporary_manual_is_supported_in_auto() is None
    await thermostat._start_temporary_manual_inference()
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Unknown
    )

    thermostat._temporary_manual_now = mock.Mock(
        return_value=dt.datetime(2026, 9, 14, 8, 0, tzinfo=dt.UTC)
    )
    thermostat.get_weekly_schedule = mock.AsyncMock(side_effect=RuntimeError("offline"))
    await thermostat._request_temporary_manual_schedules()
    assert thermostat.get_weekly_schedule.await_count == 3

    thermostat._weekly_schedule_device_cache = {}
    await thermostat._detect_device_temporary_manual_mode(2000)
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Unknown
    )


@pytest.mark.parametrize(
    "response",
    (
        (),
        (0, SeqDayOfWeek.Monday, SeqMode.Heat, []),
        (1, 0, SeqMode.Heat, [60, 2000]),
        (1, SeqDayOfWeek.Monday, 0, [60, 2000]),
        (1, SeqDayOfWeek.Monday, SeqMode.Heat, [60]),
        (1, SeqDayOfWeek.Monday, SeqMode.Heat, [24 * 60, 2000]),
        (1, SeqDayOfWeek.Monday, SeqMode.Heat, [60, 400]),
        (2, SeqDayOfWeek.Monday, SeqMode.Heat, [120, 2000, 60, 1500]),
    ),
)
def test_etrv_zb01_rejects_invalid_weekly_schedule_responses(
    zigpy_device_from_v2_quirk, response
):
    """Malformed standard Thermostat schedule responses never update the editor."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    assert device.endpoints[1].thermostat._weekly_schedule_response(response) is None


async def test_etrv_zb01_schedule_response_command_and_fetch_one_day(
    zigpy_device_from_v2_quirk,
):
    """A standard response command updates the editor, while other commands pass on."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    response = (1, SeqDayOfWeek.Monday, SeqMode.Heat, [60, 2000])
    assert (
        thermostat.handle_cluster_request(SimpleNamespace(command_id=0), response)
        is None
    )

    thermostat.get_weekly_schedule = mock.AsyncMock(return_value=response)
    assert (
        await thermostat.schedule_fetch(days_to_return=SeqDayOfWeek.Monday) == response
    )
    thermostat.get_weekly_schedule.assert_awaited_once_with(
        days_to_return=SeqDayOfWeek.Monday,
        mode_to_return=SeqMode.Heat,
        expect_reply=False,
    )


async def test_etrv_zb01_editor_day_change_preserves_each_day_and_rejects_invalid(
    zigpy_device_from_v2_quirk,
):
    """Switching weekdays snapshots the local editor without sending a device write."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    await thermostat.write_attributes({"weekly_schedule_period_1_hour": 8})
    await thermostat.write_attributes({"weekly_schedule_period_1_temperature": 2100})
    await thermostat.write_attributes({"weekly_schedule_day": SeqDayOfWeek.Tuesday})
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 0xFF
    await thermostat.write_attributes({"weekly_schedule_day": SeqDayOfWeek.Monday})
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 8
    with pytest.raises(ValueError, match="one weekday"):
        await thermostat.write_attributes({"weekly_schedule_day": 0})


async def test_etrv_zb01_temporary_manual_write_rejects_invalid_combinations(
    zigpy_device_from_v2_quirk,
):
    """Temporary manual setpoints enforce protocol range, step, and mode exclusivity."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    with pytest.raises(ValueError, match="5-30"):
        await thermostat.write_attributes({"temporary_manual_temperature": 400})
    with pytest.raises(ValueError, match="0.5 C"):
        await thermostat.write_attributes({"temporary_manual_temperature": 2025})
    with pytest.raises(ValueError, match="with system mode"):
        await thermostat.write_attributes(
            {
                "temporary_manual_temperature": 2000,
                "system_mode": RtiTekTrvzbSystemMode.Auto,
            }
        )


async def test_etrv_zb01_private_writes_fail_closed_and_clear_boost_first(
    zigpy_device_from_v2_quirk,
):
    """Private writes reject missing ON-OFF state and unacknowledged Boost exits."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    private = device.endpoints[1].rti_tek_trvzb_private
    difference = RtiTekTrvzbPrivateCluster.AttributeDefs.valve_switching_difference
    private.read_attributes = mock.AsyncMock(return_value=({}, {}))
    with pytest.raises(ValueError, match="ON-OFF mode"):
        await private.write_attributes({difference.name: 20})

    private.read_attributes = mock.AsyncMock(
        return_value=({"boost_duration": None}, {})
    )
    with pytest.raises(ValueError, match="Unable to read Boost"):
        await private._clear_active_boost_before_holiday_write()

    boost_id = RtiTekTrvzbPrivateCluster.AttributeDefs.boost_duration.id
    private.read_attributes = mock.AsyncMock(
        return_value=({"boost_duration": 1800}, {})
    )
    failed_result = [
        [foundation.WriteAttributesStatusRecord(foundation.Status.FAILURE, boost_id)],
        [],
    ]
    with (
        mock.patch.object(
            RtiTekTrvzbPrivateCluster.__mro__[1],
            "write_attributes",
            mock.AsyncMock(return_value=failed_result),
        ),
        pytest.raises(ValueError, match="Unable to exit Boost"),
    ):
        await private._clear_active_boost_before_holiday_write()


async def test_etrv_zb01_mode_change_helpers_reject_missing_or_failed_values(
    zigpy_device_from_v2_quirk,
):
    """Mode changes stop before a private read or write can leave state ambiguous."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    holiday = RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration

    device.endpoints[1].in_clusters.pop(RtiTekTrvzbPrivateCluster.cluster_id)
    with pytest.raises(ValueError, match="access TRVZB"):
        await thermostat._read_private_mode_attributes(holiday)
    device.endpoints[1].in_clusters[RtiTekTrvzbPrivateCluster.cluster_id] = private

    private.read_attributes = mock.AsyncMock(return_value=({}, {}))
    with pytest.raises(ValueError, match="Unable to read holiday_duration"):
        await thermostat._read_private_mode_attributes(holiday)

    private.write_attributes = mock.AsyncMock(return_value=([], []))
    with pytest.raises(ValueError, match="Unable to write holiday_duration"):
        await thermostat._write_private_mode_attribute(private, holiday, 0)

    await thermostat._finish_system_mode_change(private, False)
    private.write_attributes.assert_awaited_once()


async def test_etrv_zb01_schedule_editor_rejects_disabled_and_invalid_fields(
    zigpy_device_from_v2_quirk,
):
    """Disabled periods cannot receive values and clocks retain their documented bounds."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat

    await thermostat.write_attributes({"weekly_schedule_period_1_time": 0xFFFF})
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 0xFF
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]) == 0

    with pytest.raises(ValueError, match="hour must be 0-23"):
        await thermostat.write_attributes({"weekly_schedule_period_1_hour": 24})
    with pytest.raises(ValueError, match="minute must be 0-59"):
        await thermostat.write_attributes({"weekly_schedule_period_1_minute": 60})
    with pytest.raises(ValueError, match="period is disabled"):
        await thermostat.write_attributes(
            {"weekly_schedule_period_1_temperature": 2000}
        )


def test_etrv_zb01_schedule_build_requires_a_weekday_and_period(
    zigpy_device_from_v2_quirk,
):
    """An apply request requires a valid weekday and at least one enabled period."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat

    with pytest.raises(ValueError, match="at least one period"):
        thermostat._build_weekly_schedule()

    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_DAY_ATTR, 0)
    with pytest.raises(ValueError, match="one weekday"):
        thermostat._build_weekly_schedule()


async def test_etrv_zb01_thermostat_reports_refresh_local_state(
    zigpy_device_from_v2_quirk,
):
    """Standard setpoint and manual-mode reports keep local derived state aligned."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._schedule_device_temporary_manual_detection = mock.Mock()
    thermostat._temporary_manual_inference_active = True
    thermostat._update_attribute(
        Thermostat.AttributeDefs.occupied_heating_setpoint.id, 2050
    )
    assert thermostat.get("temporary_manual_temperature") == 2050
    thermostat._update_attribute(
        Thermostat.AttributeDefs.system_mode.id, RtiTekTrvzbSystemMode.Manual
    )
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )

    success = {
        "occupied_heating_setpoint": 2100,
        "system_mode": RtiTekTrvzbSystemMode.Auto,
    }
    with mock.patch.object(
        RtiTekTrvzbThermostat.__mro__[1],
        "read_attributes",
        mock.AsyncMock(return_value=(success, {})),
    ):
        assert await thermostat.read_attributes(["occupied_heating_setpoint"]) == (
            success,
            {},
        )
    assert thermostat.get("temporary_manual_temperature") == 2100


async def test_etrv_zb01_schedule_apply_rejects_failed_device_response(
    zigpy_device_from_v2_quirk,
):
    """Apply does not claim success when the standard command is rejected."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._update_weekly_schedule_period_time(1, 360)
    thermostat._update_attribute(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1], 2000)
    thermostat.set_weekly_schedule = mock.AsyncMock(
        return_value=SimpleNamespace(status=foundation.Status.FAILURE, command_id=0x01)
    )
    with pytest.raises(ValueError, match="apply failed"):
        await thermostat.schedule_apply()


def test_etrv_zb01_schedule_editor_rejects_invalid_raw_times(
    zigpy_device_from_v2_quirk,
):
    """The raw local editor accepts only minutes within a single day."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    assert thermostat._weekly_schedule_period_index(0xDEAD) is None
    with pytest.raises(ValueError, match="within one day"):
        thermostat._update_weekly_schedule_period_time(1, -1)
    with pytest.raises(ValueError, match="within one day"):
        thermostat._update_weekly_schedule_period_time(1, 24 * 60)


async def test_etrv_zb01_initialization_reads_capability_and_full_schedule(
    zigpy_device_from_v2_quirk,
):
    """An available device selects today then refreshes all schedule editor days."""

    zigpy_device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = zigpy_device.endpoints[1].thermostat
    private = zigpy_device.endpoints[1].rti_tek_trvzb_private
    wrapper = _quirked_device_for_initialize(zigpy_device)
    private.read_attributes = mock.AsyncMock(return_value=({}, {}))
    thermostat.schedule_fetch = mock.AsyncMock()

    with mock.patch.object(
        RtiTekTrvzbDevice.__mro__[1], "async_initialize", mock.AsyncMock()
    ):
        await wrapper.async_initialize()

    private.read_attributes.assert_awaited_once_with(
        ["manual_temperature_in_auto_supported"], allow_cache=True
    )
    thermostat.schedule_fetch.assert_awaited_once()
    assert thermostat._trvzb_timezone is dt.UTC

    thermostat.schedule_fetch.reset_mock()
    with mock.patch.object(
        RtiTekTrvzbDevice.__mro__[1], "async_initialize", mock.AsyncMock()
    ):
        await wrapper.async_initialize(from_cache=True)
    thermostat.schedule_fetch.assert_not_awaited()


async def test_etrv_zb01_initialization_tolerates_read_and_fetch_failures(
    zigpy_device_from_v2_quirk,
):
    """A transient capability or schedule read failure does not abort device setup."""

    zigpy_device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = zigpy_device.endpoints[1].thermostat
    private = zigpy_device.endpoints[1].rti_tek_trvzb_private
    wrapper = _quirked_device_for_initialize(zigpy_device)
    private.read_attributes = mock.AsyncMock(side_effect=RuntimeError("offline"))
    thermostat.schedule_fetch = mock.AsyncMock(side_effect=RuntimeError("offline"))

    with mock.patch.object(
        RtiTekTrvzbDevice.__mro__[1], "async_initialize", mock.AsyncMock()
    ):
        await wrapper.async_initialize()

    thermostat.schedule_fetch.assert_awaited_once()


def test_etrv_zb01_screen_direction_subscribes_to_product_name_updates():
    """The orientation select refreshes when FD22 product name data changes."""

    entity = object.__new__(RtiTekTrvzbScreenDirectionSelectEntity)
    entity._on_remove_callbacks = []
    entity._cluster = SimpleNamespace(on_event=mock.Mock(side_effect=[mock.Mock()] * 4))
    with mock.patch.object(RtiTekTrvzbScreenDirectionSelectEntity.__mro__[1], "on_add"):
        entity.on_add()

    assert entity._cluster.on_event.call_count == 4
    assert len(entity._on_remove_callbacks) == 4


async def test_etrv_zb01_temporary_manual_active_state_uses_schedule_context(
    zigpy_device_from_v2_quirk,
):
    """Supported Auto mode marks temporary control active and refreshes schedules."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    private.read_attributes = mock.AsyncMock(
        return_value=({"manual_temperature_in_auto_supported": True}, {})
    )
    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Auto}, {})
    )
    thermostat._refresh_temporary_manual_expiry = mock.Mock()
    thermostat._request_temporary_manual_schedules = mock.AsyncMock()

    await thermostat._start_temporary_manual_inference()

    assert thermostat._temporary_manual_inference_active is True
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Active
    )
    thermostat._refresh_temporary_manual_expiry.assert_called_once()
    thermostat._request_temporary_manual_schedules.assert_awaited_once()


def test_etrv_zb01_current_schedule_uses_previous_day_after_midnight(
    zigpy_device_from_v2_quirk,
):
    """Before today's first transition, temporary control uses yesterday's final setpoint."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._temporary_manual_now = mock.Mock(
        return_value=dt.datetime(2026, 9, 14, 1, 0, tzinfo=dt.UTC)
    )
    thermostat._weekly_schedule_device_cache = {
        int(SeqDayOfWeek.Monday): [(360, 2000)],
        int(SeqDayOfWeek.Sunday): [(1320, 1500)],
    }

    assert thermostat._current_weekly_schedule_temperature() == 1500


def test_etrv_zb01_weekly_schedule_response_accepts_zcl_response_object(
    zigpy_device_from_v2_quirk,
):
    """The standard response object format is parsed like its raw argument tuple."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    response = SimpleNamespace(
        num_transitions_for_sequence=1,
        day_of_week_for_sequence=SeqDayOfWeek.Monday,
        mode_for_sequence=SeqMode.Heat,
        values=[360, 2000],
    )

    assert device.endpoints[1].thermostat._weekly_schedule_response(response) == (
        SeqDayOfWeek.Monday,
        [(360, 2000)],
    )


async def test_etrv_zb01_ota_rejects_missing_endpoint_and_read_failures():
    """OTA blocks absent battery values and transport errors before installation."""

    endpoint = SimpleNamespace(id=1)
    missing_endpoint = _firmware_update_entity(
        endpoint, SimpleNamespace(device=SimpleNamespace(endpoints={}))
    )
    with pytest.raises(Exception, match="endpoint is unavailable"):
        await missing_endpoint.async_install(1)

    for read_result in (({}, {}), RuntimeError("offline")):
        power_cluster = SimpleNamespace(
            read_attributes=mock.AsyncMock(
                side_effect=read_result if isinstance(read_result, Exception) else None,
                return_value=None
                if isinstance(read_result, Exception)
                else read_result,
            )
        )
        entity = _firmware_update_entity(
            endpoint,
            SimpleNamespace(
                device=SimpleNamespace(
                    endpoints={
                        1: SimpleNamespace(
                            in_clusters={PowerConfiguration.cluster_id: power_cluster}
                        )
                    }
                )
            ),
        )
        with pytest.raises(Exception, match="battery level"):
            await entity.async_install(1)


def test_etrv_zb01_select_initializer_sets_documented_options():
    """The custom enum select supplies its two protocol labels at construction."""

    with mock.patch("zhaquirks.rti_tek.etrv_zb01.ZCLEnumSelectEntity.__init__"):
        entity = RtiTekTrvzbTemperatureControlModeSelectEntity()

    assert entity._attr_options == ["PID", "ON-OFF"]


def test_etrv_zb01_temporary_manual_handles_unknown_transitions(
    zigpy_device_from_v2_quirk,
):
    """Missing current or following schedules leave temporary mode explicitly unknown."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=dt.UTC)
    thermostat._temporary_manual_now = mock.Mock(return_value=now)

    assert thermostat._temporary_manual_now().tzinfo is dt.UTC
    assert thermostat._next_temporary_manual_transition() is None
    thermostat._weekly_schedule_device_cache = {int(SeqDayOfWeek.Monday): [(360, 2000)]}
    assert thermostat._next_temporary_manual_transition() is None

    thermostat._temporary_manual_inference_active = True
    thermostat._refresh_temporary_manual_expiry()
    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Unknown
    )

    thermostat._weekly_schedule_device_cache = {int(SeqDayOfWeek.Monday): []}
    assert thermostat._current_weekly_schedule_temperature() is None


async def test_etrv_zb01_device_temporary_manual_handles_unknown_capability(
    zigpy_device_from_v2_quirk,
):
    """A device report remains unknown when current Auto capability cannot be read."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._current_weekly_schedule_temperature = mock.Mock(return_value=2000)
    thermostat._temporary_manual_is_supported_in_auto = mock.AsyncMock(
        return_value=None
    )

    await thermostat._detect_device_temporary_manual_mode(2050)

    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Unknown
    )


def test_etrv_zb01_device_report_detection_handles_sync_and_task_replacement(
    zigpy_device_from_v2_quirk,
):
    """Report handling tolerates startup without a loop and replaces stale work."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    with mock.patch(
        "zhaquirks.rti_tek.etrv_zb01.asyncio.get_running_loop",
        side_effect=RuntimeError,
    ):
        thermostat._schedule_device_temporary_manual_detection(2000)

    stale_task = mock.Mock()
    loop = mock.Mock()
    thermostat._temporary_manual_detection_task = stale_task
    thermostat._detect_device_temporary_manual_mode = mock.Mock(
        return_value=mock.Mock()
    )
    with mock.patch(
        "zhaquirks.rti_tek.etrv_zb01.asyncio.get_running_loop", return_value=loop
    ):
        thermostat._schedule_device_temporary_manual_detection(2000)

    stale_task.cancel.assert_called_once()
    loop.create_task.assert_called_once()


def test_etrv_zb01_thermostat_report_tolerates_invalid_system_mode(
    zigpy_device_from_v2_quirk,
):
    """Malformed mode reports clear local temporary manual state without raising."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._temporary_manual_inference_active = True
    thermostat._update_attribute(Thermostat.AttributeDefs.system_mode.id, "invalid")

    assert (
        thermostat.get("temporary_manual_state")
        == RtiTekTrvzbTemporaryManualState.Inactive
    )


def test_etrv_zb01_weekly_schedule_response_rejects_nonstandard_formats(
    zigpy_device_from_v2_quirk,
):
    """Response parsing rejects objects and values outside the standard payload shape."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    valid = SimpleNamespace(
        num_transitions_for_sequence=1,
        day_of_week_for_sequence=SeqDayOfWeek.Monday,
        mode_for_sequence=SeqMode.Heat,
        values=[360, 2000],
    )

    assert thermostat._weekly_schedule_response([valid]) == (
        SeqDayOfWeek.Monday,
        [(360, 2000)],
    )
    assert thermostat._weekly_schedule_response(SimpleNamespace()) is None
    assert (
        thermostat._weekly_schedule_response(
            (1, SeqDayOfWeek.Monday, SeqMode.Heat, None)
        )
        is None
    )
    assert thermostat._store_weekly_schedule_response(()) is False


async def test_etrv_zb01_schedule_editor_accepts_raw_time_and_ignores_unknown_keys(
    zigpy_device_from_v2_quirk,
):
    """A raw time initializes its default setpoint while unrelated keys pass through."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat

    await thermostat.write_attributes({"weekly_schedule_period_1_time": 360})
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_HOUR_ATTRS[1]) == 6
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_MINUTE_ATTRS[1]) == 0
    assert thermostat.get(TRVZB_WEEKLY_SCHEDULE_TEMPERATURE_ATTRS[1]) == 2000

    with mock.patch.object(
        RtiTekTrvzbThermostat.__mro__[1],
        "write_attributes",
        mock.AsyncMock(return_value=({}, {})),
    ) as write:
        await thermostat.write_attributes({"not_a_quirk_attribute": 1})
    write.assert_awaited_once_with({"not_a_quirk_attribute": 1})


async def test_etrv_zb01_private_mode_and_boost_validation_error_paths(
    zigpy_device_from_v2_quirk,
):
    """Private writes fail closed when prerequisites cannot be established."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    private = device.endpoints[1].rti_tek_trvzb_private
    holiday = RtiTekTrvzbPrivateCluster.AttributeDefs.holiday_duration

    device.endpoints[1].in_clusters.pop(Thermostat.cluster_id)
    with pytest.raises(ValueError, match="system mode"):
        await private._validate_boost_duration_write({"boost_duration": 1})
    device.endpoints[1].in_clusters[Thermostat.cluster_id] = thermostat

    thermostat.read_attributes = mock.AsyncMock(side_effect=RuntimeError("offline"))
    with pytest.raises(ValueError, match="prerequisites"):
        await private._validate_boost_duration_write({"boost_duration": 1})

    thermostat.read_attributes = mock.AsyncMock(
        return_value=({"system_mode": RtiTekTrvzbSystemMode.Manual}, {})
    )
    private.read_attributes = mock.AsyncMock(
        return_value=({"holiday_duration": None}, {})
    )
    with pytest.raises(ValueError, match="prerequisites"):
        await private._validate_boost_duration_write({"boost_duration": 1})

    private.read_attributes = mock.AsyncMock(return_value=({"holiday_duration": 0}, {}))
    await private._validate_boost_duration_write(
        {"boost_duration": 1, holiday.name: 3600}
    )
    assert private._write_succeeded([], holiday.id) is False

    private.read_attributes = mock.AsyncMock(return_value=({"boost_duration": 0}, {}))
    await private._clear_active_boost_before_holiday_write()

    difference = RtiTekTrvzbPrivateCluster.AttributeDefs.valve_switching_difference
    private.read_attributes = mock.AsyncMock(side_effect=RuntimeError("offline"))
    with pytest.raises(ValueError, match="temperature control mode"):
        await private.write_attributes({difference.name: 20})


async def test_etrv_zb01_temporary_manual_fetches_and_stores_valid_schedules(
    zigpy_device_from_v2_quirk,
):
    """Adjacent successful schedule reads are retained for temporary-mode inference."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    thermostat._temporary_manual_now = mock.Mock(
        return_value=dt.datetime(2026, 9, 14, 8, 0, tzinfo=dt.UTC)
    )
    thermostat.get_weekly_schedule = mock.AsyncMock(
        side_effect=lambda **kwargs: (
            1,
            kwargs["days_to_return"],
            SeqMode.Heat,
            [360, 2000],
        )
    )

    await thermostat._request_temporary_manual_schedules()

    assert len(thermostat._weekly_schedule_device_cache) == 3


def test_etrv_zb01_temporary_manual_uses_local_timezone_when_unconfigured(
    zigpy_device_from_v2_quirk,
):
    """The temporary-mode clock falls back to the system local timezone."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    now = device.endpoints[1].thermostat._temporary_manual_now()

    assert now.tzinfo is not None


def test_etrv_zb01_invalid_schedule_command_delegates_to_thermostat(
    zigpy_device_from_v2_quirk,
):
    """Non-schedule commands retain the base Thermostat command handling path."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat
    with mock.patch.object(
        RtiTekTrvzbThermostat.__mro__[1],
        "handle_cluster_request",
        return_value="base-result",
    ) as handler:
        assert (
            thermostat.handle_cluster_request(SimpleNamespace(command_id=1), ())
            == "base-result"
        )

    handler.assert_called_once()


async def test_etrv_zb01_temporary_manual_rejects_duplicate_attribute_aliases(
    zigpy_device_from_v2_quirk,
):
    """Name and numeric aliases cannot submit two temporary-manual setpoints."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    thermostat = device.endpoints[1].thermostat

    with pytest.raises(ValueError, match="provided twice"):
        await thermostat.write_attributes(
            {
                "temporary_manual_temperature": 2000,
                TRVZB_TEMPORARY_MANUAL_TEMPERATURE_ATTR: 2050,
            }
        )


async def test_etrv_zb01_initialize_tolerates_missing_endpoint_or_thermostat(
    zigpy_device_from_v2_quirk,
):
    """Initialization returns cleanly when the final quirked endpoint is absent."""

    zigpy_device = zigpy_device_from_v2_quirk(
        manufacturer="Rti-Tek", model="eTRV-ZB01", cluster_ids=TRVZB_CLUSTERS
    )
    wrapper = _quirked_device_for_initialize(zigpy_device)
    with mock.patch.object(
        RtiTekTrvzbDevice.__mro__[1], "async_initialize", mock.AsyncMock()
    ):
        wrapper.device.endpoints = {}
        await wrapper.async_initialize()
        wrapper.device.endpoints = {1: SimpleNamespace(in_clusters={})}
        await wrapper.async_initialize()
