"""Additional coverage tests for the Aqara W600 thermostat quirk."""

from types import SimpleNamespace

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks import CustomCluster
from zhaquirks.xiaomi.aqara import thermostat_aeu005 as w600


class FakeFCC0:
    """Minimal fake of the W600 manufacturer cluster."""

    def __init__(self, enabled=1, schedule=0):
        """Initialize cached W600 mode attributes."""
        self._attr_cache = {
            w600.ATTR_THERMOSTAT_ENABLED: enabled,
            w600.ATTR_SCHEDULE_ENABLED: schedule,
        }
        self.writes = []
        self.reads = []

    async def write_attributes(self, attributes, **kwargs):
        """Record manufacturer attribute writes."""
        self.writes.append((attributes, kwargs))
        return [[SimpleNamespace(status=foundation.Status.SUCCESS)]]

    async def read_attributes(self, attributes, **kwargs):
        """Record manufacturer attribute reads."""
        self.reads.append((attributes, kwargs))
        return {}, {}

    def _update_attribute(self, attrid, value):
        self._attr_cache[attrid] = value


class FakeThermostat(w600.AqaraW600Thermostat):
    """Thermostat test double with an attached manufacturer cluster."""

    def __init__(self, enabled=1, schedule=0, vendor_response=None):
        """Initialize the fake thermostat state."""
        self.fcc0 = FakeFCC0(enabled, schedule)
        self.updates = []
        self.vendor_writes = []
        self.vendor_response = vendor_response or [
            [SimpleNamespace(status=foundation.Status.SUCCESS)]
        ]

    def _fcc0(self):
        return self.fcc0

    def _update_attribute(self, attrid, value):
        self.updates.append((attrid, value))

    async def _write_fcc0(self, attributes):
        self.vendor_writes.append(attributes)
        return self.vendor_response


@pytest.mark.parametrize(
    "key",
    [
        "system_mode",
        w600.ATTR_SYSTEM_MODE,
        Thermostat.AttributeDefs.system_mode,
    ],
)
def test_system_mode_key_forms_are_recognized(key):
    """Recognize string, numeric, and attribute-definition keys."""
    assert w600._key_matches_attrid(key, w600.ATTR_SYSTEM_MODE, "system_mode")


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "not_ready"), (1, "ready"), (2, "error"), (3, "in_progress")],
)
def test_calibration_status_mapping(value, expected):
    """Map all documented calibration status values."""
    assert w600._calibration_status_name(value) == expected


def test_calibration_status_mapping_keeps_unknown_values():
    """Keep unknown calibration values visible instead of hiding them."""
    assert w600._calibration_status_name(99) == "unknown_99"


@pytest.mark.parametrize(
    ("enabled", "schedule", "expected"),
    [(0, 0, w600.SYS_OFF), (1, 0, w600.SYS_HEAT), (1, 1, w600.SYS_AUTO)],
)
def test_sync_system_mode_from_vendor_state(enabled, schedule, expected):
    """Derive the persistent mode from vendor enable and schedule state."""
    thermostat = FakeThermostat(enabled, schedule)
    thermostat._sync_system_mode_from_w600()
    assert thermostat.updates[-1] == (w600.ATTR_SYSTEM_MODE, expected)


def test_sync_system_mode_ignores_unknown_enable_state():
    """Do not publish a mode before the enable attribute is known."""
    thermostat = FakeThermostat()
    thermostat.fcc0._attr_cache.pop(w600.ATTR_THERMOSTAT_ENABLED)
    thermostat._sync_system_mode_from_w600()
    assert thermostat.updates == []


def test_sync_running_state_without_fcc0_is_idle():
    """Treat missing vendor-cluster state conservatively as idle."""
    thermostat = FakeThermostat()
    thermostat.fcc0 = None
    thermostat._sync_running_state_from_valve(25)
    assert thermostat.updates == [(w600.ATTR_RUNNING_STATE, w600.RUNSTATE_IDLE)]


@pytest.mark.asyncio
async def test_vendor_write_adds_manufacturer_code_and_disables_cache():
    """Use Aqara manufacturer code and defer local caching to the quirk."""
    thermostat = FakeThermostat()
    result = await w600.AqaraW600Thermostat._write_fcc0(
        thermostat, {w600.ATTR_THERMOSTAT_ENABLED: 1}
    )
    assert result
    attributes, kwargs = thermostat.fcc0.writes[-1]
    assert attributes == {w600.ATTR_THERMOSTAT_ENABLED: 1}
    assert kwargs["manufacturer"] == w600.AQARA_MANUFACTURER_CODE
    assert kwargs["update_cache"] is False


