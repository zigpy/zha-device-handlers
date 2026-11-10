"""Tests for the Amina S EV charger quirk."""

import asyncio
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import EntityCategory
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.amina.amina_s import (
    AMINA_ENDPOINT_ID,
    AMINA_MANUFACTURER_CODE,
    AminaControlCluster,
    alarms_text,
    ev_status_text,
)

zhaquirks.setup()

AMINA_S_DIAGNOSTICS = "amina-distribution-as-amina-s-0x01220001.json"
AMINA_S_IEEE = "ab:cd:ef:12:27:02:db:b2"


def move_to_level_response(status: foundation.Status) -> foundation.DefaultResponse:
    """Return the charger's response to a MoveToLevel command."""
    return foundation.DefaultResponse(
        command_id=LevelControl.ServerCommandDefs.move_to_level.id, status=status
    )


@pytest.fixture
def amina_device(zigpy_device_from_v2_quirk):
    """Amina S device with the quirk applied."""
    return zigpy_device_from_v2_quirk(
        "amina distribution AS",
        "amina S",
        endpoint_ids=[1, AMINA_ENDPOINT_ID],
        cluster_ids={
            AMINA_ENDPOINT_ID: {
                OnOff.cluster_id: OnOff.cluster_type,
                LevelControl.cluster_id: LevelControl.cluster_type,
                ElectricalMeasurement.cluster_id: ElectricalMeasurement.cluster_type,
                AminaControlCluster.cluster_id: AminaControlCluster.cluster_type,
            }
        },
    )


@pytest.mark.parametrize(
    "value, expected",
    (
        (0x0000, "Not connected"),
        (0x0001, "EV connected"),
        (0x0003, "Ready to charge"),
        (0x0011, "Ready to charge"),
        (0x0007, "Charging"),
        (0x0009, "Paused"),
        (0x8007, "Charging (derated)"),
        (0x8000, "Not connected (derated)"),
    ),
)
def test_ev_status_text(value, expected):
    """Test the EV status summary."""
    assert ev_status_text(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    (
        (0x0000, "No alarm"),
        (0x0001, "Welded relay(s)"),
        (0x0880, "Overcurrent, Critical powerloss"),
        (0x2000, "Alarm bit 13"),
    ),
)
def test_alarms_text(value, expected):
    """Test the alarm summary."""
    assert alarms_text(value) == expected


async def test_amina_s_entities():
    """Test the entities of a real Amina S, joined from its diagnostics."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, AMINA_S_DIAGNOSTICS, DEVICE_REGISTRY
        )

        def entity(platform: Platform, suffix: str):
            return device.get_platform_entity(
                platform, unique_id=f"{AMINA_S_IEEE}-{AMINA_ENDPOINT_ID}-{suffix}"
            )

        # The quirk leaves the default on/off switch and power sensors in place
        assert not entity(Platform.SWITCH, str(OnOff.cluster_id)).is_on
        assert entity(
            Platform.SENSOR, f"{ElectricalMeasurement.cluster_id}-total_active_power"
        )

        assert entity(Platform.SENSOR, "ev_status_text").native_value == "EV connected"
        assert entity(Platform.BINARY_SENSOR, "ev_connected").is_on
        assert not entity(Platform.BINARY_SENSOR, "charging").is_on
        assert not entity(Platform.BINARY_SENSOR, "ev_ready").is_on
        assert not entity(Platform.BINARY_SENSOR, "paused").is_on
        assert not entity(Platform.BINARY_SENSOR, "derated").is_on

        assert entity(Platform.SENSOR, "alarms_text").native_value == "No alarm"
        assert not entity(Platform.BINARY_SENSOR, "alarm_active").is_on

        assert entity(Platform.SENSOR, "total_active_energy").native_value == 1384.337
        assert entity(Platform.SENSOR, "last_session_energy").native_value == 0.349
        assert entity(Platform.SENSOR, "max_level").native_value == 32

        charge_limit = entity(Platform.NUMBER, "current_level")
        assert charge_limit.native_value == 32
        assert charge_limit.native_min_value == 6
        assert charge_limit.native_max_value == 32
        assert charge_limit.entity_category is None

        for suffix in ("single_phase", "enable_offline", "offline_single_phase"):
            switch = entity(Platform.SWITCH, suffix)
            assert not switch.is_on
            assert switch.entity_category == EntityCategory.CONFIG

        assert entity(Platform.NUMBER, "offline_current").native_value == 6
        time_to_offline = entity(Platform.NUMBER, "time_to_offline")
        assert time_to_offline.native_value == 0
        assert time_to_offline.native_max_value == 60

        # The status entities follow the EV status reported by the charger
        device.device.endpoints[AMINA_ENDPOINT_ID].amina_control.update_attribute(
            AminaControlCluster.AttributeDefs.ev_status.id, 0x0007
        )
        await gateway.async_block_till_done()
        assert entity(Platform.SENSOR, "ev_status_text").native_value == "Charging"
        assert entity(Platform.BINARY_SENSOR, "charging").is_on


async def test_amina_s_charge_limit():
    """Test that the charge limit entity sends a MoveToLevel command."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, AMINA_S_DIAGNOSTICS, DEVICE_REGISTRY
        )
        charge_limit = device.get_platform_entity(
            Platform.NUMBER,
            unique_id=f"{AMINA_S_IEEE}-{AMINA_ENDPOINT_ID}-current_level",
        )
        level_cluster = device.device.endpoints[AMINA_ENDPOINT_ID].level

        with mock.patch.object(
            level_cluster,
            "request",
            mock.AsyncMock(
                return_value=move_to_level_response(foundation.Status.SUCCESS)
            ),
        ) as request:
            await charge_limit.async_set_native_value(16)

        assert request.call_count == 1
        assert (
            request.call_args[0][1] == LevelControl.ServerCommandDefs.move_to_level.id
        )
        assert request.call_args.kwargs["level"] == 16
        assert charge_limit.native_value == 16


