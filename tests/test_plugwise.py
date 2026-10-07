"""Tests for the Plugwise Emma 170-01 ZHA quirk."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import ZCLAttributeAccess

import zhaquirks
from zhaquirks.plugwise import emma

zhaquirks.setup()


PLUGWISE_MFG_CODE = 0x1172
ATTR_EXT_HEAT_DEMAND = 0xF000
ATTR_EXT_HEAT_DEMAND_TIMEOUT = 0xF001
ATTR_BOILER_WATER_TEMP = 0xF002
ATTR_DHW_TEMP = 0xF003
ATTR_RETURN_WATER_TEMP = 0xF004
ATTR_APP_FAULT_CODE = 0xF005
ATTR_OEM_FAULT_CODE = 0xF006
ATTR_MAX_DHW_SETPOINT = 0xF007
ATTR_MAX_BOILER_SETPOINT = 0xF008
ATTR_BATTERY_TYPE = 0x007F


# ── EmmaBatteryType ──────────────────────────────────────────────────────────


def test_battery_type_alkaline_value() -> None:
    """Verify Alkaline enum value is 0x00."""
    assert emma.EmmaBatteryType.Alkaline == 0x00


def test_battery_type_nimh_value() -> None:
    """Verify NiMH enum value is 0x01."""
    assert emma.EmmaBatteryType.NiMH == 0x01


def test_battery_type_is_enum8() -> None:
    """Verify EmmaBatteryType inherits from zigpy enum8."""
    assert issubclass(emma.EmmaBatteryType, t.enum8)


# ── EmmaApplicationFaultCode ─────────────────────────────────────────────────


def test_fault_code_is_bitmap8() -> None:
    """Verify EmmaApplicationFaultCode inherits from zigpy bitmap8."""
    assert issubclass(emma.EmmaApplicationFaultCode, t.bitmap8)


def test_fault_code_all_bits_defined() -> None:
    """Verify all six OpenTherm fault bits are defined with correct values."""
    fc = emma.EmmaApplicationFaultCode
    assert fc.ServiceRequest == 0x01
    assert fc.LockoutReset == 0x02
    assert fc.LowWaterPressure == 0x04
    assert fc.GasFlameFault == 0x08
    assert fc.AirPressureFault == 0x10
    assert fc.WaterOverTemp == 0x20


def test_fault_code_bits_are_powers_of_two() -> None:
    """Verify each fault bit is a distinct power of two (no overlap)."""
    fc = emma.EmmaApplicationFaultCode
    bits = [
        fc.ServiceRequest,
        fc.LockoutReset,
        fc.LowWaterPressure,
        fc.GasFlameFault,
        fc.AirPressureFault,
        fc.WaterOverTemp,
    ]
    for b in bits:
        assert b > 0 and (b & (b - 1)) == 0


# ── EmmaThermostatCluster ────────────────────────────────────────────────────


def test_thermostat_cluster_is_thermostat_subclass() -> None:
    """Verify EmmaThermostatCluster inherits from the standard Thermostat cluster."""
    assert issubclass(emma.EmmaThermostatCluster, Thermostat)


def test_thermostat_cluster_id_unchanged() -> None:
    """Verify the cluster_id matches the standard HVAC Thermostat cluster id."""
    assert emma.EmmaThermostatCluster.cluster_id == Thermostat.cluster_id


@pytest.mark.parametrize(
    "attr_name,attr_id,expected_type,writable",
    [
        ("external_heat_demand", ATTR_EXT_HEAT_DEMAND, t.uint16_t, True),
        (
            "external_heat_demand_timeout",
            ATTR_EXT_HEAT_DEMAND_TIMEOUT,
            t.uint16_t,
            True,
        ),
        ("boiler_water_temperature", ATTR_BOILER_WATER_TEMP, t.int16s, False),
        ("dhw_temperature", ATTR_DHW_TEMP, t.int16s, False),
        ("return_water_temperature", ATTR_RETURN_WATER_TEMP, t.int16s, False),
        ("oem_fault_code", ATTR_OEM_FAULT_CODE, t.uint8_t, False),
        ("max_dhw_setpoint", ATTR_MAX_DHW_SETPOINT, t.int16s, True),
        ("max_boiler_setpoint", ATTR_MAX_BOILER_SETPOINT, t.int16s, True),
    ],
)
def test_thermostat_mfg_attribute(attr_name, attr_id, expected_type, writable) -> None:
    """Verify each manufacturer-specific thermostat attribute has correct id, type, access."""
    cluster = emma.EmmaThermostatCluster
    attr = cluster.attributes_by_name[attr_name]

    assert attr.id == attr_id, f"{attr_name}: expected id 0x{attr_id:04X}"
    assert attr.type is expected_type, f"{attr_name}: expected type {expected_type}"
    assert attr.manufacturer_code == PLUGWISE_MFG_CODE, f"{attr_name}: wrong mfg code"
    assert attr.is_manufacturer_specific is True, f"{attr_name}: missing mfg flag"

    if writable:
        assert ZCLAttributeAccess.Write in attr.access, (
            f"{attr_name}: expected writable"
        )
    else:
        assert ZCLAttributeAccess.Write not in attr.access, (
            f"{attr_name}: expected read-only"
        )


def test_thermostat_application_fault_code_attribute() -> None:
    """Verify application_fault_code uses EmmaApplicationFaultCode bitmap type."""
    cluster = emma.EmmaThermostatCluster
    attr = cluster.attributes_by_name["application_fault_code"]

    assert attr.id == ATTR_APP_FAULT_CODE
    assert attr.type is emma.EmmaApplicationFaultCode
    assert attr.manufacturer_code == PLUGWISE_MFG_CODE
    assert attr.is_manufacturer_specific is True
    assert ZCLAttributeAccess.Write not in attr.access


def test_thermostat_standard_attrs_preserved() -> None:
    """Verify standard Thermostat attributes are not removed by the custom cluster."""
    cluster = emma.EmmaThermostatCluster
    required = [
        "local_temperature",
        "occupied_heating_setpoint",
        "occupied_cooling_setpoint",
        "system_mode",
        "pi_heating_demand",
        "running_state",
        "outdoor_temperature",
        "local_temperature_calibration",
        "min_heat_setpoint_limit",
        "max_heat_setpoint_limit",
        "min_cool_setpoint_limit",
        "max_cool_setpoint_limit",
    ]
    for name in required:
        assert name in cluster.attributes_by_name, (
            f"Standard attribute '{name}' missing from EmmaThermostatCluster"
        )


def test_thermostat_all_mfg_attrs_have_plugwise_mfg_code() -> None:
    """Verify all nine Plugwise-specific attributes carry mfgCode 0x1172."""
    cluster = emma.EmmaThermostatCluster
    mfg_attr_ids = {
        ATTR_EXT_HEAT_DEMAND,
        ATTR_EXT_HEAT_DEMAND_TIMEOUT,
        ATTR_BOILER_WATER_TEMP,
        ATTR_DHW_TEMP,
        ATTR_RETURN_WATER_TEMP,
        ATTR_APP_FAULT_CODE,
        ATTR_OEM_FAULT_CODE,
        ATTR_MAX_DHW_SETPOINT,
        ATTR_MAX_BOILER_SETPOINT,
    }
    for attr_id in mfg_attr_ids:
        attr = cluster.attributes.get(attr_id)
        assert attr is not None, f"Attribute 0x{attr_id:04X} missing"
        assert attr.manufacturer_code == PLUGWISE_MFG_CODE, (
            f"Attribute 0x{attr_id:04X} has wrong manufacturer code"
        )


def test_thermostat_exactly_nine_mfg_attrs() -> None:
    """Verify exactly nine Plugwise manufacturer-specific attributes are added."""
    emma_attrs = {
        a.id
        for a in emma.EmmaThermostatCluster.attributes.values()
        if a.manufacturer_code == PLUGWISE_MFG_CODE
    }
    assert len(emma_attrs) == 9, (
        f"Expected 9 Plugwise mfg attrs, got {len(emma_attrs)}: {emma_attrs}"
    )


# ── EmmaPowerConfigCluster ───────────────────────────────────────────────────


def test_power_config_cluster_is_subclass() -> None:
    """Verify EmmaPowerConfigCluster inherits from PowerConfiguration."""
    assert issubclass(emma.EmmaPowerConfigCluster, PowerConfiguration)


def test_power_config_cluster_id_unchanged() -> None:
    """Verify cluster_id matches the standard PowerConfiguration cluster id."""
    assert emma.EmmaPowerConfigCluster.cluster_id == PowerConfiguration.cluster_id


def test_power_config_battery_type_attribute() -> None:
    """Verify battery_type attribute has correct id, type, access, and mfg code."""
    cluster = emma.EmmaPowerConfigCluster
    attr = cluster.attributes_by_name["battery_type"]

    assert attr.id == ATTR_BATTERY_TYPE
    assert attr.type is emma.EmmaBatteryType
    assert attr.manufacturer_code == PLUGWISE_MFG_CODE
    assert attr.is_manufacturer_specific is True
    assert ZCLAttributeAccess.Write in attr.access


def test_power_config_standard_attrs_preserved() -> None:
    """Verify standard battery_percentage_remaining attribute is still present."""
    cluster = emma.EmmaPowerConfigCluster
    assert "battery_percentage_remaining" in cluster.attributes_by_name


# ── Module constants ─────────────────────────────────────────────────────────


def test_module_manufacturer_code() -> None:
    """Verify PLUGWISE_MFG_CODE constant is 0x1172."""
    assert emma.PLUGWISE_MFG_CODE == 0x1172


def test_module_plugwise_string() -> None:
    """Verify PLUGWISE constant is the string 'Plugwise'."""
    assert emma.PLUGWISE == "Plugwise"


def test_module_attribute_id_constants() -> None:
    """Verify all attribute ID constants match the Plugwise R0010 spec."""
    assert emma.ATTR_EXT_HEAT_DEMAND == 0xF000
    assert emma.ATTR_EXT_HEAT_DEMAND_TIMEOUT == 0xF001
    assert emma.ATTR_BOILER_WATER_TEMP == 0xF002
    assert emma.ATTR_DHW_TEMP == 0xF003
    assert emma.ATTR_RETURN_WATER_TEMP == 0xF004
    assert emma.ATTR_APP_FAULT_CODE == 0xF005
    assert emma.ATTR_OEM_FAULT_CODE == 0xF006
    assert emma.ATTR_MAX_DHW_SETPOINT == 0xF007
    assert emma.ATTR_MAX_BOILER_SETPOINT == 0xF008
    assert emma.ATTR_BATTERY_TYPE == 0x007F


# ── Quirk registration ───────────────────────────────────────────────────────


def test_quirk_required_classes_exported() -> None:
    """Verify all expected public classes are present in the quirk module."""
    assert hasattr(emma, "EmmaThermostatCluster")
    assert hasattr(emma, "EmmaPowerConfigCluster")
    assert hasattr(emma, "EmmaHumidityCluster")
    assert hasattr(emma, "EmmaBatteryType")
    assert hasattr(emma, "EmmaApplicationFaultCode")


# ── Reporting-config clamping (custom logic — required by repo guidelines) ───


async def test_thermostat_clamps_restricted_attr_intervals(zigpy_device_from_v2_quirk):
    """Verify EmmaThermostatCluster clamps min/max to firmware-accepted bounds."""
    device = zigpy_device_from_v2_quirk(manufacturer="Plugwise", model="170-01")
    cluster = device.endpoints[1].thermostat
    assert isinstance(cluster, emma.EmmaThermostatCluster)

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (
            [
                foundation.ConfigureReportingResponseRecord(
                    status=foundation.Status.SUCCESS,
                    direction=foundation.ReportingDirection.SendReports,
                    attrid=Thermostat.AttributeDefs.occupied_heating_setpoint.id,
                )
            ],
        )
        # ZHA default REPORT_CONFIG_CLIMATE is (30, 900, 25) — out of Emma's range.
        await cluster.configure_reporting(
            Thermostat.AttributeDefs.occupied_heating_setpoint.id, 30, 900, 25
        )

        assert request_mock.call_count == 1
        sent_records = request_mock.call_args.args[3]
        assert sent_records[0].min_interval == 1
        assert sent_records[0].max_interval == 870
        assert sent_records[0].reportable_change == 25


async def test_thermostat_clamps_local_temperature_change(zigpy_device_from_v2_quirk):
    """Verify local_temperature reportable_change is clamped to firmware range 1..10."""
    device = zigpy_device_from_v2_quirk(manufacturer="Plugwise", model="170-01")
    cluster = device.endpoints[1].thermostat

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (
            [
                foundation.ConfigureReportingResponseRecord(
                    status=foundation.Status.SUCCESS,
                    direction=foundation.ReportingDirection.SendReports,
                    attrid=Thermostat.AttributeDefs.local_temperature.id,
                )
            ],
        )
        await cluster.configure_reporting(
            Thermostat.AttributeDefs.local_temperature.id, 30, 900, 25
        )

        sent_records = request_mock.call_args.args[3]
        assert sent_records[0].reportable_change == 10  # clamped from 25 into 1..10


async def test_power_config_clamps_battery_max_interval(zigpy_device_from_v2_quirk):
    """Verify battery_percentage_remaining max_interval is raised to ≥ 43200."""
    device = zigpy_device_from_v2_quirk(manufacturer="Plugwise", model="170-01")
    cluster = device.endpoints[1].power

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (
            [
                foundation.ConfigureReportingResponseRecord(
                    status=foundation.Status.SUCCESS,
                    direction=foundation.ReportingDirection.SendReports,
                    attrid=PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
                )
            ],
        )
        # ZHA's REPORT_CONFIG_BATTERY_SAVE default is (3600, 10800, 1).
        await cluster.configure_reporting(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
            3600,
            10800,
            1,
        )

        sent_records = request_mock.call_args.args[3]
        assert sent_records[0].max_interval >= 43200


async def test_humidity_forces_exact_intervals(zigpy_device_from_v2_quirk):
    """Verify EmmaHumidityCluster forces min=1, max=870 regardless of input."""
    device = zigpy_device_from_v2_quirk(manufacturer="Plugwise", model="170-01")
    cluster = device.endpoints[1].humidity

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (
            [
                foundation.ConfigureReportingResponseRecord(
                    status=foundation.Status.SUCCESS,
                    direction=foundation.ReportingDirection.SendReports,
                    attrid=0,
                )
            ],
        )
        await cluster.configure_reporting(0, 30, 900, 100)

        sent_records = request_mock.call_args.args[3]
        assert sent_records[0].min_interval == 1
        assert sent_records[0].max_interval == 870
        assert sent_records[0].reportable_change == 100  # in range 10..300


async def test_humidity_passes_through_non_measured_value(zigpy_device_from_v2_quirk):
    """Verify EmmaHumidityCluster does not rewrite other attributes' reporting."""
    device = zigpy_device_from_v2_quirk(manufacturer="Plugwise", model="170-01")
    cluster = device.endpoints[1].humidity
    tolerance_attr_id = 0x0003  # RelativeHumidity.AttributeDefs.tolerance.id

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (
            [
                foundation.ConfigureReportingResponseRecord(
                    status=foundation.Status.SUCCESS,
                    direction=foundation.ReportingDirection.SendReports,
                    attrid=tolerance_attr_id,
                )
            ],
        )
        await cluster.configure_reporting(tolerance_attr_id, 30, 900, 5)

        sent_records = request_mock.call_args.args[3]
        assert sent_records[0].attrid == tolerance_attr_id
        assert sent_records[0].min_interval == 30
        assert sent_records[0].max_interval == 900
        assert sent_records[0].reportable_change == 5