@pytest.mark.asyncio
async def test_set_w600_mode_success_and_failure(monkeypatch):
    """Cache a successful mode only after both vendor and hold writes succeed."""
    base_calls = []

    async def fake_base_write(_self, attributes, *args, **kwargs):
        base_calls.append(attributes)
        return [[SimpleNamespace(status=foundation.Status.SUCCESS)]]

    monkeypatch.setattr(CustomCluster, "write_attributes", fake_base_write)
    thermostat = FakeThermostat()
    assert await thermostat._set_w600_mode(w600.SYS_AUTO)
    assert thermostat.vendor_writes == [w600.W600_MODE_WRITES[w600.SYS_AUTO]]
    assert base_calls == [{w600.ATTR_TEMP_SETPOINT_HOLD: 0}]
    assert thermostat.fcc0._attr_cache[w600.ATTR_SCHEDULE_ENABLED] == 1

    failed = FakeThermostat(
        vendor_response=[[SimpleNamespace(status=foundation.Status.FAILURE)]]
    )
    assert not await failed._set_w600_mode(w600.SYS_HEAT)
    assert failed.fcc0._attr_cache[w600.ATTR_THERMOSTAT_ENABLED] == 1


@pytest.mark.asyncio
async def test_set_w600_mode_rejects_unsupported_mode():
    """Reject a mode outside the W600 mode matrix."""
    thermostat = FakeThermostat()
    assert not await thermostat._set_w600_mode(99)
    assert thermostat.vendor_writes == []


@pytest.mark.asyncio
async def test_prepare_setpoint_wakes_explicitly_off_device():
    """Wake an explicitly off device and update the local vendor cache."""
    thermostat = FakeThermostat(enabled=0)
    assert await thermostat._prepare_setpoint_write()
    assert thermostat.vendor_writes == [{w600.ATTR_THERMOSTAT_ENABLED: 1}]
    assert thermostat.fcc0._attr_cache[w600.ATTR_THERMOSTAT_ENABLED] == 1


@pytest.mark.asyncio
async def test_prepare_setpoint_does_not_wake_unknown_or_active_device():
    """Avoid extra wake traffic when state is unknown or already enabled."""
    active = FakeThermostat(enabled=1)
    assert not await active._prepare_setpoint_write()
    assert active.vendor_writes == []

    unknown = FakeThermostat(enabled=1)
    unknown.fcc0._attr_cache.pop(w600.ATTR_THERMOSTAT_ENABLED)
    assert not await unknown._prepare_setpoint_write()
    assert unknown.vendor_writes == []


@pytest.mark.asyncio
async def test_prepare_setpoint_ignores_failed_wake():
    """Continue to the setpoint path when the wake response is unsuccessful."""
    thermostat = FakeThermostat(
        enabled=0,
        vendor_response=[[SimpleNamespace(status=foundation.Status.FAILURE)]],
    )
    assert not await thermostat._prepare_setpoint_write()
    assert w600.ATTR_THERMOSTAT_ENABLED not in thermostat.fcc0._attr_cache or (
        thermostat.fcc0._attr_cache[w600.ATTR_THERMOSTAT_ENABLED] == 0
    )


class TimeoutThermostat(FakeThermostat):
    """Thermostat fake that times out on manufacturer writes."""

    async def _write_fcc0(self, attributes):
        raise TimeoutError


@pytest.mark.asyncio
async def test_prepare_setpoint_ignores_wake_timeout():
    """Treat a sleeping-device wake timeout as best effort."""
    thermostat = TimeoutThermostat(enabled=0)
    assert not await thermostat._prepare_setpoint_write()


@pytest.mark.asyncio
async def test_write_attributes_routes_setpoint_and_manual_override(monkeypatch):
    """Write the setpoint first and then arm the manual override in schedule mode."""
    base_calls = []

    async def fake_base_write(_self, attributes, *args, **kwargs):
        base_calls.append(attributes)
        return [[SimpleNamespace(status=foundation.Status.SUCCESS)]]

    monkeypatch.setattr(CustomCluster, "write_attributes", fake_base_write)
    thermostat = FakeThermostat(enabled=1, schedule=1)
    result = await thermostat.write_attributes({"occupied_heating_setpoint": 2050})
    assert result
    assert base_calls == [
        {"occupied_heating_setpoint": 2050},
        {w600.ATTR_TEMP_SETPOINT_HOLD: 1},
    ]
    assert thermostat.updates[-1] == (w600.ATTR_TEMP_SETPOINT_HOLD, 1)


@pytest.mark.asyncio
async def test_write_attributes_rejects_invalid_system_mode():
    """Return an unsupported-attribute status for an invalid HVAC mode."""
    thermostat = FakeThermostat()
    result = await thermostat.write_attributes({w600.ATTR_SYSTEM_MODE: 99})
    assert result[0][0].status == foundation.Status.UNSUPPORTED_ATTRIBUTE


