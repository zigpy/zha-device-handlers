"""Focused regression tests for the Aqara W600 quirk.

These tests intentionally exercise the pure mapping and state-synchronisation
contracts without requiring a live Zigbee network.  In the upstream tree,
update the module import to the final zhaquirks package path if the quirk is
moved into a subpackage.
"""

from types import SimpleNamespace

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

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
    AqaraW600Thermostat,
    _all_success,
    _iter_status_records,
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
        "valve_position_raw": (0x0360, "uint16_t"),
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
    """Accept both flat and nested successful Zigpy status responses."""
    assert _all_success(records)
    assert list(_iter_status_records(records))


def test_status_processing_rejects_nested_failure() -> None:
    """Reject a nested response containing a failed status record."""
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
        (0, 25, RUNSTATE_IDLE),
    ],
)
def test_valve_position_updates_only_running_state(
    enabled: int, valve: int, expected_action: int
) -> None:
    """Ensure valve telemetry never changes the persistent HVAC mode."""
    thermostat = _FakeThermostat(enabled)

    thermostat._sync_running_state_from_valve(valve)

    assert thermostat.updates == [(0x0029, expected_action)]
    assert all(attrid != ATTR_SYSTEM_MODE for attrid, _ in thermostat.updates)
    assert ATTR_VALVE_POSITION_RAW == 0x0360
    assert ATTR_DEVICE_STATE == 0x0311
