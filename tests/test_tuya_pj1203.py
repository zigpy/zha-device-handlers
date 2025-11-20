"""Tests for Tuya PJ-1203 Single Channel Clamp Energy Meter quirk."""

import pytest
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import ClusterListener
from zhaquirks.const import MODELS_INFO
from zhaquirks.tuya.ts0601_pj1203 import (
    TuyaElectricalMeasurementPJ1203,
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


def test_pj1203_data_point_handlers():
    """Test that all DPs have handlers defined."""
    handlers = TuyaPJ1203ManufCluster.data_point_handlers

    assert 18 in handlers
    assert 19 in handlers
    assert 20 in handlers

    assert handlers[18] == "_dp_2_attr_update"
    assert handlers[19] == "_dp_2_attr_update"
    assert handlers[20] == "_dp_2_attr_update"


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
    # Calculation: (2398 * 305) // 10000 = 73 VA
    apparent_power_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.apparent_power.id
        ),
        None,
    )
    assert apparent_power_update is not None
    expected_apparent_power = (2398 * 305) // 10000
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
    # Power factor = (41 * 100) // 73 = 56%
    power_factor_update = next(
        (
            u
            for u in em_listener.attribute_updates
            if u[0] == ElectricalMeasurement.AttributeDefs.power_factor.id
        ),
        None,
    )
    assert power_factor_update is not None
    apparent_power = (2398 * 305) // 10000
    expected_pf = (abs(41) * 100) // apparent_power
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
