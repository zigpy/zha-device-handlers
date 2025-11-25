"""Tests for Tuya PJ-1203 Single Channel Clamp Energy Meter quirk."""

import pytest
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
from zhaquirks.const import MODELS_INFO
from zhaquirks.tuya.ts0601_pj1203 import (
    TuyaElectricalMeasurementPJ1203,
    TuyaMeteringPJ1203,
    TuyaPJ1203ManufCluster,
    TuyaPJ1203PowerMeter,
)


@pytest.fixture
def pj1203_device(zigpy_device_from_quirk):
    """Create a PJ-1203 device from quirk."""
    return zigpy_device_from_quirk(TuyaPJ1203PowerMeter)


def test_pj1203_signature_matches():
    """Test that quirk matches both manufacturer IDs."""
    assert ("_TZE284_cjbofhxw", "TS0601") in TuyaPJ1203PowerMeter.signature[MODELS_INFO]
    assert ("_TZE204_cjbofhxw", "TS0601") in TuyaPJ1203PowerMeter.signature[MODELS_INFO]


def test_pj1203_device_type():
    """Test that replacement device type is METER_INTERFACE."""
    from zhaquirks.const import DEVICE_TYPE, ENDPOINTS

    replacement_device_type = TuyaPJ1203PowerMeter.replacement[ENDPOINTS][1][
        DEVICE_TYPE
    ]
    assert replacement_device_type == zha.DeviceType.METER_INTERFACE


def test_pj1203_clusters_present(pj1203_device):
    """Test that the device has required clusters."""
    assert hasattr(pj1203_device.endpoints[1], "electrical_measurement")
    assert hasattr(pj1203_device.endpoints[1], "tuya_manufacturer")
    assert hasattr(pj1203_device.endpoints[1], "smartenergy_metering")


def test_pj1203_cluster_constants():
    """Test that cluster constants are correctly defined."""
    constants = TuyaElectricalMeasurementPJ1203._CONSTANT_ATTRIBUTES

    # Voltage divisor: 10 (device reports in dV)
    assert constants[ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id] == 10
    assert constants[ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id] == 1

    # Current divisor: 1000 (device reports in mA)
    assert constants[ElectricalMeasurement.AttributeDefs.ac_current_divisor.id] == 1000
    assert constants[ElectricalMeasurement.AttributeDefs.ac_current_multiplier.id] == 1

    # Power divisor: 1 (already converted by DP converter)
    assert constants[ElectricalMeasurement.AttributeDefs.ac_power_divisor.id] == 1
    assert constants[ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id] == 1


def test_pj1203_dp_mappings():
    """Test that DP to attribute mappings are correct."""
    dp_mappings = TuyaPJ1203ManufCluster.dp_to_attribute

    # DP 18 should map to current
    assert 18 in dp_mappings
    assert dp_mappings[18].attribute_name == "rms_current"

    # DP 19 should map to power (with converter)
    assert 19 in dp_mappings
    assert dp_mappings[19].attribute_name == "active_power"
    # Test the converter divides by 10
    assert dp_mappings[19].converter(1000) == 100

    # DP 20 should map to voltage
    assert 20 in dp_mappings
    assert dp_mappings[20].attribute_name == "rms_voltage"

    # DP 101 should map to total energy
    assert 101 in dp_mappings
    assert dp_mappings[101].attribute_name == "current_summ_delivered"


def test_pj1203_data_point_handlers():
    """Test that all DPs have handlers defined."""
    handlers = TuyaPJ1203ManufCluster.data_point_handlers

    assert 18 in handlers
    assert 19 in handlers
    assert 20 in handlers
    assert 101 in handlers

    assert handlers[18] == "_dp_2_attr_update"
    assert handlers[19] == "_dp_2_attr_update"
    assert handlers[20] == "_dp_2_attr_update"
    assert handlers[101] == "_dp_2_attr_update"


def test_pj1203_time_offset():
    """Test that time offset is set to 1970."""
    assert TuyaPJ1203ManufCluster.set_time_offset == 1970