@pytest.mark.asyncio
async def test_refresh_w600_mode_state_reads_required_attributes(monkeypatch):
    """Refresh vendor mode state and standard manual-override state."""
    base_reads = []

    async def fake_base_read(_self, attributes, *args, **kwargs):
        base_reads.append(attributes)
        return {}, {}

    monkeypatch.setattr(CustomCluster, "read_attributes", fake_base_read)
    thermostat = FakeThermostat()
    await thermostat.refresh_w600_mode_state()
    assert thermostat.fcc0.reads[0][0] == [
        w600.ATTR_THERMOSTAT_ENABLED,
        w600.ATTR_SCHEDULE_ENABLED,
        w600.ATTR_DEVICE_STATE,
    ]
    assert base_reads == [[w600.ATTR_TEMP_SETPOINT_HOLD]]


@pytest.mark.asyncio
async def test_fcc0_update_routes_vendor_state_to_thermostat(monkeypatch):
    """Route vendor enable and valve reports to the correct standard state."""
    monkeypatch.setattr(CustomCluster, "_update_attribute", lambda *args: None)
    thermostat = FakeThermostat(enabled=1)
    cluster = object.__new__(w600.AqaraW600FCC0)
    cluster._endpoint = SimpleNamespace(thermostat=thermostat)

    w600.AqaraW600FCC0._update_attribute(cluster, w600.ATTR_THERMOSTAT_ENABLED, 1)
    w600.AqaraW600FCC0._update_attribute(cluster, w600.ATTR_VALVE_POSITION_RAW, 20)
    assert (w600.ATTR_SYSTEM_MODE, w600.SYS_HEAT) in thermostat.updates
    assert (w600.ATTR_RUNNING_STATE, w600.RUNSTATE_HEAT_ON) in thermostat.updates


@pytest.mark.asyncio
async def test_configure_reporting_reads_and_reports_w600_attributes(monkeypatch):
    """Configure reporting and perform the initial W600 state read."""
    configured = []
    reads = []

    async def fake_base_configure(_self):
        return None

    async def fake_configure_multiple(_self, config):
        configured.append(config)

    async def fake_read(_self, attributes, *args, **kwargs):
        reads.append((attributes, kwargs))
        return {}, {}

    monkeypatch.setattr(CustomCluster, "configure_reporting", fake_base_configure)
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "find_attribute",
        lambda _self, attrid, **kwargs: attrid,
    )
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "configure_reporting_multiple",
        fake_configure_multiple,
    )
    monkeypatch.setattr(w600.AqaraW600FCC0, "read_attributes", fake_read)

    cluster = object.__new__(w600.AqaraW600FCC0)
    await w600.AqaraW600FCC0.configure_reporting(cluster)
    assert configured
    assert reads
    assert reads[0][1]["manufacturer"] == w600.AQARA_MANUFACTURER_CODE


@pytest.mark.asyncio
async def test_configure_reporting_tolerates_reporting_timeout(monkeypatch):
    """Defer reporting setup when a battery device is asleep."""

    async def fake_base_configure(_self):
        return None

    async def raise_timeout(*args, **kwargs):
        raise TimeoutError

    async def fake_read(*args, **kwargs):
        return {}, {}

    monkeypatch.setattr(CustomCluster, "configure_reporting", fake_base_configure)
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "find_attribute",
        lambda _self, attrid, **kwargs: attrid,
    )
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "configure_reporting_multiple",
        raise_timeout,
    )
    monkeypatch.setattr(w600.AqaraW600FCC0, "read_attributes", fake_read)

    cluster = object.__new__(w600.AqaraW600FCC0)
    await w600.AqaraW600FCC0.configure_reporting(cluster)


@pytest.mark.asyncio
async def test_configure_reporting_tolerates_initial_read_timeout(monkeypatch):
    """Defer the initial read when a battery device is asleep."""

    async def fake_base_configure(_self):
        return None

    async def fake_configure_multiple(*args, **kwargs):
        return None

    async def raise_timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(CustomCluster, "configure_reporting", fake_base_configure)
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "find_attribute",
        lambda _self, attrid, **kwargs: attrid,
    )
    monkeypatch.setattr(
        w600.AqaraW600FCC0,
        "configure_reporting_multiple",
        fake_configure_multiple,
    )
    monkeypatch.setattr(w600.AqaraW600FCC0, "read_attributes", raise_timeout)

    cluster = object.__new__(w600.AqaraW600FCC0)
    await w600.AqaraW600FCC0.configure_reporting(cluster)