def test_manufacturer_code(amina_device):
    """Test that the Amina attributes use the Amina manufacturer code.

    The device reports a placeholder manufacturer code in its node descriptor.
    """
    cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].amina_control

    for attr_def in cluster.AttributeDefs:
        assert cluster._get_effective_manufacturer_code(attr_def) == (
            AMINA_MANUFACTURER_CODE
        )


def test_total_active_energy_never_decreases(amina_device):
    """Test that a lower total active energy reading is ignored."""
    cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].amina_control
    attr_id = AminaControlCluster.AttributeDefs.total_active_energy.id

    cluster.update_attribute(attr_id, 1000)
    assert cluster.get(attr_id) == 1000

    cluster.update_attribute(attr_id, 0)
    assert cluster.get(attr_id) == 1000

    cluster.update_attribute(attr_id, 1500)
    assert cluster.get(attr_id) == 1500

    # Other attributes are unaffected
    session_attr_id = AminaControlCluster.AttributeDefs.last_session_energy.id
    cluster.update_attribute(session_attr_id, 500)
    cluster.update_attribute(session_attr_id, 0)
    assert cluster.get(session_attr_id) == 0


@pytest.mark.parametrize(
    "on_off, expected_command",
    (
        (None, OnOff.ServerCommandDefs.off),
        (True, OnOff.ServerCommandDefs.off),
        (False, OnOff.ServerCommandDefs.on),
    ),
)
async def test_toggle_replaced(amina_device, on_off, expected_command):
    """Test that Toggle is sent as an explicit On or Off command."""
    on_off_cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].on_off

    if on_off is not None:
        on_off_cluster._update_attribute(OnOff.AttributeDefs.on_off.id, on_off)

    with mock.patch.object(on_off_cluster, "request", mock.AsyncMock()) as request:
        await on_off_cluster.toggle()

    assert request.call_count == 1
    assert request.call_args[0][1] == expected_command.id


async def test_on_off_refreshes_ev_status(amina_device):
    """Test that an on/off update re-reads the EV status."""
    endpoint = amina_device.endpoints[AMINA_ENDPOINT_ID]

    with mock.patch.object(
        endpoint.amina_control, "read_attributes", mock.AsyncMock()
    ) as read:
        endpoint.on_off.update_attribute(OnOff.AttributeDefs.on_off.id, True)
        await asyncio.sleep(0)

    read.assert_awaited_once_with([AminaControlCluster.AttributeDefs.ev_status.name])