async def test_pj1203_voltage_attribute_update(pj1203_device):
    """Test voltage attribute update."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Simulate voltage update (2398 = 239.8V)
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_voltage.id, 2398
    )

    assert len(em_listener.attribute_updates) >= 1
    voltage_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.rms_voltage.id
        ),
        None,
    )
    assert voltage_update is not None
    assert voltage_update[1] == 2398


async def test_pj1203_current_attribute_update(pj1203_device):
    """Test current attribute update."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Simulate current update (305 = 0.305A)
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_current.id, 305
    )

    assert len(em_listener.attribute_updates) >= 1
    current_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.rms_current.id
        ),
        None,
    )
    assert current_update is not None
    assert current_update[1] == 305


async def test_pj1203_power_attribute_update(pj1203_device):
    """Test power attribute update."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Simulate power update (41 = 41W, already divided by 10 by converter)
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 41
    )

    assert len(em_listener.attribute_updates) >= 1
    power_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.active_power.id
        ),
        None,
    )
    assert power_update is not None
    assert power_update[1] == 41


async def test_pj1203_calculated_apparent_power(pj1203_device):
    """Test that apparent power is calculated from voltage and current."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Update voltage: 2398 dV = 239.8V
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_voltage.id, 2398
    )

    # Update current: 305 mA = 0.305A
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_current.id, 305
    )

    # Find apparent power update
    # Calculation: round((2398 * 305) / 10000) = 73 VA
    apparent_power_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.apparent_power.id
        ),
        None,
    )
    assert apparent_power_update is not None
    expected_apparent_power = round((2398 * 305) / 10000)
    assert apparent_power_update[1] == expected_apparent_power


async def test_pj1203_calculated_power_factor(pj1203_device):
    """Test that power factor is calculated from active and apparent power."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Update voltage: 2398 dV
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_voltage.id, 2398
    )

    # Update current: 305 mA
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_current.id, 305
    )

    # Update active power: 41W
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 41
    )

    # Find power factor update
    # Apparent power = 73 VA
    # Power factor = round((41 * 100) / 73) = 56%
    power_factor_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.power_factor.id
        ),
        None,
    )
    assert power_factor_update is not None
    apparent_power = round((2398 * 305) / 10000)
    expected_pf = min(round((abs(41) * 100) / apparent_power), 100)
    assert power_factor_update[1] == expected_pf


async def test_pj1203_power_factor_capped_at_100(pj1203_device):
    """Test that power factor is capped at 100%."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    em_listener = ClusterListener(em_cluster)

    # Set up values where calculated PF would exceed 100
    # Low voltage and current, high power
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_voltage.id, 1000
    )
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_current.id, 100
    )
    # Apparent power = (1000 * 100) // 10000 = 10 VA
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 50
    )
    # Uncapped PF would be (50 * 100) // 10 = 500%

    # Find power factor update (should be capped at 100)
    power_factor_updates = [
        u
        for u in em_listener.attribute_updates
        if u[0] == ElectricalMeasurement.AttributeDefs.power_factor.id
    ]
    assert len(power_factor_updates) > 0
    # Last update should be capped at 100
    assert power_factor_updates[-1][1] == 100