async def test_power_update_refreshes_energy(amina_device):
    """Test that a power update reads the energy counters, without overlap."""
    endpoint = amina_device.endpoints[AMINA_ENDPOINT_ID]
    attr_id = ElectricalMeasurement.AttributeDefs.total_active_power.id
    release = asyncio.Event()

    async def slow_read(*args, **kwargs):
        await release.wait()

    with mock.patch.object(
        endpoint.amina_control, "read_attributes", side_effect=slow_read
    ) as read:
        endpoint.electrical_measurement.update_attribute(attr_id, 1000)
        await asyncio.sleep(0)
        # A second update while the first read is in flight is skipped
        endpoint.electrical_measurement.update_attribute(attr_id, 2000)
        await asyncio.sleep(0)
        release.set()
        await asyncio.sleep(0)

    read.assert_called_once_with(
        [
            AminaControlCluster.AttributeDefs.ev_status.name,
            AminaControlCluster.AttributeDefs.total_active_energy.name,
            AminaControlCluster.AttributeDefs.last_session_energy.name,
        ]
    )

    # Unrelated attributes do not trigger a read
    with mock.patch.object(
        endpoint.amina_control, "read_attributes", mock.AsyncMock()
    ) as read:
        endpoint.electrical_measurement.update_attribute(
            ElectricalMeasurement.AttributeDefs.rms_voltage.id, 230
        )
        await asyncio.sleep(0)

    read.assert_not_called()


@pytest.mark.parametrize(
    "requested, max_level, expected",
    (
        (16, 32, 16),
        (40, 32, 32),
        (2, 32, 6),
        (32, 20, 20),
    ),
)
async def test_current_level_write(amina_device, requested, max_level, expected):
    """Test that current level writes send a clamped MoveToLevel command."""
    level_cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].level
    level_cluster.update_attribute(LevelControl.AttributeDefs.min_level.id, 6)
    level_cluster.update_attribute(LevelControl.AttributeDefs.max_level.id, max_level)

    with mock.patch.object(
        level_cluster,
        "request",
        mock.AsyncMock(return_value=move_to_level_response(foundation.Status.SUCCESS)),
    ) as request:
        result = await level_cluster.write_attributes(
            {LevelControl.AttributeDefs.current_level.name: requested}
        )

    assert request.call_count == 1
    assert request.call_args[0][1] == LevelControl.ServerCommandDefs.move_to_level.id
    assert request.call_args.kwargs["level"] == expected
    assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == expected
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.SUCCESS,
                attrid=LevelControl.AttributeDefs.current_level.id,
            )
        ]
    ]


async def test_current_level_write_unknown_limits(amina_device):
    """Test that the level limits fall back to the spec range if unreadable."""
    level_cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].level

    with (
        mock.patch.object(
            level_cluster, "read_attributes", side_effect=asyncio.TimeoutError
        ) as read,
        mock.patch.object(
            level_cluster,
            "request",
            mock.AsyncMock(
                return_value=move_to_level_response(foundation.Status.SUCCESS)
            ),
        ) as request,
    ):
        await level_cluster.write_attributes(
            {LevelControl.AttributeDefs.current_level.name: 40}
        )

    assert read.call_count == 1
    assert request.call_args.kwargs["level"] == 32


async def test_current_level_write_rejected(amina_device):
    """Test that a rejected MoveToLevel command fails the write."""
    level_cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].level
    level_cluster.update_attribute(LevelControl.AttributeDefs.min_level.id, 6)
    level_cluster.update_attribute(LevelControl.AttributeDefs.max_level.id, 32)
    level_cluster.update_attribute(LevelControl.AttributeDefs.current_level.id, 10)

    with mock.patch.object(
        level_cluster,
        "request",
        mock.AsyncMock(return_value=move_to_level_response(foundation.Status.FAILURE)),
    ):
        result = await level_cluster.write_attributes(
            {LevelControl.AttributeDefs.current_level.name: 16}
        )

    assert level_cluster.get(LevelControl.AttributeDefs.current_level.id) == 10
    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=LevelControl.AttributeDefs.current_level.id,
            )
        ]
    ]


async def test_other_level_writes_pass_through(amina_device):
    """Test that writes to other level attributes are written as usual."""
    level_cluster = amina_device.endpoints[AMINA_ENDPOINT_ID].level

    with (
        mock.patch.object(
            level_cluster,
            "write_attributes_raw",
            mock.AsyncMock(
                return_value=[
                    [
                        foundation.WriteAttributesStatusRecord(
                            status=foundation.Status.SUCCESS
                        )
                    ]
                ]
            ),
        ) as write,
        mock.patch.object(level_cluster, "request", mock.AsyncMock()) as request,
    ):
        await level_cluster.write_attributes(
            {LevelControl.AttributeDefs.on_level.name: 10}
        )

    assert write.call_count == 1
    assert request.call_count == 0