async def test_pj1203_no_division_by_zero(pj1203_device):
    """Test that power factor calculation handles zero apparent power."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Set voltage and current to values that result in zero apparent power
    em_cluster._update_attribute(ElectricalMeasurement.AttributeDefs.rms_voltage.id, 0)
    em_cluster._update_attribute(ElectricalMeasurement.AttributeDefs.rms_current.id, 0)
    em_cluster._update_attribute(ElectricalMeasurement.AttributeDefs.active_power.id, 0)

    # Should not raise division by zero error
    # Apparent power = 0, so power factor calculation is skipped


async def test_pj1203_read_attributes_constant(pj1203_device):
    """Test reading constant attributes."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Read voltage divisor (constant attribute)
    result = await em_cluster.read_attributes(
        [ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == 10


async def test_pj1203_read_attributes_cached(pj1203_device):
    """Test reading cached attributes."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # First update an attribute
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_voltage.id, 2400
    )

    # Then read it back
    result = await em_cluster.read_attributes(
        [ElectricalMeasurement.AttributeDefs.rms_voltage.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == 2400


async def test_pj1203_read_attributes_unsupported(pj1203_device):
    """Test reading unsupported attributes returns UNSUPPORTED_ATTRIBUTE."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Read an attribute that's not in cache or constants
    result = await em_cluster.read_attributes(
        [ElectricalMeasurement.AttributeDefs.ac_frequency.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.UNSUPPORTED_ATTRIBUTE


async def test_pj1203_read_attributes_by_name(pj1203_device):
    """Test reading attributes by name."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Update attribute first
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.rms_current.id, 500
    )

    # Read by name
    result = await em_cluster.read_attributes(["rms_current"], allow_cache=False)

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == 500


async def test_pj1203_read_active_power_type(pj1203_device):
    """Test that active_power is read with correct type (int16s)."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Update active power
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, -50
    )

    # Read it back
    result = await em_cluster.read_attributes(
        [ElectricalMeasurement.AttributeDefs.active_power.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    # Should preserve negative value (signed int)
    assert records[0].value.value == -50


def test_pj1203_metering_cluster_constants():
    """Test that metering cluster constants are correctly defined."""
    constants = TuyaMeteringPJ1203._CONSTANT_ATTRIBUTES

    # Unit of measure: kWh (0x00)
    assert constants[Metering.AttributeDefs.unit_of_measure.id] == 0x0000

    # Multiplier and divisor for kWh conversion (raw value is in Wh)
    assert constants[Metering.AttributeDefs.multiplier.id] == 1
    assert constants[Metering.AttributeDefs.divisor.id] == 1000

    # Summation formatting
    assert constants[Metering.AttributeDefs.summation_formatting.id] == 0b0_0100_011


async def test_pj1203_energy_attribute_update(pj1203_device):
    """Test energy attribute update on metering cluster."""
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)

    # Simulate energy update (12345 Wh = 12.345 kWh)
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 12345
    )

    assert len(metering_listener.attribute_updates) >= 1
    energy_update = next(
        (
            u
            for u in metering_listener.attribute_updates
            if u[0] == Metering.AttributeDefs.current_summ_delivered.id
        ),
        None,
    )
    assert energy_update is not None
    assert energy_update[1] == 12345


async def test_pj1203_read_metering_attributes_constant(pj1203_device):
    """Test reading constant metering attributes."""
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering

    # Read divisor (constant attribute)
    result = await metering_cluster.read_attributes(
        [Metering.AttributeDefs.divisor.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == 1000


async def test_pj1203_read_metering_attributes_cached(pj1203_device):
    """Test reading cached metering attributes."""
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering

    # First update an attribute
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 54321
    )

    # Then read it back
    result = await metering_cluster.read_attributes(
        [Metering.AttributeDefs.current_summ_delivered.id], allow_cache=False
    )

    records = result[0]
    assert len(records) == 1
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == 54321


# Tests for energy integration feature


async def test_pj1203_energy_counter_reset_compensation(pj1203_device):
    """Test that metering cluster compensates for device energy counter resets."""
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering

    # Initial energy reading
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 1000
    )
    assert metering_cluster.get_compensated_energy_wh() == 1000

    # Energy increases normally
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 1500
    )
    assert metering_cluster.get_compensated_energy_wh() == 1500

    # Device resets - value drops (simulating reconnect)
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 100
    )
    # Should compensate: 100 + 1500 (previous max) = 1600
    assert metering_cluster.get_compensated_energy_wh() == 1600

    # Continue accumulating after reset
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 300
    )
    assert metering_cluster.get_compensated_energy_wh() == 1800


async def test_pj1203_energy_counter_multiple_resets(pj1203_device):
    """Test that multiple device resets are handled correctly."""
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering

    # First session: accumulate to 500
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 500
    )
    assert metering_cluster.get_compensated_energy_wh() == 500

    # First reset
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 50
    )
    assert metering_cluster.get_compensated_energy_wh() == 550

    # Accumulate more
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 200
    )
    assert metering_cluster.get_compensated_energy_wh() == 700

    # Second reset
    metering_cluster._update_attribute(
        Metering.AttributeDefs.current_summ_delivered.id, 25
    )
    # Offset should now be 500 + 200 = 700, plus new value 25 = 725
    assert metering_cluster.get_compensated_energy_wh() == 725


def test_pj1203_power_integration_basic(pj1203_device):
    """Test basic power-to-energy integration."""
    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Verify initial state
    assert em_cluster._integrated_energy_wh == 0.0
    assert em_cluster._last_power_time is None
    assert em_cluster._last_power_value is None

    # First power reading - just sets the baseline, no integration yet
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )
    assert em_cluster._last_power_value == 100
    assert em_cluster._last_power_time is not None
    assert em_cluster._integrated_energy_wh == 0.0  # No integration on first reading


async def test_pj1203_power_integration_accumulation(pj1203_device, monkeypatch):
    """Test that power readings are integrated over time."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    # Mock time.monotonic to control time progression
    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # First reading at t=0
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )

    # Second reading at t=60 (1 minute later) with same power
    mock_time[0] = 60.0
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )

    # Energy = avg_power * time = 100W * 60s / 3600 = 1.6667 Wh
    expected_energy = (100 * 60) / 3600
    assert abs(em_cluster._integrated_energy_wh - expected_energy) < 0.01


async def test_pj1203_power_integration_trapezoidal(pj1203_device, monkeypatch):
    """Test trapezoidal integration with changing power levels."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # Start at 0W
    em_cluster._update_attribute(ElectricalMeasurement.AttributeDefs.active_power.id, 0)

    # 60 seconds later, power jumps to 200W
    mock_time[0] = 60.0
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 200
    )

    # Trapezoidal: avg(0, 200) * 60s / 3600 = 100 * 60 / 3600 = 1.6667 Wh
    expected_energy = (100 * 60) / 3600
    assert abs(em_cluster._integrated_energy_wh - expected_energy) < 0.01


async def test_pj1203_power_integration_gap_handling(pj1203_device, monkeypatch):
    """Test that large time gaps don't cause spurious energy accumulation."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # Initial reading
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 1000
    )

    # Gap larger than MAX_INTEGRATION_GAP (5 minutes = 300 seconds)
    mock_time[0] = 600.0  # 10 minutes
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 1000
    )

    # Should NOT integrate due to large gap
    assert em_cluster._integrated_energy_wh == 0.0


async def test_pj1203_power_integration_updates_metering(pj1203_device, monkeypatch):
    """Test that integrated energy is passed to metering cluster."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement
    metering_cluster = pj1203_device.endpoints[1].smartenergy_metering

    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # First reading
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )

    # Second reading 60 seconds later
    mock_time[0] = 60.0
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )

    # Check metering cluster received the integrated value (rounded)
    # 100W * 60s / 3600 = 1.6667 Wh -> rounded to 2
    assert metering_cluster.get_integrated_energy_wh() == 2


async def test_pj1203_reset_integrated_energy(pj1203_device, monkeypatch):
    """Test resetting the integrated energy counter."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # Accumulate some energy
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )
    mock_time[0] = 60.0  # 60 seconds
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 100
    )

    # 100W * 60s / 3600 = 1.6667 Wh
    expected_energy = (100 * 60) / 3600
    assert abs(em_cluster._integrated_energy_wh - expected_energy) < 0.01

    # Reset
    em_cluster.reset_integrated_energy()

    assert em_cluster._integrated_energy_wh == 0.0
    assert em_cluster._last_power_time is None
    assert em_cluster._last_power_value is None


async def test_pj1203_get_integrated_energy(pj1203_device, monkeypatch):
    """Test get_integrated_energy_wh method."""
    from zhaquirks.tuya import ts0601_pj1203

    em_cluster = pj1203_device.endpoints[1].electrical_measurement

    mock_time = [0.0]

    def mock_monotonic():
        return mock_time[0]

    monkeypatch.setattr(ts0601_pj1203.time, "monotonic", mock_monotonic)

    # Initial state
    assert em_cluster.get_integrated_energy_wh() == 0.0

    # Accumulate energy
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 50
    )
    mock_time[0] = 120.0  # 2 minutes
    em_cluster._update_attribute(
        ElectricalMeasurement.AttributeDefs.active_power.id, 50
    )

    # 50W * 120s / 3600 = 1.6667 Wh
    expected_energy = (50 * 120) / 3600
    assert abs(em_cluster.get_integrated_energy_wh() - expected_energy) < 0.01
